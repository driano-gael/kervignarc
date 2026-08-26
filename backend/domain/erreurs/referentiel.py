"""Erreurs du **patrimoine et de la configuration** — ce qu'un club décrit avant que
quiconque tire : le tournoi, ses archers, ses clubs, ses catégories, ses blasons, ses
gabarits de salle, ses départs, ses tarifs et ses formats.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 94 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from domain.erreurs.base import DomainError


class NomTournoiInvalide(DomainError):
    """Le nom d'un tournoi est vide (après normalisation)."""

    code = "nom_tournoi_invalide"


class CouleurInvalide(DomainError):
    """Une couleur d'accent n'est pas au format `#RRGGBB` (E16US006)."""

    code = "couleur_invalide"


class TypeDeLogoRefuse(DomainError):
    """Un logo déposé n'est ni un PNG ni un SVG sûr (E16US006).

    Couvre les quatre refus de contenu — vide, signature démentant le format annoncé, absence de
    balise `<svg>`, SVG porteur de script. Un seul code : de la place de l'organisateur c'est le
    même geste — le fichier n'est pas acceptable, le message dit lequel des quatre cas.
    """

    code = "type_de_logo_refuse"


class LogoTropVolumineux(DomainError):
    """Un logo dépasse `POIDS_LOGO_MAX_OCTETS` (E16US006)."""

    code = "logo_trop_volumineux"


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


class NomFormatInvalide(DomainError):
    """Le nom d'un format de tournoi est vide (après normalisation) — E01US023."""

    code = "nom_format_invalide"


class FormatSansEtape(DomainError):
    """Un format de tournoi ne décrit aucune phase (E01US023, ADR-0060 §5).

    Distinct d'une `SequencePhases` **vide**, qui est licite (un tournoi peut n'avoir aucune phase
    composée). Un *format*, lui, n'existe que pour être appliqué : appliquer un format vide ne
    créerait rien, et l'organisateur croirait avoir assemblé son tournoi.
    """

    code = "format_sans_etape"


class FormatSansDepart(DomainError):
    """Un format est appliqué à un tournoi qui n'a **aucun départ** (E01US025, ADR-0075).

    Symétrique de `FormatSansEtape`, à l'autre bout de l'application : le départ étant la portée
    sportive, un format s'instancie **par départ**. Sans créneau, l'application ne créerait aucune
    phase — et le silence ferait croire à un succès, exactement le piège que `FormatSansEtape` évite
    du côté du format.
    """

    code = "format_sans_depart"


class PhasesDeDepartsMeles(DomainError):
    """On promeut en format des phases venant de **plusieurs départs** (E01US025, ADR-0075).

    Un format décrit **une** séquence 1..N ; chaque départ a la sienne. Mêler deux départs
    produirait des ordres en doublon — détectés plus tard comme incohérence de séquence, donc trop
    loin de la cause pour être compréhensibles.
    """

    code = "phases_de_departs_meles"


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


class HoraireDepartInvalide(DomainError):
    """L'horaire d'un départ n'est pas un horaire du jour `HH:MM` valide (E02US010).

    Depuis E02US010, l'horaire d'un créneau est une **vraie donnée temporelle obligatoire**
    (24 h, `00:00`-`23:59`), et non plus le libellé libre d'E02US004 : « 9hzc », « matin » ou un
    horaire absent sont refusés **au domaine** (422). Le front pose un masque `HH:MM` en
    prévention, mais l'autorité reste ici — le serveur ne fait pas confiance à la saisie cliente.
    """

    code = "horaire_depart_invalide"


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


class HandicapInvalide(DomainError):
    """La valeur de handicap portée par un archer n'est pas exploitable (E05US015).

    Un handicap s'**ajoute** au score réalisé (règle donnée par le commanditaire le 31/07/2026) :
    il est donc positif ou nul. Une valeur négative retrancherait des points, ce qui n'est pas le
    système décrit — et passerait inaperçue au classement, où elle ressemblerait à une
    contre-performance.
    """

    code = "handicap_invalide"
