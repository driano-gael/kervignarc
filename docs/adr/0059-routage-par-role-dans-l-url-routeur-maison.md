# ADR-0059 — Une adresse par rôle, servie par un routeur maison

- **Statut** : Accepté
- **Date** : 2026-07-30
- **Décideurs** : Organisateur / Architecte
- **Portée** : E14US003 (adresses `/public`, `/scoreur`, `/cible`, `/admin/<tournoi>/<axe>/<destination>`)
- **Remplace** : [ADR-0032](0032-navigation-admin-par-etat-local.md) — dont il **garde** la conclusion
  sur la dépendance (routeur maison) et **renverse** celle sur les URL
- **Lie** : [ADR-0042](0042-modele-d-entree-choix-de-role-explicite.md) (les quatre portes, dont cet
  ADR prolonge la précédence), [ADR-0058](0058-decoupage-de-l-admin-en-trois-axes-d-activite.md)
  (les axes que l'adresse porte), `D-13` (verrou physique de la tablette),
  [DETTE-024](../dette.md#dette-024--routeur-maison-plutôt-quune-bibliothèque)
- **Amendé par** : [ADR-0100](0100-une-destination-d-admin-porte-l-element-qu-elle-ouvre.md) — l'adresse d'admin gagne un 4ᵉ segment, l'**élément ouvert** (E16US010). Le routeur lui-même est **inchangé** : c'est `features/admin/axes.ts` qui interprète les segments. ⚠️ Inscrit **ici** et non par un `Amende` chez ADR-0100 (qui produirait la même arête d'atlas) : c'est le lecteur du markdown brut de **cet** ADR qui doit voir l'amendement sans passer par l'atlas.

## Contexte et problème

L'application n'avait **aucune URL** : un seul point d'entrée, et le monde affiché résolu depuis le
`localStorage` (ADR-0042). [ADR-0032](0032-navigation-admin-par-etat-local.md) l'assumait — « pas de
`react-router` : le périmètre (réseau local, pas de deep-link ni d'URL partagée) ne justifie pas la
dépendance (règle 11) » — en prévoyant explicitement sa propre réévaluation « **si un vrai besoin
d'URL apparaît** ».

Le besoin est apparu, formulé par le commanditaire le 30/07/2026 :

> « je préfère de vraies URL par rôle, mais chaque branchement doit continuer à se souvenir de là où
> il est une fois branché, sauf si changement d'URL volontaire »

Trois manques concrets le motivent :

1. **`F5` perd l'écran.** La destination admin vivait dans un `useState` : un rechargement — fréquent
   sur une tablette qu'on réveille — ramenait à l'accueil.
2. **Rien n'est partageable.** Impossible d'envoyer « regarde `/admin/pilotage/supervision` » à un
   bénévole, ni d'ouvrir deux mondes dans deux onglets pour vérifier le produit.
3. **Le QR de cible était la seule adresse du produit** (`/?poste=<code>`), et elle vivait à la racine,
   sans monde nommé.

## Décision

**1. Cinq adresses, une par monde.** `/` (choix des quatre portes), `/public`, `/scoreur`, `/cible`,
`/admin/<tournoi>/<axe>/<destination>`.

**Le tournoi est dans l'adresse, pas seulement l'écran.** Corrigé en revue : la première version le
laissait en état local, si bien que `F5` restaurait l'axe et la destination mais **pas leur sujet** —
21 destinations sur 24 en dépendent, l'utilisateur retombait donc sur « choisissez un tournoi ».
Il est placé **avant** l'axe pour survivre au changement d'axe, et reconnu à sa **forme** (suite de
chiffres) : aucun axe ni aucune destination n'est numérique, la lecture est donc sans ambiguïté.

**L'adresse dit `cible`, le code dit `tablette`.** Ce n'est pas une incohérence : l'adresse est lue par
un bénévole sur l'étiquette collée devant la cible, elle doit donc parler **FFTA** (règle 3) ;
`tablette` nomme le *rôle de l'appareil* côté code. Deux publics, deux mots, une seule porte.

**2. La précédence d'entrée est étendue, pas remplacée** (fonction pure `mondeAServir`) :

| Rang | Source | Pourquoi elle prime |
|---|---|---|
| 1 | **verrou de poste** (`estPoste` / QR) | `D-13` est un contrôle d'accès **physique** : taper `/admin` ne fait pas sortir une tablette rattachée de son écran de saisie |
| 2 | **l'adresse**, si elle nomme un monde | c'est un geste explicite, au même titre qu'un tap sur une porte — sans quoi un lien envoyé à un bénévole n'ouvrirait jamais le bon écran |
| 3 | **le choix mémorisé / une session héritée** | inchangé (ADR-0042), quand l'adresse est la racine |

Quand le monde servi ne correspond pas à l'adresse, celle-ci est **corrigée en `replaceState`** — pas
`pushState` : une correction subie qu'on empilerait ferait boucler le bouton « précédent » sur une
adresse que l'application vient de refuser.

**3. Routeur maison (~110 lignes), pas de bibliothèque.**

Le commanditaire avait d'abord tranché pour `react-router-dom`. **Deux faits ont refermé l'arbitrage
le jour même** :

- **sécurité** : toutes les versions `≥ 7.12.0` tirent un `react-router` dans la plage vulnérable de
  l'avis `GHSA-qwww-vcr4-c8h2` (contournement CSRF en **mode RSC**). Le trou n'est **pas atteignable**
  ici — SPA purement cliente, servie en statique, sans React Server Components — mais la **règle 11**
  exige un `npm audit` vert, et un audit rouge qu'on ré-explique à chaque PR finit par masquer un vrai
  problème. La version corrigée (`react-router@8.3.0`) existe, mais `react-router-dom` s'arrête à 7.x ;
- **le besoin réel est petit** : cinq mondes, deux segments d'admin, aucune route imbriquée, aucune
  garde de route (les gardes sont déjà des fonctions pures testées). La règle 11 dit précisément
  « stdlib ou quelques lignes maison préférées ; en cas de doute, on n'ajoute pas ».

Le routeur est scindé en **deux fichiers volontairement asymétriques** :
`shared/navigation/routeur.ts` est **pur** (analyse et construction de chemins, correspondance
monde ↔ rôle) et porte **toutes** les décisions, donc tous les tests ;
`shared/navigation/useChemin.ts` n'est que la plomberie d'abonnement à `history`, réduite au strict
minimum. `useSyncExternalStore` y remplace le couple `useState` + `useEffect` : c'est l'API prévue
pour lire une source extérieure à React, et elle évite le défaut classique du routeur maison — un
état local qui se désynchronise du navigateur au clic sur « précédent ».

Ils vivent sous **`shared/`** et non sous `app/` : une **feature ne doit pas importer le shell**.
La première version les plaçait dans `app/`, ce qui introduisait trois imports `features/ → app/`
là où le dépôt n'en comptait aucun — inversion relevée en revue et refermée avant qu'une convention
ne s'installe.

**4. Le serveur replie les liens profonds** (`backend/api/spa.py`) : `F5` sur
`/admin/12/pilotage/supervision` demande au serveur un fichier qui n'existe pas. Le repli est
**doublement borné**, et les deux bornes attrapent des cas différents :

- **les segments du serveur** (`api`, `ws`, `health`, `docs`, `redoc`, `openapi.json`) — comparés
  **par segment** et **sans casse** : `startswith("ws")` mordrait sur une future adresse `/wsx`, et
  `/API/v1/x` (aucune route, le routage FastAPI étant sensible à la casse) recevait 200 HTML ;
- **l'intention du client** — on ne replie que si l'en-tête `Accept` demande du `text/html`, donc
  une **navigation**. C'est ce qui referme la classe entière au lieu d'allonger une liste : Vite
  copie `frontend/public/` **à la racine de `dist/`, hors `assets/`** (`favicon.svg`, `icons.svg`,
  demain un `robots.txt`), et ces fichiers-là recevaient du HTML au type MIME faux dès qu'ils
  manquaient. Les trois trous ont été trouvés en revue, pas à l'écriture.

## Alternatives écartées

- **`react-router-dom@7.11.0`** (dernière version hors plage vulnérable). Audit vert, mais sept
  versions mineures en arrière, sur un paquet que la v8 a abandonné — on prend une dépendance pour
  hériter d'une impasse.
- **`react-router@8.3.0`** (corrigé, maintenu). C'était le bon choix technique ; il n'a pas pu être
  installé sur le poste (règle de permission bloquant `npm install`), et la règle du projet interdit de
  **déclarer une dépendance fantôme** — non installée, non verrouillée. À reconsidérer à la résorption
  de DETTE-024.
- **Adresses en fragment** (`#/admin/…`). Aucun repli serveur nécessaire, donc plus sûr côté
  déploiement — mais des adresses pénibles à dicter à un bénévole et à encoder en QR, pour un repli qui
  ne coûte que cinq lignes.

## Conséquences

- **+** `F5` rend l'écran courant ; un lien s'envoie ; deux mondes s'ouvrent dans deux onglets — ce qui
  sert directement le **banc d'essai** que le commanditaire veut pour vérifier le produit.
- **+** Zéro dépendance ajoutée, `npm audit` **vert**, aucun `node_modules` de plus à auditer au jour J.
- **+** Les décisions d'aiguillage restent **pures et testées** (24 tests neufs), là où une bibliothèque
  les aurait dispersées dans des composants de routage.
- **−** On réécrit un bout de bibliothèque : pas de routes imbriquées, pas de chargement différé par
  route, pas de gardes déclaratives. **DETTE-024**.
- **⚠️ Les QR déjà imprimés** pointent vers `/?poste=<code>`. L'ancienne forme **doit continuer à
  fonctionner** — la racine porte toujours le paramètre et le verrou `D-13` force alors la tablette,
  quel que soit le chemin. Ne pas retirer ce comportement sans réimprimer les étiquettes (E09US008).

---

## Amendement du 05/08/2026 — une adresse par **porte**, plusieurs portes par monde

Cet ADR décidait « **cinq adresses, une par monde** », et son en-tête parlait des « quatre portes »
d'[ADR-0042](0042-modele-d-entree-choix-de-role-explicite.md). Les deux formulations sont devenues **fausses**
avec le lot « retours du questionnaire de maquettes ».

**Ce qui a changé.** Le commanditaire a demandé une porte de plus (`maquettes/questionnaires/a00-portes.md`,
« ce qui manque complètement ») : *« une porte pour le ou les écrans de projections »*. Or un écran de
salle **est un poste** — même code de rattachement, même jeton, même heartbeat, même révocation
(E07US004 l'avait déjà tranché). Ce qui manquait n'était donc pas un monde, c'était de
l'**orientation** : rien, à l'écran de choix, ne disait au bénévole que le vidéoprojecteur passe par
là, et il devait franchir « tablette de cible » pour rattacher un écran.

**La décision est donc élargie, pas renversée** : « une adresse par **porte** », une porte pouvant
partager son monde avec une autre. Le routeur gagne un type `Porte` (`Role | 'salle'`) à côté de
`Monde` ; `roleDeLaPorte('salle') === 'tablette'`. La précédence d'entrée de `mondeAServir` — verrou
`D-13`, puis adresse, puis choix mémorisé — est **inchangée**.

**Asymétrie assumée, et pourquoi elle est sans conséquence.** `porte → chemin` est total, mais
`chemin → monde` écrase la distinction : `construireChemin({ monde: 'tablette' })` rend toujours
`/cible`. L'app ne *reconstruit* jamais l'adresse d'un poste installé — `mondeAServir` ne pose
`corrigerUrl` que depuis la racine, ou sous verrou `D-13` avec une adresse d'un autre monde, et
`analyserChemin('/salle').monde` vaut déjà `tablette`. Un écran laissé sur `/salle` **n'y est donc
jamais réécrit**, ce que verrouille un test dédié (`routeur.test.ts`). La distinction cible/salle en
**affichage** ne vient d'ailleurs pas de l'adresse mais de `poste.type`, rendu par le serveur — seule
réponse correcte pour un écran atteint par QR, qui n'a pas d'adresse `/salle`.
