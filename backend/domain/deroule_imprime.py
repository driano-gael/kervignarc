"""Le **déroulé horaire imprimable** — un bloc par départ, une ligne par phase (E09US007).

Les heures viennent de `horaire_prevu`, jamais recalculées ici : le papier dit ce que dit l'écran.
Elles restent à la maille de la phase (ADR-0118) ; les tours ne s'impriment qu'en information.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from domain.contrat_phase import TypePhase
from domain.deroule_etape import EtapeDeroule
from domain.horaire_prevu import HeurePrevue, HorairePrevu


@dataclass(frozen=True)
class LigneDeroule:
    """Une phase du déroulé ; `debut`/`fin` à `None` = inconnu, jamais deviné."""

    ordre: int
    type: TypePhase
    titre: str | None
    debut: HeurePrevue | None
    fin: HeurePrevue | None
    tours: str | None


@dataclass(frozen=True)
class BlocDeroule:
    libelle: str
    lignes: tuple[LigneDeroule, ...]


@dataclass(frozen=True)
class DerouleImprime:
    tournoi: str
    blocs: tuple[BlocDeroule, ...]


def tours_annonces(etape: EtapeDeroule) -> str | None:
    """« 2 tours », « 5 rondes », « 3 manches » — seulement quand l'étape **règle** ce nombre.

    ⚠️ Un tableau, des poules, un Big Shoot Off comptent leurs tours selon l'effectif — et le
    tableau selon la politique de `seeding` injectée (règle 2) : les imprimer figerait une
    politique en dur. Cf. `stories/E09-exports.md` → E09US007, CA 3.
    ⚠️ Jumeau de `EtapeDeroule._nb_tours_a_la_composition` : un type ajouté ici s'examine là.
    """
    if etape.type is TypePhase.QUALIFICATION and etape.decoupage is not None:
        return _pluriel(etape.decoupage.nb_tours, "tour")
    if etape.type is TypePhase.SUISSE and etape.suisse is not None:
        return _pluriel(etape.suisse.nb_rondes, "ronde")
    if etape.type is TypePhase.COLLINE and etape.colline is not None:
        return _pluriel(etape.colline.nb_manches, "manche")
    return None


def _pluriel(nombre: int, mot: str) -> str | None:
    return f"{nombre} {mot}s" if nombre > 1 else None


def lignes_du_deroule(
    etapes: Sequence[EtapeDeroule], horaires: Sequence[HorairePrevu]
) -> tuple[LigneDeroule, ...]:
    par_etape = {horaire.etape_id: horaire for horaire in horaires}
    lignes: list[LigneDeroule] = []
    for etape in sorted(etapes, key=lambda e: e.ordre):
        horaire = par_etape.get(etape.id) if etape.id is not None else None
        lignes.append(
            LigneDeroule(
                ordre=etape.ordre,
                type=etape.type,
                titre=etape.titre,
                debut=horaire.debut if horaire is not None else None,
                fin=horaire.fin if horaire is not None else None,
                tours=tours_annonces(etape),
            )
        )
    return tuple(lignes)
