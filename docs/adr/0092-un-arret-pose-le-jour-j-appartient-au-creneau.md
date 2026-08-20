# ADR-0092 — Un arrêt posé le jour J appartient au créneau, pas au déroulé

- **Statut** : Accepté
- **Date** : 20/08/2026
- **US** : `E05US034` (tranche B du découpage d'`E05US033`)
- **Complète** : [ADR-0091](0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md)
  (qu'il ne révise pas : le mécanisme de coupe est inchangé)
- **S'appuie sur** : [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md) §4 et §5
  *(« applique » aurait été plus juste, mais le vocabulaire de l'atlas porte déjà « s'appuie
  sur » pour cette relation : en ajouter un synonyme aurait élargi une table sans rien
  distinguer de neuf.)*

## Contexte et problème

`E05US033` a livré les **arrêts programmés** : l'organisateur pose à l'atelier une liste de pauses
par phase (« après le tour 2, après le tour 5 »), et la salle s'arrête toute seule quand le tour
déclencheur s'achève. Ces arrêts sont de la **définition de déroulé** : ils vivent dans
`deroule_etape.config`, portés par le tournoi, et **tous les créneaux les rejouent** — c'est la
lettre d'ADR-0076 §4, et c'est ce qui rend impossible la divergence entre deux départs.

Le jour J, ce modèle ne suffit pas. Une panne de chauffage à 14 h, une ambulance dans le gymnase,
une remise de récompenses qui déborde : l'organisateur veut **couper maintenant, dans deux tours**,
sans avoir rien prévu à l'atelier. C'est le CA d'`E05US034` : *« bloquer dans x tours »*.

**La solution évidente est fausse.** Ajouter un `ArretProgramme` à l'`EtapeDeroule` du tournoi
« marcherait » — le déclencheur le lirait, la coupe tomberait. Mais l'arrêt serait alors **rejoué par
le créneau de l'après-midi**, qui n'a aucune raison de s'arrêter : le chauffage est réparé depuis
deux heures. C'est une décision locale **propagée**, symétrique exact de la divergence silencieuse
qu'ADR-0076 a supprimée — et aussi peu détectable, puisque rien n'a l'air anormal jusqu'au moment où
la salle s'éteint pour une raison qui n'existe plus.

ADR-0076 avait déjà tranché la question, sans qu'on ait eu besoin d'y revenir jusqu'ici :

- **§4 composer** (ajouter, éditer, réordonner une étape) se fait **au tournoi**, à l'atelier ;
- **§5 faire vivre** (démarrer, mettre en pause, terminer) se fait **au départ**, au pilotage.

Programmer une pause à l'atelier est de la composition. Couper la salle à 14 h est de la conduite.
Elles ne peuvent pas partager un rangement.

## Décision

**Un arrêt décidé pendant que la salle tire est un objet distinct, porté par le départ, et rejoué par
personne.** Le mécanisme se lit désormais en **trois natures**, là où ADR-0091 en distinguait deux :

```
Tournoi ──► EtapeDeroule.arrets      DÉFINITION  — posée à l'atelier, rejouée par TOUS les créneaux
Départ  ──► ArretDeCirconstance      CONDUITE    — posée au pilotage, rejouée par PERSONNE
Départ  ──► FranchissementArret      AVANCEMENT  — ce qu'un arrêt a coupé, ici, et son relèvement
```

1. **`ArretDeCirconstance`** (`domain/arret_programme.py`) porte `depart_id`, `phase_id`,
   `apres_tour`, `portee`. Il a une **table à lui** (`arret_de_circonstance`, migration `0049`), et
   non un document JSON : l'unicité `(depart_id, phase_id, apres_tour)` doit être tenue par le
   schéma — la pose est concurrente, un double-clic est un geste ordinaire du jour J, et un document
   JSON ne sait pas tenir une contrainte d'unicité. Le volume ne tranche rien : quelques lignes par
   créneau dans les deux cas.
2. **« Dans x tours » se convertit au serveur**, pas au client (`tour_d_un_arret_relatif`). Le tour
   courant est une donnée serveur ; un client qui le calculerait couperait au mauvais endroit dès
   qu'il aurait dix secondes de retard. **Le tour en cours compte dans les x** : « dans 1 tour » veut
   dire *celui-là finit, puis on s'arrête*, ce qui est la lecture de quelqu'un qui a le numéro du
   tour sous les yeux.
3. **Le déclencheur lit les deux natures fondues** (`arrets_applicables`), et non en deux passes. Un
   second chemin d'évaluation aurait été une seconde occasion de diverger sur la question la plus
   délicate du module — *ce tour est-il fini ?* —, celle qui a produit trois bloquants en revue
   d'`E05US033`.
4. **Strict à la pose, tolérant à l'évaluation.** Poser un arrêt sur un tour déjà occupé est
   **refusé** (l'organisateur est devant l'écran, il peut corriger). Rencontrer deux arrêts sur le
   même tour à l'évaluation les **fusionne**, portée la plus large gagnante. L'asymétrie n'est pas
   une inconséquence : la collision peut naître **après** la pose sans que personne ne se trompe —
   l'atelier ajoute un arrêt après le tour 4 pendant qu'un créneau en porte déjà un, et ADR-0076 lui
   **interdit** de voir l'avancement d'un créneau. Lever une exception à l'évaluation gèlerait le
   déclencheur du créneau entier : plus aucune pause ne tomberait, pour aucune phase.
5. **La règle « ce type annonce-t-il ses tours ? » est hissée** au module d'arrêt
   (`verifier_type_arretable`) et partagée par les deux portes d'entrée. Elle vivait sur
   `EtapeDeroule` tant qu'il n'y en avait qu'une ; deux copies divergent, et c'est toujours celle
   écrite en second qui rate le cas nouveau.
6. **Un arrêt qui a coupé porte l'instant de sa coupe** (`arrete_depuis`, horodaté par le port
   `Horloge`). C'est ce que la pastille de rappel décompte. **La première extinction, pas la
   dernière** : un arrêt de créneau éteint la salle en plusieurs minutes, et ré-horodater à chaque
   phase coupée ferait *rajeunir* le compteur — « depuis 1 min » sur une salle arrêtée depuis vingt,
   c'est-à-dire un mensonge dans le sens qui endort la vigilance. Le champ est **nullable**, et le
   `NULL` a un sens : cet arrêt n'a encore rien éteint.

### Ce qui a été écarté

- **Ajouter l'arrêt au déroulé du tournoi.** Le cœur du problème : la décision serait propagée à
  tous les créneaux. Cf. ci-dessus.
- **Un état `PROGRAMME` de plus sur `FranchissementArret`.** ADR-0091 explique pourquoi cet état
  n'existe pas : « programmé » est l'**absence** de franchissement. Le réintroduire pour les seuls
  arrêts de circonstance ferait porter à la table de l'avancement une moitié de la définition, et
  « un arrêt franchi » cesserait de vouloir dire « un arrêt atteint ».
- **Un champ JSON sur `depart`.** Écarté pour l'unicité, pas pour le volume (§1).
- **Une durée calculée par le serveur** (« depuis 14 min » dans le DTO). La route est pollée toutes
  les 10 s mais le rendu vit *entre* deux réponses : le compteur resterait figé à 14 pendant dix
  secondes de plus. Le serveur rend un **instant**, le client en fait une durée.
- **Un `retirer` sur le port.** Le CA n'en demande pas, et le coût d'une erreur de saisie est d'un
  clic : l'arrêt tombe, l'organisateur relance. Une porte de plus à garder, et celle-là capable
  d'annuler une pause que la salle attend déjà. *(Si l'usage le réclame, c'est une US, pas un
  ajout en douce.)*

## Conséquences

**Positives**

- Le jour J cesse d'être prisonnier de ce qui a été prévu la veille : couper la salle ne demande plus
  d'éditer le déroulé du tournoi, donc plus de risque d'emporter les autres créneaux.
- La frontière d'ADR-0076 est appliquée là où elle n'avait encore jamais été mise à l'épreuve : le
  premier objet du projet qui est *de la configuration* **et** *propre à un créneau*. Le rangement
  est désormais explicite plutôt que déduit à chaque fois.
- Une seule règle de type pour deux portes d'entrée, une seule évaluation pour deux natures d'arrêt :
  la surface où deux chemins peuvent diverger ne grandit pas avec la capacité.

**Négatives, et assumées**

- **Une table de plus** pour quelques lignes par créneau. Le prix de l'unicité tenue par le schéma.
- **Une cinquième lecture au chemin court d'`evaluer`.** Le déclencheur tourne après chaque
  validation de score ; il lit maintenant aussi les arrêts de circonstance avant de pouvoir sortir.
  Sans cela, un arrêt posé le jour J serait **inerte** — le mode de panne le plus vicieux du
  mécanisme : la pose répond 200, l'écran affiche l'arrêt, et l'heure passe sans que rien ne coupe.
  Quatre `SELECT` indexés deviennent cinq ; l'ordre de grandeur ne change pas.
- **Trois DTO d'arrêt à la frontière API** (`ArretProgrammeDTO`, `ArretFranchiReponse`,
  `PoserArretRelatifRequete` / `ArretDeCirconstanceReponse`). Ce n'est pas une redondance : les deux
  premiers portent un `apres_tour` **absolu**, le troisième un **relatif**. Les confondre serait le
  piège du jour J.
- **Un arrêt posé par erreur ne s'annule pas** (cf. « Ce qui a été écarté »). Il coupe, on relance.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision — cf.
ADR-0017, dont c'est la leçon, et ADR-0091, dont trois lignes affirmaient plus que le code ne portait.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 nature distincte, portée par le créneau | `backend/domain/arret_programme.py` (`ArretDeCirconstance`, `definition()`) | oui — `tests/test_domain_arret_programme.py` (section E05US034) |
| §1 table à part, unicité par le schéma | `backend/infrastructure/db/models.py` (`ArretDeCirconstanceORM`) ; `backend/migrations/versions/0049_arret_de_circonstance.py` | oui — aller-retour **et** double-pose refusée dans `tests/test_arrets_api.py` |
| §1 lecture cloisonnée par créneau | `backend/domain/ports.py` (`ArretDeCirconstanceRepository`) ; `backend/infrastructure/db/repositories/moteur.py` (`ArretDeCirconstanceRepositorySQL.par_depart`, `where depart_id`) | oui — l'oracle vérifie qu'un second créneau du **même tournoi** ne voit rien |
| §2 conversion « dans x tours » au serveur | `backend/domain/arret_programme.py` (`tour_d_un_arret_relatif`) ; `backend/application/arrets_programmes.py` (`poser_arret_relatif`) ; `backend/api/v1/phases.py` (`poser_arret_relatif`, `PoserArretRelatifRequete`) | oui — dont le décalage d'une unité (`x = 1` → tour courant) et le refus sur tour illisible |
| §3 les deux natures fondues à l'évaluation | `backend/domain/arret_programme.py` (`arrets_applicables`) ; `backend/application/arrets_programmes.py` (`_declencher_les_arrets_atteints`, `_circonstance_par_phase`, `_tour_acheve` qui reçoit désormais les arrêts et non l'étape) | oui — dont « l'arrêt du jour J s'ajoute aux programmés » (deux coupes, une relance entre les deux) |
| §3 le chemin court voit les deux natures | `backend/application/arrets_programmes.py` (`evaluer`, garde `aucun_arret`) | oui — `test_un_arret_relatif_coupe_la_phase_quand_son_tour_s_acheve` échoue si la garde ignore les arrêts de circonstance |
| §4 strict à la pose, tolérant à l'évaluation | `backend/application/arrets_programmes.py` (`poser_arret_relatif`, `verifier_arrets` sur l'union) ; `backend/domain/arret_programme.py` (`arrets_applicables`, fusion + portée la plus large) | oui — les deux moitiés ont leur oracle, et le test de fusion dit pourquoi elles diffèrent |
| §5 une règle de type, deux portes | `backend/domain/arret_programme.py` (`verifier_type_arretable`) ; appelée par `backend/domain/deroule_etape.py` (`_verifier_arrets_applicables`) **et** `backend/application/arrets_programmes.py` (`poser_arret_relatif`) | oui — 422 sur la route de pose (`tests/test_arrets_api.py`), refus de composition inchangé |
| §6 horodatage de la première coupe | `backend/domain/arret_programme.py` (`FranchissementArret.arrete_depuis`) ; `backend/application/arrets_programmes.py` (`_horodate`, port `Horloge`) ; `backend/bootstrap/composition.py` (`HorlogeSysteme`) | oui — dont « l'instant ne rajeunit pas quand une seconde phase s'éteint douze minutes plus tard » |
| §6 le serveur rend un instant, le client une durée | `backend/api/v1/phases.py` (`ArretFranchiReponse.arrete_depuis`) ; `frontend/src/shared/phases/relance.ts` (`resumeDeRelance`, `phraseDeRelance`) | oui — `frontend/src/shared/phases/relance.test.ts` (12 oracles, dont horloge en avance et date illisible) |
| CA pastille de rappel | `frontend/src/features/accueil/Accueil.tsx` (`PastilleDeRelance`, `useQueries` sur la route déjà pollée) ; `frontend/src/shared/ui/useMaintenant.ts` | oui pour la **phrase** et le **résumé** (tests) ; le montage à l'écran se vérifie à l'œil, comme le reste de l'accueil |
| CA pose depuis le pilotage | `frontend/src/features/suivi-deroule/{api.ts,hooks.ts}` (`poserArretRelatif`, `usePoserArretRelatif`) ; `PilotageCreneau.tsx` (`PoserUnePause`) | oui pour la **règle d'offre** (`peutPoserUnePause`, 6 oracles) ; le formulaire se vérifie à l'œil |
| CA état de tour lisible | `frontend/src/features/suivi-deroule/PilotageCreneau.tsx` (`EtatDuTour`), alimenté par `useSuiviDeroule` (même clé de requête que le schéma, donc aucun appel de plus) | oui — **aucune** clôture persistée n'a été ajoutée : ADR-0090 §5 (dérivation à la lecture) est inchangé |
| CA refus circonstancié | `frontend/src/features/suisse/presentation.ts` (`ceQuiManque`) ; `SaisieSuisse.tsx` (`CeQuiManqueEncore`) | oui — `frontend/src/features/suisse/presentation.test.ts`, dont la distinction *pas saisie* / *pas validée* et le cas désynchronisé |
| CA pause visible du public et de la salle | `frontend/src/features/en-cours/VueEnCours.tsx` (bandeau `encours__pause`) + `en-cours.css` ; l'écran de salle **compose** `VueEnCours` (`frontend/src/features/salle/EcranSalle.tsx`) | partiellement — le bandeau est vérifié à l'œil ; il est rendu par le **même** composant sur les deux surfaces, ce qui est ce qui garantit qu'elles ne divergent pas |

⚠️ **Ce que cet ADR ne porte pas.** La **qualification** reste hors du mécanisme : elle n'annonce
qu'un tour, donc aucune pause ne peut s'y poser. La rendre divisible en tours demande de résoudre sa
population réelle ([ADR-0082](0082-plusieurs-qualifications-dans-un-meme-deroule.md)), le plan de
cibles et les forfaits — c'est `E05US035`, sortie du périmètre au cadrage du 20/08/2026. Le refus est
**explicite** des deux côtés (`TYPES_DEROULES` / `TYPES_ARRETABLES`), donc l'organisateur ne peut pas
poser un réglage qui ne partirait jamais.
