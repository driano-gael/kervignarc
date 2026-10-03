"""Tests du service de sauvegardes (E11US006) — écrits depuis les CA « précisés au cadrage ».

Doublure du port `MagasinSauvegardes` : le service décide (ordre, verdict, refus, séquence de
restauration), le magasin exécute. La mécanique SQLite est testée à part (adapter).
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import SauvegardeIntrouvable, SauvegardeNonRestaurable
from application.sauvegardes import (
    ExamenSauvegarde,
    NatureSauvegarde,
    SauvegardeDisponible,
    ServiceSauvegardes,
    VerdictSauvegarde,
)

_REVISION = "0058_tete"


def _instant(heure: int) -> datetime.datetime:
    return datetime.datetime(2026, 10, 3, heure, 0, tzinfo=datetime.UTC)


class _MagasinFactice:
    """Magasin en mémoire qui **journalise** les gestes, pour vérifier leur ordre."""

    def __init__(self, sauvegardes: list[SauvegardeDisponible]) -> None:
        self._sauvegardes = sauvegardes
        self.examens: dict[str, ExamenSauvegarde] = {
            s.nom: ExamenSauvegarde(integre=True, revision=_REVISION) for s in sauvegardes
        }
        self.revision = _REVISION
        self.journal: list[str] = []

    def lister(self) -> list[SauvegardeDisponible]:
        return list(self._sauvegardes)

    def examiner(self, nom: str) -> ExamenSauvegarde:
        self.journal.append(f"examiner:{nom}")
        return self.examens[nom]

    def revision_en_service(self) -> str | None:
        return self.revision

    def copier_avant_restauration(self) -> str:
        self.journal.append("copie")
        return "avant-restauration-20261003-120000.db"

    def restaurer(self, nom: str) -> None:
        self.journal.append(f"restaurer:{nom}")


def _sauvegarde(nom: str, heure: int, nature: NatureSauvegarde) -> SauvegardeDisponible:
    return SauvegardeDisponible(nom=nom, nature=nature, prise_le=_instant(heure), taille_octets=10)


_P9 = _sauvegarde("kervignarc-20261003-090000.db", 9, NatureSauvegarde.PERIODIQUE)
_P11 = _sauvegarde("kervignarc-20261003-110000.db", 11, NatureSauvegarde.PERIODIQUE)
_A10 = _sauvegarde("avant-restauration-20261003-100000.db", 10, NatureSauvegarde.AVANT_RESTAURATION)


def _service(magasin: _MagasinFactice) -> tuple[ServiceSauvegardes, list[str]]:
    fermetures: list[str] = []
    service = ServiceSauvegardes(magasin, oublier_etat_volatil=lambda: fermetures.append("etat"))
    return service, fermetures


# --- CA 1 : liste, plus récentes d'abord, toutes natures confondues ---


def test_liste_des_plus_recentes_aux_plus_anciennes_toutes_natures() -> None:
    service, _ = _service(_MagasinFactice([_P9, _A10, _P11]))

    assert [s.nom for s in service.lister()] == [_P11.nom, _A10.nom, _P9.nom]


# --- CA 2 : vérification à la demande ---


def test_une_sauvegarde_integre_au_schema_en_service_est_restaurable() -> None:
    service, _ = _service(_MagasinFactice([_P9]))

    assert service.verifier(_P9.nom).verdict is VerdictSauvegarde.RESTAURABLE


def test_une_sauvegarde_corrompue_est_signalee_comme_telle() -> None:
    magasin = _MagasinFactice([_P9])
    magasin.examens[_P9.nom] = ExamenSauvegarde(integre=False, revision=_REVISION)
    service, _ = _service(magasin)

    assert service.verifier(_P9.nom).verdict is VerdictSauvegarde.CORROMPUE


@pytest.mark.parametrize("revision", ["0042_ancienne", None])
def test_une_sauvegarde_d_un_autre_schema_est_signalee(revision: str | None) -> None:
    # `None` : un fichier SQLite sans table `alembic_version` n'est pas une base Kervignarc.
    magasin = _MagasinFactice([_P9])
    magasin.examens[_P9.nom] = ExamenSauvegarde(integre=True, revision=revision)
    service, _ = _service(magasin)

    assert service.verifier(_P9.nom).verdict is VerdictSauvegarde.VERSION_DIFFERENTE


def test_la_corruption_prime_sur_la_version() -> None:
    # Une base corrompue peut mentir sur sa révision : on ne la qualifie pas d'« autre version ».
    magasin = _MagasinFactice([_P9])
    magasin.examens[_P9.nom] = ExamenSauvegarde(integre=False, revision="0042_ancienne")
    service, _ = _service(magasin)

    assert service.verifier(_P9.nom).verdict is VerdictSauvegarde.CORROMPUE


# --- CA 6 : seul un nom listé est atteignable ---


@pytest.mark.parametrize("nom", ["inconnue.db", "../kervignarc.db", "kervignarc.db"])
def test_un_nom_non_liste_est_introuvable_a_la_verification(nom: str) -> None:
    magasin = _MagasinFactice([_P9])
    service, _ = _service(magasin)

    with pytest.raises(SauvegardeIntrouvable):
        service.verifier(nom)
    assert magasin.journal == []


def test_un_nom_non_liste_est_introuvable_a_la_restauration() -> None:
    magasin = _MagasinFactice([_P9])
    service, fermetures = _service(magasin)

    with pytest.raises(SauvegardeIntrouvable):
        service.restaurer("../ailleurs.db")
    assert magasin.journal == []
    assert fermetures == []


# --- CA 2 + 3 + 4 + 5 : la restauration ---


def test_restaurer_copie_l_etat_courant_puis_restaure_puis_ferme_les_sessions() -> None:
    magasin = _MagasinFactice([_P9, _P11])
    service, fermetures = _service(magasin)

    resultat = service.restaurer(_P9.nom)

    assert magasin.journal == [f"examiner:{_P9.nom}", "copie", f"restaurer:{_P9.nom}"]
    assert fermetures == ["etat"]
    assert resultat.restauree == _P9.nom
    assert resultat.copie_de_securite == "avant-restauration-20261003-120000.db"


def test_une_copie_avant_restauration_se_restaure_elle_meme() -> None:
    # CA 4 : c'est ainsi qu'on annule une restauration.
    magasin = _MagasinFactice([_A10])
    service, _ = _service(magasin)

    assert service.restaurer(_A10.nom).restauree == _A10.nom


@pytest.mark.parametrize(
    ("examen", "verdict"),
    [
        (ExamenSauvegarde(integre=False, revision=_REVISION), VerdictSauvegarde.CORROMPUE),
        (ExamenSauvegarde(integre=True, revision="0042"), VerdictSauvegarde.VERSION_DIFFERENTE),
    ],
)
def test_une_sauvegarde_non_restaurable_est_refusee_sans_rien_toucher(
    examen: ExamenSauvegarde, verdict: VerdictSauvegarde
) -> None:
    magasin = _MagasinFactice([_P9])
    magasin.examens[_P9.nom] = examen
    service, fermetures = _service(magasin)

    with pytest.raises(SauvegardeNonRestaurable) as refus:
        service.restaurer(_P9.nom)

    assert refus.value.details == {"verdict": verdict.value}
    assert magasin.journal == [f"examiner:{_P9.nom}"]
    assert fermetures == []
