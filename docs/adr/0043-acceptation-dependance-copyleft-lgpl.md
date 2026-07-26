# ADR-0043 — Acceptation d'une dépendance copyleft (LGPL) : `zeroconf`

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`docs/dependances.md`](../dependances.md) (ajout de `zeroconf`, entête licences) ;
  [`stories/E11-exploitation.md`](../../stories/E11-exploitation.md) (E11US001 — CA « procédure réseau »).
- **Introduit par** : E11US001 (release, base & mise en réseau).
- **Réfs** : [ADR-0009](0009-gouvernance-dependances.md) (gouvernance des dépendances, §2 licences),
  [ADR-0002](0002-stack-et-topologie.md) (topologie LAN, packaging PyInstaller).

## Contexte et problème

E11US001 doit rendre le serveur joignable par un **nom mémorisable** — `kervignarc.local` — sur le
réseau local du jour J, sans configurer le routeur. C'est du **mDNS** (« Bonjour »/Avahi). La seule
bibliothèque Python mûre et adoptée pour publier un service mDNS est **`python-zeroconf`**. Or elle
est distribuée sous **LGPL-2.1**, une licence **copyleft faible**.

[ADR-0009](0009-gouvernance-dependances.md) §2 exige des licences **permissives** (MIT/BSD/Apache/ISC)
et pose que tout **copyleft** doit être **validé explicitement**. `zeroconf` est la **première**
dépendance copyleft du projet : ce choix crée un **précédent de gouvernance** qui sera opposé aux
suivants — d'où cet ADR, malgré le seuil bas (le projet acte déjà en ADR des choix mineurs).

Réécrire le mDNS à la main a été **écarté** : multicast UDP sur `224.0.0.251:5353` + encodage des
enregistrements DNS (A, PTR, SRV, TXT) + gestion des collisions de nom — non trivial, et à maintenir,
pour une fonction de **confort** (l'accès par IP reste le chemin de référence). Règle 11 (parcimonie)
ne tranche pas ici en faveur du « maison » : la lib fait gagner un vrai risque d'implémentation.

## Décision

**1. On accepte `zeroconf` (LGPL-2.1) comme dépendance runtime.** La LGPL n'impose d'obligation qu'en
cas de **distribution** d'un binaire liant la bibliothèque **en refusant à l'utilisateur le
re-link** vers une version modifiée. Kervignarc est un outil **interne mono-club**, **jamais diffusé
publiquement** : aucune distribution au sens de la LGPL n'a lieu. Aucune modification de `zeroconf`
n'est faite (simple `import`). L'obligation copyleft est donc **sans objet en pratique**.

**2. La règle générale reste « permissif par défaut ».** Cet ADR **n'ouvre pas** la porte au copyleft
en général : il tranche **un cas nommé**, sur le critère « outil interne non distribué ». Toute
future dépendance copyleft repasse par la même validation explicite (ADR-0009 §2) — et un copyleft
**fort** (GPL/AGPL) en runtime resterait à réexaminer, la contamination n'y étant pas neutralisée par
l'absence de distribution de la même façon.

**3. Condition de réexamen.** **Si** un jour le binaire était diffusé hors du club (autre club,
mise à disposition publique), cette décision est **caduque** et doit être rejugée : il faudrait alors
soit se conformer à la LGPL (permettre le re-link, p. ex. via un mode d'emploi de reconstruction),
soit remplacer `zeroconf`.

*(Note connexe, hors périmètre de cet ADR : `pyinstaller` est en **GPL-2.0-with-exception** ; son
exception autorise explicitement les binaires produits sous **toute** licence, et c'est un **outil de
build** jamais lié au runtime — aucune contamination. Documenté dans `docs/dependances.md`.)*

## Conséquences

- **Positif** : `kervignarc.local` fonctionne sans configuration réseau ; pas de code mDNS maison à
  maintenir ; la décision et ses limites sont tracées pour les prochains arbitrages de licence.
- **Négatif / vigilance** : le projet n'est plus « 100 % permissif » — l'entête de
  `docs/dependances.md` le signale. La condition de réexamen (§3) doit être **relue avant** toute
  diffusion externe du binaire ; c'est un point de contrôle facile à oublier.
- **Neutre** : `zeroconf` tire `ifaddr` (transitif, MIT), figé par le lockfile.
