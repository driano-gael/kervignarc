# ADR-0018 — Supprimer un départ à inscriptions : confirmable, effets monétaires déportés

- **Statut** : Accepté
- **Date** : 2026-07-16
- **Décideurs** : Organisateur / Architecte
- **Introduit par** : E02US009 (inscrire un archer sur des départs) — l'US qui **fait naître** le
  lien archer ↔ départ, donc le garde-fou « supprimer un départ qui porte des inscriptions »
- **Complète** : [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) (même famille :
  *signaler et confirmer* plutôt que *refuser*) ; [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md)
  (le départ est un créneau du tournoi ; le lien archer ↔ départ et son `paye` naissent en E02US009)
- **Amende** : [`stories/E02-inscriptions.md`](../../stories/E02-inscriptions.md) (E02US009 : le garde-fou
  est **confirmable**, ses effets de bord sont déportés) ; crée deux US dérivées —
  [`stories/E08-paiements.md`](../../stories/E08-paiements.md) (E08US005, remboursement) et
  [`stories/E12-pilotage-jour-j.md`](../../stories/E12-pilotage-jour-j.md) (E12US008, cycle de vie du départ)

## Contexte et problème

E02US009 pose la table de liaison **archer ↔ départ** (une *inscription*, portant `paye`). Dès qu'elle
existe, supprimer un **départ** (créneau) devient dangereux : les inscriptions de ce créneau — dont
certaines peuvent être marquées **payées** — disparaîtraient avec lui.

Le CA d'E02US009 renvoyait, pour ce garde-fou, à « patron `ClubReference` / `ArcherEngage` » — **deux
patrons opposés** :

- **`ClubReference`** (E02US001) — **refus définitif** (409) : un club référencé par un archer n'est
  pas supprimable ; il faut d'abord dénouer les références. C'est le patron d'un **référentiel global**
  partagé entre tournois, qu'on ne détruit pas à la légère.
- **`ArcherEngage`** (E02US003, [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)) —
  **signalement confirmable** (409) : supprimer un archer qui a tiré est annoncé (le message énumère ce
  qui sera détruit) et l'admin confirme ; la suppression **cascade** sur les scores.

Impossible d'écrire le test depuis un CA qui cite les deux : le comportement attendu diffère
matériellement (blocage permanent vs cascade confirmée). C'est le signal, prévu par la règle 9, d'un CA
**ambigu** — arbitré ici plutôt que deviné.

L'organisateur a par ailleurs soulevé deux effets de bord de la suppression confirmée : le
**remboursement** des inscriptions déjà payées, et le cas d'un départ **déjà lancé** (créneau en cours
ou joué). Consigne : les traiter dans l'US si réalisable, **sinon US dédiée**.

## Décision

1. **Confirmable** (patron `ArcherEngage`, non `ClubReference`). Supprimer un départ à inscriptions
   lève `DepartAvecInscriptions` (**409 `depart_avec_inscriptions`**), franchissable en rejouant
   l'appel avec `autoriser_suppression_inscrits=true` (paramètre de requête sur le `DELETE`, comme
   `autoriser_suppression_engage` — un `DELETE` n'a pas de corps, cf. ADR-0016). La suppression
   confirmée **cascade** sur les inscriptions du créneau (cascade **applicative maîtrisée**, dans la
   transaction de l'adapter — [DETTE-001](../dette.md), jamais `ON DELETE`).

   *Pourquoi confirmable et non refus dur :* un créneau est une **configuration locale du tournoi**,
   comme un archer — pas un référentiel global comme le club. Un créneau annulé (trop peu d'inscrits,
   changement d'horaire) doit pouvoir être retiré sans désinscrire manuellement chaque archer. La note
   d'E02US004 pointait déjà vers « patron E02US003 ».

2. **Le message énumère les inscriptions détruites, dont le nombre de payées.** L'effet de bord
   monétaire est rendu **visible au point de décision** (« 12 inscriptions dont 4 déjà payées seront
   effacées »), sur le modèle d'`ArcherEngage` qui énumère les flèches. C'est le « prévoir l'effet de
   bord » **réalisable** dans cette US.

3. **Remboursement déporté en US dédiée ([E08US005](../../stories/E08-paiements.md)).** Aujourd'hui
   `paye` est un **booléen** (payé oui / non) : il n'existe **aucun mouvement d'argent** (ni registre de
   transactions, ni encaissement, ni remboursement). Un remboursement est une fonctionnalité de
   **paiement** (EPIC-08), pas d'inscription. E02US009 ne peut donc que *signaler* les payées, pas les
   rembourser.

4. **Cas « départ déjà lancé » déporté en US dédiée ([E12US008](../../stories/E12-pilotage-jour-j.md)).**
   Un `Depart` n'a **aucun état de cycle de vie** ni lien départ → scores : `horaire` est un libellé
   libre, le placement (EPIC-03) et le déroulé (Q4) n'existent pas. **Rien dans les données ne dit
   qu'un créneau est lancé.** Poser ce garde-fou exigerait de modéliser le cycle de vie du départ —
   c'est du pilotage jour J (EPIC-12). On **ne pose pas un garde-fou sur un état qui n'existe pas** :
   ce serait un contrôle qu'aucun chemin réel ne déclenche, l'anti-patron déjà écarté pour `club_id`
   (E02US001) et pour le placement (E02US003).

## Conséquences

- **+** Cohérent avec la doctrine du projet (ADR-0015/0016) : *signaler et confirmer*, ne pas refuser.
  Un seul patron destructeur-confirmable à maintenir côté front (détection `code` + rejeu avec drapeau).
- **+** L'effet monétaire n'est pas silencieux : l'admin voit combien de payées il détruit avant de
  confirmer, même sans système de remboursement.
- **−** **[DETTE-007](../dette.md) s'applique à ce nouveau chemin.** Le décompte du message
  (inscriptions, dont payées) est **cru sur parole** au rejeu : entre le 409 et la confirmation,
  d'autres tablettes peuvent inscrire ou marquer payé. La confirmation reste aveugle, exactement comme
  pour l'archer engagé. La ligne DETTE-007 est **élargie** (pas de contournement local).
- **−** **[DETTE-001](../dette.md) élargie** : la table `inscription` ajoute deux FK sans `ON DELETE`
  (`archer_id`, `depart_id`), toutes deux dans la descendance de `tournoi`. La cascade applicative
  `archer → inscription` (suppression d'archer) et `depart → inscription` (suppression de départ) sont
  posées ici ; la cascade **depuis le tournoi** reste, elle, ouverte.
- **−** Deux US de plus au backlog (E08US005, E12US008). Assumé : chacune est un vrai geste métier
  distinct, plus simple isolée que bâclée ici (le forfait/suppression d'E02US003 a montré que confondre
  deux besoins en rend un faux).

## Liens

[ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) (confirmation d'une suppression
destructrice) ; [ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) (drapeau booléen, forme
du signalement) ; [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) (le départ, le lien archer ↔
départ) ; [`docs/dette.md`](../dette.md) (DETTE-001, DETTE-007) ;
[E08US005](../../stories/E08-paiements.md), [E12US008](../../stories/E12-pilotage-jour-j.md) (US dérivées).
