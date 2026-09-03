# Registre des maquettes

> Inventaire des **maquettes vivantes** du projet — les canvas de design publiés, avec leur URL et
> ce qu'ils portent. C'est la **clé de récupération** : une maquette dont l'URL n'est pas ici est
> introuvable depuis un autre poste, et sera silencieusement dupliquée à la prochaine tentative de
> mise à jour.
> Règle : une maquette créée ou abandonnée s'inscrit ici **dans le même commit**. La commande
> [`/maquettes`](../.claude/commands/maquettes.md) lit ce fichier ; elle ne devine rien.

## Pourquoi un registre plutôt que la liste du compte

La liste des artifacts d'un compte est un **catalogue d'objets**, pas un enregistrement : elle mêle
tous les projets, et ne dit ni ce qu'une maquette contient, ni si elle compte encore. Les deux
maquettes du 28/07/2026 y figuraient sans interruption **et étaient perdues malgré tout** — personne
ne savait qu'elles existaient ni ce qu'on y trouvait. C'est ce constat qui a motivé ce registre.

La colonne qui fait le travail n'est donc pas l'URL, c'est **« Ce qu'elle porte »**. Une ligne qui se
contente de répéter le titre ne sauve personne.

## Maquettes vivantes

| Maquette | Ce qu'elle porte | Màj | Statut |
|---|---|---|---|
| [Coquille admin Kervignarc](https://claude.ai/code/artifact/6accb304-a33c-4945-a75b-303dde7b2a38) | Miroir fidèle de la coquille admin (axe Pilotage, accueil à 3 axes), reproduit sur les valeurs de `frontend/src/app/App.css` et les tokens de `frontend/src/index.css` — plus trois directions de navigation pour les 21 destinations de Pilotage. | 03/09/2026 | Vérifiée |
| [Kervignarc — planches de wireframes](https://claude.ai/code/artifact/d64097a9-242c-466e-a5ed-1f535a6742e6) | Vraisemblablement les 35 planches basse fidélité des trois applis, et les parcours associés. Discussion interrompue le 28/07/2026 avec trois arbitrages d'UX restés ouverts. | 28/07/2026 | ⚠️ Contenu **non vérifié** — déduit du titre, canvas jamais rouvert. À qualifier avant de s'en servir. |
| [Kervignarc — maquettes de l'appli saisie](https://claude.ai/code/artifact/d89e74ee-7bcf-47c6-b37e-e7455b53b3ae) | Vraisemblablement l'écran de saisie des flèches — la surface tactile prioritaire de la règle 10. | 28/07/2026 | ⚠️ Contenu **non vérifié** — déduit du titre, canvas jamais rouvert. À qualifier avant de s'en servir. |

## Ce que les maquettes ont fait remonter

Dessiner l'existant oblige à confronter trois sources qui, autrement, ne se parlent jamais :
[`stories/`](../stories/) (le CA), les cahiers des charges (l'intention) et le code livré. Les écarts
qui en sortent sont consignés ici jusqu'à leur traitement — ils ne s'arbitrent pas seuls
(cf. `CLAUDE.md` règle 9 : une divergence est un **défaut à remonter**).

| Écart | Constat | Origine | Suite |
|---|---|---|---|
| `D-20` non implémenté | Le CA d'E00US015 (livrée ✅) promet un écran par défaut variant selon le statut du tournoi — « brouillon→préparation, en cours→supervision, terminé→résultats ». `frontend/src/features/admin/axes.ts:163` renvoie toujours `'accueil'`, sans lire le statut. Ce qui varie est le **contenu** de l'écran `Accueil`, pas la destination. | Coquille admin, 03/09/2026 | **À trancher** : bug à ouvrir, ou CA à aligner ? |
| Largeur de la sidebar admin | `cahier-des-charges-ux.md` §7.1 annonce **240 px** ; `App.css` applique `flex: 0 0 17rem` = **272 px**. | Coquille admin, 03/09/2026 | **À trancher** : aligner la doc sur le code, ou l'inverse. |

## Maquettes retirées

*(aucune)*

> Une maquette qui ne sert plus se déplace ici avec la raison et la date, au lieu d'être supprimée de
> la table : savoir qu'un canvas a existé et pourquoi il a été abandonné évite de refaire le même.
