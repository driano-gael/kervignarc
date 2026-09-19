"""Le palmarès rend **un podium par créneau**, juxtaposés (E06US009 — `DETTE-045` résorbée).

Tests dérivés des **CA de `stories/E06-classements.md`**, écrits avant l'implémentation (règle 9).
L'oracle n'est donc pas le comportement d'aujourd'hui — il est précisément ce que ces tests
contredisent : le palmarès résolvait « le premier départ » et ignorait les autres, silencieusement.

⚠️ **Chaque test doit échouer si l'on repasse la composition à un seul créneau**, au même titre que
`test_portee_deux_creneaux.py` : un test qui resterait vert dans les deux mailles ne prouverait
rien. C'est pourquoi les deux créneaux sont **réellement peuplés** — un créneau vide n'a pas de
classement, donc il rendrait une section vide aussi bien avant qu'après.

Arbitrage du commanditaire du **07/08/2026** : *« juxtaposé — 4 départs = 4 podiums »*, donc
**aucune** agrégation inter-départs. Étendu le **19/09/2026** au classement des clubs, que
`E16US017` avait introduit après cet arbitrage (cf. ADR-0104 amendé).
"""

from __future__ import annotations

import pytest

from application.erreurs import TournoiSansDepart
from application.exports import FormatExport, RegistreDeFormats
from application.palmares import ServicePalmares
from domain.podium import PorteePodium, ReglagePodiums
from tests.conftest import FauxClubRepository
from tests.test_service_palmares import _FauxGenerateurPalmares, _rattacher_a_un_club
from tests.test_service_routage import _Monde, _quatre


def _service(monde: _Monde, clubs: FauxClubRepository | None = None) -> ServicePalmares:
    return ServicePalmares(
        monde.tournois,
        monde.phases,
        monde._classement(),
        monde.saisie,
        monde.duels,
        RegistreDeFormats({FormatExport.PDF: _FauxGenerateurPalmares()}),
        monde.departs,
        clubs or FauxClubRepository(),
    )


def _deux_creneaux_peuples() -> tuple[_Monde, list[int], list[int]]:
    """Le matin et l'après-midi tirent **chacun** leur déroulé — quatre archers, un tableau."""
    monde = _Monde()
    matin = _quatre(monde)
    apres_midi = _quatre(monde, depart_id=monde.depart_id_2)
    monde.placer()
    return monde, matin, apres_midi


def test_un_palmares_par_creneau() -> None:
    """CA « un palmarès par créneau » : deux départs, deux sections — pas une."""
    monde, _, _ = _deux_creneaux_peuples()

    rendu = _service(monde).rendu(monde.tournoi_id)

    assert [section.depart_id for section in rendu.sections] == [
        monde.depart_id,
        monde.depart_id_2,
    ]


def test_chaque_section_ne_porte_que_les_archers_de_son_creneau() -> None:
    """CA « juxtaposition, pas addition » : deux archers de créneaux différents ne se croisent pas.

    ⚠️ C'est le test qui **tombe** si la composition repasse au tournoi : les huit archers se
    retrouveraient alors dans la même section, classés les uns contre les autres.
    """
    monde, matin, apres_midi = _deux_creneaux_peuples()

    rendu = _service(monde).rendu(monde.tournoi_id)
    vus = [{ligne.archer_id for ligne in section.complet.lignes} for section in rendu.sections]

    assert vus == [set(matin), set(apres_midi)]


def test_chaque_creneau_decerne_son_propre_or() -> None:
    """CA « aucun classement du tournoi » : chaque créneau décerne **son** or, à **son** archer.

    ⚠️ **L'assertion porte sur l'identité des deux vainqueurs, pas sur la présence de deux rangs 1.**
    La première version de ce test comparait `[1, 1]` : elle restait **verte** quand on remettait le
    raccourci « premier départ », puisque le même palmarès rendu deux fois a bien deux fois un
    rang 1. Le sabotage l'a montré — c'est la case « Sabotage » de la checklist d'implémentation.
    """
    monde, matin, apres_midi = _deux_creneaux_peuples()

    rendu = _service(monde).rendu(monde.tournoi_id)
    vainqueurs = [
        next(ligne.archer_id for ligne in section.complet.lignes if ligne.rang_min == 1)
        for section in rendu.sections
    ]

    assert vainqueurs[0] in matin
    assert vainqueurs[1] in apres_midi
    assert vainqueurs[0] != vainqueurs[1]


def test_chaque_section_est_nommee_par_son_creneau() -> None:
    """CA « chaque podium est nommé » : le libellé usuel, celui du domaine.

    ⚠️ **`Depart.libelle_creneau` et non une chaîne recomposée ici** : ce libellé est déjà persisté
    verbatim au registre de remboursement (ADR-0057), et une seconde orthographe dans le produit
    est exactement ce que `DETTE-106` recense.
    """
    monde, _, _ = _deux_creneaux_peuples()

    rendu = _service(monde).rendu(monde.tournoi_id)

    assert [section.libelle for section in rendu.sections] == [
        "Départ n°1 — 09:00",
        "Départ n°2 — 14:00",
    ]


def test_un_tournoi_mono_creneau_rend_une_seule_section() -> None:
    """CA « un tournoi mono-départ rend un seul podium — le rendu d'aujourd'hui, inchangé »."""
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    monde.departs.supprimer(monde.depart_id_2)

    rendu = _service(monde).rendu(monde.tournoi_id)

    assert len(rendu.sections) == 1
    assert rendu.sections[0].depart_id == monde.depart_id


def test_chaque_creneau_a_son_club_laureat() -> None:
    """Arbitrage du 19/09/2026 : N créneaux = N lauréats, pas un trophée agrégé (ADR-0104 amendé).

    ⚠️ Le classement des clubs **agrège** là où un podium restreint, et il désigne un **lauréat
    unique** : c'est la seule surface du produit qui nomme un vainqueur global. La juxtaposition y
    est donc un choix métier, pas une conséquence mécanique — d'où ce test à part.

    ⚠️ **Deux clubs distincts, un par créneau**, sans quoi le test resterait vert sous le raccourci
    « premier départ » : un seul club gagne partout, y compris dans un palmarès rendu deux fois.

    ⚠️ **L'assertion porte sur les blocs de podium de club, pas sur `ClassementClubs.lignes`.**
    Un décompte de médailles suppose des duels **joués** — sans eux `classer_clubs` rend zéro ligne,
    et le test aurait été vert des deux côtés du sabotage. Ce que ce test garde est donc l'entrée du
    décompte : `classer_clubs` consomme `section.complet`, dont on prouve ici qu'il ne porte que les
    clubs de **son** créneau. Le décompte lui-même est couvert en pur par
    `test_domain_classement_clubs.py`, qui n'a pas besoin d'un créneau pour cela.
    """
    monde, matin, apres_midi = _deux_creneaux_peuples()
    clubs = FauxClubRepository()
    _rattacher_a_un_club(monde, clubs, {matin[0]: "Les Archers du Matin"})
    _rattacher_a_un_club(monde, clubs, {apres_midi[0]: "La Compagnie du Soir"})
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CLUB}))
    service = _service(monde, clubs)
    service.definir_reglage_podiums(monde.tournoi_id, reglage)

    rendu = service.rendu(monde.tournoi_id)
    clubs_vus = [
        {bloc.libelle for bloc in section.complet.podiums(rendu.reglage)}
        for section in rendu.sections
    ]

    assert clubs_vus == [{"Les Archers du Matin"}, {"La Compagnie du Soir"}]


def test_un_tournoi_sans_creneau_refuse_le_palmares() -> None:
    """La garde d'aujourd'hui survit : sans créneau, il n'y a pas de classement dont tirer un
    palmarès — 409, pas une liste vide qui se lirait « personne n'a rien gagné »."""
    monde = _Monde()
    monde.departs.supprimer(monde.depart_id)
    monde.departs.supprimer(monde.depart_id_2)

    with pytest.raises(TournoiSansDepart):
        _service(monde).rendu(monde.tournoi_id)
