"""E05US024 — un prélèvement lit le classement de **sa** phase source.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US024), écrits **avant**
l'implémentation : ce qu'ils décrivent est la règle voulue, pas le code livré (règle 9).

Le défaut qu'ils ferment : jusqu'ici `application/prelevement.py` ne lisait qu'**un** classement,
celui de la qualification, et tout prélèvement visant une autre phase était **ignoré en silence** —
la phase recevait alors *tous* les archers en lice. Un tableau bien formé, plausible, et faux.

**Le décor discriminant.** Avec quatre archers classés 1-2-3-4 en qualification, l'ensemencement
serpent oppose 1 à 4 et 2 à 3. On fait gagner les **mal classés** : le tableau amont rend donc
`4ᵉ, 3ᵉ` en tête, exactement l'inverse de la qualification. « Les rangs 1 à 2 de la phase 2 » ne
peut alors pas être confondu avec « les rangs 1 à 2 de la phase 1 » — c'est ce qui rend ces tests
capables d'échouer.
"""

from __future__ import annotations

from dataclasses import replace

from domain.classement import Classement, LigneClassement
from domain.phase import Phase, PhaseId, SourcePhase, TypePhase
from tests.test_service_saisie_duels import _gagner_manches, _Monde


def _monde_a_deux_tableaux(nb: int = 4) -> tuple[_Monde, PhaseId]:
    """Le décor de l'US : qualification (ordre 1), tableau amont (ordre 2), tableau aval (ordre 3).

    `_Monde` monte déjà la qualification et **un** tableau ; on ajoute celui qui prélèvera dans
    l'autre. C'est la cascade la plus courte qui exerce la règle.
    """
    monde = _Monde()
    for rang in range(nb):
        monde.inscrire_classe(("10", "10", str(max(1, 10 - rang))))
    aval = monde.phases.ajouter(Phase.creer(monde.depart_id, 3, TypePhase.ELIMINATION_DIRECTE))
    assert aval.id is not None
    return monde, aval.id


def _declarer(monde: _Monde, phase_id: PhaseId, *sources: SourcePhase) -> None:
    phase = monde.phases.par_id(phase_id)
    assert phase is not None
    monde.phases._phases[phase_id] = replace(phase, sources=sources)


def _classement_qualification(monde: _Monde) -> list[int]:
    from application.classements import ServiceClassement

    service = ServiceClassement(
        monde.tournois,
        monde.archers,
        monde.series,
        monde.categories,
        monde.phases,
        monde.forfaits,
        monde.departs,
        monde.inscriptions,
    )
    return [ligne.archer_id for ligne in service.pour_depart(monde.depart_id).lignes]


def _jouer_le_tableau_amont(monde: _Monde) -> None:
    """Fait gagner les **mal classés** : le tableau amont inverse l'ordre de la qualification.

    Serpent sur quatre archers : match 1 = 1ᵉʳ contre 4ᵉ, match 2 = 2ᵉ contre 3ᵉ. Le camp `bas`
    (le moins bien classé) l'emporte dans les deux, puis en finale.
    """
    service = monde.service()
    tableau, _ = service.reconstruire(monde.tournoi_id, monde.phase_id)
    premiers = sorted(m.numero for m in tableau.matchs if m.tour == 1)
    for numero in premiers:
        _gagner_manches(service, monde, numero, "bas")
    finale = next(m.numero for m in tableau.matchs if m.tour == 2)
    _gagner_manches(service, monde, finale, "bas")


def _archers_de(monde: _Monde, phase_id: PhaseId) -> list[int]:
    tableau, _ = monde.service().reconstruire(monde.tournoi_id, phase_id)
    vus: dict[int, None] = {}
    for match in tableau.matchs:
        for camp in (match.haut, match.bas):
            if camp is not None:
                vus.setdefault(camp.ref_id, None)
    return list(vus)


def test_un_prelevement_dans_un_tableau_amont_lit_le_classement_de_ce_tableau() -> None:
    """**CA — le classement lu est celui de la phase désignée.**

    « Les rangs 1 à 2 de la phase 2 » prend les deux premiers **du tableau**, pas ceux de la
    qualification. C'est le pendant positif de
    `test_une_source_qui_ne_vise_pas_la_qualification_est_ignoree`, que cette US fait tomber.
    """
    monde, aval = _monde_a_deux_tableaux()
    qualification = _classement_qualification(monde)
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=4)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2))
    _jouer_le_tableau_amont(monde)

    # Les mal classés ont gagné : le tableau rend 4ᵉ puis 3ᵉ de qualification.
    assert sorted(_archers_de(monde, aval)) == sorted(qualification[2:4])
    # …et surtout **pas** les deux premiers de la qualification, ce que faisait le repli silencieux.
    assert sorted(_archers_de(monde, aval)) != sorted(qualification[:2])


def test_une_source_visant_un_tableau_amont_n_ensemence_plus_tout_le_monde() -> None:
    """**CA — le classement lu est celui de la phase désignée** (le versant « plus de repli »).

    Avant cette US, une source non lisible faisait retomber la phase sur **tous** les archers en
    lice. Le repli était le défaut : il produisait un tableau de 4 là où le déroulé en déclarait 2.
    """
    monde, aval = _monde_a_deux_tableaux()
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=4)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2))
    _jouer_le_tableau_amont(monde)

    assert monde.service().etat_tableau(monde.tournoi_id, aval).effectif == 2


def test_une_phase_sans_source_reste_peuplee_par_les_inscrits() -> None:
    """**CA — la phase de tête est inchangée.**

    Le comportement d'avant l'US, à ne pas casser : sans prélèvement déclaré, la phase prend tout
    le monde. C'est le cas de la qualification, et d'un tableau tant que rien n'est composé.
    """
    monde, _ = _monde_a_deux_tableaux()

    assert monde.service().etat_tableau(monde.tournoi_id, monde.phase_id).effectif == 4


def test_la_cascade_tient_sur_plusieurs_crans() -> None:
    """**CA — la cascade tient sur plusieurs crans.**

    La phase 4 prélève dans la 3, qui prélève dans la 2. La résolution est récursive, et le déroulé
    est acyclique par construction (`verifier_sequence` exige une source **antérieure**) : elle
    termine. Ce test échouerait par récursion infinie si l'antériorité cessait d'être garantie.
    """
    monde, aval = _monde_a_deux_tableaux()
    dernier = monde.phases.ajouter(Phase.creer(monde.depart_id, 4, TypePhase.ELIMINATION_DIRECTE))
    assert dernier.id is not None
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=4)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2))
    _declarer(monde, dernier.id, SourcePhase.par_rangs(ordre_source=3, rang_debut=1, rang_fin=2))
    _jouer_le_tableau_amont(monde)

    # Le tableau aval n'est pas joué : ses deux occupants y sont encore en lice, donc prélevables.
    # L'assertion d'effectif est ce qui rend ce test **discriminant** : sans elle, il passait déjà
    # avant l'US — les deux phases recevant « tout le monde », leurs populations étaient égales.
    assert monde.service().etat_tableau(monde.tournoi_id, dernier.id).effectif == 2
    assert sorted(_archers_de(monde, dernier.id)) == sorted(_archers_de(monde, aval))


def test_preleves_lit_le_classement_de_chaque_source_declaree() -> None:
    """**CA — plan de cibles et arbre restent ensemencés à l'identique**, testé à sa racine.

    La parité entre `ServiceSaisieDuels` et `ServicePlacementDuels` ne vient pas d'une vérification
    croisée mais du **partage de cette fonction** : c'est la raison d'être du module
    (`application/prelevement.py`), extrait après que la recopie eut lâché à E05US020 — plan de 8
    placements pour un tableau de 4. On éprouve donc la règle **une fois**, là où les deux la
    lisent.

    Deux sources visant **deux phases différentes** : chacune doit être lue dans son propre
    classement. C'est le cas qu'aucun test ne pouvait exprimer avant, la fonction ne recevant qu'un
    classement unique.
    """
    from application.prelevement import preleves

    qualification = _classement_factice([10, 20, 30, 40])
    tableau_amont = _classement_factice([40, 30])
    phase = Phase.creer(1, 3, TypePhase.ELIMINATION_DIRECTE)
    phase = replace(
        phase,
        sources=(
            SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=1),
            SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=1),
        ),
    )

    retenus = preleves(phase, qualification, {1: qualification, 2: tableau_amont}.get)

    # Le 1ᵉʳ de la qualification (10) **et** le 1ᵉʳ du tableau amont (40) — pas deux fois le même.
    assert sorted(ligne.archer_id for ligne in retenus) == [10, 40]


def _classement_factice(archer_ids: list[int]) -> Classement:
    """Un classement minimal : des rangs scratch 1..N dans l'ordre donné."""
    return Classement(
        lignes=tuple(
            LigneClassement(
                rang_scratch=rang,
                rang_categorie=rang,
                archer_id=archer_id,
                nom="N",
                prenom="P",
                categorie_id=1,
                categorie_libelle="Cat",
                cible=None,
                club_id=None,
                total=0,
                nb_dix=0,
                nb_neuf=0,
            )
            for rang, archer_id in enumerate(archer_ids, start=1)
        )
    )
