"""Tests d'intégration de `IdentiteVisuelleRepositorySQL` (E16US006, ADR-0097).

Exerce l'adapter sur une **vraie base** migrée, sans passer par l'API. Écrit **après**
l'implémentation, conformément à la règle 9 : il n'y a pas d'oracle métier ici, seulement des
coutures d'adapter.

⚠️ **Ce fichier existe parce que trois gardes défensives ajoutées en revue n'étaient exercées par
rien** — deux enveloppes d'erreur et le refus de fabriquer un défaut — et parce que l'appariement
`emplacement → colonnes` est désormais écrit **deux fois** (une pour la lecture, une pour
l'écriture) : les inverser dans une seule des deux servirait le logo du club à l'emplacement
événement sans qu'aucun test d'API ne bouge, chacun n'utilisant qu'un emplacement à la fois.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from sqlalchemy import text

from domain.identite import Couleur, EmplacementLogo, IdentiteVisuelle, Logo, TypeLogo
from domain.tournoi import Tournoi
from infrastructure.db import Database, IdentiteVisuelleRepositorySQL, TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base

_DATE = datetime.date(2026, 11, 14)

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB\x60\x82"
)
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


@pytest.fixture
def depot(tmp_path: Path) -> tuple[IdentiteVisuelleRepositorySQL, Database, int]:
    """Un adapter câblé sur une base migrée jetable, avec un tournoi persisté."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Trophée", _DATE))
    assert tournoi.id is not None
    return IdentiteVisuelleRepositorySQL(db.session_factory), db, tournoi.id


# ————————————————————————————————————————————————————————————————————————————————————————————————
# L'appariement des deux emplacements — écrit deux fois, donc à vérifier une fois


def test_les_deux_emplacements_ne_se_melangent_pas(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """⚠️ Le seul test du dépôt qui écrive **un** emplacement et relise **l'autre**.

    `_colonnes_du_logo` (lecture) et `_ecrire_le_logo` (écriture) portent chacun leur
    correspondance `emplacement → colonnes` : intervertir les deux branches dans une seule des deux
    fonctions ferait servir le mauvais logo, et aucun test d'API ne le verrait — ils n'exercent
    qu'un emplacement à la fois, ou les deux avec le même contenu.
    """
    adapter, _, tournoi_id = depot
    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.EVENEMENT, Logo.deposer(PNG, TypeLogo.PNG))

    assert adapter.logo(tournoi_id, EmplacementLogo.CLUB) is None, "l'autre emplacement reste vide"
    evenement = adapter.logo(tournoi_id, EmplacementLogo.EVENEMENT)
    assert evenement is not None
    assert evenement.contenu == PNG
    assert evenement.type_logo is TypeLogo.PNG

    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, Logo.deposer(SVG, TypeLogo.SVG))

    club = adapter.logo(tournoi_id, EmplacementLogo.CLUB)
    assert club is not None and club.contenu == SVG, "le club porte bien SON fichier"
    toujours = adapter.logo(tournoi_id, EmplacementLogo.EVENEMENT)
    assert toujours is not None and toujours.contenu == PNG, "l'événement n'a pas bougé"


def test_l_empreinte_est_persistee_avec_les_octets(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """La projection des réglages ne charge **aucun** octet : c'est la raison d'être de la table
    séparée. L'empreinte est donc **stockée**, pas recalculée — sinon connaître le numéro de version
    d'un logo obligerait à relire 512 Ko à chaque affichage public."""
    adapter, db, tournoi_id = depot
    logo = Logo.deposer(PNG, TypeLogo.PNG)
    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, logo)

    assert adapter.reglages(tournoi_id).empreintes == {EmplacementLogo.CLUB: logo.empreinte}

    # ⚠️ **La moitié qui prouve.** L'assertion ci-dessus passe que la valeur vienne de la colonne ou
    # d'un hachage à la relecture : elle ne distingue pas les deux, alors que la docstring promet
    # « stockée, pas recalculée ». On force donc un témoin en base — seule une lecture de la colonne
    # peut le rendre (relevé par deux axes de revue).
    with db.engine.begin() as cnx:
        cnx.execute(
            text(
                "UPDATE identite_tournoi SET logo_club_empreinte = 'temoin' WHERE tournoi_id = :id"
            ),
            {"id": tournoi_id},
        )

    assert adapter.reglages(tournoi_id).empreintes == {EmplacementLogo.CLUB: "temoin"}
    assert (
        adapter.empreinte_du_logo(tournoi_id, EmplacementLogo.CLUB) == "temoin"
    ), "la route des octets lit la MÊME colonne : une seule source pour la version"


def test_retirer_un_logo_efface_le_triplet_entier(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """« Les trois `NULL` ensemble, ou aucun » — l'invariant que SQLite ne sait pas exprimer et que
    cet adapter est seul à tenir. Une empreinte qui survivrait à ses octets ferait croire à un logo
    présent, et l'écran afficherait une image cassée."""
    adapter, db, tournoi_id = depot
    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, Logo.deposer(PNG, TypeLogo.PNG))

    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, None)

    assert adapter.reglages(tournoi_id).empreintes == {}
    with db.engine.connect() as cnx:
        restes = cnx.execute(
            text(
                "SELECT logo_club, logo_club_type, logo_club_empreinte "
                "FROM identite_tournoi WHERE tournoi_id = :id"
            ),
            {"id": tournoi_id},
        ).one()
    assert restes == (None, None, None), "les trois colonnes partent ensemble"


def test_l_empreinte_stockee_est_bien_celle_du_contenu(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """L'invariant que la persistance de l'empreinte met en jeu : une valeur dérivée que l'on stocke
    peut **diverger** de ce dont elle dérive. Ici l'adapter est le seul écrivain, et ce test fixe le
    contrat — ce qui est en colonne est l'empreinte des octets qui sont à côté."""
    adapter, _, tournoi_id = depot
    logo = Logo.deposer(PNG, TypeLogo.PNG)

    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, logo)

    relu = adapter.logo(tournoi_id, EmplacementLogo.CLUB)
    assert relu is not None
    assert adapter.empreinte_du_logo(tournoi_id, EmplacementLogo.CLUB) == relu.empreinte


def test_une_ligne_incoherente_est_une_erreur_technique(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """Depuis l'empreinte, « y a-t-il un logo ? » a **deux** lectures : la projection la déduit de
    l'empreinte, la route des octets du blob. Une ligne où elles divergent ferait dire « aucun logo
    »
    à `/identite` pendant que `/identite/logos/{…}` en sert un — sur la seule paire de routes que
    l'écran de salle appelle ensemble. SQLite ne sait pas l'exprimer ; l'adapter le refuse."""
    adapter, db, tournoi_id = depot
    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, Logo.deposer(PNG, TypeLogo.PNG))
    with db.engine.begin() as cnx:
        cnx.execute(
            text("UPDATE identite_tournoi SET logo_club_empreinte = NULL WHERE tournoi_id = :id"),
            {"id": tournoi_id},
        )

    with pytest.raises(InfrastructureError):
        adapter.reglages(tournoi_id)


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Le défaut appartient à l'agrégat — l'adapter n'en fabrique aucun


def test_enregistrer_des_accents_absents_n_ecrit_pas_les_couleurs_du_club(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """⚠️ Le port l'écrit noir sur blanc : « l'adapter ne **fabrique** aucun défaut ».

    La rédaction d'origine lisait `identite.accents` — la propriété **effective**, qui retombe sur
    les couleurs du club — et aurait donc persisté `#b71918` / `#1d1d1b` en faisant basculer
    `reglee` à `true` sans que personne n'ait rien choisi. C'est le défaut que l'US a chassé du
    service, réintroduit un étage plus bas. Aucun appelant d'aujourd'hui ne l'atteint : c'est le
    premier « revenir aux couleurs du club » qui l'armera, et ce test est là pour lui.
    """
    adapter, _, tournoi_id = depot

    adapter.enregistrer_accents(tournoi_id, IdentiteVisuelle())

    reglages = adapter.reglages(tournoi_id)
    assert reglages.reglee is False, "rien de choisi reste rien de choisi"
    assert reglages.accent_primaire is None
    assert reglages.accent_secondaire is None


def test_les_accents_choisis_sont_relus_tels_quels(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """Le cas apparié du précédent : ce qui a été choisi revient à l'identique, et `reglee` suit."""
    adapter, _, tournoi_id = depot
    voulue = IdentiteVisuelle().avec_accents(
        Couleur.depuis_hex("#0b6e9e"), Couleur.depuis_hex("#ffd400")
    )

    adapter.enregistrer_accents(tournoi_id, voulue)

    relue = adapter.reglages(tournoi_id)
    assert relue.reglee is True
    assert relue.accent_primaire == Couleur.depuis_hex("#0b6e9e")
    assert relue.accent_secondaire == Couleur.depuis_hex("#ffd400")


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Une ligne que le domaine refuse est une incohérence TECHNIQUE, pas une requête invalide


def test_une_couleur_illisible_en_base_sort_en_erreur_d_infrastructure(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """⚠️ Sans l'enveloppe, `Couleur.depuis_hex` laissait remonter une `DomainError` **au client**,
    sur une lecture **publique** — donc un 422 « votre requête est invalide » pour une requête qui
    n'a rien d'invalide, avec la valeur de base recopiée dans le message rendu.

    Le module fait partout ailleurs l'inverse (`_vers_tournoi` documente ce piège exact pour
    `GET /tournois`) ; le raisonnement n'avait simplement pas été porté au code neuf."""
    adapter, db, tournoi_id = depot
    adapter.enregistrer_accents(
        tournoi_id,
        IdentiteVisuelle().avec_accents(
            Couleur.depuis_hex("#0b6e9e"), Couleur.depuis_hex("#ffd400")
        ),
    )
    with db.engine.begin() as cnx:
        cnx.execute(
            text(
                "UPDATE identite_tournoi SET accent_primaire = 'pas-une-couleur' "
                "WHERE tournoi_id = :id"
            ),
            {"id": tournoi_id},
        )

    with pytest.raises(InfrastructureError):
        adapter.reglages(tournoi_id)


def test_un_type_de_logo_illisible_en_base_sort_en_erreur_d_infrastructure(
    depot: tuple[IdentiteVisuelleRepositorySQL, Database, int],
) -> None:
    """Le pendant du précédent sur la route des octets : `TypeLogo(...)` lève une `ValueError`, qui
    n'est pas une `SQLAlchemyError` — elle traversait l'adapter et sortait en 500 **non typé**."""
    adapter, db, tournoi_id = depot
    adapter.enregistrer_logo(tournoi_id, EmplacementLogo.CLUB, Logo.deposer(PNG, TypeLogo.PNG))
    with db.engine.begin() as cnx:
        cnx.execute(
            text(
                "UPDATE identite_tournoi SET logo_club_type = 'image/tiff' WHERE tournoi_id = :id"
            ),
            {"id": tournoi_id},
        )

    with pytest.raises(InfrastructureError):
        adapter.logo(tournoi_id, EmplacementLogo.CLUB)
