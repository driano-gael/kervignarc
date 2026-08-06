# ADR-0074 — Les maquettes font foi, et la charte mesurée est la source des jetons du front

- **Statut** : accepté
- **Date** : 05/08/2026
- **US** : E17US001
- **Amende** : [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md) *(inchangé sur le
  fond — l'ossature à trois axes est confirmée, c'est sa **palette** qui change)* ·
  [`epics/EPIC-16`](../../epics/EPIC-16-retours-maquettes.md) § Exclus

## Contexte

Le commanditaire, regardant l'application à côté des 36 planches de [`maquettes/`](../../maquettes/),
constate qu'elles n'ont **aucun rapport visuel**. Ce n'est pas une impression : c'est écrit dans le
code depuis le premier jour. En tête de `frontend/src/index.css` :

> *« Le design sur-mesure (charte club, WCAG AA) sera posé par les **US design** ; ici, un socle
> neutre et lisible (walking skeleton). »*

Ces « US design » n'ont **jamais existé** dans le backlog. Les 98 US livrées ont donc toutes été
construites sur le socle provisoire, dont l'accent est un **violet `#aa3bff`** sans lien avec le
club, sur fond blanc, en `system-ui`. Les maquettes, elles, appliquent
[`maquettes/assets/systeme.css`](../../maquettes/assets/systeme.css), transcription de la **charte
mesurée** de [`cahier-des-charges-design.md`](../../cahier-des-charges-design.md) §3.3 : anthracite
`#1D1D1B`, rouge club `#B71918` en aplat, alerte ambre `#FFB000`, Inter.

Deux vocabulaires de jetons cohabitaient donc, **disjoints** :

| Produit (socle) | Maquettes (charte) |
|---|---|
| `--bg` · `--surface` · `--text` · `--text-h` · `--accent` · `--warn` · `--ok` · `--dim` | `--surface-0/1/2` · `--text-muted/secondary/text` · `--brand-surface/border/text` · `--danger` · `--danger-strong` · `--success` · `--info` |

Le piège n'est pas la traduction : ce sont les **trois noms communs** — `--text`, `--border`,
`--danger` — qui portent des **valeurs différentes** de part et d'autre. Un renommage naïf aurait
produit un résultat faux sans lever la moindre erreur.

Enfin, `maquettes/README.md` se déclarait lui-même *« support de travail […] ne fait autorité sur
rien »*, et [`EPIC-16`](../../epics/EPIC-16-retours-maquettes.md) excluait les planches comme
*« pas de spécification vivante »*. Tant que ce statut tenait, **aucune revue ne pouvait opposer un
écart au front** : la conformité n'était l'affaire de personne. Le README le disait sans détour —
*« "Écran existant" ne veut pas dire "conforme" […] Confronter les deux reste à faire. »*

## Décision

**1. Les planches de `maquettes/` deviennent la référence opposable de mise en page du front.** Un
écart entre l'écran livré et sa planche est un **défaut**, constatable en revue, et non plus une
divergence tolérée. Les CDC restent au-dessus : en cas de conflit planche ↔ charte, **la charte
mesurée l'emporte** (elle porte les ratios de contraste), et la planche est corrigée.

Deux réserves, permanentes, à lire avec la règle :

- **La fidélité porte sur la mise en page, pas sur le balisage.** Là où la planche décrit un rendu
  qu'une structure sémantique rend mieux — un `<table>` contre une pile de `<div>` —, le produit
  garde la structure et n'en prend que l'apparence. Une planche est dessinée, elle n'est pas lue par
  un lecteur d'écran.
- **Un arbitrage explicite du commanditaire l'emporte sur la planche.** Cas déjà constaté : la
  densité. Les planches sont serrées, le questionnaire A02 demande l'inverse (« je mettrai plus
  d'espace, plus aéré […] pour tous les écrans ») — c'est la planche qui est en retard.

**2. `frontend/src/index.css` ne définit plus de couleur : il transcrit la charte.** Les jetons du
produit adoptent le **vocabulaire des maquettes**, un seul pour les deux dépôts de vérité. La table
de correspondance appliquée :

| Socle | Charte | Raison du choix |
|---|---|---|
| `--bg` | `--surface-0` | fond de page |
| `--surface` | `--surface-1` | cartes et panneaux |
| `--text-h` | `--text` | le niveau fort |
| `--text` | `--text-secondary` | **arbitrage** — voir ci-dessous |
| `--dim` | `--text-muted` | métadonnées |
| `--border` | `--border-subtle`, **sauf** contours actionnables → `--border` | WCAG 1.4.11 |
| `--accent` | `--brand-surface` / `--brand-border` / `--brand-text` **selon l'usage** | `DV-04` |
| `--warn` **et** `--danger` | `--danger`, escaladé en `--danger-strong` là où deux états coexistent | `DV-03` — l'alerte est ambre ; deux niveaux d'ambre, jamais de rouge |
| `--ok` | `--success` | |

**3. Le sombre est le défaut, sans suivre l'OS.** `:root` porte la déclinaison sombre de la charte
(`DV-02` : `#1D1D1B` est le fond de la banderole du club). L'option « Système » de `D-26` est
**conservée**, comme une valeur à part entière : `appliquerTheme('systeme')` pose
`data-theme="systeme"`, auquel une unique règle `@media (prefers-color-scheme: light)` rend son effet.

⚠️ **« Aucun choix » et « Système » sont deux choses distinctes**, et les confondre annule la
décision. La première version les confondait — `appliquerTheme(null)` posait `"systeme"`, or le store
initialise à `null` : une tablette neuve sous OS clair ouvrait donc l'application **en clair**,
c'est-à-dire l'alternative rejetée plus bas. Depuis la revue, `null` (jamais choisi) donne le
**sombre**, et seul un choix explicite active le suivi de l'OS.

**4. Deux valeurs ⟦DÉRIVÉ⟧ sont adoptées** : `--success:#0C7A61` et `--info:#0B6E9E` en thème clair,
absentes du CDC design §3.3.4 et proposées par le dossier de maquettes.

## Conséquences

- **L'application change d'apparence d'un coup, sur ses ~40 features à la fois.** C'est l'effet
  recherché : la palette vivait à un seul endroit, c'est ce qui rend le geste possible en une passe.
- **Le rouge du club cesse d'être un accent.** Là où `--accent` servait indistinctement de fond, de
  contour et de texte, il faut désormais choisir : `--brand-surface` (aplat), `--brand-border`
  (contour), `--brand-text` (texte). Le rouge ne fait que **2,55:1** sur l'anthracite ; l'écrire en
  texte sur le fond sombre était une faute de contraste que le socle violet masquait.
- **`--warn` disparaît.** [`stories/E12`](../../stories/E12-pilotage-jour-j.md) le citait nommément
  pour le poste hors ligne ; la note y est corrigée. L'invariant réellement porté par le CA est
  inchangé : **couleur + icône + texte**, jamais la couleur seule (`DV-03`).
- **Un bouton destructif devient ambre — en contour et en texte, jamais en aplat.** L'aplat a été
  essayé puis rejeté sur pièce (E17US002) : sur l'accueil de pilotage, « Annuler le tournoi » y
  écrasait « Marquer prêt », l'action principale. Ce n'est de toute façon pas la couleur du bouton
  qui protège, c'est le dialogue de confirmation ([ADR-0072](0072-confirmation-destructrice-dialog-natif.md)).
  **Point à confirmer par le commanditaire**, porté par une case à cocher d'`EPIC-17 § Capacités`
  pour qu'il ne se perde pas : la charte ne définit **aucune** couleur d'action destructrice ; c'est
  un **trou constaté**, pas un choix.
- **L'alerte a deux niveaux, pas un.** La fusion de `--warn` dans `--danger` avait rendu
  **identiques** des paires d'états que le produit distinguait (déconnecté / connexion en cours,
  erreur / alerte, annulé / en cours, dû / partiel, bloquant / avertissement). La charte porte
  `--danger` (9,22:1) **et** `--danger-strong` (11,79:1) : c'est le second qui porte l'escalade, le
  rouge restant exclu. *(Défaut trouvé à la revue : la substitution avait été mécanique.)*
- **Inter n'est pas embarquée.** `DV-07` l'impose, mais l'ajouter est un **ajout d'actif à arbitrer**
  (règle 11) et le jour J tourne **sans internet** : sans fichier local, aucune tablette ne la
  chargera. La pile de repli retenue est **exactement celle des maquettes**, de sorte que
  l'application et les planches se dégradent vers la même police. À trancher dans une US dédiée.
- **`E01US016`** (identité visuelle *par tournoi*) reste entière : elle surchargera ces jetons pour
  le public et l'écran de salle uniquement (`D-27`). Le fait qu'ils soient désormais **sémantiques et
  centralisés** est ce qui la rend implémentable sans toucher aux features.

## Alternatives écartées

- **Garder les noms du produit et n'en changer que les valeurs.** Moins de diff, mais deux
  vocabulaires subsistent pour une seule palette : chaque écran repris depuis une planche aurait
  demandé une traduction mentale, et `--warn`/`--danger` seraient restés deux noms pour une couleur.
- **Suivre `prefers-color-scheme` par défaut.** C'est le comportement d'origine. Rejeté : le jour J,
  ~30 tablettes BYOD suivent chacune le réglage de son propriétaire — l'application n'aurait pas deux
  fois la même apparence dans le gymnase, ce qui est l'inverse de la fidélité demandée.
- **Résoudre « Système » en JavaScript (`matchMedia`).** Fonctionne, mais demande un écouteur à
  câbler et à nettoyer pour obtenir ce qu'une règle `@media` fait nativement et en direct.
- **Promouvoir les planches écran par écran.** Évitait de figer les quatre arbitrages encore ouverts
  du dossier (noms des axes, niveau sous l'axe, étanchéité de l'Atelier, verdict d'A01), mais laissait
  un statut variable d'un écran à l'autre — donc inopposable en revue, ce qui était le problème.
