# ADR-0087 — Une attente n'est pas une indisponibilité

- **Statut** : accepté
- **Date** : 16/08/2026
- **US** : E05US030 (le système suisse à l'écran)
- **Voisins** : [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) §2 (le précédent
  exact : un repêché n'est pas un éliminé), [ADR-0083](0083-le-contrat-de-phase-jouable.md) (le
  contrat de phase jouable, dont le décor `RONDES_APPARIEES` produit ce cas),
  [ADR-0084](0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md)

## Contexte

`IssueRoutage` dit **ce que le panneau a à annoncer** à un archer : « voici ton prochain duel »,
« tu es éliminé, voici ton rang », « tu es repêché », « tu tires la prochaine manche », « on ne sait
pas où tu tires ». Chaque valeur a été ajoutée par l'US qui en avait besoin, et
[ADR-0065 §2](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) a posé le critère : **la
distinction est métier, pas technique.** Annoncer « éliminé » à un repêché le fait rentrer chez lui
avant son duel.

Le **système suisse** (`E05US026`) crée une situation qu'aucun format antérieur ne produisait. Une
phase à rondes n'expose que sa **ronde courante** : les adversaires de la suivante se choisissent au
classement du moment, donc le moteur refuse d'apparier tant que la ronde en cours n'est pas close
(`domain/suisse.py::_rondes_closes`). Deux populations se retrouvent alors **en course et sans rien
à tirer** :

- le porteur du **bye** d'une ronde à effectif impair — il chôme, ce repos lui compte une victoire ;
- l'archer dont la rencontre **vient d'être validée** pendant que les autres tirent encore.

Un format à groupes connus d'avance — les poules — n'a pas ce régime : le round-robin est écrit dès
la composition, donc un membre sans rencontre restante a réellement fini.

`E05US026` était **backend seul**, par décision de découpage : elle ne pouvait pas toucher à
`IssueRoutage`, que le front consomme (`features/routage/api.ts`). Elle a donc **emprunté**
`INDISPONIBLE` avec un motif explicite (« Rien à tirer pour l'instant : sa prochaine rencontre n'est
pas encore appariée ») et noté l'issue propre au CA d'`E05US030`. L'emprunt ne disait rien de faux —
le panneau ne *peut pas* dire où cet archer tire ensuite — mais il le **rangeait avec ceux qu'on ne
sait pas router**, et c'est ce qui coûte : le front partitionne sur l'issue (`EN_LICE`), donc le
porteur de bye sortait du groupe des tireurs encore en lice, sur l'écran projeté du gymnase.

## Décision

### 1. `EN_ATTENTE` est une issue à part entière, pas un `INDISPONIBLE` motivé

Sixième valeur de `IssueRoutage`, de même nature que `REPECHE` (ADR-0065 §2) : elle sépare deux
**situations métier** que le champ `motif` ne pouvait distinguer que pour un lecteur humain. Ce qui
la justifie n'est pas la formulation du message, c'est le **classement** de l'archer : `EN_ATTENTE`
compte parmi ceux qui tirent encore, `INDISPONIBLE` non.

Les trois cas de `ServiceRoutage._sans_rencontre` sont désormais distincts de bout en bout :

| Situation | Issue | Ce que l'écran en fait |
|---|---|---|
| Il n'est pas dans cette phase | `INDISPONIBLE` | rangé hors course, motif affiché |
| La phase est épuisée, ou il a fini | `TERMINE` | rangé hors course, rang si connu |
| Il y est, en course, mais rien d'apparié | `EN_ATTENTE` | **rangé en course**, en attente |

### 2. Le rétrécissement d'`indisponible` est assumé, et sa sûreté vient du déploiement, pas d'un mécanisme

Ce n'est pas un simple élargissement d'énumération : des lignes qui sortaient en `indisponible`
sortent désormais en `en_attente`. Un client resté à l'ancienne union verrait une valeur inconnue là
où il lisait « on ne sait pas ».

C'est **sans risque ici**, et il faut être exact sur la raison : le serveur et le front de ce projet
sont livrés **ensemble**, dans le même exécutable (ADR-0033), sur un réseau local sans client tiers.
Ce n'est pas le typage qui protège :

- le test miroir (`test_issue_reponse_est_le_miroir_de_l_enumeration`) garde la cohérence entre
  l'énumération d'application et le `Literal` publié — **entre les deux couches du serveur**, rien
  de plus ;
- le `Record` exhaustif du front (`EN_LICE`) est indexé par le type **TypeScript** : il fait échouer
  la compilation quand l'union front est élargie sans que les usages suivent — ce qu'il a fait pour
  `en_attente` —, mais une issue ajoutée **côté serveur seul** ne le ferait pas rougir. Elle
  rendrait `EN_LICE[inconnue]` → `undefined` → falsy, et l'archer partirait chez les sortis.

Toute future issue devra donc être livrée **des deux côtés dans la même US**. C'est la contrepartie
explicite de ce choix, et elle vaut aussi pour la colline (`E05US027`), dont le décor est le même.

## Conséquences

- Le panneau de routage, ses quatre canaux et l'écran de salle comptent le porteur de bye parmi les
  tireurs en course. C'était le défaut visible ; il est refermé.
- `ADR-0065 §2` disait « `IssueRoutage` passe de trois à quatre valeurs » : cette phrase est
  **périmée** (six aujourd'hui), et la définition implicite d'`INDISPONIBLE` qu'elle portait s'est
  resserrée. Le critère qu'elle pose, lui, est repris tel quel — c'est lui qui a tranché ici.
- Le titre affiché reste volontairement pauvre (« Rien à tirer pour l'instant ») : promettre « ronde
  3 » annoncerait un rendez-vous **qui n'est pas encore apparié**. C'est le *pourquoi* qui est dans
  le motif, pas un horaire.
- ⚠️ Ce que cet ADR ne tranche **pas** : qui décide de l'ouverture de la ronde suivante. Aujourd'hui
  elle se déduit à la lecture, dès la dernière validation ; un pilotage explicite par l'organisateur
  est instruit par `E05US032` et demandera son propre ADR.

## Porté dans le code par

| Module | Ce qu'il applique |
|---|---|
| `backend/application/routage.py` — `IssueRoutage.EN_ATTENTE` | la valeur elle-même et sa docstring de décision |
| `backend/application/routage.py` — `ServiceRoutage._sans_rencontre` | les **trois** cas distincts (§1), et l'ordre dans lequel ils sont tranchés |
| `backend/api/v1/routage.py` — `IssueRoutageReponse` | le miroir fermé publié au schéma, et la note sur le rétrécissement (§2) |
| `backend/tests/test_service_routage.py` — `_router_sans_rencontre` et ses quatre cas | le garde-fou : `EN_ATTENTE` n'absorbe ni `TERMINE` ni `INDISPONIBLE` |
| `backend/tests/test_routage_api.py` — `test_issue_reponse_est_le_miroir_de_l_enumeration` | l'égalité d'ensembles entre l'énumération et le `Literal` (§2, 1ᵉʳ point) |
| `frontend/src/features/routage/api.ts` — `IssueRoutage` | l'union côté client |
| `frontend/src/features/routage/presentation.ts` — `EN_LICE`, `partitionner`, `titre` | le **classement en course** (§1) : c'est là que l'emprunt coûtait |
| `frontend/src/features/routage/presentation.test.ts` | les cas qui gardent la distinction à l'écran |
