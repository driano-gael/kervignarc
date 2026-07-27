# ADR-0051 — Cycle de vie d'un départ : état dérivé, garde-fou confirmable

- **Statut** : Accepté
- **Date** : 2026-07-27
- **Décideurs** : Organisateur / Architecte
- **Portée** : E12US008 (cycle de vie d'un départ / créneau)
- **Complète / amende** : [ADR-0018](0018-supprimer-un-depart-a-inscriptions-confirmable.md)
  (suppression d'un départ à inscriptions — le garde-fou de cycle **subsume** celui d'inscriptions
  quand le créneau est lancé/clos)
- **Lie** : [ADR-0040](0040-alerte-par-calcul-d-impact.md) (alerte par calcul d'impact — même
  famille de signalement chiffré), E12US005 (complétude — mêmes décomptes, réutilisés), E04US015 /
  [ADR-0050](0050-forfait-abandon-et-disqualification.md) (forfait = série close, DETTE-014)

## Contexte et problème

E12US008 veut empêcher qu'un créneau **déjà en cours de tir** se modifie ou se supprime aussi
librement qu'un créneau encore vide — sans détruire une session en cours. Le CA (déporté d'E02US009,
ADR-0018) demandait un **état** *ouvert · lancé · clos* **dérivé d'un fait réel** (« heure atteinte,
premier score »), et un contrôle « au moins signalé » à l'édition/suppression.

Trois zones d'ombre bloquaient l'écriture des tests depuis le CA (règle 9) :

1. **De quel fait réel dériver « lancé » ?** Le CA cite « heure atteinte ». Or `Depart.horaire` est
   un **libellé libre** (`str | None`, « 9h00 »), pas une heure comparable : « heure atteinte » n'est
   pas calculable sans re-modéliser l'horaire.
2. **Quand un créneau devient-il « clos » ?** Le CA est muet.
3. **« Contrôlé » = bloquer ou avertir ?** Le CA dit « au moins signalé ».

## Décision

**1. État dérivé, jamais stocké.** `Depart` reste un agrégat **figé** (règle 4) sans colonne de
statut. L'état est un **calcul** à la lecture, porté par un value object pur `AvancementDepart`
(`domain/cycle_depart.py`) qui dérive `EtatDepart` de trois décomptes — nombre d'archers placés,
combien ont tiré, combien ont leur série close — exactement comme `domain/impact.py` dérive un niveau
d'alerte. Règle :

- `nb_ayant_tire == 0` → **ouvert** ;
- sinon, toutes les séries closes → **clos** ; sinon → **lancé**.

**2. « lancé » = présence d'un score.** Le fait réel retenu est la **flèche validée**
(`Serie.nb_fleches_validees > 0`), seul fait réel disponible. « heure atteinte » est écarté (horaire
non comparable). **« clos » = toutes les séries des archers placés closes**, au sens de
`ServiceCompletude._serie_close` : barème validé **ou** forfait (E04US015, DETTE-014). L'échelle
**s'appuie sur un tir réel** : un créneau dont la seule activité serait un forfait sans aucune flèche
reste **ouvert** — l'échelle demeure monotone (jamais *ouvert → clos* sans *lancé*).

**3. « contrôlé » = confirmable, pas bloquant.** Modifier/supprimer un créneau *lancé*/*clos* lève
`DepartEnCoursNonConfirme` (409, canal `details` chiffré : état + archers ayant tiré) tant que
`confirme_cycle` n'est pas vrai — même **famille que `ReplacementNonConfirme`** (ADR-0040), et non
un refus dur. Un créneau *ouvert* garde le comportement E02US009 à l'identique.

**4. Réutilisation de la complétude via un port étroit.** Le calcul de l'avancement (départ →
archers placés → séries → forfaits → barème) **existe déjà** dans `ServiceCompletude` (E12US005). On
ne le duplique pas : `ServiceDeparts` dépend d'un **port étroit** `LecteurAvancementDepart`
(`avancement_depart(...) -> AvancementDepart`), réalisé par `ServiceCompletude` — exactement le
patron `LecteurPaiements` (réalisé par `ServicePaiements`). Le composition root construit donc la
complétude **avant** les départs (réordonnancement à la main, règle 8).

**5. La confirmation de cycle subsume celle d'inscriptions.** À la suppression, un créneau lancé
porte forcément des inscriptions : confirmer qu'on détruit une session de tir couvre *a fortiori*
ses inscriptions. On ne demande donc pas les deux confirmations (pas de double dialogue) ; le
garde-fou `DepartAvecInscriptions` (ADR-0018) ne joue plus que sur un créneau *ouvert*.

## Conséquences

- **Positif** : aucune migration (état dérivé, pas de colonne) ; zéro duplication de l'invariant
  « série close » (forfait/DETTE-014, sensible) ; cohérence de langage avec E12US007 (signalement
  chiffré) et E02US009 (confirmation à bouton). Le front badge l'état (ouvert/lancé/clos) et
  intercepte le 409 pour proposer la confirmation.
- **Coût / limite** : la résolution barème + forfaits est **dupliquée** de `_compter_cibles`
  (2ᵉ occurrence — règle 12, extraction au 3ᵉ cas, pas avant). Le calcul relit placements et séries
  à chaque affichage de la liste des départs (un appel par créneau) : acceptable (mono-club, quelques
  créneaux) — non optimisé sciemment (règle 12, simplicité hors domaine).
- **Choix front signalé pour revue** : la confirmation réutilise le **motif d'alerte chiffrée +
  bouton délibéré** (message serveur qui chiffre les tireurs), cohérent avec le signal voisin
  `depart_avec_inscriptions` du même écran — **pas** la cérémonie « taper un mot » de
  `ConfirmationChiffree`, qu'E12US007 réserve au niveau *massif irréversible* (ici l'édition est
  réversible, la suppression est de la même famille que la suppression-avec-inscriptions).
