# E01 — Configuration du tournoi — User Stories

> EPIC : [EPIC-01](../epics/EPIC-01-configuration-tournoi.md) · Réfs : CDC fonctionnel M1, ADR-0006 (vocabulaire).

---

### E01US001 — Créer un tournoi
*En tant qu'*administrateur, *je veux* créer un tournoi (nom, date, lieu, type officiel/non), *afin de* disposer d'un contexte pour inscrire et placer.
- **CA** : tournoi persisté et listable ; champs obligatoires validés ; type officiel/non stocké.
- **Notes** : agrégat `Tournoi` (domaine) ; écriture via la file ; DTO distinct.
- **Dépend de** : E00US009 · **Jalon** : J1

### E01US002 — Éditer / lister les tournois
*En tant qu'*administrateur, *je veux* retrouver et modifier mes tournois, *afin de* les gérer dans le temps.
- **CA** : liste des tournois ; édition des métadonnées ; un tournoi en cours n'est pas supprimable sans confirmation.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US003 — Gérer les catégories (CRUD)
*En tant qu'*administrateur, *je veux* définir les catégories du tournoi, *afin de* classer et cloisonner les archers.
- **CA** : créer/éditer/supprimer une catégorie (libellé, arme, âge, sexe) ; rattachable à un tournoi.
- **Notes** : entité `Categorie` (FR, ADR-0006).
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US004 — Pré-charger les catégories FFTA salle
*En tant qu'*administrateur, *je veux* partir de catégories FFTA prédéfinies modifiables, *afin de* ne pas tout ressaisir.
- **CA** : un jeu de catégories FFTA salle est proposé à la création ; chaque catégorie reste modifiable/supprimable.
- **Notes** : jeu de référence à obtenir (question ouverte EPIC-01).
- **Dépend de** : E01US003 · **Jalon** : J1

### E01US005 — Gérer les blasons (taille/fraction + capacité)
*En tant qu'*administrateur, *je veux* définir les blasons, *afin de* modéliser l'occupation d'une cible.
- **CA** : blason = `taille` (fraction de place) + `capacite` + `nom` ; CRUD.
- **Notes** : réutilise/étend le prototype `Blason`.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US006 — Associer catégorie ↔ blason
*En tant qu'*administrateur, *je veux* lier une catégorie à un blason, *afin que* le placement en tienne compte (officiel).
- **CA** : chaque catégorie peut porter un blason par défaut ; utilisé par le placement (EPIC-03).
- **Notes** : le blason de la catégorie est un **défaut**, qu'une **phase pourra surcharger** (« finales sur triples verticaux », FFTA A.7.6/A.7.7) — la surcharge relève d'EPIC-05, cf. EF-1.4.
- **Dépend de** : E01US003, E01US005 · **Jalon** : J1

### E01US007 — Définir un gabarit de salle
*En tant qu'*administrateur, *je veux* décrire le plan de salle, *afin de* cadrer le placement.
- **CA** : gabarit = nb de cibles + capacité (1/2/4) + positions (A/B/C/D) ; persisté.
- **Notes** : entité `GabaritSalle` ; base du plan de cibles.
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US008 — Réutiliser / ajuster un gabarit
*En tant qu'*administrateur, *je veux* réutiliser un gabarit existant et l'ajuster, *afin de* gagner du temps d'un tournoi à l'autre.
- **CA** : appliquer un gabarit enregistré à un tournoi ; ajuster (nb cibles, capacités) sans altérer l'original.
- **Dépend de** : E01US007 · **Jalon** : J1

### E01US009 — Définir un barème de qualification
*En tant qu'*administrateur, *je veux* paramétrer le barème de qualif, *afin de* calculer les scores.
- **CA** : **deux presets** sélectionnables — *FFTA officiel* (60 flèches, 20 volées de 3, cumul) et *format club* (5 volées de 3, cumul) ; valeurs modifiables dans les deux cas.
- **Notes** : politique `scoring` (ADR-0004) ; MVP = qualif seule. Les 15 flèches du CDC v0.2 sont le **format club**, pas la FFTA — cf. [référentiel §10.1](../docs/referentiel-ffta.md).
- **Dépend de** : E01US001 · **Jalon** : J1

### E01US010 — Définir le tarif par départ
*En tant qu'*administrateur, *je veux* fixer le tarif d'un départ, *afin d'*alimenter le suivi de paiement.
- **CA** : ~~tarif paramétrable **par tournoi**~~ → le tarif est porté **par chaque départ** (E02US004) ; utilisé par le calcul du montant dû (E08US001).
- **Dépend de** : E01US001 · **Jalon** : J1
  > **Livrée puis révisée le 16/07/2026** ([ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md)). Cette US avait posé `tournoi.tarif_depart_centimes` — un tarif **unique au tournoi** — faute d'entité `Depart` à ce moment (les départs n'étaient pas modélisés). E02US004 modélise les départs comme des **créneaux du tournoi** ; le tarif **migre** sur le départ (obligatoire par créneau, prix possiblement différents) et le champ du tournoi est **retiré** (migration `0016`). Ce qui reste vrai d'E01US010 : la règle **centimes entiers** (ADR-0012) et le fait qu'un tarif de départ alimente la facturation (E08US001).

### E01US011 — Presets de barèmes multi-phases
*En tant qu'*administrateur, *je veux* des presets pour chaque type de phase, *afin de* couvrir les formats riches.
- **CA** : **deux jeux** de presets (*FFTA officiel* / *format club*), modifiables et réutilisables — barrage (1 flèche), sets (FFTA : 5 sets / 6 pts ; club : 4 pts), finales, Big Shoot Off ; un barème est **surchargeable par arme** (poulies au cumul, sans sets — FFTA A.7.5.2).
- **Notes** : alimente les politiques `scoring` du moteur (EPIC-05) ; cf. EF-3.4 et `config.policies.scoring_par_arme` du [modèle de données](../docs/modele-de-donnees.md). ⚠️ Le **Big Shoot Off n'a pas de règle connue** (Q9 du CDC fonctionnel) — cette US est **bloquée** sur ce point tant que le club ne l'a pas fournie.
- **Dépend de** : E01US009 · **Jalon** : J4

### E01US012 — Gérer plusieurs gabarits
*En tant qu'*administrateur, *je veux* une bibliothèque de gabarits, *afin de* gérer plusieurs salles.
- **CA** : créer/nommer/lister plusieurs gabarits ; en choisir un par tournoi.
- **Dépend de** : E01US007 · **Jalon** : J4

---

> **US de correction — cadrage FFTA du 14/07/2026.** Les deux US ci-dessous corrigent des modèles
> déjà mergés, à la suite de la confrontation du CDC au [référentiel FFTA](../docs/referentiel-ffta.md).
> Elles sont **prioritaires sur EPIC-02+** : plus on inscrit d'archers et on saisit de scores, plus
> la migration coûte.

### E01US013 — Catégorie : éligibilité sur plusieurs tranches d'âge
*En tant qu'*administrateur, *je veux* qu'une catégorie puisse couvrir **plusieurs** tranches d'âge, *afin de* représenter les regroupements FFTA (arc nu « U18 » = U15 + U18 ; « Scratch » = U21 + S1 + S2 + S3).
- **Contexte** : E01US003 modélise l'âge par un `tranche_age` scalaire, et E01US004 encode le regroupement dans un **libellé** (`_AGES_NU = ("U18", "Scratch")`). Conséquence : `tranche_age = "U18"` signifie « U18 seulement » en classique et « U15 ou U18 » en arc nu — même valeur, deux sens — et « Scratch » n'est pas une tranche d'âge. Un archer n'est pas rattachable de façon fiable à sa catégorie.
- **CA** : `Categorie.ages` remplace `tranche_age` et accepte une ou plusieurs tranches ; le pré-réglage FFTA (E01US004) encode les regroupements du [référentiel §3](../docs/referentiel-ffta.md) en éligibilités et non en libellés ; « Scratch » disparaît des tranches d'âge et devient un **libellé** de catégorie ; migration des catégories existantes ; API + front alignés ; un archer donné (arme, âge, sexe) n'est éligible qu'à **une seule** catégorie du tournoi.
- **Notes** : CDC fonctionnel EF-1.2 ; [modèle de données](../docs/modele-de-donnees.md) `CATEGORIE.ages` (JSON). Corrige E01US003 + E01US004. Touche `backend/domain/categorie.py`, `backend/application/referentiel_ffta.py`, migration, `frontend/src/features/categories/`.
- **Dépend de** : E01US003, E01US004 · **Jalon** : J1

### E01US014 — Blason : valeurs de score admises
*En tant que* scoreur, *je veux* que le pavé de saisie ne propose que les valeurs **réellement tirables sur mon blason**, *afin de* ne pas saisir un score impossible.
- **Contexte** : E01US005 modélise le blason par `taille` + `capacite` seulement. Or un **triple 40 n'a pas les zones 5 → 1** (minimum = 6, [référentiel §4.4](../docs/referentiel-ffta.md)) et le « 10 intérieur » des poulies diffère du 10 classique (§4.3). Sans cette donnée, la saisie (EPIC-04) ne peut pas construire son pavé.
- **CA** : `Blason.zones` porte les valeurs admises (ex. `["10","9","8","7","6","M"]`) ; valeur par défaut cohérente à la création ; modifiable comme le reste du blason (RG-8) ; migration des blasons existants ; exposé par l'API et éditable au front.
- **Notes** : CDC fonctionnel EF-1.3b, consommé par EF-5.2. Corrige E01US005. **Ne traite pas** la hauteur du blason — c'est [DETTE-002](../docs/dette.md), résorbée en EPIC-03.
- **Dépend de** : E01US005 · **Jalon** : J1

---

> **US de cadrage UX — entretien du 14/07/2026.** Issues de
> [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) (registre des décisions §11).

### E01US015 — Définir le grain de validation d'une phase
*En tant qu'*administrateur, *je veux* choisir **quand le scoreur valide** pour chaque phase, *afin d'*adapter la charge de mes scoreurs au format de l'épreuve.
- **CA** : chaque phase porte son **grain de validation** dans **`config.validation`** — *fin de série* · *fin de duel* · *toutes les N volées* ; presets cohérents par type de phase (qualification → **fin de série** ; élimination directe → **fin de duel**) ; **modifiable** ; le grain est **lu par la validation** (E04US007) et **affiché sur la tablette de cible** (E04US002) ; réglé **une fois à la configuration**, jamais le jour J.
- **Notes** : `D-11`. **S'appuie sur [ADR-0011](../docs/adr/0011-phase-qualification-anticipee.md)** qui a introduit `Phase` avec une `config` JSON ne portant que `scoring`, en précisant que « les autres politiques y viendront **sans changement de schéma** » → **`config.validation` à côté de `config.scoring`, zéro migration**. Motif chiffré : à 3 scoreurs pour ~30 cibles, valider **toutes les 2 volées = ~180 passages par départ** (intenable, une toutes les 40 s) contre **~60 en fin de série** (~20 par scoreur). Cf. E04US007 pour le fondement réglementaire (la validation est un acte **de fin**).
- **Dépend de** : E01US009 · **Jalon** : J1

### E01US016 — Définir l'identité visuelle du tournoi
*En tant qu'*organisateur, *je veux* déposer **le logo et les couleurs de mon tournoi**, *afin que* l'écran de salle et le téléphone des archers affichent **ma compétition**, pas un logiciel.
- **Contexte** : le club a **deux marques** — *Les Archers de Kervignac* (permanent) et l'événement, ex. *Challenge des Champions* (par édition, `docs/elements_design/`). `DV-01`.
- **CA** : l'organisateur fournit **un logo** (SVG/PNG) et **deux couleurs d'accent** — **rien d'autre** ; le système **dérive** surfaces, bordures, états et variantes de texte, en **thème sombre et clair** ; **contrôle de contraste à la saisie**, en **alerte chiffrée et non bloquante** (`P-4`) : la couleur exacte est **acceptée** pour les aplats, une **variante AA est dérivée** pour le texte et les bordures (`DV-05`) ; **aperçu sur les surfaces réelles** (écran de salle + téléphone), pas un nuancier ; **les couleurs sémantiques ne sont jamais personnalisables** (alerte/succès/info appartiennent au produit, `DV-03`) ; **défaut = identité du club** si rien n'est fourni ; s'applique **au public et à l'écran de salle uniquement** — **jamais à l'admin ni à la saisie** (`D-27`) ; **modifiable à tout moment**, y compris tournoi en cours (`P-3`).
- **Notes** : `D-27`, `D-28` · [CDC design §3.6](../cahier-des-charges-design.md) (`DV-06`). **Absent des 117 US** : le CDC design v0.1 le portait en question ouverte (`Q-D8`), fermée le 14/07/2026. **La dérivation est du code, pas une décision de designer** : teinte et saturation conservées, clarté ajustée jusqu'au seuil AA — le calcul est reproductible. Cas d'école **vérifié sur la charte réelle** : le rouge club `#B71918` donne **2,55:1** sur le fond anthracite `#1D1D1B` de sa propre charte (échec texte **et** UI) → aplat + variantes `#CC1C1B` (bordure, 3,01:1) et `#E84E4D` (texte, 4,52:1). **Pourquoi l'admin est exclu** : le jour J, un bénévole n'a pas le temps de réapprendre des repères visuels. **Ouvertes** : `Q-UX10` (qui produit le logo — un SVG de graphiste ou un JPEG de téléphone à recadrer ?), `Q-UX11` (une archive fige-t-elle son identité ?).
- **Dépend de** : E01US001 · **Jalon** : J3 *(avec l'écran de salle — E07US004 ; l'identité n'a pas de surface avant lui)*
