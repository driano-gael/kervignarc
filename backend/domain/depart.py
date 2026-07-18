"""Agrégat `Depart` — un créneau (session horaire) d'un tournoi (E02US004, ADR-0017).

Un **départ** est un créneau du tournoi, comme si le tournoi se jouait plusieurs fois dans la
journée : le hall se remplit, tire, se vide, puis se remplit d'une autre vague. C'est une entité
**du tournoi** (`tournoi_id`), **partagée** par les archers qui s'y inscrivent — l'inscription
(lien archer↔départ) est E02US009, pas cet agrégat.

Agrégat de domaine **pur** (aucune dépendance framework, immuable) : `creer`/`modifier` valident les
valeurs et renvoient une copie. Le `numero` est **attribué par le service** (1, 2, 3…, unique dans
le tournoi) ; le domaine ne voit qu'un départ à la fois et ne peut donc pas garantir l'unicité — il
vérifie seulement qu'un numéro est un entier ≥ 1.

**L'argent est compté en centimes entiers** (ADR-0012), d'où le suffixe `_centimes`. Contrairement
à l'ancien tarif du tournoi (E01US010), le tarif d'un créneau est **obligatoire** : on ne crée pas
un départ sans prix, donc l'état « non défini » (`None`) n'existe plus ici — `0` (gratuit) reste un
état licite et distinct.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.erreurs import NumeroDepartInvalide, QuotaDepartInvalide, TarifDepartInvalide
from domain.tournoi import TournoiId

DepartId = int
"""Identifiant technique d'un départ, attribué par la persistance."""

CENTIMES_PAR_EURO = 100
"""Un euro vaut cent centimes — l'unité de tout montant du projet (ADR-0012)."""

TARIF_DEPART_MAX_CENTIMES = 1000 * CENTIMES_PAR_EURO
"""Plafond du tarif d'un départ : **1 000 €**.

Règle métier, pas garde-fou technique : un départ coûte en pratique 8 à 15 € ; au-delà de mille
euros, c'est une saisie erronée, et il vaut mieux la refuser avec un message que l'enregistrer. Il a
accessoirement le mérite de tenir le tarif loin de la capacité d'un entier SQLite, qu'un montant
absurde ferait déborder en erreur non typée plutôt qu'en 422.
"""

QUOTA_DEPART_MAX = 1000
"""Plafond du quota d'un départ : **1 000 places**.

Règle métier doublée d'un garde-fou, comme `TARIF_DEPART_MAX_CENTIMES` : une salle de tir en
salle plafonne à quelques dizaines de cibles par créneau ; au-delà de mille inscrits sur un seul
départ, c'est une saisie erronée. Le borner ici (422) évite aussi qu'un entier absurde n'atteigne
SQLite et n'y déborde en erreur non typée (500). Un quota **absent** (`None`) reste illimité.
"""


@dataclass(frozen=True)
class Depart:
    """Un créneau de tir d'un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté.

    `numero` est attribué par le service (unique dans le tournoi) ; `horaire` est un libellé de
    créneau facultatif (ex. « 9h00 ») ; `tarif_centimes` est le prix **de ce créneau**, obligatoire.
    `quota` est le nombre maximal d'inscrits **de ce créneau** (E02US006), **facultatif** : `None`
    = pas de plafond. L'agrégat ne connaît que la **valeur** du quota ; le contrôle « inscrits <
    quota » vit dans le service (il voit les inscriptions, pas l'agrégat).
    """

    tournoi_id: TournoiId
    numero: int
    tarif_centimes: int
    horaire: str | None = None
    quota: int | None = None
    id: DepartId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        numero: int,
        tarif_centimes: int,
        horaire: str | None = None,
        quota: int | None = None,
    ) -> Depart:
        """Crée un départ valide.

        Lève `NumeroDepartInvalide` si le numéro n'est pas un entier ≥ 1, `TarifDepartInvalide`
        si le tarif sort de `[0, 1 000 €]`, `QuotaDepartInvalide` si un quota est défini hors de
        `[1, 1 000]`. L'horaire est normalisé (espaces de bord retirés) ; un horaire vide devient
        `None` (facultatif). Un `quota` à `None` = créneau sans plafond.
        """
        return Depart(
            tournoi_id=tournoi_id,
            numero=_numero_valide(numero),
            tarif_centimes=_tarif_valide(tarif_centimes),
            horaire=_horaire_normalise(horaire),
            quota=_quota_valide(quota),
        )

    def modifier(
        self, tarif_centimes: int, horaire: str | None = None, quota: int | None = None
    ) -> Depart:
        """Renvoie une copie au tarif, à l'horaire et au quota mis à jour (règles de `creer`).

        L'`id`, le `tournoi_id` et surtout le `numero` sont **préservés** : le numéro est attribué
        par le système, il n'est pas une donnée que l'admin corrige (au contraire du nom d'un club).
        L'édition est un **remplacement complet** : un `quota` omis (`None`) **retire** le plafond,
        comme un horaire omis l'efface — l'appelant renvoie les valeurs courantes qu'il veut garder.
        Lève `TarifDepartInvalide` / `QuotaDepartInvalide` si tarif ou quota sont hors plage.

        Abaisser le quota **sous** le nombre d'inscrits déjà en place est accepté ici : l'agrégat ne
        voit pas les inscriptions, et le blocage ne joue qu'aux **nouvelles** inscriptions (le
        service ne rejette qu'au moment d'inscrire, jamais les inscrits déjà présents — E02US006).
        """
        return replace(
            self,
            tarif_centimes=_tarif_valide(tarif_centimes),
            horaire=_horaire_normalise(horaire),
            quota=_quota_valide(quota),
        )


def _numero_valide(numero: int) -> int:
    """Vérifie qu'un numéro de créneau est un entier ≥ 1 ; lève `NumeroDepartInvalide` sinon."""
    if numero < 1:
        raise NumeroDepartInvalide("Le numéro d'un départ doit être un entier positif.")
    return numero


def _horaire_normalise(horaire: str | None) -> str | None:
    """Normalise l'horaire ; un horaire vide ou absent devient `None` (facultatif)."""
    if horaire is None:
        return None
    horaire_normalise = horaire.strip()
    return horaire_normalise or None


def _tarif_valide(tarif_centimes: int) -> int:
    """Valide le tarif : un nombre de centimes dans `[0, 1 000 €]`.

    Lève `TarifDepartInvalide` hors de cette plage. Zéro est **admis** — un créneau peut être
    gratuit. Le **plafond** est une règle métier (cf. `TARIF_DEPART_MAX_CENTIMES`).
    """
    if not 0 <= tarif_centimes <= TARIF_DEPART_MAX_CENTIMES:
        raise TarifDepartInvalide(
            "Le tarif d'un départ doit être compris entre 0 et "
            f"{TARIF_DEPART_MAX_CENTIMES // CENTIMES_PAR_EURO} €."
        )
    return tarif_centimes


def _quota_valide(quota: int | None) -> int | None:
    """Valide le quota : `None` (illimité) ou un entier de places dans `[1, QUOTA_DEPART_MAX]`.

    Lève `QuotaDepartInvalide` hors de cette plage. `None` est **admis** — un créneau sans plafond.
    `0` est **refusé** : un quota nul fermerait le créneau à toute inscription, ce qui se dit en
    supprimant le départ, pas en le plafonnant à zéro (le test doit être `is not None`, pas la
    vérité de `quota`, pour ne pas confondre `0` et « absent »).
    """
    if quota is None:
        return None
    if not 1 <= quota <= QUOTA_DEPART_MAX:
        raise QuotaDepartInvalide(
            f"Le quota d'un départ doit être compris entre 1 et {QUOTA_DEPART_MAX} places "
            "(ou absent pour un créneau sans plafond)."
        )
    return quota
