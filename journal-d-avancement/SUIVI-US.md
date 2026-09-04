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

**Dernière mise à jour : 04/09/2026, 10 h 15** · **133 US livrées** · dernière : `E16US017`
*(**le trophée du club le plus performant** — les clubs se classent enfin **entre eux**, au **décompte de médailles** : l'or d'abord, puis l'argent, puis le bronze, l'ordre olympique. Un tableau de plus au palmarès, sur les **quatre** surfaces (écran d'admin, appli publique, écran de salle, PDF). ⚠️ **Trois arbitrages tranchés au cadrage**, dont un que la fiche laissait ouvert : l'or décerné deux fois — *scratch* **et** *catégorie* cumulés — **compte deux fois**, le décompte collant ainsi aux médailles réellement remises ; la portée *club* est **exclue** du décompte, puisqu'elle décerne un or à l'intérieur de chaque club, donc à tous — et sans portée inter-club le classement **n'existe pas**, ce que l'écran **dit** au lieu d'afficher tout le monde à égalité ; enfin trois métaux seulement, la 4ᵉ place du podium par défaut ne rapportant rien. Aucun effectif minimum, *ex æquo* à décompte égal, un archer sans club n'apportant sa médaille à personne (ADR-0014). [ADR-0104](../docs/adr/0104-le-classement-des-clubs-se-compte-en-medailles-inter-clubs.md) ; la garde d'`E16US014` sur la lecture du référentiel des clubs **tombe** — il faut désormais les **nommer** dès qu'une portée inter-club est réglée ; `DETTE-029` gagne un **5ᵉ site**, ligne élargie plutôt que contournée)*. Précédente : `E16US014` *(**choisir ce que le tournoi récompense** — le palmarès n'impose plus son découpage : trois
portées **cumulables** (toutes catégories · par catégorie · par club) et un **nombre de places**
réglable, d'un seul réglage pour l'écran d'admin, l'appli publique, l'écran de salle et le PDF
([ADR-0103](../docs/adr/0103-la-portee-d-un-podium-est-un-reglage-du-tournoi.md), migration `0052`).
Les défauts serveur **sont** le comportement d'E06US004 : aucun tournoi déjà en base ne change
d'affichage. ⚠️ **La fiche a été coupée en deux au cadrage** : classer les **clubs entre eux** est un
classement neuf et non un regroupement — `E16US017`, au décompte de médailles. ⚠️ **Deux bloquants
en revue**, dont un défaut de conjonction que quatre axes ont relevé : le filtre par catégorie
rognait les podiums, jusque sur le PDF du mur. ⚠️ **« Pas d'ADR » était faux** — le « patron déjà
posé » invoqué au commit était le cloisonnement, qui portait lui-même ADR-0071 ; ADR-0067 § Décision 5
a dû être amendé, le glossaire et le modèle de données réalignés)*

**Précédente : `E00US027`**
*(**le code porte des pointeurs, pas le raisonnement** — une règle d'écriture, née des **trois
passes de revue** d'`E16US009` et de la question qu'elles ont provoquée. Sur les 12 majeurs de la 3ᵉ
passe, **un seul** portait sur du code : les autres étaient des documents qui se contredisent, dont
des commentaires que **rien ne vérifie**. Un commentaire ne survit donc qu'à trois conditions —
**contrainte non déductible**, **avertissement**, ou **renvoi d'une ligne**
([ADR-0099](../docs/adr/0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md), règle 13) ; le
reste vit déjà ailleurs. ⚠️ **On ne coupe que ce qui existe ailleurs** : le décompte de chrome du
plafond de pages, qui ne vivait que dans un commentaire, a été **déplacé** dans `DETTE-086` avant
d'être retiré. Après un lot démonstratif de 5 fichiers, l'US a été **élargie au dépôt entier** sur
arbitrage du 27/08/2026 : **1 086 blocs backend** et **453 blocs front** (236 fichiers) ramenés sous
un plafond de **huit lignes par bloc**, désormais vérifié des deux côtés par pytest et vitest.
Aucune ligne exécutable modifiée — vérifié jeton à jeton sur 437 fichiers.)*

**Avant elle : `E16US009`**
*(**l'écran de salle se règle, et montre tout le monde** — la cadence de défilement et le nombre de
noms par page se règlent par écran, et le classement projeté garde ses trois premiers en tête
pendant que le reste tourne page par page.)*

**Encore avant : `E16US006`**
*(**le tournoi porte ses couleurs et ses logos** — deux logos facultatifs, celui de l'**édition** et
celui du **club organisateur**, et deux couleurs d'accent dont le système **dérive** seul l'aplat, le
contour et la variante de texte, en thème sombre **et** clair. L'habillage porte sur l'**écran de
salle** et l'**appli publique** ; jamais sur l'admin ni la saisie (`D-27`). ⚠️ **Cette US en absorbe
une autre** : `E01US016` (identité visuelle) était ⬜, et « un second logo » n'avait pas de sens sans
le premier — fusion arbitrée au cadrage du 25/08. Migration `0050`,
[ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md), `Q-UX10` et `Q-UX11`
fermées. ⚠️ **127 fiches closes, mais 126 livraisons** : `E16US006` **absorbe** `E01US016`, et les
deux sont passées à ✅ dans le même diff. Le compteur mécanique — recalculé par l'atlas — compte des
**fiches**, pas des branches ; le noter plutôt que de forcer le chiffre à la main.)*

**Précédente : `E16US005`**
*(**le plan de cibles tient sur la largeur d'un PC** — une **cible par ligne**, couloirs côte à côte
et alignés d'une bande à l'autre, au lieu d'une mosaïque de vignettes de 160 px. La largeur gagnée
porte, sous chaque nom, **club · catégorie · blason** : soit exactement ce qui décide des deux badges
que le serveur posait déjà au niveau **cible** — « mixité non garantie », « cloisonnement non
respecté » — et qui désignaient un problème sans dire **lequel** des quatre occupants le causait. La
**réserve** devient un panneau latéral collant, et le **plan de duels** suit dans le même diff.
⚠️ **Deux CA sur trois étaient déjà tenus** par `E03US004`/`E03US007` ; le reliquat « position »
annoncé n'existait pas. **Front seul, aucune migration.** `DETTE-085` et `DETTE-086` inscrites ;
⚠️ **angle mort assumé** : l'écran n'a jamais été vu, toutes les largeurs sont calculées.)*

**Précédente : `E16US012`**
*(**l'appli dit ce qui manque avant le clic** — l'écran « **Prêt à démarrer ?** » énumère d'un coup
tout ce qui retient le lancement (créneaux, inscrits, déroulé), là où les gardes ne rendaient qu'un
manque à la fois, **au clic** : une exception s'arrête au premier rencontré. Il inaugure la
**famille « prêt à… »** — forme **unique paramétrée** par le jalon, tranchée au cadrage : un type de
réponse, une route, une coquille front ; « Prêt à terminer ? » y est migré, à rendu inchangé
([ADR-0096](../docs/adr/0096-un-jalon-enumere-ses-gardes-au-lieu-de-les-lever.md)).
⚠️ **Un CA manquait**, trouvé en écrivant les tests : « question binaire » et « avertir sans
bloquer » (`D-15`) exigent **deux** drapeaux, `pret` et `bloquant` — un tournoi sans déroulé composé
démarre. ⚠️ **Les quatre membres ne sont pas homogènes** : trois gardent une transition, *exporter*
un geste répétable. **Aucune migration.** `archiver` et `exporter` restent à instruire.)*

**Précédente : `E16US002`**
*(**nommer ses phases** — le **dernier des quatre écrans refusés** au questionnaire du 04/08/2026 est
levé, la série 🔴 est vide. Une étape du déroulé porte un **titre** (libellé, pas identité : ni
unique, ni obligatoire, et il survit à un retypage), chaque ligne ouvre **sa** fiche au lieu
d'empiler tous les réglages à l'écran — la **qualification** en gagne une, elle n'en avait aucune et
était le seul type impossible à nommer —, et les deux destinations de composition cessent de porter
**chacune le mot de l'autre** : « Phases du tournoi » et « Composer un format »
([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md)).
⚠️ **Le recadrage a RÉDUIT l'US**, à rebours du pronostic : les cinq fiches de réglages étaient déjà
livrées par les six US de formats. `DETTE-080` inscrite ; une duplication **fermée** sur preuve
(`configInchangee`, deux bugs déjà payés).)*

**Avant elle : `E05US027`**
*(**la colline jouable** — 4ᵉ et **dernière** tranche du découpage d'`E05US023`. Le format à défis
du club (*King of the Hill* / *Ladder*) se règle à l'atelier, se joue manche après manche au pavé de
duel, s'affiche au public et sur l'écran de salle. Livrée **de bout en bout en une seule branche**,
à la différence du suisse qui avait dû être coupé en deux (arbitrage du commanditaire au cadrage).
`DETTE-028` est **refermée sur son volet « moteurs de formats sans appelant »** : les quatre moteurs
d'E05US015 ont tous leur consommateur, et il ne reste plus aucun format en attente.
⚠️ **La dette ne se referme pas pour autant, et c'est dit au registre** : `ScoreAvecHandicap` et
`RoutingRepechage` restent inertes, `classement.py` ne passe toujours pas par la famille `scoring`.
Le volet **politiques** subsiste, sans US inscrite — le barrer eût été la sur-promesse type.
⚠️ **Six garde-fous posés par les tranches précédentes sont tombés, et ont été retournés** plutôt que
contournés : le test de simulation (`DETTE-066`) est tombé **dès la bascule du registre**, avant
qu'une ligne de simulation soit touchée — le 4ᵉ retrait manuel a donc été posé en connaissance de
cause. Deux autres (plancher d'inscrits, bandeau de réserve) se déplacent sur `placement` et
**cessent enfin de se déplacer** : ils suivaient le dernier format non livré, ils ont désormais un
porteur durable.
⚠️ **`DETTE-064` vérifiée quatre fois sur quatre** : le réglage a encore été oublié dans les deux
helpers de décor, et **onze** tests d'API ont échoué en `phase_pas_reglee` sur une phase parfaitement
réglée. Le piège ne se déclenche pas « parfois », il se déclenche **toujours**.
⚠️ **Le CA « réglages à l'atelier » n'était pas tenu par la 1ʳᵉ tranche** — aucune route ne posait de
réglage —, et c'est en relisant `DETTE-054` que le manque s'est vu : 8ᵉ paire de DTO jumeaux.
✅ **Le rendez-vous de la revue d'E05US030 est tenu** : `etatRencontre`, écrite deux fois à
l'identique, remonte en `shared/` au lieu d'être recopiée une 3ᵉ fois.
⚠️ **Un point de règle ouvert depuis le 31/07/2026 est tranché** : l'exemple chiffré du Ladder
contredit sa propre règle ; c'est **la règle** qui fait foi (les deux archers échangent leurs
places). Reversé à `stories/`, au référentiel §10.1 et à `docs/fonctionnel/E05US015.md`.
**Aucune migration** — le réglage vit à la racine du `config` JSON d'étape.)*
<!-- Entrée précédente, conservée pour mémoire :
*(**la salle peut s'arrêter, et repartir d'un bouton** : l'organisateur pose à l'atelier une **liste**
de pauses par phase (« après le tour 2, après le tour 5 »), chacune de portée *cette phase seule* ou
*tout le créneau*. Un arrêt atteint met la phase en `EN_PAUSE` **toute seule** — statut existant,
ADR-0045 : c'est le déclencheur qui est neuf, pas l'état —, l'archer lit « en attente » au lieu de
recevoir une cible, et un admin relance **d'un seul geste** toutes les phases qu'un même arrêt a
coupées. Un arrêt de créneau **ne coupe personne en plein tir** : chaque phase finit d'abord son tour
en cours. Une **correction** de score reste possible pendant la pause. ⚠️ **Tranche A d'un découpage
en deux** décidé au cadrage : la fiche portait 13 CA à travers modèle, migration, moteur et quatre
écrans. `E05US034` livrera la **lisibilité** (mention publique de la pause, pastille de rappel, arrêt
posé le jour J) et elle est **bloquante avant tout déploiement réel** de la capacité.
⚠️ **Le postulat central de la fiche était faux** : elle listait « `EN_PAUSE` gèle la validation »
parmi ses *pièges à vérifier*, or `EN_PAUSE` ne gelait **rien** — la pause était cosmétique, et la
docstring de `ServiceTournois.mettre_en_pause` documentait le contraire. Corrigé pour la **phase** ;
le volet **tournoi** part au registre en `DETTE-073`, majeur. ⚠️ **Une pause ne se pose que sur un
type dont l'application lit le tour** — élimination directe, poules, suisse, Big Shoot Off : la
qualification a été **sortie du périmètre en fin de revue**, son avancement demandant de résoudre sa
population réelle (ADR-0082), le plan de cibles et les forfaits. Reprise par `E05US034`.
[ADR-0091](../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md), migration
`0048` (le **franchissement** seul — la définition passe par le JSON d'étape, sans migration).)*
-->

Précédente : `E05US034`
<!-- Entrée précédente, conservée pour mémoire :
*(**le public voit enfin les trois formats sans arbre** : l'onglet « Tableaux » devient **« En
cours »** et montre la phase qui se joue quel qu'en soit le format — poule, ronde de système suisse,
manche de Big Shoot Off, arbre de duels. L'onglet **atterrit** sur la phase en cours et laisse
**remonter tout le déroulé du départ**. Le **Big Shoot Off** reçoit la route publique qui lui
manquait. `VueEcran.TABLEAUX` → `EN_COURS`, migration `0047`. ADR-0089, qui **révise** ADR-0064.)*
*(**le système suisse à l'écran** : le moteur livré le matin même par `E05US026` devient jouable par
un humain — nombre de rondes réglable avec la **borne d'effectif affichée en clair**, saisie **ronde
par ronde** au pavé de duel, attente nommée tant que la ronde en cours n'est pas close, **classement
provisoire** (points, Buchholz) entre les rondes, pose du plan de cibles. **`DETTE-056` refermée**.
Le cadrage a produit **deux US neuves**, `E05US031` (livrée ici) et `E05US032`.)*
-->

Précédente : `E05US031`
<!-- Entrée précédente, conservée pour mémoire :
*(**la carte du code** : l'atlas lit désormais le **code** et plus seulement les documents. La
matrice de dépendances est lue à l'**AST**, et une couche qui remonte le courant fait **rougir la
CI** — la règle 2 n'était vérifiée que pour le domaine, les quatre autres sens ne l'étaient par
rien. Les 60 ports sont appariés **structurellement** à leurs adapters. Côté front, la mesure a
trouvé **3 nœuds de features enchevêtrées**, dont un de **19 sur 44** : quatre chantiers en sont
nés, inscrits au backlog sans être pris. Élargit `DETTE-067`, dont le déclencheur est franchi.
Deux tranches d'atlas restent.)*
-->

Précédente : `E00US019`
*(**l'avancement, et des livrables de suivi qui ne se contredisent plus** : l'atlas montre les US
section par section avec leur état, l'ordre des epics en un schéma, la dette ouverte, et une fiche
par US qui rapproche les quatre sources. Surtout, il **recalcule** chaque compteur et **bloque** la
CI sur un écart. Il a trouvé trois défauts réels le jour même : le compteur J3 faux, deux US
livrées qui n'existaient que dans la file d'attente, et deux `DETTE-065` sur `main`. ADR-0086
amendé ; élargit `DETTE-067`. Trois tranches restent.)*

Précédente : `E00US018`
*(**l'atlas du projet** : un site statique, ouvrable au double-clic, qui montre le **règlement
en vigueur** puis l'**histoire datée** de chaque règle, et qui calcule ce que le registre ne dit
pas — une seule décision sur l'ensemble du registre porte la mention « Remplacé », alors que
vingt-deux sont amendées par une décision plus récente. Il confronte aussi au dépôt réel les
modules et symboles promis par les sections « Porté dans le code par ». Généré depuis les
sources versionnées, sans aucune dépendance, vérifié en CI. ADR-0086 ; ouvre `DETTE-067`.
Quatre tranches restent.)*

Avant elles : `E05US026`
*(**les poules jouables de bout en bout**, 1ʳᵉ tranche : un **contrat de phase jouable** remplace les
dix filtres qui décidaient chacun dans leur coin qu'une phase est jouable, et les **poules** le
taillent en devenant réellement jouables — réglées à l'atelier, posées en salle sur des blocs de
couloirs, tirées avec le pavé de duel, classées, et **lues par la phase suivante**. Rétrécit
`DETTE-028` au périmètre poules ; ouvre `DETTE-054`. ADR-0083.)*

Précédente : `E05US024`
*(**le club est libre de son format** : un prélèvement est lu dans le classement de **sa** phase
source, plus seulement dans la qualification — tableau→consolante, tableau→tableau, sur autant de
crans que le format en compte, et l'écran public **dit** « en attente » tant que la source n'a pas
départagé les places prélevées. Le plancher d'inscrits remonte la même chaîne. Née d'un arbitrage du
commanditaire au cadrage d'`E16US002` — « la création du déroulé doit permettre de composer les
phases comme on en a envie ». [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md) et
[ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md) ;
reste de `DETTE-028` sur les rangs **résorbé pour les phases classantes lues** (qualification et
élimination directe) — une source visant des **poules / suisse / colline / Big Shoot Off** reste
ignorée jusqu'à `E05US023`. ⚠️ **Plusieurs qualifications reste interdit** —
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

> **La file d'exécution tient en sept lignes.** Le détail par épic est plus bas
> (§ « Retours du questionnaire de maquettes (EPIC-16) », § « Résorptions de dette planifiées ») ;
> ici, **l'ordre**, et lui seul.
>
> | Rang | US | Pourquoi à ce rang |
> |---|---|---|
> | ~~1~~ ✅ | ~~`E05US025`~~ | **Livrée le 09/08/2026** — plusieurs qualifications dans un même déroulé. Le chantier ouvert le 08/08 par `E05US024` est **clos**. |
> | ~~2~~ ✅ | ~~`E05US023`~~ | **Livrée le 09/08/2026** — 1ʳᵉ tranche du découpage : le **contrat de phase jouable** (ADR-0083) et les **poules**, de bout en bout. Le découpage annoncé ci-contre a été fait le jour même : trois tranches restent, une par format. |
> | ~~3~~ ✅ | ~~`E05US028`~~ | **Livrée le 14/08/2026** — le **Big Shoot Off** jouable de bout en bout. Prise avant le suisse et la colline sur le conseil d'ordre ci-dessous, et **le conseil s'est vérifié** : le contrat d'ADR-0083 a bien cédé, mais **sur un nom seulement** (`monte_les_oppositions` → `deroule_par_un_service`), pas sur une structure. Deux capacités ajoutées au périmètre par le commanditaire (palmarès, routage), et surtout un **changement de règle métier** — plusieurs sortants par manche, dits tour par tour — sorti du garde-fou « test écrit depuis le CA ». Référentiel §10.1 amendé. |
> | ~~4~~ ✅ | ~~`E05US026`~~ | **Livrée le 16/08/2026 — backend seul**, le front partant en `E05US030` (périmètre coupé en cours d'US, le 15/08). Le système suisse se règle, se joue ronde après ronde, se pose sur la salle, se classe, se route et entre au palmarès. **Le remède structurel annoncé a bien eu lieu** : les deux ports de classement jumeaux sont fondus en un ([ADR-0084](../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md)) — la 3ᵉ occurrence étant née dans ce diff, l'écart à « en US dédiée » a été tranché par le commanditaire contre un commit séparé. ⚠️ **Le périmètre a triplé au cadrage** : routage (suisse **et** poules, qui l'attendaient depuis E05US023), palmarès avec une règle neuve — *une phase décerne si rien ne prélève dedans* —, et renommage `placement_poule` → `placement_par_bloc` (migration 0046). Deux dettes ouvertes (`DETTE-064` majeure), une refermée (`DETTE-063`). |
> | ~~🎯 1~~ ✅ | ~~`E05US030`~~ | **Livrée le 16/08/2026** — le système suisse **se joue** : fiche de réglages avec la **borne d'effectif affichée en clair**, saisie **ronde par ronde** au pavé de duel, attente nommée tant que la ronde précédente n'est pas close, **classement provisoire** entre les rondes (ajouté au cadrage), pose du plan de cibles, bandeau d'écart retiré. ⚠️ **Le cadrage a produit deux US neuves** (`E05US031`, `E05US032`) : le commanditaire voulait aussi la vue publique et un pilotage explicite des rondes, et les deux se sont révélés d'une autre nature que « du front » — voir leur ligne. ✅ **`DETTE-056` refermée** (le créneau de l'espace scoreur remonté, un seul sélecteur pour quatre panneaux) et l'issue de routage `EN_ATTENTE` livrée des deux côtés, ce qu'`E05US026` avait reporté ici. |
> | ~~🎯 1~~ ✅ | ~~`E05US031`~~ | **Livrée le 18/08/2026** — l'onglet public « Tableaux » devient **« En cours »** et rend la phase qui se joue quel qu'en soit le format ; il **atterrit** sur la phase courante et laisse **remonter le déroulé du départ**. ⚠️ **L'ADR annoncé « probable » était bien requis** : [ADR-0089](../docs/adr/0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md) révise ADR-0064, et le renommage `VueEcran.TABLEAUX` → `EN_COURS` **coûte une migration** (`0047`) — la propriété « trois élargissements sans migration » vaut pour un *ajout*, pas pour un *renommage*. ⚠️ **Le cadrage a ajouté du backend** : le **Big Shoot Off** n'avait aucune route publique (les deux autres formats en avaient une) ; DTO public neuf, `/etat/` ouverte, lecture scoreur migrée sur `/saisie/` — et la restriction remplacée reposait sur un secret **inexistant** (`scores` ne porte que les manches validées). Nommage tranché par le commanditaire : « En cours » plutôt que « Phases », exact mais illisible pour un spectateur. |
> | ~~🎯 1~~ ✅ | ~~`E05US032`~~ | **Livrée le 18/08/2026 — et ce n'est plus l'US qui portait ce numéro.** Le cadrage l'a **recadrée puis coupée en deux** sur une question du commanditaire : *pourquoi quatre mots — tour, ronde, manche, volée — pour un seul concept ?* Réponse : la pluralité est légitime **à l'écran** (règle 3), mais elle ne recouvrait **aucun concept commun dans le code** — cinq progressions privées, et `domain/suivi_deroule.py` qui le constatait sans le nommer (« une phase sans braquet rend un bloc à zéro tour », `# DETTE-028`). Cette tranche pose donc le **tour** comme unité d'avancement générique des six formats, **séparée du braquet** — *avancer ≠ classer*, invariant posé par le commanditaire —, avec le **mot du métier** résolu par le contrat de phase ([ADR-0090](../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md), qui complète ADR-0083). Le suivi cesse d'être aveugle hors tableau. ⚠️ **Le CA d'origine est révoqué** : il disait « la ronde suivante ne s'ouvre **que** sur décision de l'organisateur », le commanditaire a tranché **l'inverse** — l'automatique reste le défaut, l'arrêt devient une décision **programmée**. ⚠️ **La question de cadrage inscrite à la fiche était fausse sur un point** : les poules ne partagent **pas** le décor `RONDES_APPARIEES` (c'est `RENCONTRES_EN_GROUPES`) — la colline seule le partage. Sans effet sur la décision, qui vaut pour les six formats. Port `LecteurAvancementDePhase` **calqué sur ADR-0084**, trois branchements au composition root. Aucune migration. |
> | ~~🎯 1~~ ✅ | ~~`E05US033`~~ | **Livrée le 19/08/2026 — tranche A d'un découpage en deux décidé au cadrage.** La fiche portait **13 CA** traversant modèle persisté, migration, moteur, routes admin et quatre écrans : trop pour une branche (maille INVEST). Le commanditaire a arbitré la coupe — cette tranche livre **le mécanisme** (*la salle peut s'arrêter et se relancer*), `E05US034` livrera **la lisibilité** (*personne ne reste dans le noir*). L'organisateur pose à l'atelier une **liste** de pauses par phase, chacune de portée *phase seule* ou *tout le créneau* ; un arrêt atteint met la phase en `EN_PAUSE` toute seule, l'archer lit « en attente », et un admin relance **d'un seul geste** toutes les phases qu'un même arrêt a coupées. ⚠️ **Une pause ne se pose que sur un type dont l'application lit le tour** — élimination directe, poules, suisse, Big Shoot Off ; ailleurs l'atelier la **refuse** en disant pourquoi, plutôt que d'accepter un réglage qui ne partirait jamais. La **qualification** est sortie du périmètre en fin de revue (arbitrage du commanditaire du 19/08/2026) : dériver son avancement demande de résoudre sa population réelle (ADR-0082), le plan de cibles et les forfaits — repris par `E05US034`. [ADR-0091](../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md), migration `0048` (le **franchissement** seul — la définition passe par le JSON d'étape, sans migration). ⚠️ **Le postulat central de la fiche était faux, et la vérification a sauvé l'US** : elle listait « `EN_PAUSE` gèle la validation » parmi ses *pièges à vérifier*, or `EN_PAUSE` ne gelait **rien** — ni saisie, ni validation, ni routage, et `ServiceTournois.mettre_en_pause` documentait le contraire. La pause était **cosmétique** : sans ce constat, l'US livrait un arrêt qui n'arrête personne. Le volet **phase** est corrigé ici (arbitrage du commanditaire) ; le volet **tournoi** reste cosmétique et part au registre en `DETTE-073`, **majeur**, parce qu'il *mente* à l'organisateur. ⚠️ **Angle mort assumé** : ni le public ni l'écran de salle ne *disent* que c'est une pause — `E05US034` est donc **bloquante avant tout déploiement réel** de la capacité. |
> | ~~🎯 1~~ ✅ | ~~`E05US034`~~ | **Livrée le 20/08/2026 — l'angle mort d'`E05US033` est fermé.** La pause s'**annonce** au public et sur l'écran de salle (bandeau, pas un suffixe de titre en petits caractères), le **tableau de bord rappelle** qu'une salle attend (« 2 phases attendent votre relance depuis 14 min », tout en haut, disparaît une fois relancé), le pilotage **dit où en est chaque phase** (« Ronde 3 — tour 3 sur 5 ») et l'écran de saisie du suisse **nomme** ce qui manque, en séparant *pas encore saisie* de *saisie non validée* — deux attentes qui n'appellent pas le même geste. ⚠️ **Le geste neuf a produit un ADR** : poser une pause le jour J n'est **pas** éditer le déroulé. L'ajouter à l'`EtapeDeroule` l'aurait fait rejouer par le créneau du soir, qui n'a aucune raison de s'arrêter pour une panne réparée à midi — ADR-0076 avait déjà tranché (§4 composer au tournoi, §5 **faire vivre au départ**) sans qu'on ait eu à y revenir. D'où `ArretDeCirconstance`, porté par le créneau et rejoué par personne : [ADR-0092](../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md), migration `0049`. ⚠️ **Périmètre coupé au cadrage du 20/08/2026** : la fiche mêlait cinq CA d'IHM et **un chantier moteur** (rendre la qualification divisible en tours), soit le profil exact qui avait déjà fait couper `E05US033`. Arbitrage du commanditaire : la lisibilité d'abord — ce qui bloque le déploiement, c'est « personne ne sait pourquoi la salle attend », pas « on ne peut pas mettre une qualification en pause ». Le chantier moteur devient **`E05US035`** (3ᵉ report du même CA). ⚠️ **Le CA « état de tour lisible » est tranché** — message circonstancié, **aucune clôture persistée** : ADR-0090 §5 dérive l'avancement à la lecture, en persister un second aurait fait deux sources pour une même vérité. ⚠️ **`0091` manquait à la liste nominative d'ADR-0075** — 4ᵉ omission consécutive, et cette fois constatée **hors revue** ; `0091` et `0092` y sont ajoutés, avec le constat que rien dans le dépôt ne réclame cette inscription. |
> | ~~🎯 1~~ ✅ | ~~`E05US035`~~ | **Livrée le 20/08/2026 — le 3ᵉ report est soldé.** La qualification se règle en `n` **tours égaux** à l'atelier (« 20 volées en 2 tours de 10 »), son avancement se lit tour par tour comme les quatre autres formats, et **une pause peut enfin s'y programmer** — sur le format que tout le monde tire. ⚠️ **Un troisième obstacle, absent de la fiche, a été découvert en implémentant** : lever le refus supposait d'ajouter la qualification à `TYPES_DEROULES`, mais cette table décide aussi si le rang de départ d'une phase **relève le plancher d'inscrits** (E05US021) — un tournoi à qualification prélevée aurait refusé de démarrer, en échange d'un réglage d'affichage. D'où une **capacité distincte** au registre de phase (`avancement_lisible`) et une table `TYPES_ARRETABLES` qui en dérive : [ADR-0093](../docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md). ⚠️ **Le découpage est tenu hors du barème** (*avancer ≠ classer*, ADR-0090) : un tour de qualification ne produit **aucun** classement intermédiaire, et c'est ce qui fait que changer le découpage en cours de phase ne re-partitionne aucun score — contrairement au format du tir d'un Big Shoot Off (`DETTE-062`). ⚠️ **Les deux tables ont bien bougé ensemble** : le test que la tranche précédente avait écrit *pour tomber aujourd'hui* est tombé, et il a été retourné en comparaison des deux registres. **Aucune migration** (racine du `config` JSON d'étape). `DETTE-054` élargie d'une 7ᵉ paire. ⚠️ **Ancienne fiche partiellement fausse** : elle annonçait « le registre d'avancement **et** `TYPES_DEROULES` » — c'est bien le second qu'il ne fallait **pas** toucher. | 
> | ~~🎯 1~~ ✅ | ~~`E05US029`~~ | **Livrée le 21/08/2026 — le confort annoncé, plus une correction de la fiche elle-même.** Une phase de poules peut composer ses groupes **par tranches de rangs contiguës** (« rangs 1-6, 7-12, … ») au lieu de les équilibrer : le format club en cascade se monte en **une** étape au lieu de six écrites à la main. Le mode est un **réglage** de `ReglageDePoules`, pas un `TypePhase` neuf (règle 2). ⚠️ **La fiche annonçait le mauvais remède sur son 2ᵉ obstacle** : elle concluait qu'il fallait porter `rang_premier` **au groupe**. Vérification faite dans le code, il suffit que le **classement de phase se lise groupe par groupe** — chaque poule occupe alors sa tranche, et le `rang_premier` unique de la phase décale l'ensemble comme avant. Un décalage par groupe aurait fait **deux mécanismes** prétendant situer le même archer dans l'espace de rangs du tournoi, soit la seconde vérité que `DETTE-034` documente. D'où le vrai sujet, et le titre de l'ADR : **le mode commande aussi la LECTURE**, pas seulement la composition — les deux versants sont indissociables, n'en porter qu'un produit le classement « bien formé, plausible et faux » d'ADR-0081. [ADR-0094](../docs/adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md). ⚠️ **Trois arbitrages tranchés au cadrage du 21/08/2026**, tous reversés à la fiche : la **cascade à resserrement** entre au périmètre (éprouvée de bout en bout, `test_service_poules_en_cascade.py`) ; les **groupes du bas gonflent** quand l'effectif ne tombe pas juste — question qui ne se posait pas au serpent, les groupes y étant équilibrés par construction ; le garde-fou « 2ᵉ phase de poules au serpent » est un **refus** avec dérogation à cocher, et non un bandeau — le défaut monte un tournoi jouable mais dépourvu de l'intérêt visé, ce qui ne se voit qu'en salle. ⚠️ **Le prédicat du refus porte sur la SOURCE, pas sur le rang dans le déroulé** : une phase nourrie par la qualification garde le serpent, même si des poules la précèdent. **Aucune migration** (racine du `config` JSON d'étape, comme E05US035) et **aucun tournoi déjà réglé ne change de composition**. `DETTE-054` élargie — non d'une paire, mais de **deux champs** dans une paire existante : le décompte en « paires » sous-estime la dette, c'est noté au registre. |
> | ~~🎯 1~~ ✅ | ~~`E05US027`~~ | **Livrée le 22/08/2026 — 4ᵉ et dernière tranche, la file des formats est vide.** La colline se règle, se joue et s'affiche de bout en bout ; `DETTE-028` est refermée sur son volet « moteurs de formats sans appelant ». ⚠️ **Le pronostic de cette ligne s'est vérifié** : le port unifié d'ADR-0084 en est à sa 4ᵉ occurrence et **aucune duplication n'a été écrite** — un branchement d'une ligne au composition root, comme promis. ⚠️ **Périmètre confirmé « de bout en bout » au cadrage**, à la différence du suisse coupé en deux : la colline bénéficiait de tout ce que les trois tranches précédentes avaient posé (décor `RONDES_APPARIEES`, issue `EN_ATTENTE`, port de classement, port d'avancement), donc il n'y avait presque rien à inventer. ⚠️ **Six garde-fous sont tombés et ont été retournés**, dont celui de `DETTE-066` qui a fait son office **avant** qu'une ligne de simulation soit touchée — c'est la première fois qu'un retrait manuel est posé en connaissance de cause plutôt que découvert en revue. ⚠️ **Le CA « réglages à l'atelier » manquait à la 1ʳᵉ tranche** et a été rattrapé en relisant le registre de dette (8ᵉ paire, `DETTE-054`) : le service savait lire un réglage qu'aucune route ne permettait de poser. ✅ Rendez-vous d'E05US030 tenu (`etatRencontre` remontée en `shared/`) ; écart du Ladder **tranché** et reversé aux trois documents de CA. `DETTE-064` élargie (4ᵉ, sur onze tests d'API), `DETTE-065` (7ᵉ copie), `DETTE-031` élargie. **Aucune migration.** |
> | ~~🎯 1~~ ✅ | ~~`E16US002`~~ | **Livrée le 22/08/2026 — le dernier des quatre écrans refusés est levé, la série `🔴` est vide.** Une phase du déroulé porte enfin un **titre** (« Tableau des jeunes »), chaque ligne ouvre **sa** fiche au lieu d'empiler tous les réglages à l'écran, et les deux menus de composition cessent de porter **chacun le nom de l'autre** : « Phases (format) » composait le déroulé d'un tournoi, « Composer un déroulé » fabrique un format de bibliothèque — ils disent désormais **« Phases du tournoi »** et **« Composer un format »** ([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md)). ⚠️ **Le recadrage annoncé a RÉDUIT l'US, à rebours du pronostic de cette ligne** : les cinq fiches de réglages qu'elle annonçait comme « matière en plus » étaient déjà **livrées et câblées** par les six US de formats — il ne restait ni moteur ni catalogue à inventer. La fiche disait « probablement trop large pour une branche » ; c'était vrai le 04/08, faux le 22/08. ⚠️ **La qualification portait le défaut** : « gérée ailleurs », elle n'ouvrait aucun formulaire et ses réglages traînaient à plat dans la barre d'actions — elle était le **seul type impossible à nommer**, précisément celui dont le CA dit qu'on peut en avoir plusieurs. ⚠️ **Le tracker annonçait « champ neuf → migration » : c'était faux.** `deroule_etape` n'a que quatre colonnes, *tous* les champs de définition vivent dans le `config` JSON — **aucune migration**. ⚠️ **Un message trompeur, antérieur à l'US, est tombé avec le renommage** : « éditable depuis l'écran de composition du déroulé » désignait l'atelier, qui ne travaille sur **aucun tournoi**. ⚠️ **Un garde-fou d'E05US035 était plus faible que son nom** : ses requêtes portaient sur l'écran entier alors que le formulaire d'ajout permanent affiche les mêmes libellés — il serait resté vert avec le réglage de la qualification **entièrement décâblé**. Requêtes portées à la ligne. `DETTE-080` inscrite (plomberie des deux formulaires jumeaux, 10ᵉ réglage) ; une duplication **fermée** sur preuve (`configInchangee`, deux bugs déjà payés). `DETTE-035` reste ouverte — chiffrage `P-4` sorti du périmètre au cadrage. |
> | ~~🎯 1~~ ✅ | ~~`E16US012`~~ | **Livrée le 23/08/2026 — la contrainte d'ordre d'`EPIC-16` est levée.** La famille « prêt à… » est **instruite** ([ADR-0096](../docs/adr/0096-un-jalon-enumere-ses-gardes-au-lieu-de-les-lever.md)) et livre son 1ᵉʳ membre neuf : « **Prêt à démarrer ?** » liste **d'un coup** ce qui retient le lancement, là où les gardes ne rendaient qu'un manque à la fois. ⚠️ **Le vrai problème n'était pas la navigation, et il n'était pas dans la fiche** : les gardes du cycle de vie **ne sont lisibles qu'en échouant** — `vers_pret` lève `TournoiSansDepart`, `demarrer` lève `EffectifInsuffisantPourDemarrer`, et une exception ne rend que le **premier** manquement rencontré. Un jalon les **énumère** sans les exécuter ; là où le calcul ne peut pas être partagé mécaniquement, l'accord écran ↔ garde est **épinglé par un test de cohérence** (patron déjà employé entre `_TRANSITIONS` et la légalité du service). ⚠️ **La question de cadrage inscrite à la fiche est tranchée** : « 2 notions » ou quatre écrans ? → **une forme unique paramétrée** — un type de réponse, une route, une coquille front. Elle unifie la *réponse* et la *question*, **pas les règles** : les fusionner aurait demandé l'union de toutes les entrées, donc reconstruit les quatre variantes à l'intérieur. ⚠️ **Un CA manquait à la fiche, découvert en écrivant les tests** : « question binaire » et « avertir sans bloquer » (`D-15`) sont incompatibles avec un seul drapeau — un tournoi **sans déroulé composé démarre**, il faut donc `pret` **et** `bloquant`, ce second portant l'**asymétrie** (démarrer a des gardes de **contenu**, terminer n'en a aucune — mais la garde de **statut**, elle, est commune aux trois membres qui gardent une transition, et c'est la **seule** d'`archiver`). ⚠️ **Les quatre membres ne sont pas de même nature** : trois gardent une **transition** (ADR-0026 §2), *exporter* garde un **geste répétable** — ce qu'ils partagent est la question, pas la machine à états, ce qui autorise la famille à traverser deux axes d'ADR-0058. **`terminer` a été migré sur la coquille commune** (arbitrage technique tranché en cours d'US) : deux occurrences réelles plutôt qu'une abstraction sur pari. Son rendu **gagne** le verdict en tête, et l'écran cesse d'annoncer au futur ce qui est déjà fait sur un tournoi terminé. ⚠️ **Angle mort assumé** : la frise porte toujours ses propres boutons « Démarrer »/« Terminer » — deux endroits pour le même geste, à instruire quand `archiver` rejoindra la famille. ⚠️ **Question métier laissée ouverte volontairement** : faut-il refuser de lancer un tournoi sans déroulé composé ? Aujourd'hui c'est permis ; un test tombera si la garde durcit. **Aucune migration** (lecture dérivée). ADR-0096 **n'entre pas** à la liste nominative d'ADR-0075 (IHM, cf. précédent `0095`) — c'est écrit dans l'ADR pour qu'un trou non commenté ne produise pas la prochaine omission. |
> | ~~🎯 1~~ ✅ | ~~`E16US005`~~ | **Livrée le 24/08/2026 — et c'était une US bien plus petite que sa fiche.** Le plan de cibles passe à **une cible par ligne** sur la largeur d'un PC (couloirs côte à côte et **alignés d'une bande à l'autre**), chaque jeton porte **club · catégorie · blason**, et la **réserve** devient un panneau latéral **collant**. ⚠️ **Deux des trois CA étaient déjà tenus, constat fait au cadrage** : le « puits de réserve » existe depuis `E03US004` — y compris la distinction que le CA réclame (« un archer en réserve doit se distinguer d'un archer sans cible »), explicite dans `presentation.ts` depuis `E03US007` : `en_reserve` neutre contre trois anomalies ambre — et la « préservation des placements manuels » est le bouton « Placer les restants ». Ils n'ont rien coûté ; ils ont **gagné des tests de non-régression**, que rien ne portait. ⚠️ **Le reliquat de vocabulaire annoncé n'existait pas** : `a11-placement.html` ne dit « position » nulle part et l'écran expose déjà `aria-label="Couloir de tir A"` — même cas qu'`E16US004`, dont la liste de maquettes était fausse pour la même raison. L'avertissement est **laissé** sur `E16US010` et `E16US011`, où il n'a pas été vérifié. ⚠️ **Le cadrage a élargi le périmètre sur deux points, tous deux tranchés par le commanditaire** : (a) la largeur gagnée porte les **repères d'arbitrage**, sans quoi les badges « mixité non garantie » / « cloisonnement non respecté » continuaient de désigner une cible sans dire **quel** occupant la cause ; (b) le **plan de duels est aligné dans le même diff** — il partage `.placement__cibles`, le même utilisateur et le même PC. ⚠️ **Un CA est né du cadrage** : la réserve devient **collante**. Une cible par ligne allonge le plan, et le glisser-déposer HTML5 natif **ne fait pas défiler la page** — laisser la réserve en pied d'écran aurait *aggravé* le geste que le questionnaire demandait justement de simplifier. **Front seul, aucune migration, aucun DTO touché** (`club_id`/`categorie_id` vivent sur `Archer`, `blason_id` sur `Placement`). La traduction en clair est **une fonction pure** posée dans le module que les duels importent déjà ; le **rendu**, lui, reste double — `DETTE-085` inscrite (quatre composants jumeaux recopiés), à résorber **avec `DETTE-083`**, même geste et même destination. Le nombre de colonnes de couloirs est **dérivé du plan**, borné par `POSITIONS` (`DETTE-010`, marqueur posé). ⚠️ **La revue a rendu deux bloquants, et ils avaient la même racine : une mise en page qu'aucun test ne peut prouver, livrée sans avoir été regardée** (contrôle visuel impossible sur ce poste, l'extension navigateur n'étant pas connectée). **(1)** Le changement n'avait été appliqué qu'à **un** des deux écrans : `Duels.tsx` calculait les repères, montait trois requêtes pour eux, et ne les rendait jamais — en perdant au passage la typographie de ses jetons, déplacée vers un `<span>` qu'il n'émettait pas. C'est **exactement** le défaut que `DETTE-085` décrit, survenu dans le commit qui l'inscrit : `tsc` ne voit pas une propriété fournie et jamais consommée, et aucun test ne montait cet écran. **(2)** Le point de bascule responsive mesurait le **viewport** alors que la contrainte est la **colonne de contenu**, plus étroite de 368 px sous la coquille : à 1366 px, l'US laissait **52 px de texte** par couloir contre **123 px avant elle** — elle rendait donc l'écran *plus* tassé que ce qu'elle prétendait corriger. Corrigé par trois leviers : pistes fixes resserrées, seuil porté à `78rem` (calibré sur l'offset de la coquille, chiffre commenté), et repères **tronqués avec bulle** au lieu de cassés au milieu des mots — ce dernier rendant la mise en page robuste à la largeur plutôt qu'accordée à une fenêtre supposée. ⚠️ **Un majeur que seul l'axe adversarial a vu** : `.reserve--survol` remettait un fond **transparent** sur le panneau devenu collant — donc le plan visible au travers pendant le glisser, c'est-à-dire pendant le geste que l'US existe pour rendre praticable. ⚠️ **Deux défauts de traçabilité, tous deux dus à un `replace` sur un texte non unique** : la puce « vocabulaire vérifié » avait été barrée dans le bloc d'`E16US004` au lieu d'`E16US005`, et la cellule *Résorption* de `DETTE-085` citait `E05US027` en **précédent** — que l'atlas extrayait comme US **résorbante**, déclarant une dette du 24/08 résorbée par une US du 22/08. `DETTE-083` porte le même artefact sur `main` : signalé, non corrigé ici. **`DETTE-085` passe de *mineur* à *majeur*** — le mécanisme n'est plus un risque mais un défaut constaté — et gagne son garde-fou : **un test de rendu par écran**, vérifié en réintroduisant le bug. ⚠️ **La 2ᵉ passe a rendu un bloquant de plus, et il visait le correctif du premier** : la troncature qui rendait la largeur tenable ne laissait lire que le **club** à 1366 px — donc la mixité (RG-3) sans jamais le cloisonnement (RG-4), soit la moitié du CA, pendant que deux étapes de la fiche écrite dans le même commit exigeaient de lire catégorie et blason. Corrigé par **deux lignes de repères** (club, puis catégorie · blason), une troncature **limitée aux cases** — la réserve est une colonne large, l'y appliquer coupait pour rien — et ~10 px repris par couloir (8 sur la largeur de la réserve, 2,4 sur la lettre de couloir — ⚠️ le `padding` n'en rend aucun, le dépôt est en `box-sizing: border-box`). ⚠️ **Le critère qui avait qualifié le 2ᵉ bloquant n'est toujours pas franchi** : 104 px de texte par couloir à 1366 px contre ~121 avant l'US. Il subsiste une bande **[1249, 1377] px** où l'écran est moins lisible qu'avant — `1366×768` en plein milieu. Le correctif dérivé (seuil à `90rem`) coûterait la réserve collante sous 1440 px, soit un CA né du cadrage : l'arbitrage demande de **voir** les deux rendus et reste ouvert, inscrit en `DETTE-086`. ⚠️ **Et le correctif de l'artefact d'atlas avait rejoué le piège** : l'identifiant `E05US027` retiré de la cellule *Résorption* avait été remplacé par « garde-fou posé en attendant (E16US005) », si bien que l'atlas publiait une US qui **introduit et résorbe** la même dette — donnée plausible, donc pire que l'absurdité de départ, et écrite dans le commit qui gravait la leçon inverse. La cellule ne nomme plus aucune US ; **trois** artefacts du même type sont corrigés (`085`, `083`, `081`), et un contrôle a montré que sept autres entrées relèvent d'un arbitrage cas par cas (une dette peut être élargie **et** partiellement résorbée par la même US) — d'où un remède d'outillage proposé au registre, différent de celui que la revue suggérait. ⚠️ **Angle mort assumé et non levé** : l'écran n'a jamais été vu. Le contrôle visuel est impossible sur ce poste (extension navigateur non connectée) et un banc d'essai statique n'a pas pu être ouvert non plus ; toutes les largeurs sont **calculées** depuis le CSS, jamais mesurées. **Une relecture humaine à l'écran reste requise avant merge.** |
> | ~~🎯 1~~ ✅ | ~~`E16US006`~~ | **Livrée le 25/08/2026** — l'**identité visuelle du tournoi**, qui **absorbe `E01US016`** (jamais livrée : « un second logo » n'avait pas de sens sans le premier). Deux logos facultatifs, deux accents dérivés par le domaine, portée public + salle. ⚠️ **Trois CA d'origine sur quatre étaient caducs ou déjà livrés** — l'origine FFTA/locale est tenue depuis `E01US023`, *clubs* et *barèmes* n'ont aucun porteur. [ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md), migration `0050`. |
> | ~~🎯 1~~ ✅ | ~~`E16US009`~~ | **Livrée le 26/08/2026 — les deux moitiés en suspens de `P06` et `P07` sont tenues.** La cadence et la taille d'une page projetée se **règlent par écran** (`DETTE-039` refermée sur son volet technique), et le classement projeté garde ses **trois premiers** figés pendant que le reste **tourne page par page**. ⚠️ **Le mot « défilement » du CA a été tranché en PAGINATION** ([ADR-0098](../docs/adr/0098-un-ecran-projete-pagine-au-lieu-de-defiler.md)) : un cadre `overflow-y: auto` sur un vidéoprojecteur est un cadre que **personne ne peut actionner** — c'est précisément pour cela que `E16US005` avait laissé `teteFigee` **à zéro** sur cette surface, en inscrivant le rendez-vous dans le code. La forme retenue est celle que le commanditaire **accepte déjà** dans le même questionnaire (`P06`, compteur de pages compris), et elle a l'avantage d'être **déterministe et testable** là où une animation continue ne se prouve pas. ⚠️ **Le lien est mécanique, pas cosmétique** : la tête figée ne passe à 3 **que si** un réglage de pages est fourni ; sans lui elle retombe à zéro. On ne peut donc pas livrer par inadvertance « 3 lignes et rien d'autre », qui est la régression refusée le 05/08. ⚠️ **Un CA sur quatre était déjà livré la veille** : le logo sur l'écran de salle est venu avec `E16US006` — vérifié dans le code au cadrage, 3ᵉ US d'affilée où ce contrôle évite d'implémenter du déjà-fait. ⚠️ **L'alternative du CA « le rendre réglable **ou** le mesurer » est tranchée : réglable.** Mesurer suppose une salle et un projecteur — c'est de l'exploitation, pas du code. L'US rend la valeur corrigeable sans recompiler et **le dit à l'organisateur sous les deux champs** ; `DETTE-039` garde donc sa section de détail, son incertitude n'étant **pas** levée. ⚠️ **Un piège absent de la fiche, trouvé en implémentant** : le cumul du temps d'affichage vivait dans **une seule** variable de module, sous le postulat écrit « une seule surface projetée par onglet, donc pas de collision possible ». Ce postulat tombe à la **deuxième** vue paginée — les pages du classement avançaient pendant que l'écran montrait les affectations. Compteur **indexé par vue**, avec son test. ⚠️ **Deux remontées en `shared/` sur preuve** (2ᵉ consommateur réel, jamais sur pari) : le module de pagination et l'en-tête de page quittent `features/routage/`, sans quoi `competition → routage` ajoutait deux arêtes d'enchevêtrement (`DETTE-083`, signal `features-enchevetrees`). ✅ **Les tests de rendu ont été vérifiés en réintroduisant le bug** — la leçon de `DETTE-085`, appliquée cette fois d'avance. **Migration `0051`** (deux colonnes nullables, aucune donnée écrite : le défaut serveur est **identique** aux constantes front, donc aucun écran installé ne change de comportement). ⚠️ **Angle mort assumé, identique à `E16US005`** : l'écran n'a **jamais été vu sur un vidéoprojecteur**. 40 noms et 3 lignes de tête restent un pari — c'est ce que le réglage rend corrigeable, mais **une relecture humaine en salle reste requise**. ⚠️ **Trois passes de revue, trois décomptes de hauteur successifs, aucune mesure** : la conversion « noms de liste → lignes de tableau » a dû être bornée par un plafond (9 lignes), retenu sur le décompte **le plus pessimiste** — ce qu'un calcul garantit ici n'est pas la justesse mais la **direction de l'erreur** (plus de pages plutôt que des archers jamais montrés). Le reste est inscrit : **`DETTE-086` élargie**, dont l'entrée prédisait mot pour mot ce défaut. Deux résidus explicites — la liste de noms n'est **pas** plafonnée, et au-delà de 27 noms réglés le classement n'évolue plus (l'aide de l'admin le dit, un cadran bloqué ressemblant à une panne). |
> | ~~🎯 1~~ ✅ | ~~`E16US008`~~ | **Livrée le 28/08/2026 — et deux de ses trois CA ont bougé au cadrage.** Chaque ligne bloquée du feu vert porte le **geste qui la lève** : le duel amont se déplie sur place avec ses archers et sa cible, et l'organisateur y **déclare le forfait lui-même** (route élargie, pas doublée). ⚠️ **« Ouvrir le duel amont » était infaisable** — la saisie de duel n'existe que derrière un code scoreur ; le lien aurait mené à un écran de connexion. ⚠️ **Au tour ≥ 2, « cible non attribuée » ne se lève par aucun geste** (`DETTE-019`) : la ligne le dit au lieu d'offrir un bouton inerte. ➡️ Le CA « déclenchement automatique » est **sorti en `E16US013`** : c'est un changement de moteur, personne n'évalue les conditions côté serveur aujourd'hui. |
> | ~~🎯 1~~ ✅ | ~~`E16US010`~~ | **Livrée le 29/08/2026 — quatre CA, dont un déjà à moitié construit et un obstacle absent de la fiche.** La recherche de la sidebar porte une **déroulante d'entité** (tournoi · archer · club), replie casse et accents, traverse **toutes les éditions** et **ouvre la fiche d'un clic** ; la liste des tournois porte **deux niveaux de pastille** dérivés du jalon « prêt à démarrer » ; les **doublons** quittent leur écran dédié pour la **ligne de l'archer**. ⚠️ **L'obstacle réel n'était dans aucun CA** : rien ne permettait d'ouvrir une fiche depuis l'extérieur — l'état d'édition était un `useState` **local à la ligne** et l'adresse d'admin n'avait que trois segments. D'où [ADR-0100](../docs/adr/0100-une-destination-d-admin-porte-l-element-qu-elle-ouvre.md), qui fait entrer l'élément ouvert dans l'adresse ; bénéfice non demandé : une fiche devient **adressable** (lien, favori, F5, *Précédent*). ⚠️ **Deux affirmations de la fiche étaient fausses** : la variante « toutes entités » n'était annoncée nulle part dans `CoquilleAdmin` (la formule n'existait que dans la fiche), et `Archer` **n'existe pas hors tournoi** — chercher hors pilotage veut donc dire chercher à travers toutes les éditions (`ArcherRepository.tous()`). ⚠️ **Le CA « doublons » était le moins cher, à rebours de sa fiche** : détection, route et fusion existaient depuis `E02US005` — c'était une **affordance à déplacer**. La vue d'ensemble perdue est compensée par un décompte en tête de liste (arbitrage du commanditaire : l'icône **remplace** l'écran). ⚠️ **Un CA n'est PAS livré, et c'est écrit** : « déclarer un forfait » depuis la fiche d'archer — la route de qualification est réservée au **scoreur** (`exiger_scoreur`), `E16US008` n'ayant élargi que celle des duels. L'écran dit où le geste se fait plutôt que d'armer un bouton qui partirait en 401 (même arbitrage qu'`E16US008` sur « cible non attribuée ») ; **élargir cette route est une décision de rôles, en attente du commanditaire**. ⚠️ **Manquement à la règle 9 signalé de lui-même** : `domain/recherche.py` a été écrit **avant** ses tests, alors que le domaine se teste depuis le CA d'abord — la liste des cas venait bien du CA, mais l'ordre a été inversé ; c'est noté en tête du fichier de tests. ⚠️ **Le 4ᵉ avertissement « vocabulaire position » consécutif était faux** (après `E16US004` et `E16US005`) : le seul reliquat vivait dans `docs/fonctionnel/E12US006.md`. `DETTE-006` **élargie** (6ᵉ usage de `cle_nom`, 4ᵉ hors club) ; `PlaceDeLArcher` remonté en `placement/` sur **2ᵉ consommateur réel**. **Aucune migration.** |
> | ~~🎯 1~~ ✅ | ~~`E16US007`~~ | **Livrée le 30/08/2026 — la fiche a été découpée au cadrage, comme ses propres Notes le prescrivaient, et elle a rétréci de moitié en route.** L'écran « Exports & impressions » propose désormais **un bouton par format** et non par document : les deux listes sortent en **PDF ou CSV**, la feuille de marque en **PDF seul**. [ADR-0101](../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md). ⚠️ **Deux des cinq CA d'origine étaient CADUCS**, vérifié dans le code au cadrage — 4ᵉ US d'affilée où ce contrôle évite d'implémenter du déjà-fait : *paiement groupé par club* est livré depuis `E08US002` (`recap_par_club`, `marquer_club`) ⚠️ **mais *audit consultable en cours de tournoi* NE l'était PAS — conclusion corrigée en revue (axe D)** : le jugement portait sur le serveur (route ouverte, aucune restriction de statut) alors que le CA parle de l'organisateur, et **aucun écran ne consomme la route**. Le CA reste **dû**, reporté en `E16US016`. C'est le défaut le plus coûteux du lot : il avait été inscrit dans quatre artefacts durables, dont un livrable rendu au commanditaire. ⚠️ **Le CA a dû être précisé pour être vérifiable** : « l'ajout d'un format ne demande pas de toucher l'écran » n'est démontrable que si le **serveur sert le catalogue** ; deux CA ont été ajoutés à la fiche pour l'écrire. Et le catalogue porte les **formats**, pas les **URL** — y mettre un gabarit d'adresse par export aurait reconstruit l'**union de toutes les entrées** que l'instruction de la famille « prêt à… » (`E16US012`) avait déjà refusée. Conséquence assumée et écrite : ajouter un *format* ne touche pas l'écran, ajouter un *export* si. ⚠️ **Le point de conception qui compte est la dérivation** : les formats annoncés au catalogue sont **lus sur le câblage** (`RegistreDeFormats.formats`), jamais réécrits à la main. Une liste figée aurait continué d'offrir un format débranché — l'organisateur aurait reçu une **400 sur un choix que le serveur lui a lui-même proposé**, soit le « bien formé, plausible et faux » d'ADR-0081. ⚠️ **Un format est un adapter, pas une branche** (règle 2 appliquée au rendu) : aucun service ne contient de `if format == …`. Ajouter `xlsx` sera un adapter et une ligne au composition root. ⚠️ **Une route livrée n'avait AUCUN appelant front** : la feuille de marque existait côté serveur sans qu'aucun bouton n'y mène. Elle entre au catalogue — et c'est elle qui, **mono-format**, prouve que la liste est propre à chaque document. ⚠️ **Le CSV a coûté plus que le mécanisme** : quatre partis dictés par le tableur réel (BOM UTF-8, point-virgule, montants sans symbole, aucune ligne de total) — un CSV « conforme à la RFC » s'ouvre en bouillie sur une machine française, et l'export n'exporte alors rien. ADR-0101 §4. ⚠️ **La porte des commentaires a mordu trois fois** (règle 13-i, huit lignes **docstrings comprises**) : trois blocs de raisonnement sont partis en ADR, le code gardant un renvoi — c'est exactement l'office de cette règle. **Aucune dépendance ajoutée** (ReportLab était là, `csv` est stdlib) et **aucune migration**. `DETTE-095` inscrite : un `identifiant` servi au catalogue mais absent de la table de l'écran **disparaît en silence** — mode de panne de `DETTE-091`/`094`, cette fois à travers deux langages. **Trois reliquats écrits** en `E16US016` (palmarès en tableur — renommage d'une route **publique** à arbitrer ; export de l'audit ; `xlsx`, règle 11), plus `E16US014` (podiums) et `E16US015` (QR par scoreur). ✅ **Un reliquat d'`E16US010` est soldé dans le même lot** : sur décision du commanditaire, la route de forfait **en qualification** s'ouvre à l'organisateur — **élargie, pas doublée**, comme celle des duels en `E16US008`. Le geste vit sur la **fiche d'archer**, la place que le CA d'`E16US010` désignait déjà : aucune destination d'admin n'a été inventée (ADR-0058). ⚠️ **Deux tests ont rougi, et c'était leur office** : l'un côté API, l'autre côté écran, tous deux écrits pour épingler la frontière de rôles ; celui du front **nommait sa propre cause de péremption**. Ils ont été retournés, pas supprimés. **L'annulation reste au panneau scoreur** — seul écran qui affiche le classement, donc seul à savoir *qui* est déjà forfait ; un bouton « Annuler » ignorant s'il a quelque chose à annuler serait pire que son absence — `DETTE-090` **élargie**, `D-15` n'étant pas tenu pour l'organisateur. ⚠️ **La revue a rendu 2 bloquants, 10 majeurs et 22 remarques mineures.** Les **2 bloquants sur 2** et **5 majeurs sur 10** viennent de ce reliquat ; le volet exports en porte trois — dont le **seul défaut de sécurité du lot**, l'injection de formule CSV. ⚠️ *(La 1ʳᵉ rédaction disait « tous les défauts de fond » : elle s'arrangeait, et c'est l'axe C2 de la 2ᵉ passe qui a recompté.)* (1) `DeclarerForfait` était monté **sans `key`** : changer d'archer conservait l'état React, si bien que l'archer suivant lisait « Forfait enregistré » sans que rien soit écrit pour lui, et qu'un motif saisi pour A partait avec le POST de B — corrigé et **prouvé en réintroduisant le bug**. (2) La surface était livrée **sans fiche fonctionnelle**, pendant que **deux** fiches (`E16US008`, `E16US010`) affirmaient qu'elle n'existait pas. (3) L'arbitrage n'était **pas reversé dans `stories/`** (règle 9) alors que `dependances.py` y renvoie comme source. (4) **ADR-0050**, qui porte la frontière de rôles, nommait `autoriser_forfait_duel` — symbole supprimé par ce diff : rouvert. (5) L'élargissement avait **désarmé deux tests en silence** — `_scoreur` laisse le Bearer admin posé, et `autoriser_forfait` teste l'admin en premier : plus rien ne prouvait que le chemin scoreur marche. Réarmé, **vérifié par sabotage**, et le jumeau manquant du 403 `scoreur_hors_tournoi` ajouté. (6) Aucun **dialogue de confirmation**, alors que le feu vert en a un pour le même acte : le geste passe désormais par `BoutonConfirme`, qui nomme l'archer et avertit **avant** le clic. **Enseignement de pilotage** : ce reliquat méritait son propre cadrage et sa propre US — le traiter comme de la plomberie a produit les deux bloquants. ⚠️ **Angle mort assumé, comme `E16US005` et `E16US009`** : **l'écran n'a jamais été ouvert** (extension navigateur non connectée sur ce poste). Le dialogue de confirmation, les libellés de boutons, les états de chargement et le repli « aucun document connu » ne sont prouvés que par des tests jsdom ; `flex-wrap` a d'abord été posé sur une classe employée **24 fois dans 21 fichiers** avant d'être restreint à un modificateur local (relevé en 2ᵉ passe). **Une relecture humaine à l'écran reste requise.** ⚠️ **La 2ᵉ passe a rendu 1 bloquant et 16 majeurs, dont trois RÉGRESSIONS du commit de correctifs** — `disabled` perdu en passant par `BoutonConfirme` (double écriture possible, l'écran affichant une erreur sur un forfait pourtant enregistré), et deux corrections documentaires appliquées **à l'artefact visible et pas à son jumeau**. Le conseil de l'axe D est reversé ici : *une correction faite « partout » se termine par un `grep`, pas par une relecture*. |
> | ~~🎯 1~~ ✅ | ~~`E16US014`~~ | **Livrée le 31/08/2026 — et la fiche a été coupée en deux au cadrage.** Le palmarès cesse d'imposer son découpage : trois portées **cumulables** (scratch · catégorie · club) et une **profondeur** réglable, d'un seul réglage pour l'écran, le public, l'écran de salle et le PDF. ⚠️ **La question ouverte de la fiche est tranchée** : *par club* classe les **archers d'un club entre eux** ; classer les **clubs entre eux** est un classement **neuf** et non un regroupement — il part en `E16US017`, au **décompte de médailles** (arbitrage du 31/08, deux autres barèmes écartés et écrits dans la fiche). ⚠️ **Aucune arithmétique d'ex æquo n'a été réécrite** : `_numeroter(paquets, retenir=…)` renumérote déjà un sous-ensemble depuis 1 — un rang de club est le **même** appel avec un autre filtre, `DETTE-029` n'a pas gagné de 5ᵉ site. La profondeur par défaut (4) et la portée par défaut (*catégorie*) **sont** le comportement d'E06US004 : aucun tournoi en base ne change d'affichage (migration `0052`). |
> | ~~🎯 1~~ ✅ | ~~`E16US017`~~ | **Livrée le 04/09/2026 — tranche B d'`E16US014`, et les trois questions ouvertes sont tranchées.** Les clubs se classent entre eux au **décompte de médailles** (or, puis argent, puis bronze — l'ordre olympique), sur les quatre surfaces du palmarès. L'or décerné deux fois **compte deux fois** ; la portée *club* est **exclue** du décompte — elle donne un or à l'intérieur de chaque club, donc à tous —, et sans portée inter-club le classement **n'existe pas**, ce que l'écran **dit** plutôt que d'afficher un tableau vide. Aucun effectif minimum, *ex æquo* à décompte égal. [ADR-0104](../docs/adr/0104-le-classement-des-clubs-se-compte-en-medailles-inter-clubs.md) ; `DETTE-029` élargie à un **5ᵉ site**. |
> | **🎯 1** | reste d'`E16` | `E16US011` (**à découper**, deux contradictions à arbitrer), `E16US013` (**fiche neuve**, trois questions à trancher — candidate à un ADR), `E16US015` (QR par scoreur — **question de sécurité** : un code scoreur est un secret personnel, l'afficher en QR le rend photographiable), `E16US016` (reliquat d'exports — **arbitrage `xlsx`, règle 11**) — **sans ordre imposé**. Deux membres de la famille « prêt à… » restent à instruire (*prêt à archiver*, *prêt à exporter*) — le second se rattache désormais à `E16US016`. |
> | hors file | `E06US009`, `E01US026`, `E05US022` | Résorptions de dette **tranchées** le 07/08, à replacer quand une fenêtre s'ouvre — voir leur section. |
> | 🔒 **en attente de vous** | `E17US005`, `E17US006` | **Deux décisions vous sont demandées**, et ces US ne sont **pas prenables** avant. `E17US005` : embarquer la police Inter au dépôt (ajout d'actif, règle 11 — trois options, cf. sa fiche ; résorbe `DETTE-043`). `E17US006` : quelle couleur pour l'action **destructrice**, la charte l'ayant laissée vide (`DV-03` exclut le rouge). Une US bloquée sur arbitrage se débloque en **posant la question** : elle est posée ici pour ne pas dormir au fond d'`EPIC-17`. |
>
> ---
>
> **⚡ Détail — retours du questionnaire de maquettes (04/08/2026), [`EPIC-16`](../epics/EPIC-16-retours-maquettes.md).**
> Les 36 planches ont été passées en revue par le commanditaire, une par une. Le **lot « front
> seul »** (tout ce qui ne demandait ni décision métier ni backend) a été livré le 05/08/2026 sur la
> branche `feat/retours-maquettes-front` — **hors US numérotée**, d'où un compte d'US inchangé. Ce qui
> reste est spécifié dans [`stories/E16`](../stories/E16-retours-maquettes.md), **treize US** dont
> **dix livrées** ; le tableau complet est en section « Retours du questionnaire de maquettes
> (EPIC-16) », qui fait foi. *(Ce compte disait « douze US dont trois livrées », figé au 04/08/2026 :
> corrigé le 29/08/2026 — `E16US013` est née depuis, et sept US ont été livrées entre-temps.)*
>
> **Prendre d'abord les quatre écrans refusés (🔴)** — ce sont les seuls retours qui disent « l'écran
> ne répond pas au besoin ». **Trois sur quatre sont levés** (A10, A14, P03) ; reste A07 :
>
> | Ordre | US | Ce qu'elle lève |
> |---|---|---|
> | ~~1~~ ✅ | ~~`E16US001`~~ | **Livrée le 05/08/2026** — **plan de salle** (A10). Le refus ne tenait qu'à un mot : arbitrage rendu (« pas de tir » = groupement de cibles, « **couloir de tir** » = place d'un archer, « poste » = tablette), appliqué partout où l'utilisateur lit, et l'écran **montre** désormais, cible par cible, les couloirs occupables (le maillon *blasons* reste expliqué en toutes lettres : le gabarit ne les connaît pas). Renommage `position` → `couloir` dans le code/l'API/la base **différé** ([DETTE-042](../docs/dette.md)). |
> | ~~2~~ ✅ | ~~`E16US003`~~ | **Livrée le 07/08/2026** — **complétude** (A14). Les deux questions ouvertes ont été reposées et **confirment le CA** : le refus visait le mélange **à l'écran**, pas le découpage du domaine ; « Terminer » ne regarde que le sportif. Front seul, aucun changement de domaine ni d'API. Le sportif reste au pilotage sur un écran renommé « **Prêt à terminer ?** » (« Complétude du déroulé » a été écarté en revue : la sidebar porte déjà « Suivi du déroulé », et ADR-0076 réserve « déroulé » au plan composé une fois), l'administratif part **en tête de l'écran Paiements** — pas sur une destination neuve : `hors_sportif` ne porte qu'une ligne et `paiements` est déjà une destination de l'axe gestion. Le **tableau de bord d'accueil** est filtré lui aussi. La planche A14 redessinée du 05/08 est **écartée** (réserve 2 d'ADR-0074). ⚠️ Cadrage à reprendre : le commanditaire vise une **famille « prêt à… »** (démarrer / terminer / archiver / exporter) — refonte de navigation, US dédiée à instruire, cf. `stories/E16`. |
> | ~~3~~ ✅ | ~~`E16US004`~~ | **Livrée le 08/08/2026** — **public multi-archers** (P03). **Front seul, vérification faite** : `…/archers/{id}/deroule` est déjà public et anonyme pour n'importe quel archer (ADR-0039) et `…/tableaux` rend toutes les phases — aucune ligne de backend. Cadrage : **un seul interrupteur « mes archers / tout » en tête de l'écran public**, gouvernant les six onglets, et non un par vue. Conséquences : `VueTableaux` **perd** son sélecteur local « Mon chemin / Tableau complet » (E07US005), qui disait la même chose ; le palmarès ne centre que le classement final, **jamais les podiums** ; chaque vue nomme « aucun de vos archers ici » distinctement de son propre vide ; l'interrupteur disparaît sur un tournoi sans suivi. Recherche par club (un club seul suffit), suivi actionnable dans les deux sens, récapitulatif de journée en `<details>` **ouvert par défaut** (P02 dit « repliable », pas « replié »), détail des flèches dépliable depuis le classement. **Arbitrage du commanditaire, rendu en revue** : l'appli publique **s'ouvre centrée** sur les archers suivis — le CA d'E07US005 le promettait (« *Mon chemin* par défaut dès qu'on suit quelqu'un ») et l'interrupteur unique l'aurait révoqué en silence ; porté par [ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md). **Trois passes de revue** (1 bloquant + 14 majeurs à la 1ʳᵉ, 3 majeurs à la 2ᵉ dont un défaut *introduit* par le correctif précédent, 0 majeur à la 3ᵉ) ; DETTE-031 élargie. ⚠️ Reliquat « position » : la liste de maquettes de `stories/E16` était **fausse** (déjà corrigées par E16US001) — le vrai reliquat était dans `docs/fonctionnel/`, balayé ici. |
> | ~~4~~ ✅ | ~~`E16US002`~~ | **Livrée le 22/08/2026** — **Phases** (A07), le dernier écran refusé. Titre de phase, fiche dépliable par ligne, et les deux destinations de composition renommées ([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md)). Ce qui suit décrivait l'US **avant** sa livraison : ⚠️ **Périmètre rétréci au cadrage du 08/08/2026, et deux US en sont sorties.** Le CA « plusieurs phases de même type » n'était pas un problème d'écran : le moteur ne lisait qu'un classement, celui de la qualification, et l'unicité de la qualification n'était que le pansement de ce raccourci → `E05US024` (livrée) + `E05US025` (🎯, hors file E16). Le CA « gabarit de phase » est **tranché** : un seul niveau, ADR-0060 §5 confirmé — la brique réutilisable reste le **format**. Il reste donc la **liste**, le **titre de phase** (champ neuf → migration) et la **fiche de réglages** par type. Toujours à recadrer contre ADR-0076 (une partie du refus porte sur un écran qui n'existe plus sous cette forme). |
> | ✅ | ~~`E16US005`~~ | **Livrée le 24/08/2026** — hors série des refus (A11 était *validé avec réserves*) : le plan de cibles passe à **une cible par ligne**, les jetons portent les repères d'arbitrage, la réserve devient un panneau collant, et le plan de duels suit. Deux CA sur trois étaient **déjà tenus** par `E03US004`/`E03US007` ; le reliquat « position » annoncé **n'existait pas**. |
> | ✅ | ~~`E16US012`~~ | **Livrée le 23/08/2026** — la famille « prêt à… » est instruite ([ADR-0096](../docs/adr/0096-un-jalon-enumere-ses-gardes-au-lieu-de-les-lever.md)) et livre « **Prêt à démarrer ?** », qui énumère les gardes du feu vert au lieu de les lever une par une ; « Prêt à terminer ? » est migré sur la coquille commune, qui y gagne son verdict. **Deux membres restent à instruire** (`archiver`, `exporter`) : ils répondent `404` (`jalon_non_instruit`) plutôt qu'une liste vide qui se lirait « rien ne manque ». |
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
> ~~⚠️ **Conséquence pour `E16US002` (écran « Phases », A07, refusé)** : elle doit être **recadrée**~~ — ✅ **recadrage fait le 22/08/2026, et le constat ci-dessous était juste** : une partie du refus portait bien sur un écran disparu (la planche dessinait « 1/8 » et « 1/4 » en lignes de phase, alors qu'une étape porte tout le tableau par sa `profondeur`). Ce qui suit décrivait la situation avant :
>
> ⚠️ ~~elle doit être **recadrée**~~
> avant d'être prise. L'écran a changé de nature avec [ADR-0076](../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
> — il compose désormais un déroulé **sans statut**, le pilotage ayant migré vers « Suivi du
> déroulé ». Une partie du refus A07 (« 1/8 et 1/4 présentés comme des phases ») porte sur un écran
> qui n'existe plus sous cette forme.

> ~~**🎯 Prochaine : `E05US025`**~~ — ✅ **livrée le 09/08/2026**. Ce qui suit décrivait l'US avant
> sa prise ; conservé parce que le cadrage l'a **démenti sur un point**, et que la fausse piste vaut
> d'être gardée : la « fourche » (haute et basse puisant dans la même phase amont) a d'abord été
> jugée **non représentable**, sur une lecture erronée de l'invariant d'ordres. L'`ordre` d'une phase
> est **topologique** — il dit qui peut alimenter qui, pas qui passe avant qui sur le pas de tir —
> et rien n'impose une seule phase en cours à la fois. Aucun chantier de graphe n'était nécessaire.
> Cf. [ADR-0082](../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md) §1.
>
> ~~**🎯 Prochaine : `E05US023`**~~ — ✅ **livrée le 09/08/2026**, découpée le jour même en quatre
> tranches. La 1ʳᵉ a posé le **contrat de phase jouable** (ADR-0083) et rendu les **poules** jouables
> de bout en bout ; les trois autres portent chacune un format restant.
>
> ~~**🎯 Prochaine : `E05US028`**~~ — ✅ **livrée le 14/08/2026**. Ce qui suit décrivait les trois
> tranches avant leur prise ; le conseil d'ordre a été suivi et **il était juste**, ce qui vaut
> d'être gardé : le contrat n'a cédé que sur un **nom**, et le corriger a coûté quatre fichiers au
> lieu d'un rework sur du code livré. Deux tranches restent.
>
> ⚠️ **Ce que cette US a coûté de plus que prévu, et qui n'était dans aucune fiche** : le CA
> annonçait un réglage (« nombre d'éliminés par manche ») que ni `ConfigurationBigShootOff`, ni le
> moteur, ni le référentiel §10.1 ne connaissaient. La divergence est sortie **en écrivant le test
> depuis le CA**, avant d'implémenter — exactement là où la règle 9 la place. Questionné, le
> commanditaire a **élargi la règle** plutôt que corrigé le CA, et a ajouté deux capacités au
> périmètre (palmarès, routage). Le suisse et la colline n'ont pas ce risque : leur règle est écrite
> et leur CA cite des paramètres qui **existent**.
>
> ~~**🎯 Prochaine : `E05US026` (ou `E05US027`)**~~ — ✅ **`E05US026` livrée le 16/08/2026**,
> backend seul. Ce qui suit décrivait les deux tranches restantes ; **la colline reste**, et le
> constat ci-dessous se vérifie une troisième fois. Elles sont
> **indépendantes entre elles**. Chacune habite le contrat : une ligne au registre
> (`domain/contrat_phase.py`), un service applicatif, une exposition à l'atelier et en salle. C'est
> ce que la 1ʳᵉ tranche a acheté, et c'est ce qui les rend tenables une par une.
>
> <details><summary>Le conseil d'ordre qui a décidé de prendre E05US028 en premier (vérifié)</summary>
>
> ⚠️ **Un conseil d'ordre, pas une contrainte** : `E05US028` (Big Shoot Off) est celle qui
> **éprouvera** le contrat — elle n'a ni groupes ni duels, et son grain de validation est
> `FIN_DE_SERIE` là où les trois autres sont `FIN_DE_DUEL`. La prendre tôt fait remonter tôt un
> éventuel élargissement du contrat, au lieu de le découvrir après deux tranches écrites dessus.
> Le contrat annonce lui-même où il pourrait céder (ADR-0083 §2 et sa section « Ce que le contrat a
> déjà appris »).
>
> **Verdict du 14/08/2026** : le pari est tenu. Le contrat a cédé sur **une capacité mal nommée**,
> pas sur une structure — les six questions, le décor `VOLEE_COLLECTIVE` et le grain `FIN_DE_SERIE`
> ont tous tenu tels quels. Le coût du correctif : quatre fichiers, aucune migration.
>
> </details>
>
> <details><summary>Ce que disait cette section avant la livraison d'E05US025</summary>
>
> **plusieurs qualifications dans un même déroulé**, la seconde
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
> </details>
>
> **Ensuite : `E05US023`** — **rendre jouables poules, système suisse, colline et Big Shoot Off**,
> et les rendre **composables à l'atelier**. **Rang arbitré le 08/08/2026** sur la priorité
> « au plus tôt » donnée par le commanditaire : elle passe **devant `E16US002`**, mais **derrière
> `E05US025`**, parce que `E05US024`+`E05US025` forment un **seul chantier** — les couper laisserait
> le peuplement générique à moitié exploité, et `E05US023` s'y appuie (un format jouable doit
> pouvoir être **peuplé** depuis n'importe quelle source).
> ⚠️ **À découper avant de la prendre** : quatre moteurs × deux surfaces (exécution + atelier) ne
> tiennent pas dans une branche. Découpage retenu : **1ʳᵉ tranche** = le contrat « phase jouable »
> générique **plus un** format — c'est elle qui paie le coût du pattern —, puis **une tranche par
> format restant**, chacune portant son **moteur** et son **exposition à l'atelier**. Ne pas livrer
> un moteur sans sa surface : `poule.py` et `big_shoot_off.py` sont déjà dans ce cas depuis
> `E05US015` (moteurs sans consommateur de production, `DETTE-028`) et c'est précisément ce que
> l'US vient corriger.
> **Trois effets de bord à traiter dans l'US, pas après** : (a) elle résorbe le reste de
> `DETTE-028` (poules / suisse / colline / BSO encore ignorés comme **sources** de prélèvement,
> cf. `E05US024`) ; (b) le CA d'**`E06US003`** dit explicitement « l'US qui livrera l'exécution de
> ces phases devra reprendre ce CA » — c'est une **obligation de correction de CA**, pas une
> option ; (c) elle **débloque `E01US011`** (presets de barèmes multi-phases, J4), qui attendait la
> règle du Big Shoot Off — verrou en réalité **déjà levé** le 31/07 par `E05US015`, la note d'US
> était périmée (corrigée le 08/08).
>
> ~~**Puis : `E16US002`**~~ — ✅ **livrée le 22/08/2026** ([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md)). Ce qui suit décrivait l'US avant sa livraison :
>
> ~~l'écran **« Phases »** (A07), **dernier des quatre écrans refusés**~~.
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
> `E16US008` (feu vert), ~~`E16US009` (écran de salle)~~ **livrée le 26/08/2026**, ~~`E16US010` (recherche & alertes)~~ **livrée le 29/08/2026**,
> ~~`E16US007` (exports — formats)~~ **livrée le 30/08/2026** (découpée : podiums → `E16US014`,
> QR scoreur → `E16US015`, reliquats → `E16US016`), ~~`E16US014` (podiums configurables)~~
> **livrée le 31/08/2026** (coupée en deux : le classement des clubs entre eux → `E16US017`),
> et `E16US011`
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
>    **n'a pas été validée**. **Seul A07 reste concerné** : A14 a été traité par `E16US003` (07/08)
>    et P03 par `E16US004` (08/08), toutes deux livrées **sans** la réponse du tour 2, en écartant la
>    planche redessinée. La mise en garde ne vaut donc plus que pour **`E16US002`**.
>    - **Précédent posé le 07/08/2026 par `E16US003`, confirmé le 08/08 par `E16US004`** : la planche A14 a été **écartée** et l'US
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
> ~~**🎯 Prochaine : `E13US002`**~~ — composer les équipes. ⚠️ **Supplanté** le 05/08/2026 : la
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
| 38 | E04US001 | Rattacher une tablette à sa cible (QR + jeton de poste) | ✅ |
| 39 | E09US008 | Imprimer QR de cible & codes scoreurs | ✅ *(ordre rétabli le 08/08/2026 : `E09US008` **déclare** dépendre d'`E04US001` et a été livrée après elle — 19/07 contre 18/07. L'ordre inverse décrivait l'usage du **jour J**, pas la construction)* |
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

## J3 — Placement intégral 1→N + écran de salle — 🔶 **en cours (25/26)**

| Seq | US | Titre | État |
|---|---|---|---|
| 73 | E05US010 | Placement intégral 1→N **& peuplement multiple** | ✅ *(routing générique + cascade, sources multiples, oracle 120, ADR-0061 ; absorbe E05US018, résorbe DETTE-015)* |
| 74 | E05US015 | **Catalogue de types de phase** (échauffement, barrage, poules, repêchage, BSO) | ✅ *(11 formats : + suisse, colline, handicap, finale spectacle — le commanditaire a fourni leurs règles le 31/07 ; ADR-0062)* |
| 74bis | E01US024 | **Composer, diagnostiquer et simuler un déroulé** | ✅ *(brouillon + invariant déplacé vers `appliquer`, schéma SVG maison, 2 gravités d'anomalie, simulation composée sur ADR-0054/0055 ; ADR-0063 — résorbe DETTE-030, ne résorbe DETTE-028 qu'à moitié)* |
| 74ter | E01US025 | **Le départ est la portée sportive** + le déroulé se définit **une fois** | ✅ *(corrige [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md), resté **13 mois** sans portage dans le moteur : 4 départs de 100 rendaient UN classement de 400. `Phase`/`BarrageDePlaces` pendent au départ, `EtapeDeroule` porte la définition au tournoi ; migrations 0042/0043 ; garde-fou mécanique `test_portee_sportive.py` ; ADR-0075 + ADR-0076. ⚠️ **fiche écrite après coup**, US prise hors tracker — CA de non-régression, pas oracle. Ouvre DETTE-044/045/046, aggrave DETTE-025/026. **Reliquat de revue soldé le 07/08** : portée départ appliquée au suivi du déroulé, aux tableaux publics, au routage jour J et au contrôle d'effectif ; migrations 0042/0043 rendues réversibles ; cloisonnement du barrage ; décors de test passés à **deux créneaux**)* |
| 75 | ~~E05US018~~ | ~~Oracle 120~~ → **absorbée par E05US010** | ⛔ *(le moteur et sa preuve ne se séparent pas ; hors décompte)* |
| 76 | E06US006 | **Classement intégral 1→N & profondeur configurable** | ✅ *(la profondeur se règle **par phase** et non plus au câblage ; absence = preset du type, podium pour une élimination directe et intégral pour un placement — ADR-0070, DETTE-035 ouverte)* |
| 76bis | E05US020 | **Le moteur consomme les prélèvements déclarés** | ✅ *(cœur de DETTE-028 : prélèvement par rangs honoré, plage relative résolue, tranche de rangs au palmarès — DETTE-034 soldée, ADR-0068)* |
| 76ter | E05US021 | **Un format connaît son effectif minimum** (avertir avant de lancer) | ✅ *(minimum **déduit** des prélèvements, exigence de club au-dessus, refus au démarrage + annonce avant le clic — ADR-0069)* |
| 76quater | E05US024 | **Un prélèvement lit le classement de sa phase source** | ✅ *(reste de `DETTE-028` sur les rangs **résorbé pour les phases classantes lues** — qualification et élimination directe ; une source visant des poules / suisse / colline / Big Shoot Off reste ignorée jusqu'à E05US023 : tableau→consolante, tableau→tableau, cascade récursive sur un graphe acyclique ; un tableau se lit comme un classement, fourchettes *ex æquo* fermées par la politique `aggregation` (ADR-0067) et non par un départage local qui aurait contredit le palmarès ; le plancher d'inscrits remonte la chaîne et refuse de chiffrer une fenêtre amont plafonnée. **Une fenêtre qui coupe un bloc encore indécis est refusée et annoncée** (ADR-0081) : un tableau de 8 non commencé rendait « les rangs 5 à 8 » comme étant les 4 derniers **qualifiés** — bien formé, plausible, faux, et moins détectable qu'avant l'US ; l'écran public affiche désormais « en attente du tableau *n* ». Le « cycle » invoqué par E05US020 pour reporter ce cas **n'existait pas** — récursion, pas cycle de modules : une justification de report se re-vérifie à la reprise. [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md), [ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md))* |
| 76quinquies | E05US025 | **Plusieurs qualifications dans un même déroulé** | ✅ *(le format demandé le 08/08 se compose, se joue et se classe : **chaque tour a son barème** (écran « Barème & validation » listant une section par qualification), **chaque archer une feuille par tour** (`serie.phase_id`, migration `0044`), et le **classement final va de 1 à N** — la haute occupe 1..60, la basse 61..120, le premier de la basse restant derrière le dernier de la haute même s'il a mieux tiré. `_anomalies_unicite_qualification` retirée : ce n'était pas une règle de tir à l'arc mais un pansement sur neuf lecteurs incohérents, et l'US répare les lecteurs. `ResultatPhase.origine` empêche une qualification de décerner une médaille — sans elle, trois qualifications d'affilée remettaient un podium complet avant le moindre duel. **Résorbe `DETTE-046`** sans US dédiée (la phase subsume le départ). Deux défauts trouvés en route : le cache mypy annonçait « Success » sur des appels qui plantaient à l'exécution, et l'atelier **refusait de composer** une seconde qualification faute de réglages de départ. Ouvre `DETTE-052` (la saisie admin devine le créneau). ADR-0082, qui **amende ADR-0069**)* |
| 76sexies | E05US023 | **Les poules jouables de bout en bout** (1ʳᵉ tranche : le contrat de phase jouable) | ✅ *(un **contrat de phase jouable** (`domain/contrat_phase.py`) remplace les **dix** filtres sur `ELIMINATION_DIRECTE` qui répondaient chacun à une question un peu différente et que le code documentait comme « ne se recoupant que par coïncidence » — deux divergences y étaient déjà consignées, ajouter quatre formats en aurait garanti trois de plus. Les tables existantes ne disparaissent pas, elles **dérivent** d'une source unique par capacité. Les **poules** le taillent en devenant jouables : réglées à l'atelier (`config.poules`, à la racine du `config`, sans migration), posées en salle par **bloc de couloirs contigus** — une poule de 5 tient sur 4 couloirs, le membre au repos change à chaque tour, donc on persiste « poule → couloirs » et jamais « archer → couloir » (migration `0045`) —, tirées avec le **pavé de duel d'E04US013** (une rencontre *est* un duel ordinaire, même table `duel`, même file hors-ligne), classées aux cinq critères du §10.1, et **lues par la phase suivante** : le classement de phase se range « par rang de poule d'abord », tout le monde y figure, et les blocs sont déclarés **indécis** tant qu'un départage optionnel n'est pas demandé — ADR-0081 refuse alors la fenêtre qui les coupe et honore celle qui les contient. L'atelier **avertit** quand un tableau nourri par des poules peut réunir deux membres d'un même groupe (les exempts peuvent rejouer une poule au 1ᵉʳ tour) plutôt que de corriger en douce une règle que personne n'a demandée. Le branchement `ServicePoules` ↔ `ServiceSaisieDuels` passe par un **port étroit** câblé au composition root : les deux services se tiennent par les deux bouts, et un import paresseux aurait caché le cycle au lieu de le casser. **Rétrécit `DETTE-028`** au périmètre poules — le signal d'écart est désormais **dérivé du registre**, donc il ne peut plus mentir type par type. Ouvre `DETTE-054` (3ᵉ paire de DTO jumeaux entre les deux routeurs de composition). Reste hors périmètre et **dit comme tel** : le routage d'un membre de poule, le palmarès, le forfait en poule. [ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md))* |
| 76septies | E05US028 | **Le Big Shoot Off jouable de bout en bout** | ✅ *(3ᵉ tranche du découpage d'`E05US023`, livrée le 14/08/2026 : la volée de barrage se règle, se joue, se départage et entre au palmarès. Règle métier amendée en cours d'US — plusieurs sortants par manche, dits tour par tour (référentiel §10.1). ADR-0083 tenu sur sa structure. **Insérée ici le 16/08/2026** : elle n'existait que dans la file d'attente, donc dans aucun compteur.)* |
| 76octies | E05US026 | **Le système suisse jouable** (backend) | ✅ *(livrée le 16/08/2026, **backend seul** — le front part en `E05US030`. Se règle, se joue ronde après ronde, se pose sur la salle, se classe, se route et entre au palmarès. Les deux ports de classement jumeaux fondus en un ([ADR-0084](../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md)). Ouvre `DETTE-064` (majeure), referme `DETTE-063`. **Insérée ici le 16/08/2026**, même raison.)* |
| 76nonies | E05US030 | **Le système suisse à l'écran** | ✅ *(livrée le 16/08/2026 — la 2ᵉ moitié d'`E05US026`, coupée à la couture backend / front. Fiche de réglages (nombre de rondes) avec la **borne d'effectif dite en clair** — elle existait au domaine et ne se voyait nulle part, donc l'organisateur la découvrait par un refus ou par un déficit de rondes muet le jour J. Saisie **ronde par ronde** au pavé de duel (`famille: 'suisse'`, 3ᵉ valeur — les quatre aiguillages binaires « poule ou tableau » du mécanisme sont passés en `Record` exhaustifs, faute de quoi le format tombait du côté tableau partout où l'un d'eux aurait été oublié). Attente nommée tant que la ronde en cours n'est pas close, **classement provisoire** (points rendus en victoires, Buchholz) ajouté au cadrage, bouton de pose du plan de cibles — écrit d'emblée pour ne pas rejouer le défaut d'E05US023, où le hook de pose n'avait aucun appelant. ✅ **`DETTE-056` refermée** ; ✅ issue de routage `EN_ATTENTE` livrée des deux côtés. ⚠️ Le cadrage a produit `E05US031` et `E05US032`.)* |
| 76decies | E05US031 | **Le public voit les formats sans arbre** | ✅ *(livrée le 18/08/2026 — onglet « En cours » qui aiguille par format et remonte le déroulé du départ ; route publique neuve pour le Big Shoot Off ; `VueEcran.TABLEAUX` → `EN_COURS`, migration `0047`. ADR-0089, révise ADR-0064)* |
| 76undecies | E05US032 | **Une phase avance par tours** | ✅ *(livrée le 18/08/2026 — **recadrée au cadrage du jour** : la fiche s'intitulait « L'organisateur ouvre la ronde suivante » et son CA est **révoqué**. Le **tour** devient l'unité d'avancement générique des six formats, séparée du **braquet** (*avancer ≠ classer*), avec le mot du métier résolu par le contrat de phase — 7ᵉ question, `UniteDeTour`. Le suivi du déroulé cesse d'afficher « zéro tour » sur tout format qui ne classe qu'à la fin. Port `LecteurAvancementDePhase` calqué sur ADR-0084, branché par type. [ADR-0090](../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md). Aucune migration.)* |
| 76duodecies | E05US033 | **L'organisateur programme les pauses du déroulé** | ✅ *(livrée le 19/08/2026 — **tranche A** d'un découpage en deux décidé au cadrage : la fiche portait 13 CA à travers modèle, migration, moteur et quatre écrans. Livre le **mécanisme** : liste de pauses posées à l'atelier, portée phase ou créneau, bascule automatique en `EN_PAUSE`, reprise admin d'un seul geste pour tout un arrêt, routage « en attente ». Une pause ne se pose que sur un type dont l'application lit le tour — la qualification, sortie du périmètre en fin de revue, revient en `E05US034`. [ADR-0091](../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md), migration `0048`. ⚠️ A révélé que `EN_PAUSE` **ne gelait rien** — pause cosmétique, docstring fausse : corrigé pour la phase, `DETTE-073` **majeure** pour le tournoi)* |
| 76terdecies | E05US034 | **La pause se voit, et se pose en cours de journée** | ✅ *(livrée le 20/08/2026 — **tranche B** du découpage d'`E05US033`, et son filet de sécurité : bandeau de pause au public **et** à l'écran de salle, pastille de rappel au tableau de bord (« 2 phases attendent votre relance depuis 14 min »), pose d'une pause le jour J (« bloquer dans x tours »), état de tour lisible au pilotage, refus circonstancié du suisse (*pas saisie* vs *pas validée*). ⚠️ Un arrêt posé le jour J appartient au **créneau**, pas au déroulé — [ADR-0092](../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md), migration `0049`. ⚠️ La **qualification divisible en tours** est sortie du périmètre au cadrage → `E05US035`, 3ᵉ report du même CA)* |
| 76quaterdecies | E05US035 | **La qualification se découpe en tours** | ✅ *(livrée le 20/08/2026 — le **3ᵉ report est soldé**. « 20 volées en 2 tours de 10 » se règle à l'atelier, l'avancement se lit tour par tour, et une **pause peut enfin se poser sur le format que tout le monde tire**. Le tour se dérive du **plus lent** d'une population résolue en trois filtres — archers placés, admis par *cette* phase (deux qualifications peuvent coexister dans un créneau, ADR-0082), forfaits soustraits : c'est ce trio qui avait fait reporter le CA trois fois. ⚠️ Un obstacle **absent de la fiche** a été découvert en implémentant : la table qui refusait l'arrêt (`TYPES_DEROULES`) décide **aussi** du plancher d'inscrits (E05US021), donc y verser la qualification aurait fait refuser le démarrage d'un tournoi à qualification prélevée. « Arrêtable » devient une **capacité distincte** du registre de phase — [ADR-0093](../docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md). ⚠️ Le découpage est tenu **hors du barème** (*avancer ≠ classer*, ADR-0090) : le modifier en cours de phase ne re-partitionne **aucun** score. **Aucune migration** ; `DETTE-054` élargie d'une 7ᵉ paire)* |
| 76quindecies | E05US029 | **Des poules de niveau en une seule étape** | ✅ *(livrée le 21/08/2026 — le tournoi club **en cascade** se compose sans corvée : une phase de poules peut répartir son classement source en **tranches de rangs contiguës** (« rangs 1-6, 7-12, … ») au lieu de les équilibrer au serpent, là où il fallait jusqu'ici écrire **six étapes à la main**. Le mode est un **réglage** de `ReglageDePoules`, pas un `TypePhase` neuf (règle 2). ⚠️ **La fiche annonçait le mauvais remède** sur son 2ᵉ obstacle — porter `rang_premier` **au groupe** — et la vérification dans le code l'a corrigé : il suffit que le **classement de phase se lise groupe par groupe**, chaque poule occupant alors sa tranche. Le remède annoncé aurait fait deux mécanismes pour situer un même archer dans l'espace de rangs (la seconde vérité de `DETTE-034`). D'où le sujet réel : le mode commande **aussi la lecture**, et les deux versants sont indissociables — [ADR-0094](../docs/adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md). ⚠️ Trois arbitrages au cadrage : **cascade à resserrement** au périmètre (éprouvée de bout en bout), **groupes du bas** gonflés quand l'effectif ne tombe pas juste, garde-fou « 2ᵉ phase au serpent » en **refus** avec dérogation — son prédicat portant sur la **source**, pas sur le rang dans le déroulé. **Aucune migration** ; `DETTE-054` élargie de deux champs, pas d'une paire. **Insérée ici le 21/08/2026** — née du cadrage d'`E05US026`, elle n'existait que dans la file d'attente)* |
| 76sexdecies | E05US027 | **La colline jouable** | ✅ *(livrée le 22/08/2026 — **4ᵉ et dernière tranche** du découpage d'`E05US023`, et celle qui vide la file des formats. Le *King of the Hill* / *Ladder* se règle à l'atelier (manches + **portée de défi**, avec la borne que l'effectif autorise affichée en clair), se joue manche après manche au pavé de duel, se route, se classe et s'affiche au public comme sur l'écran de salle — **backend et front dans la même branche**, à la différence du suisse. `DETTE-028` **refermée sur son volet « moteurs de formats sans appelant »** ; ⚠️ **le volet politiques subsiste** (`ScoreAvecHandicap`, `RoutingRepechage`, `classement.py` hors famille `scoring`) et n'a aucune US inscrite — le barrer eût été la sur-promesse type. ⚠️ **Le format n'a pas de bye, il a des archers AU REPOS** : à portée 1, les **deux extrémités** se reposent une manche sur deux quel que soit l'effectif — ce n'est pas le cas limite d'un effectif impair, et l'issue `EN_ATTENTE` (ADR-0087) y est donc le **régime ordinaire**, pas l'exception. ⚠️ **Rien de l'ordre de la colline n'est persisté** : il se rejoue de l'ordre initial et des manches closes (même parti qu'ADR-0090 §5) — le persister aurait donné deux vérités qui divergent à la première correction de score. ⚠️ **Six garde-fous sont tombés et ont été retournés**, dont celui de `DETTE-066` **avant** qu'une ligne de simulation soit touchée ; deux autres se déplacent sur `placement` et **cessent de se déplacer**. ⚠️ **Écart du Ladder tranché** (l'exemple contredit la règle : c'est la règle qui fait foi) et reversé aux **trois** documents de CA. `DETTE-054` (8ᵉ paire), `DETTE-064` (4ᵉ, sur onze tests d'API), `DETTE-065` (7ᵉ copie), `DETTE-031` élargies. **Aucune migration.**)* |
| 77 | E03US007 | **Contrainte séparation catégorie/blason** | ✅ *(réglage de tournoi à 4 positions, contrainte **dure** au placement auto **et** au glisser-déposer, **sur les deux plans** (cibles et duels), raison de réserve propre `cloisonnement`, cibles non conformes signalées — ADR-0071, DETTE-036/037 ; tranche la priorité des contraintes restée ouverte à EPIC-03)* |
| 78 | E09US005 | Classements PDF | ⬜ *(rétrécie par E06US004 : le **palmarès** a son PDF ; reste celui du classement de **qualification**)* |
| 79 | E00US013 | Factoriser les briques d'UI partagées | ✅ *(remontée de J3, DETTE-004 résorbée)* |
| 80 | E01US016 | Définir l'identité visuelle du tournoi | ✅ *(25/08 — **livrée sous le numéro `E16US006`**, qui l'a absorbée : « un second logo » n'avait pas de sens sans le premier. CA livré en entier, à une réserve nommée près — l'usage de l'accent **secondaire** reste mince, aucune planche ne disant ce qu'il doit peindre)* |
| 81 | E07US004 | Écran de salle **+ suivi du déroulé** (un composant, trois surfaces) | ✅ *(poste typé cible/écran, pilotage par état lu, suivi superposé — ADR-0064)* |
| 82 | E07US005 | **Vue tableaux/arbres live** | ✅ *(onglet public « Tableaux » à deux lectures — « Mon chemin » par archer suivi et tableau complet par tour —, DTO public restreint, vue `tableaux` de l'écran de salle : le catalogue d'ADR-0064 couvre enfin son CA en entier ; DETTE-031 élargie)* |
| 83 | ~~E05US019~~ | ~~Enregistrer une séquence comme modèle~~ → **absorbée par E01US023** | ⛔ *(doublon repéré le 31/07 : ADR-0060 §5 ; hors décompte — la capacité est livrée, l'US ne l'est pas en propre)* |
| — | E00US015 | Ossature de navigation admin (coquille) | ✅ *(fait en avance — ajout 18/07 ; **comptée dans « Ajouts de l'entretien du 18/07 »**, hors décompte de J3)* |

## J4 — Confort, richesse & robustesse — ⬜ **non commencé (0/7)**

| Seq | US | Titre | État |
|---|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc | ⬜ |
| 85 | E01US011 | Presets de barèmes multi-phases | ⬜ |
| 86 | E01US012 | Gérer plusieurs gabarits | ⬜ |
| 87 | E03US010 | Générer / éditer le déroulé horaire | ⬜ |
| 88 | E09US007 | Déroulé horaire imprimable | ⬜ |
| 89 | ~~E05US016~~ | ~~Routing repêchage (WA)~~ → **absorbée par E05US015** | ⛔ *(le repêchage est une politique `routing`, pas un type de phase — ADR-0062 §1 ; hors décompte)* |
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

## Ajouts de la démo du 27/07/2026 — ✅ **traités (12/12)**

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

## Retours du questionnaire de maquettes (EPIC-16) — 🔶 **en cours (13/17)**

> Ce que le commanditaire reproche **aux maquettes**, là où [`E17`](../epics/EPIC-17-fidelite-aux-maquettes.md)
> amène le **produit** jusqu'à elles. Issu du questionnaire du 04/08/2026 (36 planches passées une
> par une). Le **lot « front seul »** — tout ce qui ne demandait ni décision métier ni backend — a
> été livré le 05/08/2026 **hors US numérotée** (branche `feat/retours-maquettes-front`), d'où un
> compte d'US inchangé. Détail : [`stories/E16`](../stories/E16-retours-maquettes.md).
>
> **Les quatre écrans refusés (🔴) passent en premier** : ce sont les seuls retours qui disent
> « l'écran ne répond pas au besoin ». **Les quatre sont levés** depuis le 22/08/2026 : `A07`
> (`E16US002`) était le dernier.

| US | Titre | Refus levé | État |
|---|---|---|---|
| E16US001 | Plan de salle : se mettre d'accord sur ce qu'est un pas de tir | 🔴 A10 | ✅ *(05/08 — « pas de tir » = groupement de cibles, « couloir de tir » = place d'un archer, « poste » = tablette ; ADR-0073 amende ADR-0006 ; renommage `position` → `couloir` différé, DETTE-042)* |
| E16US002 | Phases : une bibliothèque de phases réglables, pas une séquence figée | 🔴 A07 | ✅ *(22/08 — **dernier écran refusé levé**. Titre de phase (libellé, pas identité — ni unique, ni obligatoire, et il survit à un retypage), **fiche dépliable par ligne** offerte à **tous** les types (la qualification n'en avait aucune et était le seul type impossible à nommer), et les deux destinations de composition renommées — elles portaient **chacune le mot de l'autre**. [ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md). **Aucune migration** (racine du `config` JSON, contre « migration » annoncée). Périmètre **rétréci** au cadrage du 08/08 — les CA « plusieurs phases de même type » et « gabarit de phase » en étaient sortis — puis **réduit encore** au cadrage du 22/08 : les cinq fiches de réglages existaient déjà, et le chiffrage `P-4` ([`DETTE-035`](../docs/dette.md)) a été laissé hors périmètre par le commanditaire. `DETTE-080` inscrite.)*
| E16US003 | Complétude : ne plus mélanger le déroulé et la gestion administrative | 🔴 A14 | ✅ *(07/08 — front seul ; écran renommé « Prêt à terminer ? », l'administratif part en tête de Paiements ; planche redessinée **écartée** au titre de la réserve 2 d'ADR-0074)* |
| E16US004 | Le public suit **plusieurs** archers, de bout en bout | 🔴 P03 | ✅ *(08/08 — front seul ; **un seul** interrupteur « mes archers / tout » gouvernant les six onglets, ouverture centrée sur les archers suivis ; ADR-0079 ; DETTE-031 élargie)* |
| E16US005 | Placement : la largeur d'un PC, et un puits de réserve | — | ✅ *(24/08 — **une cible par ligne** sur la largeur d'un PC, jetons portant **club · catégorie · blason** (la cause des badges de mixité et de cloisonnement, jusqu'ici invisible), **réserve en panneau collant**, et le **plan de duels aligné** dans le même diff. ⚠️ **Le renvoi ci-contre était juste, et au-delà** : non seulement le puits existait côté serveur, mais la zone, la dépose, la reprise **et** la distinction « mis de côté » / « impossible à placer » étaient toutes livrées — **deux CA sur trois déjà tenus**, désormais couverts par des tests. Le reliquat « position » annoncé **n'existait pas**. **Front seul, aucune migration.** `DETTE-085` inscrite : les deux plans sont des jumeaux recopiés composant par composant, et cette US est la première à payer la copie — à résorber avec `DETTE-083`)* |
| E16US006 | **L'identité visuelle du tournoi : deux logos, deux couleurs** | — | ✅ *(25/08 — **fiche recadrée au cadrage, et presque entièrement réécrite**. Absorbe `E01US016`, jamais livrée : réclamer « un second logo » supposait que le premier existe, or `grep -i logo backend/` rendait **zéro** occurrence. Deux logos facultatifs, deux accents dérivés par le **domaine** (teinte et saturation conservées, clarté ajustée jusqu'au seuil AA), contrôle de contraste **chiffré et non bloquant**, portée **public + salle** seulement. ⚠️ **Trois CA d'origine sur quatre sont tombés** : l'origine FFTA/locale est livrée depuis `E01US023` (enum `OrigineBrique`, deux listes séparées, l'origine suit à la copie), et *clubs* / *barèmes* n'ont **aucun porteur**. ⚠️ **Un défaut trouvé par le test d'API** : `reglee` circulait comme drapeau sur trois couches, si bien que déposer un logo faisait passer le tournoi pour « réglé » — remplacé par une valeur absente. ⚠️ **`charte.test.ts` étendu, pas relâché** : son contrôle ne voyait pas un CSS fabriqué en TypeScript ; les **trois strates** de `DV-06` y sont désormais encodées, vérifiées par mutation. Migration `0050`, [ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md))* |
| E16US007 | Exports : choisir le format de chaque document | 30/08/2026 | ✅ *(catalogue d'exports servi par le serveur — [ADR-0101](../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md) : il porte les **formats**, pas les URL, et ces formats **dérivent du câblage** ; PDF + CSV sur les deux listes, PDF seul sur la feuille de marque, qui entre au passage sur l'écran faute d'y avoir jamais eu de bouton. ⚠️ **Un CA d'origine caduc** (paiement par club) ; le CA *audit consultable en cours* avait été déclaré caduc **à tort** — aucun écran ne consomme la route — et reste **dû** (`E16US016`) ; découpée en `E16US014` / `E16US015` / `E16US016`. `DETTE-095`. Aucune dépendance, aucune migration)* |
| E16US014 | Podiums configurables | 31/08/2026 | ✅ *(trois portées **cumulables** — toutes catégories · catégorie · club — et une profondeur réglable, sur les quatre surfaces du palmarès ; migration `0052`, défauts serveur = comportement d'E06US004, [ADR-0103](../docs/adr/0103-la-portee-d-un-podium-est-un-reglage-du-tournoi.md) qui **révise ADR-0067 §5**. Coupée en deux au cadrage : les **clubs entre eux** → `E16US017`. Les équipes restent hors périmètre, EPIC-13. ⚠️ **Cinq passes de revue, trois bloquants** : le même défaut s'y est déplacé quatre fois — un prédicat qui énonçait quelque chose sur une population à partir d'une autre. `DETTE-096` et `DETTE-097` ouvertes au passage)* |
| E16US017 | Le classement des clubs entre eux | 04/09/2026 | ✅ *(tranche B d'`E16US014`. Les clubs se classent entre eux au **décompte de médailles**, ordre olympique, sur les quatre surfaces du palmarès (écran, public, salle, PDF). **Trois arbitrages tranchés au cadrage** — [ADR-0104](../docs/adr/0104-le-classement-des-clubs-se-compte-en-medailles-inter-clubs.md) : (1) l'or décerné deux fois quand *scratch* et *catégorie* sont cumulés **compte deux fois** — la question laissée ouverte par la fiche ; (2) la portée *club* est **exclue** du décompte, un or gagné contre ses propres coéquipiers ne comparant aucun club à un autre — et sans portée inter-club le classement **n'existe pas**, ce que l'écran dit au lieu d'afficher tout le monde à zéro ; (3) trois métaux seulement, la 4ᵉ place du podium par défaut ne rapportant rien. ⚠️ La garde d'`E16US014` sur la lecture du référentiel des clubs **tombe** (il faut nommer les clubs dès qu'une portée inter-club est réglée), et `DETTE-029` gagne un **5ᵉ site**, ligne élargie)* |
| E16US015 | Un QR par scoreur | — | ⬜ *(sortie d'`E16US007` le 30/08/2026 ; le jumeau existe — QR SVG par **cible**. ⚠️ **Question de sécurité à trancher** : un code scoreur est un secret personnel)* |
| E16US016 | Exports : les formats et documents qui restent dus | — | ⬜ *(reliquat d'`E16US007`, 30/08/2026 : palmarès en tableur (**renommage d'une route publique** à arbitrer, `DETTE-031` en vis-à-vis), export du journal d'audit, format `xlsx` (**règle 11**). Petite par construction : `E16US007` a livré le mécanisme)* |
| E16US008 | Feu vert : agir depuis la ligne du duel qui bloque | 28/08/2026 | ✅ *(chaque ligne bloquée porte **le geste qui la lève** — le duel amont se **déplie sur place** (occupants + cible) et porte le bouton de forfait, « cible non attribuée » renvoie au plan de duels, « adversaire non déterminé » n'offre rien (cela se répare à la composition). Autorisation **élargie, pas doublée** : `POST /forfaits/duel` et son annulation acceptent admin **ou** scoreur (`autoriser_forfait_duel`, jumelle d'`autoriser_saisie`), `declare_par = "Administrateur"`. ⚠️ **Deux constats de cadrage, dans le code, contre la fiche** : (a) « ouvrir le duel amont » est **impossible** — `SaisieDuels` n'est monté que dans `EspaceScoreur`, derrière un code scoreur, donc le lien aurait posé l'organisateur devant un écran de connexion ; d'où le dépliage sur place ; (b) au **tour ≥ 2** aucune cible n'est attribuée (garde délibérée, `DETTE-019`), donc « cible non attribuée » n'y est levable par **aucun** geste — la ligne **dit la limite** au lieu d'offrir une fausse porte. ➡️ Le CA « déclenchement automatique » est **sorti au cadrage** vers `E16US013` (fiche neuve) : c'est un changement de moteur, personne n'évalue les conditions côté serveur aujourd'hui. `DETTE-017` élargie à **5 sites** (dont un **4ᵉ jamais inscrit**, `pilotage_tour.py`) et `DETTE-019` à un **3ᵉ site, dans le front**. Aucune migration)* |
| E16US009 | Écran de salle : régler ce qui défile, et défiler ce qui ne tient pas | 26/08/2026 | ✅ *(pagination réglable par écran + tête figée de 3 — [ADR-0098](../docs/adr/0098-un-ecran-projete-pagine-au-lieu-de-defiler.md), migration `0051`, `DETTE-039` résorbée sur son volet technique)* |
| E16US010 | Chercher partout, et voir d'avance ce qui bloque un lancement | 29/08/2026 | ✅ *(recherche transverse à trois entités avec ouverture de la fiche — [ADR-0100](../docs/adr/0100-une-destination-d-admin-porte-l-element-qu-elle-ouvre.md), l'élément ouvert entre dans l'adresse ; pastille de complétude en liste **dérivée** du jalon `démarrer` (ADR-0096), une route d'agrégat ; doublons signalés **sur la ligne**, écran dédié retiré ; fiche d'archer en consultation au pilotage. ⚠️ **CA « déclarer un forfait » non livré ici** — route réservée au scoreur en qualification ; ✅ **levé le 30/08/2026** avec `E16US007`, sur décision du commanditaire (route élargie, geste posé sur la fiche d'archer). `DETTE-006` élargie. Aucune migration)* |
| E16US013 | Le lancement d'un tour : automatique ou manuel, au choix | — | ⬜ *(**fiche neuve**, sortie d'`E16US008` au cadrage du 28/08/2026. Candidate à un **ADR** : le lancement cesse d'être un geste pour devenir une politique. ⚠️ Trois questions à trancher avant d'implémenter, aucune dans le questionnaire — qui évalue les conditions côté serveur, que fait l'automatique d'un duel bloqué, et la maille « par tour » a-t-elle un support persistant)* |
| E16US011 | Ce que trois questionnaires « validés » demandaient quand même | — | ⬜ *(**rattrapage** : sept règles classées « validées tel quel » à tort, dont **deux contradictions à arbitrer** — S08 contre un endpoint vivant, A09 contre ADR-0014/0015)* |
| E16US012 | La famille des écrans « prêt à… » | — | ✅ *(forme instruite + `démarrer` livré ; `terminer` migré. `archiver` et `exporter` restent à brancher — ADR-0096)* |

> Les retours **écartés** et les questions **restées sans réponse** sont listés en fin de
> [`stories/E16`](../stories/E16-retours-maquettes.md) : aucun questionnaire ne reste sans suite.
> Deux écrans remontés par le dossier de maquettes ne sont **spécifiés nulle part** — le **barrage**
> (égalité 5–5 en duel) et le **conflit de saisie** (deux postes sur la même volée) : ils sont
> maquettés, pas décidés.

## Fidélité aux maquettes (EPIC-17) — 🔶 **en cours (4/10)**

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
| E17US005 | Embarquer la **police du club** pour le jour J (`DV-07`) | J3 | 🔒 *(**spécifiée, pas prenable** — arbitrage d'ajout d'actif en attente, règle 11 ; 3 options soumises dans la story)* |
| E17US006 | Donner une couleur à l'**action destructrice** | J3 | 🔒 *(**spécifiée, pas prenable** — trou de la charte, ADR attendu ; `DV-03` exclut le rouge et rien ne couvre le cas)* |
| E17US007 | **Résorber** les écarts relevés sur les écrans d'administration | J3 | ⬜ *(le relevé est fait depuis le 06/08 ; c'est l'US qui le solde qui manquait — A06, A09, A12, A08, A04, A17)* |
| E17US008 | Confronter les **9 planches de saisie** `S**` et résorber | J3 | ⬜ |
| E17US009 | Confronter les **7 planches publiques** `P**` et résorber | J3 | ⬜ |
| E17US010 | Empêcher le dossier de maquettes de **dériver** du produit | J3 | ⬜ *(resynchroniser `appareils.js` **et** rendre la dérive mécaniquement détectable ; **à prendre avant** E17US008/E17US009)* |

## Ajout du 15/08/2026 — Atlas du projet — 🔶 **en cours (3/5)**

> Demande du commanditaire, hors file d'exécution : *« je ne vois pas bien l'état réel du projet,
> et son historique »*. Outillage de suivi, pas une capacité produit — ces US **n'entrent pas** dans
> la file 🎯 ci-dessus, qui reste celle du produit ; elles se prennent quand le commanditaire le
> décide. Cf. [`stories/E00-socle.md`](../stories/E00-socle.md) § E00US018 et
> [ADR-0086](../docs/adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md).
> Livrée le 15/08 : le règlement en vigueur, l'histoire datée de chaque règle, les 83 décisions avec
> **ce qui les a amendées depuis**, et la confrontation de ce que l'écrit promet à ce que le dépôt
> contient. Ouvre `DETTE-067`.
> Livrée le 16/08 : l'**avancement** — les US section par section, l'ordre des epics, la dette
> ouverte, une fiche par US — et le **garde-fou de cohérence** entre les quatre livrables de
> suivi, compteurs recalculés compris. Trois défauts réels trouvés le jour même.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US018 | L'atlas : le règlement en vigueur et l'histoire des décisions | hors jalon | ✅ |
| E00US019 | L'atlas : l'avancement, et des livrables de suivi qui ne se contredisent pas | hors jalon | ✅ *(compteurs recalculés et **bloquants**, graphe des epics en réduction transitive, fiche par US ; a trouvé le compteur J3 faux, deux US livrées restées hors jalon, et deux `DETTE-065` sur `main`)* |
| E00US020 | L'atlas : la carte du code | hors jalon | ✅ *(matrice de dépendances lue à l'AST et **sens des dépendances bloquant** — la règle 2 n'était vérifiée que pour le domaine ; 60 ports appariés structurellement à leurs adapters ; graphe des features du front. A mesuré 3 nœuds d'enchevêtrement, dont un de **19 features sur 44**)* |
| E00US021 | Atlas — le métier (cycles de vie, énumérations, entités) | hors jalon | 🎯 *(cible, sans fiche détaillée — prochaine tranche de l'atlas)* |
| E00US022 | Atlas — les flux (saisie → file d'écriture → WebSocket) | hors jalon | ⬜ *(cible)* |

## Ce que la carte du code a révélé (16/08/2026) — ⬜ **à planifier (0/4)**

> Ces quatre US **n'existent que parce qu'`E00US020` les a mesurées**. Elles ne sont dans aucun
> jalon et ne se prennent pas d'elles-mêmes : elles attendent l'arbitrage du commanditaire.
> `E00US025` demande en outre une décision **avant** de coder (ajout de dépendance, règle 11).

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US023 | Nommer le noyau partagé du front, et défaire les enchevêtrements | hors jalon | ⬜ |
| E00US024 | Sortir la logique des quatre composants XXL du front | hors jalon | ⬜ |
| E00US025 | Le contrat DTO front ↔ back, vérifié plutôt que recopié | hors jalon | ⬜ |
| E00US026 | Rallier le JavaScript de l'atlas à l'outillage du front (`DETTE-067`) | hors jalon | ⬜ |

## Ajout du 27/08/2026 — Qualité de lecture, code **et documentation** — 🔶 **en cours (1/4)**

> ⚠️ **Section élargie le 30/08/2026.** Elle ne portait que le **code** (`E00US027`, ADR-0099).
> La revue d'`E16US007` a montré que le raisonnement chassé du code avait été déversé dans une
> documentation que rien ne vérifie non plus : un fait unique écrit dans **11 documents sur 13**.
> [ADR-0102](../docs/adr/0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) étend la
> décision, et trois US la portent.

> Née d'une question du commanditaire après les **trois passes de revue** d'`E16US009` : *« pourquoi
> autant de passes ? »*. La mesure a montré que la majorité des remarques de 2ᵉ et 3ᵉ passe portaient
> non sur du code mais sur des **documents qui se contredisent** — dont des commentaires que rien ne
> vérifie. D'où une règle d'écriture, et un lot démonstratif.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US027 | Le code porte des pointeurs, pas le raisonnement | hors jalon | ✅ *(règle 13 + [ADR-0099](../docs/adr/0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md) : un commentaire ne survit que s'il porte une **contrainte non déductible**, un **avertissement**, ou un **renvoi d'une ligne**. Le reste vit déjà ailleurs — `git` pour l'historique, `stories/` pour les CA, l'ADR pour le raisonnement, `docs/dette.md` pour l'archéologie. ⚠️ **On ne coupe que ce qui existe ailleurs** : le décompte de chrome de `LIGNES_PROJETEES_MAX`, qui ne vivait que dans un commentaire, a été **déplacé** dans `DETTE-086` avant d'être retiré. Appliquée **au dépôt entier** après arbitrage du 27/08/2026 (plafond de **8 lignes** par bloc, « tout, maintenant ») : le cliquet backend passe de **1 086 blocs à 0**, le front de **453 blocs sur 236 fichiers à 0**. La règle est **dure des deux côtés** et vérifiée — `test_commentaires_bornes.py` (pytest, tout le code de production) et `commentaires.test.ts` (vitest, tout `frontend/src`, tests compris). ⚠️ Le chiffre « 103 » annoncé en 1ʳᵉ passe était le **reliquat** au moment d'une reprise, pas le total : corrigé en revue. Mesure d'entree : **36 %** de commentaire sur le code de production (39 206 / 108 118 lignes) et **151 fichiers** au-dessus de 40 %, dont **103 cote backend** — une premiere mesure disait 13 %, elle ne voyait aucune docstring Python)* |
| E00US028 | Un ADR qui nomme du code disparu fait rougir la CI | hors jalon | ⬜ *(née de la revue d'`E16US007`, 30/08/2026 — [ADR-0102](../docs/adr/0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) §3. ⚠️ **Le contrôle existe déjà** : `portage-symbole-absent` (`backend/atlas/controles.py`) rend **22 constats** et vit en sévérité `SIGNAL`, noyé dans un lot de 45 que personne ne lit. L'US solde les 22 et le passe **bloquant**. Ferme la limite écrite en dernière ligne des Notes d'`E00US027`, sur sa première moitié)* |
| E00US029 | Une fiche fonctionnelle décrit ce qui existe, jamais ce qui manque | hors jalon | ⬜ *(née de la revue d'`E16US007`, 30/08/2026 — [ADR-0102](../docs/adr/0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) §2. Source de pourrissement n° 1 mesurée : deux fiches livrées affirmaient qu'un geste n'existait pas alors qu'il venait d'être livré)* |
| E00US030 | Un fait, un lieu : la charte des documents | hors jalon | ⬜ *(née de la revue d'`E16US007`, 30/08/2026 — [ADR-0102](../docs/adr/0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) §1 et §4. **Mesuré** : 13 documents touchés par une US, dont **11** énonçant le même fait. ⚠️ **US structurante** — touche `CLAUDE.md`, et une question revient au commanditaire sur `00-resume-projet.md`, qui est un livrable. À prendre **après** `E00US028` et `E00US029`)* |

## Résorptions de dette planifiées (arbitrages du 07/08/2026)

> Quatre questions ouvertes du registre ont été **tranchées par le commanditaire** à la revue
> d'E01US025. Elles ne sont pas dans le jalon courant : elles sont ici pour que « reprend les US »
> les retrouve, et parce qu'une décision non planifiée se reperd.

| US | Titre | Résorbe | État |
|---|---|---|---|
| E05US023 | **Rendre jouables** poules, suisse, colline, Big Shoot Off — **et composables à l'atelier** | `DETTE-028` | ✅ *(**découpée le 09/08/2026 en quatre tranches**, comme annoncé — 4 moteurs × 2 surfaces ne tenant pas dans une branche : poules (`E05US023`, 09/08), Big Shoot Off (`E05US028`, 14/08), système suisse (`E05US026` + `E05US030`, 15-16/08), colline (`E05US027`, 22/08). **Les quatre sont livrées.** ⚠️ **Mais `DETTE-028` n'est refermée que sur son volet « moteurs de formats »** : le volet **politiques** subsiste — `ScoreAvecHandicap` et `RoutingRepechage` inertes, `classement.py` hors famille `scoring` — et **il n'a aucune US inscrite**. Ne pas lire cette ligne comme la fermeture de la dette.)* |
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
- **🔒 US bloquée sur un arbitrage** : elle est **spécifiée** dans `stories/` mais **pas prenable**
  tant que l'utilisateur n'a pas tranché (ajout d'actif — règle 11, choix métier, trou de charte).
  Elle compte au dénominateur d'un jalon comme une ⬜ : le travail existe, il est seulement en
  attente. Deux à ce jour : `E17US005` (police), `E17US006` (couleur destructrice).
- **⛔ US absorbée** : la capacité a été livrée par **une autre US**, celle-ci n'existe donc plus
  comme unité de travail. À distinguer de **caduque** (`E10US004`), où la capacité elle-même n'a
  plus d'objet. Une US absorbée n'est **ni ✅ ni ⬜** : elle est **hors décompte** (voir la règle de
  comptage ci-dessous). Quatre à ce jour : `E05US016`, `E05US018`, `E05US019`, `E12US004`.
- **`~~barré~~`** : l'identifiant ou le titre est barré quand l'US est **absorbée, caduque ou déjà
  faite** dans une file de priorité — le texte barré est conservé pour que la référence reste
  trouvable, jamais supprimé. Le **glyphe d'état n'est pas barré** (sinon l'état devient illisible).
- **Règle de comptage d'un jalon** : `n/N` compte les **lignes portant un identifiant d'US**
  (colonne `Seq` quand le tableau en a une — celui de J0 n'en a pas), **US absorbées exclues**. Une
  ligne **sans identifiant d'US** (relevé, lot hors US — ex. « Relevé d'écarts des 19 planches
  admin » d'EPIC-17) ne compte **ni au numérateur ni au dénominateur** : c'est du travail livré, pas
  une US. Les lignes à `Seq = —` (US hors séquence, remontées d'une section d'ajouts) sont comptées
  **dans leur section d'origine**, pas dans le jalon — sans quoi la même US serait comptée deux
  fois. C'est cette règle qui donne J0 12/12, J1 46/46, J2 14/14, J3 25/26 et J4 0/7.
  *(J3 corrigé **deux fois** le 16/08/2026, par deux modes de panne différents, tous deux
  trouvés par le recalcul automatique d'`E00US019` et non à l'œil. **1.** Le compteur disait
  `12/15` quand le corps portait 14 ✅ sur 16 lignes — l'en-tête n'avait pas suivi le corps.
  **2.** `E05US026` et `E05US028`, livrées, n'existaient que dans la **file d'attente** — un
  tableau en citation, qu'aucun compteur ne lit. Elles ont été insérées ici (`76septies`,
  `76octies`), d'où `16/18`. Ce second mode est propre au total annoncé en tête : il gonflait
  « 111 US livrées » sans faire bouger un seul `n/N`, donc rien ne le contredisait.)*
  *(Les deux précisions — « quand le tableau en a une » et « ligne sans identifiant » — ont été
  ajoutées en revue le 08/08/2026 : à la lettre, la version initiale rendait `0/0` pour J0, dont le
  tableau n'a pas de colonne `Seq`, et ne disait pas comment traiter la ligne de relevé d'EPIC-17.)*
  *(Instituée le 08/08/2026 : trois compteurs sur cinq étaient faux, chacun d'un mode différent —
  en-tête mise à jour sans le corps (J3), US absorbée comptée au dénominateur (J4), lignes ajoutées
  sans toucher l'en-tête (démo 27/07). Sans règle écrite, chaque correction en rouvrait une autre.)*
- *« fait en avance »* : US traitée avant son rang de séquence (dépendance ou opportunité).
- *« définie en `stories/`, non implémentée »* : le fichier de spec existe (créé à l'entretien du
  18/07) mais aucun code n'est livré — ne pas confondre présence en `stories/` et US faite.
  ⚠️ Piège pour toute vérification automatique : `E00US016`, `E01US018` et `E01US019` ont un commit
  `docs(...)` **dans `main`**, donc un `grep` sur `git log` les compte comme livrées. Elles ne le
  sont pas.
