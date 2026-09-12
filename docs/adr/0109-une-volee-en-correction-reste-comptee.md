# ADR-0109 — Une volée en correction reste comptée : le verrou d'écriture n'est pas le compte

- **Statut** : Accepté
- **Date** : 2026-09-11
- **Décideurs** : Organisateur / Architecte
- **Portée** : E16US019 (annuler une validation pour corriger)
- **S'appuie sur** : [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) (l'acte et sa trace
  dans une seule transaction — l'annulation y entre sans rien changer), [ADR-0036](0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md)
  (l'idempotence par identifiant, que l'annulation réemploie), [ADR-0039](0039-exposition-publique-du-deroule-scores-provisoires.md)
  (le déroulé public distingue le **provisoire** du validé — c'est le statut par volée que la
  décision 1 oblige à redériver)
- **Voisin** : [ADR-0107](0107-une-ecriture-concurrente-est-arbitree-par-le-role-de-qui-ecrit.md),
  dont le CA de préséance dépend de la notion de « volée rouverte » définie ici

## Contexte

Le questionnaire de maquettes S08 demandait deux choses qui se lisaient comme contradictoires :
*« plus de modification une fois validé »* et *« une validation peut être annulée »*. Le cadrage
d'`E16US019` a montré qu'il s'agissait d'**une procédure en deux temps** — on n'édite pas un score
validé, on **annule la validation**, on corrige, on revalide — et non d'un affrontement.

Reste que « rouvrir une volée » n'était pas gratuit. Dans `domain/serie.py`, `Volee.verrouillee`
était une *property* dérivée : `validee_par is not None`. Un seul champ portait donc **deux sens** :

1. **le droit d'écrire** — `saisir_volee` refuse une volée verrouillée ;
2. **le compte** — `cumul`, `compter`, `nb_fleches_validees` et `est_complete` ne somment que les
   volées verrouillées.

Annuler « en remettant `validee_par` à `None` » aurait donc rouvert l'écriture **et** retiré la
volée de tous les totaux. Le versant visible était connu (classement, palmarès, écran de salle,
et l'exposition publique qui rebascule en `en_attente`). Le versant invisible l'était moins :
`nb_fleches_validees` n'alimente aucun total — c'est la mesure de « **l'archer a déjà tiré** », et
**trois décisions** en dérivent :

- `application/archers.py` → l'avertissement `ChangementCategorieArcherEngage` (E02US003) ;
- `application/placement.py` → `_impact`, le décompte « cibles avec scores » qu'un organisateur lit
  avant de confirmer une régénération de plan ;
- `application/completude.py` → `_a_tire` / `_est_clos`, la clôture d'un créneau.

Les trois se seraient **désarmées ensemble**, le temps d'une correction, sans que personne l'ait
décidé. Et le cas qui tranche n'est pas la correction rapide : c'est l'annulation **jamais suivie
de ressaisie** — le scoreur annule, part en pause, personne ne corrige. L'archer serait alors resté
hors classement **indéfiniment**, sans que rien ne le signale.

Deux branches ont été présentées au commanditaire — « fenêtre assumée » (la volée sort des totaux)
et « acte unique » (annuler et ressaisir d'un bloc, donc aucune réouverture pour la tablette). Il
les a **toutes deux écartées** au profit d'une troisième.

## Décision

**1. Le verrou d'écriture et le compte deviennent deux états distincts.** `Volee` gagne
`correction_ouverte_par` ; `validee` (« cette volée compte ») vaut `validee_par is not None`, et
`verrouillee` (« on ne peut pas y écrire ») vaut `validee and not en_correction`. Les quatre
lecteurs de totaux passent de `verrouillee` à `validee` : **ils ne bougent pas** quand une
correction s'ouvre.

**2. Annuler rouvre le LOT de validation, identifié en base.** `Volee` gagne `lot_validation`,
posé par `Serie.valider`. Le lot **n'est pas recalculable** : `saisir_volee` n'impose aucun ordre
de saisie, alors que `valider` prend « les `N` premières non validées » — un lot réel peut donc être
non contigu (volées 1 et 3 si la 2 n'était pas saisie), et une tranche de rang `(n-1) // N`
rouvrirait des volées que personne n'a annulées. `validee_par` étant un **nom** et non l'identité
d'un acte, deux lots du même scoreur étaient jusqu'ici indiscernables.

**3. La ressaisie préserve la validation.** `Serie.saisir_volee` sur une volée en correction
**réécrit ses valeurs sans toucher** `validee_par` / `lot_validation` : le total suit la dernière
saisie, la volée ne quitte jamais le compte. Sans cette clause, la décision 1 serait perdue à
l'endroit exact où elle sert — la même clause vaut côté front pour la saisie optimiste hors-ligne.

**4. Refermer une correction est un geste NOMMÉ, distinct de valider.** `refermer_correction(numero)`
revalide le lot rouvert qui contient cette volée, sous un **nouveau** lot et **hors grain** : le
grain régit la *première* validation, et l'appliquer ici laisserait ouvert indéfiniment tout lot
rouvert plus petit que `N` — sur une série incomplète, `RienAValider` serait le seul résultat
possible. `valider`, qui ne reçoit aucune cible, **refuse** tant qu'une correction est ouverte
(`CorrectionOuverte`).

⚠️ **Deux rédactions ont essayé de deviner le lot, et les deux ont été des bloquants de revue** :
« toutes les corrections de la feuille », puis « la plus ancienne ». Dans les deux cas, un scoreur
qui relisait le lot B re-signait « valides » les volées du lot A qu'il n'avait **jamais vues** —
avec leurs valeurs fausses, sous **son** nom, dans le registre qu'on ouvre en contestation. La leçon
est plus large que ce lot : **un geste qui engage une signature ne devine pas sa cible.** Le grain régit la **première**
validation ; le lui appliquer ici laisserait ouvert indéfiniment tout lot rouvert plus petit que
`N` — et, sur une série incomplète, `RienAValider` serait le seul résultat possible. C'est le seul
geste qui referme une correction ; il n'existe pas d'« annuler l'annulation ».

**5. La contrepartie est assumée et rendue visible.** Entre l'annulation et la ressaisie, le
classement affiche un score que le scoreur a déclaré faux. C'est le prix de ne jamais faire
disparaître un archer, et il est **payé par un marqueur** — « En correction » à l'écran scoreur —
qui fait partie de la décision, pas de son habillage.

## Conséquences

- **Une migration** (`0054`), qui n'était pas prévue par la fiche d'US : deux colonnes sur `volee`.
  Le backfill donne `lot_validation = numero` aux volées déjà validées — **un lot par volée**. Les
  lots d'avant l'US ne sont pas connus et les inventer par le grain serait faux (le grain a pu
  changer) ; la conséquence est bornée et dicible : sur un tournoi antérieur, annuler rouvre la
  volée seule au lieu de son bloc. ⚠️ **Un lot d'une seule volée doit rester revalidable** même
  sous un grain « toutes les N » : c'est pourquoi la décision 4 referme une correction **hors
  grain** (relevé en revue — sinon un tel lot restait ouvert jusqu'à ce que N volées se libèrent). Le backfill tient l'invariant dont dépend `annuler_validation` —
  `lot_validation` non `NULL` **si et seulement si** `validee_par` l'est.
- **`corriger_volee` survit.** Deux chemins d'écriture coexistent donc sur un score validé — le
  scoreur corrige en place, ou il rouvre pour que la tablette ressaisisse — et c'est assumé.
  ⚠️ **Les deux SE CROISENT, et il le faut** *(retourné en 2ᵉ passe de revue : la rédaction
  précédente disait que `corriger_volee` refusait une volée en correction)*. Il opère sur une volée
  **comptée**, pas verrouillée : c'est le **seul** recours quand une pause tombe entre l'annulation
  et la ressaisie, puisque les deux gestes qui referment une correction sont, eux, gelés. Corriger
  ne referme pas la fenêtre — le scoreur revalide ensuite.
- **L'audit gagne un acte**, `ANNULATION_VALIDATION` — pas l'inverse d'un acte : rouvrir une volée
  à l'écriture est une décision humaine, elle se trace comme telle.
- **`ADR-0035` n'est pas rouvert** : ses §2 et §3 (réécriture d'un score corrigé, `CORRECTION_SCORE`)
  survivent tous les deux.
- ⚠️ **`ADR-0039` EST touché, et sa Décision 2 est redéfinie.** Elle posait le statut public comme
  `en_attente = not Volee.verrouillee` ; ce n'est plus une définition tenable, puisque `verrouillee`
  a cessé de vouloir dire « ce score compte ». Le statut public dérive désormais de `validee`.
  *(La première rédaction de cet ADR affirmait l'inverse — « l'exposition publique ne rebascule
  jamais en `en_attente` » — alors que `deroule.py` n'avait pas été touché : la réponse publique se
  contredisait elle-même, cumul 54 face à zéro volée publiée « valide ». **Bloquant de revue**, et
  exactement le mode de panne d'ADR-0017 : un ADR qui décrit un code qu'il n'a pas relu.)*
- ⚠️ **La pause BLOQUE l'annulation** — à rebours de `corriger_volee`, et à rebours de la première
  rédaction. « La pause gèle ce qui *avance*, jamais ce qui *répare* » (E05US033) reste vrai, mais
  les **deux** gestes qui referment une correction sont, eux, gelés : `saisir_volee` et `valider`
  portent `refuser_si_en_pause`. Annuler pendant une pause rouvrait donc une volée que plus rien ne
  pouvait refermer jusqu'à la relance. Pendant une pause, on répare par `corriger_volee`.
  *(Relevé en revue : le test d'origine prouvait la permissivité sans jamais dérouler la suite du
  parcours qu'elle rendait possible.)*
- ⚠️ **La ressaisie d'une volée rouverte est tracée `CORRECTION_SCORE`.** Sans cela, l'annulation
  faisait **baisser** la traçabilité : le seul chemin d'écriture restant est `saisir_volee`, ouvert
  au **poste de cible** et muet, là où `corriger_volee` exigeait le scoreur et écrivait
  l'avant/après. Une volée déjà comptée ne se réécrit pas sans trace.
- ⚠️ **Asymétrie connue, non résolue ici** : l'annulation est ouverte à l'admin **et** au scoreur
  (réponse S08), mais `POST /saisie/validations` reste réservé au scoreur. Un admin qui annule ne
  peut donc pas **re**valider lui-même. Rien ne se bloque — la volée reste comptée, précisément par
  la décision 1 — mais élargir la validation demanderait un CA que S08 ne donne pas.
- ⚠️ **Ce que cet ADR ne dit pas** : rien pour les **duels**, le **barrage de places** ni le **Big
  Shoot Off**. Le premier tient déjà S08 (`DuelVerrouille`), le deuxième rouvre volontairement sur
  saisie (y appliquer S08 restaurerait un bug corrigé), le troisième est immuable. Le périmètre est
  la **qualification**, et lui seul.

## Porté dans le code par

- `backend/domain/serie.py` — `Volee.validee` / `Volee.en_correction` / `Volee.verrouillee`
  (décision 1), `Serie.annuler_validation` (décision 2), la clause de préservation dans
  `Serie.saisir_volee` (décision 3) et la pose du lot dans `Serie.valider` (décision 4). ⚠️ Les
  quatre lecteurs de totaux (`cumul`, `compter`, `nb_fleches_validees`, `est_complete`) filtrent sur
  `validee` : **les repasser à `verrouillee` annulerait silencieusement tout cet ADR**. Le diraient
  `test_domain_serie_annulation.py` d'abord, puis les trois tests de chaînage
  (`test_service_{archers,placement,completude}.py`) qui prouvent que les gardes ne se relâchent pas.
- `backend/migrations/versions/0054_volee_annulation_validation.py` — les deux colonnes et le
  backfill qui tient l'invariant `lot_validation ⇔ validee_par`.
- `backend/infrastructure/db/models.py` — `VoleeORM.lot_validation` / `correction_ouverte_par`, et
  `backend/infrastructure/db/repositories/tir.py` — le mapping aller-retour des deux champs (sans
  lui, l'agrégat perdrait son lot à chaque relecture : la persistance rejoue purge + réinsertion).

- `backend/domain/entree_audit.py` — `ActionAuditee.ANNULATION_VALIDATION`.
- `backend/api/v1/saisie.py` — `POST /api/v1/saisie/annulations` et `POST /api/v1/saisie/refermetures`
  (la route qui **nomme** le lot, décision 4), et `VoleeReponse.en_correction` /
  `lot_validation` : le lot est exposé **pour que l'écran puisse nommer** ce qu'il va rouvrir.
- `backend/api/dependances.py` — `autoriser_annulation_validation` (admin ou scoreur) et
  `autoriser_lecture_serie`, qui élargit au scoreur la lecture d'une feuille.
- `frontend/src/features/validation-qualif/etat.ts` — `voleesQueLAnnulationRouvre` et
  `avertissementAnnulation` : la décision 5 rendue lisible **avant** le geste.
- `backend/api/v1/deroule.py` — `VoleeDerouleReponse.de_volee` : le statut public dérive de
  `validee`. ⚠️ **Ce module manquait à la première rédaction**, et c'est lui qui contredisait
  l'ADR ; son test d'API pose l'invariant « cumul = somme des volées publiées *valide* ».
- `backend/application/saisie.py` — `ServiceSaisie.annuler_validation` : résolution de phase, trace
  `ANNULATION_VALIDATION`, et `refuser_si_en_pause` (⚠️ **inverse de la première rédaction**, qui
  écrivait ici « absence délibérée » ; cf. § Conséquences). `ServiceSaisie.saisir_volee` trace
  `CORRECTION_SCORE` quand la volée est en correction, sous l'identité que la **garde** a résolue
  (`_auteur_de_saisie`) — jamais sous le marqueur déclaré.
- `frontend/src/features/saisie/volees.ts` — `serieOptimiste` préserve l'état de validation d'une
  volée en correction (décision 3, versant hors-ligne), et `prochaineASaisir` **met la volée rendue
  en tête** : sans quoi la tablette ouvrait un pavé verrouillé sur la dernière volée du barème.
- `frontend/src/features/saisie/Saisie.tsx` — la tablette **nomme** la volée qu'on lui rend
  (« Volée rendue par MARTIN — à ressaisir »), au lieu de la laisser deviner.
