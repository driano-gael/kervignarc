# ADR-0120 — Une phase oppose des équipes par un réglage d'étape ; l'engagement est dérivé

- **Statut** : Accepté
- **Date** : 2026-10-03
- **US** : E13US004
- **Décideurs** : Organisateur / Architecte
- **Prolonge** : [ADR-0028](0028-epreuves-par-equipes-participant.md) point 4 (placement, saisie et
  classement clés sur le participant), pour le seul **tableau à élimination directe**.

## Contexte

ADR-0028 a fait opposer des `Participant` au moteur de duels, pour que les équipes y entrent sans
refonte. E13US002 a livré l'entité `Equipe` (composition signalée, jamais bloquée) et E13US003 le
barème d'équipe. Mais **aucun module de production ne construisait `Participant.equipe(...)`** : une
équipe se composait sans pouvoir se jouer.

Trois faits du code ont orienté la décision :

1. **Rien n'« engage » un participant dans une phase.** Un tableau est **recalculé à chaque
   lecture** : classement du départ → prélèvement → ensemencement → rejeu des duels validés
   (`ServiceSaisieDuels._decor`). Aucune table ne dit qui joue.
2. Une phase reçoit ses réglages **de son étape** (ADR-0076), sérialisés dans le JSON `config` de
   l'étape et du format — barème de duel compris (ADR-0117).
3. Le tir persiste déjà le **genre** de chaque camp (`haut_genre`, `bas_genre`) : un duel d'équipe se
   relit tel quel.

## Décision

1. **« Par équipes » est un réglage d'étape** : `EtapeDeroule.equipes: TypeEquipe | None`, recopié
   sur `Phase.equipes` à l'instanciation et porté par le format de bibliothèque. `None` = individuel,
   le comportement d'avant. Seule l'**élimination directe** l'accepte dans cette tranche ; tout
   autre type le refuse (`EquipesNonPrisesEnCharge`). Comme le barème, le réglage est **verrouillé
   au premier tir** de l'étape (ADR-0117 §5).
2. **L'engagement est une dérivation, pas un geste.** À chaque reconstruction, `engager_les_equipes`
   (domaine pur) range les équipes du type : sont engagées celles qui sont conformes et dont tous
   les membres sont en lice au classement du départ ; les autres sont **écartées avec leurs
   motifs**, jamais en silence. C'est la forme que prend « refusée à l'engagement » quand
   l'engagement n'existe pas comme acte : l'équipe n'entre pas, et l'écran dit pourquoi.
3. **Rang d'entrée = somme des qualifications des membres**, départagée par la somme des 10 puis des
   9, puis par l'ordre de création (`DETTE-121`). Le tableau d'équipes s'ensemence ensuite par la **même**
   politique de seeding que l'individuel : seule la liste des participants change.
4. **Le barème par défaut d'un duel d'équipes est le preset FFTA du type**, via une seconde méthode
   du résolveur injecté (`bareme_equipe_pour(type, arme)`), et non le barème individuel.
5. **Le moteur ne change pas.** `Tableau`, `Duel` et la persistance du tir traitent déjà des
   participants opaques. Ce sont les couches hautes qui résolvent une équipe en membres : arme et
   blason (lus sur la catégorie de ses membres, homogène puisqu'elle est conforme), noms, et
   archers à poser sur les cibles. ⚠️ **L'arme est homogène parce que l'équipe est conforme ; le
   blason ne l'était pas** (la conformité d'E13US002 ne lisait que l'arme et le sexe) : la revue
   l'a relevé, et l'écart « blasons différents » écarte désormais une telle équipe.
   **Frontière** : `Camp = Duelliste | DuellisteEquipe` n'apparaît que sur la surface du tableau ;
   poules, suisse et colline gardent `Duelliste`. L'API aplatit un camp d'équipe (nom d'équipe,
   prénom vide, `equipe_id`, `archer_id` nul) ; routage et simulation l'écartent explicitement.
6. **Une phase d'équipes est un îlot** dans cette tranche : elle ne prélève pas par rangs et
   n'alimente aucune phase aval, ce que le déroulé signale en anomalie (`DETTE-120`). Le classement
   d'un tableau d'équipes est indexé par équipe, donc le prélever comme un classement d'archers
   produirait une population fausse mais bien formée.

7. **La composition se fige au premier tir, par départ** (arbitrages de revue du 03/10/2026).
   L'engagement étant recalculé, supprimer ou recomposer une équipe dont un membre tire un départ
   où le tableau de ce type a un tir réécrirait l'ensemencement : `ServiceEquipes` le refuse (409,
   `VerrouCompositionEquipes`). Le gel ne couvre **que** cet écran : supprimer ou fusionner un
   archer, modifier une catégorie, déclarer un forfait de qualification changent encore
   l'engagement, comme en individuel (`DETTE-123`) — le remède est de figer l'engagement.

## Alternatives écartées

- **Une table d'engagement persistée** (« l'équipe X est engagée dans la phase Y »). Elle donnerait
  au refus la forme d'un geste, mais introduirait un second chemin d'entrée dans un tableau à côté
  de l'ensemencement dérivé, donc deux vérités qui peuvent diverger. Écartée tant qu'aucun besoin
  (engagement manuel, inscription payante par équipe) ne l'exige.
- **Bloquer la phase** tant qu'une équipe du type est non conforme. Écartée par le commanditaire au
  cadrage : une équipe incomplète le jour J bloquerait tout le monde.
- **Refuser l'engagement si le barème n'est pas réglé.** Écartée au cadrage : le résolveur
  individuel applique déjà un preset FFTA par défaut, et l'équipe a le sien.
- **Un nouveau `TypePhase` « élimination par équipes »**. Il dupliquerait le contrat de phase
  (ADR-0083) pour une différence qui n'est pas de format mais de participants : règle 2, un format
  est de la configuration.

## Conséquences

- ✅ Un tableau d'équipes se joue avec les écrans existants (plan de duels, saisie, pilotage).
- ✅ Corriger une composition fait entrer l'équipe tant qu'aucun tir n'a eu lieu ; après, la garde
  de désynchronisation d'ADR-0049 §4 masque le tir plutôt que de le prêter à d'autres camps.
- ⚠️ Les presets équipe vivent **deux fois** — au front (formulaire) et au serveur (défaut) : la
  recopie élargit `DETTE-119`.
- ⚠️ Restent hors tranche, regroupés dans `E13US005` : prélèvement top N et chaînage (`DETTE-120`),
  forfait d'équipe (les forfaits déclarés restent individuels et n'atteignent pas un tableau
  d'équipes), affectations publiques des membres, palmarès, autres formats, départage au tir du rang
  d'entrée (`DETTE-121`).

## Porté dans le code par

| Point | Module |
|---|---|
| 1 — réglage d'étape | `domain/deroule_etape.py`, `domain/phase.py` (garde), `domain/format_tournoi.py`, `infrastructure/db/repositories/moteur.py`, `application/phases.py` (verrou), `api/v1/phases.py`, `api/v1/formats.py`, `frontend/src/shared/phases/` |
| 2, 3 — engagement et rang d'entrée | `domain/engagement_equipes.py`, `domain/equipe.py` (écart « blasons différents »), `application/equipes.py` (`a_engager`, `jouee`), `application/saisie_duels.py` (`_decor`, `_equipes_sans_tableau`) |
| 4 — barème par défaut | `domain/duel.py` (`ResolveurBaremeDuelFfta.bareme_equipe_pour`), `application/saisie_duels.py` (`_bareme_du`) |
| 5 — résolution en couche haute | `application/saisie_duels.py`, `application/placement_duels.py`, `application/pilotage_tour.py`, `domain/placement.py` (adjacence par groupe de duel) ; frontière `Camp` : `api/v1/saisie_duels.py` et `api/v1/tableaux.py` (aplatissement), `application/routage.py` et `application/pilotage_simulation.py` (camp d'équipe écarté) |
| 6 — îlot | `domain/phase.py` (`_anomalies_ilot_d_equipes`), `application/saisie_duels.py` (`_equipes_engagees`, `_classement_produit`) |
| 7 — composition figée | `application/equipes.py` (`_refuser_si_en_jeu`), `application/verrou_bareme.py` (`VerrouCompositionEquipes`, `VerrouBaremeDuel.etape_tiree_dans`) |
