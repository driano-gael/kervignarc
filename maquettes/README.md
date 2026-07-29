# Maquettes — dossier de conception

> **Statut : support de travail en cours de revue. Ne fait autorité sur rien.**
> Ce dossier n'est pas du cadrage. En cas de divergence avec
> [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) ou
> [`cahier-des-charges-design.md`](../cahier-des-charges-design.md), **les CDC gagnent**.

## Point de reprise — au 29/07/2026

*Cette section est le **point d'entrée d'une nouvelle session**. Elle dit où on en est, ce qui attend
une décision, et ce qu'il ne faut surtout pas refaire trop tôt. Elle se met à jour à chaque avancée.*

### Ce qui est fait

| | |
|---|---|
| **35 écrans maquettés** | 19 admin · 9 saisie · 7 publique — tout est dans `main` |
| **35 questionnaires saisissables** | on répond dans le navigateur, « Télécharger le .md » produit le fichier à déposer dans `questionnaires/` |
| **Système de design** | `assets/systeme.css` — transcrit la charte **mesurée** du CDC design §3.3, ratio de contraste en commentaire sur chaque token |
| **Revue** | **1 écran arbitré sur 35** — A02. Les 34 autres questionnaires sont vierges. |

### Le seul arbitrage rendu à ce jour — A02

Verdict du commanditaire sur la v1 : **🔴 à refaire**. Réponse intégrale versionnée dans
[`questionnaires/a02-ossature.md`](questionnaires/a02-ossature.md) — **c'est la source à relire en
premier**, pas ce résumé.

Modèle retenu pour la v2, sur **trois niveaux** :

| Niveau | Mot | Choisit | Qui l'a arrêté |
|---|---|---|---|
| 1 | **rôle** | quel écran : administration, saisie, public | commanditaire |
| 2 | **espace** | ce que je viens faire : Préparation · Déroulé · Résultats | commanditaire (« espace ») ; noms proposés par l'assistant |
| 3 | **étape** | où j'en suis dans cet espace | assistant |

Les **4 étapes de la Préparation** viennent du commanditaire : briques → assemblage → organisation →
remplissage. Conséquence structurante actée : **les briques (catégories, blasons, clubs, gabarits,
barèmes, tarifs) sont le patrimoine du club, pas d'un tournoi** — elles vivent hors du sélecteur de
tournoi.

« Phase » a été **écarté** pour le niveau 3 : le mot désigne déjà une entité du domaine sportif
(qualification, 1/8ᵉ — `ADR-0011`).

### Ce qui attend une décision du commanditaire

1. **Les étapes du Déroulé et des Résultats** — celles de la planche A02 sont une **déduction de
   l'assistant**, pas la description du commanditaire. C'est le point le plus fragile du dossier et
   la première question du questionnaire A02.
2. **Les mots** — « étape » pour le niveau 3, « Résultats » plutôt qu'« Après ».
3. **Briques référencées ou copiées ?** Si un tarif change en 2027, le tournoi 2026 archivé
   doit-il bouger ? Cette question **touche le modèle de données, pas la maquette** : elle se tranche
   avec [`docs/modele-de-donnees.md`](../docs/modele-de-donnees.md) et mérite un **ADR**.

### ⚠️ Ce qu'il ne faut pas faire tout de suite

**Ne pas refaire A03, A04, A06 et A09.** Elles découlent mécaniquement du nouveau modèle
d'ossature — les reprendre avant que le modèle soit validé, c'est quatre fois le même rework.
A06 en particulier range encore les référentiels sous le sélecteur de tournoi, ce que le modèle v2
contredit.

### Comment reprendre

Dire simplement « **on reprend les maquettes** ». L'état réel se lit dans les fichiers, pas dans la
mémoire d'une session :

- `questionnaires/*.md` — un fichier rempli = un écran arbitré ;
- `git log main --first-parent -- maquettes/` — l'historique des décisions.

Pour consulter les pages sans perturber un agent qui travaillerait en parallèle sur le dépôt, créer
un répertoire de consultation dédié :

```bash
git worktree add ../kervignarc-maquettes main
# puis ouvrir ../kervignarc-maquettes/maquettes/index.html
```

---

## Comment s'en servir

1. Ouvre [`index.html`](index.html) dans un navigateur — c'est la porte d'entrée des 35 écrans.
2. Regarde un écran : chaque page présente **plusieurs partis pris de mise en page**, les **états système**
   (chargement, vide, erreur, hors-ligne, verrou, conflit) et, quand c'est utile, les **thèmes**.
3. Clique sur **« Remplir le questionnaire »** : la feuille s'ouvre **dans le navigateur, saisissable**.
   Tu réponds, puis **« ⬇ Télécharger le .md »** produit le fichier à déposer dans
   [`questionnaires/`](questionnaires/).

La navigation va **dans les deux sens** : chaque maquette pointe vers son questionnaire, chaque questionnaire
ramène à sa maquette — et les deux enchaînent vers l'écran suivant, pour dérouler les 35 sans repasser par
l'index.

**Pourquoi cette mécanique en deux temps.** Le livrable versionné reste le **Markdown** : c'est lui qui se
diffe, se relit et se commente dans Git. Mais un `.md` ouvert dans un navigateur n'est qu'un texte mort — d'où
la feuille HTML, qui n'est qu'un **moyen de le remplir confortablement**. Rien n'oblige à passer par elle :
les gabarits `.md` vierges restent dans `questionnaires/` pour qui préfère son éditeur.

Trois détails utiles :

- **Tes réponses sont sauvegardées au fil de la frappe** dans le navigateur : un onglet fermé ne fait pas
  perdre vingt minutes. Si le stockage est refusé (certains navigateurs le bloquent sur les fichiers ouverts
  en `file://`), la page **le dit** au lieu de faire semblant — télécharge alors avant de fermer.
- **« Aperçu »** montre le Markdown exact qui sera produit, sans rien télécharger.
- **« Copier le markdown »** fonctionne aussi hors contexte sécurisé (repli sur `execCommand`) — même piège
  technique que le jour J, où l'appli tourne en `http` sur le réseau local.

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
├── index.html                    porte d'entrée — les 35 écrans par application
├── assets/systeme.css            le système de design (tokens de la charte + composants)
├── assets/questionnaire.css/.js  la feuille saisissable et son export markdown
├── <code>-<slug>.html            une page de maquette par écran
└── questionnaires/
    ├── <slug>.html               la feuille à remplir dans le navigateur
    └── <slug>.md                 le gabarit vierge — et la cible de l'export
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
