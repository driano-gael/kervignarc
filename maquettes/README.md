# Maquettes — dossier de conception

> **Statut : support de travail en cours de revue. Ne fait autorité sur rien.**
> Ce dossier n'est pas du cadrage. En cas de divergence avec
> [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) ou
> [`cahier-des-charges-design.md`](../cahier-des-charges-design.md), **les CDC gagnent**.

## Comment s'en servir

1. Ouvre [`index.html`](index.html) dans un navigateur — c'est la porte d'entrée des 35 écrans.
2. Regarde un écran : chaque page présente **plusieurs partis pris de mise en page**, les **états système**
   (chargement, vide, erreur, hors-ligne, verrou, conflit) et, quand c'est utile, les **thèmes**.
3. Remplis son questionnaire dans [`questionnaires/`](questionnaires/) — un fichier Markdown par écran.
   Tu peux en traiter un par jour ou dix d'affilée : chaque fiche est indépendante.

Les questionnaires sont volontairement en Markdown : ils se remplissent dans ton éditeur, se versionnent,
et je les relis directement pour appliquer tes retours. Aucun export, aucune ressaisie.

## Ce qui se discute, et ce qui ne se discute pas

**Ce qui se discute** : la structure des écrans, la hiérarchie de l'information, le vocabulaire, les gestes,
ce qui manque.

**Ce qui ne se discute pas ici** : les couleurs. Elles viennent de la charte **mesurée**
(`cahier-des-charges-design.md` §3.3), où chaque valeur a son ratio de contraste calculé. Trois conséquences
qui expliquent l'essentiel de ce que tu vois :

- Le **rouge du club est une surface, jamais un accent** (`DV-04`) — 2,55:1 sur le fond sombre. On écrit
  *en blanc dessus*, pas *avec*.
- L'**alerte est ambre, en aplat plein** (`DV-03`) — le signal se joue sur la luminance, pas la teinte.
- Un **token sémantique est une paire**, pas une couleur : l'ambre `#FFB000` (9,22:1 sur sombre) tombe à
  1,83:1 sur blanc et **doit** devenir `#9F6D00` en thème clair.

Si tu veux contester une de ces règles, c'est légitime — mais ça se fait en **ADR**, pas dans un
questionnaire d'écran : elles engagent les 35 écrans à la fois.

## Organisation du dossier

```
maquettes/
├── index.html              porte d'entrée — les 35 écrans par application
├── assets/systeme.css      le système de design (tokens de la charte + composants)
├── <code>-<slug>.html      une page par écran
└── questionnaires/         une fiche Markdown par écran, à remplir
```

Le CSS est **partagé** : une correction de token se répercute sur les 35 pages. C'est aussi ce qui garantit
qu'aucune page n'invente sa propre couleur.

## Deux limites à connaître

1. **La police n'est pas la bonne.** La charte impose **Inter** (`DV-07`), qui n'est pas embarquée ici. Si tu
   ne l'as pas installée, tu vois une police système : les *proportions* sont justes, le *dessin* des lettres
   ne l'est pas.
2. **Ces maquettes vieillissent pendant qu'on les relit.** Exemple vécu : la planche **A15** (bascule de tour)
   a été dessinée comme un écran « à concevoir » ; **E12US002** a livré le feu vert le 28/07/2026, pendant la
   rédaction de ce dossier. La planche a été corrigée le jour même, mais le cas se reproduira — à chaque
   ouverture d'un questionnaire, vérifier `git log main --first-parent` si l'écran a l'air d'avoir bougé.
3. **« Écran existant » ne veut pas dire « conforme ».** La mention signale qu'un composant du même rôle vit
   dans `frontend/src/features/` — elle ne dit rien de la ressemblance entre l'écran livré et la maquette.
   Confronter les deux reste à faire.

## Trous trouvés en maquettant

Ce que l'exercice a fait remonter, et qui n'est écrit nulle part ailleurs :

| Trou | Détail |
|---|---|
| **Charte incomplète** | `--success` et `--info` sont marqués *⟦à dériver⟧* en thème clair. Valeurs proposées ici : `#0C7A61` et `#0B6E9E`. À valider et à reverser au CDC design. |
| **Écran manquant** | Le **conflit de saisie** (deux postes modifient la même volée) n'est décrit ni dans le CDC UX ni dans les stories. Inévitable dès lors que le scoreur peut corriger. |
| **Écran manquant** | Le **barrage** (égalité 5–5 en duel) n'apparaît dans aucune planche. Rare, décisif. |
| **Arbitrage matériel** | Le choix « pavé appelé » / « pavé permanent » (S02) ne se tranche pas sur le papier : il dépend de la taille réelle des tablettes du parc. |

## Lien avec les wireframes

Ce dossier **remplace** les planches basse fidélité de [`../docs/wireframes/`](../docs/wireframes/) pour tout
ce qui est mise en page. Les wireframes restent utiles pour une chose : ils portent le **parcours utilisateur**
de chaque application (diagrammes de flux), que les maquettes ne rejouent pas.
