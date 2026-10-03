"""Service des **sauvegardes** : lister, vérifier, restaurer à chaud (E11US006, ADR-0119).

⚠️ **`restaurer` s'exécute dans la file d'écriture** (règle 7) : c'est l'appelant (frontière API)
qui l'y soumet. Le service ne la connaît pas — même contrat que tout autre cas d'usage d'écriture.

Port au niveau **applicatif**, comme `ConstructeurArchive` : une sauvegarde est une préoccupation
d'exploitation, pas une règle métier.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from application.erreurs import SauvegardeIntrouvable, SauvegardeNonRestaurable


class NatureSauvegarde(StrEnum):
    PERIODIQUE = "periodique"
    AVANT_RESTAURATION = "avant_restauration"


class VerdictSauvegarde(StrEnum):
    RESTAURABLE = "restaurable"
    CORROMPUE = "corrompue"
    VERSION_DIFFERENTE = "version_differente"


@dataclass(frozen=True)
class SauvegardeDisponible:
    nom: str
    nature: NatureSauvegarde
    prise_le: datetime.datetime
    taille_octets: int


@dataclass(frozen=True)
class ExamenSauvegarde:
    """Constat brut du magasin ; `revision` vaut `None` sans table `alembic_version` lisible."""

    integre: bool
    revision: str | None


@dataclass(frozen=True)
class VerificationSauvegarde:
    nom: str
    verdict: VerdictSauvegarde


@dataclass(frozen=True)
class RestaurationEffectuee:
    restauree: str
    copie_de_securite: str


class MagasinSauvegardes(Protocol):
    """Port : le dossier des sauvegardes et la base en service."""

    def lister(self) -> list[SauvegardeDisponible]: ...

    def examiner(self, nom: str) -> ExamenSauvegarde:
        """Intégrité et révision d'une sauvegarde, **en lecture seule**."""
        ...

    def revision_en_service(self) -> str | None: ...

    def copier_avant_restauration(self) -> str:
        """Copie l'état courant hors rétention ; renvoie le nom de la copie."""
        ...

    def restaurer(self, nom: str) -> None:
        """Remplace le contenu de la base en service par celui de la sauvegarde."""
        ...


class ServiceSauvegardes:
    def __init__(
        self, magasin: MagasinSauvegardes, oublier_etat_volatil: Callable[[], None]
    ) -> None:
        self._magasin = magasin
        self._oublier_etat_volatil = oublier_etat_volatil

    def lister(self) -> list[SauvegardeDisponible]:
        return sorted(self._magasin.lister(), key=lambda s: s.prise_le, reverse=True)

    def verifier(self, nom: str) -> VerificationSauvegarde:
        self._exiger_listee(nom)
        return VerificationSauvegarde(nom, self._verdict(nom))

    def restaurer(self, nom: str) -> RestaurationEffectuee:
        self._exiger_listee(nom)
        verdict = self._verdict(nom)
        if verdict is not VerdictSauvegarde.RESTAURABLE:
            raise SauvegardeNonRestaurable(nom, verdict.value)
        copie = self._magasin.copier_avant_restauration()
        self._magasin.restaurer(nom)
        # ⚠️ Après la restauration, jamais avant : un échec laisse sessions et registres intacts.
        self._oublier_etat_volatil()
        return RestaurationEffectuee(restauree=nom, copie_de_securite=copie)

    def _exiger_listee(self, nom: str) -> None:
        # CA 6 : la liste est la seule source des noms admis — aucun chemin construit depuis `nom`.
        if nom not in {s.nom for s in self._magasin.lister()}:
            raise SauvegardeIntrouvable(nom)

    def _verdict(self, nom: str) -> VerdictSauvegarde:
        examen = self._magasin.examiner(nom)
        if not examen.integre:
            return VerdictSauvegarde.CORROMPUE
        if examen.revision is None or examen.revision != self._magasin.revision_en_service():
            return VerdictSauvegarde.VERSION_DIFFERENTE
        return VerdictSauvegarde.RESTAURABLE
