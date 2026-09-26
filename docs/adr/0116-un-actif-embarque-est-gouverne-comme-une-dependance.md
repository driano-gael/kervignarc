# ADR-0116 — Un actif embarqué est gouverné comme une dépendance, sans manifeste

- **Statut** : Accepté
- **Date** : 2026-09-26
- **US** : E17US005
- **Décideurs** : Organisateur (arbitrage d'actif, règle 11) / Architecte
- **Étend** : [ADR-0009](0009-gouvernance-dependances.md) — sa gouvernance visait les paquets
  installés depuis PyPI/npm ; celui-ci l'étend aux **fichiers versionnés** qu'aucun gestionnaire ne
  suit.
- **Amende** : [ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)
  — § Conséquences, « Inter n'est pas embarquée » : elle l'est désormais.

## Contexte

`DV-07` impose **Inter**. `E17US001` en a posé la pile, pas le fichier : le jour J tourne sans
internet, sur ~30 tablettes **BYOD** qui ne l'ont pas installée, et chacune retombait sur sa propre
police système (`DETTE-043`). Embarquer un fichier de police, c'est introduire au dépôt une classe
d'objets qu'ADR-0009 ne couvre pas : **pas de manifeste, pas de lockfile, pas d'audit**. Ni
`pip-audit` ni `npm audit` ne verront jamais sa version, sa provenance ou un remplacement.

Le commanditaire a tranché le 26/09/2026 entre trois options (embarquer · assumer le repli système
et corriger les planches · une police déjà présente sur le parc) : **embarquer**, avec le fichier
**officiel** tel quel plutôt qu'un sous-ensemble latin reconditionné (~50 Ko) ou un paquet npm.

## Décision

**1. Un actif embarqué se déclare comme une dépendance.** Il a sa ligne dans
[`docs/dependances.md`](../dependances.md) § « Actifs embarqués » : version, rôle, justification,
**provenance** (URL de la release officielle), **empreinte sha256**, licence. Sa licence est
versionnée **à côté du fichier**. Le mettre à jour, c'est remplacer le fichier **et** sa ligne dans
le même commit. L'ajout reste un **arbitrage** du commanditaire (règle 11), jamais de la plomberie.

**2. L'empreinte est opposable.** Sans manifeste, la ligne du registre est la seule trace de
provenance : un test la confronte au fichier (`police.test.ts`), sans quoi elle dériverait en
silence — exactement la dérive « registre ≠ réalité » que combat ADR-0009.

**3. Un actif référencé par le code vit sous `frontend/src/assets/`, pas sous `public/`.** Vite le
nomme alors par son contenu (`InterVariable-<hash>.woff2`) : un cache de tablette ne sert jamais une
version périmée après une mise à jour, et le chemin reste juste quelle que soit la base de l'appli.
`public/` reste pour ce qui doit garder une URL fixe (`favicon.svg`).

**4. Pour Inter : un fichier variable, sans `local()`, romain seul.**
- **Variable** (100–900), pas des graisses statiques : le front en emploie **cinq** (400, 500, 600,
  700, 800). Faute de la graisse exacte, CSS prend la plus proche **en dessous jusqu'à 500**,
  **au-dessus au-delà** : avec 400 et 800 seuls, les 94 usages en 600/700 seraient sortis en 800.
- **Pas de `local()`** : une Inter installée sur un poste, d'une autre version, rendrait autrement
  d'un poste à l'autre — la dispersion que l'US vient fermer.
- **Romain seul** : l'italique n'est pas embarquée (~380 Ko de plus pour trois usages :
  `.recherche-place--vide/--attente`, `.frise__note`, un `<em>` de `ReglageBigShootOff`). Le
  navigateur **synthétise** une oblique, au dessin distinct de la vraie italique d'Inter. Choix
  définitif, non une dette : l'italique est marginale dans ce produit.

**5. Le serveur épingle les types de ce qu'il sert.** Sous Windows, `mimetypes` lit le registre, qui
**écrase** sa table (`.js` en `application/javascript`, `.mjs` en `text/plain` sur le poste de dev)
et ignore `.woff2`. `monter_spa` épingle donc tous les types émis par le build : un `.js` en
`text/plain` serait refusé comme module, soit une page blanche sur toutes les tablettes.

## Conséquences

- La prochaine icône, image ou police embarquée suit ce patron : ligne au registre, empreinte,
  licence à côté, test d'empreinte. Sans le test, la ligne n'engage à rien.
- Les planches (`maquettes/assets/systeme.css`) lisent **le même fichier** par chemin relatif, sans
  copie qui dériverait ; un test vérifie qu'elles y pointent. Hors du dépôt, ou dans un navigateur
  qui refuse les polices en `file://`, elles retombent sur la police système (`maquettes/README.md`).
- **Licence** : OFL 1.1 autorise l'embarquement et la redistribution. Kervignarc est **interne,
  jamais distribué** (même raisonnement que la LGPL de `zeroconf`, ADR-0043) : `OFL.txt` reste dans
  le dépôt et n'est pas copié dans le build. À revoir si l'exécutable sortait un jour du club.
- Le poids (344 Ko, une fois par tablette puis en cache) est négligeable en réseau local.

## Porté dans le code par

- `frontend/src/index.css` — la règle `@font-face` (fichier, plage 100–900, `swap`, sans
  `local()`) et l'héritage de la police par `input`, `select`, `textarea`.
- `frontend/src/assets/fonts/` — `InterVariable.woff2` (Inter 4.1 officiel) et `OFL.txt`.
- `frontend/src/shared/police.test.ts` — les points 1 à 4 : fichier et licence présents, empreinte
  au registre, graisses employées couvertes, `swap`, aucun chargement externe (`index.html` et
  `public/` compris), planches alignées.
- `backend/api/spa.py` — `TYPES_DU_BUILD`, épinglés par `monter_spa` (point 5) ;
  `backend/tests/test_spa.py` (`test_le_build_est_servi_avec_ses_types`), sous registre hostile simulé.
- [`docs/dependances.md`](../dependances.md) — § « Actifs embarqués ».
- `.gitattributes` — `*.woff2 binary` : déclaré, jamais laissé à l'heuristique de `text=auto`.
- `maquettes/assets/systeme.css` — la même `@font-face`, par chemin relatif.
