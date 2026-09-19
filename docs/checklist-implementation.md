# Checklist d'implémentation

Les défauts que `/revue-us` trouve **le plus souvent**, transformés en questions à se poser
**pendant** qu'on code — et non après, quand une revue les relève.

> **D'où elle vient.** Dépouillement des **152 corps de commit de correction de revue** de `main`
> (19/09/2026, 433 Ko). Chaque case correspond à une famille observée **au moins 12 fois**. Ce n'est
> pas une liste de bonnes pratiques : c'est la liste de ce qui est réellement passé au travers ici.
>
> **Comment s'en servir.** À lire **au début** d'une US, pas à la fin. Une case n'est cochable que
> par une vérification faite — `grep`, test rejoué, fichier ouvert — jamais par intention.
> Cf. [ADR-0110](adr/0110-la-porte-mecanique-tient-dans-un-script-et-deux-etages.md) pour la porte
> qui l'accompagne.

## Avant de coder

- [ ] **Périmètre** — Si l'US a une **surface utilisateur**, j'ai reformulé ce qu'elle livre et
      demandé si c'est bien tout le périmètre voulu. Un CA clair mais **trop étroit** ne déclenche
      aucun garde-fou.
- [ ] **CA** — J'ai lu la puce **CA** de `stories/` (pas `docs/fonctionnel/`, qui est un *produit*
      de l'US). Si je n'arrive pas à en écrire le test, le CA est ambigu : je questionne, je ne
      devine pas.
- [ ] **Prérequis** — `grep` dans `docs/adr/` : un ADR impose-t-il une US préalable ?
- [ ] **Dette** — `grep DETTE-` sur les fichiers que je vais toucher. *(34 commits : une dette
      existante gagnait un site sans que la ligne du tableau l'enregistre.)*

## Pendant que je code

- [ ] **Code mort** — Chaque symbole, champ, paramètre et branche JSX que j'ajoute a un appelant
      **de production**, prouvé par `grep`. *(29 commits — dont un réglage central monté sous une
      condition toujours fausse.)*
- [ ] **Jumeau** — Ce raisonnement, **combien de sites le portent ?** J'ai listé les appelants et
      traité **tous** ceux qui remontent, jumeau front compris. *(26 commits.)*
- [ ] **Conjonction** — Si le diff touche back **et** front : qui émet l'événement, qui le consomme,
      qui rafraîchit ? Aucun relecteur mono-couche ne verra le trou. *(14 commits.)*
- [ ] **Typage** — Pas de paramètre à défaut qui laisse un champ s'oublier en silence ; pas de
      `Record` non exhaustif ; `assert` → garde typée (404, jamais 500). *(21 commits.)*
- [ ] **Vocabulaire** — Terme métier neuf : vérifié au glossaire qu'il n'est pas déjà pris par la
      FFTA. Libellés exposés **en clair**, jamais la valeur brute d'un énuméré. *(19 commits.)*
- [ ] **État React** — L'état est-il indexé sur un `id` que SQLite **réattribue** ? Le composant
      survit-il à un remontage, un double-clic, un refetch en échec ? *(24 commits.)*
- [ ] **Tactile & a11y** — Boutons répétés distinguables au lecteur d'écran ; cibles utilisables au
      doigt (règle 10). *(20 commits.)*
- [ ] **Perf** — Pas de lecture par archer dans une boucle ; rien de long sur le thread du writer
      unique (règle 7). *(15 commits.)*

## Tests

- [ ] **Ordre** — Domaine et service : test écrit **depuis le CA, avant** le code. API, repository,
      câblage : après.
- [ ] **Sabotage** — Chaque test neuf, je l'ai **vu rouge** en cassant le code. Un test qui n'a
      jamais échoué ne garde rien. *(31 commits de tests placebo.)*
- [ ] **Couverture des chemins** — Pour chaque chemin que le diff ajoute, je peux nommer
      `fichier::test` qui le traverse **de bout en bout** — pas une doublure qui court-circuite la
      sérialisation. *(42 commits.)*
- [ ] **Migration** — Aller-retour `upgrade`/`downgrade` réellement joué si je l'annonce réversible.
      *(12 commits.)*

## Ce que j'écris autour du code

- [ ] **Affirmations** — Chaque phrase que j'écris **ou que je laisse en place** (commentaire,
      docstring, ADR, CA, registre, tracker) est relue **contre le code d'aujourd'hui**, et chaque
      chiffre annoncé est re-`grep`é. ⚠️ **Famille n° 1 : 58 commits.**
- [ ] **ADR** — Si le diff touche la *Décision* ou les *Conséquences* d'un ADR, j'ai réécrit
      « Porté dans le code par » en **ouvrant chaque module cité**, pas en le déduisant. *(25
      commits — le défaut a survécu treize mois sur ADR-0017.)*
- [ ] **Arbitrage** — Tout arbitrage tranché en cours d'US est reversé dans la **puce CA** de
      `stories/`, **dans le même commit**. *(22 commits.)*
- [ ] **Garde-fou** — Si j'en écris un : qu'est-ce qu'il **ne** couvre **pas** ? Je l'ai fait
      échouer exprès. Un garde-fou qui promet plus qu'il ne tient est pire que pas de garde-fou.
- [ ] **Suivi** — US à surface visible : `SUIVI-US.md` **et** `00-resume-projet.md` **et** le
      fichier daté, dans le commit de l'US. *(21 commits.)*
- [ ] **Fiche fonctionnelle** — `docs/fonctionnel/<ExxUSyyy>.md` décrit ce qui **existe** et est
      **exécutable** par un non-technicien. *(20 commits.)*

## Avant de dire « prêt »

- [ ] **Le diff entier, d'un bloc** — `git diff main...HEAD` relu en une fois. C'est l'angle de
      `revue-axe-c1`, le seul qui attrape les défauts de conjonction, et je code par morceaux.
- [ ] **Porte complète** — `python porte.py`, **jamais pendant la revue** : les deux se disputent
      les 4 cœurs, et c'est ce qui a produit la seule porte à 40 minutes du registre.

## Quand je corrige une revue

*(14 commits imputent un défaut à leur **propre correctif** précédent — cette section est la plus
rentable du fichier.)*

- [ ] **La classe, pas le cas** — Mon correctif ferme-t-il le cas signalé, ou la **classe** de
      défauts ? *(13 commits : « le trou a été déplacé, pas fermé ».)*
- [ ] **Test du correctif** — Chaque correctif porte son test. Sans lui, il est supprimable sans
      rien casser.
- [ ] **Phrases de clôture** — ⚠️ Les majeurs de 2ᵉ passe se logent dans les phrases où l'auteur
      **déclare le problème résolu** (« sans effet de bord », « les autres sources sont à jour »).
      Ces phrases-là se vérifient comme du code.
- [ ] **Outils de masse** — Un `sed` ou un script sur N fichiers abîme de la prose que **rien ne
      vérifie**. Relire le diff produit, pas seulement le compte de remplacements.
