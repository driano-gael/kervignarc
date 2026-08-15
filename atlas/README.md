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
cd backend && python -m atlas
```

Stdlib pure, aucune dépendance — c'est ce que prouve le job de CI, qui tourne sans `pip install`.

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

Il ne dit **pas** si une règle est encore d'actualité — c'est indécidable mécaniquement. La page
« Écarts constatés » affiche des **signaux à vérifier**, jamais un verdict. Et le contrôle de
portage vérifie qu'un fichier **existe**, pas qu'il **fait** ce que l'ADR promet.

## Vérifier le rendu après une modification

Le site n'a ni build, ni typage, ni test de rendu (`DETTE-065`). Ce qui est vérifié
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
- **Les décisions** — les 83 ADR, filtrables, plus les chaînes d'amendement.
- **Une décision** (`adr.html?id=0075`) — son voisinage et l'état réel de ce qu'elle promet.
- **Ce qui a changé** — l'errata, du plus récent au plus ancien.
- **Écarts constatés** — là où l'écrit et le code ont divergé.
- **Rechercher** — balayage direct du corpus, expressions exactes comprises.
