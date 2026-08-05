# Maquettes — dossier de conception

> **Statut : support de travail en cours de revue. Ne fait autorité sur rien.**
> Ce dossier n'est pas du cadrage. En cas de divergence avec
> [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) ou
> [`cahier-des-charges-design.md`](../cahier-des-charges-design.md), **les CDC gagnent**.

## Point de reprise — au 05/08/2026

*Cette section est le **point d'entrée d'une nouvelle session**. Elle dit où on en est, ce qui attend
une décision, et ce qu'il ne faut surtout pas refaire trop tôt. Elle se met à jour à chaque avancée.*

### Ce qui est fait

| | |
|---|---|
| **36 écrans maquettés** | 1 porte d'entrée · 19 admin · 9 saisie · 7 publique |
| **151 écrans pleins** | chaque planche est rendue à la **taille réelle de son appareil**, ossature comprise — PC 1600 × 900, tablette 1280 × 800, vidéoprojecteur 1920 × 1080, téléphone 390 × 844 |
| **36 questionnaires saisissables** | trame en **onze sections**, générée depuis `assets/questionnaire.js` ; « Télécharger le .md » produit le fichier à déposer dans `questionnaires/` |
| **Système de design** | `assets/systeme.css` — transcrit la charte **mesurée** du CDC design §3.3, ratio de contraste en commentaire sur chaque token |
| **Ossature** | `assets/appareils.js` — la navigation des trois axes est **transcrite d'`axes.ts`** (30 destinations), pas recopiée à la main |
| **Revue** | **tour 1 clos** : les 36 questionnaires ont été remplis le 04/08/2026 et sont archivés dans `questionnaires/tour-1-2026-08-04/`. Le **tour 2** repart de zéro sur les écrans pleins. |
| **Livré dans le code** | l'ossature de ce dossier **est implémentée** : E14US003, [ADR-0058](../docs/adr/0058-decoupage-de-l-admin-en-trois-axes-d-activite.md). Le vocabulaire de salle aussi : E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md) |

### Pourquoi le dossier a basculé en plein écran — 05/08/2026

Le commanditaire ne voyait *« que des composants de pages »*. Deux causes, cumulées : `.variante`
bornait chaque maquette à **430 px**, et **aucune ossature n'était balisée** — les `.colonnes` /
`.flanc` du CSS étaient des vestiges du modèle v1 refusé, utilisés par **zéro** page sur 36. On
jugeait donc un composant hors de son emplacement final, ce qui rend la critique difficile à formuler.

Quatre choses à savoir avant de toucher au dossier :

- **`transform: scale()`, jamais `zoom`.** `zoom` refait la mise en page aux dimensions réduites : les
  retours à la ligne ne tombent pas où ils tombent à 100 %, on jugerait une mise en page qui n'existe
  pas. Et **ne jamais ajouter `will-change:transform` ni `translateZ(0)`** sur un cadre — le texte
  deviendrait flou sur les 151 planches d'un coup.
- **La hauteur est fixe**, donc la ligne de flottaison existe : un voile annonce « ↓ N px sous la
  ligne », mesuré à l'exécution. C'est ce qui permet enfin de poser la question « le bouton est-il
  visible sans défiler ? », impossible tant que les `.ui` s'étiraient au contenu.
- **L'ossature est générée** depuis des attributs `data-*`, pas écrite dans chaque bloc — sans quoi une
  correction toucherait 151 endroits. Contrepartie : `appareils.js` **se désynchronise d'`axes.ts`** à
  chaque US qui renomme ou ajoute une destination. Le resynchroniser fait partie de la reprise.
- **Le cadre est l'écran nu**, sans chrome navigateur. Exact pour la cible et le vidéoprojecteur, qui
  tournent en plein écran le jour J ; **optimiste d'environ 120 px** sur PC et téléphone, où une barre
  d'adresse mange le haut. Décision assumée, à ne pas « corriger » sans la rouvrir.

### Le modèle d'ossature, arrêté le 30/07/2026 — **trois axes d'activité**

Le critère de découpage a changé **deux fois**. Il faut connaître les trois états pour ne pas
réintroduire un modèle abandonné :

| Version | Critère | Sort |
|---|---|---|
| v1 | temps du tournoi — Préparation / Jour J / Après | **🔴 refusée** : « la sidebar fait vivre le tournoi sous tous ses états en même temps » |
| v2 | même découpage, renommé « espaces » + un 3ᵉ niveau « étape » | **abandonnée** : le problème était le *critère*, pas le vocabulaire |
| **v3** | **nature de l'activité** — Atelier (hors tournoi) · Pilotage · Gestion | **retenue et livrée** |

Ce qui a emporté la décision : un rangement temporel **coupe en morceaux une activité qui dure**. La
gestion administrative commence des semaines avant, encaisse pendant, exporte après — rangée par
temps, elle se disperse. C'était le cas dans le code livré, par simple ordre d'arrivée des US.

Décisions actées avec le commanditaire :

- les trois axes sont le **travail de l'admin** ⇒ un **accueil admin** choisit l'axe. L'option « trois
  URL de premier niveau » a été **écartée** ;
- **vraies URL par rôle** (`/public`, `/scoreur`, `/cible`, `/admin/<axe>/…`), la mémoire de position
  étant portée par l'URL ;
- les **briques sont le patrimoine du club** : **copiées** dans le tournoi à l'assemblage, modifiables
  localement, et une modification déclarée **permanente remonte** dans la brique de l'atelier ;
- la **recherche change de nature selon l'axe** : toutes entités et ouverture en *modification* en
  atelier/gestion, archer *du tournoi* en *consultation* en pilotage.

### Ce qui attend une décision du commanditaire

1. **Les mots** — « Atelier », « Pilotage », « Gestion » sont de l'assistant ; le commanditaire a
   donné les **contenus** des trois axes, pas leurs étiquettes. Première question du questionnaire A02.
2. **Faut-il un niveau nommé sous l'axe ?** Les quatre temps de la Préparation donnés le 29/07
   (briques → assemblage → organisation → remplissage) se **redistribuent** sur les trois axes
   plutôt que de disparaître — reste à dire s'il faut encore un niveau, ou juste une liste plate.
3. **L'étanchéité le jour J** — l'axe Gestion doit rester ouvert (`P-3`, le retardataire de 8 h 50) ;
   l'atelier n'a rien à faire dans la journée (`P-6`). Masqué, ou seulement rangé ailleurs ?
4. **Le verdict d'ensemble d'A01** n'a pas été rendu (aucune case cochée en §2).

### ⚠️ Ce qu'il ne faut pas faire tout de suite

**Ne pas redessiner les écrans de l'Atelier en supposant qu'ils sont hors tournoi.** Quatre d'entre
eux — catégories, blasons, barèmes, phases — portent encore un identifiant de tournoi côté serveur
(**DETTE-023**). Seuls **Clubs** et **Gabarits** tiennent la promesse. Le lot « atelier » les
libérera ; dessiner avant, c'est dessiner un écran qui ne peut pas exister.

**Ne pas rouvrir le débat « trois URL de premier niveau »** : tranché, écarté par le commanditaire.

### Comment reprendre

Dire simplement « **on reprend les maquettes** ». L'état réel se lit dans les fichiers, pas dans la
mémoire d'une session :

- `questionnaires/*.md` — un **talon** = écran non arbitré, un fichier rempli = écran arbitré ;
- `questionnaires/tour-1-2026-08-04/` — les 36 réponses du premier tour, rendues sur les vignettes.
  Plusieurs ont déjà piloté des changements du front (commit `a660f8f`) : à lire avant de refaire un
  écran, pour ne pas redemander ce qui est acquis ;
- `git log main --first-parent -- maquettes/` — l'historique des décisions.

Pour consulter les pages sans perturber un agent qui travaillerait en parallèle sur le dépôt, créer
un répertoire de consultation dédié :

```bash
git worktree add ../kervignarc-maquettes main
# puis ouvrir ../kervignarc-maquettes/maquettes/index.html
```

---

## Comment s'en servir

1. Ouvre [`index.html`](index.html) dans un navigateur — c'est la porte d'entrée des 36 écrans.
2. Regarde un écran : chaque page présente **plusieurs partis pris de mise en page**, les **états système**
   (chargement, vide, erreur, hors-ligne, verrou, conflit) et, quand c'est utile, les **thèmes**.
3. Clique sur **« Remplir le questionnaire »** : la feuille s'ouvre **dans le navigateur, saisissable**.
   Tu réponds, puis **« ⬇ Télécharger le .md »** produit le fichier à déposer dans
   [`questionnaires/`](questionnaires/).

La navigation va **dans les deux sens** : chaque maquette pointe vers son questionnaire, chaque questionnaire
ramène à sa maquette — et les deux enchaînent vers l'écran suivant, pour dérouler les 36 sans repasser par
l'index.

**Pourquoi cette mécanique en deux temps.** Le livrable versionné reste le **Markdown** : c'est lui qui se
diffe, se relit et se commente dans Git. Mais un `.md` ouvert dans un navigateur n'est qu'un texte mort — d'où
la feuille HTML, qui n'est qu'un **moyen de le remplir confortablement**.

**Il n'y a plus de gabarit `.md` vierge**, et c'est délibéré. Depuis le 05/08/2026 la trame vit à un seul
endroit (`assets/questionnaire.js`), qui construit le formulaire *et* produit le markdown. La recopier dans
36 fichiers rejouerait la dérive constatée ce jour-là : le questionnaire d'A02 posait encore les questions de
la v2 « rôle, espace, étape » quand la maquette était passée en v3 « trois axes » depuis une semaine. Chaque
`questionnaires/<slug>.md` est donc un **talon** court, remplacé par le fichier téléchargé quand on répond.

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
questionnaire d'écran : elles engagent les 36 écrans à la fois.

## Organisation du dossier

```
maquettes/
├── index.html                    porte d'entrée — les 36 écrans par application
├── assets/systeme.css            le système de design (tokens de la charte + composants)
├── assets/questionnaire.css/.js  la feuille saisissable et son export markdown
├── <code>-<slug>.html            une page de maquette par écran
└── questionnaires/
    ├── <slug>.html               la feuille à remplir dans le navigateur
    └── <slug>.md                 le gabarit vierge — et la cible de l'export
```

Le CSS est **partagé** : une correction de token se répercute sur les 36 pages. C'est aussi ce qui garantit
qu'aucune page n'invente sa propre couleur.

## Quatre limites à connaître

1. **Les cadres sont réduits.** Un écran est dessiné à sa taille réelle puis ramené à l'échelle pour tenir
   dans la page : les **proportions et la densité sont justes**, la **taille perçue du texte ne l'est pas**.
   Pour juger une taille de texte ou une cible tactile, passer en **« taille réelle »** (bouton en haut à
   droite de chaque planche) *et* remettre le zoom du navigateur à 100 %. Le cadre représente l'**écran nu** :
   sur PC et téléphone, une barre d'adresse mangerait encore ~120 px en vrai.

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
