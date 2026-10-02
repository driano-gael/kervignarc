# E13 — Épreuves par équipes — User Stories

> EPIC : [EPIC-13](../epics/EPIC-13-equipes.md) · Réfs : [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md), référentiel FFTA §6.3/§7, CDC technique §5.
> **Créé le 18/07/2026** — décision d'entrer les équipes dans le MVP (renverse le « hors périmètre » du cadrage du 14/07, ADR-0028).

---

### E13US001 — Abstraction participant (le match oppose des participants)
*En tant que* développeur, *je veux* que le moteur oppose des **participants** (archer **ou** équipe) et non des archers en dur, *afin d'*ajouter les équipes sans refondre le moteur de duels.
- **CA** : le modèle de duel porte `MATCH.participant_A/B` ; un `Participant` est **soit** un archer individuel **soit** une équipe ; un tournoi individuel est le cas où chaque participant **est** un archer (aucune complication du cas simple) ; peuplement et routage (E05) opèrent sur des participants.
- **Notes** : réalise la porte ouverte du cadrage (CDC §10). **Doit précéder E05US005** (l'arbre d'élimination) — sinon le moteur se fige sur des archers ([ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md), risque). Tests domaine depuis ce CA (règle 9).
- **Dépend de** : E05US001 · **Jalon** : J2 *(avant E05US005)*

### E13US002 — Composer les équipes d'un tournoi
*En tant qu'*organisateur, *je veux* créer des équipes et y affecter des archers, *afin d'*inscrire des équipes à une épreuve.
- **CA** :
  1. Entité `Equipe` du tournoi : **nom** (non vide, unique dans le tournoi), **type** (`standard` | `mixte`), **effectif attendu** (entier de 1 à 99, prérempli selon le type : **3** en standard, **2** en mixte — FFTA §6.4/§7 — et modifiable ; une modification qui ne change pas le type **garde** l'effectif choisi), **membres** (archers). CRUD : créer, renommer / changer type et effectif, supprimer, ajouter et retirer un membre. **Seul l'effectif est configurable** : les règles d'arme commune et de mixité du CA 4 sont celles de la FFTA, fixes (arbitrage du 01/10/2026, en revue).
  2. Un membre est un archer **du même tournoi** que l'équipe ; sinon refus.
  3. Un archer appartient à **au plus une équipe par type** dans le tournoi (une standard **et** une mixte au plus) : une seconde affectation du même type est **refusée** (conflit).
  4. La composition se **compose membre par membre** : une équipe non conforme **s'enregistre**, elle n'est **pas bloquée**. Chaque équipe expose sa **conformité** — conforme, ou la liste des écarts :
     - **effectif** différent de l'effectif attendu (trop peu / trop de membres) ;
     - **armes différentes** entre membres (l'arme est lue sur la catégorie) ;
     - en **mixte** : il manque un homme **ou** une femme ; en **standard** : membres de **sexes différents** (FFTA §6.4, épreuves par sexe) ;
     - **non vérifiable** quand une catégorie de membre n'a pas d'arme, ou pas de sexe (sexe absent ou « mixte ») — le critère concerné est signalé « non vérifiable », jamais deviné.
  5. Le **sexe** et l'**arme** d'un archer sont ceux de **sa catégorie** — l'archer n'en porte pas (arbitrage du 01/10/2026). Changer la catégorie d'un membre change la conformité de son équipe.
  6. **« Engagé » s'élargit** : un archer membre d'une équipe est engagé. Sa suppression est **signalée** en nommant l'équipe ; confirmée, elle le **retire** de l'équipe (l'équipe subsiste). La **désinscription** d'un départ, elle, ne touche pas aux équipes.
  7. Supprimer un tournoi supprime ses équipes et leurs membres (cascade explicite d'E01US026) ; supprimer une équipe ne touche à aucun archer.
  8. Écran d'administration **« Équipes »** du tournoi : liste des équipes avec type, membres et conformité (écarts lisibles en clair), création, édition, suppression, ajout / retrait de membre.
- **Notes** : entité enfant du tournoi (comme `Depart`, `Scoreur`). Arbitrages du **01/10/2026** au cadrage : sexe **lu sur la catégorie** (pas de champ neuf sur l'archer) ; composition **signalée, pas bloquée** — le refus d'une équipe non conforme viendra à l'**engagement dans une phase** (E13US004) ; **une équipe par type** ; périmètre **backend + écran**. Choix technique de l'auteur : l'effectif « configurable » est porté **par l'équipe** plutôt que par un réglage du tournoi (aucun écran de réglage neuf). **Arbitrage de revue (01/10/2026)** : le CA d'origine disait « la contrainte de composition (nombre d'archers, mixité) est configurable » ; le commanditaire a validé que **seul l'effectif** l'est — les règles d'arme et de mixité restent FFTA, et comme elles sont signalées sans bloquer, une équipe hors règle (challenge interne) s'enregistre en affichant ses écarts. La borne 99 est une garde technique (un entier hors 64 bits faisait un 500), pas une règle FFTA. Cas limite tranché par l'auteur, hors CA d'origine : à la **fusion de deux archers**, les appartenances de l'absorbé passent au survivant ; si le survivant est déjà dans une **autre** équipe du même type, la fusion est **refusée** (rien ne se perd en silence). ~~Élargit DETTE-001~~ — périmé : `DETTE-001` est soldée par `E01US026` (cascade explicite), les tables d'équipe **entrent** dans cette cascade (CA 7). Réf. FFTA corrigée : la composition est au **§6.4**, pas §6.3. Tests domaine (règle de composition) depuis ce CA.
- **Dépend de** : E13US001, E02US002 · **Jalon** : J2

### E13US003 — Scoring d'équipe (barème et barrage)
*En tant que* scoreur, *je veux* saisir et cumuler le score d'une **équipe** (volées alternées, cumul des membres), *afin de* départager des équipes en duel.
- **CA** :
  1. Le score d'un match d'équipe est porté par le **barème de duel de la phase** (`BaremeDuel`, réglé par phase et par arme — [ADR-0117](../docs/adr/0117-le-bareme-de-duel-est-un-reglage-d-etape-verrouille-au-premier-tir.md)), sans **aucune branche `if équipe`** dans le moteur : la volée d'un camp est le **cumul** des flèches de ses membres, quel que soit l'archer qui les a tirées.
  2. Le barème porte un **nombre de flèches de barrage** par camp (entier ≥ 1). Un barème qui n'en dit rien — tous ceux enregistrés avant cette US — en tire **1** : rien ne change pour l'individuel.
  3. Le barrage d'un duel se saisit avec **exactement** ce nombre de flèches par camp, sinon refus. Le camp au **plus haut total** gagne ; à totaux égaux, la **désignation** (plus près du centre, §8.2) tranche, comme aujourd'hui. Le point de set (§7) ou la victoire au cumul qui en découle sont inchangés.
  4. Deux **presets FFTA** rejoignent ceux du réglage de barème (§6.4, §7, §8.2), et posent comme eux un défaut plus une surcharge par arme à poulies connue : **équipe** = sets, **4 manches de 6 flèches**, premier à **5**, barrage **3** — poulies : cumul, 4 volées de 6, barrage 3 ; **équipe mixte** = sets, 4 manches de **4**, premier à 5, barrage **2** — poulies : cumul, 4 volées de 4, barrage 2.
  5. Le nombre de flèches de barrage se **règle** dans le formulaire du barème de duel, comme les autres champs, et le barrage d'un duel se saisit avec ce nombre de flèches.
  6. Cas de référence (oracle, §7) : un match d'équipe en sets à **4-4** après quatre manches va au barrage ; 3 flèches par camp, le plus haut total gagne et le score final est **5-4**.
- **Notes** : **Arbitrage du 02/10/2026 au cadrage** — le CA d'origine (« une implémentation de la politique `scoring`, résolue par le couple (phase, type de participant) ») recopiait [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md) §3, écrit avant que le score des duels ne soit livré par `BaremeDuel` (ADR-0049, ADR-0117). La famille `scoring` n'a **aucun appelant de production** (`DETTE-028`) et une phase d'équipes est déjà une phase distincte : la dimension « type de participant » n'aurait rien à départager. Retenu : **barème + barrage**, ADR-0028 §3 amendé. Les « volées alternées » sont un **ordre de tir** (feux, §9), sans effet sur le score. Interprétation de l'auteur : le barrage **mixte** à **2 flèches** (1 par archer) étend la règle « 1 par archer » de §8.2, qui ne cite que l'équipe à trois. La **saisie** d'une volée d'équipe et l'engagement d'une équipe dans une phase restent à `E13US004`.
- **Dépend de** : E13US001, E05US003 · **Jalon** : J2

### E13US004 — Placement, saisie & classement par équipe
*En tant qu'*organisateur, *je veux* placer, saisir et classer des **équipes**, *afin de* dérouler une épreuve par équipes de bout en bout.
- **CA** : le placement pose une **équipe** (ses archers sur des cibles voisines) ; la saisie enregistre une **volée d'équipe** ; le classement produit des **rangs d'équipe** ; chaque brique traite un participant qui n'est pas un individu. Une équipe dont la composition n'est **pas conforme** (`ecarts_de_composition` non vide, E13US002) est **refusée** à l'engagement dans une phase, en **nommant ses écarts** — c'est le refus qu'E13US002 a renvoyé ici en ne faisant que signaler.
- **Notes** : les briques restent dans EPIC-03/04/06 ; EPIC-13 les **coordonne** pour le cas équipe. Découpage plus fin possible à la planification (par brique) si l'US est trop large pour une branche.
- **Dépend de** : E13US001, E13US002, E13US003 · **Jalon** : J2 → J3
