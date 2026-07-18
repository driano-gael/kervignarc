# ADR-0030 — Saisie de score autorisée au poste de cible, bornée par le lieu (403 hors-cible)

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E10-acces-roles.md`](../../stories/E10-acces-roles.md) (E10US007, bloc
  « Arbitrages tranchés »). N'amende **pas** le glossaire (« saisie » vs « validation » y sont déjà
  définis, E04US001/E10US003) ni la dette (aucun raccourci assumé).
- **Introduit par** : E10US007 (poste de cible : saisir sans s'identifier).
- **S'appuie sur** : [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) (le jeton de
  poste, `exiger_poste` **prêt** qui renvoie le `Poste` servi), [ADR-0025](0025-mode-d-identite-scoreur-par-code-individuel.md)
  (élargir l'autorisation d'une écriture au-delà de l'admin, sans route parallèle),
  [ADR-0007](0007-erreurs-par-couche.md) (erreurs typées, mapping HTTP à la **seule** frontière API).

## Contexte et problème

E10US001 a fermé **en intérim** toutes les écritures derrière `exiger_admin`, faute des autres modes
d'identité. E10US007 réalise la promesse annoncée en fin d'ADR-0029 : **élargir la saisie de score au
jeton de poste** (le *lieu*, `D-13`) — un **marqueur** saisit sans compte ni code — tout en garantissant
qu'« un poste ne saisit que pour **SA** cible ». Aujourd'hui une seule surface de saisie existe : le
`POST /api/v1/archers/{archer_id}/scores` de la tranche verticale (E00US011). E04US002 (grille de
saisie par volée) et la **validation** (scoreur seul) restent à venir.

Trois choix que le CA ne tranche pas seul (arbitrés le 18/07/2026, doute **technique** — tranché,
documenté, signalé après coup) :

1. **Comment autoriser « admin OU poste »** sans ouvrir de route parallèle ni casser le garde-fou
   `test_acces_public` (« toute écriture sans session → 401 ») ?
2. **Où vit le contrôle « SA cible »** — à l'API (comme `exiger_poste`) ou dans le service ?
3. **Quel statut HTTP** pour un poste **valide** qui vise la **mauvaise** cible ?

## Décision

**1. Une dépendance combinée `autoriser_saisie(request) -> Poste | None`.** Elle renvoie `None` si une
session **admin** est valide (l'admin saisit sans contrainte), le `Poste` si un **jeton de poste**
(`X-Jeton-Poste`) est valide, et lève `NonAuthentifie` (→ 401) sinon. On **élargit** l'endpoint
existant (on remplace `dependencies=[Depends(exiger_admin)]` par la valeur rendue par
`autoriser_saisie`) plutôt que d'ajouter une route « poste » distincte — même principe qu'ADR-0025
(élargissement endpoint par endpoint, l'admin reste autorisé). L'admin est essayé **en premier** :
mode le plus large, purement en mémoire, alors que résoudre un poste **relit la base** (statut du
tournoi, ADR-0029). C'est le **premier** endpoint du projet qui exploite la **valeur** rendue par sa
dépendance ; d'où la forme `Annotated[Poste | None, Depends(autoriser_saisie)]` (et non un défaut
`= Depends(...)`, qui déclencherait un faux positif B008).

**2. Le contrôle « SA cible » vit dans le SERVICE, pas à l'API.** `ServiceArchers.saisir_score` gagne
un paramètre `poste_autorise: Poste | None` ; quand il est fourni, le service lève `SaisieHorsCible`
si l'archer visé n'est pas placé sur `(poste.tournoi_id, poste.cible_index)`. **Divergence assumée
avec ADR-0029**, qui envisageait la garde « sur `exiger_poste` » (donc à l'API) : la vérifier à l'API
imposerait une **lecture séparée** de l'archer *avant* de soumettre l'écriture, ouvrant une fenêtre de
course (l'archer replacé entre le contrôle et l'écriture). Dans le service, le contrôle et l'écriture
tiennent dans la **même commande de la file du writer unique** (règle 7) — atomique, sans course. Le
service reçoit un `Poste` (type **domaine** : aucune violation de couche, il n'apprend rien de HTTP) ;
l'API se borne à décider *s'il* passe un poste. L'existence de l'archer se vérifie **avant** sa cible
(un archer inconnu rend 404, pas 403).

**3. « SA cible » = même tournoi ET même index — d'où un contrôle sur le couple, pas sur l'index seul.**
Plusieurs tournois tournent **en concurrence** (intérieur + extérieur, ADR-0029) et les numéros de
cible **se répètent** d'un tournoi à l'autre : comparer le seul `cible_index` laisserait le poste
« cible 4 » d'un tournoi voisin saisir pour la cible 4 d'ici. Le `tournoi_id` fait partie de
l'invariant. Un archer **non placé** (`cible is None`) n'est sur aucune cible : `None != cible_index`
le refuse naturellement (seul l'admin saisit hors placement).

**4. Nouveau statut : 403 (`SaisieHorsCible`), le premier du projet.** Un jeton de poste valide sur la
mauvaise cible est **authentifié mais interdit pour cette ressource** : ni 401 (aucune session) ni 409
(conflit d'état). Le mapping (`api/erreurs.py`, seule frontière autorisée à traduire en HTTP, ADR-0007)
gagne une branche 403 ; la table d'ADR-0007 passe de « 401/404/409 » à « 401/403/404/409 ». Côté front
(E04US002), cela distingue proprement « re-rattacher le poste » (401) de « ce n'est pas ta cible » (403).

## Conséquences

- **+** E04US002 (saisie par volée) **hérite du patron** : elle réutilisera `autoriser_saisie` pour la
  saisie, et la **validation** acceptera admin **ou** scoreur (jamais le poste — « un poste saisit, il
  ne valide pas »). Le socle 403 « authentifié mais interdit » est posé pour toute règle d'accès à
  venir.
- **+** Élargissement **sans route parallèle** ni duplication d'autorisation : une seule surface de
  saisie, une seule dépendance, l'admin conservé.
- **+** Contrôle **atomique** (dans la write-queue) : pas de fenêtre de course entre « lire la cible de
  l'archer » et « écrire le score ».
- **+** Aucune dépendance nouvelle ; `Annotated[..., Depends(...)]` est du FastAPI standard.
- **−** La garde « on ne saisit que sur un tournoi **en cours** » n'est **pas** posée ici : `exiger_poste`
  refuse déjà un tournoi `TERMINE` (ADR-0029), mais un tournoi `brouillon` reste saisissable via poste.
  Cohérent avec le périmètre (la garde de statut de saisie relève d'E04US002, cf. ADR-0029 §3) — signalé,
  non corrigé ici.
- **−** `SaisieHorsCible` porte un message **volontairement générique** (« ce poste ne peut saisir que
  pour sa propre cible ») : aucun détail interne ne fuit (règle 5). Le diagnostic fin (quelle cible sert
  le poste, où est placé l'archer) reste au serveur.
- **Périmètre** : E10US007 est une US **d'autorisation, sans surface front** (la grille de saisie est
  E04US002) : pas de scénario fonctionnel `docs/fonctionnel/` livré ici — il n'y a pas d'UI à décrire
  pour un non-technicien. Le comportement est garanti par les tests service (depuis le CA) et API.
