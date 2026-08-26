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
from dataclasses import replace

import pytest

from application.erreurs import TournoiArchiveNonModifiable, TournoiIntrouvable
from application.identite import ServiceIdentite
from domain.identite import Couleur, EmplacementLogo, IdentiteVisuelle, Logo, TypeLogo
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
        self.fichiers: dict[EmplacementLogo, Logo] = {}

    def reglages(self, tournoi_id: TournoiId) -> IdentiteVisuelle:
        return self.identite

    def logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> Logo | None:
        # ⚠️ Rendait `None` en dur, alors que les deux méthodes d'écriture venaient d'être rendues
        # fidèles au port. Conséquence : la moitié « et ses logos » du test d'archive n'était
        # exercée par rien, et une garde de statut ajoutée par distraction à `ServiceIdentite.logo`
        # aurait éteint les logos d'un tournoi archivé sans faire rougir personne (relevé en revue).
        return self.fichiers.get(emplacement)

    def empreinte_du_logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> str | None:
        fichier = self.fichiers.get(emplacement)
        return None if fichier is None else fichier.empreinte

    def enregistrer_accents(
        self, tournoi_id: TournoiId, identite: IdentiteVisuelle
    ) -> IdentiteVisuelle:
        # ⚠️ Le port dit « écrit les deux accents, **sans toucher aux logos** » et rend l'identité
        # relue, présence des logos comprise. Un faux qui écraserait tout serait vrai par vacuité
        # dès la première assertion sur `logos_presents` — et « régler une couleur n'efface pas un
        # logo » est un CA. Un faux qui ment sur son port ne teste que lui-même (relevé en revue).
        self.ecritures.append("accents")
        self.identite = replace(
            identite,
            empreintes=dict(self.identite.empreintes),
        )
        return self.identite

    def enregistrer_logo(
        self, tournoi_id: TournoiId, emplacement: EmplacementLogo, logo: Logo | None
    ) -> IdentiteVisuelle:
        """Écrit **un** emplacement ; les accents et l'autre emplacement ne bougent pas."""
        self.ecritures.append(f"logo:{emplacement.value}")
        if logo is None:
            self.fichiers.pop(emplacement, None)
            self.identite = self.identite.sans_logo(emplacement)
        else:
            self.fichiers[emplacement] = logo
            self.identite = self.identite.avec_logo(emplacement, logo.empreinte)
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
    "statut", [statut for statut in StatutTournoi if statut is not StatutTournoi.ARCHIVE]
)
def test_l_identite_se_regle_a_tout_moment(statut: StatutTournoi) -> None:
    """`P-3`. Changer une couleur ou un logo ne touche **aucun score** : rien ne justifie de geler
    l'identité parce que les archers tirent. C'est le CA, et c'est aussi ce qui rend l'écran utile —
    un logo oublié se rattrape le matin même, pas la veille.

    ⚠️ **Dérivé de l'enum, et non énuméré à la main.** La première rédaction listait cinq statuts et
    oubliait `annulé` — précisément le membre ambigu du lot (terminal, mais « conserve la trace »),
    donc celui qu'un test dérivé du CA aurait dû forcer à trancher. Écrit ainsi, le jour où un
    huitième statut apparaît, ce test **exige** qu'on décide s'il accepte l'écriture, au lieu de le
    laisser hors du champ en silence."""
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


def test_un_tournoi_archive_garde_ses_couleurs_et_les_sert() -> None:
    """Lecture seule veut dire **lecture**, justement : une archive garde ses couleurs et ses logos,
    et l'appli publique doit continuer de les servir. Sans ce test, resserrer la garde d'écriture
    d'un cran de trop éteindrait l'affichage d'un tournoi passé sans faire rougir personne.

    ⚠️ La première rédaction lisait une archive **sans identité** et vérifiait qu'elle rendait le
    rouge du club : elle prouvait seulement que `pour_tournoi` ne lève pas sur `ARCHIVE`, jamais la
    conservation qu'elle annonçait — le défaut hérité est ce que le faux rend de toute façon."""
    service, identites = _service(StatutTournoi.ARCHIVE)
    identites.identite = IdentiteVisuelle().avec_accents(
        Couleur.depuis_hex("#0b6e9e"), Couleur.depuis_hex("#ffd400")
    )
    identites.fichiers[EmplacementLogo.CLUB] = Logo.deposer(PNG, TypeLogo.PNG)

    identite = service.pour_tournoi(1)

    assert identite.reglee is True
    assert identite.primaire.couleur.hex == "#0b6e9e", "l'archive garde SES couleurs"
    assert identite.secondaire.couleur.hex == "#ffd400"
    # « et ses logos » : la seconde moitié de la promesse, qu'aucune assertion ne tenait.
    assert service.logo(1, EmplacementLogo.CLUB) is not None, "l'archive sert encore son logo"
    assert service.empreinte_du_logo(1, EmplacementLogo.CLUB) is not None


def test_un_tournoi_archive_sans_identite_herite_comme_les_autres() -> None:
    """Le cas apparié : l'archive n'est pas un état particulier pour la lecture, seulement pour
    l'écriture. Un tournoi passé qui n'avait rien réglé hérite du club, comme un tournoi neuf."""
    service, _ = _service(StatutTournoi.ARCHIVE)

    identite = service.pour_tournoi(1)

    assert identite.reglee is False
    assert identite.primaire.couleur.hex == "#b71918", "le rouge du club, hérité"


def test_regler_les_accents_n_efface_pas_un_logo_deja_depose() -> None:
    """CA : les deux gestes sont indépendants. Ce test ne vaut que parce que `FauxIdentites`
    respecte le contrat du port — un faux qui écraserait tout le rendrait vrai par vacuité."""
    service, identites = _service(StatutTournoi.BROUILLON)
    service.deposer_logo(1, EmplacementLogo.CLUB, PNG, TypeLogo.PNG)

    apres = service.regler_accents(1, "#0b6e9e", "#ffd400")

    assert apres.reglee is True
    assert set(apres.empreintes) == {EmplacementLogo.CLUB}, "le logo a survécu au réglage"


def test_un_tournoi_inconnu_est_introuvable_avant_toute_garde_de_statut() -> None:
    """L'ordre compte : un identifiant inconnu rend `404`, pas `409`. Les deux refus vivent dans la
    même méthode, et les intervertir donnerait un message de conflit sur un tournoi qui n'existe
    pas."""
    service, _ = _service(None)

    with pytest.raises(TournoiIntrouvable):
        service.regler_accents(1, "#b71918", "#1d1d1b")
