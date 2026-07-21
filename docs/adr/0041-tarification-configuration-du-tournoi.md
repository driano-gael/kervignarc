# ADR-0041 — La tarification est une configuration du tournoi, pas du code

- **Statut** : Accepté *(organisateur, 21/07/2026 — sujet de facturation = unité facturée, joueur ou club)*
- **Date** : 2026-07-21
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`cahier-des-charges.md`](../../cahier-des-charges.md) (M8 —
  le montant dû n'est plus « somme des tarifs des départs » en dur mais **le résultat d'une politique
  de tarification** ; le tarif peut porter sur l'archer *ou* le club) ; [`stories/E01-configuration.md`](../../stories/E01-configuration.md)
  (E01US010 — note « tarif par départ » = **stratégie par défaut**, pas la seule) ;
  [`stories/E08-paiements.md`](../../stories/E08-paiements.md) (E08US001 — le dû est *lu*, pas figé ;
  E08US002 — **incarne** la stratégie par défaut : elle re-dérive le dû, le paiement est un booléen par
  créneau) ; nouvelles US d'évolution **E01US020** et **E01US021**.
- **Introduit par** : E08US002 (suivi des paiements) — le besoin a **émergé en cadrant l'US** : pour
  suivre un encaissement il faut un « dû », et l'organisateur a précisé le 21/07/2026 que ce dû doit
  pouvoir se calculer de plusieurs façons selon le tournoi.
- **S'appuie sur** : [ADR-0004](0004-moteur-de-phases-politiques.md) (les politiques du moteur sont
  **injectables** — la tarification en devient une, au même titre que `scoring`/`seeding`) ;
  [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) (le tarif est porté par le **départ**, d'où
  « somme des tarifs » comme stratégie par défaut) ; [ADR-0028](0028-epreuves-par-equipes-participant.md) /
  E13US001 (**abstraction participant** — le « sujet de facturation » archer|club en est un cas).

## Contexte et problème

E08US001 (livrée) calcule le montant dû d'un archer comme la **somme des tarifs des départs** auxquels
il est inscrit. En cadrant E08US002 (suivi des paiements), l'organisateur a indiqué le 21/07/2026 que
ce modèle n'est **qu'un cas** : selon le type de tournoi, la facturation peut être portée par un
**archer** ou par un **club**, avec éventuellement un **dégressif** (par départ pour un archer, par
nombre d'archers pour un club), en **pourcentage** ou en **montant** saisi.

Point important : l'organisateur **n'a pas de liste concrète** de ces modèles. La demande est
explicitement de **rester ouvert** au besoin — pas de livrer un catalogue de tarifs aujourd'hui.

Deux règles du projet se tendent ici :

- **Règle 2** — « un format de tournoi est de la **configuration**, pas du code ». La tarification a
  bien vocation à rejoindre les politiques injectables : le *comment on calcule le dû* est un point
  d'injection choisi par la configuration du tournoi, pas une cascade de `if` dans le service.
- **Règle 9 (remède structurel)** — un pattern s'introduit sur **preuve dans le code d'aujourd'hui**
  (3ᵉ occurrence réelle), **jamais sur une évolution supposée**. Or il n'existe **qu'un** modèle de
  prix en code, et les autres sont **anticipés**, pas actuels.

Écrire tout de suite le moteur de tarification (sujet archer|club, dégressif, config par tournoi)
serait la **généralité spéculative** que la règle 9 interdit. Ne rien décider laisserait E08US002 se
figer sur « dû = somme des tarifs de l'archer » et rendrait l'ouverture coûteuse plus tard. Cet ADR
tranche **la direction** sans écrire le moteur.

## Décision

**1. La tarification est une propriété de configuration du tournoi.** À terme, *comment se calcule le
montant dû* est une **politique injectable** (règle 2, [ADR-0004](0004-moteur-de-phases-politiques.md)),
choisie à la création/configuration du tournoi — au même rang que `scoring` ou `seeding`. Un tournoi
porte sa **stratégie de tarification** ; le service de paiement **lit** un dû, il ne le code pas.

**2. Le sujet de facturation est configuré par tournoi : `archer` ou `club`.** « Celui qui doit
l'argent » est un choix de configuration. Le cas **`club`** — le club est l'unité facturée, pas
seulement le payeur groupé de ses archers — s'appuie sur le **référentiel club** ([ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md),
`club_id`), et **non** sur l'abstraction `Participant` d'[ADR-0028](0028-epreuves-par-equipes-participant.md).
« Sujet de facturation » (qui **doit l'argent**) et « participant » (qui **tire** dans un match, archer
ou équipe) sont deux abstractions **distinctes** : un club n'est pas une équipe, et facturer un club ne
requiert **rien** de la machinerie équipes/E13 — le rattachement `club_id` existant suffit. *(La 1ʳᵉ
rédaction de cet ADR les avait conflés, créant une fausse dépendance à E13US001 — corrigé le 21/07/2026.)*

**3. L'option dégressive est un paramètre de configuration, non un cas codé.** Case à cocher à la
configuration, avec **pourcentage** *ou* **montant** ; appliquée **par départ** (sujet archer) ou **par
palier de nombre d'archers** (sujet club). C'est une **stratégie de tarification** de plus, pas une
branche dans le service.

**4. Un seul modèle est implémenté aujourd'hui, et le déclencheur d'implémentation est explicite.** La
stratégie par défaut — **somme des tarifs des départs de l'archer** (E08US001, sujet `archer`, sans
dégressif) — reste **la seule codée**. On n'introduit la politique injectable et une 2ᵉ stratégie
**que lorsqu'un tournoi réel la demande** (règle 9). D'ici là, la direction vit dans cet ADR et dans
les US d'évolution, pas dans du code en attente.

**5. E08US002 incarne la stratégie par défaut ; elle ne s'en découple pas.** *(Précisé le 21/07/2026
après confrontation au code livré par la session parallèle — la 1ʳᵉ rédaction annonçait à tort un
découplage.)* Le suivi des paiements **re-dérive** le dû lui-même — `domain/paiement.py` somme les
tarifs des créneaux (`recapituler`) — au lieu de lire `montant_du_par_archer` (E08US001). C'est donc
une **2ᵉ occurrence** du calcul « somme des tarifs », **admise par la règle 9** (« dupliquer une 2ᵉ
fois, attendre le 3ᵉ cas »), pas une séparation de responsabilités. Le fait de paiement stocké est le
**booléen `paye` par créneau** ; payé et reste sont **dérivés**, aucun montant réglé n'est saisi.
**Conséquence pour E01US020** : introduire la politique de tarification devra rediriger **les deux**
sites qui calculent aujourd'hui le dû (`montant_du_par_archer` **et** `recapituler`) — ce n'est pas un
simple branchement.

## Conséquences

- **+** L'**ouverture demandée est acquise et documentée** (règle 2 satisfaite en *direction*) sans
  écrire une ligne de moteur spéculatif (règle 9 respectée). Le jour où le 2ᵉ modèle arrive, la
  direction est déjà pensée — mais pas « clés en main » : il faudra rediriger les **deux** sites qui
  calculent le dû aujourd'hui vers la politique (cf. Décision 5), pas seulement en brancher un.
- **+** **E08US002 est livrable maintenant** sur la réalité archer, sans attendre la tarification
  riche.
- **−** Quand un 2ᵉ modèle deviendra réel, il faudra **à la fois** introduire la politique injectable
  `PolitiqueTarification` **et**, pour le sujet `club`, l'abstraction du sujet de facturation — donc un
  **rework assumé** de E08US001/E08US002 (« dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » est la
  réponse admise). Le coût est **reporté**, pas supprimé.
- **−** Le sujet `club` s'appuie sur le **référentiel club** (ADR-0014), **déjà livré** : il **ne dépend
  pas** d'E13/des équipes (cf. Décision 2 — ne pas confondre facturation et participation).
- **−** La stratégie par défaut « somme des tarifs » est désormais **codée en double**
  (`montant_du_par_archer` + `recapituler`) : 2ᵉ occurrence admise (règle 9), mais dette latente que le
  passage à la politique injectable devra résorber en réunifiant les deux sites.
- **Hors périmètre de cet ADR** : le **détail** des barèmes (forfait club, formules de dégressif),
  l'**écran de configuration** de la tarification, et le **remboursement** d'une inscription payée
  annulée ([E08US005](../../stories/E08-paiements.md)) — chacun porté par son US le moment venu.
