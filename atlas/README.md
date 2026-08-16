# L'atlas — le dépôt cartographié

Un site statique qui répond à une question : **qu'est-ce qui fait règle aujourd'hui, depuis quand,
et est-ce encore tenu ?**

## L'ouvrir

Double-clic sur [`index.html`](index.html). Rien d'autre — pas de serveur, pas de build, pas de
dépendance. Les données sont servies en `.js` (et non en `.json`) précisément pour que `file://`
fonctionne : sur ce protocole, `fetch()` est bloqué par la politique d'origine des navigateurs.

Un serveur local marche aussi, si tu préfères : `python -m http.server 8000` depuis ce dossier.

## Le régénérer

```bash
cd backend && python -m atlas              # génère
cd backend && python -m atlas --verifier   # ne rien écrire, juste dire si c'est à jour
```

Stdlib pure, aucune dépendance — c'est ce que prouve le job de CI, qui tourne sans `pip install`.
La génération **exige git** : sans lui, l'histoire des règles ne peut pas être reconstituée, et un
atlas amputé de son histoire serait pire qu'une génération refusée.

`--verifier` a quatre issues, et elles sont toutes des états distincts :

| Code | Ce qu'il dit |
|---|---|
| `0` | à jour |
| `1` | **données périmées** — régénère |
| `2` | source invalide — **git absent**, fichier source manquant, ADR illisible, libellé de relation inconnu, en-tête de tracker illisible, table de suivi mal formée |
| `3` | **écart bloquant** — un ADR nomme un module qui n'existe pas, ou deux livrables de suivi se contredisent |

⚠️ **Après un commit qui déplace des lignes de `CLAUDE.md`, régénère et commite à nouveau.**
L'histoire d'une règle vient d'un `git log -L <bornes>` résolu contre `HEAD` : au moment du hook,
le commit n'existe pas encore, et le hook valide du périmé contre du périmé. Seule la CI le voit.

## Ce qui est généré, ce qui ne l'est pas

| Dossier | Statut |
|---|---|
| `donnees/*.js` | **Généré.** Ne jamais éditer à la main : la CI régénère et compare, toute retouche est écrasée puis rejetée. |
| `*.html`, `statique/*` | Écrits à la main. |

L'atlas **n'a aucune autorité** : il lit `CLAUDE.md` et `docs/adr/`, il ne les remplace pas. Chaque
page nomme sa source. Le supprimer ne perdrait aucune information — c'est ce qui le distingue du
wiki externe rejeté par [ADR-0001](../docs/adr/0001-adopter-les-adr.md), et ce qui justifie qu'il
existe malgré cette décision.

## Ce qu'il sait — et ce qu'il ne saura jamais

Il **calcule** ce que le registre ne dit pas : quelles décisions ont été amendées depuis, et si les
modules qu'un ADR déclare porter sa décision existent encore.

Il **recalcule** aussi les compteurs du tracker au lieu de les recopier — c'est ce qui a trouvé, le jour de sa livraison, un compteur de jalon faux et deux US livrées qui n'apparaissaient dans aucun tableau compté.

Il **confronte** enfin les règles d'architecture au code : le sens des dépendances entre couches est
lu à l'AST et **fait rougir la porte** s'il est enfreint — jusqu'à `E00US020`, seul le domaine était
surveillé, les quatre autres sens ne l'étaient par rien.

Il ne dit **pas** si une règle est encore d'actualité — c'est indécidable mécaniquement. La page
« Écarts constatés » affiche des **signaux à vérifier**, jamais un verdict. Et le contrôle de
portage vérifie qu'un fichier **existe**, pas qu'il **fait** ce que l'ADR promet.

## Vérifier le rendu après une modification

Le site n'a ni build, ni typage, ni test de rendu (`DETTE-067`, dont le seuil de résorption — 2 000 lignes — est à ~20 lignes). Ce qui est vérifié
mécaniquement — absence de `fetch()`, de module ES, de ressource externe, présence du `viewport`,
tableaux dans un conteneur défilant — l'est par `backend/tests/test_atlas_site.py`. Le reste se
regarde à l'œil :

1. **Ouvrir `index.html` en double-clic** (`file://`, sans serveur). Console navigateur **vide**,
   onglet Réseau **vide** : c'est le contrôle qui valide toute l'architecture du site.
2. Trois largeurs — **360 × 640**, 768 × 1024 (le matériel réel du projet), 1440 × 900.
3. À chaque largeur : aucun défilement **horizontal**, aucun texte tronqué, cibles tactiles
   confortables, tableaux et schémas défilant dans leur propre conteneur.
4. Les deux thèmes : le navigateur suit `prefers-color-scheme`, le sombre est le défaut.

## Les pages

- **Le règlement** — les 29 règles en vigueur, dans l'ordre où elles sont écrites.
- **Une règle** (`regle.html?id=…`) — son texte du jour, puis son histoire datée.
- **Les décisions** — tous les ADR du registre, filtrables, plus les groupes liés par amendement.
- **Une décision** (`adr.html?id=0075`) — son voisinage et l'état réel de ce qu'elle promet.
- **L'avancement** — les US par section, l'ordre des epics, la dette ouverte. Les compteurs y
  sont **recalculés**, jamais recopiés.
- **Une US** (`us.html?id=E05US026`) — ce que les quatre livrables de suivi disent d'elle.
- **La carte du code** — la matrice de dépendances entre couches et paquets, l'inventaire des ports
  et de leurs adapters, le graphe des features du front. Le backend y est lu à l'**AST** (exact,
  donc bloquant) ; le front à l'**expression régulière** (heuristique, donc signalé).
- **Ce qui a changé** — l'errata, du plus récent au plus ancien.
- **Écarts constatés** — là où l'écrit et le code ont divergé.
- **Rechercher** — balayage direct du corpus, expressions exactes comprises.
