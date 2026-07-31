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
- **Notes** : ⚠️ **livré** avec le cycle à **trois** statuts (`brouillon → en_cours → terminé`). Ce cycle est **enrichi à sept statuts** par **E01US017** ([ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md)) : la transition directe `brouillon → en_cours` y devient `brouillon → prêt → en_cours`. **Ne pas dériver de nouveau test de cycle de vie de ce CA-ci** — la source est E01US017 / ADR-0026.
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
  > **Évolution — 21/07/2026** ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)) : le tarif porté par le départ, sommé sur les départs d'un archer, n'est plus « la » règle mais la **stratégie de tarification par défaut** (et la seule codée). Le montant dû devient à terme le résultat d'une **politique injectable** choisie par tournoi (sujet archer|club, dégressif). Cf. E01US020/E01US021 ci-dessous — non implémentées.
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

> **US d'évolution — tarification riche.** Nées du cadrage d'E08US002 le 21/07/2026
> ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)). L'organisateur a demandé que
> le calcul du montant dû **reste ouvert** : facturation par archer *ou* par club, dégressif possible.
> **Aucune n'est implémentée** : la seule stratégie codée reste « somme des tarifs des départs de
> l'archer » (E08US001). On n'implémente une de ces US **que quand un tournoi réel la demande**
> (règle 9 — pas de moteur spéculatif). **À rediscuter avec l'organisateur** avant de prendre l'une
> d'elles : ni le catalogue exact des modèles ni les formules de dégressif ne sont figés.

### E01US020 — Modèle de tarification injectable & sujet de facturation
*En tant qu'*administrateur, *je veux* choisir, à la configuration d'un tournoi, **qui** est facturé (archer ou club) et **selon quel modèle**, *afin de* couvrir les formats de tournoi où le prix ne se réduit pas à « somme des créneaux d'un archer ».
- **CA (à cadrer)** : la tarification devient une **politique injectable** (règle 2, [ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)) portée par le tournoi ; un **sujet de facturation** `archer | club` est choisi à la configuration ; le **forfait club** (montant fixe indépendant du nombre d'archers) et le **prix club = cumul des prix archers** sont deux stratégies possibles.
- **Notes** : le sujet `club` s'appuie sur le **référentiel club** ([ADR-0014](../docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md), `club_id` déjà livré), **pas** sur l'abstraction participant d'[ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md) (qui modélise l'unité de *match*, non de *facturation*) : facturer un club **ne dépend pas** des équipes/E13. Le rework est **assumé** (ADR-0041) et devra rediriger **les deux** sites qui calculent aujourd'hui le dû (`montant_du_par_archer` d'E08US001 **et** le récap paiements `recapituler` d'E08US002 — 2ᵉ occurrence de « somme des tarifs », règle 9).
- **Dépend de** : E01US010, E08US001 · **Jalon** : à planifier · **ADR** : [ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md) · **État** : définie, non implémentée

### E01US021 — Tarification dégressive
*En tant qu'*administrateur, *je veux* activer un tarif dégressif à la configuration du tournoi, *afin de* récompenser les inscriptions multiples (plusieurs départs, ou un club nombreux).
- **CA (à cadrer)** : **option cochable** à la configuration ; réduction exprimée en **pourcentage** *ou* en **montant** saisi ; appliquée **par départ** (sujet archer : le 2ᵉ départ, etc.) ou **par palier de nombre d'archers** (sujet club) — la forme exacte de la formule reste **à préciser avec l'organisateur**.
- **Notes** : c'est une **stratégie de tarification** de plus (E01US020), pas une branche dans le service. Suppose E01US020 posée (politique injectable + sujet de facturation).
- **Dépend de** : E01US020 · **Jalon** : à planifier · **ADR** : [ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md) · **État** : définie, non implémentée

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
  > **Périmètre de l'invariant d'éligibilité — tranché le 16/07/2026 ([ADR-0019](../docs/adr/0019-categorie-eligibilite-multi-tranches.md)).** L'invariant « un archer (arme, âge, sexe) n'est éligible qu'à **une seule** catégorie » est livré ici comme **propriété testée du preset FFTA** (à (arme, sexe) fixés, les tranches des catégories sont disjointes), **pas** comme un contrôle à l'exécution : l'agrégat `Archer` ne porte encore ni arme, ni âge, ni sexe (juste `categorie_id`), la vérification runtime est donc **reportée** à l'US qui l'en dotera. `ages` est un **enum fermé** des huit tranches (`TrancheAge`) ; les valeurs libres d'avant (« senior »…) ne sont plus admises et une catégorie migrée dont l'ancien `tranche_age` n'était pas une tranche FFTA perd sa contrainte d'âge (`ages = []`).
- **Dépend de** : E01US003, E01US004 · **Jalon** : J1

### E01US014 — Blason : valeurs de score admises
*En tant que* scoreur, *je veux* que le pavé de saisie ne propose que les valeurs **réellement tirables sur mon blason**, *afin de* ne pas saisir un score impossible.
- **Contexte** : E01US005 modélise le blason par `taille` + `capacite` seulement. Or un **triple 40 n'a pas les zones 5 → 1** (minimum = 6, [référentiel §4.4](../docs/referentiel-ffta.md)) et le « 10 intérieur » des poulies diffère du 10 classique (§4.3). Sans cette donnée, la saisie (EPIC-04) ne peut pas construire son pavé.
- **CA** : `Blason.zones` porte les valeurs admises (ex. `["10","9","8","7","6","M"]`) ; valeur par défaut à la création = le **jeu complet d'un blason simple** (`10 → 1` + `M`) ; modifiable comme le reste du blason (RG-8) ; migration des blasons existants **backfillée avec ce même défaut** ; exposé par l'API et éditable au front.
- **Notes** : CDC fonctionnel EF-1.3b, consommé par EF-5.2. Corrige E01US005. **Ne traite pas** la hauteur du blason — c'est [DETTE-002](../docs/dette.md), résorbée en EPIC-03. Vocabulaire fermé aux zones du [référentiel §4.2](../docs/referentiel-ffta.md) (`10`→`1`, `M`), porté par l'énuméré `ZoneScore` et validé **à la frontière** (400), comme `TrancheAge` — [ADR-0019](../docs/adr/0019-categorie-eligibilite-multi-tranches.md). Les règles **structurelles** restent au domaine (422) : `M` **toujours** admis (un manqué est possible sur tout blason), au moins une zone marquante, **pas de doublon**, et les zones sont **normalisées dans l'ordre canonique** (10 → 1 puis M) — l'ordre de saisie ne portant aucune information, c'est un contrat d'API observable qui pilotera l'ordre du pavé d'EPIC-04. Un jeu **non contigu** est admis : la contiguïté ne sert aucun consommateur, et RG-8 interdit d'imposer le règlement. L'**édition est un remplacement complet** : `zones` est obligatoire au PUT, comme le nom, la taille et la capacité — en faire le seul champ partiel d'un PUT total tendrait un piège de read-modify-write au prochain client (import, script) construisant son corps depuis un modèle incomplet. À la **création** seule, `zones` omises = défaut. La **mouche (X)** n'est **pas** une zone : c'est le centre du 10 (§4.3 la donne comme un diamètre), aucune valeur de score distincte — si le départage FFTA au nombre de X est retenu, il relèvera d'EPIC-06.
- **Dépend de** : E01US005 · **Jalon** : J1 · **ADR** : [ADR-0020](../docs/adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md) · **révisé par** [ADR-0027](../docs/adr/0027-vocabulaire-de-score-injectable-defaut-ffta.md) (E01US018 — le vocabulaire de score devient configurable ; l'enum fermé et `VALEUR_FLECHE_MAX` sont abandonnés)
  > **CA précisé le 17/07/2026 — arbitrage soumis à l'organisateur et tranché par lui**, en cours d'US (règle 9 : un CA ambigu se questionne **avant** d'implémenter). Le v0.1 disait « valeur par défaut **cohérente** à la création » sans dire cohérente **avec quoi** — or le domaine ne peut pas la déduire : `Blason.taille` est une **fraction de place** (`]0, 1]`), pas un diamètre, donc rien ne distingue un triple 40 d'un blason simple. Le défaut ne pouvait être qu'une **constante choisie** : un choix métier, pas un doute technique.
  > **Trois options ont été soumises**, l'organisateur a retenu la première : (1) **sur-ensemble** `10 → 1` + `M`, que l'admin restreint pour un triple — **retenue** ; (2) défaut = triple `10 → 6` + `M`, le cas le plus fréquent du club — écartée ; (3) pas de défaut, `zones` obligatoires à la création — écartée. **Contrepartie assumée** de (1) : un triple 40 laissé au défaut ouvre le pavé sur `5 → 1`, intirables — c'est-à-dire exactement ce que l'US veut empêcher. Même raison pour le **backfill** de la migration `0019` : aucune donnée en base ne permet de reconnaître un triple (déduire du `nom` serait une heuristique sur du texte libre, fausse en silence sur une donnée qui pilote la saisie) — les blasons **existants** sont donc à reprendre à la main, cf. [fiche fonctionnelle](../docs/fonctionnel/E01US014.md). Raisonnement complet et options en [ADR-0020](../docs/adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md).

---

> **US de cadrage UX — entretien du 14/07/2026.** Issues de
> [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) (registre des décisions §11).

### E01US015 — Définir le grain de validation d'une phase
*En tant qu'*administrateur, *je veux* choisir **quand le scoreur valide** pour chaque phase, *afin d'*adapter la charge de mes scoreurs au format de l'épreuve.
- **CA** : chaque phase porte son **grain de validation** dans **`config.validation`** — *fin de série* · *fin de duel* · *toutes les N volées* ; presets cohérents par type de phase (qualification → **fin de série** ; élimination directe → **fin de duel**) ; **modifiable** ; le grain est **lu par la validation** (E04US002) et **affiché sur la tablette de cible** (E04US002) ; réglé **une fois à la configuration**, jamais le jour J.
- **Notes** : `D-11`. **S'appuie sur [ADR-0011](../docs/adr/0011-phase-qualification-anticipee.md)** qui a introduit `Phase` avec une `config` JSON ne portant que `scoring`, en précisant que « les autres politiques y viendront **sans changement de schéma** » → **`config.validation` à côté de `config.scoring`, zéro migration**. Motif chiffré : à 3 scoreurs pour ~30 cibles, valider **toutes les 2 volées = ~180 passages par départ** (intenable, une toutes les 40 s) contre **~60 en fin de série** (~20 par scoreur). Cf. E04US002 pour le fondement réglementaire (la validation est un acte **de fin**).
- **Dépend de** : E01US009 · **Jalon** : J1

### E01US016 — Définir l'identité visuelle du tournoi
*En tant qu'*organisateur, *je veux* déposer **le logo et les couleurs de mon tournoi**, *afin que* l'écran de salle et le téléphone des archers affichent **ma compétition**, pas un logiciel.
- **Contexte** : le club a **deux marques** — *Les Archers de Kervignac* (permanent) et l'événement, ex. *Challenge des Champions* (par édition, `docs/elements_design/`). `DV-01`.
- **CA** : l'organisateur fournit **un logo** (SVG/PNG) et **deux couleurs d'accent** — **rien d'autre** ; le système **dérive** surfaces, bordures, états et variantes de texte, en **thème sombre et clair** ; **contrôle de contraste à la saisie**, en **alerte chiffrée et non bloquante** (`P-4`) : la couleur exacte est **acceptée** pour les aplats, une **variante AA est dérivée** pour le texte et les bordures (`DV-05`) ; **aperçu sur les surfaces réelles** (écran de salle + téléphone), pas un nuancier ; **les couleurs sémantiques ne sont jamais personnalisables** (alerte/succès/info appartiennent au produit, `DV-03`) ; **défaut = identité du club** si rien n'est fourni ; s'applique **au public et à l'écran de salle uniquement** — **jamais à l'admin ni à la saisie** (`D-27`) ; **modifiable à tout moment**, y compris tournoi en cours (`P-3`).
- **Notes** : `D-27`, `D-28` · [CDC design §3.6](../cahier-des-charges-design.md) (`DV-06`). **Absent des 117 US** : le CDC design v0.1 le portait en question ouverte (`Q-D8`), fermée le 14/07/2026. **La dérivation est du code, pas une décision de designer** : teinte et saturation conservées, clarté ajustée jusqu'au seuil AA — le calcul est reproductible. Cas d'école **vérifié sur la charte réelle** : le rouge club `#B71918` donne **2,55:1** sur le fond anthracite `#1D1D1B` de sa propre charte (échec texte **et** UI) → aplat + variantes `#CC1C1B` (bordure, 3,01:1) et `#E84E4D` (texte, 4,52:1). **Pourquoi l'admin est exclu** : le jour J, un bénévole n'a pas le temps de réapprendre des repères visuels. **Ouvertes** : `Q-UX10` (qui produit le logo — un SVG de graphiste ou un JPEG de téléphone à recadrer ?), `Q-UX11` (une archive fige-t-elle son identité ?).
- **Dépend de** : E01US001 · **Jalon** : J3 *(avec l'écran de salle — E07US004 ; l'identité n'a pas de surface avant lui)*

### E01US017 — Cycle de vie enrichi du tournoi (sept statuts)
*En tant qu'*organisateur, *je veux* un cycle de vie de tournoi qui **dise s'il est prêt**, qu'on puisse **geler** et **archiver**, et qui **garde la trace d'un abandon**, *afin de* piloter l'événement sans lancer un brouillon vide ni confondre « fini » et « clos ».
- **Contexte** : le cycle livré (E01US002) n'a que `brouillon → en_cours → terminé`, et `demarrer()` ne vérifie **rien** — un brouillon vide démarre. Remontées du 18/07/2026, tranchées en [ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md).
- **CA — statuts** : l'enum passe à **sept** — `brouillon`, `prêt`, `en_cours`, `en_pause`, `terminé`, `archivé`, `annulé` (sémantique : ADR-0026 §1, chacun porte un comportement distinct).
- **CA — transitions** (le reste refusé en `409`) : `brouillon ⇄ prêt`, `prêt → en_cours`, `en_cours ⇄ en_pause`, `en_cours → terminé`, `terminé → archivé` ; `annuler` depuis `brouillon`/`prêt`/`en_cours`/`en_pause` (**pas** depuis `terminé`) ; **pas** de retour `terminé → en_cours` (réouverture différée).
- **CA — garde « prêt à démarrer »** : `brouillon → prêt` **exige la complétude** (logique d'E12US005 appliquée à froid : catégories, blasons associés, gabarit, barème, **≥ 1 départ à horaire valide**) ; toute édition d'un tournoi `prêt` qui **invalide** la complétude le **rétrograde** en `brouillon`.
- **CA — gels** : `en_pause` (niveau **tournoi**) **refuse toute validation de score** jusqu'à `reprendre` ; distinct du `en_pause` d'une **phase** (E05, [ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)) — les deux niveaux coexistent (ADR-0026 §3).
- **CA — permissions** : suppression **interdite** dès `en_cours` (et `en_pause`) ; `archivé` = **lecture seule totale** ; `annulé` **conserve** toutes les données (trace, ≠ suppression).
- **Notes** : garde dans `ServiceTournois`, transitions **pures** dans l'agrégat `Tournoi`, **aucune horloge** (tout est déclenché par un acte admin — règle 9). L'accueil admin par statut (`D-20`) consomme les deux extrémités neuves (`prêt`, `archivé`). L'**archive effective** (export + verrou physique) reste EPIC-11 ; ici, seul le **statut** `archivé` et son verrou logique. Tests **API/service** après implémentation (câblage) ; la garde de complétude **dérive du CA d'E12US005**.
- **Dépend de** : E01US002, E12US005 · **Jalon** : J1 *(cycle de vie — socle des gardes métier ; tiré tôt car il conditionne « prêt à démarrer »)*

### E01US018 — Vocabulaire de score configurable par tournoi
*En tant qu'*organisateur, *je veux* que les valeurs de score admises ne soient pas gravées dans le logiciel mais **configurables** (défaut FFTA), *afin de* tenir un format dont le barème n'est pas celui de la FFTA salle.
- **Contexte** : E01US014 (livré) a figé les zones en énuméré **fermé** `ZoneScore` (`10 → 1` + `M`) et `domain.bareme` plafonne la flèche à `VALEUR_FLECHE_MAX = 10`. Contraire au principe « le règlement est un template » ([référentiel §10](../docs/referentiel-ffta.md)) et au moteur composable (règle 2). Tranché en [ADR-0027](../docs/adr/0027-vocabulaire-de-score-injectable-defaut-ffta.md).
- **CA — vocabulaire** : le jeu de valeurs admissibles est **porté par le tournoi** (résolu par la politique `scoring`), **pré-rempli FFTA** (`10 → 1` + `M`) à la création, **surchargeable** par l'admin.
- **CA — max dérivé** : `score_max` d'un barème = `nb_flèches_total × max(valeurs marquantes)` ; la constante `VALEUR_FLECHE_MAX` disparaît — « 10 » n'est plus qu'un défaut.
- **CA — intégrité conservée, gardien déplacé** : `M` toujours présent, ≥ 1 zone marquante, pas de doublon, ordre canonique — désormais validés au **domaine/service (422)**, non plus par un enum à la frontière (400). Contrepartie assumée (ADR-0027).
- **CA — blason = sous-ensemble** : les `zones` d'un blason restent un sous-ensemble du vocabulaire du **tournoi** ; le défaut à la création d'un blason = le vocabulaire du tournoi.
- **CA — migration** : vocabulaire par tournoi (colonne/JSON), **backfill FFTA** ; comportement observable **inchangé** pour un tournoi laissé au défaut.
- **Notes** : révise E01US014 / ADR-0020 (pt 1). Tests domaine/service **depuis ce CA** (règle 9) — la validation du vocabulaire est une règle métier. La **mouche (X)** reste hors vocabulaire.
- **Dépend de** : E01US014 · **Jalon** : J1 · **ADR** : [ADR-0027](../docs/adr/0027-vocabulaire-de-score-injectable-defaut-ffta.md)

### E01US019 — Capacité de cible non bornée (positions au-delà de D)
*En tant qu'*organisateur, *je veux* déclarer une cible de plus de 4 postes, *afin de* configurer une butte à **3 triples verticaux** comme le prévoit la FFTA.
- **Contexte** : le gabarit (E01US007, livré) **plafonne la capacité à [1,4]** (`POSITIONS = A..D` en dur, `CAPACITE_CIBLE_MAX`) alors que le modèle et le référentiel (§5, EF-4.3) la veulent **non bornée** — [DETTE-010](../docs/dette.md). Divergence code ↔ modèle ↔ référentiel constatée le 18/07/2026.
- **CA — capacité non bornée** : la capacité d'une cible est **≥ 1**, **sans plafond** (le défaut usuel reste 4) ; le gabarit accepte une capacité > 4.
- **CA — positions au-delà de D** : les positions continuent l'**alphabet** (`A, B, C, D, E, F`…) au-delà de 4.
- **CA — placement** : le moteur de placement (E03) **suit** — il pose des archers sur les positions au-delà de `D` sans supposer un maximum de 4.
- **Notes** : retire le plafond de `gabarit_salle.py` et généralise `POSITIONS`. ⚠️ **Le placement (E03US001) suppose aujourd'hui 4 positions** — vérifier `_prochaine_lettre` et la génération des lettres. Marqueur `DETTE-010` retiré à la résorption. Tests domaine (gabarit + placement) depuis ce CA.
- **Dépend de** : E01US007, E03US001 · **Jalon** : J1 → J3 *(le placement doit suivre)*

### E01US022 — Blason FFTA par défaut par catégorie + affichage du blason hérité
*En tant qu'*organisateur, *je veux* que chaque catégorie ait, par défaut, le blason prévu par la FFTA à 18 m, et que l'écran archer montre le blason **hérité de sa catégorie**, *afin de* ne pas avoir à choisir un blason par archer ni me demander « par défaut, ça vaut quoi ? ».
- **Contexte** : retour de la démo du 27/07/2026 (« je n'ai pas trouvé comment ajouter un blason sur un archer → ok vu avec la catégorie, du coup par défaut ça vaut quoi ? »). E01US006 (livré) pose déjà le **mécanisme** — le blason est un défaut **porté par la catégorie**, surchargeable par une phase — mais le pré-chargement FFTA (E01US004) ne renseigne **aucune** valeur de défaut, et l'écran archer n'expose pas le blason hérité.
- **CA — défaut FFTA par catégorie** : le pré-réglage FFTA renseigne le blason par défaut de chaque catégorie selon le [référentiel §3](../docs/referentiel-ffta.md) à 18 m — **Classique** : U11 = 80, U13/U15 = 60, U18/U21/S1/S2/S3 = 40 ; **Poulies** : triples 40 ; **Arc Nu** : U18 = 60, Scratch = 40 — **modifiable** (le référentiel est un template, jamais imposé ; [ADR-0020](../docs/adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)/[ADR-0022](../docs/adr/0022-hauteur-de-centre-portee-par-la-categorie.md)).
- **CA — blason hérité visible** : l'écran archer (`Archers.tsx` / `NouvelArcher.tsx`) affiche, **en lecture**, le blason **hérité de la catégorie** de l'archer (pas de champ blason **par archer** — la surcharge par archer reste **hors périmètre**).
- **Notes** : s'appuie sur `precharger_ffta` (`application/referentiel_ffta.py`, déjà câblé) + l'association E01US006. La règle FFTA exacte est à **revérifier au référentiel** à l'implémentation. Tests **service** (le défaut posé par le preset) après implémentation ; front vérifié **à l'écran**. US à **surface visible** (écran archer) → doc fonctionnelle + journal d'avancement.
- **Arbitrage tranché en cours d'US (28/07/2026, périmètre — option « preset blasons + défauts + affichage »)** : le CA supposait qu'il suffisait de **renseigner** le blason par défaut, l'association E01US006 étant déjà là. Mais `blason_id` est une **clé étrangère vers un blason existant du tournoi**, et **aucun blason n'était pré-chargé** (E01US005 n'a livré qu'un CRUD manuel, pas de jeu FFTA ; `precharger_ffta` ne créait que des catégories). Renseigner le défaut supposait donc d'abord de **créer les blasons**. E01US022 **absorbe** ce pré-chargement de blasons : `precharger_ffta` crée d'abord (idempotemment, par nom) les **quatre blasons canoniques** du §3 — « Blason 80 cm », « Blason 60 cm », « Blason 40 cm », « Triple 40 cm » — puis relie chaque catégorie au sien. `taille` étant une **fraction de place** (pas un diamètre), les valeurs retenues sont celles que le placement traite déjà comme canoniques (80 → `1.0`, 60 → `0.5`, 40 et triple → `0.25` ; `capacite` 1) ; le triple 40 se distingue par ses **zones** (10 → 6 + M, pas de 5 → 1, §4.4). Blasons et liens restent modifiables (template, RG-8). Affichage livré sur **`Archers.tsx`** (liste, blason à côté de la catégorie) **et `NouvelArcher.tsx`** (indice « Blason hérité de la catégorie » sous le choix de catégorie). Pas de champ blason **par archer** (hors périmètre, inchangé).
- **Dépend de** : E01US004, E01US006 · **Jalon** : J1 · **Origine** : démo 27/07/2026

### E01US023 — Les briques de l'atelier deviennent le patrimoine du club
*En tant qu'*organisateur, *je veux* que mes catégories, blasons et formats de tournoi vivent **dans l'atelier, hors de tout tournoi**, et qu'assembler un tournoi en prenne une **copie**, *afin de* ne plus tout ressaisir chaque année sans pour autant réécrire l'histoire des éditions passées.
- **Contexte** : [DETTE-023](../docs/dette.md#dette-023--latelier-affiche-des-briques-encore-scopées-par-tournoi). E14US003 range huit destinations dans l'axe **atelier**, dont la promesse est « fabriquer, **hors tournoi** » ; **cinq** ne la tiennent pas — les quatre repérées par DETTE-023 (`/tournois/{id}/categories`, `/blasons`, `/bareme-qualification`, `/phases`) **plus `Simulation`**, qui rejoue un tournoi et n'avait été comptée par personne (trouvée à la revue du 31/07/2026). L'atelier affiche donc « Choisissez un tournoi ci-dessus » sur la moitié de ses écrans, **sans sélecteur pour le faire**. Le pré-chargement FFTA est le symptôme de fond : il **recrée** les quatre blasons canoniques à chaque tournoi, faute de patrimoine où les ranger.
- **CA — bibliothèque** : une catégorie, un blason et un **format de tournoi** peuvent exister **sans tournoi** — ce sont des **modèles de bibliothèque**, listables et modifiables depuis l'atelier sans qu'aucun tournoi ne soit choisi. Le pré-chargement FFTA alimente **la bibliothèque**, une fois pour toutes, et non chaque tournoi.
- **CA — deux listes séparées** : la bibliothèque distingue à l'écran les briques **officielles FFTA** des **créations de l'utilisateur**. La marque d'origine dit **d'où vient** la brique — elle ne certifie **pas** la conformité au règlement (RG-8 : l'application n'impose ni ne vérifie la conformité).
- **CA — modifier un officiel** : modifier une brique d'origine FFTA propose **deux issues explicites** — en faire une **copie** (les deux modèles coexistent, la copie passant en « création utilisateur ») ou **modifier l'officiel sur place** (le règlement peut évoluer). Jamais d'écrasement silencieux.
- **CA — copie à l'assemblage** : appliquer une brique de bibliothèque à un tournoi en crée une **copie** rattachée à ce tournoi. Le tournoi porte **son propre matériau**. Modifier la copie **n'altère pas** le modèle ; modifier le modèle **n'altère aucun** tournoi déjà assemblé.
- **CA — promotion (« c'est permanent »)** : depuis la copie d'un tournoi, l'organisateur peut déclarer une modification **permanente** : elle est alors **promue** dans la brique de bibliothèque. La promotion ne réécrit **pas** l'histoire — les tournois déjà assemblés gardent leur copie, seuls les **prochains** assemblages héritent de la correction.
- **CA — format de tournoi** : un **format** est une brique nommée portant une **séquence de modèles de phases** (type, barème de qualification, grain de validation, effectif, source). Il ne porte **ni statut, ni tournoi**. L'appliquer à un tournoi **crée ses phases** (ordre 1..N, statut `à venir`), qui restent ensuite ajustables sans altérer le format.
- **CA — import du référentiel des clubs** : l'organisateur peut alimenter le référentiel des clubs **en masse** (une ligne = un club) au lieu de les saisir un à un, et obtient un **compte-rendu** : créés / doublons ignorés / lignes vides. Le doublon s'entend au sens de `domain.club.cle_nom` (casse, accents et espaces de bord repliés), comme la saisie unitaire — un import ne doit pas ouvrir une porte que le formulaire ferme.
- **Notes** : généralisation du patron **déjà éprouvé** de `gabarit_salle` (E01US007/E01US008 : « appliquer un modèle (copie), lire et ajuster la copie sans altérer le modèle ») — on ne l'invente pas, on l'étend. Tests **domaine et service** écrits **depuis ce CA** (règle 9) : bibliothèque, copie indépendante, promotion non rétroactive, application d'un format. Tests **API / repository** après implémentation. US à **surface visible** (l'atelier) → doc fonctionnelle + journal d'avancement. Résorbe DETTE-023.
- **Arbitrage tranché avec le commanditaire (30/07/2026, copie plutôt que référence)** : la brique est **copiée** à l'assemblage, pas **référencée**. Motif : si un tarif ou un barème change en 2027, le tournoi 2026 **archivé ne doit pas bouger** — une brique référencée réécrirait l'histoire, ce que l'archive en lecture seule (EPIC-11) et le journal d'audit interdisent. **Contrepartie assumée** : un tournoi encore en **brouillon** n'hérite pas d'une correction faite ensuite dans la bibliothèque ; il faut lui réappliquer la brique.
- **Arbitrage tranché en cours d'US (30/07/2026, forme des phases)** : « libérer le barème et les phases » ne peut **pas** se faire en rendant `Phase.tournoi_id` nullable, comme pour les catégories et les blasons. Deux raisons trouvées dans le code : (1) le **barème n'est pas une entité** — il vit dans la `config` de la phase de type `qualification` (`application/bareme_qualification.py`), il n'y a rien à rendre nullable ; (2) une `Phase` porte `ordre`, `statut`, `source` et `effectif`, et son invariant est **collectif** — `SequencePhases` exige que les ordres forment la suite contiguë `1..N` (`domain/phase.py`). Des phases de bibliothèque au `tournoi_id` nul porteraient un statut vide de sens et des ordres en collision, et toute lecture globale lèverait `SequenceOrdreInvalide` : il aurait fallu **désarmer** le garde-fou qui protège le moteur de phases. La brique réutilisable est donc le **format** (séquence de modèles de phases), pas la phase. Options soumises au commanditaire et retenue : *nouvelle brique « Format »*.
- **Arbitrage tranché en cours d'US (30/07/2026, périmètre de l'import des clubs)** : « import des clubs » figurait au reste-à-faire sans spécification retrouvable dans le backlog. Tranché en **import du référentiel** (liste collée, une ligne = un club, avec compte-rendu) — et **non** l'import des inscrits depuis un fichier fédéral, qui est **E02US007** et reste entier. Les deux ne se confondent pas : celui-ci alimente un référentiel **global** de l'atelier, celui-là crée archers, clubs et départs **d'un tournoi** avec ses propres pièges (quota, homonymes, licence).
- **Arbitrage tranché en cours d'US (31/07/2026, revue — quatre points reversés ici)** : la revue a établi quatre règles que ni le CA ni l'ADR ne portaient, et qui décident du comportement observable. (1) **Unicité de nom en bibliothèque** — deux modèles ne peuvent pas porter le même nom (au sens casse et espaces repliés), à la création **comme au renommage** : l'assemblage et la promotion dédoublonnent par le nom, donc deux homonymes les rendraient non déterministes (un seul serait copié, l'autre compté « déjà présent » sans jamais atteindre un tournoi) → 409 `nom_brique_deja_pris`. (2) **Appliquer un format est refusé** si une phase du tournoi est engagée, **si une phase porte des données** (forfait déclaré au pointage, duelliste posé à la main — les deux FK sont en `ON DELETE CASCADE`), ou **si le format ne décrit aucune qualification** alors que le tournoi en a une (il perdrait son barème, que rien ne permettrait de recréer). (3) **Promouvoir une copie qui n'a pas d'homonyme en bibliothèque crée un modèle « création du club »**, jamais un « officiel FFTA » : une brique renommée localement n'a aucun ancêtre au référentiel fédéral, et la ranger dans la liste officielle salirait la séparation demandée. Mettre à jour un **homonyme** conserve, elle, l'origine du modèle existant (« modifier un officiel le laisse officiel »). (4) **Une brique de bibliothèque ne peut hériter que d'un blason de bibliothèque** — à la création **et** à l'édition ; sans quoi un modèle traînerait une clé étrangère vers l'édition d'un tournoi, recopiée à chaque assemblage.
- **Dépend de** : E01US003, E01US005, E01US007, E14US003 · **Jalon** : J1 · **ADR** : [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) · **Origine** : DETTE-023, arbitrage commanditaire 30/07/2026

### E01US024 — Composer, diagnostiquer et simuler un déroulé de tournoi
*En tant qu'*organisateur, *je veux* composer un déroulé complet dans l'atelier, **le voir**, savoir
s'il tient debout et **le faire tourner** avant de l'utiliser, *afin de* comprendre mon tournoi d'un
coup d'œil au lieu de le déduire d'une liste de réglages.

- **Contexte** : E01US023 a fait du **format** une brique du club, mais l'écran livré ne sait
  fabriquer qu'une **qualification** — pas d'élimination directe, pas d'effectif, pas de source. La
  capacité de composer un déroulé a donc **disparu de l'atelier** : le contournement documenté
  (« composez-le sur un tournoi puis enregistrez-le comme format ») oblige à passer par une édition
  pour fabriquer un modèle du club, soit exactement le mélange que le découpage en axes supprime.
- **CA — le brouillon** : un format s'**enregistre à tout moment**, même incomplet ou incohérent ;
  il ne s'**applique** à un tournoi que s'il est cohérent. Demande du commanditaire (31/07/2026) :
  « *on doit pouvoir sauvegarder le brouillon tout le temps, mais on ne peut réellement l'utiliser
  pour un vrai tournoi que s'il est valide, avec un déroulé cohérent* ». L'invariant **quitte
  l'enregistrement pour l'usage** : ce qui doit être cohérent, ce n'est pas la ligne en base, ce sont
  les **phases produites**. Même patron que le tournoi, qui se crée en `brouillon` et ne passe `prêt`
  que s'il a au moins un départ ([ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md)).
  Le **nom** reste obligatoire (clé d'unicité) ; l'application refuse en **disant pourquoi**, jamais
  d'un refus muet.
- **CA — le schéma à braquets** : un **visuel découpé par phase**, calculé pour un effectif donné.
  Demande du commanditaire : « *je veux un visuel découpé par phase qui montre où sont les archers,
  ce qui leur est demandé, où ils iront après leur phase, comme un arbre faisant apparaître les
  « braquets » des joueurs, en fonction du nombre d'archers […] un visuel bien pensé pour un écran de
  PC, il ne doit pas laisser d'incompréhension pour celui qui crée l'assemblage de phases* ». Chaque
  bloc répond à **quatre questions** : *qui est là* (combien, et quelle tranche de rangs), *ce qu'on
  leur demande* (barème, format de duel), *où ils vont après* (une flèche par sortie), *combien de
  tours*. Plusieurs flèches peuvent **entrer** dans un bloc, pas seulement en sortir — une phase se
  peuple de sources multiples (E05US010) : c'est précisément ce qu'un schéma rend lisible et qu'une
  liste rend opaque.
- **CA — les braquets** : à chaque tour, les perdants forment une **tranche de rangs** qui devient un
  sous-tableau. C'est la **Règle R** de `moteur-placement-lucky-loser.md` rendue visible.
- **CA — effectif simulé** : un champ « simuler avec N archers » en tête d'écran. Sans effectif, un
  format reste abstrait (« qualification puis tableau ») ; avec, les braquets deviennent calculables
  (« rangs 33 à 120 »). Changer N recalcule le dessin.
- **CA — le schéma EST le contrôle de validité** : un archer **sans destination** est un **trou
  visible** dans le dessin, pas un message d'erreur abstrait. C'est ce qui unifie le brouillon et le
  visuel — et ce qui rend le diagnostic compréhensible par un non-technicien.
- **CA — simuler le format** : lancer le déroulé sur N inscrits fictifs et voir ce qu'il produit.
  Demande du commanditaire : « *je veux être sûr de pouvoir lancer une simulation du format du
  tournoi une fois les phases et le nombre d'inscrits donnés* ». La simulation révèle ce qu'aucune
  relecture ne donne : le format **tient-il** à cet effectif (personne bloqué, personne oublié),
  **combien de duels au total** — donc quelle charge pour les scoreurs et les cibles —, combien de
  tours par phase, et le **classement 1→N effectivement produit**.
- **CA — l'ajustement d'effectif** : simuler à **120** puis à **82** doit fonctionner sans retoucher
  le format (cf. E05US010, CA « plages relatives »). C'est le contrôle qui valide à la fois les
  sources relatives et la simulation.

**Notes — à lire avant de commencer.**

> **Il n'y a PAS de moteur de simulation à écrire.** `ServiceSimulation`
> ([ADR-0054](../docs/adr/0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md), E15US002 ✅)
> rejoue déjà qualif → duels → classement sur des adapters **in-memory**, la non-persistance étant
> une propriété **structurelle** (aucun chemin vers SQLite ni vers la file d'écriture). Et
> `ServiceJeuEssai` (E15US001 ✅) sait générer des archers fictifs. Il n'y a qu'à **composer les
> deux** : `simuler_format(format, effectif)` fabrique un tournoi éphémère **dans le harnais**, y
> applique le format, y génère N archers, et le joue. C'est même plus propre que le chemin existant,
> qui hydrate depuis un tournoi réel : ici rien ne vient de la base, donc le garde-fou d'ADR-0054 §4
> (« on ne simule qu'un tournoi avant démarrage ») n'a pas lieu de s'appliquer — il n'y a pas de
> tournoi réel à polluer.

> **Une seule source de règles, deux usages.** `verifier_coherence_etape` et `verifier_sequence`
> (`backend/domain/phase.py`, ~l. 324 et 339) lèvent aujourd'hui la **première** erreur rencontrée.
> Les transformer en **générateurs d'anomalies**, les versions levantes devenant de minces
> enveloppes qui lèvent la première produite. Les anomalies sont les **instances d'erreurs typées
> existantes** (`FormatSansEtape`, `SequenceOrdreInvalide`, `PhaseQualificationIncomplete`,
> `SourceApresPhase`…), qui portent déjà leur `code` et leur message : **aucune règle n'est
> recopiée** — c'est ce qui évite la duplication d'invariant que le registre de dette proscrit.

> ⚠️ **Cinq tests seront INVERSÉS**, et c'est délibéré. `test_domain_format_tournoi.py` vérifie
> aujourd'hui que la **construction refuse** (format sans étape, ordres non contigus, source
> postérieure, qualification sans barème). Ils deviendront des tests du **diagnostic** : mêmes cas,
> même vocabulaire, assertion retournée. Précédent au projet : DETTE-009 (« test de non-régression
> HTTP **inversé** »). **À signaler explicitement en revue** — c'est ce qui ressemble le plus à un
> garde-fou désarmé sans en être un, l'enforcement se **déplaçant** vers `appliquer`.

> **SVG maison, aucune bibliothèque** (règle 11 ; précédent [DETTE-024](../docs/dette.md), routeur
> maison plutôt qu'une dépendance). La mise en page d'un graphe à 3-8 nœuds tient en quelques
> dizaines de lignes. Logique **pure et testée** dans un module dédié (calcul des tranches et des
> flux depuis format + effectif) : le JSX ne se teste pas, la logique si — convention du projet
> (`features/blasons/zones.ts`, `features/phases/ordre.ts`). Réutiliser `deplacer<T>` de
> `frontend/src/features/phases/ordre.ts`, générique et déjà testé.

> **Le modèle à imiter pour l'éditeur** : `frontend/src/features/phases/Phases.tsx` fait déjà ce
> travail pour un tournoi (ajouter, typer, source, effectif, monter/descendre). Différences : pas de
> **statut** (un modèle n'en a pas) ; la **qualification est éditable ici** (barème + grain), alors
> que dans un tournoi elle est gérée par l'écran « Barème & validation » ; les **ordres sont dérivés
> de la position** dans la liste, jamais saisis — ce qui supprime par construction toute la classe
> d'erreurs « ordres non contigus ».

> **Décision structurante ⇒ ADR** : « un format se compose en brouillon ; l'invariant se vérifie à
> l'application, pas à l'enregistrement ». Conséquence à assumer noir sur blanc : **la base peut
> contenir des formats incohérents**, et c'est `appliquer` qui protège le tournoi.

- **Absorbe** : l'éditeur visuel et la simulation de format, cadrés le 31/07/2026 comme US distinctes
  puis regroupés à la demande du commanditaire (« des US les plus grosses possible »).
- **Dépend de** : **E05US010** (sources multiples et relatives — sans elles le schéma ne peut pas
  montrer les braquets ni s'ajuster à l'effectif) · **Jalon** : J3
- **Origine** : cadrage du 31/07/2026, parti du constat que l'écran d'E01US023 ne composait rien.
