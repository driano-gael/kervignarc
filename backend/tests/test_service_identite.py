"""Tests du service **identité visuelle** — les gardes de statut (E16US006, ADR-0097).

Écrits **depuis le CA** (règle 9) : `P-3` dit « modifiable à tout moment, **tournoi en cours
compris** », et `ADR-0026` §1 dit qu'un tournoi `archivé` est en lecture seule totale. Les deux
règles vivent dans ce service, elles se testent donc ici — et non par l'API, où atteindre `archivé`
demanderait de traverser tout le cycle de vie (`vers-pret` exige un départ, `demarrer`, `terminer`,
`archiver`) pour éprouver un `if` de deux lignes.

⚠️ **Ce fichier existe parce qu'il manquait.** La revue a relevé que la seule garde de statut
introduite par l'US n'était couverte à **aucune couche** — ni le refus sur archivé, ni l'acceptation
en cours — alors que `docs/fonctionnel/E16US006.md` (étape 10) promet les deux comportements au
recetteur, message d'erreur compris. Une garde documentée que rien n'exerce est précisément ce que
`api/erreurs.py` documente déjà deux fois avoir laissé passer (`MancheIntrouvable`,
`JalonNonInstruit`).
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import TournoiArchiveNonModifiable, TournoiIntrouvable
from application.identite import ServiceIdentite
from domain.identite import EmplacementLogo, IdentiteVisuelle, Logo, TypeLogo
from domain.tournoi import StatutTournoi, Tournoi, TournoiId
from tests.conftest import FauxTournoiRepository

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB\x60\x82"
)


class FauxIdentites:
    """Adapter en mémoire du port `IdentiteVisuelleRepository`.

    Garde trace de ce qu'on lui a demandé d'écrire : ce que ces tests veulent savoir, c'est si le
    service a **laissé passer** l'écriture, pas ce que la base en aurait fait.
    """

    def __init__(self) -> None:
        self.ecritures: list[str] = []
        self.identite = IdentiteVisuelle()

    def reglages(self, tournoi_id: TournoiId) -> IdentiteVisuelle:
        return self.identite

    def logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> Logo | None:
        return None

    def enregistrer_accents(
        self, tournoi_id: TournoiId, identite: IdentiteVisuelle
    ) -> IdentiteVisuelle:
        self.ecritures.append("accents")
        self.identite = identite
        return identite

    def enregistrer_logo(
        self, tournoi_id: TournoiId, emplacement: EmplacementLogo, logo: Logo | None
    ) -> IdentiteVisuelle:
        self.ecritures.append(f"logo:{emplacement.value}")
        return self.identite


def _service(statut: StatutTournoi | None) -> tuple[ServiceIdentite, FauxIdentites]:
    """Câble le service sur deux faux conformes aux ports — `statut=None` = tournoi inconnu.

    Le repository de tournois vient du `conftest` partagé plutôt que d'un faux local à un seul
    `par_id` : un faux partiel obligerait à un `# type: ignore[arg-type]` au montage, et un outil
    contourné dans un fichier de test n'est pas plus « vert » qu'ailleurs. Il satisfait le protocole
    en entier, donc `mypy --strict` vérifie réellement le câblage que ce fichier prétend éprouver.
    """
    identites = FauxIdentites()
    tournois = FauxTournoiRepository()
    if statut is not None:
        tournois.ajouter(
            Tournoi(
                nom="Challenge des Champions",
                date=datetime.date(2026, 11, 14),
                statut=statut,
            )
        )
    return ServiceIdentite(identites, tournois), identites


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA `P-3` — « modifiable à tout moment, tournoi en cours compris »


@pytest.mark.parametrize(
    "statut",
    [
        StatutTournoi.BROUILLON,
        StatutTournoi.PRET,
        StatutTournoi.EN_COURS,
        StatutTournoi.EN_PAUSE,
        StatutTournoi.TERMINE,
    ],
)
def test_l_identite_se_regle_a_tout_moment(statut: StatutTournoi) -> None:
    """`P-3`. Changer une couleur ou un logo ne touche **aucun score** : rien ne justifie de geler
    l'identité parce que les archers tirent. C'est le CA, et c'est aussi ce qui rend l'écran utile —
    un logo oublié se rattrape le matin même, pas la veille."""
    service, identites = _service(statut)

    service.regler_accents(1, "#b71918", "#1d1d1b")
    service.deposer_logo(1, EmplacementLogo.CLUB, PNG, TypeLogo.PNG)
    service.retirer_logo(1, EmplacementLogo.CLUB)

    assert identites.ecritures == ["accents", "logo:club", "logo:club"]


# ————————————————————————————————————————————————————————————————————————————————————————————————
# ADR-0026 §1 — l'archivé est en lecture seule TOTALE


def test_un_tournoi_archive_refuse_le_reglage_des_accents() -> None:
    service, identites = _service(StatutTournoi.ARCHIVE)

    with pytest.raises(TournoiArchiveNonModifiable):
        service.regler_accents(1, "#b71918", "#1d1d1b")

    assert identites.ecritures == [], "le refus doit précéder l'écriture, pas la suivre"


def test_un_tournoi_archive_refuse_le_depot_d_un_logo() -> None:
    """⚠️ Le dépôt d'un logo est la seule écriture qui **crée la ligne** d'identité : un refus qui
    arriverait après coup laisserait une trace dans une archive censée être figée."""
    service, identites = _service(StatutTournoi.ARCHIVE)

    with pytest.raises(TournoiArchiveNonModifiable):
        service.deposer_logo(1, EmplacementLogo.EVENEMENT, PNG, TypeLogo.PNG)

    assert identites.ecritures == []


def test_un_tournoi_archive_refuse_le_retrait_d_un_logo() -> None:
    """Le retrait est idempotent, donc inoffensif en apparence — raison de plus pour le verrouiller
    explicitement : « ça ne changeait rien » est ce qu'on dit après avoir effacé le logo d'une
    archive."""
    service, identites = _service(StatutTournoi.ARCHIVE)

    with pytest.raises(TournoiArchiveNonModifiable):
        service.retirer_logo(1, EmplacementLogo.CLUB)

    assert identites.ecritures == []


def test_un_tournoi_archive_se_lit_normalement() -> None:
    """Lecture seule veut dire **lecture**, justement : une archive garde ses couleurs et ses logos,
    et l'appli publique doit continuer de les servir. Sans ce test, resserrer la garde d'écriture
    d'un cran de trop éteindrait l'affichage d'un tournoi passé sans faire rougir personne."""
    service, _ = _service(StatutTournoi.ARCHIVE)

    identite = service.pour_tournoi(1)

    assert identite.reglee is False
    assert identite.primaire.couleur.hex == "#b71918", "le rouge du club, hérité"


def test_un_tournoi_inconnu_est_introuvable_avant_toute_garde_de_statut() -> None:
    """L'ordre compte : un identifiant inconnu rend `404`, pas `409`. Les deux refus vivent dans la
    même méthode, et les intervertir donnerait un message de conflit sur un tournoi qui n'existe
    pas."""
    service, _ = _service(None)

    with pytest.raises(TournoiIntrouvable):
        service.regler_accents(1, "#b71918", "#1d1d1b")
