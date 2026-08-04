"""Tests du service `ServiceTableauxPublics` (E07US005) — repositories factices.

Ces cas dérivent du CA d'E07US005 (`stories/E07-affichage-public.md`), écrits **avant**
l'implémentation (règle 9). Le CA tient en une ligne — « rendu de l'arbre (**principal +
placement**) mis à jour en live » —, complétée par le cadrage d'intention du 04/08/2026 (deux
lectures dans l'appli publique, plus la vue `tableaux` de l'écran de salle). Ce qui en relève du
**service** :

- « principal **+ placement** » — le point du CA qui décide quelque chose ici, et qui a demandé
  **deux lectures avant d'être juste**. Première lecture : « deux **types de phase** »
  (`TypePhase.ELIMINATION_DIRECTE` et `TypePhase.PLACEMENT`, les deux membres de
  `TYPES_EN_TABLEAU`). Le test écrit sur cette lecture a **échoué**, et c'est lui qui a trouvé le
  fait : `ServiceSaisieDuels._decor` refuse tout type autre que l'élimination directe — le type
  `placement` est composable mais **pas exécutable** (`DETTE-028`). Lecture retenue, et c'est celle
  du vocabulaire des tableaux : « principal + placement » désigne les **deux branches d'un même
  arbre** — la branche des gagnants et les **sous-tableaux de placement** que `PlacementEnCascade`
  alimente sous profondeur intégrale (E06US006). Les deux lectures sont couvertes ci-dessous : ce
  qui est livrable l'est, ce qui ne l'est pas est **caractérisé** plutôt que passé sous silence ;
- ce qui n'est **pas** un tableau (qualification) n'a pas d'arbre à montrer ;
- « **live** » : la vue se relit en continu, donc la lecture est **pure** — elle ne doit rien
  écrire, sans quoi le simple fait de regarder l'écran modifierait le tournoi ;
- et la contrainte de surface, qui ne vient pas du CA mais du **contexte de la vue** : c'est un
  écran **public, projeté, sans personne devant**. Un tableau illisible (phase déclarée avant que
  la qualification l'alimente) ne doit pas emporter les autres — la page blanche est le mode de
  défaillance à éviter, comme pour l'écran de salle (E07US004).

Le monde est celui d'E04US018 (`test_service_routage._Monde`), réemployé plutôt que recopié :
c'est le **même** arbre reconstruit que lisent le routage, le pilotage et le suivi du déroulé.
"""

from __future__ import annotations

import pytest

from application.erreurs import TournoiIntrouvable
from application.tableaux_publics import ServiceTableauxPublics
from domain.bareme import BaremeQualification
from domain.phase import Phase, SourcePhase, TypePhase
from domain.politiques import ProfondeurClassement
from tests.test_service_routage import _huit, _Monde, _quatre


def _service(monde: _Monde) -> ServiceTableauxPublics:
    return ServiceTableauxPublics(monde.tournois, monde.phases, monde.saisie)


# --- CA « l'arbre (principal + placement) » -----------------------------------------------------


def test_l_arbre_rendu_porte_le_principal_et_le_placement() -> None:
    """CA : « rendu de l'arbre (**principal + placement**) ».

    « Principal » et « placement » sont les **deux branches d'un même arbre**, pas deux écrans :
    sous profondeur intégrale (E06US006), `PlacementEnCascade` fait descendre chaque perdant dans
    un **sous-tableau de placement** qui joue les rangs au-delà du podium. Ce que la vue doit donc
    rendre, c'est l'arbre **entier** — matchs des places 5-8 compris —, et non la seule branche des
    gagnants.

    C'est le point du CA qu'une lecture rapide rate : `EtatTableau.duels` les porte déjà tous, mais
    rien ne garantissait qu'un rendu ne filtre pas sur la branche principale (le suivi du déroulé,
    lui, filtre délibérément — cf. `_est_de_la_branche`, E07US004).
    """
    monde = _Monde(profondeur=ProfondeurClassement.integrale())
    _huit(monde)
    monde.placer()

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert [t.type for t in tableaux] == [TypePhase.ELIMINATION_DIRECTE]
    assert [t.ordre for t in tableaux] == [2]
    assert [t.etat.phase_id for t in tableaux] == [monde.phase_id]
    places = {duel.place_en_jeu for duel in tableaux[0].etat.duels}
    assert (1, 2) in places, "la finale du tableau principal"
    assert any(
        place is not None and place[0] > 2 for place in places
    ), "les matchs de placement (rangs au-delà du podium) doivent être rendus aussi"


def test_une_phase_de_type_placement_est_omise_tant_que_le_moteur_l_ignore() -> None:
    """`TypePhase.PLACEMENT` est **composable** (E05US015) mais **pas exécutable** : c'est
    `DETTE-028`, et `ServiceSaisieDuels._decor` refuse explicitement tout type autre que
    l'élimination directe.

    Ce test **caractérise la limite** plutôt que de la taire : la vue n'affichera rien pour une
    telle phase, et elle ne le peut pas. Le filtre du service reste `TYPES_EN_TABLEAU` (domaine) —
    donc le jour où le moteur saura monter ce type, la phase entrera dans la vue **sans toucher à
    ce service**. Si ce test se met à échouer, ce n'est pas une régression : c'est le signal que
    `DETTE-028` est résorbée et qu'il faut l'inverser.
    """
    monde = _Monde()
    _quatre(monde)
    placement = monde.phases.ajouter(
        Phase.creer(
            monde.tournoi_id,
            3,
            TypePhase.PLACEMENT,
            profondeur=ProfondeurClassement.integrale(),
        )
    )
    assert placement.id is not None

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert [t.ordre for t in tableaux] == [2]


def test_une_phase_sans_arbre_n_est_pas_rendue() -> None:
    """La qualification n'a pas d'arbre : elle n'a rien à faire dans une vue « tableaux ».

    Le filtre est `TYPES_EN_TABLEAU` (domaine) et non une liste écrite ici : c'est le quatrième
    lecteur de cette question, et la revue d'E07US004 avait déjà relevé qu'une copie locale
    finirait par diverger.
    """
    monde = _Monde()
    _quatre(monde)
    monde.phases.ajouter(Phase.qualification(monde.tournoi_id, BaremeQualification.creer(2, 3)))

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert [t.type for t in tableaux] == [TypePhase.ELIMINATION_DIRECTE]


def test_un_tournoi_sans_phase_rend_une_liste_vide_et_non_une_erreur() -> None:
    """Avant qu'un format soit appliqué, la vue doit dire « pas encore de tableau », pas casser.

    Même posture que le suivi du déroulé (E07US004) : le public ouvre l'onglet quand il veut, y
    compris à 8 h du matin.
    """
    monde = _Monde()

    assert _service(monde).pour_tournoi(monde.tournoi_id).tableaux == ()


def test_un_tournoi_inconnu_est_refuse() -> None:
    """Un identifiant inventé n'est pas un tournoi vide : la frontière API doit pouvoir répondre
    404 plutôt que d'afficher un tournoi fantôme sans tableau."""
    monde = _Monde()

    with pytest.raises(TournoiIntrouvable):
        _service(monde).pour_tournoi(404)


# --- CA « mis à jour en live » ------------------------------------------------------------------


def test_l_arbre_rendu_porte_le_vainqueur_acquis_et_le_match_suivant() -> None:
    """CA « **live** » : ce que la vue montre doit **bouger** quand un duel est validé.

    La progression ne vient pas d'un mécanisme de rafraîchissement (c'est l'affaire du transport)
    mais de la **lecture** : l'arbre est reconstruit à chaque appel (ADR-0023), donc le vainqueur
    validé occupe déjà le match du tour suivant. C'est ce que ce test vérifie — sans quoi la vue
    afficherait un arbre figé quel que soit le rafraîchissement.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()
    vainqueur = monde.gagne_de(1)
    monde.gagner(1)

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert len(tableaux) == 1
    duels = {duel.numero: duel for duel in tableaux[0].etat.duels}
    joue = duels[1]
    assert joue.duel is not None and joue.duel.verrouille
    occupants = [
        duel.numero
        for duel in tableaux[0].etat.duels
        if duel.tour == 2
        and vainqueur in {d.archer_id for d in (duel.haut, duel.bas) if d is not None}
    ]
    assert occupants, "le vainqueur validé doit occuper un match du tour suivant"


def test_le_podium_acquis_est_rendu() -> None:
    """Le tableau ne se lit pas seulement match par match : ce que le public attend en fin de
    phase, c'est **qui a gagné**. Le podium acquis fait donc partie de la photo rendue."""
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    for numero in (1, 2):
        monde.gagner(numero)
    for numero in (3, 4):
        monde.gagner(numero)

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert tableaux[0].etat.est_termine
    assert [rang for rang, _ in tableaux[0].etat.podium] == [1, 2, 3, 4]


def test_la_lecture_est_pure() -> None:
    """CA « live » ⇒ la vue est relue en continu, par autant d'appareils qu'il y a de spectateurs.

    Si la lecture écrivait quoi que ce soit, regarder l'écran modifierait le tournoi — et le
    modifierait d'autant plus qu'il y a du monde. Même exigence que le routage (`D-08`).
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()
    monde.gagner(1)
    avant = (
        dict(monde.duels._tirs),
        dict(monde.placements._plan),
        list(monde.series._series),
    )

    _service(monde).pour_tournoi(monde.tournoi_id)

    assert dict(monde.duels._tirs) == avant[0]
    assert dict(monde.placements._plan) == avant[1]
    assert list(monde.series._series) == avant[2]


# --- Surface publique : un arbre illisible n'emporte pas les autres ------------------------------


def test_un_tableau_illisible_est_omis_sans_emporter_les_autres() -> None:
    """Une phase de tableau **déclarée mais pas encore alimentée** ne peut pas être reconstruite :
    un tableau demande au moins deux participants (`EffectifTableauInvalide`), et un prélèvement
    sur des rangs que le tournoi n'a pas encore n'en rend aucun.

    Le cas est celui du matin : le déroulé est composé pour 8 archers, 4 ont tiré, la phase de
    placement prélève les rangs 5-8. Sur une surface publique et projetée, la faire remonter en
    erreur donnerait une **page blanche** pour tout le monde à cause d'une phase à venir. On
    l'omet donc, et les tableaux lisibles restent lisibles. C'est la posture d'E07US004 (« un écran
    figé ne se plaint pas », donc on ne le fige pas pour une raison évitable), pas un `except` de
    confort.
    """
    monde = _Monde()
    _quatre(monde)
    monde.phases.ajouter(Phase.qualification(monde.tournoi_id, BaremeQualification.creer(2, 3)))
    a_venir = monde.phases.ajouter(
        Phase.creer(
            monde.tournoi_id,
            3,
            TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase(ordre_source=1, rang_debut=5, rang_fin=8),),
        )
    )
    assert a_venir.id is not None

    tableaux = _service(monde).pour_tournoi(monde.tournoi_id).tableaux

    assert [t.ordre for t in tableaux] == [2]
