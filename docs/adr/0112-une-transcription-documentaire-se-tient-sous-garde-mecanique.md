# ADR-0112 — Une transcription documentaire inévitable se tient **sous garde mécanique**

- **Statut** : Accepté
- **Date** : 2026-09-23
- **US** : E17US010
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0102](0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) — la documentation porte des
    pointeurs, pas des copies : ce qui vient d'ailleurs **se cite en une ligne, avec un lien**,
    jamais recopié. Le présent ADR en pose
    l'**exception bornée**, pour le cas où la citation est techniquement impossible
  - [ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) — les maquettes **font foi** : elles sont relues en
    séance et arbitrées, donc leur péremption coûte des décisions fausses
  - [ADR-0099](0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md) — un commentaire est le seul
    artefact que **rien ne vérifie** ; c'est exactement ce statut qu'on retire ici à une copie

> ⚠️ **Cet ADR ne figure PAS à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md).**
> C'est une convention **documentaire et d'outillage**, comme `0099` et `0102` : il ne décide rien
> du moteur sportif, de la portée, ni d'une politique injectable. Il porte tout de même sa section
> « Porté dans le code par », parce qu'il nomme un contrôle exécutable — un ADR d'outillage dont
> personne ne peut vérifier qu'il est tenu retombe au rang d'intention.

## Contexte

[ADR-0102 §1](0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) est clair : un fait qui vit ailleurs
**se cite en une ligne avec un lien, jamais ne se recopie**. La règle suppose que citer soit
possible. Elle ne l'est pas toujours.

`maquettes/` est un dossier de pages HTML statiques, ouvertes directement dans un navigateur, sans
bundler ni étape de build — c'est ce qui permet de corriger une planche **en séance**, devant le
commanditaire. Un fichier de ce dossier ne peut donc pas `import` un module TypeScript du produit.
La navigation des trois axes d'administration y est **recopiée à la main** dans
`maquettes/assets/appareils.js`, depuis `frontend/src/features/admin/axes.ts`.

Cette copie s'est périmée en silence. Mesuré à l'ouverture d'`E17US010` : **quatre** destinations
livrées absentes des maquettes (`identite`, `archer`, `pret-demarrer`, `audit`), **une** fantôme
(`doublons`, retirée du produit par `E16US010`) et **quatre** libellés périmés — soit **cinq US**
de dérive accumulée. Deux de ces libellés avaient été renommés par `E16US002` *précisément parce
qu'ils portaient chacun le nom de l'autre* : la maquette continuait d'enseigner la confusion que le
produit venait de corriger.

Le coût n'est pas cosmétique. ADR-0074 a décidé que **les maquettes font foi** : on les relit
planche par planche et on en tire des arbitrages. Une planche périmée produit une décision sur une
application qui n'existe plus.

## Décision

**Quand une copie documentaire d'un fait du code est techniquement inévitable, elle n'est admise
que si un contrôle de CI la compare à sa source.** Sans ce contrôle, la règle d'ADR-0102 §1
s'applique sans exception : on cite, on ne recopie pas.

Quatre points fixent la forme du contrôle.

### 1. Le sens de lecture : la source s'**importe**, la copie se **parse**

Le contrôle importe la source produit (`AXE_PAR_DESTINATION`) et ne parse que la copie. La source
est donc lue par le compilateur, jamais par une expression régulière : **un seul des deux côtés
peut mentir sur sa propre forme**.

C'est ce qui a écarté le patron des garde-fous existants du dépôt. `test_domain_isolation.py` et
`test_portee_sportive.py` sont en Python ; un troisième du même genre aurait dû parser `axes.ts`
*et* `appareils.js` — deux parseurs fragiles au lieu d'un. Le contrôle vit donc côté front.

### 2. Le parseur échoue **fermé**

Toute ligne qui *ressemble* à une entrée et que le motif strict ne sait pas lire est **signalée**,
jamais jetée. Sans cette règle, le contrôle échoue ouvert : une entrée écrite dans une forme
inattendue disparaît de la comparaison au lieu de la faire rougir.

⚠️ **Ce n'est pas une précaution théorique.** Dans la rédaction initiale d'`E17US010`, un simple
commentaire de fin de ligne — `['doublons', 'Doublons'], // à retirer un jour` — suffisait à
escamoter le fantôme exact que l'US venait de retirer, la suite restant verte. Démontré par
sabotage en revue, sur le fichier réel.

### 3. L'asymétrie : la copie peut devancer le produit, jamais retarder sur lui

Une planche **en avance** sur le produit est légitime — on maquette avant de livrer. Une
destination **livrée** qu'aucune planche ne montre ne l'est pas : c'est la dérive qui fait relire
du périmé. Le premier sens se déclare et passe ; le second reste rouge **sans échappatoire**.

### 4. L'échappatoire est nominative, justifiée, locale et **périssable**

La déclaration s'écrit `// PLANCHE-A-VENIR: <id> — <pourquoi>`. Quatre bornes, chacune fermant un
contournement mesuré en revue :

- **nominative** — elle ne dispense qu'un identifiant, jamais un ensemble ;
- **justifiée** — la raison est exigée par le motif lui-même : une échappatoire gratuite se pose
  sans y penser ;
- **locale** — reçue dans un bloc ouvert seulement, sur la ligne qu'elle dispense. Posée dans la
  bannière du fichier, elle couvrait une entrée trois cents lignes plus bas ;
- **périssable** — le jour où la destination est livrée, la déclaration **rougit**. C'est le point
  qui la distingue d'un `skip` oublié : sans lui, le commentaire affirmerait « aucune route
  produit » indéfiniment après que la route existe, et rien ne le dirait — le mode de panne
  qu'ADR-0099 décrit.

**Voie préférée** : ne pas inscrire du tout l'écran non livré dans la table. `appareils.js` le rend
alors « non livrée », en pointillés, mécanisme qui préexiste à cet ADR. `PLANCHE-A-VENIR` n'est
réservé qu'au cas où l'entrée de barre latérale doit elle-même figurer.

## Conséquences

- La copie cesse d'être un artefact que rien ne vérifie. C'est le statut qu'ADR-0099 réserve aux
  commentaires, et la raison pour laquelle il les borne : ici on ne borne pas, on **vérifie**.
- Le contrôle ne couvre que ce qu'il dit couvrir. Les **libellés**, l'**ordre** et les `data-ecran`
  des planches restent transcrits à la main — inscrits en `DETTE-110`, avec leur remède. Un
  garde-fou qui se croit plus large qu'il n'est éteint la vigilance : c'est pourquoi le périmètre
  exact est écrit dans `appareils.js`, dans `maquettes/README.md` et au registre.
- **Un second candidat existe et n'est pas couvert** : `maquettes/assets/systeme.css` « transcrit la
  charte mesurée du CDC design §3.3 » (ADR-0074, `maquettes/README.md`). Le critère de cet ADR lui
  est applicable ; aucun contrôle ne le tient à ce jour. C'est écrit ici plutôt que taire, pour ne pas
  reproduire le défaut d'ADR-0017 — un ADR dont on croit qu'il est porté partout alors qu'il ne
  l'est qu'à un endroit.
- Le contrôle est exécuté par `npm test`, donc par la porte mécanique et par la CI (job `frontend`,
  bloquant). Le dossier `maquettes/` n'est pas dans le périmètre de prettier ni d'eslint, donc
  aucun outil ne reformate le fichier dans le dos du parseur.

## Porté dans le code par

- `frontend/src/maquettes-navigation.test.ts` — le contrôle lui-même : import de la source, parseur
  qui échoue fermé, asymétrie, et les quatre bornes de l'échappatoire. Sa seconde suite éprouve le
  garde-fou sur une source factice, chaque détection ayant été vue rouge.
- `maquettes/assets/appareils.js` — la copie tenue sous garde (table `DESTINATIONS`), et l'en-tête
  qui énonce le périmètre exact du contrôle.
- `frontend/src/features/admin/axes.ts` — la source, `AXE_PAR_DESTINATION`.
- `maquettes/README.md` — la règle rendue au lecteur du dossier de maquettes.

⚠️ **Non porté** : `maquettes/assets/systeme.css` (cf. Conséquences) et les attributs `data-ecran`
des planches — nommés pour que leur absence soit lue comme un trou connu, pas comme un oubli.
