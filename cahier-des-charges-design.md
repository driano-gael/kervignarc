# Cahier des charges — Visuel & Ergonomie — Kervignarc

**Solution logicielle de gestion de tournoi de tir à l'arc en salle (18 m)**

| | |
|---|---|
| **Version** | 0.1 (design — cadrage du périmètre graphique & ergonomique) |
| **Date** | 08/07/2026 |
| **Statut** | À valider par le client · **charte à compléter** |
| **Sources** | `cahier-des-charges.md` (fonctionnel v0.2), `cahier-des-charges-technique.md` (v0.1), entretien design du 08/07/2026 |
| **Périmètre** | Identité visuelle, système de design, ergonomie des 4 contextes d'usage, inventaire des besoins graphiques par module. Le détail d'implémentation front (composants React) découlera de ce document. |

> **Document vivant.** La charte graphique (couleurs, logo, typographie) est renseignée par **emplacements réservés** notés `⟦À COMPLÉTER⟧`. Elle sera mise à jour au fil de l'évolution de la solution. Les décisions à trancher sont marquées `Q-Dn`.

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

### 2.1 Les 4 contextes d'usage
Priorité de l'effort de design : **les quatre sont dans le périmètre** (décision entretien), avec un socle mutualisé.

| # | Contexte | Utilisateur | Terminal | Posture / condition | Enjeu ergonomique dominant |
|---|---|---|---|---|---|
| **C1** | **Pilotage** | Admin / organisateur | PC portable (clavier + souris/pavé) | Assis, poste de commande, concentré | Densité d'information, éditeur de phases, glisser-déposer, prévention d'erreur |
| **C2** | **Saisie** | Scoreur | ~30 tablettes (BYOD) | Debout, près du pas de tir, mains parfois froides | Rapidité tactile, gros boutons, très peu de clics, zéro ambiguïté |
| **C3** | **Consultation** | Archer / public | Mobile perso (BYOD hétérogène) | En mouvement, coup d'œil rapide | « Où je tire / où j'en suis » en < 3 s |
| **C4** | **Projection** | — (affichage passif) | Écran/vidéoprojecteur de salle | Vu à plusieurs mètres | Lisibilité à distance, hiérarchie forte, auto-défilement |

### 2.2 Conditions matérielles (issues du CDC technique)
- **Réseau local sans internet** → **tous les assets embarqués** : polices, icônes, images. **Aucune dépendance CDN / Google Fonts en ligne.** Contrainte forte sur le choix typographique (§4.3).
- **BYOD hétérogène** → cibler un large parc : tablettes Android/iPad d'âges divers, smartphones d'entrée de gamme. **Responsive obligatoire**, dégradation gracieuse sur petits écrans et navigateurs anciens.
- **PWA, tolérance aux coupures** → prévoir les **états visuels réseau** : en ligne / hors-ligne / synchronisation en cours / échec (cf. §7.2, composant *bandeau de connexion*).
- **Lumière de salle variable** (décision entretien) → **thème clair ET thème sombre** avec bascule ; **écran projeté en sombre par défaut** ; tablette adaptable à la salle.

### 2.3 Impacts directs sur le design
| Contrainte | Conséquence de conception |
|---|---|
| Mains froides / gestes rapides sur tablette | Cibles tactiles **≥ 48 px** (au-delà du minimum AA de 44 px), espacement généreux, pas de geste fin |
| Coup d'œil à distance (projeté) | Échelle typographique dédiée, contrastes renforcés, très peu de texte par écran |
| Réseau local sans internet | Bibliothèque de polices/icônes **auto-hébergée et versionnée** |
| Live + latence | Feedback optimiste + indicateur de synchro visibles |

---

## 3. Identité visuelle *(charte club existante — à compléter)*

> **Cadre.** Une charte club existe et doit être respectée (décision entretien), mais les éléments concrets ne sont pas encore fournis. Cette section fixe **la structure attendue** de l'identité ; les valeurs seront renseignées dans les emplacements réservés et versionnées.

### 3.1 Marque
- **Nom du club / compagnie** : `⟦À COMPLÉTER⟧`
- **Nom du tournoi** (si distinct) : `⟦À COMPLÉTER⟧`
- **Baseline / ton éditorial** : sportif & dynamique (à décliner en microcopie, §8).

### 3.2 Logo
- **Fichier(s)** : `⟦À COMPLÉTER — déposer le SVG dans /assets/brand/⟧`
- Déclinaisons attendues : **horizontale** (barre de nav admin), **carrée/icône** (favicon, PWA, écran projeté), **monochrome clair** et **monochrome sombre** (pour poser sur fonds contrastés).
- **Zone de protection**, taille minimale et interdits d'usage : `⟦À COMPLÉTER⟧`

### 3.3 Palette de couleurs
Structure cible (valeurs à renseigner depuis la charte club) :

| Rôle | Usage | Valeur |
|---|---|---|
| **Primaire** | Actions principales, identité | `⟦#______⟧` |
| **Secondaire** | Accents, éléments sportifs | `⟦#______⟧` |
| **Accent / signal** | Live, points chauds, alertes positives | `⟦#______⟧` |
| **Neutres** (5–7 gris) | Fonds, bordures, textes | `⟦échelle à définir⟧` |
| **Sémantiques** | succès / avertissement / erreur / info | `⟦4 couleurs, contrastées AA⟧` |
| **Fonds thème clair / sombre** | Surfaces des deux thèmes | `⟦À COMPLÉTER⟧` |

> ⚠️ **Toute couleur de la charte utilisée sur du texte ou une cible d'action devra être validée en contraste WCAG AA** (§6). Si une couleur club ne passe pas, on définira une **variante accessible** dédiée à l'UI (la charte de communication et la charte applicative peuvent diverger sur ce point — à acter, `Q-D1`).

### 3.4 Typographie
- **Contrainte** : polices **embarquées** (réseau local sans internet). Pas de police propriétaire non redistribuable sauf licence.
- **Couple recommandé** (à valider) : une police de titres à caractère sportif + une police de texte très lisible en petit corps et sur tablette. Proposition par défaut si la charte n'impose rien : `⟦À COMPLÉTER — ex. Inter / IBM Plex⟧`.
- **Échelle typographique** : à définir par contexte — notamment une **échelle « écran projeté »** nettement plus grande que l'échelle applicative (§7.4).

### 3.5 Iconographie & imagerie
- **Jeu d'icônes** unique, embarqué, cohérent (trait, épaisseur, grille). `⟦set à choisir⟧`
- **Pictogrammes métier** spécifiques à dessiner : **blason/cible**, **flèche/volée**, **position A/B/C/D**, **club**, **départ**, statuts de match. (cf. §5.4)
- **Imagerie / photos** : usage, droits, traitement `⟦À COMPLÉTER⟧`.

---

## 4. Système de design *(sur-mesure — cf. Q-D2)*

### 4.1 Approche
Décision entretien : **système de design sur-mesure**. Recommandation inscrite (à confirmer `Q-D2`) : **couche visuelle 100 % sur-mesure** (aucune identité de librairie visible) **posée sur des primitives d'accessibilité éprouvées** (comportement clavier / ARIA / focus / gestion du focus-trap). On garde une identité entièrement propre sans réécrire les fondations d'accessibilité — cohérent avec l'exigence WCAG AA (§6) et la stack **React + TypeScript** du CDC technique.

### 4.2 Design tokens (source de vérité)
Le système repose sur des **tokens** (variables de design) versionnés, faisant le lien charte ↔ code :
- **Couleur** (rôles sémantiques, pas de couleur « en dur »), **typographie** (familles, tailles, graisses, interlignes), **espacement** (échelle 4/8 px), **rayons**, **ombres/élévation**, **durées d'animation**, **points de rupture responsive**.
- **Thématisation par tokens** : le passage clair ↔ sombre ↔ projeté ne change que les valeurs de tokens, pas les composants (§7).

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
Par criticité le jour J, à maquetter en premier :
1. **Saisie de score tablette (M5)** — le poste le plus utilisé et le plus sensible aux erreurs.
2. **Plan de cibles / placement (M4)** — l'écran signature de l'admin (drag-drop + contraintes).
3. **Éditeur de séquence de phases (M3)** — la complexité fonctionnelle la plus élevée à rendre lisible.
4. **Écran projeté classement/tableau (C4/M7)** — la vitrine de l'événement.
5. **Consultation mobile « ma cible / mon classement » (C3)** — le plus grand nombre d'utilisateurs.

### 5.3 Parcours à scénariser (maquettes de flux, pas seulement d'écrans)
- **Préparer un tournoi** (admin) : création → gabarit → séquence de phases → inscriptions → placement → impression.
- **Saisir une volée** (scoreur) : sélection cible → archer → saisie flèche par flèche → validation → passage archer suivant. Objectif chiffré à fixer (`Q-D3`, ex. « une volée de 3 flèches saisie et validée en < 10 s »).
- **Trouver sa cible** (archer/public) : ouverture → recherche nom → « vous tirez cible 12, position B, départ 2 ».
- **Suivre le live** (public/projeté) : rotation automatique classement ↔ tableaux ↔ plans.

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

- **Contrastes** : texte normal ≥ 4,5:1, texte large ≥ 3:1, éléments d'interface/graphiques ≥ 3:1. **Toute couleur de charte est validée sous cette contrainte** (cf. §3.3, `Q-D1`).
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

### 7.1 Thèmes (clair / sombre / projeté)
- **Thème clair** et **thème sombre** pilotés par tokens (§4.2), **bascule manuelle** + respect de la préférence système.
- **Thème projeté** : variante à très fort contraste, grand corps, dérivée du thème sombre (§7.4).
- Le choix par défaut s'adapte au contexte : tablette = selon lumière de salle ; projeté = sombre.

### 7.2 États système transverses (à concevoir une fois, réutilisés partout)
Chargement (squelettes), **vide** (message + action), **erreur** (récupérable), **hors-ligne / synchro** (bandeau de connexion), **live** (indicateur de fraîcheur des données), **verrou** (score validé), **conflit** (correction concurrente).

### 7.3 Ergonomie C1 — Pilotage admin (PC)
- Densité maîtrisée, navigation persistante, raccourcis clavier, **prévention d'erreur** (confirmations sur actions destructrices, validation en amont dans M3).
- Le drag-drop (M4) a des **alternatives clavier/menu** (accessibilité + robustesse).
- Feedback immédiat des contrôles de cohérence (M3 EF-3.8).

### 7.4 Ergonomie C2 — Saisie tablette (scoreur) — *poste critique*
- **Peu de clics, gros boutons, une action à la fois.** Le pavé de volée occupe le pouce/l'index sans viser.
- **Feedback optimiste** : la saisie s'affiche instantanément, la synchro se fait en tâche de fond avec indicateur.
- **Prévention d'erreur** : ordre logique des flèches, annulation/correction immédiate avant validation, confirmation de validation, **verrouillage** après coup avec correction tracée par rôle habilité.
- Fonctionne **debout, d'une main**, mains froides : zones de touche larges, pas de geste précis.
- Objectif de performance de saisie à chiffrer (`Q-D3`).

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

| # | Sujet | À décider |
|---|---|---|
| **Q-D1** | Divergence charte communication ↔ charte applicative si une couleur club ne passe pas le contraste AA | Autorise-t-on une **variante accessible** dédiée à l'UI ? |
| **Q-D2** | Périmètre du « sur-mesure » | **Couche visuelle sur-mesure sur primitives a11y** (recommandé) **ou** tout recodé y compris comportements (poste de coût/risque) ? |
| **Q-D3** | Objectif de performance de saisie tablette | Fixer une cible chiffrée (ex. volée de 3 flèches saisie+validée < 10 s) |
| **Q-D4** | Éléments de charte concrets | Fournir **nom, couleurs (hex), logo (SVG), typo** |
| **Q-D5** | Mode de saisie tablette par défaut | Scoreur (défaut) vs archer — cohérent avec H1/Q7 du CDC fonctionnel ; impacte l'écran C2 |
| **Q-D6** | Support cible minimal (BYOD) | Liste des navigateurs/OS/tailles d'écran à garantir |
| **Q-D7** | Multilingue | Interface FR seule, ou prévoir l'internationalisation ? |
| **Q-D8** | Personnalisation par tournoi | Le logo/les couleurs peuvent-ils changer d'un tournoi à l'autre, ou charte club figée ? |

---

*Document produit à partir du CDC fonctionnel v0.2, du CDC technique v0.1 et de l'entretien design du 08/07/2026. Charte graphique à compléter et à faire vivre avec la solution. À relire et amender avant lancement de la conception UI/UX.*
