# EPIC-17 — Fidélité de l'application aux maquettes — User Stories

> Voir [`epics/EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) et
> [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md).
>
> **Ne pas confondre avec [`E16`](E16-retours-maquettes.md)** : E16 traite ce que le commanditaire
> reproche **aux maquettes** ; E17 amène **le produit** jusqu'à elles. Une US qui change ce que
> montre un écran est une E16 ; une US qui change **la ressemblance** entre l'écran et sa planche est
> une E17.
>
> **La source du CA est ici la planche et la charte mesurée**, pas un questionnaire : les écarts se
> constatent en superposant `maquettes/<code>-<slug>.html` et l'écran livré.

---

### E17US001 — Poser la charte du club dans l'application
*En tant qu'*organisateur, *je veux* que l'application porte **les couleurs et la typographie de mon club**, *afin de* montrer au bureau l'outil qui a été validé sur les maquettes, et non une maquette technique grise et violette.

- **Contexte** : `frontend/src/index.css` portait encore, en toutes lettres, le socle du walking
  skeleton — *« le design sur-mesure sera posé par les US design »*. Ces US n'existaient pas. Les 98
  US livrées ont donc toutes hérité d'un accent violet `#aa3bff`, d'un fond blanc et de `system-ui`.
- **CA** :
  - **aucune couleur n'est écrite dans le front hors d'`index.css`** — les features ne connaissent
    que des jetons **sémantiques** (le nom dit l'usage, jamais la teinte) ; les seules exceptions
    admises sont celles qui ont une raison **physique** et commentée (le QR reste sur fond blanc pour
    rester scannable, quel que soit le thème) ;
  - les jetons portent **les valeurs de la charte mesurée** ([CDC design §3.3](../cahier-des-charges-design.md)),
    telles que transcrites par [`maquettes/assets/systeme.css`](../maquettes/assets/systeme.css) —
    anthracite `#1D1D1B`, rouge club `#B71918`, alerte ambre `#FFB000` ;
  - **le rouge du club n'est jamais une couleur de texte ni de contour en thème sombre** (`DV-04`,
    2,55:1) : trois jetons distincts selon l'usage — aplat, contour, texte ;
  - **l'alerte est ambre, jamais rouge** (`DV-03`) ; le rouge sur l'anthracite ne signale rien ;
  - **chaque déclinaison de thème redéfinit l'ensemble des jetons** : un jeton oublié dans un thème
    est une faute de contraste silencieuse (l'ambre `#FFB000` tombe à 1,83:1 sur blanc) ;
  - **le thème sombre est le défaut**, sans suivre le système (`DV-02`) ; le choix explicite d'un
    poste le surcharge, et l'option « Système » de `D-26` **reste disponible et fonctionnelle** ;
  - un **contour d'élément actionnable** (champ, bouton, touche) est distinct d'un **séparateur
    décoratif** : 4,04:1 contre 1,55:1 (WCAG 1.4.11) ;
  - la **police est celle des maquettes**, à pile de repli identique, pour que l'écran et la planche
    se dégradent de la même façon quand Inter est absente du poste.
- **Notes** : `DV-02`, `DV-03`, `DV-04`, `DV-07`, `D-26` · [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md).
  **Un seul arbitrage discutable** : l'ancien `--text` du produit (corps) devient
  `--text-secondary` et non `--text`, pour **conserver la hiérarchie à deux niveaux** que
  `--text`/`--text-h` portaient. Reprendre `--text` partout aurait mis tout le corps de texte à
  16,88:1 et aplati la hiérarchie sur la seule graisse. **Réversible en une ligne** si le rendu
  paraît trop sourd. **Non fait, à arbitrer** : embarquer Inter (ajout d'actif, règle 11 — sans
  fichier local, aucune tablette ne la chargera le jour J, qui tourne sans internet) ; et la
  **couleur d'une action destructrice**, que la charte ne définit pas — elle est ambre par défaut,
  ce qui lui fait partager sa teinte avec « poste hors ligne ».
- **Dépend de** : — · **Jalon** : J1 *(transverse : conditionne toute confrontation d'écran)*
