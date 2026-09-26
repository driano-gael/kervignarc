# ADR-0115 — L'import des inscrits est un plan pur, écrit en une transaction ; la licence identifie la fiche

- **Statut** : Accepté
- **Date** : 2026-09-26
- **US** : E02US007
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) et
  [ADR-0015](0015-signaler-un-doublon-plutot-que-l-interdire.md) — leur « alternative écartée »
  commune, le n° de licence, **arrive** : les deux ADR nommaient E02US007 comme point de réouverture.

## Contexte

Deux exports réels sont versés dans `docs/sources/import inscription/`, et ils ne se ressemblent
pas : **Ianseo** (CSV `;`, sans en-tête, Latin-1) porte l'identité complète de l'archer ;
**Résult'Arc** (`.xls` OLE2) ne porte **ni nom ni prénom** — licence, sexe, arme, n° de départ,
paiement, cible, trispot. Aucun des deux ne porte de catégorie exploitable, ni de quoi créer un
départ (horaire et tarif, obligatoires depuis E02US010).

Trois contraintes pèsent sur la forme :

1. **« Aucun import partiel silencieux »** (CA « rapport »). Or chaque méthode de repository ouvre sa
   session et commite seule : enchaîner `ServiceArchers.ajouter` puis `ServiceInscriptions.inscrire`
   ligne à ligne ferait 2 × N transactions, et un import coupé à la ligne 50 laisserait 49 archers.
2. **Le quota d'un départ n'a aucun filet SQL** (E02US006) : un import qui écrit sans le recompter le
   franchit en silence.
3. **ADR-0015** : un import écrit en masse, sans personne pour confirmer ; poser
   `autoriser_homonyme` pour tout le fichier désarmerait le signalement.

## Décision

### 1. Un plan pur, calculé deux fois

Le domaine (`domain/import_inscrits.py`) décide de chaque ligne sur un **instantané** du tournoi :
`CREER` (fiche + inscription), `INSCRIRE` (fiche déjà désignée par la licence), `HOMONYME`,
`REJETEE` + motif. L'ordre du fichier compte : une ligne voit les fiches créées et les places prises
par les précédentes — c'est ce qui re-contrôle le quota (contrainte 2), via `Depart.est_complet`,
règle désormais partagée avec `ServiceInscriptions.inscrire` plutôt que dupliquée.

L'**aperçu** calcule le plan et le rend. La **confirmation** redépose le fichier et **recalcule** le
plan dans la même commande de la file d'écriture (règle 7) : rien n'est gardé côté serveur entre les
deux appels, et l'état écrit est celui du moment, pas celui de l'aperçu.

### 2. Une transaction pour tout le fichier

`ImportInscritsRepositorySQL.appliquer` écrit clubs, fiches et inscriptions dans **une** session et
commite une fois (patron de `fusionner` et de la cascade d'E01US026). Il ne revérifie rien : le plan
a été calculé dans la même commande sérialisée. Une erreur en cours de route annule tout.

### 3. La licence identifie la fiche dans le tournoi

- `Archer.licence` : **facultative** (la raison d'ADR-0014 tient toujours au guichet), normalisée
  (espaces retirés, majuscules, `[A-Z0-9]{1,12}`).
- **Une fiche par licence dans le tournoi** (arbitrage du commanditaire, 26/09/2026) : un licencié
  qui tire aux départs 1 et 2 est une fiche et deux inscriptions. À l'import, une licence connue
  **inscrit la fiche existante** ; au guichet, créer ou éditer une fiche vers une licence déjà prise
  est refusé (`409 licence_deja_prise`, **refus**, aucun drapeau). Une licence déjà inscrite **sur
  ce départ** est une ligne rejetée.
- **Deux licences connues et différentes ne sont jamais des homonymes** (ADR-0015 amendé) : le
  signalement, la détection de doublons (E02US005) et la fusion la consultent. Une seule licence
  connue ne décide rien : la question reste posée. Deux fiches de licences différentes ne se
  fusionnent pas ; une fusion vers une fiche sans licence lui transmet celle de l'absorbée.
- Filet en base : index **partiel** `UNIQUE(tournoi_id, licence) WHERE licence IS NOT NULL`
  (migration `0058`) — un `UNIQUE` plein refuserait deux archers sans licence.

### 4. Les homonymes sont collectés, pas tranchés

Une ligne homonyme n'est pas écrite ; le rapport la présente, et l'admin **coche** celles qu'il
confirme (`?homonymes=` à la confirmation). C'est la réponse qu'ADR-0015 attendait : ni tout refuser,
ni tout accepter.

### 5. Deux sources, reconnues au contenu

Un adapter par source (`infrastructure/import_inscrits/`), aiguillés par la **signature binaire**
(OLE2 → Résult'Arc, sinon CSV Ianseo). Résult'Arc ne crée personne : il inscrit la fiche que sa
licence désigne, et une licence inconnue est rejetée avec un motif qui renvoie à l'export Ianseo.
Paiement, cible et trispot sont lus mais **non repris** — le rapport les nomme.

### 6. Catégorie déduite, sinon rejet

Sexe + tranche d'âge + arme, contre les catégories **du tournoi** ; une contrainte absente de la
catégorie accepte tout. Zéro ou plusieurs candidates : ligne rejetée, candidates nommées.
⚠️ **Interprétation** : « l'âge atteint dans l'année civile de la licence » (référentiel §2) est lu
comme l'année de **fin** de saison (un tournoi du 15/11/2026 compte l'âge atteint en 2027), la
licence FFTA portant ce millésime. Non vérifié sur un texte réglementaire : à confirmer.

## Conséquences

- **+** Aucun import partiel : un fichier s'écrit en entier ou pas du tout, et le rapport dit ligne
  à ligne pourquoi une ligne n'est pas partie.
- **+** Le doublon devient **décidable** dès que les deux fiches portent une licence.
- **−** `xlrd` entre au manifeste (règle 11, `docs/dependances.md`), et son fichier réel ne s'ouvre
  qu'avec `ignore_workbook_corruption=True` : la table OLE2 que Résult'Arc écrit est mal formée.
  Un Résult'Arc d'une autre version pourrait différer — seul un vrai fichier le dira.
- **−** La licence est **servie publiquement** : `GET /tournois/{id}/archers` est une lecture ouverte
  et son DTO la porte désormais. Assumé — le n° de licence figure sur les feuilles de résultats
  FFTA —, mais c'est une donnée personnelle de plus sur le LAN.
- **−** Le plan est recalculé à la confirmation : si un inscrit a été ajouté entre l'aperçu et la
  confirmation, le rapport final peut différer de l'aperçu. C'est voulu (on écrit l'état réel), et
  c'est le rapport **final** que l'écran affiche.
- **−** Le rapprochement **entre tournois** par licence, qu'ADR-0015 évoquait, n'est pas fait : la
  licence n'est unique que dans un tournoi.

## Porté dans le code par

- `backend/domain/import_inscrits.py` — `planifier_import`, `tranche_age`, décisions et motifs.
- `backend/domain/archer.py` — `Archer.licence`, `normaliser_licence`, `licences_distinctes`.
- `backend/domain/depart.py` — `Depart.est_complet`, partagé avec `application/inscriptions.py`.
- `backend/domain/doublons.py` — une paire de licences distinctes n'est pas rapprochée.
- `backend/application/archers.py` — `LicenceDejaPrise` au guichet, homonymie et fusion.
- `backend/application/import_inscrits.py` — aperçu, confirmation, instantané du tournoi.
- `backend/infrastructure/import_inscrits/` — lecteurs Ianseo et Résult'Arc, aiguillage.
- `backend/infrastructure/db/repositories/import_inscrits.py` — écriture en une transaction.
- `backend/migrations/versions/0058_archer_licence.py` — colonne et index partiel.
- `backend/api/v1/import_inscrits.py` — les deux routes ; `api/corps.py` — lecture bornée.
