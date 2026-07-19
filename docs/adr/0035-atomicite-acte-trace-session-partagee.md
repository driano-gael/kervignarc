# ADR-0035 — Atomicité acte↔trace : co-écriture score + audit dans une session partagée

- **Statut** : Accepté
- **Date** : 2026-07-19
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US002) ;
  précise l'usage du socle d'audit posé par [`stories/E10-acces-roles.md`](../../stories/E10-acces-roles.md)
  (E10US005). N'amende pas la dette (la couture est introduite, pas contournée).
- **Introduit par** : E04US002 (saisie de qualification — tranche backend).
- **S'appuie sur** : socle d'audit E10US005 (`ServiceAudit.consigner`, port `AuditRepository`,
  `ActionAuditee.VALIDATION`/`CORRECTION_SCORE`), règle 7 (SQLite single-writer, file d'écriture,
  transactions courtes), le patron `ArcherRepositorySQL.supprimer` (plusieurs écritures, un commit).

## Contexte et problème

Deux actes d'E04US002 doivent **laisser une trace** dans le journal d'audit métier (E10US005) :
- la **validation** d'une volée/série (qui, quand — `ActionAuditee.VALIDATION`) ;
- la **correction** d'un score verrouillé (qui, quand, avant→après — `ActionAuditee.CORRECTION_SCORE`).

La revue adversariale d'E10US005 a remonté le risque : `ServiceAudit.consigner` **commit dans sa
propre session** (`AuditRepositorySQL.consigner` : `with session_factory() as s: s.add(...); s.commit()`).
Être « dans la même commande de la file du writer unique » (règle 7) garantit qu'aucune **autre**
écriture ne s'intercale — mais **pas** que l'acte et sa trace tiennent dans la **même transaction**.
Deux commits successifs (le score, puis la trace) laissent une fenêtre : si le second échoue, on a un
score validé **non tracé** — ou, dans l'autre ordre, une **trace fantôme** sans acte. Pour un journal
qui « tient lieu de signature » de la feuille de marque (FFTA B.6.1.1), une validation non tracée ou
une trace sans acte est un défaut de fond, pas cosmétique.

Trois options (posées dans la story E04US002) : (a) ordonner les deux commits et **assumer** la
fenêtre en dette ; (b) rendre la trace *best-effort* (log si elle échoue) ; (c) **co-localiser** les
deux écritures dans **une seule transaction**.

## Décision

**Option (c) : une couture de session partagée.** L'écriture de l'acte de score et la consignation de
sa trace se font dans **une seule session, un seul `commit`** — donc **tout ou rien**.

**1. Le port d'audit accepte une session fournie.** `AuditRepository.consigner` gagne la capacité
d'écrire dans une session **existante** au lieu d'en ouvrir une : soit un paramètre optionnel
`session`, soit une méthode dédiée `consigner_dans(session, entree)`. Sans session fournie, le
comportement historique (session propre + commit) est préservé — les appels existants d'E10US005 ne
changent pas.

**2. La face applicative est `SerieRepository.enregistrer_avec_trace(serie, entree)`.** L'entrée
d'audit est **construite et datée par le service applicatif** (`ServiceSaisie`, via le port `Horloge`
— comme `ServiceAudit` le fait en E10US005, jamais par le domaine ni la base) : elle arrive **déjà
prête** au port. Le repository de saisie ne **construit ni ne date** rien ; dans un unique
`with session_factory() as session:` il (i) écrit/verrouille la volée ou réécrit le score corrigé,
(ii) écrit l'`EntreeAudit` reçue dans **la même** session (via `AuditRepository.consigner_dans`, §1),
(iii) fait **un seul** `session.commit()`. C'est le patron `ArcherRepositorySQL.supprimer` (plusieurs
écritures, un commit) étendu à **deux préoccupations** (score + audit) au lieu d'une cascade
intra-table. *(La construction/datation reste ainsi au service — un adapter qui relirait la `Horloge`
serait une double lecture d'horloge.)*

**3. La trace est datée par la `Horloge` au niveau du service, jamais par le domaine ni la base.**
`avant`/`apres`
valent `None` pour une `VALIDATION` (elle ne porte pas d'avant/après) et portent les valeurs
verbatim pour une `CORRECTION_SCORE` — **`None`, jamais `""`** (le socle conserve verbatim ; `""` est
distinct de `NULL` à la relecture).

## Conséquences

- **+** Zéro écriture déchirée : une validation sans trace, ou une trace sans acte, devient
  **impossible** — la contrainte d'intégrité que le journal-signature exige.
- **+** La couture est réutilisable : tout futur acte devant être tracé atomiquement (forfait —
  E12US004, remboursement…) passera par le même patron « écriture + `consigner_dans(session, …)` ».
- **+** Rétrocompatible : le chemin « session propre » de `consigner` reste, les consignations
  autonomes d'E10US005 ne bougent pas.
- **−** Le journal d'audit **cesse d'être totalement découplé** de l'écrivain métier : un repository
  de score connaît désormais le socle d'audit. C'est un couplage **assumé et localisé** (la couture),
  préféré à une fenêtre d'incohérence. La règle 7 (transactions courtes) tient : les deux écritures
  sont brèves et sans logique métier longue dans la transaction.
- **−** `consigner_dans(session, …)` **ne commit pas** : l'appelant est responsable du commit unique.
  Mal utilisée (oubli du commit, ou commit intermédiaire), elle romprait l'atomicité — d'où sa
  réservation aux repositories de co-écriture, testée explicitement (acte **et** trace, ou **ni l'un
  ni l'autre**, sur injection d'échec).
