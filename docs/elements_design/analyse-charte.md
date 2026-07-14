# Analyse de la charte graphique — `docs/elements_design/`

> Note de synthèse produite à partir des 4 sources du dossier, destinée à alimenter
> `cahier-des-charges-design.md`. Les PDF ne sont pas rendables nativement (poppler absent) :
> rendu obtenu via `python -m pip install pymupdf` puis `fitz` (matrix 2x / 0.28x).

> ✅ **Note versée le 14/07/2026 dans [`cahier-des-charges-design.md`](../../cahier-des-charges-design.md)
> v0.3 (§3), qui fait désormais foi.** Ce fichier est conservé comme **trace de l'analyse d'origine**.
> Apports repris tels quels : les **deux niveaux d'identité** (§1 → `DV-01`), la référence **CMJN
> C19/M100/J100/N11** (§2 → §3.3.1 du CDC — *contrôle de conversion : `#B80000`, à un point du hex, la
> traduction écran est juste*), le **rouge = accent/surface** (§2 → `DV-04`), la **banderole comme direction
> du thème sombre** (§4 → `DV-02`), les **typos non récupérables** (§3 → `DV-07`).
>
> ⚠️ **Deux rectifications**, à lire avant de réutiliser cette note :
>
> 1. **§2 — le ratio rouge sur blanc est `6,63:1`, pas `4,3:1`.** Le rouge `#B71918` **passe AA en texte
>    normal sur blanc**, petit corps inclus ; la mention « échoue pour le petit texte » est donc inexacte.
>    Calcul : `L(#B71918) = 0,1083` → `(1,00 + 0,05) / (0,1083 + 0,05) = 6,63`.
>    **La contrainte réelle est ailleurs, et elle est plus dure** : sur l'**anthracite `#1D1D1B`** — le fond
>    de la banderole, donc du thème sombre que cette note recommande à juste titre — le rouge tombe à
>    **`2,55:1`** et échoue **même au 3:1 d'un élément d'interface**. *La conclusion « rouge = accent/surface »
>    reste donc valide : c'est sa justification qui change de thème.*
> 2. **§4 — c'est le « E » de KERVIGNAC qui est remplacé par trois barres, pas le « K ».** Cf. le rendu de
>    `banderolle pdf.svg` : `K` + trois barres + `RVIGNAC`.
>
> **Divergence de cadrage** (§1, tranchée par le client le 14/07/2026) : la note propose que « l'application
> porte l'identité club, un tournoi recevant un habillage en surcouche ». L'arbitrage retenu est plus précis —
> **`D-27`** : l'identité du tournoi habille **l'appli publique et l'écran de salle** ; **l'admin et la saisie
> restent l'outil**, neutres d'un tournoi à l'autre.

## 1. Deux niveaux d'identité (à distinguer dans le CDC)

| Niveau | Fichiers | Registre |
|---|---|---|
| **Identité club** (permanente, chartée) | `club/logo.pdf`, `club/banderolle pdf.*` | Sobre, sportif, pictogramme archer |
| **Identité évènement** (Challenge des Champions) | `CDC/Logo sur fond rouge.*`, `CDC/Affiche…2026.*` | Grunge / stencil, urbain, compétitif (« Duels Contest ») |

**Implication CDC** : l'application porte l'**identité club** (durable, chartée) ; un tournoi donné
peut recevoir un **habillage évènementiel** plus expressif en surcouche (bannière, page publique).
L'affiche « Challenge des Champions » est un **évènement daté** (14 déc. 2025), pas la marque de l'app.

## 2. Tokens couleur (extraits des fichiers)

| Rôle | Valeur écran | Référence source |
|---|---|---|
| **Rouge de marque** (primaire) | `#B71918` | nuancier officiel imprimeur **CMJN 19/100/100/11** (encarté dans `logo.pdf`) |
| **Anthracite / quasi-noir** | `#1D1D1B` | textes, contours, fond sombre banderolle |
| **Blanc** | `#FFFFFF` / `#F9F9F9` | aplats, texte sur rouge |
| **Gris secondaires** | `#575756`, `#666666`, `#7C7C7B`, `#D1D1D1` | textures, éléments neutres |

Le rouge est **spécifié en CMJN dans le logo lui-même** (C:19 M:100 J:100 N:11) → c'est **la**
référence à respecter ; `#B71918` en est la traduction écran.

### ⚠️ Contrainte WCAG à inscrire
Rouge `#B71918` sur blanc ≈ **ratio 4.3:1** → passe AA pour **gros texte uniquement**, **échoue
pour le petit texte**. Le rouge doit donc être une couleur d'**accent / surface**, avec texte
**anthracite ou blanc** ; **jamais rouge-sur-blanc en corps de texte**.

## 3. Typographies repérées (dans les SVG)

- **Arial** (bold + regular) — texte courant / titres
- **Stencil** — accents évènementiels (dates, mentions)
- **Calibri** — mentions légales / URL
- Les lettrages **« KERVIGNAC »** et **« CHALLENGE DES CHAMPIONS »** sont **vectorisés** (police
  grunge custom, non récupérable comme fonte) → **à traiter comme image**, pas à reproduire en CSS.

> Rappel contrainte réseau local : polices à **embarquer** (pas de CDN).

## 4. Vocabulaire visuel réutilisable

- **Pictogramme archer** blanc sur cartouche rouge (`logo.pdf`) → candidat idéal **logo app / favicon / avatar**.
- **« K » barré** (barres horizontales façon encoche de flèche / cible) → détail signature du club.
- **Cible concentrique + flèche + couronne + étoiles** → registre « champion / duel » (évènement).
- **Banderolle = thème sombre déjà défini** : fond anthracite `#1D1D1B` à **texture nid-d'abeilles
  (hexagones)** + **coup de pinceau rouge** + texte blanc. À réutiliser tel quel comme direction
  du mode sombre / écran projeté.

## 5. Pistes concrètes pour le CDC

1. **Figer les tokens** ci-dessus comme base des thèmes clair/sombre (cohérent avec l'existant).
2. **Thème sombre** : suivre la banderolle (anthracite + hexagones + accent rouge) — pas à inventer.
3. **Rouge = accent/surface**, texte anthracite/blanc (cf. contrainte WCAG §2).
4. **Chapitre « niveaux d'identité »** : charte permanente de l'app vs habillage d'un tournoi.

---
*Sources : `club/logo.pdf`, `club/banderolle pdf.pdf/.svg`, `CDC/Logo sur fond rouge.pdf/.svg`, `CDC/Affiche challenge des champions 2026.pdf/.svg` (+ PNG embarqué). Analyse du 2026-07-14.*
