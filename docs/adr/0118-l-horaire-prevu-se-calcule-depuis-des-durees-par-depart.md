# ADR-0118 — L'horaire prévu se calcule depuis des durées d'étape, pour chaque départ, par le graphe des sources

- **Statut** : Accepté
- **Date** : 2026-10-02
- **US** : E03US010
- **Décideurs** : Organisateur / Architecte

## Contexte

Le cahier des charges demande un déroulé horaire de la journée (EF-4.10, EF-9.1) et laissait ouverte
sa production : c'est sa question **Q4** (« auto ou saisie manuelle ? »), que cet ADR ferme, avec la
question **P05** laissée ouverte dans [`stories/E16`](../../stories/E16-retours-maquettes.md) le
10/09/2026 (lecture **(a)** retenue). Trois faits du code d'aujourd'hui contraignent la réponse :

1. **Le déroulé est défini une fois par tournoi** ([ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)),
   mais l'heure dépend du **créneau** : un tournoi à deux départs (9 h, 14 h) joue la même séquence à
   deux heures différentes. Une heure stockée sur l'étape serait fausse dès le second départ.
2. **L'`ordre` d'une étape est topologique, pas chronologique** ([ADR-0082](0082-plusieurs-qualifications-dans-un-meme-deroule.md)) :
   deux étapes nourries par la même source se jouent **en même temps**. Additionner les durées dans
   l'ordre ferait commencer la seconde après la première.
3. **Une pause programmée n'a pas de durée** ([ADR-0091](0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md)) :
   elle est levée par un geste d'admin, donc elle ne peut pas s'ajouter d'elle-même à un horaire.

Le référentiel FFTA ne donne que le temps de **tir** d'une volée (2 min), pas la cadence réelle
(tir, marque, retrait) : toute estimation automatique reposerait sur une constante inventée.

## Décision

1. **L'étape porte une durée, jamais une heure.** `EtapeDeroule.duree_prevue` : minutes entières,
   1 à 1440, **facultative**, pauses comprises. Elle n'est **jamais préremplie** (arbitrage du
   02/10/2026). Elle voyage avec le format (`ModelePhase.duree_prevue`), comme `titre`.
2. **L'heure se calcule, par départ, sur le graphe des sources.** Une étape sans source commence à
   l'heure du départ ; une étape avec sources commence à la fin **la plus tardive** de ses sources ;
   sa fin est son début plus sa durée. Le calcul est une fonction pure du domaine
   (`horaires_prevus`), exécutée à chaque lecture : **rien n'est persisté** hormis la durée.
3. **L'inconnu se propage, jamais ne se devine.** Sans durée, la fin d'une étape est inconnue, et
   le début (donc la fin) de toute sa descendance aussi. Une source introuvable ou un cycle — que le
   déroulé n'admet pas — donnent « inconnu » plutôt qu'une erreur.
4. **Une heure garde son jour.** Comptée en minutes depuis minuit du jour du départ, elle peut passer
   24 h ; elle se rend `HH:MM` plus un nombre de jours après (« lendemain »).
5. **Une route de lecture dédiée, étroite et ouverte** : `GET /tournois/{id}/horaires-prevus`, un jeu
   d'horaires par créneau. `PhaseReponse` n'est **pas** élargie : la route d'avancement est déjà
   servie entière à l'anonyme (`DETTE-071`), et le public ne lit que le **début** (réponse P05 :
   « seulement pour les départs des différentes phases, les autres sont trop imprévisibles »).
6. **Prévisionnel seul** : aucun calcul d'avance ou de retard sur le réel.

## Alternatives écartées

- **Heures saisies à la main, par étape et par départ** : à refaire pour chaque créneau, et rien ne
  se décale quand l'heure d'un départ change.
- **Heure épinglée sur une étape** (« finales à 17 h ») : plus riche, mais des cas limites (une heure
  épinglée antérieure à la fin de ses sources) que le besoin exprimé ne demande pas. Réouvrable.
- **Maille du tour** : plus fine, mais le commanditaire juge les tours « trop imprévisibles ».
- **Préremplissage par une cadence** (minutes par volée) : constante non fournie par le référentiel.
- **Champs d'horaire sur `PhaseReponse`** : aggraverait `DETTE-071` ; le public rapproche donc par
  `ordre`, qu'une phase partage avec l'étape dont elle est assemblée (ADR-0076).

## Conséquences

- **Aucune migration** : la durée vit à la racine du `config` JSON de l'étape, comme `titre` ; une
  étape antérieure se relit « durée inconnue », ce qui est exactement le sens voulu.
- Deux étapes parallèles qui partagent en réalité les mêmes cibles seront annoncées **simultanées** :
  le graphe ne connaît pas la salle. L'organisateur l'exprime aujourd'hui par une durée plus longue
  sur la source ; une contrainte de salle relèverait d'une autre US.
- L'heure d'un départ modifiée n'invalide pas le cache des horaires côté front : il se rattrape au
  remontage et par un poll de 60 s — c'est un prévisionnel.
- `E09US007` (déroulé imprimable) peut consommer la même lecture.

## Porté dans le code par

- `backend/domain/horaire_prevu.py` — `horaires_prevus` (§2, §3), `HeurePrevue` (§4),
  `verifier_duree_prevue` et `DUREE_PREVUE_MAX` (§1).
- `backend/domain/deroule_etape.py` — `EtapeDeroule.duree_prevue`, validée dans `__post_init__`.
- `backend/domain/format_tournoi.py` — `ModelePhase.duree_prevue`, traduite par `pour_tournoi` et
  `d_etape` ; sans invariant (E01US024), d'où la borne de `backend/api/v1/formats.py`.
- `backend/infrastructure/db/repositories/moteur.py` — `_politiques_json` (deux appelants) et
  `_lire_duree_prevue`.
- `backend/application/phases.py` — `ServicePhases.horaires_prevus` et `HorairesDuDepart`.
- `backend/api/v1/phases.py` — `lister_horaires_prevus` (§5) et `ConfigPhaseRequete.duree_prevue`.
- `frontend/src/features/phases/GrilleHoraire.tsx` — la grille admin ; la durée se saisit par
  `frontend/src/shared/phases/ChampDureePrevue.tsx`.
- `frontend/src/features/en-cours/presentation.ts` — `debutsPrevus`, lu par `VueEnCours.tsx` (§5).
