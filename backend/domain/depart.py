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

from domain.erreurs import NumeroDepartInvalide, TarifDepartInvalide
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


@dataclass(frozen=True)
class Depart:
    """Un créneau de tir d'un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté.

    `numero` est attribué par le service (unique dans le tournoi) ; `horaire` est un libellé de
    créneau facultatif (ex. « 9h00 ») ; `tarif_centimes` est le prix **de ce créneau**, obligatoire.
    """

    tournoi_id: TournoiId
    numero: int
    tarif_centimes: int
    horaire: str | None = None
    id: DepartId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        numero: int,
        tarif_centimes: int,
        horaire: str | None = None,
    ) -> Depart:
        """Crée un départ valide.

        Lève `NumeroDepartInvalide` si le numéro n'est pas un entier ≥ 1, `TarifDepartInvalide`
        si le tarif sort de `[0, 1 000 €]`. L'horaire est normalisé (espaces de bord retirés) ; un
        horaire vide devient `None` (facultatif).
        """
        return Depart(
            tournoi_id=tournoi_id,
            numero=_numero_valide(numero),
            tarif_centimes=_tarif_valide(tarif_centimes),
            horaire=_horaire_normalise(horaire),
        )

    def modifier(self, tarif_centimes: int, horaire: str | None = None) -> Depart:
        """Renvoie une copie au tarif et à l'horaire mis à jour (mêmes règles que `creer`).

        L'`id`, le `tournoi_id` et surtout le `numero` sont **préservés** : le numéro est attribué
        par le système, il n'est pas une donnée que l'admin corrige (au contraire du nom d'un club).
        Seuls le tarif et l'horaire d'un créneau s'éditent. Lève `TarifDepartInvalide` si le tarif
        est hors plage.
        """
        return replace(
            self,
            tarif_centimes=_tarif_valide(tarif_centimes),
            horaire=_horaire_normalise(horaire),
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
