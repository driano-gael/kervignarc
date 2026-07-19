"""Erreurs du domaine (ADR-0007) — une règle métier est violée.

Racine `DomainError` : le domaine **ignore HTTP**. La traduction en réponse (HTTP 422,
code métier) se fait uniquement à la frontière API (`api/erreurs.py`).
"""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier. Chaque sous-classe porte un `code` stable."""

    code = "erreur_domaine"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NomTournoiInvalide(DomainError):
    """Le nom d'un tournoi est vide (après normalisation)."""

    code = "nom_tournoi_invalide"


class NomArcherInvalide(DomainError):
    """Le nom d'un archer est vide (après normalisation)."""

    code = "nom_archer_invalide"


class PrenomArcherInvalide(DomainError):
    """Le prénom d'un archer est vide (après normalisation, E02US002)."""

    code = "prenom_archer_invalide"


class NomClubInvalide(DomainError):
    """Le nom d'un club est vide (après normalisation)."""

    code = "nom_club_invalide"


class LibelleCategorieInvalide(DomainError):
    """Le libellé d'une catégorie est vide (après normalisation)."""

    code = "libelle_categorie_invalide"


class HauteurCentreInvalide(DomainError):
    """La hauteur du centre de l'or d'une catégorie n'est pas un entier strictement positif.

    Hauteur du sol au centre de l'or, en cm (E03US001, ADR-0022). Pilote la contrainte de
    placement « une butte, une hauteur » : 130 cm par défaut, 110 cm pour les U11 (référentiel §5).
    """

    code = "hauteur_centre_invalide"


class NomBlasonInvalide(DomainError):
    """Le nom d'un blason est vide (après normalisation)."""

    code = "nom_blason_invalide"


class TailleBlasonInvalide(DomainError):
    """La taille d'un blason sort de la plage autorisée (fraction de place `]0, 1]`)."""

    code = "taille_blason_invalide"


class CapaciteBlasonInvalide(DomainError):
    """La capacité d'un blason est inférieure à 1."""

    code = "capacite_blason_invalide"


class ZonesBlasonInvalides(DomainError):
    """Les valeurs de score admises d'un blason sont invalides (E01US014).

    Hors vocabulaire du référentiel (§4.2), doublon, absence de `M`, ou aucune zone marquante.
    """

    code = "zones_blason_invalides"


class NomGabaritInvalide(DomainError):
    """Le nom d'un gabarit de salle est vide (après normalisation)."""

    code = "nom_gabarit_invalide"


class NombreCiblesInvalide(DomainError):
    """Le nombre de cibles d'un gabarit de salle est inférieur à 1."""

    code = "nombre_cibles_invalide"


class CapaciteCibleInvalide(DomainError):
    """Le plafond d'archers d'une cible sort de la plage autorisée (`[1, 4]`)."""

    code = "capacite_cible_invalide"


class CibleInvalide(DomainError):
    """Le numéro de cible d'un placement n'est pas un entier strictement positif."""

    code = "cible_invalide"


class NombreVoleesInvalide(DomainError):
    """Le nombre de volées d'un barème de qualification est inférieur à 1."""

    code = "nombre_volees_invalide"


class NombreFlechesParVoleeInvalide(DomainError):
    """Le nombre de flèches par volée d'un barème de qualification est inférieur à 1."""

    code = "nombre_fleches_par_volee_invalide"


class NumeroDepartInvalide(DomainError):
    """Le numéro d'un départ (créneau) n'est pas un entier strictement positif (E02US004)."""

    code = "numero_depart_invalide"


class TarifDepartInvalide(DomainError):
    """Le tarif d'un départ sort de la plage autorisée (`[0, 1 000 €]`, E02US004 / ADR-0017).

    Un tarif **nul** est licite (créneau gratuit). Contrairement à l'ancien tarif du tournoi, le
    tarif d'un créneau est **obligatoire** — il n'y a plus d'état « non défini » : voir
    `Depart.tarif_centimes`.
    """

    code = "tarif_depart_invalide"


class QuotaDepartInvalide(DomainError):
    """Le quota d'un départ (créneau) est défini mais n'est pas un entier ≥ 1 (E02US006).

    Le quota est **facultatif** : `None` = illimité, un état licite et distinct. Défini, il compte
    des **places** — au moins une, sinon le créneau serait fermé à toute inscription (on le
    supprimerait plutôt). Un plafond `QUOTA_DEPART_MAX` borne le haut, même raison que le tarif :
    une valeur absurde est une faute de frappe, et on la refuse ici (422) plutôt que de la laisser
    déborder la capacité d'un entier SQLite en erreur non typée (500).
    """

    code = "quota_depart_invalide"


class NombreVoleesParValidationInvalide(DomainError):
    """La cadence d'un grain « toutes les N volées » est inférieure à 1 (E01US015)."""

    code = "nombre_volees_par_validation_invalide"


class NombreVoleesParValidationManquant(DomainError):
    """Un grain « toutes les N volées » a été demandé sans préciser N (E01US015)."""

    code = "nombre_volees_par_validation_manquant"


class CadenceValidationSuperieureAuBareme(DomainError):
    """La cadence de validation dépasse le nombre de volées du barème de la phase (E01US015).

    Valider « toutes les 30 volées » une qualification qui n'en compte que 20, c'est ne **jamais**
    valider : le grain et le barème vivent sur la même phase, leur cohérence est une règle métier.
    """

    code = "cadence_validation_superieure_au_bareme"


class GrainIncompatibleAvecTypePhase(DomainError):
    """Le grain de validation n'a pas de sens pour ce type de phase (E01US015).

    Ex. « fin de duel » sur une phase de `qualification`, qui ne comporte pas de duels.
    """

    code = "grain_incompatible_avec_type_phase"


class ScoreInvalide(DomainError):
    """La valeur d'un score sort de la plage autorisée pour une flèche (0 à 10)."""

    code = "score_invalide"


class NumeroVoleeInvalide(DomainError):
    """Le numéro (rang) d'une volée n'est pas un entier `>= 1` (E04US002)."""

    code = "numero_volee_invalide"


class NombreFlechesVoleeInvalide(DomainError):
    """Le nombre de flèches d'une volée ne correspond pas au barème de la phase (E04US002).

    Le barème (E01US009) fixe combien de flèches compte une volée ; une volée d'un autre compte est
    refusée à la saisie — distinct de `NombreFlechesParVoleeInvalide`, qui protège le **barème**,
    quand celle-ci protège une **volée saisie** contre ce barème.
    """

    code = "nombre_fleches_volee_invalide"


class ValeurHorsBlason(DomainError):
    """Une valeur saisie n'est pas une zone admise du blason tiré (E04US002, `Blason.zones`).

    Le pavé de saisie se déduit du **blason** et non du barème : sur un triple 40 les valeurs 5 → 1
    n'existent pas (référentiel §4.4). Une valeur hors des `zones_admises` est donc refusée.
    """

    code = "valeur_hors_blason"


class VoleeVerrouillee(DomainError):
    """Tentative de modifier par simple saisie une volée déjà validée (E04US002).

    Après validation, une volée est verrouillée : le seul chemin d'écriture est la **correction
    tracée** (rôle habilité, `Serie.corriger_volee`), pas la ré-saisie.
    """

    code = "volee_verrouillee"


class VoleeNonVerrouillee(DomainError):
    """Tentative de corriger une volée qui n'est pas verrouillée (E04US002).

    La correction tracée ne vise que le **verrouillé** ; une volée en cours se modifie par saisie
    ordinaire (`Serie.saisir_volee`), sans trace d'audit.
    """

    code = "volee_non_verrouillee"


class VoleeIntrouvable(DomainError):
    """Aucune volée de ce numéro dans la série (E04US002) — corriger n'est pas créer."""

    code = "volee_introuvable"


class SerieIncomplete(DomainError):
    """Validation « fin de série » demandée avant que toutes les volées du barème soient saisies."""

    code = "serie_incomplete"


class RienAValider(DomainError):
    """Aucune volée à valider : ni lot complet du grain, ni reliquat de fin de barème (E04US002)."""

    code = "rien_a_valider"


class NomScoreurInvalide(DomainError):
    """Le nom d'un scoreur est vide (après normalisation, E10US003)."""

    code = "nom_scoreur_invalide"


class CodeScoreurInvalide(DomainError):
    """Le code individuel d'un scoreur est vide (après normalisation, E10US003).

    Le code est **attribué par le service** (généré, jamais saisi à la création) : cette erreur
    protège l'invariant à la construction de l'agrégat, elle n'est pas un cas d'entrée utilisateur.
    """

    code = "code_scoreur_invalide"


class CodePosteInvalide(DomainError):
    """Le code d'un poste de cible est vide (après normalisation, E04US001).

    Le code est **attribué par le service** (généré, jamais saisi à la création) : cette erreur
    protège l'invariant à la construction de l'agrégat, elle n'est pas un cas d'entrée utilisateur.
    Le numéro de cible invalide réutilise, lui, `CibleInvalide` (déjà défini pour le placement).
    """

    code = "code_poste_invalide"


class AuteurAuditInvalide(DomainError):
    """L'auteur d'une entrée du journal d'audit est vide (après normalisation, E10US005).

    L'auteur est le **nom** de qui a agi (scoreur, admin) — le premier des « qui / quand /
    avant-après ». Une entrée sans auteur ne dit pas *qui* : elle manque sa raison d'être en litige.
    """

    code = "auteur_audit_invalide"


class ObjetAuditInvalide(DomainError):
    """L'objet d'une entrée du journal d'audit est vide (après normalisation, E10US005).

    L'objet décrit *ce sur quoi* porte l'action (quelle série, quelle cible, quel archer). Sans lui,
    une **validation** — qui n'a ni avant ni après — ne serait plus rattachable à rien.
    """

    code = "objet_audit_invalide"


class HorodatageAuditInvalide(DomainError):
    """L'horodatage d'une entrée d'audit n'est pas un instant **UTC** *aware* (E10US005).

    Le « quand » d'une trace de litige doit être comparable **sans ambiguïté de fuseau**. La
    persistance stocke un `DateTime` **sans fuseau** et l'adapter réattache UTC à la relecture :
    cette réattache n'est fidèle **que si** l'instant écrit était déjà UTC. Un `datetime` **naïf**
    (aucun fuseau) ou **aware non-UTC** (ex. `Europe/Paris`) ferait donc **mentir le journal en
    silence** — la valeur murale serait stockée puis relue comme de l'UTC. On ferme ce chemin **à la
    construction**, comme les autres invariants de l'entrée, plutôt que laisser une horloge fautive
    corrompre la preuve.
    """

    code = "horodatage_audit_invalide"
