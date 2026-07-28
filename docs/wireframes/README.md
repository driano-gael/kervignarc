# Planches de wireframes — document de travail

> **Statut : brouillon en cours de discussion. Ne fait autorité sur rien.**
> Ce dossier n'est **pas** du cadrage : il n'engage ni le CDC UX, ni les stories, ni les US front.
> Tant que cette ligne est là, une divergence entre ces planches et
> [`cahier-des-charges-ux.md`](../../cahier-des-charges-ux.md) se tranche **en faveur du CDC**.

## Ce que c'est

`planches-3-applis.html` — 35 planches de wireframes **basse fidélité** couvrant les trois applications
(admin `/admin`, saisie `/saisie`, publique `/`), plus les parcours utilisateur de chacune et la liste des
questions à trancher.

Produit le 28/07/2026 à partir du **CDC UX §6 à §8** : chaque planche renvoie aux décisions `D-nn`, aux
principes `P-n` et aux questions ouvertes `Q-UXn` qui la justifient. Les écrans ne sont pas inventés, ils
sont **dérivés** de décisions déjà prises.

## Pourquoi c'est ici et pas discuté

Le travail a été interrompu avant la revue des parcours. Il est versionné pour **survivre au poste** (le
suivi se fait sur GitHub, la mémoire locale de l'assistant ne voyage pas d'une machine à l'autre) — pas
parce qu'il serait validé. La branche `docs/wireframes-3-applis` est **parquée, sans PR**.

## Comment le lire

- **En ligne** : https://claude.ai/code/artifact/d64097a9-242c-466e-a5ed-1f535a6742e6 (page privée)
- **En local** : ouvrir le `.html` dans un navigateur.

⚠️ Le fichier est un **fragment HTML** (pas de `<!doctype>`, `<html>` ni `<head>`) : c'est le format attendu
par le support de publication, qui fournit l'enveloppe. Il s'ouvre correctement en local malgré tout.
Pour republier une version modifiée **au même lien**, republier ce fichier en passant l'URL ci-dessus —
sans quoi un nouveau lien est créé et l'ancien reste figé.

## Reprise — où on s'était arrêtés

Rien n'a encore été relu par le commanditaire. Trois points sont sortis de l'exercice et attendent un
arbitrage (détail en fin de document, section « À trancher ensemble ») :

| Réf. | Question | Enjeu |
|---|---|---|
| `Q-UX2` | Scannabilité des affectations sur l'écran de salle | 200 archers ne tiennent pas à l'écran ; qui rate son nom attend un cycle entier. Vue la plus utile du produit, mécanisme non résolu. |
| `Q-UX8` | Geste central du placement (glisser-déposer *vs* sélectionner-puis-affecter) | Ce ne sont pas deux habillages du même écran, ce sont deux écrans. Le CDC le note « non instruit ». |
| `Q-UX3` | La validation par le scoreur vaut-elle double marque (FFTA B.6.1.1) ? | À confirmer par un arbitre. Si non, c'est tout le rôle du scoreur qui est à repenser. |

Deux réserves à ne pas perdre de vue à la reprise :

1. La mention « écran existant » sur une planche signale qu'un composant du **même rôle** vit dans
   `frontend/src/features/` — elle ne dit **rien** de la ressemblance entre l'écran livré et le wireframe.
   Confronter les deux reste à faire.
2. Les contraintes de placement affichées en planche A11 (même club sur cibles différentes, mixité des
   catégories) sont une **hypothèse**, pas une lecture du référentiel FFTA. À vérifier avant usage.

## Si ce document est un jour validé

Il devient une référence de conception à laquelle les US front se rattachent, au même titre que le CDC UX —
et cette page perd son bandeau de brouillon. Ce passage se fait par une décision explicite, pas par
l'usage : un brouillon qu'on se met à citer sans l'avoir validé est une source de vérité fantôme.
