# La saisie résiste aux coupures réseau — 20 juillet 2026, 00h35

## En deux phrases

Le jour du tournoi, si une tablette perd le wifi en pleine saisie, **plus rien n'est perdu** : les
volées sont mises de côté et **renvoyées toutes seules** dès que le réseau revient. Et un petit voyant
dit en permanence si tout passe bien, si on est coupé, ou si un rattrapage est en cours.

## Le problème qu'on a réglé

Un gymnase, ce n'est pas un réseau parfait : une borne wifi saturée, une tablette qui s'éloigne, et la
connexion saute deux ou trois secondes. Jusqu'ici, une volée saisie pile à ce moment-là **échouait** —
le marqueur voyait une erreur et se retrouvait bloqué, avec le risque de perdre le score ou de le
retaper.

Or **un score perdu en silence est la pire des choses** dans une compétition. Il fallait que la
tablette encaisse ces micro-coupures sans que le bénévole ait à s'en occuper.

## Ce qui change concrètement

- **On peut saisir même hors-ligne.** Si le réseau est coupé, la volée n'échoue plus : elle s'affiche
  comme saisie, marquée **« en attente d'envoi »**, et le marqueur **continue** sa cible normalement.
- **Le rattrapage est automatique.** Dès que la connexion revient, les volées en attente **repartent
  toutes seules**, dans l'ordre. Aucun bouton à presser.
- **Aucun doublon.** Même si une volée était partie juste avant la coupure, elle n'est pas enregistrée
  deux fois : le serveur reconnaît qu'il s'agit du même geste.
- **Ça survit à la fermeture de l'onglet.** Si la tablette se met en veille ou qu'on ferme l'onglet
  avant que le réseau revienne, les saisies en attente sont **toujours là** à la réouverture.
- **Un voyant clair, en permanence** (en haut à droite) : **« En ligne »** (tout va bien),
  **« Hors ligne · 2 saisies en attente »** (coupé, avec le nombre de volées en attente), ou
  **« Synchronisation… »** (le rattrapage est en cours).

Un point à savoir, normal et voulu : tant qu'on est hors-ligne, le **total** d'un archer ne bouge pas.
C'est logique — un total ne compte que les volées **validées par le scoreur**, et une volée en attente
ne l'est pas encore.

## Ce qui existait déjà (et qu'on a simplement branché)

La **diffusion en direct** — le fait qu'un score validé apparaisse tout seul sur le classement public
et les autres écrans en une à deux secondes — **fonctionnait déjà** grâce aux fondations posées plus
tôt. On s'est contenté de le vérifier ; il n'y avait rien à reconstruire.

## Pour les curieux

La décision de conception (comment on détecte une coupure, où on range les saisies en attente, comment
on évite les doublons) est consignée dans une note d'architecture dédiée. Le comportement est aussi
décrit pas à pas, façon mode d'emploi, dans la fiche de test fonctionnel de cette fonctionnalité.
