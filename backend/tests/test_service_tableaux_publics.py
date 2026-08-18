"""Tests du service `ServiceTableauxPublics` (E07US005) — repositories factices.

Ces cas dérivent du CA d'E07US005 (`stories/E07-affichage-public.md`), écrits **avant**
l'implémentation (règle 9). Le CA tient en une ligne — « rendu de l'arbre (**principal +
placement**) mis à jour en live » —, complétée par le cadrage d'intention du 04/08/2026 (deux
lectures dans l'appli publique, plus la vue `en_cours` de l'écran de salle). Ce qui en relève du
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

from application.erreurs import DepartIntrouvable
from application.saisie_duels import EtatTableau
from application.tableaux_publics import ServiceTableauxPublics, TableauPublic
from domain.bareme import BaremeQualification
from domain.phase import Phase, SourcePhase, TypePhase
from domain.politiques import ProfondeurClassement
from tests.conftest import poser_phase_factice
from tests.test_service_routage import _huit, _Monde, _quatre


def _etat(tableau: TableauPublic) -> EtatTableau:
    """L'arbre d'un tableau public, dont ces tests supposent qu'il est **monté**.

    `TableauPublic.etat` est facultatif depuis E05US024 : une phase peut être **en attente** de sa
    phase source, qui n'a pas encore attribué les places qu'elle prélève (ADR-0081). Les tests de ce
    module ne décrivent que des tableaux montables ; passer par ce helper garde l'assertion à un
    seul endroit au lieu de la répéter à chaque accès.
    """
    assert tableau.etat is not None
    return tableau.etat


def _service(monde: _Monde) -> ServiceTableauxPublics:
    return ServiceTableauxPublics(monde.departs, monde.phases, monde.saisie)


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

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert [t.type for t in tableaux] == [TypePhase.ELIMINATION_DIRECTE]
    assert [t.ordre for t in tableaux] == [2]
    assert [_etat(t).phase_id for t in tableaux] == [monde.phase_id]
    places = {duel.place_en_jeu for duel in _etat(tableaux[0]).duels}
    assert (1, 2) in places, "la finale du tableau principal"
    # Les paires **nommées**, et non `place[0] > 2` : ce prédicat était satisfait par la petite
    # finale `(3, 4)`, qui existe déjà en profondeur podium — le test passait donc à l'identique
    # sans `integrale()` et ne prouvait pas le point du CA qu'il annonce (relevé en revue). Le
    # miroir ci-dessous complète la démonstration : sans profondeur intégrale, ces paires sont
    # absentes.
    assert {(5, 6), (7, 8)} <= places, "les matchs de placement (rangs 5→8) doivent être rendus"


def test_sans_profondeur_integrale_il_n_y_a_pas_de_match_de_placement() -> None:
    """Miroir du test ci-dessus — c'est **le couple** qui prouve, pas l'assertion seule.

    En profondeur `podium` (le défaut), le tournoi ne dispute que les rangs 1 à 4 : les places 5-8
    ne se jouent pas, elles restent *ex æquo*. Sans ce test, une assertion satisfaite par la petite
    finale laisserait croire que le placement est couvert alors qu'il ne l'est pas.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    places = {duel.place_en_jeu for duel in _etat(tableaux[0]).duels}
    assert (1, 2) in places and (3, 4) in places
    assert not ({(5, 6), (7, 8)} & places)


def test_un_match_de_placement_non_terminal_ne_se_nomme_pas_comme_une_demi_finale() -> None:
    """**Le défaut trouvé en revue, figé ici.**

    `place_en_jeu` n'est renseigné que sur les matchs **terminaux** (`domain/tableau.py`). Un match
    du sous-tableau des places 5-8 se dispute donc au **même tour** qu'une demi-finale **sans aucun
    champ qui l'en distingue** — et tout consommateur qui le nommait par son numéro de tour
    l'appelait « Demi-finale ». C'est ce que lisait l'archer sorti en quart, sur la vue publique.

    Le libellé vient désormais du domaine et s'appuie sur la **plage** (`Match.plage`), disponible
    dès le premier tour. Ce test vaut pour toutes les surfaces : le routage lit le même libellé.
    """
    monde = _Monde(profondeur=ProfondeurClassement.integrale())
    _huit(monde)
    monde.placer()

    duels = _etat(_service(monde).pour_depart(monde.depart_id).tableaux[0]).duels
    par_libelle = {duel.numero: (duel.libelle, duel.plage) for duel in duels if duel.tour == 2}

    demies = [num for num, (lib, _) in par_libelle.items() if lib == "Demi-finale"]
    placement = [num for num, (lib, _) in par_libelle.items() if lib == "Places 5 à 8"]
    assert len(demies) == 2, f"le tour 2 porte deux demi-finales, pas {len(demies)}"
    assert len(placement) == 2, "les matchs des places 5-8 se nomment par leurs rangs"
    assert all(par_libelle[num][1] == (5, 8) for num in placement)


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
    placement = poser_phase_factice(
        monde.departs,
        monde.deroules,
        monde.phases,
        Phase.creer(
            monde.depart_id,
            3,
            TypePhase.PLACEMENT,
            profondeur=ProfondeurClassement.integrale(),
        ),
    )
    assert placement.id is not None

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert [t.ordre for t in tableaux] == [2]


def test_une_phase_sans_arbre_n_est_pas_rendue() -> None:
    """La qualification n'a pas d'arbre : elle n'a rien à faire dans une vue « tableaux ».

    Le filtre est `TYPES_EN_TABLEAU` (domaine) et non une liste écrite ici : c'est le quatrième
    lecteur de cette question, et la revue d'E07US004 avait déjà relevé qu'une copie locale
    finirait par diverger.
    """
    monde = _Monde()
    _quatre(monde)
    poser_phase_factice(
        monde.departs,
        monde.deroules,
        monde.phases,
        Phase.qualification(monde.depart_id, BaremeQualification.creer(2, 3)),
    )

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert [t.type for t in tableaux] == [TypePhase.ELIMINATION_DIRECTE]


def test_un_tournoi_sans_phase_rend_une_liste_vide_et_non_une_erreur() -> None:
    """Avant qu'un format soit appliqué, la vue doit dire « pas encore de tableau », pas casser.

    Même posture que le suivi du déroulé (E07US004) : le public ouvre l'onglet quand il veut, y
    compris à 8 h du matin.
    """
    monde = _Monde()

    assert _service(monde).pour_depart(monde.depart_id).tableaux == ()


def test_un_creneau_inconnu_est_refuse() -> None:
    """Un identifiant inventé n'est pas un créneau vide : la frontière API doit pouvoir répondre
    404 plutôt que d'afficher un créneau fantôme sans tableau."""
    monde = _Monde()

    with pytest.raises(DepartIntrouvable):
        _service(monde).pour_depart(404)


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

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert len(tableaux) == 1
    duels = {duel.numero: duel for duel in _etat(tableaux[0]).duels}
    joue = duels[1]
    assert joue.duel is not None and joue.duel.verrouille
    occupants = [
        duel.numero
        for duel in _etat(tableaux[0]).duels
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

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert _etat(tableaux[0]).est_termine
    assert [rang for rang, _ in _etat(tableaux[0]).podium] == [1, 2, 3, 4]


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

    _service(monde).pour_depart(monde.depart_id)

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
    poser_phase_factice(
        monde.departs,
        monde.deroules,
        monde.phases,
        Phase.qualification(monde.depart_id, BaremeQualification.creer(2, 3)),
    )
    a_venir = poser_phase_factice(
        monde.departs,
        monde.deroules,
        monde.phases,
        Phase.creer(
            monde.depart_id,
            3,
            TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase(ordre_source=1, rang_debut=5, rang_fin=8),),
        ),
    )
    assert a_venir.id is not None

    tableaux = _service(monde).pour_depart(monde.depart_id).tableaux

    assert [t.ordre for t in tableaux] == [2]


# --- Portée : les arbres sont ceux d'un créneau (ADR-0075) ---------------------------------------


def test_les_arbres_rendus_sont_ceux_du_creneau_interroge() -> None:
    """**La garde de portée.** Deux créneaux, chacun son tableau de rang 2 : chaque appel n'en voit
    qu'un.

    À la maille tournoi, `par_tournoi` concaténait les deux et la réponse portait **deux** entrées
    d'`ordre` 2 — indiscernables, puisque `TableauPublic` ne porte pas de `depart_id`. Le
    spectateur voyait l'arbre du matin sous l'onglet de l'après-midi, sans rien pour s'en douter.
    """
    monde = _Monde()
    _quatre(monde)
    matin = monde.phase_id
    assert matin is not None
    _quatre(monde, depart_id=monde.depart_id_2)
    apres_midi = monde.phase_id
    assert apres_midi is not None and apres_midi != matin

    vus_le_matin = _service(monde).pour_depart(monde.depart_id).tableaux
    vus_l_apres_midi = _service(monde).pour_depart(monde.depart_id_2).tableaux

    assert [t.phase_id for t in vus_le_matin] == [matin]
    assert [t.phase_id for t in vus_l_apres_midi] == [apres_midi]
