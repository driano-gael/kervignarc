# ADR-0036 — Idempotence de la saisie par identifiant de saisie (registre en mémoire, borné)

- **Statut** : Accepté
- **Date** : 2026-07-19
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US002, CA
  « enregistrement » ex-005 et bloc « Arbitrages »). N'amende pas la dette (aucun raccourci assumé :
  la volatilité est un **choix** cohérent avec le modèle de session, pas un emprunt).
- **Introduit par** : E04US002 (saisie de qualification — tranche exposition PR2b).
- **S'appuie sur** : [ADR-0005](0005-file-d-ecriture-sqlite-writer-unique.md) (writer unique — la
  **sérialisation** des écritures, dont ce registre tire son atomicité), [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md)
  et [ADR-0034](0034-poste-selectionne-son-depart-courant.md) (états de session **en mémoire,
  volatils** — même parti retenu ici).

## Contexte et problème

Le CA « enregistrement » (ex-005) exige qu'**un rejeu réseau ne crée pas une volée en double** : la
tablette peut renvoyer une écriture dont l'accusé de réception s'est perdu (coupure, reconnexion),
et E04US009 rejouera même une **file hors-ligne** entière à la reconnexion.

La saisie ordinaire d'une volée est *déjà* idempotente par nature — la persistance fait un **upsert**
par clé métier `(série, numéro)` (E04US002 PR2a), rejouer la même volée la réécrit à l'identique,
sans doublon. Mais les actes **tracés** ne le sont pas : une **validation** rejouée écrirait une
**seconde entrée d'audit** (le journal E10US005 est en ajout seul), une **correction** rejouée
réappliquerait le geste et empilerait une trace de plus. Il faut donc une déduplication explicite,
au-delà de l'upsert.

Le CA mentionnait « ADR-0005 » comme source de cette idempotence : c'est **faux** (acté dans la
story). ADR-0005 ne traite que la **sérialisation** single-writer, pas la déduplication d'une
requête rejouée. Le mécanisme est donc **introuit ici**, sans antériorité.

## Décision

**1. Le client fournit un identifiant de saisie ; la commande de la file dédoublonne dessus.** Chaque
écriture de volée (saisie, validation, correction) porte un **identifiant opaque** généré côté
client (un par geste utilisateur). Un `RegistreIdempotence` mémorise `identifiant → résultat` : un
premier passage exécute l'acte et mémorise son résultat ; tout rejeu du même identifiant **renvoie ce
résultat sans ré-exécuter**. Absence d'identifiant (`None`/vide) = pas de déduplication.

**2. La déduplication est consultée DANS la commande de la file** (writer unique, ADR-0005), pas au
bord HTTP. C'est ce qui rend le contrôle « déjà vu ? » et l'écriture **atomiques** : deux rejeux
concurrents ne peuvent pas manquer tous deux le cache et s'exécuter en double, puisque le writer les
**sérialise**. Marqueur `# E04US002 : idempotence` à l'endroit exact de la déduplication.

**3. Registre en mémoire, borné (LRU), volatil.** Aucune table, aucune persistance : un
dictionnaire borné (~2048 identifiants, éviction LRU) protégé par un verrou. Un **redémarrage
serveur oublie les identifiants** — sans conséquence, la fenêtre de rejeu (ACK perdu, reconnexion)
tient dans une exécution. Ce choix **aligne** l'idempotence sur le reste du modèle de session du
projet : le jeton de poste (ADR-0029) et le départ courant (ADR-0034) sont eux aussi en mémoire et
volatils. Simplicité assumée hors domaine (règle 12) : mono-club, réseau local.

## Alternatives écartées

- **Table de déduplication persistée** (identifiant → résultat en base). Survivrait au redémarrage,
  mais ajoute une écriture à **chaque** saisie (à rebours de la brièveté des transactions, règle 7),
  une migration, et le stockage d'un résultat d'agrégat non trivial — pour un gain nul en
  exploitation (le redémarrage serveur le jour J est l'exception, et la reprise se refait au geste).
  Sur-ingénierie pour le contexte mono-club local.
- **S'appuyer sur la seule idempotence de l'upsert.** Suffit pour la saisie ordinaire, mais **laisse
  fuir** le doublon d'audit sur validation/correction rejouées — précisément le cas que le CA vise.
- **Clé d'idempotence au bord HTTP** (avant la file). Simple à écrire, mais le contrôle et l'écriture
  ne seraient plus atomiques : deux rejeux concurrents pourraient franchir le cache ensemble.

## Conséquences

- **+** Un rejeu réseau (ou la reprise d'une file hors-ligne, E04US009) ne crée ni volée en double,
  ni trace d'audit fantôme. Le mécanisme est **réutilisable** tel quel par le writer WebSocket
  d'E04US009 et l'orchestrateur d'E12US002 (mêmes commandes en file).
- **+** Aucune migration, aucun coût d'écriture supplémentaire, aucune dette : le mécanisme naît
  simple et cohérent avec les sessions existantes.
- **−** L'idempotence ne survit pas à un redémarrage serveur. Accepté (fenêtre de rejeu courte) et
  **signalé**, pas contourné ; réversible vers une table si un besoin réel émergeait (E04US009).
- **−** Le registre garde en mémoire une référence au résultat de chaque saisie récente (borné LRU) :
  la borne est le garde-fou, dimensionnée bien au-dessus du volume d'un tournoi.
