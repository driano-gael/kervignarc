# ADR-0017 — Le départ est un créneau du tournoi, pas une participation de l'archer

- **Statut** : Accepté
- **Date** : 2026-07-16
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E02-inscriptions.md`](../../stories/E02-inscriptions.md) (E02US004 : le CA
  décrivait un départ comme une **participation numérotée de l'archer**, « base de facturation » —
  sens abandonné ici) ; [`stories/E01-configuration.md`](../../stories/E01-configuration.md)
  (E01US010 : le tarif **quitte** le tournoi pour le départ) ;
  [`stories/E08-paiements.md`](../../stories/E08-paiements.md) (E08US001 : le montant dû devient une
  **somme des tarifs des départs**, non plus `tarif × nb`) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`DEPART` change de parent ; `TOURNOI.tarif_depart_centimes` retiré) ;
  [`docs/glossaire.md`](../glossaire.md) (*Départ*, *Tarif d'un départ*, *Engagé*)
- **Complète** : [ADR-0012](0012-argent-en-centimes-entiers.md) (l'argent reste en **centimes
  entiers** ; seul le **porteur** du tarif change — du tournoi vers le départ)
- **Introduit par** : E02US004 (configurer les départs d'un tournoi) ; **lie** l'US d'inscription
  archer → départs (E02US009), E08US001 (facturation), E02US006 (quotas **par créneau**), EPIC-03
  (`PLACEMENT.depart_id` désigne désormais un vrai créneau), et la résorption de
  [DETTE-001](../dette.md)

## Contexte et problème

Le mot **« départ »** portait **deux sens** dans le dépôt, jamais réconciliés :

- **Sens A — une participation individuelle numérotée de l'archer.** C'est ce que le glossaire, le
  modèle de données (`DEPART` = `archer_id + numero`), l'EPIC-02, EF-2.3 et le brief client d'origine
  encodaient. Finalité documentée : la **facturation** (`tarif × nombre de départs`). L'admin y saisit
  *combien de fois* l'archer tire ; « départ 2 » est le 2ᵉ passage **de cet archer**. C'est aussi ce
  que le CA d'E02US004 demandait mot pour mot.
- **Sens B — une session (vague) de tir partagée par toute la salle.** C'est la pratique FFTA réelle :
  un créneau horaire où le hall de 30 cibles se remplit, tire ses 60 flèches, se vide, puis se remplit
  d'une autre vague. L'archer **choisit sur quel(s) créneau(x)** il s'inscrit ; chaque créneau a son
  horaire et, éventuellement, **son propre prix**. Ce sens n'apparaissait qu'**une fois** dans tout le
  dépôt (une maquette parlant de « validations / départ (30 cibles) ») et n'était **modélisé nulle
  part** — mais `PLACEMENT.depart_id` et l'affichage « cible / position / **départ** » (EF-4.7,
  E03US001, E07US004) le préparaient déjà techniquement.

**Arbitrage métier (16/07/2026).** L'organisateur tranche pour le **sens B** : « un départ est un
créneau horaire sur un tournoi, comme si le tournoi pouvait se jouer plusieurs fois dans la même
journée ; il faut son entité `Depart`, avec un nombre de départs par tournoi sur des créneaux
horaires, et **possiblement des prix différents** ». Et, sur le porteur du prix : **chaque départ
porte son prix** (obligatoire), le tarif unique du tournoi disparaît.

Le CA d'E02US004 (sens A) est donc **périmé**, non pas ambigu — il s'écrivait sans effort et il était
faux. C'est exactement le piège de la règle 9 : un CA périmé non corrigé fait dériver l'US suivante de
tests faux. Il est réécrit ici, dans le même commit.

## Options

1. **Garder le sens A** — `DEPART(archer_id, numero)`, prix = `tarif_tournoi × nb`. Écarté : ne
   modélise aucun créneau, interdit les prix différents, et fait de `PLACEMENT.depart_id` une clé vers
   une ligne *propre à un archer* alors que le placement affecte des archers **à une même session**.
2. **Sens B, prix par défaut au tournoi + surcharge par départ.** Écarté par l'arbitrage : conserve un
   tarif au tournoi que le métier ne veut plus (« plus de tarif au niveau tournoi »).
3. **Sens B, prix obligatoire porté par chaque départ** (retenu). `DEPART` devient une entité du
   **tournoi** ; le tarif y vit ; le tournoi n'a plus de tarif propre.

## Décision

- **`DEPART` change de parent** : enfant de `TOURNOI` (`tournoi_id` **NOT NULL**), non plus d'`ARCHER`.
  Champs : `numero` (**unique par tournoi**), `horaire` (libellé de créneau, **optionnel**),
  `tarif_centimes` (**NOT NULL, ≥ 0**, centimes — ADR-0012).
- **Le prix vit sur le départ ; `TOURNOI.tarif_depart_centimes` est retiré.** E01US010 est
  retravaillé : il posait « le tarif d'un départ » sur le tournoi *faute de départs modélisés* ;
  maintenant qu'ils existent, le prix va sur eux. L'état « **non défini** » (`NULL`) que l'ADR-0012
  distinguait de « gratuit » (`0`) **disparaît** pour le tarif : on ne crée pas un départ sans prix,
  donc l'inquiétude « annoncer 0 € à une compétition dont le tarif a été oublié » n'a plus d'objet.
  `0` = gratuit reste un état valide et distinct.
- **L'archer s'inscrit sur N départs via un lien archer ↔ départ**, introduit par l'US d'inscription
  (E02US009), **pas** par celle-ci. Les colonnes `montant_du_centimes` et `paye` que le modèle v0.3
  posait sur `DEPART` **quittent** `DEPART` (elles étaient par-archer) : elles vivent sur ce lien. Le
  montant dû d'une inscription **se dérive** du `tarif_centimes` du départ (rien à recopier).
- **Facturation (E08US001)** = **somme des `tarif_centimes` des départs** auxquels l'archer est
  inscrit — non plus `tarif × nb`, puisque les prix peuvent différer.
- **Découpage en deux US** (INVEST) : **E02US004** configure les créneaux d'un tournoi (créer / éditer
  / supprimer, horaire, prix) ; **E02US009** inscrit un archer sur un ou plusieurs créneaux.

## Conséquences

- **+** Le modèle colle à la pratique FFTA. `PLACEMENT.depart_id` désigne un **vrai créneau partagé**,
  et les quotas « par départ » (E02US006) deviennent une **capacité par créneau** — ce qu'ils
  n'étaient pas quand le départ était une ligne par archer.
- **+** Prix différents par créneau possibles, tout en gardant la règle centimes (ADR-0012).
- **−** **On retravaille du livré.** E01US010 (tarif au tournoi) et son écran front sont retirés au
  profit de l'écran de configuration des départs ; migration `0016` **supprimant**
  `tournoi.tarif_depart_centimes`. Coût assumé : le projet est en pré-production (J1), aucune donnée de
  tarif réelle n'existe, et il y a précédent (migration `0015` qui **vide** `archer`).
- **−** **[DETTE-001](../dette.md) élargie** : `depart.tournoi_id` est une nouvelle FK de la
  descendance de `TOURNOI` **sans `ON DELETE`** — supprimer un tournoi non vide la violera comme les
  autres. La ligne existante est élargie (pas de contournement local).
- **−** **La définition d'« engagé » (glossaire) attend encore.** Elle devait « s'élargir aux
  départs » ; mais tant qu'il n'y a pas d'inscription archer → départ (E02US009), un départ **seul** ne
  rend personne engagé. L'élargissement se fera avec E02US009, pas ici.
- **−** **Tables `DEPART` sans consommateur monétaire avant E02US009 / E08US001** : le `tarif_centimes`
  d'un départ n'alimente une facture qu'une fois les inscriptions posées. Ce n'est **pas** une colonne
  morte pour autant — l'écran de configuration l'affiche et l'édite dès cette US (le prix d'un créneau
  est une donnée de configuration en soi, comme le barème ou le gabarit).

## Liens

[ADR-0012](0012-argent-en-centimes-entiers.md) (centimes entiers — règle inchangée, porteur du tarif
déplacé) ; [ADR-0006](0006-ubiquitous-language.md) (`Depart`, vocabulaire) ;
[ADR-0007](0007-erreurs-par-couche.md) (erreurs de domaine du départ) ;
[`docs/modele-de-donnees.md`](../modele-de-donnees.md) (`DEPART`, `TOURNOI`) ;
[`docs/glossaire.md`](../glossaire.md) (*Départ*, *Tarif d'un départ*) ; [`dette.md`](../dette.md)
(DETTE-001) ; [E08US001](../../stories/E08-paiements.md) (la facturation qui consomme le tarif) ;
EPIC-03 (`PLACEMENT.depart_id`).
