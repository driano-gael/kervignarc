# EPIC-17 — Fidélité de l'application aux maquettes

- **ID** : EPIC-17
- **Statut** : En cours *(la charte est posée ; la confrontation écran par écran reste à faire)*
- **Priorité** : MVP *(l'application est montrée au club ; elle ne ressemble pas à ce qui a été validé)*
- **Dépend de** : EPIC-14 (ossature admin à trois axes), EPIC-16 (retours du questionnaire)
- **Réfs** : [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) ·
  [`maquettes/`](../maquettes/) · [`cahier-des-charges-design.md`](../cahier-des-charges-design.md) §3.3

## Objectif / valeur

**Distinguer cet épic d'[EPIC-16](EPIC-16-retours-maquettes.md) : celui-ci traite les retours *sur*
les maquettes, celui-là amène le *produit* jusqu'aux maquettes.** Les deux sont nés du même dossier
et se lisent facilement l'un pour l'autre — ce sont pourtant deux directions opposées.

Le dossier de maquettes le disait déjà, sans que personne n'en fasse une suite :

> *« "Écran existant" ne veut pas dire "conforme". La mention signale qu'un composant du même rôle
> vit dans `frontend/src/features/` — elle ne dit rien de la ressemblance entre l'écran livré et la
> maquette. **Confronter les deux reste à faire.** »*
> — [`maquettes/README.md`](../maquettes/README.md)

La confrontation a été faite le 05/08/2026 et l'écart de départ était **total** : le front tournait
encore sur le socle du walking skeleton — accent violet `#aa3bff`, fond blanc, `system-ui` — parce
que les « US design » annoncées en tête d'`index.css` n'avaient jamais été écrites. Aucune des 98 US
livrées n'avait de raison de s'en apercevoir : chacune était conforme à *son* CA.

## Périmètre

### Inclus

- **La charte, posée une fois pour toutes** : jetons, thème de référence, typographie (E17US001).
- **La confrontation planche par planche** des 36 écrans, et la correction des écarts de mise en
  page et de hiérarchie de l'information.
- **Le maintien de la correspondance** : `maquettes/assets/appareils.js` se désynchronise d'`axes.ts`
  à chaque US qui renomme une destination — la resynchronisation fait partie de l'épic.

> ⚠️ **Méthode — lire le questionnaire avant la planche.** Une planche montre **plusieurs partis
> pris** ; c'est le questionnaire qui dit lequel a été **retenu**, et la réponse est parfois
> « **telles que livrées** » — c'est-à-dire le front lui-même. Cas vérifié sur **A00** : le
> commanditaire a coché « A — Les quatre portes telles que livrées » et « ✅ Validé tel quel », alors
> que la planche propose à côté une liste verticale à URL affichées. S'aligner sur la première
> variante venue aurait **défait un écran validé**. L'ordre est donc : questionnaire → variante
> retenue → comparaison → alignement. *(Ajouté le 06/08/2026 : la première rédaction de cet épic
> disait « confronter les planches », sans cette précaution.)*

### Exclus

- **La palette elle-même ne se discute pas ici** : elle vient de la charte mesurée, où chaque valeur
  porte son ratio de contraste. La contester est légitime, mais en ADR, pas en US d'écran
  (`cahier-des-charges-design.md` §3.3).
- **L'identité visuelle *par tournoi*** (`E01US016`), qui surcharge ces jetons pour le public et
  l'écran de salle seulement (`D-27`).
- *(Levé)* Les écrans de l'Atelier étaient exclus tant que **DETTE-023** tenait — ils portaient encore
  un identifiant de tournoi côté serveur, donc l'écran maquetté ne pouvait pas exister. La dette est
  **résorbée depuis le 31/07/2026** (E01US023, [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)) :
  les six destinations de l'atelier s'ouvrent sans tournoi. Ils rentrent donc dans le périmètre.
  *(`maquettes/README.md` portait encore l'avertissement inverse au 05/08 ; corrigé dans le même
  commit — c'est exactement le genre de note qui survit à sa cause et fait renoncer à un écran
  faisable.)*

## Capacités

> **Chaque capacité nomme l'US qui la porte.** *(Instituée le 08/08/2026 : six capacités sur onze
> n'en avaient aucune, et comme les cinq restantes étaient cochées, l'épic se lisait comme
> **terminé**. Une capacité sans US n'est pas planifiée — elle ne se fera qu'à la faveur d'un autre
> travail, ou pas du tout.)*

- [x] Poser la charte du club dans l'application (`E17US001`).
- [x] Aligner le catalogue de composants sur les formes des planches (`E17US002`).
- [x] Relever les écarts des 19 planches admin (`A01`→`A19`, ci-dessous).
- [x] A01 connexion + A02 accueil des axes (`E17US003`).
- [x] A13 supervision — la grille de tuiles (`E17US004`).
- [ ] Embarquer **Inter** pour le jour J, sans réseau (`DV-07`) — `E17US005`.
      ⛔ **Arbitrage d'actif en attente (règle 11)** : l'US est spécifiée, **pas prenable**.
- [ ] Trancher la **couleur d'une action destructrice** — trou de la charte (`DV-03` exclut le rouge,
      rien n'est prévu pour ce cas) : aujourd'hui contour ambre — `E17US006`.
      ⛔ **Arbitrage en attente** : ADR attendu, l'US est spécifiée, **pas prenable**.
- [x] **Résorber** les écarts 🔴 des planches `A**` (admin) — `E17US007` : A06 et A09.
- [x] Les quatre écarts 🟠 — tableaux à colonnes A04, A08, A12, bandeau de totaux A17 — `E17US012`.
- [ ] Confronter les 9 planches `S**` (saisie & scoreur) et résorber — `E17US008`.
- [x] Confronter les 7 planches `P**` (public & écran de salle) et résorber — `E17US009`.
- [ ] Resynchroniser `maquettes/assets/appareils.js` sur `axes.ts`, **et rendre la dérive détectable
      mécaniquement** — `E17US010`. *(À prendre **avant** `E17US008`/`E17US009` : elles relisent
      16 planches, autant qu'elles décrivent l'application d'aujourd'hui.)*

> **Compte des planches** : **36** — 1 porte d'entrée (`a00`) + 19 admin (`a01`→`a19`) + 9 saisie
> (`s01`→`s09`) + 7 public (`p01`→`p07`). La formulation « les 19 `A**`, 9 `S**`, 7 `P**` » de la
> version précédente en **oubliait `a00`** et ne couvrait donc que 35 planches — corrigé le
> 08/08/2026 en comptant le dossier plutôt qu'en recopiant un chiffre. `a00` **est confrontée** :
> elle figure au relevé admin ci-dessous, verdict **conforme**.

## Relevé d'écarts — les 19 planches admin (06/08/2026)

Méthode appliquée : **questionnaire → variante retenue → écran livré**. Les écarts ci-dessous sont
mesurés contre la **variante retenue**, jamais contre la première proposition d'une planche. Sources
vérifiées : questionnaires du 04/08, balisage des planches, code des features, et rendu réel au
navigateur pour les écrans atteignables sans jeu de données.

**Hors périmètre d'E17, et pourquoi :**

| Planche | Motif |
|---|---|
| A07 · phases | 🔴 **« à refaire »**, aucune variante retenue — il n'y a rien à quoi s'aligner. `E16US002`. |
| A14 · complétude | **Tranchée le 07/08/2026 par `E16US003`** : l'**écran livré fait foi**, pas la planche. `maquettes/a14-completude.html` a été redessinée le 05/08 **après** le questionnaire et **sans** tour 2 de validation ; elle range les impayés dans une liste « À voir » à côté des contrôles sportifs — donc elle **re-mélange** ce que le commanditaire a refusé. Écartée au titre de la **réserve 2 d'[ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)** (« un arbitrage explicite du commanditaire l'emporte sur la planche »). Ce n'est **pas** un écart de fidélité à résorber ; sa proposition reste une piste pour `E16US008` (feu vert). |
| A10 · plan de salle | 🔴 levé par `E16US001` (le refus portait sur le vocabulaire). |
| A05 · identité | L'écran **n'existe pas** : `E01US016` est ⬜. Ce n'est pas un écart de fidélité, c'est une US non livrée. |
| A00 · portes, A03 · accueil-statuts, A19 · écran de salle | **Conformes.** A03 adapte bien son contenu au statut (`FriseCycleDeVie`) ; A19 porte emplacement, cadence, QR et pilotage. |

### 🔴 Le produit implémente une variante **écartée** — le plus grave

Ces trois écrans ont un parti pris explicitement **non retenu** par le commanditaire. Corriger coûte
une refonte d'écran, mais ne pas corriger, c'est livrer ce qu'il a refusé.

| Planche | Retenu | Livré | Constat |
|---|---|---|---|
| ~~**A13 · supervision** ✅~~ **corrigé** (E17US004) | **B — grille de tuiles** (« 30 d'un œil ») | ~~`<table>` = variante **A**~~ → **grille de tuiles** | Les cibles se lisent désormais en tuiles ; l'IP et la révocation, absentes de la planche, ont été **conservées dans la tuile**. Le tableau des **écrans de salle** reste (A19 est conforme). |
| **A06 · référentiels** 🟡 | **B — panneau latéral d'édition** | édition **en place** = variante **A** | `Blasons.tsx` bascule tout l'écran en formulaire (`if (edition) …`). Le panneau latéral (`.avec-panneau` des planches) n'existe pas dans le front. |
| **A09 · inscriptions** 🟡 | **B — recherche d'abord, liste ensuite** | formulaire puis liste = variante **A** | Ni recherche en tête, ni compteurs d'entrée (« Voir les 156 inscrits », « Non placés · 3 », « Non réglés · 12 », « Doublons · 2 »). |

### 🟠 Les listes du produit ne sont pas des tableaux à colonnes

L'écart le plus **systématique** : les planches présentent les données d'administration en
**carte-tableau à colonnes nommées**, le produit en listes ou en cartes. Cinq écrans n'ont **aucun**
`<table>`.

| Planche | Colonnes attendues | Livré |
|---|---|---|
| ~~**A12 · postes**~~ ✅ **corrigé** (E17US012) | POSTE · TYPE · RATTACHEMENT · APPAREIL · SIGNE DE VIE · JETON | aucune table ; actions « Régénérer un jeton », « Détacher », « Réactiver » non repérées |
| ~~**A08 · scoreurs**~~ ✅ **corrigé** (E17US012) | NOM · CODE D'ACCÈS · ÉTAT · PÉRIMÈTRE · DERNIÈRE VALIDATION | aucune table ; l'impression des accès existe |
| **A15 · bascule de tour** 🟡 | DUEL · CIBLE · ARCHER A · ARCHER B · HEURE, + encart « CE QUI SE FIGE / CONSÉQUENCE » | aucune table (recoupe `E16US008`) |
| **A18 · exports** 🟡 | DOCUMENT · FORMAT · POUR QUI · CONTENU, + « Tout télécharger » | aucune table (recoupe `E16US007`) |
| **A11 · placement** 🟡 | panneaux « Non placés — 3 » et « Contraintes actives » | aucune table (recoupe `E16US005`) |
| ~~**A04 · tournois**~~ ✅ **corrigé** (E17US012) | ÉTAT · NOM · DATE · INSCRITS · CIBLES · AVANCEMENT · CE QUI RESTE | ligne simple + pastille ; **les colonnes de droite supposent des données que l'écran ne va pas chercher** |
| ~~**A17 · paiements**~~ ✅ **corrigé** (E17US012 — bandeau et ancienneté ; export trésorier : `E16US007`) | ARCHER · CLUB · CAT. · TARIF · DÛ · DEPUIS, + bandeau Attendu / Encaissé / Restant dû / Archers concernés, + « Exporter pour le trésorier » | table présente mais colonnes ARCHER · DÛ · PAYÉ · RESTE · STATUT · ACTION ; **ni bandeau de totaux, ni export trésorier, ni ancienneté** — et l'écran est ✅ |

### 🟡 Écarts de forme, peu coûteux

| Planche | Écart |
|---|---|
| ~~**A01 · connexion** 🟡~~ **corrigé** (E17US003) | La planche retient « **formulaire sobre plein cadre** » ; le produit affichait une carte collée en haut à gauche. Désormais colonne centrée, bandeau de titre, libellés visibles, bouton pleine largeur, échappatoire centrée sous la carte. |
| ~~**A02 · ossature** 🟡~~ **partiellement corrigé** (E17US003) | La question « Que venez-vous faire ? » et la ligne de contexte de l'axe Pilotage sont posées. ⚠️ **Le relevé initial se trompait** sur les compteurs : le front affichait **déjà** « N en cours » (`CoquilleAdmin.tsx`) — je l'avais jugé sur un tournoi en **brouillon**, donc sur un état où le compteur ne s'affiche pas. C'est exactement la limite annoncée plus bas (« les écrans sans jeu de données n'ont pu être vus qu'à l'état vide »). Restent hors périmètre : la pastille d'alerte de complétude (`E16US010`) et « 28/30 postes en ligne » (agrégat absent du serveur). |

### Ce que ce relevé ne dit pas

- Il compare des **structures**, pas des pixels : un écran peut être structurellement conforme et mal
  proportionné, et l'inverse.
- Les écrans sans jeu de données n'ont pu être vus qu'à l'état vide ; les écarts de **densité de
  liste** y sont invisibles.
- Un écart marqué « recoupe `E16Uxxx` » **ne doit pas être traité deux fois** : l'US E16 porte déjà le
  besoin, E17 n'ajoute que l'exigence de ressemblance.

## Relevé d'écarts — les 9 planches de saisie (24/09/2026)

Même méthode que l'axe admin — **questionnaire → variante retenue → écran livré** —, mais elle a
buté d'entrée sur un obstacle que l'axe admin n'avait rencontré que sur A02. Sources vérifiées :
questionnaires du 04/08, balisage des planches, code des features, **et l'application réelle**
peuplée d'un tournoi de jeu d'essai (16 archers, 8 cibles, qualification en cours), flèches saisies
à la main.

### ⚠️ Le maillon du milieu a bougé — lire ceci avant d'utiliser le relevé

**Les questionnaires ne décrivent plus les variantes des planches.** Les questionnaires ont été
remplis le **04/08** sur les maquettes **en vignettes** ; les planches ont été **redessinées le
05/08** en écrans pleins. Les lettres n'ont pas suivi. `maquettes/README.md` le signalait pour une
planche (« le questionnaire d'A02 posait encore les questions de la v2 ») ; mesuré sur l'axe saisie,
c'est **4 planches sur 9** dont la **variante retenue** ne se lit plus par sa lettre — `S01`, `S04`, `S06`, `S08` — auxquelles s'ajoute `S05`, dont le refus n'a plus de cible : **5 sur 9** où la lettre du questionnaire ne désigne plus rien d'utilisable. `S02`, `S03`, `S07` et `S09` concordent **sur leur variante retenue**, même quand d'autres lettres ont glissé. ⚠️ **Le chiffre se recompte depuis la table ci-dessous**, et il a fallu **deux** passes de revue pour qu'il le devienne : « 7 sur 9 » puis « 6 sur 9 » n'étaient recalculables ni l'un ni l'autre. Dans l'US même dont l'objet est la fausse certitude qui se transmet comme un fait.

| Planche | Le questionnaire faisait choisir entre | La planche dessine | Effet |
|---|---|---|---|
| **S01** | A « le QR domine » / **B « le code court domine »** / C « liste des cibles libres » | A « Saisie du code » / B « Scan du QR » | 🔴 **lettres inversées** — le retenu est la planche **A**. Le « pourquoi » le prouve (*« pas sûr que les caméras soient accessibles »*). C a disparu |
| **S02** | **A « grille complète, pavé appelé »** / B « un archer à la fois » / C « grille + pavé permanent » | A « Grille complète, pavé appelé » / B « Pavé permanent » / C « une cible à quatre couloirs » | 🟢 **A concorde** (même libellé). B et C ont glissé |
| **S03** | **A « pavé numérique complet »** / B « blason tactile » / C « décroissant contextuel » | A « Pavé à dix touches » / B « pavé réduit au blason » / C « saisie par la cible » | 🟢 **la variante retenue concorde** (« pavé numérique complet » ↔ « pavé à dix touches ») ; ce sont les **non retenues** qui ont glissé — « blason tactile » est devenu **C**, pas B |
| **S04** | **A « feuille appelée par un lien discret »** / B « sélecteur permanent » / C « confirmation à la validation » | A « Choisir le marqueur » / B « Changer en cours de série » | 🔴 **les trois options jugées n'existent plus** |
| **S05** | A « deux colonnes symétriques » / B « score de set dominant » / C « archer actif agrandi » — **aucune retenue** | A « Le duel en set-system » / B « Le pavé de duel » | 🔴 **le refus porte sur des variantes disparues** |
| **S06** | **A « vainqueur et perdant à égalité »** / B « plein écran vainqueur » / C « retour automatique compté » | A « Où tire-t-on ensuite » / B « Après la bascule » | 🟡 aucune lettre ne correspond, mais le refus de C est **déjà intégré** à la planche (*« la barre prévient sans compter »*) |
| **S07** | **A « liste par ancienneté d'attente »** / B « carte unique » / C « groupé par zone » | A « La file d'attente » / B « Validation d'une cible » | 🟢 A concorde par l'intention |
| **S08** | **A « totaux par volée, détail sur demande »** / B « détail flèche à flèche déplié » | A « Validation à la cible » / B « Validation à distance » | 🔴 **ce n'est pas la même question** : densité d'affichage d'un côté, place du scoreur de l'autre |
| **S09** | **A « vocabulaire proposé »** (option unique) | 10 états, sans lettres | 🟢 concorde |

**Conséquence — tranchée en [ADR-0113](../docs/adr/0113-un-arbitrage-se-lit-par-l-intention-pas-par-la-lettre.md),
qui amende la réserve 2 d'ADR-0074 :** sur cet axe comme sur les suivants, la variante retenue se
lit **par l'intention** — le libellé coché et le « pourquoi » —, **jamais par la lettre**. C'est
exactement le piège d'A00 que le CA d'épic nomme (« jamais la première variante venue »), un cran
plus haut : ici même la *lettre* du questionnaire est une fausse piste. Les trois planches où
l'intention ne se traduit plus (**S04**, **S05**, **S08**) n'ont **plus d'étalon** : elles sont
relevées ci-dessous mais **exclues de toute résorption de fidélité** — s'aligner y serait deviner.

**Le geste qui referme ceci** : remplir le **tour 2** des questionnaires `S**` sur les écrans pleins
(les feuilles existent, `maquettes/questionnaires/s0*.html`, et produisent le `.md`). C'est du temps
du commanditaire, donc ce n'est pas une tâche que l'assistant peut prendre — d'où sa place au
tracker, pas ici.

### Hors périmètre de résorption, et pourquoi

| Planche | Motif |
|---|---|
| **S07 · file scoreur** | 🔴 **L'écran n'existe pas** — ni front, ni serveur. Toutes les routes de validation sont **par archer** (`GET /saisie/series/{tournoi}/{archer}`) ; aucune ne rend les cibles en attente, encore moins triées par ancienneté. Comme A05 dans le relevé admin : ce n'est pas un écart de fidélité, c'est une **US non livrée**. ⚠️ **Le tri d'`E16US011` le rangeait parmi les « validés ✅, rien à faire »** — exact sur ses *réponses* (les deux questions ciblées sont restées vides), faux sur son *verdict* : « ✅ validé tel quel — **on peut coder ça** » est un **feu vert**, pas un constat de livraison. Un ✅ sur une planche sans écran veut dire l'inverse de ce que le tri en a conclu |
| **S05 · saisie de duel** | 🔴 **Étalon perdu** (tableau ci-dessus). ⚠️ Et sa critique n'a **aucun destinataire** : *« trop tassé »*, *« les emplacements de saisie de volée sont trop étroits »*, *« au lieu de 2 colonnes je préférerais sur 2 hauteurs, adapté tablette et téléphone »* ne sont portés par **aucune US**, ni E16 ni E17 — S05 n'est ni dans les « retours écartés » d'`E16-retours-maquettes.md`, ni dans une US fille d'`E16US011` |
| **S08 · validation de cible** | 🔴 **Étalon perdu**, et doublement : la variante retenue (« totaux par volée, détail sur demande ») est **contredite par la réponse ciblée de la même feuille** — *« les deux, flèches et total »*. L'écran existe depuis `E16US019` |
| **S04 · marqueur** | Étalon perdu pour le **parti pris** ; les écarts relevés ci-dessous portent sur ce que la planche **actuelle** montre, et sont donc à prendre comme des propositions, pas comme des manquements mesurés |
| **S06 · routage** | **Conforme.** `PanneauRoutage` (`E16US018`, 10/09/2026) porte les trois minutes, le signal non chiffré et la poignée de réouverture — la planche a d'ailleurs été mise à jour ce jour-là. Seule sa **pastille d'état** ment (voir plus bas) |

### 🔴 Un seul défaut de mise en page en produit quatre — l'axe saisie ne prend pas la tablette

C'est le **point de levier du relevé** : quatre écarts distincts ont une cause unique, et elle tient
en deux jetons CSS.

**Mesuré dans l'application** : la coquille `.app[data-monde='tablette']` porte bien
`--largeur-app: 72rem` (1152 px), mais la surface tablette **n'a pas réglé ses deux autres jetons** —
`--largeur-carte` et `--largeur-carte-l` restent au **défaut prudent** (24 rem / 40 rem) que l'en-tête
d'`App.css` décrit comme « celui de l'écran de choix et de tout monde à venir », en demandant que
« chaque surface l'élargisse ou le resserre selon **sa** contrainte physique ». L'**admin** a bien
surchargé les trois ; la **tablette** n'en a surchargé qu'un. Résultat : la grille de saisie est
plafonnée à **640 px** dans une coquille de 1152, et la ligne d'archer fait **575 px** sur un écran
de 1366.

Or la variante retenue de **S02** fonde son choix exactement là-dessus :

> « ce que la tablette permet enfin — à 1280 × 800, **les lignes d'archer font toute la largeur** : le
> nom se lit sans abréger, les flèches sont des cibles tactiles de **40 px**, et le cumul de série
> tient à côté sans rien chasser. »

| Écart | Planche | Livré (mesuré) |
|---|---|---|
| Largeur de la ligne d'archer | toute la largeur de la tablette | **575 px** sur 1366 — 624 px (46 %) de vide à droite |
| Touches du pavé (**S03**) | « plus de **90 px** de large », corps **19 px** | **48 × 48 px**, corps **16 px** |
| Cases de relecture de volée | — | **31 × 21 px** |
| Carte de rattachement (**S01**) | `max-width:520px; margin:40px auto` — **colonne centrée** | carte à `x=145`, **alignée à gauche** |

⚠️ **Vérifié, pas supposé** : régler les deux jetons sur la surface tablette porte la ligne d'archer
de **575 à 828 px**, essayé dans le navigateur avant d'écrire une ligne de code. ⚠️ **Mesure du
jeton seul** : la mise en côte-à-côte du pavé (résorption de l'écart suivant) reprend ensuite une
colonne, et le chiffre livré est **694 px** — cf. le tableau de résorption. Les deux sont vrais, à
des étapes différentes.

⚠️ **L'écart de S01 est le défaut d'A01, déjà corrigé.** `E17US003` a remplacé « une carte collée en
haut à gauche » par une colonne centrée (`.connexion { max-width: 26rem; margin: 0 auto }`) sur
l'écran de connexion. La correction **n'a pas traversé l'axe** : le rattachement du poste, qui est le
même geste (un écran, un champ, un bouton), est resté dans l'angle.

### 🔴 Le pavé de saisie s'ouvre sous la ligne de flottaison

**Mesuré** : toucher un archer ouvre le pavé à **742 px du haut de page**, dans une fenêtre de
**641 px** — la page passe à 1282 px. Le pavé est **entièrement invisible sans défiler**. Or S03
énonce son propre enjeu : « le geste répété **~4 300 fois par départ** : un demi-geste économisé ici
pèse plus que n'importe quelle élégance ailleurs. »

⚠️ **Deux nuances, parce qu'un constat gonflé se retourne contre le relevé.** (a) Le pavé **reste
ouvert et enchaîne** sur la volée suivante : le défilement est payé **une fois par archer**, pas par
volée. (b) La fenêtre de mesure faisait **641 px de haut, pas 800** — Chrome ne descend pas sous
1366 px de large sur le poste de relevé. À 800 px de haut moins la barre du navigateur, le pavé
serait **au ras du bord**, pas confortablement visible : l'écart tient, sa sévérité est à confirmer
sur une vraie tablette.

### 🔴 Le hors-ligne est une pastille de 10 px, là où la planche impose un aplat

**S09** retient « Hors ligne — **aplat ambre plein, sur toute la largeur** », et son verdict tranche
la question de forme : « **l'aplat, pas la bordure** — un bandeau plein se voit du coin de l'œil
pendant qu'on regarde la cible. Une bordure colorée, non. » Le commanditaire a répondu **« non »** à
« l'aplat ambre plein est-il trop agressif ? ». **S02** appelle cette garantie « **la promesse la
plus importante du produit** », « écrite en toutes lettres à l'endroit où le doute naît ».

**Livré** : `IndicateurConnexion` rend une pastille de **10 px** et un libellé de **14 px**, en ligne,
dans l'en-tête, en haut à droite (`.indicateur--deconnecte`). ✅ La règle transverse « jamais la
couleur seule » **est** tenue (`role="status"` + libellé).

⚠️ **Ne pas confondre avec `E17US006`.** `App.css` documente un aplat « essayé et rejeté sur pièce »
— mais c'était l'aplat de l'**action destructrice**, un autre sujet, et celui-là est bloqué sur
arbitrage. Rien n'a jamais été tranché sur le **bandeau hors ligne**.

### 🔴 La ligne d'archer ne porte pas la volée en cours

**Planche S02** : la ligne est `pos | nom | fl fl fl | somme` — les **trois flèches de la volée en
cours** y sont, dont celle en train d'être tapée (`fl saisie`). La ligne **est** la zone de saisie.

**Livré** : la ligne est un **bouton d'ouverture** portant `position | nom | avancement | cumul`, plus
une relecture des volées **closes**. Aucune case de flèche.

⚠️ **La réserve du commanditaire n'est tenue qu'à moitié**, et il faut être précis sur la moitié
tenue. Il l'a écrite **deux fois** dans la même feuille (« pourquoi ce choix » *et* « évolutions
souhaitées ») : *« l'appel du pavé doit se faire à la sélection de **la zone de saisie** »*. Le code
la cite et y a répondu — `Saisie.tsx` explique que le pavé était ouvert d'office sur l'archer A et
qu'il est devenu **appelé**. C'est la bonne moitié. L'autre ne l'est pas : le déclencheur est
**l'archer**, pas la zone de saisie, et l'invite le dit en toutes lettres — « Touchez un **archer**
pour ouvrir le pavé de saisie ». Il n'y a pas de zone de saisie à sélectionner, faute de cases de
flèche dans la ligne.

✅ En revanche la **contre-vérification** (exigence de S02, confirmée « oui » au questionnaire) est
bien rendue : chaque volée close affiche son total et ses trois flèches (`27` / `10 9 8`).

### 🟠 Le cumul affiché n'est pas celui qui a été demandé

Le questionnaire S02 répond à « le cumul de série affiché en permanence est-il utile ? » par
« **en permanence**, c'est un bon rappel sur la cible ». Le code s'en réclame — un commentaire de
`Saisie.tsx` cite la question et se déclare conforme.

**Il ne l'est pas.** Vérifié jusqu'au domaine : `Serie.cumul` est la somme des volées **validées**
(`domain/serie.py`), décision saine et documentée — c'est le score officiel, celui que le départage
du classement compte. Mais avec le grain « validation à la fin de la série », il vaut **0 pendant
toute la série** : à l'écran, 27 points marqués, cumul « 0 ». Le rappel affiche zéro exactement quand
il servirait.

La planche, elle, distingue **trois** nombres : la **somme de la volée** (`27`), le **cumul de
série** (`Cumul série : 55`) et le **total** (`332`). Le produit n'en montre qu'un — et c'est le
seul des trois qui reste à zéro.

⚠️ **Cas d'école de la règle 13** : le commentaire affirme la conformité, et **rien ne le vérifie** —
ni test, ni type, ni compilateur. La phrase a survécu à la livraison.

### 🟡 Écarts de forme, peu coûteux

| Planche | Écart |
|---|---|
| **S01 · rattachement** | Le numéro de cible s'affiche en **16 px / 700** ; la planche l'impose à **48 px / 800** *et dit pourquoi* : « le seul moyen de repérer une tablette posée devant la mauvaise cible **avant que quiconque tire** » |
| **S01 · rattachement** | **L'action principale est le plus petit texte de l'écran** : « Rattacher cet appareil » en **13 px**, contre 18 px par touche du pavé et 13,5 px pour « ← Corriger ». La planche demande un `bouton principal geant` |
| **S01 · rattachement** | L'écran **nomme** au lieu de **demander** : « Poste de saisie » (18 px) contre « **Quelle cible ?** » (26 px / 800). Le verdict de la planche est « **un écran, une question** » — c'est le parti pris, pas une tournure |
| **S02 · poste de cible** | L'en-tête ne porte pas le repère **« Série 2 · volée 8 sur 12 »** de la planche ; l'avancement n'existe que par archer (« 1/20 volées ») |
| **S04 · marqueur** | Le lien discret est conforme, mais il ouvre une **liste nue de quatre noms**. La planche porte la phrase qui justifie le geste — « son nom accompagne chaque volée saisie : c'est la première marque, celle que le scoreur vient contresigner » — et son verdict dit « **sans elle, le geste paraît administratif** ». Le changement en cours de série ne dit pas non plus que « les volées déjà saisies **gardent le nom du marqueur qui les a entrées** » |

### 🟢 Là où c'est la planche qui est en retard

Le CA d'épic tranche : « là où fidélité et usage s'opposent, **l'usage gagne et la planche est
corrigée** ». Trois cas, et le premier porte une information devenue **fausse**.

- **Le pavé alphanumérique de S01 n'est pas dessiné.** Le produit en a un, à alphabet désambiguïsé —
  ni `I`, ni `O`, ni `0`, ni `1` —, ce qui est exactement l'évolution demandée au questionnaire
  (« un pavé de saisie ok **mais qui ne laisse pas de caractère non accessible**, adapté tablette et
  téléphone »). ⚠️ **Effet de bord** : la planche « Code refusé » donne comme **première cause, par
  ordre de fréquence**, « le **0** et le **O** se confondent ». Cette cause est devenue
  **impossible** — aucun des deux caractères n'est saisissable. La planche affirme un diagnostic que
  le produit a rendu faux.
- **Le sélecteur de départ du poste** (« Choisissez le départ que sert cette cible ») n'apparaît sur
  aucune planche : ajout d'`E04US002`, légitime, à verser dans S01.
- **Le grain de validation** est affiché (« Validation à la fin de la série »), ce que l'exigence de
  S02 réclamait (`D-11`) — la planche ne le montre pas à cet endroit.

### 🟠 Une transcription documentaire de plus, et elle n'est pas sous garde

**Les pastilles d'état des planches sont fausses, dans les deux sens** :

| Planche | Dit | Réalité |
|---|---|---|
| `s04-marqueur` | « à concevoir » | `SelecteurMarqueur` **existe** (`features/saisie/Saisie.tsx`) |
| `s06-routage` | « à concevoir » | `PanneauRoutage` **existe** depuis `E16US018` (10/09/2026) |
| `s07-file-scoreur` | « **écran existant** » | **aucun écran**, aucun endpoint |

`index.html` en porte une **seconde couche**, par axe. Ces pastilles décrivent l'état du **produit** :
c'est une transcription au sens d'[ADR-0112](../docs/adr/0112-une-transcription-documentaire-se-tient-sous-garde-mecanique.md),
et elle n'est ni sous garde, ni **énumérée** dans `DETTE-110` — dont la liste du hors-garde se
déclare pourtant « **le seul lieu** » où elle vit. La ligne est donc à élargir, pas à doubler.


### Ce qu'`E17US008` a résorbé, et ce qu'elle a laissé

**Résorbé** — cinq écrans touchés (`S01`, `S02`, `S03`, `S04`, `S09`), sous le plafond de six que
l'US se fixe :

| Écart | Ce qui a été fait | Vérifié |
|---|---|---|
| La tablette ne prenait pas sa largeur | `--largeur-carte` / `--largeur-carte-l` réglés sur `.app[data-monde='tablette']`, comme l'admin règle les siens | ligne d'archer **575 → 694 px** |
| Le pavé sous la ligne de flottaison | grille et pavé **côte à côte** dès 60 rem (`.saisie__travail`) ; le pavé reste **appelé**, il n'est pas permanent | pavé à `y=275` au lieu de `y=742`, page **1282 → 896 px** |
| Le hors-ligne en pastille de 10 px | `BandeauHorsLigne` — aplat ambre **pleine largeur** sous l'en-tête, texte « la saisie continue ». ⚠️ **Sur la surface tablette seulement** : ailleurs aucune file n'absorbe l'écriture (le scoreur a la sienne, mais l'indicateur ne la compte pas — `DETTE-112`). Ce n'est **pas** un écart à relever en `E17US009` | **provoqué pour de vrai** (backend coupé) : aplat `#ffd400`, encre `#1d1d1b`, 1104 px |
| Le cumul restait à 0 toute la série | `cumulSaisi` — somme des volées **saisies** ; `Serie.cumul` (validées) reste intact côté domaine | 27 points marqués → **27** affiché |
| `S01` collé en haut à gauche | colonne centrée `.rattachement`, comme `.connexion` pour A01 | |
| `S01` nommait au lieu de demander | « Poste de saisie » → « **Quelle cible ?** », 26 px / 800 | |
| `S01` : action principale minuscule | `.bouton--geant` — 56 px de haut, corps **18 px** (était 13 px) | |
| Numéro de cible en 16 px | **48 px** dans l'état « Rattaché » (S01), **22 px** dans l'en-tête de grille (S02) | |
| `S04` : liste nue de quatre noms | la phrase de la planche, qui dit ce qu'on engage en choisissant. ⚠️ **Livrée comme PROPOSITION, pas comme résorption de fidélité** : `S04` n'a plus d'étalon pour son *parti pris*, et cette phrase est le seul contenu que la planche porte **identique dans ses deux variantes**. À reposer au tour 2 (ADR-0113 §3) | |
| Pastilles d'état fausses | `s04` et `s06` passent à « écran existant », `s07` à « à concevoir » | |
| La planche `S01` portait un diagnostic faux | « le 0 et le O se confondent » réécrit ; pavé désambiguïsé et sélecteur de départ inscrits | |

⚠️ **Un défaut trouvé en chemin, qu'aucun relevé ne cherchait** : la classe `.bascule-theme` existait
dans le JSX **sans aucune règle CSS** — le sélecteur de luminosité de `S01` se rendait
« LuminositéSystèmeClairSombre », d'un seul tenant. Rien ne vérifie qu'une classe posée dans un
`className` existe en CSS ; seul le fait d'ouvrir l'écran le montre. C'est l'argument du CA
« vérification au navigateur », payé une seconde fois après `E17US002`.

**Laissé, et pourquoi** :

- ✅ ~~🔴~~ **Résorbé par `E17US011` (25/09/2026)** — la ligne porte la volée en cours, le pavé est
  ancré en bas de l'écran dès 45 rem (tablette en paysage **et** en portrait) ; les 🟠 ci-dessous se
  ferment avec lui (touches à 87 px en paysage, cf. la fiche), **sauf sur téléphone**, où le pavé
  reste empilé sous la grille. Ce qui suit décrit l'écart **avant** l'US.
- 🔴 **La ligne d'archer ne porte toujours pas la volée en cours.** Le motif est le **périmètre** :
  mettre les trois flèches dans la ligne et y déplacer le déclencheur du pavé, c'est **redessiner
  l'écran le plus utilisé du produit**, pas le rapprocher de sa planche. Une US de fidélité ne fait
  pas ça en cinquième position ; `E17US011` le fait, et y résorbe `DETTE-111` dans le même geste.
  ⚠️ **Ce motif est le second : le premier était FAUX, et sa correction vaut d'être lue.** La 1ʳᵉ
  rédaction invoquait un invariant de revue du 05/08 — « une zone tapable de plus détruit le tampon
  de frappe du pavé ». L'axe adversarial est allé lire le code : les brouillons ont été **remontés
  dans `Saisie`** depuis, et le commentaire qui le dit (`Saisie.tsx`) précise que cela « **supprime
  la classe entière de défauts** ». L'invariant était **mort**, et trois commentaires du code le
  répétaient encore — corrigés ici. Leçon : un motif de report se vérifie **dans le code du jour**,
  comme une section « Porté dans le code par » (ADR-0075). → **`E17US011`**
- 🟠 **« Les lignes d'archer font toute la largeur » n'est tenu qu'à moitié** (575 → 694 px, pas
  1216). La cause est enchaînée à la précédente : tant que le pavé porte seul la saisie, il lui faut
  une colonne, et cette colonne est prise sur la grille. C'est **la résorption de l'écart ci-dessus
  qui débloque celle-ci** — la ligne portant la volée, le pavé rétrécit et rend sa colonne.
- 🟠 **Les touches du pavé restent à 48 × 48 px**, là où S03 promet « plus de 90 px de large ». Même
  chaîne : 90 px par touche demandent la largeur d'une tablette entière pour le pavé.
- 🟠 **Le côte-à-côte ne s'applique qu'au-delà de 60 rem.** Sous cette largeur — téléphone, **et
  tablette en portrait** (768 px) —, le pavé reste empilé sous la grille : l'écart « le pavé s'ouvre
  sous la ligne de flottaison » y est **inchangé, et non mesuré**. Or le questionnaire S02 répond
  « tablette standard **ou téléphone** ». Le commentaire CSS présentait l'empilement comme le cas du
  téléphone, ce qui le faisait passer pour un choix. *(Relevé par l'axe adversarial.)*
- **`S05`, `S07`, `S08`** : hors périmètre, motifs au tableau plus haut. `S07` n'est pas un écart de
  fidélité mais une **US non livrée**.

### Ce que ce relevé ne dit pas

- Il compare des **structures**, pas des pixels — comme celui de l'axe admin.
- **Il n'a pas pu juger la densité à la bonne taille** : Chrome reste bloqué à **1366 px** de large
  et **641 px** de haut sur le poste de relevé, là où les planches se jugent à 1280 × 800. Tout ce
  qui se décide à la ligne de flottaison est donc **mesuré, pas vu**.
- **Les états système n'ont pas été provoqués au moment du relevé** : **conflit, verrou et erreur
  récupérable** ont été lus dans le code et le CSS, jamais déclenchés — un écart de *rendu* y reste
  possible. Le **hors-ligne** fait exception : il a été provoqué pour de vrai (backend coupé) **à la
  résorption**, pas au relevé. *(La 1ʳᵉ rédaction l'énumérait avec les trois autres et contredisait
  le tableau de résorption — relevé par trois axes.)*
- **S05 et S08 n'ont pas été parcourus en salle** : leur étalon étant perdu, une visite n'aurait
  produit que des impressions.

## Relevé d'écarts — les 7 planches publiques (25/09/2026)

Même méthode — **questionnaire → variante retenue → écran livré** —, lue **par l'intention**
([ADR-0113](../docs/adr/0113-un-arbitrage-se-lit-par-l-intention-pas-par-la-lettre.md)). Sources
vérifiées : les sept questionnaires du 04/08, le balisage des planches, le code des features, **et
l'application réelle** peuplée du jeu d'essai « petit » (16 archers, 8 cibles, deux paires
d'homonymes), parcourue au navigateur.

### Le constat d'ensemble : l'axe public a été rapproché **avant** d'être relevé

Contrairement à l'axe saisie, le gros du travail était **déjà fait**, par les US E16 qui portaient
les réserves du questionnaire : `E16US004` (suivre plusieurs archers, interrupteur « mes archers /
tout », filtre par club, récapitulatif repliable), `E16US009` (pages, râteau et compteur projetés,
tête figée des trois premiers), `E16US006` (logos du tournoi). **Trois planches sur sept étaient donc
en retard sur le code**, pas l'inverse — c'est la planche qui a été corrigée (CA d'`E17US009`).

| Planche | Variante retenue (questionnaire du 04/08) | La planche actuelle | Effet |
|---|---|---|---|
| **P01** | **A « recherche puis case c'est moi »** 🟡 | A « Se désigner » / B « Recherche en cours » | 🟢 **concorde par l'intention** ; le suivi de plusieurs archers y est déjà intégré |
| **P02** | **A « maintenant / ensuite empilés »** 🟡 | A « suivi d'un archer » / B « plusieurs » / C « déroulé » | 🟡 aucune lettre ne correspond ; l'intention (empiler, défiler) est en A, les réserves en B et C |
| **P03** | **aucune** 🔴 « à refaire » | A / B | ⛔ **hors résorption** (réserve 2 d'ADR-0074, arbitrage d'`E16US004`) |
| **P04** | **A « ma cible d'abord, plan ensuite »** ✅ | A « Trouver sa cible » | 🔴 **ordre inversé au redessin** : plan d'abord, carte de l'archer en bas |
| **P05** | **A « “mon chemin” en liste »** 🟡 | A « L'arbre » / **B « Le duel de mon archer »** | 🔴 **lettres glissées** : le retenu est la planche **B** |
| **P06** | **A « défilement par pages, tri par nom »** 🟡 | A « Affectations du tour » | 🔴 **la planche rangeait par duel** — l'ancienne B « tri par cible », **écartée** |
| **P07** | **A « classement rotatif par catégorie »** 🟡 | A « Classement en direct » | 🟢 concorde ; la réserve (« 3 premiers toujours visibles ») manquait à la planche |

### Écarts relevés, et ce qui en a été fait

| Planche | Écart | Sens | Traitement |
|---|---|---|---|
| **P04** | le produit n'avait **pas de « ma cible »** : un spectateur qui suit un archer devait le chercher dans la grille | 🔴 produit en retard | **résorbé** : carte des places suivies **avant** la grille, cible marquée « vos archers » en toutes lettres (`DV-03`) — `mesPlaces`, `PlanCiblesPublic` |
| **P04** | la planche regroupait la salle en « pas de tir A / B » | 🟢 planche en retard | **planche corrigée** : le gabarit est une **liste** de cibles (ADR-0073), l'écran ne peut pas savoir quelles cibles forment une rangée |
| **P01** | une ligne de résultat ne portait **que le nom** — deux homonymes (fréquents dans une famille) indistinguables | 🟠 produit en retard | **résorbé** : « club · catégorie » sous le nom (planche B, « le club en second ») — `identiteSecondaire` |
| **P02** | la carte suivie ne portait pas non plus le club et la catégorie (planche A) | 🟠 produit en retard | **résorbé**, même règle, même fonction |
| **P01** | « Aucun résultat » ne donnait qu'une cause | 🟡 forme | **résorbé** : l'inscription « peut-être pas encore enregistrée » est dite |
| **P05** | chaque tour portait une heure (« demi-finale — 15 h 10 ») | 🟢 planche en retard | **planche corrigée** : réponse du 04/08, un horaire « seulement pour les départs des différentes phases » |
| **P06** | planche : dix affectations par duel, 12 s | 🟢 planche en retard | **planche redessinée** sur l'écran livré : tri par nom, râteau et compteur en grand, 40 noms et 20 s réglables |
| **P07** | planche : huit lignes fixes | 🟢 planche en retard | **planche redessinée** : tête figée des trois premiers, le reste pagine |
| P01, P02, P06, P07 | pastilles « à concevoir » sur des écrans livrés | 🟢 | passées à « écran existant » |

### Laissé, et pourquoi

- **P02 · le rang provisoire et « volée 8 sur 12 »** de la planche A ne sont pas dans la carte de
  suivi. Ils viennent du **redessin du 05/08**, jamais validé (pas de tour 2), et le parti pris
  retenu — « maintenant / ensuite » — ne les nommait pas : c'est une **proposition** de la planche,
  pas un manquement mesuré (même statut que `S04`, ADR-0113 §3). ⚠️ Le rang demanderait en plus une
  lecture du classement par archer suivi (`DETTE-031`). **À reposer au tour 2.**
- **P02 · l'état « Vous ne suivez personne »** centré, avec un bouton : le produit garde sa phrase
  d'introduction et la recherche visible d'emblée. Écart de forme, sans perte d'information.
- **P02 · « les six onglets sur 342 px »** : la planche pose une question (menu, barre du bas,
  défilement) **à laquelle personne n'a répondu**. Pas d'étalon.
- **P05 · l'arbre « un tour à la fois »** (planche A) n'est **pas** la variante retenue.

### Ce que ce relevé ne dit pas

- **L'écran de salle n'a pas été jugé à sa distance d'usage** — le CA le demande (1920 × 1080, lu à
  plusieurs mètres). Chrome reste bloqué à **1366 px** sur le poste du relevé ; P06 et P07 ont été
  confrontés **au code et au CSS**, pas vus projetés. **Ce contrôle reste à faire en salle.**
- Il compare des **structures**, pas des pixels, comme les deux relevés précédents.
- L'appli publique a été parcourue à **1366 px** de large, pas sur un téléphone de 360 px : la
  planche se juge sur téléphone.

## Critères d'acceptation (epic)

- Un écran livré et sa planche sont **superposables** : mêmes zones, même hiérarchie, mêmes formes,
  aux écarts documentés près. **La densité fait exception** : le commanditaire a demandé en A02 « plus
  d'espace, plus aéré […] pour tous les écrans », donc le produit est **volontairement plus aéré** que
  les planches, et c'est la planche qui est en retard.
- Aucune couleur du front n'est écrite hors de la charte ; les jetons sont **sémantiques**, jamais
  des noms de couleur.
- Tout écart assumé est **écrit** — registre de dette ou note de planche —, jamais laissé au constat.

## Risques

- **Les planches vieillissent pendant qu'on les relit.** Le cas s'est déjà produit (A15, corrigée le
  jour même où E12US002 a livré le feu vert). Vérifier `git log main --first-parent` quand un écran a
  l'air d'avoir bougé.
- **Trois arbitrages du dossier restent ouverts** (noms des trois axes, niveau sous l'axe,
  étanchéité de l'Atelier le jour J). Les écrans qu'ils touchent ne peuvent pas être figés avant
  réponse — ADR-0074 rend les planches opposables, il ne tranche pas ces trois points.
  *(Le « verdict d'A01 », longtemps compté comme quatrième, **a été rendu** : le questionnaire du
  04/08 coche « A — Formulaire sobre plein cadre » et « 🟡 validé avec réserves ». C'est
  `maquettes/README.md` qui était périmé, et cet épic l'avait recopié — corrigé à la revue
  d'E17US003.)*
- **La fidélité peut se retourner contre l'ergonomie.** Une planche est jugée à l'arrêt ; un écran de
  saisie est jugé une flèche à la main, à 3 m d'une cible. Là où les deux s'opposent, l'usage gagne
  et la planche est corrigée — pas l'inverse.
