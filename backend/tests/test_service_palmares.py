"""Tests du service `ServicePalmares` (E06US004) — repositories factices.

Le service **compose** ce que le domaine sait faire : il reconstruit chaque phase à tableau (via
`ServiceSaisieDuels.reconstruire`, comme le routage et le pilotage), en lit les positions acquises
(`Tableau.positions_acquises`) et confie la fusion à `domain/palmares.py`. Ce qui se teste ici est
donc la **composition** — que le palmarès dise vraiment ce que le tournoi a produit —, la règle de
fusion étant couverte en pur dans `test_domain_palmares.py`.

Cas dérivés du CA d'E06US004 (`stories/E06-classements.md`), écrits **avant** l'implémentation
(règle 9) :

- **CA podium** : « rangs 1-4 issus de la finale/petite finale » — sur un vrai tableau joué ;
- **CA agrégation** : « rangs des différentes phases fusionnés en un classement cohérent par
  catégorie » — les duellistes devant, les non-qualifiés dans l'ordre de la qualification ;
- **arbitrage du 03/08/2026** : les sortis au même tour sont départagés par une politique
  injectable, `AggregationParQualification` par défaut.

Le décor est celui d'E07US008 (`_Monde`) : mêmes services sur repositories en mémoire, classement
**vrai** sur des séries semées. Le réutiliser plutôt que d'en monter un second garantit que le
palmarès lit exactement le tournoi que le routage et le pilotage lisent.
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import TournoiIntrouvable
from application.palmares import ServicePalmares
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.classement import StatutClassement
from domain.forfait import Forfait, NatureForfait
from domain.inscription import Inscription
from domain.palmares import OriginePalmares, Palmares
from domain.phase import Phase
from domain.politiques import (
    Aggregation,
    AggregationExAequo,
    AggregationParQualification,
    ProfondeurClassement,
)
from tests.conftest import poser_phase_factice
from tests.test_service_routage import _Monde

_QUAND = datetime.datetime(2026, 3, 14, 14, 20, tzinfo=datetime.UTC)


def _monde_de_quatre() -> tuple[_Monde, list[int]]:
    """Quatre archers semés du meilleur au moins bon, une phase de tableau, le plan posé."""
    monde = _Monde()
    archers = [
        monde.inscrire_classe(("10", "10", "10")),
        monde.inscrire_classe(("10", "10", "9")),
        monde.inscrire_classe(("10", "9", "9")),
        monde.inscrire_classe(("9", "9", "9")),
    ]
    monde.creer_phase_tableau()
    monde.placer()
    return monde, archers


def _monde_de_huit() -> tuple[_Monde, list[int]]:
    """Huit archers semés du meilleur au moins bon — l'effectif où l'ex æquo **définitif** existe.

    Sous `ProfondeurPodium`, la profondeur élague le sous-tableau des rangs 5-8 : les quatre battus
    des quarts n'ont plus aucun match, donc plus rien ne les départagera. À quatre archers, ils
    descendraient en petite finale et le cas ne se présenterait pas.
    """
    monde = _Monde(capacites=(4, 4, 4, 4))
    # Totaux strictement décroissants (30 → 23) : le classement de qualification est donc exactement
    # l'ordre de cette liste, sans ex æquo à départager, et `archers.index` vaut rang de qualif - 1.
    archers = [
        monde.inscrire_classe(valeurs)
        for valeurs in (
            ("10", "10", "10"),
            ("10", "10", "9"),
            ("10", "9", "9"),
            ("9", "9", "9"),
            ("9", "9", "8"),
            ("9", "8", "8"),
            ("8", "8", "8"),
            ("8", "8", "7"),
        )
    ]
    monde.creer_phase_tableau()
    monde.placer()
    return monde, archers


def _abandonner_en_qualification(monde: _Monde, archer_id: int) -> None:
    """Déclare un abandon **en qualification** : l'archer est relégué au classement (ADR-0050) et
    n'entre donc pas au tableau (`_decor` n'ensemence que les archers en lice).

    Il faut une phase de qualification pour cela — `ServiceClassement` filtre les forfaits par
    phase, un forfait déclaré en duels ne reléguant pas le rang de qualif.
    """
    # La qualification pend au **créneau** (ADR-0075) : posée sur `tournoi_id`, elle était
    # orpheline — l'assemblage l'écartait, et le forfait ne reléguait plus personne.
    phase = poser_phase_factice(
        monde.departs,
        monde.deroules,
        monde.phases,
        Phase.qualification(monde.depart_id, BaremeQualification.creer(1, 3)),
    )
    assert phase.id is not None
    monde.forfaits.semer(
        Forfait.creer(
            tournoi_id=monde.tournoi_id,
            archer_id=archer_id,
            phase_id=phase.id,
            nature=NatureForfait.ABANDON,
            declare_par="DURAND",
            declare_le=_QUAND,
        )
    )


class _FauxGenerateurPalmares:
    """Double du port `GenerateurPalmares` : retient le dernier appel, ne rend rien de réel.

    Le rendu ReportLab est couvert par les tests d'API (document non vide, `%PDF`) ; ici on ne
    vérifie que **ce que le service lui donne** — c'est la seule chose dont il soit responsable.
    """

    def __init__(self) -> None:
        self.appels: list[tuple[str, Palmares]] = []

    def palmares(self, tournoi: str, palmares: Palmares) -> bytes:
        self.appels.append((tournoi, palmares))
        return b"%PDF-faux"


def _service(
    monde: _Monde,
    generateur: _FauxGenerateurPalmares | None = None,
    aggregation: Aggregation | None = None,
) -> ServicePalmares:
    return ServicePalmares(
        monde.tournois,
        monde.phases,
        monde._classement(),
        monde.saisie,
        monde.duels,
        generateur or _FauxGenerateurPalmares(),
        monde.departs,
        aggregation,
    )


def _rangs(
    monde: _Monde, aggregation: Aggregation | None = None
) -> list[tuple[int, int | None, int | None]]:
    palmares = _service(monde, aggregation=aggregation).pour_tournoi(monde.tournoi_id)
    return [(ligne.archer_id, ligne.rang_min, ligne.rang_max) for ligne in palmares.lignes]


# --- gardes --------------------------------------------------------------------------------------


def test_tournoi_inconnu_refuse() -> None:
    """Même garde que les autres lectures : 404 à la frontière, pas un palmarès vide."""
    monde, _ = _monde_de_quatre()

    with pytest.raises(TournoiIntrouvable):
        _service(monde).pour_tournoi(999)


def test_sans_phase_de_tableau_le_palmares_est_celui_de_la_qualification() -> None:
    """Un tournoi qui n'a pas encore de duels a déjà un palmarès : son classement de qualification.

    C'est le cas de **toute la matinée** du jour J — l'écran ne doit pas rester vide en attendant
    la première finale.
    """
    monde = _Monde()
    attendus = [
        monde.inscrire_classe(("10", "10", "10")),
        monde.inscrire_classe(("9", "9", "9")),
    ]

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert [ligne.archer_id for ligne in palmares.lignes] == attendus
    assert all(ligne.origine is OriginePalmares.QUALIFICATION for ligne in palmares.lignes)


# --- CA « podium » -------------------------------------------------------------------------------


def test_le_podium_sort_des_matchs_terminaux_du_tableau() -> None:
    """CA podium : les rangs 1-4 sont ceux de la finale et de la petite finale.

    Le décor fait gagner le camp **haut** de chaque match : au tour 1, le mieux classé ; en finale
    et en petite finale, celui que l'arbre a mis en haut. Les rangs du palmarès doivent donc être
    ceux du tableau, et non ceux de la qualification — c'est tout l'objet du CA.
    """
    monde, _ = _monde_de_quatre()
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)
    tableau, _lignes = monde.saisie.reconstruire(monde.tournoi_id, monde.phase_id or 0)
    attendus = [place.participant.ref_id for place in tableau.podium()]

    podium = palmares.podium(monde.categorie_id)
    assert [ligne.archer_id for ligne in podium] == attendus
    assert [ligne.rang_min for ligne in podium] == [1, 2, 3, 4]
    assert all(ligne.origine is OriginePalmares.DUELS for ligne in podium)
    assert all(ligne.decerne for ligne in podium)


def test_le_podium_se_publie_des_la_petite_finale_sans_attendre_la_finale() -> None:
    """La petite finale se tire couramment **avant** la finale (le bronze avant l'or, usage en
    salle). Les rangs 3-4 se publient donc dès qu'elle est tranchée — la garde inverse priverait
    l'écran du podium pendant tout l'intervalle (régression rattrapée en revue d'E05US005)."""
    monde, _ = _monde_de_quatre()
    for numero in (1, 2):
        monde.gagner(numero)
    monde.gagner(4)  # la petite finale, avant la finale

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert [ligne.rang_min for ligne in palmares.podium(monde.categorie_id)] == [3, 4]


# --- CA « agrégation » ---------------------------------------------------------------------------


def test_les_duellistes_precedent_les_archers_restes_en_qualification() -> None:
    """CA agrégation : la fusion place le tableau devant, la qualification derrière.

    Un forfait d'abandon déclaré en qualification n'entre pas au tableau (`_decor` n'ensemence que
    les archers en lice) : il fournit ici, sans artifice, l'archer « resté en qualification » que
    le palmarès doit ranger **après** les quatre duellistes.
    """
    monde, archers = _monde_de_quatre()
    _abandonner_en_qualification(monde, archers[0])

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert palmares.lignes[-1].archer_id == archers[0]
    assert palmares.lignes[-1].statut is StatutClassement.ABANDON
    assert palmares.lignes[-1].origine is OriginePalmares.QUALIFICATION


def test_un_archer_encore_en_lice_n_est_pas_range_derriere_les_elimines() -> None:
    """Le palmarès se consulte **pendant** le tournoi : un demi-finaliste est au pire 4ᵉ, donc
    devant les battus du 1ᵉʳ tour. Le classer sur son rang de qualification le ferait tomber
    derrière des archers qu'il vient de battre."""
    monde, _ = _monde_de_quatre()
    monde.gagner(1)
    monde.gagner(2)

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)
    finalistes = {monde.gagne_de(1), monde.gagne_de(2)}

    assert {ligne.archer_id for ligne in palmares.lignes[:2]} == finalistes
    assert all(ligne.rang_max == 2 for ligne in palmares.lignes[:2])


# --- arbitrage : politique de départage injectable -----------------------------------------------


def test_les_sortis_au_meme_tour_sont_departages_par_la_qualification_par_defaut() -> None:
    """Politique par défaut : les quatre battus des quarts sont ex æquo 5ᵉ-8ᵉ ; leur rang de
    qualification les départage, et ils prennent les rangs 5, 6, 7 et 8 dans cet ordre.

    Le décor tronque au podium (`ProfondeurPodium`) : le sous-tableau des rangs 5-8 est élagué,
    donc **aucun match** ne départagera jamais ces quatre-là. C'est exactement le trou qu'ADR-0065
    avait laissé ouvert en refusant d'inventer un rang dans le routage.
    """
    monde, archers = _monde_de_huit()
    battus = [monde.perd_de(numero) for numero in (1, 2, 3, 4)]
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)

    rangs = {
        ligne.archer_id: (ligne.rang_min, ligne.rang_max)
        for ligne in _service(monde).pour_tournoi(monde.tournoi_id).lignes
    }
    attendus = sorted(battus, key=archers.index)

    assert [rangs[archer_id] for archer_id in attendus] == [(5, 5), (6, 6), (7, 7), (8, 8)]


def test_la_politique_ex_aequo_est_injectable() -> None:
    """La même situation, avec `AggregationExAequo` : les deux battus restent 3ᵉ-4ᵉ tous les deux.

    C'est ce que l'arbitrage du 03/08/2026 demandait — la règle de départage est une **politique**
    (règle 2), pas une décision figée dans le service.
    """
    monde, _ = _monde_de_huit()
    battus = [monde.perd_de(numero) for numero in (1, 2, 3, 4)]
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)

    rangs = {
        ligne.archer_id: (ligne.rang_min, ligne.rang_max)
        for ligne in _service(monde, aggregation=AggregationExAequo())
        .pour_tournoi(monde.tournoi_id)
        .lignes
    }

    assert [rangs[archer_id] for archer_id in battus] == [(5, 8)] * 4


def test_la_politique_par_defaut_est_le_departage_par_la_qualification() -> None:
    """Le défaut n'est pas implicite : câblé ou non, le service se comporte pareil."""
    monde, _ = _monde_de_huit()
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)

    assert _rangs(monde) == _rangs(monde, aggregation=AggregationParQualification())


# --- filtrage par catégorie ----------------------------------------------------------------------


def test_le_filtre_par_categorie_restreint_l_affichage_sans_renumeroter() -> None:
    """Comme le classement de qualification (E06US001) : on voit une catégorie sans perdre la
    position d'ensemble. Le décor n'a qu'une catégorie — le filtre doit donc tout rendre, et une
    catégorie inconnue ne rien rendre, sans lever.

    Sans phase de tableau : les rangs sont alors ceux de la qualification, ce qui rend l'effet du
    **filtre** lisible sans le mêler à celui des duels.
    """
    monde = _Monde()
    archers = [
        monde.inscrire_classe(("10", "10", "10")),
        monde.inscrire_classe(("10", "10", "9")),
        monde.inscrire_classe(("9", "9", "9")),
    ]

    tout = _service(monde).pour_tournoi(monde.tournoi_id)
    filtre = _service(monde).pour_tournoi(monde.tournoi_id, categorie_id=monde.categorie_id)
    autre = _service(monde).pour_tournoi(monde.tournoi_id, categorie_id=999)

    assert [ligne.archer_id for ligne in filtre.lignes] == [
        ligne.archer_id for ligne in tout.lignes
    ]
    assert [ligne.rang_min for ligne in filtre.lignes] == list(range(1, len(archers) + 1))
    assert autre.lignes == ()


# --- CA « exportable » ---------------------------------------------------------------------------


def test_l_export_pdf_recoit_exactement_le_palmares_affiche() -> None:
    """CA « affiché et exportable » : le document part du **même** calcul que l'écran.

    Un PDF qui recalculerait de son côté finirait par diverger de l'affichage — et c'est celui-là
    qu'on colle au mur. On vérifie donc que le port reçoit le palmarès rendu par `pour_tournoi`,
    et le nom du tournoi pour l'en-tête.
    """
    monde, _ = _monde_de_quatre()
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)
    generateur = _FauxGenerateurPalmares()

    document = _service(monde, generateur).imprimer(monde.tournoi_id)

    assert document == b"%PDF-faux"
    ((tournoi, palmares),) = generateur.appels
    attendu = monde.tournois.par_id(monde.tournoi_id)
    assert attendu is not None
    assert tournoi == attendu.nom
    assert palmares == _service(monde).pour_tournoi(monde.tournoi_id)


def test_l_export_pdf_refuse_un_tournoi_inconnu() -> None:
    """Même garde que la lecture : 404 avant d'appeler le générateur."""
    monde, _ = _monde_de_quatre()
    generateur = _FauxGenerateurPalmares()

    with pytest.raises(TournoiIntrouvable):
        _service(monde, generateur).imprimer(999)

    assert generateur.appels == []


def test_l_export_pdf_honore_le_filtre_de_categorie() -> None:
    """Imprimer le palmarès d'une catégorie n'imprime que ses lignes — le geste de l'organisateur
    qui affiche un document par catégorie près de son podium."""
    monde, _ = _monde_de_quatre()
    generateur = _FauxGenerateurPalmares()

    _service(monde, generateur).imprimer(monde.tournoi_id, categorie_id=999)

    ((_tournoi, palmares),) = generateur.appels
    assert palmares.lignes == ()


def test_une_phase_sans_duel_tranche_ne_pese_pas_sur_le_palmares() -> None:
    """Le déroulé se compose **à l'avance** (E01US024) : la phase de tableau existe dès le matin.

    Sans garde, `_decor` l'ensemençait avec tous les archers en lice et chacun n'avait acquis que
    la plage de son premier match — le tableau entier. Le palmarès affichait « 1ᵉʳ-Nᵉ · à
    départager » sur **toutes** ses lignes, pendant toute la qualification, sur l'onglet public et
    l'écran de salle (défaut trouvé en revue par trois axes).

    Attendu : tant qu'aucun duel n'est tranché, le palmarès **est** le classement de qualification.
    """
    monde, archers = _monde_de_quatre()

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert [ligne.archer_id for ligne in palmares.lignes] == archers
    assert [ligne.rang_min for ligne in palmares.lignes] == [1, 2, 3, 4]
    assert all(ligne.origine is OriginePalmares.QUALIFICATION for ligne in palmares.lignes)
    assert palmares.podium(monde.categorie_id) == ()


def test_le_premier_duel_tranche_fait_basculer_le_palmares_sur_le_tableau() -> None:
    """Le pendant du test précédent : la bascule se fait sur **ce que le tableau a décidé**, et non
    sur le statut de la phase — que l'organisateur passe à la main et peut oublier.

    Après un seul duel validé, le battu sort sur sa fourchette et tous les autres restent devant
    lui, y compris ceux qui n'ont pas encore tiré : ils sont toujours en course pour la première
    place.
    """
    monde, _ = _monde_de_quatre()
    monde.gagner(1)

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)
    battu = monde.perd_de(1)

    assert palmares.lignes[-1].archer_id == battu
    assert all(ligne.origine is OriginePalmares.DUELS for ligne in palmares.lignes)


# --- CA « podium » : la petite finale est un réglage du moteur de phases -------------------------


def test_sans_petite_finale_le_bronze_n_est_pas_gagne_au_tir() -> None:
    """**Le match pour la 3ᵉ place est un paramètre du moteur** — la politique `depth` (ADR-0004).

    `ProfondeurPodium(jusqu_au=4)`, le défaut câblé en production, dispute la finale **et** la
    petite finale : le bronze est gagné au tir. `jusqu_au=2` ne dispute que la finale — plus aucun
    match ne départage les deux battus des demies, que la politique `aggregation` range alors sur
    leur qualification.

    C'est là que se voit la distinction **classement / podium** (arbitrage du 03/08/2026) : les
    quatre archers ont une place, mais seules les deux premières ont été **gagnées**. Le drapeau
    `decerne` porte la différence, et l'écran comme le PDF l'affichent.
    """
    monde = _Monde(profondeur=ProfondeurClassement.top(2))
    for valeurs in (("10", "10", "10"), ("10", "10", "9"), ("10", "9", "9"), ("9", "9", "9")):
        monde.inscrire_classe(valeurs)
    monde.creer_phase_tableau()
    monde.placer()
    for numero in (1, 2, 3):
        monde.gagner(numero)

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)
    podium = palmares.podium(monde.categorie_id)

    assert [ligne.rang_categorie_min for ligne in podium] == [1, 2, 3, 4]
    assert [ligne.decerne for ligne in podium] == [True, True, False, False]


def test_avec_petite_finale_le_bronze_est_decerne() -> None:
    """Le pendant : au défaut du moteur (`jusqu_au=4`), la petite finale se tire et le bronze est
    bien décerné. Deux tests pour un seul réglage — c'est le réglage qui est l'objet du test."""
    monde, _ = _monde_de_quatre()
    for numero in (1, 2, 3, 4):
        monde.gagner(numero)

    podium = _service(monde).pour_tournoi(monde.tournoi_id).podium(monde.categorie_id)

    assert [ligne.rang_min for ligne in podium] == [1, 2, 3, 4]
    assert all(ligne.decerne for ligne in podium)


def test_un_forfait_avant_tout_duel_ne_fait_pas_basculer_le_palmares() -> None:
    """Un **walkover de forfait** avance l'arbre sans qu'une flèche soit tirée (ADR-0050).

    Le premier critère (« un match a un vainqueur hors bye ») le prenait pour un duel joué et
    rouvrait la régression « 1ᵉʳ-Nᵉ sur toutes les lignes » — sur un geste que le produit
    encourage : l'archer qui prévient le matin qu'il ne restera pas pour les duels. D'où le
    critère « un **tir** enregistré » (contre-revue, axe C1).
    """
    monde, archers = _monde_de_quatre()
    assert monde.phase_id is not None
    monde.forfaits.semer(
        Forfait.creer(
            tournoi_id=monde.tournoi_id,
            archer_id=archers[3],
            phase_id=monde.phase_id,
            nature=NatureForfait.ABANDON,
            declare_par="DURAND",
            declare_le=_QUAND,
        )
    )

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert [ligne.rang_min for ligne in palmares.lignes] == [1, 2, 3, 4]
    assert all(ligne.origine is OriginePalmares.QUALIFICATION for ligne in palmares.lignes)


def test_le_rang_de_categorie_reste_borne_par_la_categorie() -> None:
    """Un rang de catégorie ne sort **jamais** de l'effectif de sa catégorie.

    La fourchette acquise (« 1ᵉʳ-8ᵉ ») est exprimée dans l'espace de rangs du **tournoi** : la
    rendre telle quelle comme rang de catégorie annonçait « 1ᵉʳ-8ᵉ » à une catégorie de deux
    archers, et faisait chevaucher un rang ouvert avec un rang décerné. Relevé par trois axes en
    contre-revue — c'était une régression de mon propre correctif.
    """
    monde = _Monde()
    autre = monde.categories.ajouter(
        Categorie.creer(monde.tournoi_id, "Cat2", arme="Arc Classique", blason_id=1, hauteur_cm=130)
    )
    assert autre.id is not None
    archers = [monde.inscrire_classe(v) for v in (("10", "10", "10"), ("10", "10", "9"))]
    for valeurs in (("10", "9", "9"), ("9", "9", "9")):
        archer = monde.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=monde.tournoi_id, categorie_id=autre.id)
        )
        assert archer.id is not None
        monde.inscriptions.ajouter(Inscription(archer_id=archer.id, depart_id=monde.depart_id))
        monde.series.semer(monde.tournoi_id, archer.id, tuple(ZoneScore(v) for v in valeurs))
        archers.append(archer.id)
    monde.creer_phase_tableau()
    monde.placer()
    monde.gagner(1)

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    par_categorie: dict[int, int] = {}
    for ligne in palmares.lignes:
        par_categorie[ligne.categorie_id] = par_categorie.get(ligne.categorie_id, 0) + 1
    for ligne in palmares.lignes:
        assert ligne.rang_categorie_max is not None
        assert ligne.rang_categorie_max <= par_categorie[ligne.categorie_id]


def test_un_bye_resolu_ne_fait_pas_basculer_le_palmares() -> None:
    """Un **bye** avance un archer sans qu'une flèche soit tirée (effectif ≠ puissance de 2).

    Les deux tests de bascule tournaient sur un tableau de 4, **sans aucun bye** : la clause
    `not match.est_bye` n'était donc jamais exercée, alors qu'elle est le cœur du correctif et que
    le cas est le plus courant en salle. Ici, six archers (tableau de 8, deux byes) et un tir
    **saisi mais non validé** — le tableau s'est avancé tout seul, rien n'est tranché.
    """
    monde = _Monde(capacites=(4, 4))
    for valeurs in (
        ("10", "10", "10"),
        ("10", "10", "9"),
        ("10", "9", "9"),
        ("9", "9", "9"),
        ("9", "9", "8"),
        ("9", "8", "8"),
    ):
        monde.inscrire_classe(valeurs)
    monde.creer_phase_tableau()
    monde.placer()
    assert monde.phase_id is not None
    numero = next(
        m.numero for m in monde.saisie.reconstruire(1, monde.phase_id)[0].matchs if m.est_jouable
    )
    monde.saisie.saisir_manche(
        monde.tournoi_id, monde.phase_id, numero, 1, (ZoneScore.DIX,) * 3, (ZoneScore.SIX,) * 3
    )

    palmares = _service(monde).pour_tournoi(monde.tournoi_id)

    assert all(ligne.origine is OriginePalmares.QUALIFICATION for ligne in palmares.lignes)
    assert [ligne.rang_min for ligne in palmares.lignes] == [1, 2, 3, 4, 5, 6]
