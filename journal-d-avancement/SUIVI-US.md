# Suivi des US — état d'avancement

> **Ce fichier est le point de reprise.** Quand l'utilisateur dit « **reprend les US** », l'assistant
> lit ce tableau : il y trouve ce qui est **fait** (mergé sur `main`), et **la prochaine US** à
> prendre. La séquence de référence est celle de [`stories/README.md`](../stories/README.md) (jalons
> de valeur J0→J4). Le détail de chaque US est dans `stories/Exx-*.md`.
>
> **Règle de mise à jour** : une US passe à ✅ **dans son propre dernier commit, la revue
> (`/revue-us`) faite et poussée** — sans attendre la confirmation « c'est mergé ». C'est sûr parce
> que cette mise à jour **voyage avec le diff de l'US** : elle n'atteint `main` qu'**au merge de la
> PR**. Donc sur `main` ce tableau reste **toujours vrai** (le ✅ y apparaît pile au merge) ; sur la
> branche, il est optimiste d'un cran — c'est le livrable. Le même commit pointe la 🎯 suivante. En
> cas de doute au moment de reprendre, recouper avec `git log main --first-parent` / `git branch -r`.

**Dernière mise à jour : 08/08/2026, 12 h 37** · **106 US livrées** · dernière : `E05US024`
*(**le club est libre de son format** : un prélèvement est lu dans le classement de **sa** phase
source, plus seulement dans la qualification — poules→tableau, tableau→consolante, sur autant de
crans que le format en compte. Le plancher d'inscrits remonte la même chaîne. Née d'un arbitrage du
commanditaire au cadrage d'`E16US002` — « la création du déroulé doit permettre de composer les
phases comme on en a envie ». [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md) ;
reste de `DETTE-028` sur les rangs **résorbé**. ⚠️ **Plusieurs qualifications reste interdit** —
c'est `E05US025`, qui ne pouvait pas passer devant : sans cette lecture, une 2ᵉ qualification aurait
reçu *tous* les inscrits.)*

Avant elle : `E16US004`
*(**le public suit plusieurs archers de bout en bout** — refus P03 levé. **Un seul interrupteur
« mes archers / tout »** en tête de l'onglet public, armé par défaut, qui gouverne les cinq vues
(classement, tableaux, affectations, palmarès, plan de cibles) au lieu d'un réglage par écran ;
recherche par club, récapitulatif repliable de la journée, détail des flèches d'un tiers. Front seul.
[ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md))*.
Avant elle : `E16US003`
*(⚠️ **corrigé le 08/08/2026** : ce paragraphe décrivait `E16US003` sous l'étiquette `E16US004` — la
ligne d'en-tête avait été mise à jour sans son texte, et « précédente » sautait donc une US. Défaut
de tracker, pas de code ; relevé en tenant ce fichier pour `E05US024`.)*
*(**la complétude sportive ne parle plus d'argent** — refus A14 levé. Les deux questions ouvertes
de la story ont été reposées et **confirment le CA** : le refus portait sur le mélange **à l'écran**,
pas sur le découpage du domaine, et « Terminer » ne regarde bien que le sportif. Front seul : le
serveur séparait déjà `sportif` / `hors_sportif`, seule la **destination** change — le sportif reste
au pilotage sur un écran renommé « **Prêt à terminer ?** », l'administratif part en tête de l'écran
**Paiements** (axe gestion). **Pas de destination neuve** : `hors_sportif` ne porte qu'une ligne, et
`paiements` est déjà une destination de l'axe. Le **tableau de bord d'accueil** est filtré lui aussi
(arbitrage de revue : il ouvre l'axe pilotage, y laisser les impayés déplaçait le trou au lieu de le
fermer). La planche A14 redessinée du 05/08 est **écartée** au titre de la réserve 2 d'ADR-0074 (un
arbitrage du commanditaire prime la planche) — elle mélange encore. La confirmation de « Terminer »
**continue** de chiffrer les impayés : c'est le seul point de croisement légitime, et le bouton
n'est **jamais bloqué** par un manque, `D-15`)*. Avant elle : `E01US025`
*(**le départ est la portée sportive** — une décision de juillet 2025 que seule la logistique avait
portée : le moteur classait les 4 créneaux ensemble, soit un classement de 400 au lieu de quatre de
100. Corrigé, et la correction a révélé un second défaut — le déroulé **recopié** par créneau, libre
de diverger : il se définit désormais **une fois** au tournoi, chaque départ n'en portant que
l'avancement. Composer et piloter deviennent deux écrans. ADR-0075 + ADR-0076, migrations 0042/0043,
garde-fou mécanique. ⚠️ **US prise hors tracker et spécifiée après coup** — sa fiche vaut
non-régression, pas oracle)*. Précédente : `E17US004`
*(la **supervision passe en grille de tuiles** — planche A13, variante **B** « 30 d'un œil », retenue
et **validée sans réserve**, alors que le produit livrait la variante **A**, le tableau. Écran du jour
J : une tablette muette se repère au **cadre ambre** de sa tuile, état écrit en toutes lettres
(`DV-03`) ; l'IP de diagnostic et la révocation, **absentes de la planche**, sont conservées dans la
tuile. `voleeCourte`/`fractionAvancement` pures et testées **avant** le rendu, avec un test qui leur
interdit de diverger d'`avancementLibelle`)*. Précédente : `E17US003` *(A01 **connexion en colonne
centrée** — bandeau de titre, étiquettes visibles au-dessus des champs, bouton pleine largeur,
échappatoire sous la carte — et A02 **accueil des axes** — la question « Que venez-vous faire ? » et le
contexte de l'axe Pilotage. Précédée du **relevé d'écarts des 19 planches admin**, méthode
« questionnaire → variante retenue → écran »)*. Précédente : `E17US002`
*(le catalogue de composants — boutons, champs, cartes, onglets, pastilles, en-têtes de table —
adopte les **formes** des planches : deux familles de rayons (ossature 8-10 px, contenu 4-6 px), bouton
d'action en graisse 800, pastilles en petites capitales. **Deux non-reprises assumées** : la densité
(le commanditaire a demandé plus d'aération en A02, la planche est en retard) et le balisage des
listes (un `<table>` reste un `<table>`, il n'en prend que l'apparence). Vérifiée **au navigateur**,
ce qui a levé deux défauts invisibles aux tests — portes d'accueil en graisse 800, et « Annuler le
tournoi » en aplat ambre écrasant l'action principale)*. Précédente : `E17US001`
*(l'application **prend les couleurs du club** : elle tournait encore sur la palette du walking
skeleton — accent violet `#aa3bff`, fond blanc, `system-ui` — parce que les « US design » annoncées en
tête d'`index.css` n'ont jamais été écrites. Les jetons portent désormais la **charte mesurée**
(anthracite `#1D1D1B`, rouge club en **aplat seulement**, alerte **ambre**), le **sombre est le
défaut** sans suivre l'OS, et l'option « Système » de `D-26` survit par une règle `@media` dédiée.
**Décision de fond : les maquettes font foi** — ADR-0074, épic neuf [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md).
Deux points laissés ouverts au commanditaire : embarquer **Inter** (actif, règle 11) et la couleur
d'une **action destructrice**, absente de la charte)*. Précédente : `E16US001` *(le **plan de salle** parle enfin de la salle du club : « **pas de tir** » = un groupement de cibles, « **couloir de tir** » = la place d'un archer (A/B/C/D), « poste » reste une tablette — et l'écran **montre** les couloirs cible par cible. Premier des quatre écrans refusés relevé ; ADR-0073, qui **amende ADR-0006** et ferme la variante « plan libre » ; DETTE-042 pour le renommage `position` → `couloir` en base, différé et rattaché à E01US019)*. Précédente : `E07US005` *(le public suit les **arbres de duels en direct** — « mon chemin » par archer suivi ou tableau complet par tour —, et l'écran de salle sait enfin projeter les tableaux : le catalogue de vues d'ADR-0064 est complet)*. Précédente : `E03US007` *(l'organisateur choisit **ce qu'une cible n'a pas le droit de mélanger** — rien, la catégorie, le blason, ou les deux : contrainte **dure** sur le plan de cibles **et** le plan de duels, réserve motivée, plan antérieur signalé — ADR-0071)*.

---

## 🎯 Prochaine US

> **⚡ PRIORITÉ — retours du questionnaire de maquettes (04/08/2026), [`EPIC-16`](../epics/EPIC-16-retours-maquettes.md).**
> Les 36 planches ont été passées en revue par le commanditaire, une par une. Le **lot « front
> seul »** (tout ce qui ne demandait ni décision métier ni backend) a été livré le 05/08/2026 sur la
> branche `feat/retours-maquettes-front` — **hors US numérotée**, d'où un compte d'US inchangé. Ce qui
> reste est spécifié dans [`stories/E16`](../stories/E16-retours-maquettes.md), dix US.
>
> **Prendre d'abord les quatre écrans refusés (🔴)** — ce sont les seuls retours qui disent « l'écran
> ne répond pas au besoin ». **Trois sur quatre sont levés** (A10, A14, P03) ; reste A07 :
>
> | Ordre | US | Ce qu'elle lève |
> |---|---|---|
> | ~~1~~ ✅ | ~~`E16US001`~~ | **Livrée le 05/08/2026** — **plan de salle** (A10). Le refus ne tenait qu'à un mot : arbitrage rendu (« pas de tir » = groupement de cibles, « **couloir de tir** » = place d'un archer, « poste » = tablette), appliqué partout où l'utilisateur lit, et l'écran **montre** désormais, cible par cible, les couloirs occupables (le maillon *blasons* reste expliqué en toutes lettres : le gabarit ne les connaît pas). Renommage `position` → `couloir` dans le code/l'API/la base **différé** ([DETTE-042](../docs/dette.md)). |
> | ~~2~~ ✅ | ~~`E16US003`~~ | **Livrée le 07/08/2026** — **complétude** (A14). Les deux questions ouvertes ont été reposées et **confirment le CA** : le refus visait le mélange **à l'écran**, pas le découpage du domaine ; « Terminer » ne regarde que le sportif. Front seul, aucun changement de domaine ni d'API. Le sportif reste au pilotage sur un écran renommé « **Prêt à terminer ?** » (« Complétude du déroulé » a été écarté en revue : la sidebar porte déjà « Suivi du déroulé », et ADR-0076 réserve « déroulé » au plan composé une fois), l'administratif part **en tête de l'écran Paiements** — pas sur une destination neuve : `hors_sportif` ne porte qu'une ligne et `paiements` est déjà une destination de l'axe gestion. Le **tableau de bord d'accueil** est filtré lui aussi. La planche A14 redessinée du 05/08 est **écartée** (réserve 2 d'ADR-0074). ⚠️ Cadrage à reprendre : le commanditaire vise une **famille « prêt à… »** (démarrer / terminer / archiver / exporter) — refonte de navigation, US dédiée à instruire, cf. `stories/E16`. |
> | ~~3~~ ✅ | ~~`E16US004`~~ | **Livrée le 08/08/2026** — **public multi-archers** (P03). **Front seul, vérification faite** : `…/archers/{id}/deroule` est déjà public et anonyme pour n'importe quel archer (ADR-0039) et `…/tableaux` rend toutes les phases — aucune ligne de backend. Cadrage : **un seul interrupteur « mes archers / tout » en tête de l'écran public**, gouvernant les six onglets, et non un par vue. Conséquences : `VueTableaux` **perd** son sélecteur local « Mon chemin / Tableau complet » (E07US005), qui disait la même chose ; le palmarès ne centre que le classement final, **jamais les podiums** ; chaque vue nomme « aucun de vos archers ici » distinctement de son propre vide ; l'interrupteur disparaît sur un tournoi sans suivi. Recherche par club (un club seul suffit), suivi actionnable dans les deux sens, récapitulatif de journée en `<details>` **ouvert par défaut** (P02 dit « repliable », pas « replié »), détail des flèches dépliable depuis le classement. **Arbitrage du commanditaire, rendu en revue** : l'appli publique **s'ouvre centrée** sur les archers suivis — le CA d'E07US005 le promettait (« *Mon chemin* par défaut dès qu'on suit quelqu'un ») et l'interrupteur unique l'aurait révoqué en silence ; porté par [ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md). **Trois passes de revue** (1 bloquant + 14 majeurs à la 1ʳᵉ, 3 majeurs à la 2ᵉ dont un défaut *introduit* par le correctif précédent, 0 majeur à la 3ᵉ) ; DETTE-031 élargie. ⚠️ Reliquat « position » : la liste de maquettes de `stories/E16` était **fausse** (déjà corrigées par E16US001) — le vrai reliquat était dans `docs/fonctionnel/`, balayé ici. |
> | 4 | `E16US002` | **Phases** (A07) — **le dernier écran refusé**. ⚠️ **Périmètre rétréci au cadrage du 08/08/2026, et deux US en sont sorties.** Le CA « plusieurs phases de même type » n'était pas un problème d'écran : le moteur ne lisait qu'un classement, celui de la qualification, et l'unicité de la qualification n'était que le pansement de ce raccourci → `E05US024` (livrée) + `E05US025` (🎯, hors file E16). Le CA « gabarit de phase » est **tranché** : un seul niveau, ADR-0060 §5 confirmé — la brique réutilisable reste le **format**. Il reste donc la **liste**, le **titre de phase** (champ neuf → migration) et la **fiche de réglages** par type. Toujours à recadrer contre ADR-0076 (une partie du refus porte sur un écran qui n'existe plus sous cette forme). |
> | — | `E16US012` | **Famille « prêt à… »** — *née d'E16US003, hors file des 🔴*. Le commanditaire vise quatre écrans « puis-je passer à l'étape suivante, et sinon que manque-t-il ? » : **prêt à démarrer / terminer / archiver / exporter**. E16US003 n'en a livré qu'un (l'écran de complétude sportive, renommé). C'est une **refonte de navigation** qui recoupe la frise du cycle de vie (E14US001, ADR-0026), le feu vert (`E16US008`) et les exports (`E16US007`) : à instruire d'un bloc, ADR probable, **avant** que ces deux US ne figent chacune leur variante dans leur coin. |
>
> **⚡ Passé devant les 05 et 06/08/2026 — `E17US001` → `E17US004`** *(hors séquence E16)* : le commanditaire a comparé
> l'application aux maquettes et constaté qu'elles n'avaient rien à voir. La cause n'était pas un
> écran mais **la palette**, jamais posée. Traité en une passe sur les ~40 features, avec un épic neuf
> pour la suite ([`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) — confronter les 36 planches
> aux écrans livrés). La file E16 ci-dessous est **inchangée**.

> ⚠️ **`E01US025` a été prise hors de cette file** (06–07/08/2026) et n'y change rien : c'était la
> correction d'un **défaut de fond** — le moteur classait les créneaux ensemble —, découverte en
> relisant [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md), pas une US planifiée.
> Elle n'avait ni fiche ni ligne ici avant sa livraison ; les deux ont été écrites **après**, ce qui
> est un manquement à signaler et non un précédent à suivre. La 🎯 ci-dessous est donc inchangée.
>
> ⚠️ **Conséquence pour `E16US002` (écran « Phases », A07, refusé)** : elle doit être **recadrée**
> avant d'être prise. L'écran a changé de nature avec [ADR-0076](../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
> — il compose désormais un déroulé **sans statut**, le pilotage ayant migré vers « Suivi du
> déroulé ». Une partie du refus A07 (« 1/8 et 1/4 présentés comme des phases ») porte sur un écran
> qui n'existe plus sous cette forme.

> **🎯 Prochaine : `E05US025`** — **plusieurs qualifications dans un même déroulé**, la seconde
> moitié du chantier ouvert le 08/08/2026 par `E05US024`. **Hors file E16**, et assumé : le cadrage
> d'`E16US002` a montré que le refus A07 n'était pas d'abord un problème d'écran (voir ci-dessous).
> Elle **dépend d'E05US024** par nécessité, pas par confort — sans le peuplement générique livré
> hier, une 2ᵉ qualification recevrait *tous* les inscrits. Ce qui reste à faire n'est plus le
> peuplement mais les **lecteurs** : `ServiceBaremeQualification` est bâti de bout en bout sur
> « **le** barème du tournoi », et les 12 appels de `portee.qualification_du_tournoi` sont à trier un
> par un — terrain `DETTE-048`, « le seul module à n'être ni testé ni surveillé ». **ADR attendu**,
> et **trois points à trancher au cadrage**, listés dans la story (classement publié quand il y a
> deux qualifications ; ce que voit un archer engagé dans les deux ; ce qu'exige la complétude).
>
> **Ensuite : `E16US002`** — l'écran **« Phases »** (A07), **dernier des quatre écrans refusés**.
> Son périmètre a **rétréci** au cadrage du 08/08/2026 : le CA « plusieurs phases de même type » en a
> été **sorti** (devenu `E05US024` + `E05US025`), et le CA « gabarit de phase » est **tranché** — un
> seul niveau, [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5
> confirmé, la brique réutilisable reste le **format**. Restent la **liste**, le **titre de phase**
> (champ neuf sur `EtapeDeroule` → migration) et la **fiche de réglages** par type.
> ⚠️ **À recadrer avant d'être prise**, pour la raison notée juste au-dessus : depuis
> [ADR-0076](../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md), cet écran
> compose un déroulé **sans statut**, le pilotage ayant migré vers « Suivi du déroulé » — une partie
> du refus (« 1/8 et 1/4 présentés comme des phases ») porte donc sur un écran qui n'existe plus sous
> cette forme. C'est la plus lourde du lot : elle touche le **domaine et l'API**, probablement un ADR,
> et se cadre contre ADR-0060 et ADR-0062.
>
> ⚠️ La planche **A07 a été redessinée le 05/08** et **n'a pas été validée** (pas de tour 2). Le
> précédent est posé deux fois désormais (A14 en E16US003, P03 en E16US004) : la lire, mais faire foi
> sur le **questionnaire du tour 1**, au titre de la **réserve 2 d'ADR-0074**.
>
> Puis, sans ordre imposé : `E16US005` (placement), `E16US006` (origine FFTA + logo club),
> `E16US008` (feu vert), `E16US009` (écran de salle), `E16US010` (recherche & alertes),
> `E16US007` (exports/paiements/podiums — **à redécouper avant de prendre**), et `E16US011`
> (**rattrapage** : sept règles énoncées dans des questionnaires que le premier tri avait classés
> « validés tels quels » à tort — dont **deux contradictions à arbitrer**, S08 contre un endpoint
> vivant et A09 contre ADR-0014/0015).
>
> Les retours **écartés** et les questions **restées sans réponse** sont listés en fin de
> [`stories/E16`](../stories/E16-retours-maquettes.md) : aucun questionnaire ne reste sans suite.

> **⚠️ Le dossier de maquettes a changé de forme le 05/08/2026 — lire avant de prendre une US E16.**
> Les 36 planches sont désormais rendues **entières, à la taille réelle de leur appareil** (PC
> 1600 × 900, tablette 1280 × 800, vidéoprojecteur 1920 × 1080, téléphone 390 × 844), avec navigation,
> bandeaux et en-têtes — **151 écrans pleins**. Elles ne montraient jusqu'ici que des vignettes de
> 430 px sans ossature. Hors US numérotée : aucune décision métier, aucun changement de domaine, le
> compte d'US est **inchangé**. PR #135 et #136.
>
> **Trois conséquences pour E16, à ne pas manquer :**
>
> 1. **Les réponses du tour 1 sont archivées, pas perdues** —
>    `maquettes/questionnaires/tour-1-2026-08-04/`. Elles restent la **source des dix US E16** et
>    gardent toute leur valeur : c'est sur elles que E16US001 a été livrée. Les fichiers de travail
>    sont repartis vierges pour un **tour 2**, sur des écrans que le commanditaire n'a pas encore vus.
> 2. **Trois des quatre écrans refusés ont été redessinés en même temps.** A07 (phases), A14
>    (complétude) et P03 (classements publics) ont maintenant une proposition en plein écran — qui
>    **n'a pas été validée**. Prendre `E16US002` (ou `E16US004`, qui touche P03) sans avoir la réponse
>    du tour 2 sur ces planches, c'est risquer d'implémenter une proposition que le commanditaire
>    écartera.
>    - **Précédent posé le 07/08/2026 par `E16US003`** : la planche A14 a été **écartée** et l'US
>      livrée sur le **questionnaire du tour 1**, qui fait foi. Motif à reprendre tel quel — la
>      **réserve 2 d'ADR-0074** (« un arbitrage explicite du commanditaire l'emporte sur la planche »),
>      et **non** « la planche n'a pas été validée » : les planches sont opposables **sans** validation,
>      et ce second motif ouvrirait la porte à écarter n'importe laquelle.
> 3. **Une erreur de fond a été corrigée sur A07, et elle change le cadrage d'`E16US002`.** La planche
>    listait « 1/8 de finale » et « 1/4 de finale » comme **des phases**. C'est faux :
>    `backend/domain/tableau.py` ne connaît qu'**une** phase d'élimination directe, qui porte tout le
>    tableau — les niveaux sont des `tour` de match. Le refus de A07 doit donc être relu à la lumière
>    de cette correction : une partie portait peut-être sur ce malentendu.
>
> Le dossier a par ailleurs fait remonter **deux écrans qui n'existaient nulle part** : le **barrage**
> (égalité 5–5 en duel, le seul moment où l'application cède la décision à un juge) et le **conflit de
> saisie** (deux postes modifiant la même volée). Ni l'un ni l'autre n'est spécifié — ils sont
> maquettés, pas décidés.


> **⚡ Priorité immédiate — retours de la démo du 27/07/2026.** Avant de reprendre la séquence J2,
> traiter le **lot démo** (bugs & petits ajouts), puis les épics **EPIC-14** (accueil admin) et
> **EPIC-15** (jeu d'essai & simulation) — détail en section « Ajouts de la démo du 27/07/2026 » plus
> bas. Ordre des bugs : ~~E02US010~~ ✅ (horaire `HH:MM`), ~~E01US017~~ ✅ (7 statuts),
> ~~E11US008~~ ✅ (LAN + QR), ~~E03US011~~ ✅ (placement), ~~E01US022~~ ✅ (blason FFTA).
> **Les bugs du lot démo sont clos**, **EPIC-14 est livrée** (accueil-tableau de bord + aide
> contextuelle) et **EPIC-15 est close** (`E15US001` jeu d'essai + `E15US002` moteur de simulation
> éphémère + `E15US003` cockpit de simulation livrés). **`E12US002` est livrée** (feu vert + lancement) ;
> la séquence J2 reprend maintenant à `E08US005`.
>
> **⚡ PRIORITÉ — le chantier « moteur de phases & plan de tournoi » (cadré le 31/07/2026).** Il passe
> **devant** `E07US008`. Quatre US, à prendre **dans cet ordre** — chacune porte son contexte complet,
> lisez-la avant de coder :
>
> | Ordre | US | Ce qu'elle livre |
> |---|---|---|
> | ~~1~~ ✅ | ~~`E05US010`~~ | **Livrée le 31/07/2026** — moteur de placement 1→N, **routing générique** (`route(contexte)`), **sources multiples et relatives**, oracle 120 ([ADR-0061](../docs/adr/0061-routing-generique-et-placement-en-cascade.md)) |
> | ~~2~~ ✅ | ~~`E05US015`~~ | **Livrée le 31/07/2026** — le **catalogue de types**, élargi à **onze** formats ([ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md)) |
> | ~~3~~ ✅ | ~~`E01US024`~~ | **Livrée le 01/08/2026** — écran « Composer un déroulé » : brouillon enregistrable à tout moment, **schéma à braquets** (Règle R rendue visible), diagnostic à deux gravités et **simulation** sur N archers fictifs ([ADR-0063](../docs/adr/0063-brouillon-de-format-invariant-a-l-application.md)) |
> | ~~4~~ ✅ | ~~`E07US004`~~ | **Livrée le 02/08/2026** — **écran de salle** (poste typé cible/écran, déroulé de vues, pilotage à distance) + le schéma à braquets **rempli par la réalité**, sur trois surfaces ([ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md)) |
>
> **Le chantier « moteur de phases & plan de tournoi » est clos** (4/4). `E07US008` reprend donc la
> tête de la séquence J2.
>
> **Pourquoi E05US010 était en tête** : le verrou du moteur n'était pas le catalogue de types mais
> le **routing** — `DestinationPerdant` n'avait qu'**une** valeur, `ELIMINE`, et une méthode sans
> argument ne peut rendre qu'une réponse constante. **C'est levé** : `Routing.route(contexte)` rend
> `HorsTableau` ou `VersPlage`, et E05US015 n'a eu qu'à ajouter sa destination de repêchage
> (`VersRepechage`) — la prévision s'est vérifiée au mot près.
>
> **Ce qu'E05US015 a livré au-delà de son CA d'origine.** Le commanditaire a fourni le 31/07 les
> règles des **cinq formats** que le *gate* « pas de règle écrite, pas d'US » retenait depuis
> l'origine (handicap, système suisse, King of the Hill, Ladder, finale spectacle) : ils sont entrés
> dans l'US. Découverte de conception au passage — **trois de ces onze formats ne sont pas des types
> de phase** : le repêchage est une politique `routing`, le handicap une politique `scoring`, la
> finale spectacle un assemblage de briques déjà livrées. Un type se justifie par une **structure**,
> pas par un réglage ([ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) §1).
>
> **Origine** : une session de cadrage du 31/07/2026, partie du constat que l'écran « Formats » livré
> par E01US023 ne savait composer qu'une qualification. Trois découvertes y ont été faites et sont
> consignées dans les US : **Q9 fermée** (la règle du Big Shoot Off, bloquante depuis le cahier des
> charges, a été fournie par le commanditaire), **E05US019 était un doublon** d'E01US023, et le
> **verrou routing** ci-dessus. *(Aucun code n'a été écrit ce jour-là : seul le backlog.)*
>
> **`E07US008` est livrée (02/08/2026)** — le **canal n°2** est en place. Elle a tenu plus que sa
> promesse de « simple surface publique » : le service savait router **une liste d'archers fournie**,
> pas *tout* le tableau, et deux cas du CA n'étaient pas couverts du tout. D'où
> [ADR-0065](../docs/adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) :
> - le **rang de l'éliminé** se lit désormais sur la **plage du match perdu** (*Règle R*), donc en
>   **fourchette** (« 5ᵉ-8ᵉ ») — plus de « rang publié en fin de phase » là où le rang *est* acquis.
>   Le panneau de la tablette (E04US018) en bénéficie sans y toucher : même projection ;
> - le **repêché** a une **issue distincte** de « éliminé » et voit la phase qui le reprend ;
> - `affectations` est entrée au catalogue de l'écran de salle **sans migration**, exactement comme
>   ADR-0064 l'avait prévu. Il ne lui manque plus que `tableaux` (E07US005).
>
> **La revue a trouvé un bloquant et neuf majeurs, tous corrigés avant la PR.** Deux méritent d'être
> retenus parce qu'ils disent quelque chose de la manière dont l'US a été écrite : (a) le panneau
> rangeait **les demi-finalistes sous « Sortis du tableau »** dès le 2ᵉ tour — il partitionnait sur
> la *cible*, que le serveur ne pose qu'au tour 1 ; la recette ne déroulait que le tour 1, donc elle
> ne pouvait pas le voir ; (b) la fourchette de rangs n'était **pas bornée par l'effectif** — « 65ᵉ-128ᵉ »
> sur l'oracle 120 — parce que les seuls effectifs du décor de test, 4 et 8, sont précisément ceux
> où `taille == effectif`. Dans les deux cas le défaut naît de la **rencontre** du code et de son
> jeu d'essai, pas de l'un des deux.
>
> **`E06US003` est livrée (02/08/2026)** — les ex æquo peuvent enfin se départager **au tir**.
> L'US a surtout révélé que le travail n'était pas là où le CA le laissait croire : le **moteur** du
> barrage était livré et pur depuis E05US015 (absents relégués → plus haut score → distance au
> centre → groupes à rejouer), mais **sans aucun appelant**. Ce qui manquait, c'était le
> **déclenchement**, la **persistance** et le **verdict** — [ADR-0066](../docs/adr/0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md) :
> - le **seuil** (« barrer jusqu'au rang N ») est un réglage de **format**, donc une politique. Logé
>   dans la famille `tiebreak` plutôt qu'en 7ᵉ famille, pour que seuil et comparateur restent
>   **accordés** — barrer selon §8.1 dans un tournoi qui départage en poule n'aurait aucun sens ;
> - le seuil désigne le rang du **groupe**, pas chacune de ses places : un barrage déclenché au 8ᵉ
>   tranche donc aussi la 9ᵉ. C'est le cas d'usage même — « départager la dernière place
>   qualificative » est par construction une égalité qui chevauche le seuil ;
> - le **verdict n'est pas stocké**, il se recalcule depuis les tirs. C'est ce qui rend une flèche
>   mal notée corrigeable : la corriger corrige le classement ;
> - `classement.py` **passe enfin par `PolitiquesPhase.tiebreak`** au lieu de réimplémenter §8.1 à la
>   main — la couture qu'E06US001 avait annoncée, et **une part de DETTE-028**.
>
> **Le défaut du produit ne bouge pas** : sans seuil réglé, le classement est mot pour mot celui
> d'E06US001 (rangs partagés), ce qu'un test fixe explicitement.
>
> **Les trois portées sont câblées** (élargissement demandé après le cadrage), mais **la boucle
> n'est fermée que pour la qualification** : là, les tireurs sont *dérivés* du classement et le
> verdict y *retourne*. En poule et en Big Shoot Off, l'organisateur *désigne* les tireurs — ni
> `poule.py` ni `big_shoot_off.py` n'ont de consommateur de production (vérifié dans le code,
> DETTE-028), donc il n'existe aucun classement où lire les ex æquo ni reverser le verdict. Le
> barrage y est pleinement opérationnel ; son résultat se lit à l'écran et se reporte à la main.
>
> ⚠️ **La revue a trouvé cinq bloquants**, tous corrigés. Trois méritent d'être retenus parce
> qu'aucun axe ne pouvait les voir seul : la manche était **écrite puis validée** (une saisie
> refusée mettait le classement *public* en 422 pour tout le tournoi) ; la **manche 1** n'était
> jamais confrontée aux tireurs annoncés (un barrage saisi à moitié classait **premier** l'archer
> non noté) ; et le **seuil ne se réglait par aucun écran** — livré jusqu'à l'API, la fiche de
> recette décrivait un champ qui n'existait pas. S'y ajoutait un défaut relevé par **les cinq
> axes** : un archer qu'une volée validée en retard amenait à égalité *après* le tir prenait la
> place devant le vainqueur du barrage, sans que rien ne le signale.
>
> **`E05US021` est livrée (04/08/2026)** — le contrôle d'effectif remonte de la tablette vers la
> table de l'organisateur ([ADR-0069](../docs/adr/0069-effectif-minimum-deduit-et-exige.md)). Trois
> points méritent d'être retenus :
> - le minimum se **déduit** des prélèvements, il ne se saisit pas. Le CA laissait les deux ouverts
>   (« déclare, **ou** dérive ») ; un nombre saisi peut contredire le déroulé écrit juste en dessous,
>   et le problème reviendrait là même où l'US le retire. Le club peut exiger **plus** (règle
>   sportive), jamais moins — l'énoncer sous le plancher rend le format inapplicable ;
> - **portée volontairement étroite** : un rang se lit dans le classement de sa *phase source*, pas
>   dans les inscrits. Seuls les prélèvements visant la **première** phase se traduisent en nombre
>   d'inscrits ; élargir aurait produit un chiffre **faux**, ce qui est pire que pas de chiffre ;
> - **aucune anomalie nouvelle** à la composition : `PrelevementVide` couvrait déjà le cas. Le
>   minimum est exposé comme une **donnée** du diagnostic — l'ajouter en anomalie aurait signalé le
>   même défaut deux fois, le piège déjà documenté dans `_anomalies_effectif_declare`.
>
> Le CA a été **élargi au cadrage** (04/08) sur deux points, reversés dans `stories/` : le minimum
> exigé facultatif, et l'annonce **avant** le clic (le CA d'origine ne prévoyait qu'un refus au
> clic — qui n'apprend rien tant qu'on ne clique pas). Un test d'API a trouvé un vrai défaut au
> passage : la lecture de l'exigence rendait 200 sur un tournoi inexistant.
>
> **`E06US006` est livrée** (04/08/2026, [ADR-0070](../docs/adr/0070-profondeur-de-classement-reglee-par-phase.md)).
> La prévision s'est vérifiée sur un point et trompée sur un autre, et les deux méritent d'être lues
> avant de prendre la suite : **le palmarès n'a effectivement pas bougé** — sous placement intégral
> les fourchettes se referment d'elles-mêmes, le mécanisme d'E06US004 *était* déjà le « regroupement
> du reliquat » du CA. En revanche, la profondeur n'était **exposée nulle part** : elle était figée
> au composition root, avec un commentaire annonçant qu'E01US024 l'exposerait — ce qu'E01US024 n'a
> pas fait. **Le vrai travail était l'exposition, pas le classement.** Un CA hérité d'une refonte de
> maille (« ex-006 / ex-007 ») décrit l'intention, pas l'état du code : le vérifier **avant** de
> cadrer aurait évité un aller-retour d'analyse.
>
> **Ce que la revue a corrigé, et qui vaut pour les US suivantes.** Un **bloquant** trouvé par les
> **cinq** axes : un composant monté sous condition (`{enTableau && …}`) qui dérivait son état
> d'une prop — au retour, l'écran affichait un réglage et le formulaire en soumettait un autre. La
> leçon est réutilisable telle quelle : *un état dérivé d'une prop, dans un composant monté sous
> condition, diverge dès que la condition bascule*. Le test qui aurait dû l'attraper suivait le
> chemin **aller** du garde-fou et jamais le retour. L'axe adversarial a par ailleurs **mesuré** ce
> que l'US annonçait à la louche (128 → 436 duels sur un tableau de 120, et non « une trentaine →
> plus d'une centaine ») : un chiffre faux reversé dans `stories/` serait devenu l'oracle des US
> suivantes.
>
> **`E03US007` est livrée** (04/08/2026, [ADR-0071](../docs/adr/0071-cloisonnement-categorie-blason-active-et-dur.md)).
> Trois points valent d'être retenus avant de prendre la suite :
> - **la contrainte est d'une autre nature que ses deux voisines.** Mixité de club (ADR-0047) et
>   côte à côte des duellistes (ADR-0048) sont des **préférences** obtenues en ré-ordonnant l'entrée
>   du glouton ; le cloisonnement s'**active délibérément**, donc il est **dur** et se câble *dans*
>   le glouton. Le réflexe « faire comme la mixité » aurait produit une règle officielle violable au
>   mieux — c'est-à-dire rien. Corollaire : l'ordre de priorité laissé ouvert par EPIC-03 depuis
>   l'origine est tranché — `capacité/espace/hauteur` > `cloisonnement` > `mixité` > `adjacence` ;
> - **le seuil d'ADR-0023 §2 n'est pas franchi — mais pas pour la raison qu'on croyait.** ADR-0047
>   désignait cette US comme « la prochaine occasion » d'extraire un mécanisme de contraintes
>   injectables. Verdict : **non**, on n'extrait rien. Le paragraphe qui l'explique (ADR-0071 §6) a
>   dû être **réécrit deux fois** avant d'être juste, et c'est la leçon la plus réutilisable de
>   l'US : (1) « aucune duplication n'apparaît » était faux — la **séquence de gardes** de
>   `_CibleEnCours` était recopiée, et l'US y avait ajouté la même ligne des deux côtés ; (2) « cinq
>   contraintes, le seuil de trois est dépassé » était faux aussi — ADR-0023 compte les contraintes
>   **ajoutées** au socle, et la mixité n'en étant pas une (ré-ordonnancement), le cloisonnement est
>   le **premier** ajout. Le remède réel n'était pas un registre mais **deux délégations** :
>   `accueille` ne réécrit plus ni les gardes (`peut_accueillir`) ni la consommation (`reprendre`).
>   Le seuil reste donc posé pour la contrainte suivante. **À retenir pour EF-1.4** : vérifier ce
>   que le seuil compte *avant* de conclure qu'il est atteint ;
> - **une position du réglage ne sert à rien aujourd'hui, et c'est écrit partout.**
>   `blason_et_categorie` rend le même plan que `categorie` tant que le blason **dérive** de la
>   catégorie. Livrée sur demande du commanditaire, la redondance est documentée dans le code, la
>   story, l'ADR §3 et la fiche de recette — elle se dissipera avec EF-1.4 (une phase surcharge le
>   blason). Ne pas la relire plus tard comme une capacité acquise.
>
> **E07US005 est livrée (04/08/2026)** — l'appli publique gagne un onglet « Tableaux » à deux
> lectures (« Mon chemin » par archer suivi, tableau complet par tour) et l'écran de salle sa
> quatrième vue. **Le catalogue de vues d'ADR-0064 couvre désormais son CA en entier**, après trois
> élargissements et **zéro migration** — la prévision de conception d'E07US004 est validée jusqu'au
> bout. Deux enseignements à ne pas perdre :
>
> - **le test a corrigé la lecture du CA, pas l'inverse.** « L'arbre (principal + placement) » a
>   d'abord été lu comme « les deux **types de phase** en tableau » ; le test écrit sur cette
>   lecture a échoué en découvrant que `TypePhase.PLACEMENT` est **composable mais pas exécutable**
>   (`DETTE-028` — `ServiceSaisieDuels._decor` le refuse). La bonne lecture était « les deux
>   **branches d'un même arbre** », sous-tableaux de placement compris (E06US006). Écrire le test
>   depuis le CA **avant** d'implémenter est exactement ce qui a rendu l'erreur visible en dix
>   minutes plutôt qu'à la recette ;
> - **la maquette avait deux questions ouvertes et son questionnaire était vide.** Elles ont été
>   tranchées au cadrage (les deux lectures, oui ; les horaires prévisionnels, non — le domaine n'en
>   porte aucun) et **reversées dans `stories/`**. Le CA d'origine tenait en une ligne : sans le
>   cadrage, l'US aurait livré un tableau brut sans « mon chemin ».
>
> **🎯 ~~Prochaine :~~ `E13US002`** — composer les équipes. ⚠️ **Supplanté** le 05/08/2026 : la
> priorité est passée au lot **EPIC-16** (retours de maquettes), voir la section « Prochaine US » en
> haut de ce fichier, qui **fait foi**. `E13US002` reste la meilleure candidate **hors E16**.
> *(Choisie parmi les ⬜ : le **fil équipes** est débloqué depuis `E13US001` (abstraction
> `Participant`, ADR-0028) et n'a jamais été repris ; c'est la dernière capacité **métier** encore
> absente du MVP+1, là où les autres ⬜ de J3 sont du confort (`E01US016` identité visuelle) ou un
> export déjà à moitié couvert. Alternatives si la priorité change : `E09US005` (PDF du classement
> de qualification, rétrécie par E06US004) et `E01US016`.)*
> *Note : **J2 est terminé** (14/14). Son compteur affichait `11/14` — périmé de deux crans depuis
> E07US008 et E06US003, qui l'avaient laissé en l'état ; recompté et corrigé par E06US004. **J3**
> l'était aussi (`4/11` pour six lignes ✅) : un premier jet de ce commit s'était arrêté à la ligne
> du dessus, ce que la revue a relevé — un recompte annoncé qui ne recompte qu'un jalon laisse le
> voisin faux et fait repartir « reprend les US » sur une base fausse.*
> *Note : le **fil équipes** est **débloqué** — `E13US002` (composer les équipes) peut être pris à tout
> moment maintenant qu'`E13US001` a posé l'abstraction `Participant`.*
> *`E12US004` (tracer un forfait) est **absorbée** par `E04US015` — voir ci-dessous.*
> *J1 est **terminé** (46/46) ; le confort « ma journée » et les classements imprimables restent hors
> décompte du jalon.*
>
> *Fait juste avant :*
> - `E07US004` **écran de salle & suivi du déroulé** — US à **surface visible**, qui **clôt le
>   chantier moteur** par sa sortie visuelle. L'écran de salle est un **`Poste` typé** (`cible` |
>   `ecran`), pas un agrégat parallèle : le CA disait « rien de neuf à inventer », et le typage fait
>   hériter gratuitement le jeton, le QR, le heartbeat et la supervision. ⚠️ Le prix est que
>   `cible_index` devient `int | None` — mypy strict a listé les **14 points** qui supposaient « tout
>   poste est une cible », et l'invariant est désormais **exigible au point d'usage** (`Poste.cible()`
>   lève) plutôt que porté par un `CHECK` hors domaine. **Décision centrale** : le pilotage admin est
>   un **état lu, pas un ordre poussé** — le hub temps réel est mono-canal, et surtout la **fin** d'une
>   prise de contrôle naît du *temps qui passe*, qu'aucun événement serveur ne peut diffuser (le
>   raisonnement d'ADR-0038 §4, réemployé). Corollaire assumé : déroulé **persisté**, consigne **en
>   mémoire** — un redémarrage *libère* les écrans au lieu de les figer. **Q-UX7 fermée** (durée **et**
>   retour explicite ; `Consigne.exige_rappel` nomme le cas « sans échéance » **dans le domaine**, ce
>   qui donne un point d'ancrage au « jamais un état forcé qu'on oublie »). Le suivi **superpose** la
>   réalité sur la projection d'E01US024 **sans la recalculer** — le CA dit « le **même** schéma » —,
>   et le piège du lot est traité : **un exempt n'est pas un duel joué** (les compter afficherait
>   « premier tour terminé » avant que quiconque ait tiré). Côté front, **un seul composant de dessin
>   pour trois surfaces**, sans variation de géométrie : c'est le `viewBox` du SVG qui met tout à
>   l'échelle. ⚠️ Le **catalogue de vues** est plus court que le CA (`affectations` E07US008 et
>   `tableaux` E07US005 manquent) — les offrir programmerait une page vide ; leur ajout sera **une
>   ligne, sans migration**. Migration `0038`.
>   [ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md).
>   Recette : [`docs/fonctionnel/E07US004.md`](../docs/fonctionnel/E07US004.md).
> - `E05US015` **catalogue de types de phase** — US à **surface visible**, qui **ferme la question Q9**
>   du cahier des charges, bloquante depuis l'origine du projet. Six types neufs, **chacun avec son
>   moteur** (ADR-0045 §2 : on n'offre pas un type qu'aucun moteur ne sait dérouler) : `echauffement`,
>   `barrage`, `poules`, `big_shoot_off`, `suisse`, `colline` — King of the Hill **et** Ladder étant
>   **un seul** moteur, la portée de défi les sépare. ⚠️ **Trois formats attendus ne sont pas des
>   types** : repêchage = politique `routing` (`RoutingRepechage`, qui **décore** un routing existant
>   au lieu de le remplacer — le format du club repêche *et* place), handicap = politique `scoring`,
>   finale spectacle = élimination directe à 8 + `BaremeDuel` déjà livré. `Scoring.total()` est
>   **ressignée** pour recevoir un `ContexteScore` (un handicap est une donnée du tireur) : rupture
>   annoncée par `politiques.py`, qui n'a coûté **aucun** appelant de production. `DecompteDepartage`
>   s'élargit par **champs à défaut 0**, ce qui réduit à rien la « rupture la plus risquée de l'US ».
>   L'échauffement porte l'invariant le plus intéressant du lot — une phase **sans classement** ne se
>   prélève pas **par rangs**. Handicap : deux valeurs par archer (officiel + surcharge), migration
>   `0037` ; ⚠️ **aucune table n'est codée** — le projet n'en a aucune, la FFTA n'a pas de système
>   officiel, et en inventer une donnerait des classements plausibles mais faux.
>   [ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md).
>   Recette : [`docs/fonctionnel/E05US015.md`](../docs/fonctionnel/E05US015.md).
> - `E05US010` **placement intégral 1→N & peuplement multiple** — la tête du chantier moteur, qui
>   **résorbe DETTE-015**. Le moteur ne désigne plus quatre archers mais les **classe tous** : chaque
>   perdant redescend dans le tableau des places qu'il peut encore atteindre (*Règle R*), jusqu'à un
>   match terminal qui fixe deux rangs (*Règle T*). **Découverte de conception qui a changé la
>   solution** : l'élimination directe livrée par E05US005 **est déjà un placement** — elle a une
>   petite finale, donc les perdants des demies rejouent — simplement **tronqué au rang 4**. La
>   génération est donc devenue une **récursion sur les plages de rangs** dont l'ancien format est le
>   cas particulier : à profondeur `podium`, elle rend **le même arbre, la même numérotation**
>   (non-régression structurelle, pas plaquée). `Routing` dit *où* descend un perdant, `Depth` dit
>   *jusqu'où* — et le routage se décide à la **construction**, pas à chaque match joué, sans quoi la
>   structure dépendrait de l'ordre de saisie (ADR-0049). Côté peuplement : `Phase.sources` (liste),
>   trois natures (`rangs` / `issue_de_tour` / `reste`) et **plages relatives** (fin ouverte) — un
>   format composé pour 120 archers tient à 82. Migration **0036 sur les deux tables** (`phase` **et**
>   `format_tournoi`, l'écueil signalé par la revue d'E01US023). **L'oracle 120 existe enfin** : il
>   était cité par la règle 9 depuis l'origine sans qu'aucun test ne l'implémente — c'est désormais un
>   rejeu du classeur réel (fixture extraite en stdlib, sans ajouter `openpyxl`). ⚠️ Il porte sur les
>   rangs **5 à 120** : le sommet du classeur est un **Big Shoot Off** (E05US015), pas une finale
>   d'élimination — il n'y a rien à y comparer. [ADR-0061](../docs/adr/0061-routing-generique-et-placement-en-cascade.md).
>   Recette : [`docs/fonctionnel/E05US010.md`](../docs/fonctionnel/E05US010.md).
> - `E01US023` **les briques de l'atelier deviennent le patrimoine du club** — US à **surface
>   visible**, qui **résorbe DETTE-023**. Catégories et blasons peuvent exister **sans tournoi**
>   (modèles de bibliothèque) ; un tournoi en reçoit une **copie** ajustable, et une modification
>   déclarée permanente **remonte** au club sans rétroagir sur les éditions déjà montées (copie et
>   non référence : un réglage changé en 2027 ne doit pas réécrire le tournoi 2026 archivé —
>   [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)).
>   Le déroulé devient une brique neuve, **`FormatTournoi`** : « libérer les phases » en rendant
>   `Phase.tournoi_id` nullable était impossible sans désarmer l'invariant `SequencePhases`
>   (ordres contigus 1..N) — arbitré avec le commanditaire. `Barème`, `Phases` **et `Simulation`**
>   passent au **pilotage** (elles règlent ou rejouent une édition, comme `Plan de salle` face à
>   `Gabarits` — ADR-0060 §6, qui amende ADR-0058) ; l'atelier gagne `Formats`, le pilotage gagne
>   `Assemblage`. Ajouts au passage : pré-chargement FFTA **dans
>   la bibliothèque** (au lieu d'à chaque tournoi) et **import en masse des clubs**.
>   Recette : [`docs/fonctionnel/E01US023.md`](../docs/fonctionnel/E01US023.md).
> - `E04US018` **afficher la prochaine cible après validation** — US à **surface visible**, le
>   **canal n°1 des quatre canaux de routage** (`D-09`) et le **premier récepteur** du signal
>   `tour_lance` d'`E12US002`. Un service de lecture **pure** (`application/routage.py`) répond « où
>   tire cet archer ensuite » en agrégeant ce que le tableau reconstruit et le plan de duels persisté
>   tiennent déjà : **rien n'est calculé** à la bascule (`D-08`), puisque les cibles sont attribuées
>   aux **matchs** et non aux archers. Endpoint `GET /api/v1/routage/{tournoi}` (lecture **publique**,
>   contrat E10US001), qui **résout lui-même** la phase de tableau quand le client ne la donne pas —
>   la tablette de qualification ne connaît que sa cible. **Périmètre élargi au cadrage** : les
>   **deux** surfaces (qualif après validation des séries **et** duels après validation d'un duel),
>   un seul composant `PanneauRoutage`. **Trois informations du CA étaient insatisfiables** et sont
>   **retirées ou annoncées** plutôt que devinées : l'**heure** (n'existe pas par tour de tableau),
>   le **repêchage** (E05US016), le **rang intermédiaire** (E06US004) — et la **cible d'un tour ≥ 2**
>   (E05US010) n'est **jamais** reprise du tour 1, qui serait périmée (même garde que le feu vert).
>   Ce qui manque est **nommé côté serveur** (« cible attribuée au lancement du tour », « en attente
>   du duel n°2 », « rang publié en fin de phase ») pour que les quatre canaux disent la même chose.
>   Nouveau `libelle_tour` au domaine (« Quart de finale », « 1/8 de finale », « Petite finale »).
>   Tests **service depuis le CA** (prochain duel, exempt, élimination, podium, lecture pure) ;
>   API/front **après**. Oracle 120 vert. Story alignée (Arbitrages). **Aucun ADR** : ADR-0056 avait
>   déjà tranché le fond — vérifié à la revue sur les quatre candidats. La revue a fait ajouter, avant
>   la PR : le **signal `forfait`** sur la ligne de grille (sans lui, un abandon privait la cible
>   entière du panneau **à vie**), une **porte d'ouverture manuelle** en toutes circonstances, des
>   lignes **nominatives** dans le panneau dégradé, et surtout la garde « **la pose n'est annoncée que
>   si l'adversaire du jour est posé sur la même cible** » — un reclassement recalcule l'appariement
>   alors que le plan reste persisté, et l'ancienne pose enverrait les deux duellistes sur deux
>   buttes. Deux dettes inscrites au registre : [DETTE-019](../docs/dette.md) (jumeau de
>   `ServicePilotageTour`, point d'entrée d'E05US010) et **DETTE-020** (libellé de tour à deux
>   domiciles). Recette : [`docs/fonctionnel/E04US018.md`](../docs/fonctionnel/E04US018.md).
> - `E08US005` **rembourser une inscription payée annulée** — US à **surface visible**. Quand une
>   inscription **payée** est effacée (désinscription ou suppression de départ), la somme encaissée
>   devient un **remboursement à traiter** dans un **registre à part** (agrégat/table `remboursement`,
>   migration 0033) : il **survit** à la disparition de l'inscription/du départ, d'où **aucune FK**
>   vers eux — on fige des **instantanés** (nom d'archer, libellé de créneau, montant), comme l'audit
>   fige le nom de l'auteur. La création est **atomique** avec le `DELETE` (nouvelles méthodes de repo
>   `supprimer_avec_remboursement(s)`) : jamais de somme effacée sans contrepartie. Deux issues,
>   **remboursé** ou **reporté** (intention consignée, pas de ré-inscription auto) ; le **traitement**
>   est **audité** (`REMBOURSEMENT`, ADR-0035) et **terminal** (`RemboursementDejaTraite`, 409), tandis
>   que la **création** n'est pas tracée à l'audit — la ligne du registre **est** sa trace datée. La
>   **désinscription payée** devient **confirmable** (`InscriptionPayeeARembourser`, 409 chiffré),
>   comme la suppression de départ (ADR-0018). Décision d'archi tranchée au cadrage :
>   [ADR-0057](../docs/adr/0057-registre-de-remboursements.md). Tests **service depuis le CA** (issues,
>   confirmable, création aux deux déclencheurs) ; repository/API **après**. Oracle 120 vert. Front :
>   onglet **« Remboursements »** de l'écran Paiements + dialogue de confirmation à la désinscription.
>   Story alignée (Notes). Recette : [`docs/fonctionnel/E08US005.md`](../docs/fonctionnel/E08US005.md).
> - `E12US002` **lancer un tour — feu vert + lancement** — US à **surface visible**, la **bascule de
>   tour** du J2 (là où le produit gagne sa valeur). Un écran admin **« Feu vert »** (« Jour J »)
>   montre **en continu**, duel par duel à venir, les trois questions du CA — *participants connus ?*,
>   *cible attribuée ?*, *source amont validée ?* — et **nomme** le blocage (« en attente du duel n°3 »,
>   « cible non attribuée »), jamais un simple drapeau (`P-3`). Un **bouton chiffre** ce qu'il déclenche
>   (« 2 duels · cibles 1 · 4 archers prévenus ») et fait **partir** les duels **prêts** (jouables **et**
>   placés), l'unité lançable étant le **duel** (`D-23`) ; le geste est **recalculé dans la file**, jamais
>   cru sur parole (précédent E12US007), rien de prêt ⇒ 409 `aucun_duel_a_lancer`. **Décision d'archi
>   tranchée** ([ADR-0056](../docs/adr/0056-lancement-d-un-tour-acte-audite-et-diffuse.md)) : le lancement
>   est un **acte audité** (`ActionAuditee.LANCEMENT`) qui **déclenche la diffusion** d'un `LiveEvent`
>   typé post-commit (règle 7) — **aucun statut posé** sur le tableau (reconstruit, ADR-0049). **Périmètre
>   séquencé** (règle 9) : les 3 canaux récepteurs (tablette E04US018, public E07US008, salle E07US004)
>   n'existent pas — le signal **part** mais n'est écouté de façon ciblée par personne ; la cible des
>   tours ≥ 2 attend le placement 1→N (E05US010). `Q-UX6` **partiellement tranchée** (socle du CA livré ;
>   métriques d'exploitation en plus restent à arrêter devant l'écran). Nouveau `ServicePilotageTour`
>   (compose saisie + placement de duels + audit, service→service). Tests **service depuis le CA** (feu
>   vert, chiffrage, filtrage des non-prêts, trace) ; API **après** (câblage, diffusion typée). Oracle 120
>   vert. Front : écran + poll live, logique de présentation pure testée. Story alignée (Notes). Recette :
>   [`docs/fonctionnel/E12US002.md`](../docs/fonctionnel/E12US002.md).
> - `E15US003` **bot pilote automatique pausable + cockpit interactif multi-vues + canal isolé** — US à
>   **surface visible**, **3ᵉ et dernière d'EPIC-15** (close). Un écran admin **« Simulation »** rejoue
>   le tournoi courant **sans rien persister** : un **bot** génère des scores plausibles (déterministes
>   par graine, règle 9) et fait avancer qualif → duels → classement par **pas discrets pilotés côté
>   front** (ADR-0055 §2 : *ticker*, pas de boucle serveur → déterministe et testable). **Session
>   vivante** en mémoire (`ServicePilotageSimulation` + `SessionSimulation` + registre), **hors file
>   d'écriture** — règle 7 intacte, non-pollution **structurelle** (ADR-0054 réutilisé). Trois états
>   gardés `en_cours ⇄ en_pause → terminée` (409 hors état) ; **reprise en main** en pause : l'humain
>   joue la **même unité** que le bot (saisir une volée / désigner un vainqueur). **Générateur de
>   scores** = stratégie **injectable** (règle 1/2), application. **Canal WS isolé** `/ws/simulation`
>   (broadcaster dédié — l'isolement est **structurel**, deux hubs). Refactor : `charger_tournoi_simulable`
>   + `hydrater_harnais` extraits en **source unique** partagée avec le rejeu one-shot (E15US002
>   inchangé). Tests **service depuis le CA** (bot, pause/reprise, reprise en main qualif & duels,
>   déterminisme, non-pollution, garde-fous) ; API/WS **après** (câblage, canal isolé). Oracle 120 vert.
>   **Arbitrage tranché au cadrage** : périmètre **« tout d'un coup »** (bot + cockpit + reprise en main
>   + canal isolé), la reprise en main imposant la session vivante serveur. Story alignée (Notes).
>   Décisions : [ADR-0055](../docs/adr/0055-session-de-simulation-vivante-pilotee-par-pas.md). Recette :
>   [`docs/fonctionnel/E15US003.md`](../docs/fonctionnel/E15US003.md).
> - `E15US002` **moteur de simulation éphémère + garde-fou (non-persistance)** — US **sans surface
>   visible directe** (couche moteur/infra), **2ᵉ d'EPIC-15**, **cœur technique**. Rejoue le moteur
>   (qualif → duels → classement) d'un tournoi **avant démarrage** sur un jeu d'**adapters in-memory**
>   (`infrastructure/memory/`) câblant les **mêmes** services (`ServiceClassement`,
>   `ServicePlacementDuels`, `ServiceSaisieDuels`) et politiques que la production : « ne rien
>   persister » est **structurel** (aucun chemin de ces adapters vers SQLite ni la file d'écriture —
>   règle 7). **Option A** confirmée par le spike (aucun service moteur ne touche la base/la file).
>   **`ServiceSimulation`** (application) ne connaît **aucun** adapter : la composition root lui injecte
>   une **usine de harnais** (règle 8) ; il **hydrate** les repos in-memory par les ports (identifiants
>   préservés) puis fait tourner ses services. **Garde-fou** `SimulationTournoiDemarre` (409) —
>   simulable `brouillon`/`prêt` seulement (arbitrage « terminé/archivé ? » tranché **non**, cohérent
>   avec `PeuplementTournoiDemarre` d'E15US001). **Non-pollution vérifiée** sur **vraie base** (compteurs
>   de lignes inchangés). **Anti-dérive** par **tests de conformité de port** (mêmes assertions
>   SQL ↔ in-memory). **Pas d'API ni d'UI** (substrat pour le cockpit E15US003). Tests service **depuis
>   le CA** ; oracle 120 vert. Décisions : [ADR-0054](../docs/adr/0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md).
> - `E15US001` **jeu d'essai : générer des inscrits + scénarios rejouables** — US à **surface visible**,
>   **1ʳᵉ d'EPIC-15**. Un écran admin **« Jeu d'essai »** (groupe Préparation) : bouton **« peupler N
>   archers »** sur le tournoi courant (données réalistes, N borné [1, 500]) **et** un **catalogue de
>   scénarios** (`petit` 16 · `gros` 120 · `multi-format` 60) qui **instancie un tournoi complet prêt à
>   lancer** (catégories FFTA + départs + archers inscrits → passe `prêt`). **Donnée réelle persistée**,
>   **à distinguer** de la simulation éphémère (E15US002). **Arbitrages tranchés au cadrage** : trio de
>   scénarios figé + destination dédiée + graine optionnelle. **Déterminisme** (règle 9) par
>   `random.Random(graine)` injectée. **Réutilise les services existants** (`ServiceJeuEssai` compose
>   Tournois/Catégories/Départs/Archers/Inscriptions/Clubs — pas de court-circuit du domaine), tout dans
>   **une** commande de file (patron `precharger_ffta`). **Pas d'ADR** (outillage sans nouveau pattern,
>   règle 12). Tests service **depuis le CA** ; API testée après. Story alignée (Notes). Recette :
>   [`docs/fonctionnel/E15US001.md`](../docs/fonctionnel/E15US001.md).
> - `E14US002` **aide contextuelle « ce qui est saisissable et pourquoi »** — US à **surface visible**,
>   **2ᵉ et dernière d'EPIC-14** (close). Sur **chaque** écran d'administration, un bouton **« ⓘ Aide »**
>   replié par défaut se **déplie au tap** pour expliquer, en langage organisateur, ce qui s'y saisit et
>   à quoi ça sert en aval. **Présentation pure** — **aucun** changement domaine/API (note story
>   respectée). **Arbitrages tranchés au cadrage** (CA stub → maquette) : **(1)** couvrir **toutes les
>   ~22 destinations** (pas seulement les écrans de saisie), texte **centralisé** ; **(2)** forme **bouton
>   « ⓘ » déployé au tap**, masqué par défaut — dicté par la contrainte **tactile** (les `title=` au
>   survol ne s'affichent pas au doigt). D'où : un composant unique `AideEcran` (`shared/ui/`, patron
>   comme `MessageErreur`), un dictionnaire `id → texte` (`features/admin/aide-ecrans.ts`, **1 point de
>   vérité**), rendu **une seule fois** en tête de `.coquille__contenu` (la coquille connaît la
>   destination active → zéro édition des 22 features). Textes = **1ᵉʳ jet à relire** avec l'organisateur
>   (signalé dans le fichier). Story alignée (Notes). **Extension à la demande utilisateur** : l'US
>   **outille le test de rendu front** (Testing Library + jsdom, devDependencies MIT, `npm audit` vert),
>   env `jsdom` global + `src/test-setup.ts`, et **1er test de rendu** `AideEcran.test.tsx` — décision
>   structurante, [ADR-0053](../docs/adr/0053-outillage-test-de-rendu-front.md), libs dans
>   [`docs/dependances.md`](../docs/dependances.md) ; sert désormais aux US front suivantes. Recette :
>   [`docs/fonctionnel/E14US002.md`](../docs/fonctionnel/E14US002.md).
> - `E14US001` **accueil-tableau de bord contextualisé par tournoi (`D-20`)** — US à **surface
>   visible**, **première d'EPIC-14** (lisibilité admin). Choisir un tournoi ouvre son **Accueil** :
>   (1) **frise des 7 statuts** (ADR-0026), courant surligné, avec les **boutons d'action** offerts
>   par le statut ; (2) **checklist « à faire »** (réutilise la complétude E12US005) ; (3)
>   **chiffres-clés** — inscrits & réglés (paiements E08US002), postes en ligne (supervision E12US001)
>   — et **alertes** dérivées. **Aucune règle métier nouvelle** (agrège, ne recalcule pas — cadrage).
>   **Arbitrages tranchés au cadrage** (CA stub) : *les 3 briques d'un coup* + *frise à boutons
>   d'action* → d'où l'exposition en **lecture** de la topologie (`transitions_possibles` domaine +
>   `GET …/transitions`, source unique + test de cohérence topologie↔gardes, règle 1). **Bug corrigé
>   au passage** : le front ne gérait que **3 statuts** et se **bloquait** dès `prêt`/`en_pause` (badge
>   muet, aucun bouton) → aligné sur les 7 ; la frise **remplace** l'ancien `CycleDeVie`. Story alignée
>   (Notes). Décisions : [ADR-0052](../docs/adr/0052-accueil-admin-contextualise-par-statut.md).
>   Recette : [`docs/fonctionnel/E14US001.md`](../docs/fonctionnel/E14US001.md).
> - `E01US022` **blason FFTA par défaut par catégorie + affichage hérité** — US à **surface visible**
>   (dernier bug du lot démo). Le pré-chargement FFTA (`precharger_ffta`) crée désormais aussi les
>   **quatre blasons** canoniques du §3 — « Blason 80 cm » / « 60 cm » / « 40 cm » / « Triple 40 cm »
>   — et **relie chaque catégorie au sien** (Classique U11 → 80, U13/U15 → 60, adultes → 40 ;
>   Poulies → triple 40 ; Arc Nu « U18 » → 60, « Scratch » → 40). **Arbitrage de périmètre tranché**
>   (option « preset blasons + défauts + affichage ») : `blason_id` étant une FK vers un blason
>   **existant du tournoi** et E01US005 n'ayant livré **aucun jeu** de blasons, l'US **absorbe** leur
>   pré-chargement (idempotent par nom, réutilise un blason personnalisé de même nom). `taille` =
>   fraction de place (canoniques du placement : 80 → `1.0`, 60 → `0.5`, 40/triple → `0.25`) ; le
>   triple 40 se distingue par ses **zones** (10 → 6 + M, pas de 5 → 1, §4.4). Blasons/liens
>   **modifiables** (template, RG-8). Affichage **lecture** sur `Archers.tsx` (liste) et
>   `NouvelArcher.tsx` (indice sous la catégorie) — **pas** de blason par archer (hors périmètre).
>   Story alignée (Notes). Recette : [`docs/fonctionnel/E01US022.md`](../docs/fonctionnel/E01US022.md).
> - `E03US011` **placement : retour visuel de génération + position A..D côté admin** — US à
>   **surface visible**, correctif **front** (présentation, domaine inchangé). Le bouton
>   **« Générer le plan »** affiche « Génération… » pendant l'appel puis **confirme le résultat**
>   (« Plan prêt » si tous placés ; « Plan généré : N placés, M en réserve » sinon ; « aucun archer à
>   placer » si le départ est vide) — l'échec silencieux diagnostiqué était **muet-mais-ok** (le POST
>   `/regenerer` réussit, seul le retour manquait). Et chaque archer posé affiche sa **position**
>   (lettre A..D, badge accent) sur sa cible **côté admin**, comme côté public — la lettre
>   n'apparaissait que sur les cases **libres**. Recette : [`docs/fonctionnel/E03US011.md`](../docs/fonctionnel/E03US011.md).
> - `E11US008` **accès réseau LAN + QR de rattachement à l'écran** — US à **surface visible**. Le
>   lancement de dev (`run_dev.py`) écoute désormais sur **`0.0.0.0`** comme la release (`--host` pour
>   restreindre), et **affiche l'IP LAN** joignable par les tablettes (réutilise `release.reseau.adresse_lan`).
>   L'écran **Postes de cible** affiche, par cible, son **QR de rattachement** en **image SVG**
>   (vectorielle, agrandissable pour le scan) via un endpoint `GET …/postes/{cible_index}/qr` — rendu
>   `renderSVG` **pur Python**, aucune dépendance ajoutée (PNG/`renderPM` écarté : `rlPyCairo` absent).
>   Endpoint **admin** (le QR encode le code) ; le front le charge en **blob authentifié** (le Bearer
>   admin est en JS, un `<img src>` direct n'emporterait pas le jeton). **DETTE-012** gagne un **2ᵉ
>   consommateur** (même marqueur) et reste **ouverte** ; sa parade — ouvrir l'admin par l'IP LAN —
>   est désormais **atteignable en dev** et **documentée** (`docs/deploiement.md` §6). Recette :
>   [`docs/fonctionnel/E11US008.md`](../docs/fonctionnel/E11US008.md).
> - `E02US010` **horaire de départ `HH:MM` obligatoire & ≥ 1 départ** — US à **surface visible**.
>   L'horaire d'un créneau devient une **vraie donnée temporelle `HH:MM`** (24 h), **obligatoire**,
>   validée **au domaine** (422 ; 400 si le champ manque à la frontière) — le libellé libre
>   d'E02US004 est abandonné ; le front pose un **masque de saisie**. Deux gardes de cohérence :
>   passer un tournoi **`prêt`** exige **≥ 1 départ** (`TournoiSansDepart`, première brique de la
>   complétude de préparation, [ADR-0026] §2), et supprimer le **dernier** départ d'un tournoi
>   **non-brouillon** est **refusé** (`DernierDepartNonSupprimable`). Migration 0032 : reprise
>   best-effort des horaires libres existants → `HH:MM` + colonne NOT NULL. La suppression d'un
>   tournoi non vide reste bloquée par **DETTE-001** (500), rendue systématique par cette US (notée).
>   Recette : [`docs/fonctionnel/E02US010.md`](../docs/fonctionnel/E02US010.md).
> - `E12US008` **cycle de vie d'un départ** — US à **surface visible**. Un créneau porte un **état
>   dérivé** (jamais saisi) : **ouvert** (aucun score) → **lancé** (au moins une flèche validée) →
>   **clos** (toutes les séries closes, barème validé ou forfait). Modifier/supprimer un créneau
>   **lancé/clos** est **signalé et confirmable** (alerte chiffrée, même famille qu'E12US007) ; un
>   créneau **ouvert** reste librement éditable (E02US009 inchangé). État **non stocké** : calculé en
>   réutilisant `ServiceCompletude` via un **port étroit** (comme `LecteurPaiements`). À la
>   suppression, la confirmation de cycle **subsume** celle des inscriptions. Badge d'état + confirmation
>   côté front. Décisions : [ADR-0051](../docs/adr/0051-cycle-de-vie-d-un-depart.md). Recette :
>   [`docs/fonctionnel/E12US008.md`](../docs/fonctionnel/E12US008.md).
> - `E04US015` **gérer abandon / disqualification** — US à **surface visible**. Un acte **scoreur**
>   « déclarer abandon / DSQ », **en qualification comme en duels** ([ADR-0050](../docs/adr/0050-forfait-abandon-et-disqualification.md),
>   qui **fusionne E04US015 + E12US004**). Concept unique `Forfait` **scopé à la phase** : en qualif
>   un **abandon** est relégué en fin de classement (rangé, score affiché), une **DSQ** en est sortie
>   (rang vide, score conservé) ; en duels le forfaitaire **cède** son match (l'adversaire passe). Les
>   **flèches sont préservées** (≠ suppression, ADR-0016) ; l'acte est **daté, attribué, motivé,
>   réversible** (`D-15`) et **audité** (`FORFAIT`). **DETTE-014 résorbée** (la complétude compte un
>   forfaitaire comme « série close »). `Q-UX5` fermée sur le **scoreur**. Recette :
>   [`docs/fonctionnel/E04US015.md`](../docs/fonctionnel/E04US015.md).
> - `E04US013` **écran scoreur (tranche front)** — US à **surface visible**, sous la **même US** que le
>   backend (le compte d'US ne bouge pas). Le scoreur choisit une **phase de tableau**, voit la **liste
>   des duels par tour**, ouvre un duel et le score : **grille de manches** (sets ou cumul selon `mode`,
>   résolu par arme côté serveur — le front n'en décide pas), **barrage** conditionnel (§8.2, désignation
>   manuelle du plus près du centre), **validation** qui verrouille et fait avancer le tableau jusqu'au
>   **podium**. **File hors-ligne + rejeu** dédiée aux actes de duel (2ᵉ occurrence du motif de
>   résilience, **dupliquée** — pas extraite, règle 12). Le **contrat de lecture** des duels a été
>   **enrichi** (pavé exposé dès la lecture : zones du blason, nb de manches/flèches, seuil), analogue à
>   la grille de qualif. Écran monté dans l'**Espace scoreur**. Recette :
>   [`docs/fonctionnel/E04US013.md`](../docs/fonctionnel/E04US013.md).
> - `E04US013` **backend** (saisie en duels) — **sans surface visible** (domaine → moteur → politiques →
>   persistance → service → **API scoreur**). Un **duel** se score au **système de sets** (points de set
>   2/1-1/0, premier à 6 — FFTA ; club 4) ou **au cumul** en arc à poulies (A.7.5.2) ; à égalité, un
>   **barrage** (1 flèche, puis désignation du plus près du centre — l'appli ne mesure pas la distance).
>   Le **vainqueur validé** est transmis au moteur `Tableau.jouer` : le tableau, **non persisté**, est
>   **reconstruit** du classement et **rejoué** des duels validés (seul le **tir** est persisté, table
>   `duel`, migration 0030). Le barème est **résolu par arme** via un **résolveur injecté à défaut FFTA**
>   (E01US011 le configurera — **dépendance sur-affirmée retirée**). Décisions :
>   [ADR-0049](../docs/adr/0049-saisie-et-scoring-des-duels.md).
> - `E03US009` (placer les duellistes côte à côte) — US à **surface visible**. Le placement d'une phase
>   de tableau met les **deux adversaires d'un duel** du 1er tour **côte à côte** « dans la mesure du
>   possible », par ré-ordonnancement de l'entrée du glouton (moteur inchangé, ADR-0048) ; les duels non
>   rapprochés sont **signalés**. Plan **matérialisé par phase** (table `placement_tableau`, migration
>   0029), ajustable au glisser-déposer. Recette : [`docs/fonctionnel/E03US009.md`](../docs/fonctionnel/E03US009.md).

---

## J0 — Walking skeleton — ✅ **terminé (12/12)**

| US | Titre | État |
|---|---|---|
| E00US001 | Initialiser le monorepo | ✅ |
| E00US002 | Configurer la qualité (ruff, mypy, ESLint…) | ✅ |
| E00US003 | CI bloquante | ✅ |
| E00US004 | Squelette de couches + garde-fou d'imports | ✅ |
| E00US005 | Composition root minimale | ✅ |
| E00US006 | SQLite (WAL) + migration initiale | ✅ |
| E00US007 | File d'écriture + writer unique | ✅ |
| E00US008 | WebSocket + diffusion post-commit | ✅ |
| E00US009 | Repository + endpoint bout-en-bout | ✅ |
| E00US010 | Shell React | ✅ |
| E00US011 | Tranche verticale démontrable | ✅ |
| E00US012 | Exécutable de dev (FastAPI sert le front) | ✅ |

## J1 — Tournoi de qualification de bout en bout — ✅ **terminé (46/46)**

| Seq | US | Titre | État |
|---|---|---|---|
| 13 | E01US001 | Créer un tournoi | ✅ |
| 14 | E10US002 | Accès administrateur protégé | ✅ |
| 15 | E10US001 | Consultation publique ouverte | ✅ |
| 16 | E01US002 | Éditer / lister les tournois | ✅ |
| 17 | E01US003 | Gérer les catégories (CRUD) | ✅ |
| 18 | E01US004 | Pré-charger les catégories FFTA salle | ✅ |
| 19 | E01US013 | Catégorie : éligibilité multi-âges | ✅ |
| 20 | E01US005 | Gérer les blasons | ✅ |
| 21 | E01US014 | Blason : valeurs de score admises | ✅ |
| 22 | E01US006 | Associer catégorie ↔ blason | ✅ |
| 23 | E01US007 | Définir un gabarit de salle | ✅ |
| 24 | E01US008 | Réutiliser / ajuster un gabarit | ✅ |
| 25 | E01US009 | Définir un barème de qualification | ✅ |
| 26 | E01US015 | Grain de validation d'une phase | ✅ |
| 27 | E01US010 | Définir le tarif par départ | ✅ |
| 28 | E02US001 | Gérer le référentiel clubs | ✅ |
| 29 | E02US002 | Créer un archer | ✅ |
| 30 | E02US003 | Éditer / supprimer un archer | ✅ |
| 31 | E02US004 | Configurer les départs (créneaux) | ✅ |
| 32 | E02US009 | Inscrire un archer sur des départs | ✅ |
| 33 | E00US014 | Outiller les tests du front | ✅ |
| 34 | E08US001 | Calculer le montant dû | ✅ |
| 35 | E03US001 | Placement automatique & plan de cibles | ✅ |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) | ✅ |
| 37 | E10US003 | Scoreurs : définition & session | ✅ |
| 38 | E09US008 | Imprimer QR de cible & codes scoreurs | ✅ |
| 39 | E04US001 | Rattacher une tablette à sa cible (QR) | ✅ |
| 40 | E10US007 | Poste de cible : saisir sans s'identifier | ✅ |
| 41 | E04US002 | Saisie de qualification en temps réel | ✅ |
| 42 | E04US009 | Diffusion live & résilience réseau | ✅ |
| 43 | E12US001 | Superviser les postes de saisie | ✅ |
| 44 | E06US001 | Classement de qualification | ✅ |
| 45 | E07US001 | Vues publiques : classements, plans, live | ✅ |
| 46 | E07US006 | Suivre des archers : ma journée *(tranche 1, front)* | ✅ |
| **46b** | **E07US009** | **Suivre le déroulé du tour en direct** *(tranche 2, backend + ADR)* | ✅ |
| 47 | E10US005 | Journal d'audit métier | ✅ *(fait en avance)* |
| 48 | E12US007 | Alerter par calcul d'impact | ✅ |
| 49 | E08US002 | Suivi des paiements | ✅ |
| 50 | E12US005 | Afficher la complétude du tournoi | ✅ |
| 51 | E12US006 | Rechercher un archer depuis n'importe où | ✅ |
| 52 | E02US005 | Détecter et fusionner les doublons | ✅ |
| 53 | E02US006 | Contrôler les quotas | ✅ *(fait en avance)* |
| 54 | E09US001 | Socle PDF & feuille de marque | ✅ *(fait en avance)* |
| 55 | E09US003 | Listes imprimables (placement, club, paiement) | ✅ |
| 56 | E11US001 | Release, base et mise en réseau | ✅ |
| 57 | E11US003 | Sauvegarde & archive | ✅ |

## J2 — Duels simples + bascule de tour — ✅ **terminé (14/14)**

| Seq | US | Titre | État |
|---|---|---|---|
| 58 | E05US001 | Séquence de phases | ✅ |
| 59 | E05US003 | Politiques injectables & assemblage | ✅ |
| 60 | E05US005 | Arbre d'élimination directe *(moteur sur `Participant`)* | ✅ |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible | ✅ |
| 62 | E03US009 | Placer les duellistes côte à côte | ✅ |
| 63 | E04US013 | Saisie en duels | ✅ *(backend + API + écran scoreur)* |
| 64 | E04US015 | Gérer abandon / disqualification | ✅ *(qualif + duels, ADR-0050)* |
| 65 | E12US004 | ~~Tracer un forfait~~ | ⛔ *(absorbée par E04US015)* |
| 66 | E12US008 | Cycle de vie d'un départ | ✅ *(état dérivé + garde-fou confirmable, ADR-0051)* |
| 67 | E08US005 | Rembourser une inscription payée annulée | ✅ *(registre de remboursements, ADR-0057)* |
| 68 | E12US002 | Lancer un tour (feu vert + lancement) | ✅ *(feu vert + lancement-événement, ADR-0056)* |
| 69 | E04US018 | Afficher la prochaine cible après validation | ✅ *(panneau de routage, canal n°1)* |
| 70 | E07US008 | Vue publique des affectations du prochain tour | ✅ *(canal n°2 : téléphone + panneau collectif, rang en fourchette, issue « repêché », ADR-0065)* |
| 71 | E06US003 | Barrage de tir pour places décisives | ✅ *(seuil dans la politique `tiebreak`, manches persistées, verdict recalculé, ADR-0066)* |
| 72 | E06US004 | Podium des duels & agrégation des rangs | ✅ *(palmarès : fusion des rangs de phases, podiums par catégorie, export PDF, politique `aggregation`, ADR-0067)* |

## J3 — Placement intégral 1→N + écran de salle — 🔶 **en cours (11/13)**

| Seq | US | Titre | État |
|---|---|---|---|
| 73 | E05US010 | Placement intégral 1→N **& peuplement multiple** | ✅ *(routing générique + cascade, sources multiples, oracle 120, ADR-0061 ; absorbe E05US018, résorbe DETTE-015)* |
| 74 | E05US015 | **Catalogue de types de phase** (échauffement, barrage, poules, repêchage, BSO) | ✅ *(11 formats : + suisse, colline, handicap, finale spectacle — le commanditaire a fourni leurs règles le 31/07 ; ADR-0062)* |
| 74bis | E01US024 | **Composer, diagnostiquer et simuler un déroulé** | ✅ *(brouillon + invariant déplacé vers `appliquer`, schéma SVG maison, 2 gravités d'anomalie, simulation composée sur ADR-0054/0055 ; ADR-0063 — résorbe DETTE-030, ne résorbe DETTE-028 qu'à moitié)* |
| 74ter | E01US025 | **Le départ est la portée sportive** + le déroulé se définit **une fois** | ✅ *(corrige [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md), resté **13 mois** sans portage dans le moteur : 4 départs de 100 rendaient UN classement de 400. `Phase`/`BarrageDePlaces` pendent au départ, `EtapeDeroule` porte la définition au tournoi ; migrations 0042/0043 ; garde-fou mécanique `test_portee_sportive.py` ; ADR-0075 + ADR-0076. ⚠️ **fiche écrite après coup**, US prise hors tracker — CA de non-régression, pas oracle. Ouvre DETTE-044/045/046, aggrave DETTE-025/026. **Reliquat de revue soldé le 07/08** : portée départ appliquée au suivi du déroulé, aux tableaux publics, au routage jour J et au contrôle d'effectif ; migrations 0042/0043 rendues réversibles ; cloisonnement du barrage ; décors de test passés à **deux créneaux**)* |
| 75 | ~~E05US018~~ | ~~Oracle 120~~ → **absorbée par E05US010** | ⬜ *(le moteur et sa preuve ne se séparent pas)* |
| 76 | E06US006 | **Classement intégral 1→N & profondeur configurable** | ✅ *(la profondeur se règle **par phase** et non plus au câblage ; absence = preset du type, podium pour une élimination directe et intégral pour un placement — ADR-0070, DETTE-035 ouverte)* |
| 76bis | E05US020 | **Le moteur consomme les prélèvements déclarés** | ✅ *(cœur de DETTE-028 : prélèvement par rangs honoré, plage relative résolue, tranche de rangs au palmarès — DETTE-034 soldée, ADR-0068)* |
| 76ter | E05US021 | **Un format connaît son effectif minimum** (avertir avant de lancer) | ✅ *(minimum **déduit** des prélèvements, exigence de club au-dessus, refus au démarrage + annonce avant le clic — ADR-0069)* |
| 76quater | E05US024 | **Un prélèvement lit le classement de sa phase source** | ✅ *(reste de `DETTE-028` sur les rangs **résorbé** : poules→tableau, tableau→consolante, cascade récursive sur un graphe acyclique ; un tableau se lit comme un classement, fourchettes *ex æquo* fermées par la politique `aggregation` (ADR-0067) et non par un départage local qui aurait contredit le palmarès ; le plancher d'inscrits remonte la chaîne et refuse de chiffrer une fenêtre amont plafonnée. Le « cycle » invoqué par E05US020 pour reporter ce cas **n'existait pas** — récursion, pas cycle de modules : une justification de report se re-vérifie à la reprise. [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md))* |
| 76quinquies | E05US025 | **Plusieurs qualifications dans un même déroulé** | ⬜ 🎯 *(**dépend d'E05US024**, nécessairement : sans peuplement générique, une 2ᵉ qualification recevrait *tous* les inscrits. L'unicité (`_anomalies_unicite_qualification`, E05US021) n'est **pas une règle métier** — sa docstring la dit « supposée partout et vérifiée nulle part », posée pour fermer un bug plutôt que pour exprimer une règle du tir à l'arc. Reste à faire : les **lecteurs**, pas le peuplement — `ServiceBaremeQualification` est bâti sur « **le** barème du tournoi », et les 12 appels de `portee.qualification_du_tournoi` (terrain `DETTE-048`) sont à trier un par un. **ADR attendu** ; 3 points à trancher au cadrage, listés dans la story)* |
| 77 | E03US007 | **Contrainte séparation catégorie/blason** | ✅ *(réglage de tournoi à 4 positions, contrainte **dure** au placement auto **et** au glisser-déposer, **sur les deux plans** (cibles et duels), raison de réserve propre `cloisonnement`, cibles non conformes signalées — ADR-0071, DETTE-036/037 ; tranche la priorité des contraintes restée ouverte à EPIC-03)* |
| 78 | E09US005 | Classements PDF | ⬜ *(rétrécie par E06US004 : le **palmarès** a son PDF ; reste celui du classement de **qualification**)* |
| 79 | E00US013 | Factoriser les briques d'UI partagées | ✅ *(remontée de J3, DETTE-004 résorbée)* |
| 80 | E01US016 | Définir l'identité visuelle du tournoi | ⬜ |
| 81 | E07US004 | Écran de salle **+ suivi du déroulé** (un composant, trois surfaces) | ✅ *(poste typé cible/écran, pilotage par état lu, suivi superposé — ADR-0064)* |
| 82 | E07US005 | **Vue tableaux/arbres live** | ✅ *(onglet public « Tableaux » à deux lectures — « Mon chemin » par archer suivi et tableau complet par tour —, DTO public restreint, vue `tableaux` de l'écran de salle : le catalogue d'ADR-0064 couvre enfin son CA en entier ; DETTE-031 élargie)* |
| 83 | ~~E05US019~~ | ~~Enregistrer une séquence comme modèle~~ → **livrée par E01US023** | ✅ *(doublon repéré le 31/07 : ADR-0060 §5)* |
| — | E00US015 | Ossature de navigation admin (coquille) | ✅ *(fait en avance — ajout 18/07)* |

## J4 — Confort, richesse & robustesse — ⬜ **non commencé (0/8)**

| Seq | US | Titre | État |
|---|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc | ⬜ |
| 85 | E01US011 | Presets de barèmes multi-phases | ⬜ |
| 86 | E01US012 | Gérer plusieurs gabarits | ⬜ |
| 87 | E03US010 | Générer / éditer le déroulé horaire | ⬜ |
| 88 | E09US007 | Déroulé horaire imprimable | ⬜ |
| 89 | ~~E05US016~~ | ~~Routing repêchage (WA)~~ → **absorbée par E05US015** | ⬜ |
| 90 | E11US006 | Restauration & arrêt propre | ⬜ |
| 91 | E10US006 | Modifier le mot de passe admin | ⬜ |

## Ajouts de l'entretien du 18/07/2026 — 🔶 **en cours (4/10)**

> Non renumérotés dans les jalons ci-dessus (séquence indicative, à insérer au bon rang). Cf.
> [`stories/README.md`](../stories/README.md) § « Ajouts » et ADR-0026/0027/0028.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US015 | Coquille de navigation admin | J3 | ✅ |
| E00US016 | Écrans admin : liste/fiche & référentiels | J3 | ⬜ *(définie en `stories/`, non implémentée)* |
| E01US017 | Cycle de vie enrichi (7 statuts) | J1 | ✅ |
| E01US018 | Vocabulaire de score configurable | J1 | ⬜ *(idem)* |
| E01US019 | Capacité de cible non bornée | J1→J3 | ⬜ *(idem)* |
| E02US010 | Horaire de départ HH:MM obligatoire | J1 | ✅ |
| E13US001 | Abstraction participant | J2 | ✅ *(livrée avant E05US005, ADR-0028)* |
| E13US002 | Composer les équipes d'un tournoi | J2 | ⬜ |
| E13US003 | Scoring d'équipe (politique injectable) | J2 | ⬜ |
| E13US004 | Placement, saisie & classement par équipe | J2→J3 | ⬜ |

## Ajout du 20/07/2026 — ✅ **livrée (1/1)**

> Issu de l'échange sur le modèle d'entrée de l'appli (une seule SPA, désormais **quatre** expériences).
> Cf. [`stories/E00-socle.md`](../stories/E00-socle.md) § E00US017 et [ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md).
> Livrée le 21/07 : écran de choix 4 portes (Tablette / Public / Scoreur / Admin), choix persistant,
> le public ne peut pas escalader, échappatoire « Changer de rôle » ; front seul.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US017 | Écran d'accueil : choisir son appareil / rôle | J3 | ✅ |

## Ajout du 21/07/2026 — ⬜ **à planifier (0/2)**

> Issus du cadrage d'E08US002 : la tarification devient une **configuration du tournoi**
> ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)). Ouverture **décidée**, pas
> codée — seule « somme des tarifs de l'archer » est implémentée. Cf. [`stories/E01-configuration.md`](../stories/E01-configuration.md).

| US | Titre | Jalon | État |
|---|---|---|---|
| E01US020 | Modèle de tarification injectable & sujet de facturation (archer/club) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; sujet `club` sur `club_id`/ADR-0014, **pas** via E13)* |
| E01US021 | Tarification dégressive (option config, %/montant) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; dépend d'E01US020)* |

## Ajouts de la démo du 27/07/2026 — ✅ **traités (10/10)**

> Retours de la présentation au client final **et** du développeur (27/07/2026). Cadrage par le
> dialogue (esprit agile). Deux US **déjà spécifiées** remontent en priorité (♻️, pas de doublon) ;
> les autres sont **neuves** (🆕). **Bugs d'abord**, puis EPIC-14 (accueil admin) et EPIC-15 (jeu
> d'essai & simulation). Détail des US : `stories/Exx-*.md`. Épics :
> [`EPIC-14`](../epics/EPIC-14-lisibilite-admin.md), [`EPIC-15`](../epics/EPIC-15-jeu-d-essai-simulation.md).

| US | Titre | Épic | État |
|---|---|---|---|
| E02US010 | Horaire de départ `HH:MM` (corrige « 8h00 → 18h00 » : n° collé à l'horaire) | E02 ♻️ | ✅ |
| E01US017 | Cycle de vie enrichi (7 statuts) — **prérequis** du dashboard | E01 ♻️ | ✅ |
| E11US008 | Accès LAN (poste organisateur) + QR de rattachement à l'écran | E11 🆕 | ✅ |
| E03US011 | Placement : retour visuel de génération + position A..D côté admin | E03 🆕 | ✅ |
| E01US022 | Blason FFTA par défaut par catégorie + affichage hérité | E01 🆕 | ✅ |
| E14US001 | Accueil-tableau de bord contextualisé (`D-20`) | E14 🆕 | ✅ |
| E14US002 | Aide contextuelle « ce qui est saisissable & pourquoi » | E14 🆕 | ✅ |
| E15US001 | Jeu d'essai : générer des inscrits + scénarios rejouables | E15 🆕 | ✅ |
| E15US002 | Moteur de simulation éphémère + garde-fou (non-persistance) | E15 🆕 | ✅ *(rejeu in-memory, ADR-0054)* |
| E15US003 | Bot pilote auto pausable + cockpit interactif multi-vues | E15 🆕 | ✅ *(session vivante + canal isolé, ADR-0055)* |
| E14US003 | Admin rangée en **trois axes d'activité** + une adresse par rôle | E14 🆕 | ✅ *(ADR-0058 révise `D-19` ; ADR-0059 remplace ADR-0032)* |
| E01US023 | Les briques de l'atelier deviennent le **patrimoine du club** (bibliothèque, copie, promotion) | E01 🆕 | ✅ *(ADR-0060 ; DETTE-023 résorbée ; brique `FormatTournoi` ajoutée)* |

## Fidélité aux maquettes (EPIC-17) — 🔶 **en cours (4 US livrées)**

> Amener le **produit** jusqu'aux maquettes, là où [`E16`](../stories/E16-retours-maquettes.md) traite
> les retours *sur* les maquettes. Cf. [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md),
> qui rend les planches **opposables** en revue.

| US | Titre | Jalon | État |
|---|---|---|---|
| E17US001 | Poser la **charte du club** dans l'application | J1 | ✅ *(ADR-0074 ; `--warn`/`--ok`/`--accent` supprimés, garde-fou `charte.test.ts`)* |
| E17US002 | Le **catalogue de composants** adopte les formes des planches | J1 | ✅ *(vérifié au navigateur ; densité **non** reprise — arbitrage A02)* |
| — | **Relevé d'écarts des 19 planches admin** | — | ✅ *(dans [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) ; 6 planches hors périmètre, 3 variantes écartées, 5 écrans sans tableau)* |
| E17US003 | A01 **connexion** + A02 **accueil des axes** conformes à leur planche | J1 | ✅ |
| E17US004 | A13 **supervision en grille de tuiles** (variante B retenue) | J2 | ✅ *(écran du jour J ; IP + révocation conservées)* |
| — | Embarquer **Inter** pour le jour J (`DV-07`) | J3 | ⬜ *(**arbitrage d'actif en attente** — règle 11)* |
| — | Confronter les 19 planches `A**`, 9 `S**`, 7 `P**` aux écrans livrés | J3 | ⬜ |

## Résorptions de dette planifiées (arbitrages du 07/08/2026)

> Quatre questions ouvertes du registre ont été **tranchées par le commanditaire** à la revue
> d'E01US025. Elles ne sont pas dans le jalon courant : elles sont ici pour que « reprend les US »
> les retrouve, et parce qu'une décision non planifiée se reperd.

| US | Titre | Résorbe | État |
|---|---|---|---|
| E05US023 | **Rendre jouables** poules, suisse, colline, Big Shoot Off — **et composables à l'atelier** | `DETTE-028` | ⬜ *(**« au plus tôt dans le backlog »** — priorité donnée par le commanditaire ; **à découper**, 4 moteurs × 2 surfaces ne tient pas dans une branche)* |
| E06US009 | Un palmarès **par départ, juxtaposés** | `DETTE-045` | ⬜ *(arbitrage rendu : « 4 départs = 4 podiums », donc **aucune** agrégation inter-départs à écrire)* |
| E01US026 | Supprimer un tournoi : **signaler puis confirmer** | `DETTE-001` | ⬜ *([ADR-0077](../docs/adr/0077-supprimer-un-tournoi-signaler-puis-confirmer.md) — étend ADR-0016 ; ferme la **plus ancienne** dette du registre et le `xfail` d'E02US010)* |
| E05US022 | Ancrer la séquence sur **l'identité** de l'étape | `DETTE-026` | ⬜ *([ADR-0078](../docs/adr/0078-la-sequence-s-ancre-sur-l-identite-de-l-etape.md) — seuil de la règle 16 **dépassé** : 4 écrivains ; allège aussi `DETTE-025`)* |

⚠️ **`DETTE-044` (`NewType` sur les identifiants) n'a pas d'US** et reste sans arbitrage requis :
c'est elle qui a rendu tout le reste invisible pendant E01US025 — la bascule de portée n'a produit
que 10 erreurs mypy, le **renommage** des méthodes de port en a révélé 157 de plus, toutes des
appels compilables et faux. À prendre avant la prochaine US qui touche une portée.

## US caduque

| US | Titre | Motif |
|---|---|---|
| E10US004 | ~~Habiliter un scoreur sur plusieurs cibles~~ | Sans objet depuis `D-12`/`D-13` (scoreur itinérant). Conservée comme trace. |

---

## Légende

- ✅ mergé sur `main` · 🎯 prochaine US à prendre · 🔶 jalon en cours · ⬜ à faire
- *« fait en avance »* : US traitée avant son rang de séquence (dépendance ou opportunité).
- *« définie en `stories/`, non implémentée »* : le fichier de spec existe (créé à l'entretien du
  18/07) mais aucun code n'est livré — ne pas confondre présence en `stories/` et US faite.
