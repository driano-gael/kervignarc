# Cahier des charges — Visuel & Ergonomie — Kervignarc

**Solution logicielle de gestion de tournoi de tir à l'arc en salle (18 m)**

| | |
|---|---|
| **Version** | 0.3 (design — **charte réelle versée** ; l'architecture d'expérience reste au CDC UX) |
| **Date** | 14/07/2026 |
| **Statut** | À valider par le client · **charte instruite** (`Q-D4` fermée) · questions ouvertes `Q-Dn` (§10) |
| **Sources** | `cahier-des-charges.md` (fonctionnel v0.3), `cahier-des-charges-technique.md` (v0.2), entretien design du 08/07/2026, entretien de conception du 14/07/2026, **éléments graphiques fournis le 14/07/2026 (`docs/elements_design/`) + arbitrages client du même jour** |
| **Documents liés** | **`cahier-des-charges-ux.md` (UX v0.2)** — architecture d'expérience, layouts, règles d'interaction |
| **Nouveautés v0.3** | **La charte cesse d'être un emplacement vide.** Les éléments réels du club et de l'événement sont versés (§3) et **mesurés** : le rouge club **échoue au contraste sur le fond de sa propre charte** (2,55:1), d'où une palette applicative **dérivée** (§3.3). Ajout : **registre des décisions visuelles `DV-nn`** (§11), **thèmes** (§7.1) et **identité par tournoi** (§3.6). **`Q-D1`, `Q-D4` et `Q-D8` fermées.** |
| **Périmètre** | **Identité visuelle et système de design** : charte, tokens, composants, accessibilité, thématisation, microcopie. **Ne traite plus** l'architecture d'expérience (combien d'applis, navigation, layouts, règles d'interaction) : c'est **`cahier-des-charges-ux.md`**. |

> **Document vivant.** Chaque décision visuelle porte un identifiant **`DV-nn`** (registre §11) avec sa version
> d'introduction ; les questions non tranchées portent `Q-Dn` (§10). **Une décision n'est jamais réécrite
> silencieusement** : elle est remplacée, l'ancienne passant à *Remplacée par DV-nn*. **Historique des
> versions en §12.**

> 📐 **Les ratios de contraste de ce document sont calculés, pas estimés** (WCAG 2.1, luminance relative).
> Ils sont **reproductibles** : toute couleur ajoutée à la charte doit être passée au même calcul avant d'être
> inscrite ici. C'est ce qui a révélé que trois couleurs de la charte de communication sont inutilisables en
> l'état dans l'interface (§3.3).

> ⚠️ **Répartition des deux CDC design.** Ce document répond à **« à quoi ça ressemble »** (couleurs, typo,
> composants, états, accessibilité). Le CDC UX répond à **« comment c'est structuré »** (applis, navigation,
> écrans, règles). En cas de contradiction entre les deux, **le CDC UX fait foi sur la structure**, ce
> document sur l'identité. Les décisions de structure sont tracées au registre `D-nn` du CDC UX §11.

---

## 1. Objectifs & principes directeurs du design

### 1.1 Objectif
Définir le **périmètre des besoins graphiques et fonctionnels** de l'interface : ce qui doit être dessiné, pour qui, dans quelles conditions, et selon quelles règles d'identité et d'ergonomie — de sorte que la conception UI/UX puisse démarrer sans ambiguïté et rester cohérente sur les 4 contextes d'usage.

### 1.2 Principes directeurs
- **P-1 — L'ergonomie prime sur l'esthétique le jour J.** L'outil est utilisé sous pression, debout, sur des appareils variés. Vitesse et absence d'erreur avant tout.
- **P-2 — Un socle commun, quatre déclinaisons.** Un seul système de design (couleurs, typo, composants) décliné selon le contexte (admin dense / tablette tactile / mobile consultation / écran projeté). On ne conçoit pas quatre produits.
- **P-3 — Registre sportif & dynamique** (décision entretien), tenu par la couleur, le rythme et les données live, **jamais au détriment de la lisibilité**.
- **P-4 — Terrain réel d'abord.** Gymnase, réseau local sans internet, lumière variable, BYOD hétérogène : le design est validé dans ces conditions, pas en studio.
- **P-5 — Accessibilité WCAG AA** comme exigence contractuelle, pas comme option (cf. §6).
- **P-6 — Le temps réel est un élément de design.** Mises à jour live, états de synchronisation, latence réseau : ce sont des composants visuels à part entière, pas des détails techniques.

---

## 2. Contraintes de contexte (ce qui conditionne tout le reste)

### 2.1 Les 4 contextes d'usage — *remplacés en v0.2 par 3 applications*

> ⚠️ **Amendé le 14/07/2026 (`D-01`, `D-02`).** Le découpage en 4 contextes est **remplacé** par
> **3 applications** découpées par **geste** (admin / saisie / public), l'écran de salle devenant un **poste
> de l'appli publique** et non un contexte isolé. Voir **`cahier-des-charges-ux.md` §3**, qui donne la table
> de correspondance C1–C4 → applis (§3.4).
>
> Le tableau ci-dessous **reste utile** comme description des **conditions d'usage** (posture, terminal,
> enjeu ergonomique) — c'est sa lecture *« quatre produits à concevoir »* qui est caduque. Deux corrections
> de fond y sont apportées : le contexte de saisie recouvre en réalité **deux postes distincts** (la tablette
> de la cible et l'appareil itinérant du scoreur, CDC UX §7.2–7.3), et le parc n'est **pas** du BYOD (§2.2).

| # | Contexte | Utilisateur | Terminal | Posture / condition | Enjeu ergonomique dominant |
|---|---|---|---|---|---|
| **C1** | **Pilotage** | Admin / organisateur | PC portable (clavier + souris/pavé) | Assis, poste de commande, concentré | Densité d'information, éditeur de phases, glisser-déposer, prévention d'erreur |
| **C2** | **Saisie** | **Marqueur** (tablette de cible) **et scoreur** (appareil itinérant) | **Parc club, tablette min.** (§2.2) | Debout, près du pas de tir, mains parfois froides | Rapidité tactile, gros boutons, très peu de clics, zéro ambiguïté |
| **C3** | **Consultation** | Archer / public | Mobile perso (BYOD hétérogène) | En mouvement, coup d'œil rapide | « Où je tire / où j'en suis » en < 3 s |
| **C4** | **Projection** | — (affichage passif, **poste piloté** `D-21`) | Écran/vidéoprojecteur de salle | Vu à plusieurs mètres | Lisibilité à distance, hiérarchie forte, auto-défilement |

### 2.2 Conditions matérielles (issues du CDC technique)
- **Réseau local sans internet** → **tous les assets embarqués** : polices, icônes, images. **Aucune dépendance CDN / Google Fonts en ligne.** Contrainte forte sur le choix typographique (§4.3).
- ~~**BYOD hétérogène** → cibler un large parc : tablettes Android/iPad d'âges divers, smartphones d'entrée de gamme.~~ **Amendé le 14/07/2026 (`D-05`, `D-02`)** → **parc de tablettes du club**, avec **interdiction d'y installer quoi que ce soit** (navigateur seul) ; **tablettes personnelles en appoint** en cas de manque ; **taille tablette ou PC garantie**. Conséquences : **pas de mode kiosque** (l'appli vit dans un onglet, ~100 px perdus, fermeture accidentelle possible), **plancher à 768 px pour la saisie** (le smartphone n'est plus une cible — la contrainte des 48 px devient tenable partout), parc **hétérogène malgré tout** (appoint perso) → concevoir défensivement. Détail : **CDC UX §4.1**.
- **Responsive obligatoire, mais par appli** (`D-02`) : saisie ≥ 768 px · public ≥ 360 px · admin ≥ 1280 px. **Chaque appli assume son terrain** au lieu de tout faire partout mal (CDC UX §3.2).
- **PWA, tolérance aux coupures** → prévoir les **états visuels réseau** : en ligne / hors-ligne / synchronisation en cours / échec (cf. §7.2, composant *bandeau de connexion*). ⚠️ Le **raccourci sur l'écran d'accueil** (plein écran, pas de sortie accidentelle) est suspendu à `Q-UX1` — conçu pour l'onglet en attendant.
- **Lumière de salle variable** (décision entretien) → **thème sombre par défaut** (c'est la charte, `DV-02`) **et thème clair** en déclinaison complète, **bascule mémorisée par poste** (`D-26`) : *la lumière varie d'une cible à l'autre*. Écran de salle : sombre. Détail : §7.1.

### 2.3 Impacts directs sur le design
| Contrainte | Conséquence de conception |
|---|---|
| Mains froides / gestes rapides sur tablette | Cibles tactiles **≥ 48 px** (au-delà du minimum AA de 44 px), espacement généreux, pas de geste fin |
| Coup d'œil à distance (projeté) | Échelle typographique dédiée, contrastes renforcés, très peu de texte par écran |
| Réseau local sans internet | Bibliothèque de polices/icônes **auto-hébergée et versionnée** |
| Live + latence | Feedback optimiste + indicateur de synchro visibles |

---

## 3. Identité visuelle *(charte réelle — versée le 14/07/2026)*

> ✅ **`Q-D4` — la seule question bloquante du document — est fermée.** Les éléments graphiques ont été
> fournis (`docs/elements_design/`). Cette section ne décrit plus une structure attendue : elle **verse la
> charte** et en tire les conséquences applicatives, mesurées.

### 3.0 Ce que le matériau fourni apprend — `DV-01`

**Il y a deux marques, pas une.** C'est le fait structurant, et il n'était pas anticipé :

| Dossier | Marque | Matériau | Rôle |
|---|---|---|---|
| `elements_design/club/` | **Les Archers de Kervignac** — le **club** | Banderole, logo | L'**organisateur**. Identité permanente. |
| `elements_design/CDC/` | **Challenge Des Champions** — l'**événement** | Affiche 2025 (« 14 décembre », « Ouvert à tous les archers licenciés », « Venez participer à notre Duels Contest »), logo couronne-cible | Le **tournoi**. Identité **par édition**, datée. |

> ⚠️ **Piège de lecture.** Le dossier `CDC/` **n'est pas** « cahier des charges » : c'est le **Challenge Des
> Champions**. Un agent qui reprend le projet doit le savoir avant d'y chercher des spécifications.

**Conséquence :** la personnalisation par tournoi (`Q-D8`) n'est **pas une hypothèse d'école** — le matériau
prouve qu'un tournoi porte sa propre identité, distincte de celle du club. Elle est traitée en **§3.6**.

**Registre graphique observé** (banderole club) : fond **anthracite**, motif **nid d'abeille** en filigrane,
**coup de pinceau rouge** dynamique, **trajectoires de flèches** en traits blancs fins, logo carré à l'archer
stylisé, et une **signature** : le **« E » de KERVIGNAC remplacé par trois barres rouges** (empennage).
Registre de l'affiche événement : **grunge / stencil**, lettres éraillées, couronne, étoiles.

### 3.1 Marque
- **Nom du club** : **Les Archers de Kervignac**.
- **Nom de l'événement** (distinct) : **Challenge des Champions** — *« Duels Contest »*, édition datée.
- **Nom de la solution logicielle** : *Kervignarc* (nom de l'outil, **interne** — cf. `Q-D9`).
- **Baseline / ton éditorial** : sportif & dynamique (à décliner en microcopie, §8).

### 3.2 Logo — `DV-08`
- **Fichiers fournis** : `docs/elements_design/club/` (logo, banderole — SVG + PDF) et
  `docs/elements_design/CDC/` (logo « sur fond rouge », affiche — SVG + PDF).
- **Le logo se pose sur un aplat rouge, pas sur le fond de page.** C'est l'usage constant de la charte
  (« Logo sur fond rouge ») et c'est **aussi ce que le contraste impose** (§3.3).
- **Co-branding hiérarchisé** (arbitrage client, 14/07/2026) : **l'événement domine, le club signe**. Sur
  l'écran de salle et l'appli publique, le logo du tournoi est au premier plan ; le club apparaît en pied
  (« organisé par les Archers de Kervignac »). **Si le tournoi n'a pas d'identité propre, le club reprend la
  place** — aucune surface ne reste vide.
- Déclinaisons **à produire** : **horizontale** (bandeaux), **carrée/icône** (favicon, écran de salle),
  **monochrome clair** et **monochrome sombre**. `⟦à dériver des SVG fournis⟧`
- **Zone de protection**, taille minimale, interdits d'usage : `⟦À COMPLÉTER — à demander au club⟧`

### 3.3 Palette — la charte **mesurée** — `DV-02`, `DV-03`, `DV-04`

#### 3.3.1 Les couleurs de la charte (telles que fournies)

| Rôle charte | Valeur | Relevé dans |
|---|---|---|
| **Rouge club** | **`#B71918`** | Logo, banderole, affiche (variantes `#b71917`, `#b51d1b` → **normalisées sur `#B71918`**) |
| **Anthracite** | **`#1D1D1B`** | Fond de la banderole, ombres portées du logo |
| **Blanc** | **`#FFFFFF`** · `#F9F9F9` *(cassé)* | Texte et pictogrammes sur aplats |
| **Gris** | `#575756` · `#666666` · `#7C7C7B` · `#D1D1D1` | Motif, dégradés, textes secondaires |

> 🎯 **La référence du rouge est un CMJN, pas un hex.** Le logo **encarte son nuancier imprimeur** :
> **C 19 · M 100 · J 100 · N 11**. C'est **la** valeur de référence de la marque ; **`#B71918` en est la
> traduction écran** (contrôle de conversion : `C19/M100/J100/N11` → `#B80000`, soit **un point de rouge
> d'écart** — la traduction est juste). *Source : `docs/elements_design/analyse-charte.md`, note de conception
> du 14/07/2026.*
>
> **Conséquence pratique :** en cas de doute sur une déclinaison (impression M9, goodies, tenue), **c'est le
> CMJN qui fait foi**, pas le hex de l'appli.

#### 3.3.2 Le verdict du contraste — **le fait central du document**

> **Sur le fond anthracite de sa propre charte, le rouge du club plafonne à 2,55:1.** Il échoue au 4,5:1 du
> texte **et** au 3:1 minimal d'un élément d'interface.

| Couleur | Sur `#1D1D1B` | Verdict |
|---|---|---|
| Rouge club `#B71918` | **2,55:1** | ❌ **Ni texte, ni bordure, ni signal** |
| *(le même, sur **blanc** — thème clair)* | *6,63:1* | ✅ *Texte AA — cf. §3.3.5* |
| Gris `#575756` *(le plus fréquent de la banderole)* | **2,33:1** | ❌ Inutilisable |
| Gris `#666666` | 2,94:1 | ❌ Inutilisable |
| Gris `#7C7C7B` | 4,04:1 | ⚠️ Éléments d'interface **seulement** (pas de texte normal) |
| Gris `#D1D1D1` | 11,06:1 | ✅ Texte AA |
| Blanc `#FFFFFF` | 16,88:1 | ✅ |
| **Blanc sur aplat rouge `#B71918`** | **6,63:1** | ✅ **C'est l'usage juste** |

**Trois conclusions fermes :**

1. **`DV-04` — Le rouge club est une *surface*, pas un *accent*.** On ne l'utilise pas *pour* écrire : on
   écrit **en blanc dessus**. C'est exactement ce que fait la charte de communication (logo sur fond rouge,
   banderole) — **le contraste ne fait que confirmer l'intention du graphiste.**
2. **La charte de communication n'est pas une charte applicative.** Trois de ses couleurs ne peuvent pas
   porter de texte sur son propre fond. **Ce n'est pas un défaut de la charte** : une banderole n'a pas de
   texte de 14 px, une console de supervision si. → **`Q-D1` est fermée** (§3.5).
3. **`DV-03` — Le signal se joue sur la *luminance*, pas sur la *teinte*.** Le rouge de marque est **sombre**
   (2,55:1) ; tout ce qui alerte est **lumineux** (≥ 8:1). Les deux ne jouent pas dans le même registre :
   **ils ne peuvent pas être confondus**, et cette distinction **survit au daltonisme** (en protanopie le
   rouge s'assombrit encore, l'ambre reste clair).

#### 3.3.3 Palette applicative dérivée — **thème sombre (référence)**

| Rôle | Token | Valeur | Sur fond | Usage |
|---|---|---|---|---|
| **Fond** | `--surface-0` | **`#1D1D1B`** *(charte)* | — | Le fond de la banderole **est** le fond de l'appli |
| **Surface** | `--surface-1` | `#262624` | 1,11:1 | Cartes, panneaux |
| **Surface élevée** | `--surface-2` | `#2F2F2C` | 1,26:1 | Modales, menus |
| **Bordure discrète** | `--border-subtle` | `#3D3D3A` | 1,55:1 | Séparateurs **décoratifs** |
| **Bordure fonctionnelle** | `--border` | `#7C7C7B` *(charte)* | 4,04:1 | Champs, contours **actionnables** (≥ 3:1 exigé) |
| **Texte faible** | `--text-muted` | `#8A8A87` | 4,88:1 | Métadonnées |
| **Texte secondaire** | `--text-secondary` | `#A8A8A5` | 7,08:1 | Labels |
| **Texte** | `--text` | `#FFFFFF` *(charte)* | 16,88:1 | Corps |
| **Marque — aplat** | `--brand-surface` | **`#B71918`** *(charte)* | *(blanc dessus : 6,63:1)* | Bandeaux, logo, en-têtes |
| **Marque — bordure** | `--brand-border` | **`#CC1C1B`** *(dérivée)* | 3,01:1 | Contours, soulignés actifs |
| **Marque — texte** | `--brand-text` | **`#E84E4D`** *(dérivée)* | 4,52:1 | Liens, texte de marque |

> **`--brand-border` et `--brand-text` sont *dérivées* du rouge charte** (teinte et saturation conservées,
> clarté remontée jusqu'au seuil AA). **Le club reconnaît son rouge ; l'archer lit l'écran.**

#### 3.3.4 Palette sémantique — **jamais personnalisable** — `DV-03`

> **C'est le verrou de la cohérence graphique** (§3.6) : un tournoi peut changer sa marque, **il ne peut pas
> changer ce qu'« alerte » veut dire.**

| Rôle | Token | Thème sombre | Sur `#1D1D1B` | Thème clair | Sur `#FFFFFF` |
|---|---|---|---|---|---|
| **Alerte / critique** | `--danger` | **`#FFB000`** | **9,22:1** | **`#9F6D00`** | **4,50:1** |
| **Alerte renforcée** | `--danger-strong` | `#FFD400` | 11,79:1 | `⟦à dériver⟧` | — |
| **Succès / feu vert** | `--success` | `#22D3AA` | 8,82:1 | `⟦à dériver⟧` | — |
| **Info / live** | `--info` | `#38BDF8` | 7,88:1 | `⟦à dériver⟧` | — |
| ~~Orange `#FF6B35`~~ | — | **écarté** | 5,95:1 | — | **se noie dans le rouge club (2,34:1)** |

**Deux pièges que le calcul a révélés, et qui sont des exigences :**

- ⚠️ **L'ambre s'effondre à 1,83:1 sur blanc.** Le thème clair **exige** sa variante foncée `#9F6D00` — un
  token sémantique **n'est pas une couleur, c'est une paire** (une valeur par thème). Sans ça, l'alerte est
  invisible dès qu'un poste bascule en clair (`D-26`, CDC UX).
- ⚠️ **L'orange est interdit** : à 2,34:1 du rouge club, il s'y noie. **Une couleur d'alerte doit se détacher
  du fond *et* de la marque.**

**Forme de l'alerte critique — `DV-03`.** Un poste hors ligne **n'est pas une pastille** : c'est un **aplat
ambre plein, texte anthracite**. Sur fond sombre, un aplat lumineux est le signal le plus fort disponible, et
il est **structurellement impossible à confondre** avec un accent de marque (rouge, sombre, en surface fine).
Rappel `P-4` (CDC UX) : **l'alerte chiffre son impact** — la couleur ne fait que la rendre visible.

> **Ne jamais coder par la seule couleur** (§6) : tout état porte **couleur + icône + texte**.

#### 3.3.5 Le thème clair ne pose pas le même problème — et c'est contre-intuitif

> **Le rouge club est *inutilisable* en thème sombre (2,55:1) et *pleinement utilisable* en thème clair
> (6,63:1).** La même couleur, deux régimes opposés.

| Rouge `#B71918` sur… | Ratio | Verdict |
|---|---|---|
| Anthracite `#1D1D1B` *(thème sombre)* | **2,55:1** | ❌ Aplat uniquement |
| **Blanc `#FFFFFF`** *(thème clair)* | **6,63:1** | ✅ **Texte AA, petit corps inclus** |

**Donc en thème clair, `--brand-text` n'a pas besoin d'être dérivé : c'est le rouge charte, tel quel.** La
dérivation (§3.5) ne se déclenche **que là où le contraste l'exige** — elle n'est pas une transformation
systématique, mais **une réponse à une mesure**.

> ⚠️ **Point de vigilance tracé.** La note de conception `analyse-charte.md` (14/07/2026) annonce **4,3:1**
> pour ce couple et en conclut que le rouge « échoue pour le petit texte ». **Le calcul WCAG 2.1 donne
> 6,63:1** — le rouge **passe**. Détail : `L(#B71918) = 0,1083` → `(1,00 + 0,05) / (0,1083 + 0,05) = 6,63`.
> Un ratio de 4,3:1 supposerait une luminance de 0,194, soit un rouge **nettement plus clair**. **La valeur
> retenue par ce CDC est 6,63:1**, et elle est reproductible (en-tête). *La conclusion de fond de la note —
> « le rouge est une couleur d'accent/surface » — reste juste : elle l'est en **thème sombre**, où le vrai
> chiffre (2,55:1) est **plus sévère** que celui qu'elle annonçait.*

### 3.4 Typographie — `DV-07`

> **Arbitrage client (14/07/2026) : l'UI est sobre.** Le registre grunge/stencil **reste sur l'affiche** et,
> au plus, sur le **titrage de l'écran de salle**. Motifs : illisible en petit corps, hostile à
> l'accessibilité, et **la charte ne fournit pas de typo exploitable** — `Stencil` est un titrage décoratif,
> `Arial` et `Calibri` sont des **polices système**, pas un choix de charte.

- **Contrainte absolue** : polices **embarquées et versionnées** (réseau local sans internet — **aucun Google
  Fonts, aucun CDN**, cf. §2.2).
- **Couple retenu** (recommandation inscrite, à confirmer) :
  - **Interface & corps** : **Inter** — dessinée pour les écrans, excellente en petit corps, chiffres
    tabulaires (indispensable pour les **colonnes de scores**), licence SIL OFL **redistribuable**.
  - **Écran de salle** : une **condensée à fort caractère** — plus de rang/nom/club/score par ligne à
    distance. `⟦à choisir — ex. Inter Tight, Archivo Narrow⟧`
- **Le « dynamique » se tient par le rythme, la couleur et le live — pas par la texture** (`P-3`).
- **Échelle typographique** : par contexte, dont une **échelle « écran de salle »** nettement plus grande que
  l'échelle applicative (§7.6).

### 3.5 Divergence charte communication ↔ charte applicative — `DV-05` *(ferme `Q-D1`)*

> **Question ouverte depuis la v0.1, tranchée le 14/07/2026** — et le matériau fourni l'a rendue concrète :
> **le rouge du club ne passe pas sur le fond du club.**

**Règle retenue — « accepter, puis dériver » :**

1. **La couleur fournie est acceptée telle quelle** et sert aux **aplats de marque** (bandeaux, logo,
   en-têtes) où le blanc posé dessus passe AA.
2. Pour **le texte et les bordures**, le système **dérive automatiquement** une variante de même teinte,
   éclaircie (thème sombre) ou assombrie (thème clair), jusqu'au seuil AA — cf. `#CC1C1B` / `#E84E4D`.
3. **Les couleurs sémantiques ne sont jamais touchées** (§3.3.4).

**Pourquoi pas « refuser »** : on refuserait le rouge du club à son propre club. **Pourquoi pas « avertir et
laisser passer »** : l'accessibilité est **contractuelle** (§6), elle ne se négocie pas au cas par cas — et
`P-3` (« l'appli n'empêche pas ») **régit les actions de l'organisateur le jour J, pas la conformité d'un
livrable**.

### 3.6 Identité par tournoi — `DV-06` *(ferme `Q-D8`)*

> **Arbitrage client (14/07/2026) :** chaque tournoi peut porter son identité, **avec un thème par défaut
> personnalisable, respectant une cohérence graphique.**

**Ce que l'organisateur fournit — et rien d'autre :**

| Fourni | Nature | Défaut si absent |
|---|---|---|
| **Un logo** | SVG ou PNG | Le logo du club |
| **2 couleurs d'accent** | `accent-1` (marque dominante) · `accent-2` (secondaire) | Rouge club `#B71918` + anthracite |

**Le système dérive tout le reste** : surfaces, bordures, variantes de texte accessibles (§3.5), états de
survol/focus/pressé, thème clair **et** sombre. **L'organisateur ne choisit pas une palette : il donne deux
couleurs et un logo.**

**Les trois verrous de la cohérence graphique :**

1. **Les couleurs sémantiques ne sont pas personnalisables** (§3.3.4). Alerte, succès, info et live
   appartiennent **au produit**, pas au tournoi. *Un tournoi ne redéfinit pas ce que « hors ligne » veut dire.*
2. **Les neutres, l'échelle typographique, les espacements et les composants ne bougent pas.** Seul le
   **chrome de marque** change.
3. **Toute couleur fournie passe le calcul de contraste à la saisie** (§3.5) : acceptée en aplat, dérivée pour
   le texte. **La conformité AA n'est pas à la main de l'organisateur.**

**Portée — `D-27` (CDC UX) :** l'identité du tournoi habille **l'appli publique et l'écran de salle**.
**L'admin et la saisie restent l'outil** : neutres et stables d'un tournoi à l'autre. *Le jour J, un bénévole
n'a pas le temps de réapprendre des repères visuels.*

**Quand se prépare-t-elle ?** À la **configuration du tournoi** — `P-6` (CDC UX) : *tout ce qui s'identifie se
prépare à l'avance*. Cf. **E01US016**.

### 3.7 Iconographie & imagerie
- **Jeu d'icônes** unique, embarqué, cohérent (trait, épaisseur, grille). `⟦set à choisir — ex. Lucide (ISC,
  redistribuable, trait cohérent)⟧`
- **Pictogrammes métier** spécifiques à dessiner : **blason/cible**, **flèche/volée**, **position A/B/C/D**,
  **club**, **départ**, statuts de match. (cf. §5.4)
  > La charte **fournit déjà deux amorces** : l'**archer stylisé** du logo club et la **cible concentrique**
  > du logo événement. À réutiliser plutôt qu'à réinventer.
- **Signature graphique disponible, non retenue à ce jour** : le **« E » en trois barres**, le **motif nid
  d'abeille**, les **trajectoires courbes**. Écartés de l'UI (sobriété, `DV-07`) ; **candidats pour l'écran de
  salle et les gabarits d'impression**, où la lisibilité n'est pas menacée. `⟦à arbitrer au maquettage⟧`
- **Imagerie / photos** : l'**affiche du tournoi** est un asset exploitable (accueil public, écran de salle).
  ⚠️ **Une image en fond met la lisibilité en danger** → si elle est utilisée, **voile de contraste imposé** et
  revalidation AA du texte posé dessus. Droits et traitement : `⟦À COMPLÉTER⟧`

---

## 4. Système de design *(sur-mesure — cf. Q-D2)*

### 4.1 Approche
Décision entretien : **système de design sur-mesure**. Recommandation inscrite (à confirmer `Q-D2`) : **couche visuelle 100 % sur-mesure** (aucune identité de librairie visible) **posée sur des primitives d'accessibilité éprouvées** (comportement clavier / ARIA / focus / gestion du focus-trap). On garde une identité entièrement propre sans réécrire les fondations d'accessibilité — cohérent avec l'exigence WCAG AA (§6) et la stack **React + TypeScript** du CDC technique.

### 4.2 Design tokens (source de vérité)
Le système repose sur des **tokens** (variables de design) versionnés, faisant le lien charte ↔ code :
- **Couleur** (rôles sémantiques, pas de couleur « en dur »), **typographie** (familles, tailles, graisses, interlignes), **espacement** (échelle 4/8 px), **rayons**, **ombres/élévation**, **durées d'animation**, **points de rupture responsive**.
- **Thématisation par tokens** : le passage sombre ↔ clair ↔ salle ne change que les valeurs de tokens, pas les composants (§7).

**Trois strates, et elles n'ont pas le même régime — `DV-06`.** C'est ce qui rend la personnalisation par
tournoi (§3.6) possible **sans perdre la cohérence graphique** :

| Strate | Exemples | Personnalisable par tournoi ? | Qui la fixe |
|---|---|---|---|
| **Marque** | `--brand-surface`, `--brand-border`, `--brand-text`, logo | ✅ **Oui** — 2 accents + 1 logo, le reste **dérivé** (§3.5) | L'organisateur |
| **Sémantique** | `--danger`, `--success`, `--info`, `--live` | ❌ **Jamais** | Le produit (§3.3.4) |
| **Structure** | Neutres, échelle typo, espacements, rayons, composants | ❌ **Jamais** | Le design system |

> **La règle en une phrase : un tournoi peut changer *de quoi ça a l'air*, jamais *ce que ça veut dire*.**

⚠️ **Corollaire technique :** les variantes accessibles étant **dérivées par calcul** (§3.5), la dérivation
est **du code, pas une décision de designer** — elle tourne au moment où l'organisateur saisit sa couleur, et
son résultat est **vérifiable** (le calcul de contraste est reproductible, cf. en-tête).

### 4.3 Grille & responsive
- Grille et **points de rupture** couvrant : mobile (≥ 360 px), tablette (≥ 768 px), desktop admin (≥ 1280 px), écran projeté (≥ 1920 px).
- Règles de densité par contexte : **compacte** (admin), **confort tactile** (tablette), **lisible mobile**, **grand format** (projeté).

### 4.4 Bibliothèque de composants (inventaire à concevoir)
**Composants génériques :** boutons (primaire/secondaire/danger/fantôme), champs & formulaires, sélecteurs, listes & tableaux de données, onglets, modales & panneaux latéraux, notifications/toasts, badges & pastilles de statut, fil d'Ariane, pagination, états vides, squelettes de chargement.

**Composants métier (spécifiques — cf. §5.4) :** carte de cible, plan de salle, arbre de tableau (bracket), pavé de saisie de volée, ligne de score, carte d'archer, carte de match/duel, chronologie de phases, tuile de classement.

**Pour chaque composant, le CDC exige la définition des états :** repos, survol, focus clavier, actif/pressé, désactivé, chargement, erreur, **live/mise à jour**, hors-ligne. (cf. §6 et §7.2)

---

## 5. Périmètre des besoins graphiques par module fonctionnel

> Cœur du document : mise en correspondance **modules fonctionnels (M1→M9) ↔ écrans & composants graphiques** à produire. C'est l'inventaire qui « cible le périmètre des besoins graphiques et fonctionnels ».

### 5.1 Tableau de correspondance module → écrans → contexte

| Module (CDC fonctionnel) | Écrans / vues à concevoir | Composants clés | Contexte(s) |
|---|---|---|---|
| **M1 Configuration** | Assistant de création de tournoi ; éditeurs catégories / blasons / barèmes / gabarits de salle ; tarifs | Formulaires complexes, éditeur de gabarit visuel, presets | C1 |
| **M2 Inscriptions** | Liste des inscrits (tri/filtre/recherche) ; fiche archer ; import XLS (mapping colonnes, aperçu, résolution d'erreurs) ; référentiel clubs | Table de données dense, formulaire, assistant d'import, dédoublonnage | C1 |
| **M3 Moteur de phases** *(cœur)* | **Éditeur de séquence de phases** (composer/ordonner) ; configuration d'une phase (type, source, barème, sortie) ; contrôles de cohérence & alertes ; enregistrement de modèle | **Chronologie/pipeline de phases**, cartes de phase, panneau de config, bandeaux d'alerte | C1 |
| **M4 Placement & plan de cibles** | Plan de salle interactif ; **glisser-déposer** des archers ; visualisation des contraintes (capacité, blason, mixité club) ; déroulé horaire | **Plan de cibles**, carte de cible (positions A/B/C/D), badges de contrainte, timeline | C1 (édition) · C3/C4 (lecture) |
| **M5 Saisie des scores** | **Écran de saisie tablette** (par cible/archer) ; pavé de volée adapté au barème (cumul / sets / shoot-off / BSO) ; validation & verrouillage ; correction tracée | **Pavé de saisie de volée**, ligne de score, indicateur de synchro, verrou/traçabilité | **C2** |
| **M6 Tableaux & progression** | Arbre de tableau (bracket) ; construction de tableau (seeding, byes) ; repêchage Lucky Loser ; tableaux de placement ; BSO ; édition manuelle | **Bracket**, carte de match, éditeur de seeding | C1 (édition) · C3/C4 (lecture) |
| **M7 Classement & affichage public** | Classement intégral 1→N ; classements par catégorie/phase ; **écran projeté** ; vue mobile publique ; plans & déroulé publics | Tuiles de classement, table classée, **vues projetées auto-défilantes** | **C3 + C4** |
| **M8 Paiement (suivi)** | Vue par archer / par club ; statut payé/non payé ; totaux | Table, badges de statut, totaux | C1 |
| **M9 Exports & documents** | Aperçus & mise en page **imprimable/PDF** : déroulé, plans, feuilles de marque, tableaux, classements, listes paiement | Gabarits print (A4), aperçu avant export | C1 (déclenchement) · sortie papier |

### 5.2 Écrans prioritaires (les « pièces maîtresses » du design)

> ⚠️ **Réordonné le 14/07/2026.** L'entretien de conception a établi que **le produit ne vend pas du
> confort : il fait disparaître un temps mort** (CDC UX §1). Or **la bascule de tour — l'écran qui porte
> toute la valeur — était absente de cette liste**, et deux écrans de pilotage manquaient. Les écrans
> ci-dessous ne font que **rendre la bascule possible**. Hiérarchie de référence : **CDC UX §1.2**.

Par criticité le jour J, à maquetter en premier :

1. **Bascule de tour** (CDC UX §8) — **c'est le produit**. L'admin lance, tout est prêt avant l'appui, le bouton chiffre son impact.
2. **Console de supervision** (CDC UX §7.1) — 30 postes, distinguer « ils tirent lentement » de « leur tablette est morte ».
3. **Saisie de score sur la tablette de cible (M5)** — le poste le plus utilisé et le plus sensible aux erreurs.
4. **Plan de cibles / placement (M4)** — l'écran signature de l'admin (drag-drop + contraintes). ⚠️ **Non instruit à ce jour : `Q-UX8`** (entretien dédié à prévoir).
5. **Consultation mobile « ma journée » (C3)** — le plus grand nombre d'utilisateurs ; ce n'est pas un tableau de résultats, **c'est un GPS** (CDC UX §7.4).
6. **Écran de salle (C4/M7)** — la vitrine, **et un canal de routage à part entière** (`D-21`).
7. **Éditeur de séquence de phases (M3)** — la complexité fonctionnelle la plus élevée à rendre lisible.

### 5.3 Parcours à scénariser (maquettes de flux, pas seulement d'écrans)
- **Enchaîner un tour** (admin) — **le parcours qui porte la valeur** (`D-22`→`D-24`) : dernier duel validé → feu vert → lancement (global ou par événement) → 4 canaux prévenus. **Objectif contractuel : < 2 min** (`D-25`).
- **Préparer un tournoi** (admin) : création → gabarit → séquence de phases → **scoreurs** → inscriptions → placement → impression (**dont les QR de cible**, `D-07`).
- **Saisir une volée** (**marqueur**, sur la tablette de sa cible) : la cible est déjà connue (jeton de poste) → saisie flèche par flèche des 3–4 archers → validation par le scoreur → **la tablette affiche les prochaines cibles** (`D-09`).
- **Valider** (scoreur, itinérant) : file triée par ancienneté → choix d'une cible → contrôle → validation tracée (`D-12`).
- **Trouver sa cible** (archer/public) : ouverture → **« c'est moi » déjà mémorisé** → « vous tirez cible 12, position B, départ 2 » — la recherche par nom n'est que la première fois (`D-09`).
- **Suivre le live** (public/écran de salle) : déroulé automatique classement ↔ **affectations** ↔ tableaux ↔ plans, **pilotable par l'admin** (`D-21`).

> ⚠️ **`Q-D3` est fermée et remplacée** (14/07/2026, `D-25`). L'objectif « volée saisie et validée en < 10 s »
> **visait à côté** : si le marqueur met 12 s au lieu de 10, personne ne le remarque — il attend les autres
> archers de sa cible. Si la bascule entre deux tours prend 20 min, **150 personnes attendent**. La métrique
> contractuelle est désormais : **« dernier duel validé » → « les archers savent où aller » en < 2 min**. La
> vitesse de saisie reste une exigence de confort, pas un objectif contractuel.

### 5.4 Composants métier spécifiques à dessiner (récapitulatif)
| Composant | Rôle | Points de vigilance design |
|---|---|---|
| **Carte de cible** | Représente une cible et ses positions A/B/C/D + blasons | Lisibilité des fractions de place, occupation partielle, code couleur club |
| **Plan de salle** | Grille des ~30 cibles | Zoom/scroll, drag-drop, densité, impression |
| **Pavé de saisie de volée** | Saisir 10/9/…/M par flèche | Grosses touches, ordre décroissant, annulation facile, adaptation au barème |
| **Ligne / carte de score** | État d'un archer/match | Cumul, points de set, vainqueur, état live |
| **Arbre de tableau (bracket)** | Duels et progression | Grand nombre de matchs (jusqu'à M484), navigation, byes, Lucky Loser |
| **Chronologie de phases** | Séquence M3 | Représenter sources/sorties entre phases, alertes de cohérence |
| **Tuile de classement projeté** | Affichage distance | Très gros corps, rang/nom/club/score, défilement |
| **Bandeau de connexion** | État réseau PWA | En ligne / hors-ligne / synchro / échec |

---

## 6. Accessibilité — exigence WCAG AA (contractuelle)

Niveau retenu (décision entretien) : **WCAG 2.1 niveau AA**. Exigences minimales à inscrire :

- **Contrastes** : texte normal ≥ 4,5:1, texte large ≥ 3:1, éléments d'interface/graphiques ≥ 3:1. **Toute couleur de charte est passée au calcul avant d'être inscrite** (§3.3) — c'est ce qui a montré que **le rouge club échoue sur le fond club** (2,55:1). Règle en cas d'échec : **`DV-05` — accepter en aplat, dériver la variante AA** (`Q-D1` fermée).
- ⚠️ **Le contraste se vérifie dans les deux thèmes.** Une valeur conforme en sombre peut échouer en clair : l'ambre d'alerte passe de **9,22:1** à **1,83:1** (§3.3.4). **Chaque token sémantique est une paire, pas une couleur.**
- **Cibles tactiles** : ≥ 44 px (AA) — porté à **≥ 48 px sur la saisie tablette** (C2).
- **Focus clavier visible** et **ordre de tabulation logique** (indispensable côté admin C1).
- **Ne pas coder l'information par la seule couleur** (statuts payé/live/erreur = couleur **+** icône/texte).
- **Cibles de navigation clavier complète** pour les écrans de pilotage (M1–M6).
- **Textes redimensionnables** jusqu'à 200 % sans perte de fonction.
- **Rôles/États ARIA** corrects sur composants sur-mesure (d'où la recommandation §4.1 de s'appuyer sur des primitives a11y).
- **Mouvement** : respect de `prefers-reduced-motion` (le registre « dynamique » ne doit pas gêner).

> Une **checklist d'accessibilité par composant** sera annexée à la livraison du design system.

---

## 7. Thématisation & ergonomie par contexte

### 7.1 Thèmes (sombre par défaut / clair / salle) — `DV-02`

> ⚠️ **Amendé le 14/07/2026.** La v0.2 laissait le défaut « s'adapter au contexte ». **Arbitrage client :
> thème sombre par défaut, bascule vers le clair si besoin.**

**Le thème sombre n'est pas une option de confort : c'est la charte.** Le fond de la banderole du club **est**
`#1D1D1B` (§3.3). L'appli sombre **ressemble au club** ; l'appli claire est la déclinaison.

| Thème | Statut | Fond | Défaut sur |
|---|---|---|---|
| **Sombre** | **Référence** *(charte)* | `#1D1D1B` | **Les 3 applis** |
| **Clair** | Déclinaison complète (pas dégradée) | `#FFFFFF` / neutres clairs | — *(sur demande)* |
| **Salle** | Dérivé du sombre : contraste renforcé, très grand corps | `#1D1D1B` | Écran de salle (§7.6) |

- **Bascule manuelle, disponible partout.** La préférence système est respectée **à la première ouverture
  seulement** ; **un choix explicite prime toujours** et n'est plus écrasé.
- **La bascule est mémorisée *par poste*, avec le jeton** (`D-26`, CDC UX §4) : *la lumière varie d'une cible
  à l'autre dans un gymnase.* La tablette près de la baie vitrée passe en clair ; les 29 autres ne bougent
  pas. Le choix **survit à la fermeture de l'onglet** (`D-05` : pas de kiosque, l'onglet se ferme).
- ⚠️ **Un thème n'est pas une inversion.** Chaque token sémantique **a une valeur par thème** : l'ambre
  d'alerte `#FFB000` (9,22:1 sur sombre) **tombe à 1,83:1 sur blanc** et doit devenir `#9F6D00` (§3.3.4).
  **Une bascule de thème qui rend l'alerte invisible est un bug de sécurité, pas un détail esthétique.**

### 7.2 États système transverses (à concevoir une fois, réutilisés partout)
Chargement (squelettes), **vide** (message + action), **erreur** (récupérable), **hors-ligne / synchro** (bandeau de connexion), **live** (indicateur de fraîcheur des données), **verrou** (score validé), **conflit** (correction concurrente).

### 7.3 Ergonomie C1 — Pilotage admin (PC)
- Densité maîtrisée, navigation persistante, raccourcis clavier, **prévention d'erreur** (confirmations sur actions destructrices, validation en amont dans M3).
- Le drag-drop (M4) a des **alternatives clavier/menu** (accessibilité + robustesse).
- Feedback immédiat des contrôles de cohérence (M3 EF-3.8).

### 7.4 Ergonomie C2 — Saisie sur la tablette de cible (**marqueur**) — *poste critique*

> ⚠️ **Amendé le 14/07/2026.** Ce n'est **pas le scoreur** qui saisit : la tablette est **fixée à la cible**
> et c'est un **marqueur** (un archer de la cible, désigné selon FFTA B.6.1.1) qui tape pour les 3–4 archers.
> Le scoreur, lui, est **itinérant** et **valide** (CDC UX §7.3). Deux postes, pas un.

- **Peu de clics, gros boutons, une action à la fois.** Le pavé de volée occupe le pouce/l'index sans viser.
- **Feedback optimiste** : la saisie s'affiche instantanément, la synchro se fait en tâche de fond avec indicateur.
- **Prévention d'erreur** : ordre logique des flèches (**décroissant**, FFTA B.6.1.3), annulation/correction immédiate avant validation, confirmation de validation, **verrouillage** après coup avec correction tracée par rôle habilité.
- Fonctionne **debout, d'une main**, mains froides : zones de touche larges, pas de geste précis.
- **Le marqueur actif est affiché discrètement et tapable** (`D-04`) : il change rarement, donc **l'interface ne s'organise pas autour de ce changement** — pas de sélecteur permanent qui vole de l'espace au pavé.
- **La tablette indique le grain de validation actif** (`D-11`) : sans ça, le marqueur ne sait pas quand le scoreur viendra.
- **Après validation, la tablette devient un panneau de routage** : « MARTIN → cible 4, 14h20 » (`D-09`).
- **Pas de mode kiosque** (`D-05`) : l'appli vit dans un onglet, la fermeture accidentelle **arrivera** → le rattachement doit se refaire **en un geste** (scan du QR de la cible, `D-07`).
- ~~Objectif de performance de saisie à chiffrer (`Q-D3`).~~ → **`D-25`** : la métrique contractuelle est la **bascule de tour < 2 min** (§5.3). La vitesse de saisie reste une exigence de confort.

### 7.5 Ergonomie C3 — Consultation mobile (archer/public)
- Entrée directe sur l'essentiel : **recherche par nom → ma cible / mon classement**. Zéro configuration.
- Contenu scannable, gros repères, pas de menu profond.

### 7.6 Ergonomie C4 — Écran projeté
- **Échelle typographique dédiée**, hiérarchie très forte, peu d'items par vue.
- **Auto-défilement / rotation** entre classement, tableaux et plans, à cadence réglable.
- Pensé pour être vu à plusieurs mètres, sans interaction.

---

## 8. Microcopie & ton éditorial
- Registre **sportif & dynamique** mais **clair et concis** ; vocabulaire **métier en français** (Archer, Cible, Blason, Volée, Duel, Barrage — cohérent avec l'ubiquitous language du projet).
- Messages d'erreur **utiles et non culpabilisants** (surtout sur la saisie tablette et l'import XLS).
- Cohérence des libellés d'action à travers les 4 contextes.

---

## 9. Livrables design attendus
1. **Fondations / design tokens** (couleurs, typo, espacements, thèmes) — versionnés.
2. **Bibliothèque de composants** (génériques + métier) avec tous les états.
3. **Maquettes haute-fidélité** des 5 écrans prioritaires (§5.2), en thèmes clair/sombre/projeté selon le contexte.
4. **Prototype interactif** des parcours clés (§5.3), utilisable pour tests terrain.
5. **Guide d'accessibilité** (checklist AA par composant).
6. **Kit d'assets embarqués** (polices, icônes, logo en déclinaisons) prêt pour le réseau local sans internet.
7. **Gabarits d'impression/PDF** (M9).

---

## 10. Décisions à trancher & questions ouvertes (design)

> Les questions de **structure** ont migré vers `cahier-des-charges-ux.md` §12 (`Q-UXn`). Ne restent ici que
> les questions d'**identité visuelle**.

| # | Sujet | Statut | À décider |
|---|---|---|---|
| **Q-D1** | ~~Divergence charte communication ↔ charte applicative~~ | **Fermée le 14/07/2026** | **`DV-05` : « accepter, puis dériver »** (§3.5). La question a cessé d'être théorique : **le rouge du club ne passe pas sur le fond du club** (2,55:1). La couleur exacte vit en **aplat** ; les variantes texte/bordure sont **dérivées** (`#E84E4D`, `#CC1C1B`). |
| **Q-D2** | Périmètre du « sur-mesure » | **Ouverte** | **Couche visuelle sur-mesure sur primitives a11y** (recommandé) **ou** tout recodé y compris comportements (poste de coût/risque) ? |
| **Q-D3** | ~~Objectif de performance de saisie tablette~~ | **Fermée le 14/07/2026** | **Remplacée par `D-25`** (CDC UX §1.1) : la métrique contractuelle est la **bascule de tour < 2 min**, pas la vitesse de saisie. Motif en §5.3. |
| **Q-D4** | ~~Éléments de charte concrets~~ | **Fermée le 14/07/2026 — était bloquante** | **Éléments fournis** (`docs/elements_design/`) et **versés en §3** : marque (**deux** — club et événement), logo, palette mesurée, typo arbitrée (`DV-01`→`DV-08`). **Le maquettage haute fidélité est débloqué.** Reliquats **non bloquants** : `Q-D10` (zone de protection du logo), `Q-D11` (condensée écran de salle). |
| **Q-D5** | ~~Mode de saisie tablette par défaut : scoreur vs archer~~ | **Tranchée le 14/07/2026** | **Ni l'un ni l'autre** (`D-13`) : la tablette est **fixée à la cible** et **ouverte** — pas d'authentification, l'identité est **le lieu**. Le **marqueur** (un archer de la cible) saisit pour tous et est **tracé à la volée** (`D-04`) ; le **scoreur** valide (`D-03`). |
| **Q-D6** | Support cible minimal | **Ouverte** | ~~BYOD~~ → le parc est **fourni par le club, navigateur seul**, complété par des tablettes personnelles (`D-05`). Reste à lister : **navigateurs/OS garantis** du parc club, et le plancher réel de l'appoint perso. Cf. aussi `Q-UX1` (raccourci PWA). |
| **Q-D7** | Multilingue | **Ouverte** | Interface FR seule, ou prévoir l'internationalisation ? |
| **Q-D8** | ~~Personnalisation par tournoi~~ | **Fermée le 14/07/2026** | **`DV-06` : logo + 2 accents, le système dérive le reste** (§3.6). Portée : **public + écran de salle** (`D-27`). **Les sémantiques ne sont jamais personnalisables** — c'est le verrou de la cohérence. Le matériau fourni a **prouvé** le besoin : le Challenge des Champions a sa propre identité. |
| **Q-D9** | **Nom affiché de la solution** | **Ouverte** | *Kervignarc* est le nom de l'**outil**. L'archer qui ouvre l'appli publique doit-il voir le nom du **tournoi** (« Challenge des Champions »), du **club**, ou de l'**outil** ? Recommandation : **le tournoi** — l'archer vient pour la compétition, pas pour le logiciel. |
| **Q-D10** | **Zone de protection & interdits du logo** | **Ouverte** — non bloquante | À demander au club : marge minimale, taille minimale, usages interdits. Sans ça, le logo sera intégré « au jugé » (§3.2). |
| **Q-D11** | **Police condensée de l'écran de salle** | **Ouverte** — non bloquante | Inter est retenue pour l'UI (`DV-07`). Reste à choisir la condensée du grand format : `Inter Tight`, `Archivo Narrow`… **Contrainte : licence redistribuable + embarquable** (§2.2). |
| **Q-D12** | **Signature graphique sur l'écran de salle** | **Ouverte** — au maquettage | Le **« E » en trois barres**, le **nid d'abeille**, les **trajectoires** : écartés de l'UI (`DV-07`), mais **candidats** sur l'écran de salle et les gabarits d'impression, où la lisibilité n'est pas menacée (§3.7). |

---

## 11. Registre des décisions visuelles

> **Version** = version de ce document où la décision apparaît. Les décisions de **structure** sont au
> registre `D-nn` du **CDC UX §11** ; celles-ci portent l'**identité**. Une décision n'est jamais réécrite
> silencieusement : elle est **remplacée**, l'ancienne passant à *Remplacée par DV-nn*.

| ID | Décision | Statut | Ver. | Remplace / impacte |
|---|---|---|---|---|
| **DV-01** | **Deux marques** : le **club** (permanent) et l'**événement** (par édition). `elements_design/CDC/` = *Challenge Des Champions*, **pas** « cahier des charges » | Actée | 0.3 | Rend `Q-D8` concrète |
| **DV-02** | **Thème sombre = référence** (le fond `#1D1D1B` **est** la charte) ; clair en déclinaison complète ; **bascule mémorisée par poste** | Actée | 0.3 | Amende §7.1 v0.2 · `D-26` (CDC UX) |
| **DV-03** | **Le signal se joue sur la luminance, pas la teinte** : alerte = **ambre `#FFB000`** (9,22:1), aplat plein ; **le rouge n'est jamais un signal** ; **orange écarté** (2,34:1 du rouge) ; sémantiques **non personnalisables** | Actée | 0.3 | Résout le faux conflit « rouge marque vs rouge alerte » |
| **DV-04** | **Le rouge club est une *surface*, pas un *accent*** : `#B71918` = **2,55:1** sur l'anthracite → échoue au texte **et** à l'UI ; on écrit **en blanc dessus** (6,63:1) | Actée | 0.3 | Confirme l'usage de la charte de communication |
| **DV-05** | **« Accepter, puis dériver »** : couleur exacte en aplat, **variantes AA dérivées** pour texte/bordure (`#E84E4D` / `#CC1C1B`) | Actée | 0.3 | **Ferme `Q-D1`** |
| **DV-06** | **Identité par tournoi = logo + 2 accents**, le système dérive tout le reste ; **3 strates de tokens** (marque personnalisable / sémantique et structure figées) | Actée | 0.3 | **Ferme `Q-D8`** · `D-27`, `D-28` (CDC UX) · E01US016 |
| **DV-07** | **UI sobre** : le grunge/stencil reste sur l'affiche ; **Inter** pour l'UI (OFL, chiffres tabulaires) + une condensée pour la salle | Actée | 0.3 | `Q-D11`, `Q-D12` · Écarte `Stencil`/`Arial`/`Calibri` |
| **DV-08** | **Co-branding hiérarchisé** : l'événement domine, le club signe en pied ; **sans identité de tournoi, le club reprend la place** | Actée | 0.3 | §3.2 |

---

## 12. Historique des versions

| Version | Date | Origine | Contenu |
|---|---|---|---|
| **0.3** | 14/07/2026 | **Éléments graphiques fournis** (`docs/elements_design/`) + arbitrages client du 14/07/2026 | **La charte cesse d'être un emplacement vide.** `Q-D4` (bloquante) **fermée** : marque, logo, palette et typo versés et **mesurés** (§3). Fait central : **le rouge club échoue au contraste sur le fond de sa propre charte** (2,55:1) → palette applicative **dérivée** (§3.3.3) et règle **« accepter, puis dériver »** (`DV-05`, **ferme `Q-D1`**). **Le faux conflit « rouge marque vs rouge alerte » est dissous** : le signal se joue sur la **luminance** (`DV-03`, ambre `#FFB000`). **Identité par tournoi** tranchée (`DV-06`, **ferme `Q-D8`**) : logo + 2 accents, 3 strates de tokens. **Thème sombre = référence**, bascule **par poste** (`DV-02`). **UI sobre**, Inter (`DV-07`). Ajout du **registre `DV-nn`** (§11) et de 4 questions (`Q-D9`→`Q-D12`, non bloquantes). |
| **0.2** | 14/07/2026 | Entretien de conception du 14/07/2026 | **Amendement sur 5 contradictions** : §2.1 contextes C1–C4 → 3 applis + postes (`D-01`) ; §2.2 BYOD → parc club navigateur seul + planchers par appli (`D-05`, `D-02`) ; §5.2 écrans prioritaires réordonnés (la **bascule de tour** manquait) ; §5.3 `Q-D3` **fermée** → `D-25` ; §10 `Q-D5` **tranchée**, `Q-D6` reformulée. **Périmètre resserré sur l'identité visuelle** : l'architecture d'expérience passe à `cahier-des-charges-ux.md` v0.1. |
| **0.1** | 08/07/2026 | Entretien design du 08/07/2026 | Création. Cadrage du périmètre graphique & ergonomique : principes, 4 contextes d'usage, identité visuelle (emplacements réservés), système de design sur-mesure & tokens, inventaire des besoins graphiques par module (M1→M9), WCAG AA, thématisation, microcopie, livrables, 8 questions ouvertes. |

---

*Document produit à partir du CDC fonctionnel v0.3, du CDC technique v0.2, de l'entretien design du 08/07/2026, de l'entretien de conception du 14/07/2026 et des **éléments graphiques fournis le 14/07/2026** (`docs/elements_design/`). **Traite l'identité visuelle** ; l'architecture d'expérience est dans `cahier-des-charges-ux.md`. **La charte est instruite** (`Q-D4` fermée) : le maquettage haute fidélité est débloqué. Document vivant — toute décision nouvelle s'inscrit au registre `DV-nn` §11, et **toute couleur ajoutée passe le calcul de contraste** avant d'être inscrite.*
