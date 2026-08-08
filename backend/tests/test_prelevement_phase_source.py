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
from domain.classement_de_tableau import ClassementSource
from domain.phase import IssueTour, Phase, PhaseId, SourcePhase, TypePhase
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

    qualification = _source_factice([10, 20, 30, 40])
    tableau_amont = _source_factice([40, 30])
    phase = Phase.creer(1, 3, TypePhase.ELIMINATION_DIRECTE)
    phase = replace(
        phase,
        sources=(
            SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=1),
            SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=1),
        ),
    )

    retenus = preleves(phase, qualification.classement, {1: qualification, 2: tableau_amont}.get)

    # Le 1ᵉʳ de la qualification (10) **et** le 1ᵉʳ du tableau amont (40) — pas deux fois le même.
    # ⚠️ Assertion sur la **liste**, pas sur son tri (correctif de revue, axe B) : la docstring de
    # `preleves` fait de l'ordre `(ordre_source, rang)` une propriété essentielle — « le `Seeding`
    # consomme cette liste dans l'ordre : la permuter changerait les appariements ». Un `sorted()`
    # dans l'assertion aurait laissé passer n'importe quelle permutation.
    assert [ligne.archer_id for ligne in retenus] == [10, 40]


def test_un_archer_vise_par_deux_sources_n_est_preleve_qu_une_fois() -> None:
    """Le dédoublonnage de `preleves`, que rien n'exerçait (correctif de revue, axe B).

    `verifier_sequence` ne contrôle le non-recoupement qu'**au sein** d'une phase : rien n'empêche
    deux sources visant deux phases différentes de désigner le même archer. Sans dédoublonnage, il
    disputerait deux duels à la fois dans le même tableau.
    """
    from application.prelevement import preleves

    qualification = _source_factice([10, 20])
    # Le 1ᵉʳ du tableau amont est **aussi** le 1ᵉʳ de la qualification.
    tableau_amont = _source_factice([10, 20])
    phase = replace(
        Phase.creer(1, 3, TypePhase.ELIMINATION_DIRECTE),
        sources=(
            SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=1),
            SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=1),
        ),
    )

    retenus = preleves(phase, qualification.classement, {1: qualification, 2: tableau_amont}.get)

    assert [ligne.archer_id for ligne in retenus] == [10]


def _source_factice(
    archer_ids: list[int],
    plages_indecises: tuple[tuple[int, int], ...] = (),
    rang_premier: int = 1,
) -> ClassementSource:
    """Un `ClassementSource` minimal : rangs 1..N dans l'ordre donné."""
    return ClassementSource(
        classement=_classement_factice(archer_ids),
        plages_indecises=plages_indecises,
        rang_premier=rang_premier,
    )


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


def _jouer_le_premier_tour(monde: _Monde) -> None:
    """Ne joue que le tour 1 du tableau amont : la finale reste à tirer.

    Le décor du cas « fenêtre qui **contient** un bloc indécis » : les deux vainqueurs partagent
    la plage `[1..2]` de la finale à venir.
    """
    service = monde.service()
    tableau, _ = service.reconstruire(monde.tournoi_id, monde.phase_id)
    for numero in sorted(m.numero for m in tableau.matchs if m.tour == 1):
        _gagner_manches(service, monde, numero, "bas")


def test_une_fenetre_qui_coupe_un_bloc_indecis_est_refusee() -> None:
    """**ADR-0081** — on ne prélève pas des places que la compétition n'a pas encore attribuées.

    Le cas trouvé par la revue adversariale, et le plus dangereux de l'US : un tableau de 8 **non
    commencé** porte ses huit archers sur la plage `[1..8]` de leur quart en cours. Leur demander
    « les rangs 5 à 8 » — les quatre battus des quarts — rendait les quatre **derniers qualifiés**,
    parce que la politique `aggregation` départageait l'unique paquet sur le rang de qualification.

    La consolante recevait donc le bon **nombre** d'archers, avec des noms crédibles : un bracket
    bien formé, plausible et faux, **moins** détectable qu'avant l'US (où elle recevait tout le
    monde, ce qui sautait aux yeux). Ce test échoue sur le code d'avant le correctif.
    """
    import pytest

    from application.erreurs import PrelevementEnAttente

    monde, aval = _monde_a_deux_tableaux(8)
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=8)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=5, rang_fin=8))

    with pytest.raises(PrelevementEnAttente, match="pas encore départagé"):
        monde.service().etat_tableau(monde.tournoi_id, aval)


def test_la_meme_fenetre_se_resout_une_fois_les_quarts_tires() -> None:
    """Le pendant du précédent : le refus est **temporaire**, pas un blocage de composition.

    Une fois le tour 1 joué, les battus portent `[5..8]` avec `en_lice=False` — la plage est
    *ex æquo*, plus indécise : la politique `aggregation` a le droit de la fermer (Règle R,
    ADR-0065/0067). La consolante reçoit alors les **vrais** battus.
    """
    monde, aval = _monde_a_deux_tableaux(8)
    qualification = _classement_qualification(monde)
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=8)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=5, rang_fin=8))
    _jouer_le_premier_tour(monde)

    battus = sorted(_archers_de(monde, aval))
    assert len(battus) == 4
    # Les mal classés ont gagné leurs quarts : les battus sont les **mieux** classés — donc
    # exactement l'inverse de ce que le repli sur le rang de qualification aurait produit.
    assert battus == sorted(qualification[:4])


def test_une_fenetre_qui_contient_un_bloc_indecis_reste_honoree() -> None:
    """**ADR-0080 §2 est préservé** : c'est « couper », pas « chevaucher », qui est interdit.

    Deux archers qui vont tirer la finale partagent `[1..2]`. Une phase qui prélève « les rangs 1 à
    2 » les veut **tous les deux** — elle veut les finalistes, pas le champion. Refuser ici aurait
    été le refus abusif symétrique, que le projet tient pour aussi coûteux qu'un oubli.
    """
    monde, aval = _monde_a_deux_tableaux(4)
    _declarer(
        monde, monde.phase_id, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=4)
    )
    _declarer(monde, aval, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2))
    _jouer_le_premier_tour(monde)

    assert len(_archers_de(monde, aval)) == 2


def test_la_tranche_cumule_le_decalage_le_long_de_la_chaine() -> None:
    """**CA — `tranche` suit la même règle**, et le premier jet ne la suivait pas.

    Une phase prélevant « les rangs 1 à 2 » d'un tableau qui disputait lui-même les places 33 et
    suivantes joue pour la **33ᵉ** place. Sans ce cumul, `domain/palmares.py` calculait un décalage
    nul et publiait le vainqueur de cette finale de consolante **1ᵉʳ du tournoi**, devant le
    champion — `DETTE-034` rouverte un cran plus bas.

    Testé sur `tranche` directement : le défaut est arithmétique, et un résolveur factice le montre
    sans monter trois tableaux. Ce test rend **1** sur le code d'avant le correctif.
    """
    from application.prelevement import tranche

    # La phase source dispute les places 33+ : son rang local 1 vaut le rang 33 du tournoi.
    amont = _source_factice([40, 30], rang_premier=33)
    phase = replace(
        Phase.creer(1, 3, TypePhase.ELIMINATION_DIRECTE),
        sources=(SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2),),
    )

    assert tranche(phase, {2: amont}.get) == 33


def test_une_source_de_nature_inerte_ne_fait_pas_echouer_la_phase() -> None:
    """Une source `le_reste` / `par_issue_de_tour` est **sans effet**, pas destructrice.

    Régression mesurée en revue (axe C1) : le résolveur était appelé **avant** le test de nature,
    si bien qu'une source inerte visant un tableau amont déclenchait sa reconstruction complète —
    et faisait remonter l'échec de cette reconstruction à la phase aval. Une source dont le contrat
    est de ne rien faire cassait l'écran de duels d'une autre phase.
    """
    from application.prelevement import preleves

    qualification = _source_factice([10, 20])

    def _resolveur_qui_explose(_ordre: int) -> ClassementSource | None:
        raise AssertionError("une source inerte ne doit jamais être résolue")

    phase = replace(
        Phase.creer(1, 3, TypePhase.ELIMINATION_DIRECTE),
        sources=(SourcePhase.par_issue_de_tour(ordre_source=2, tour=1, issue=IssueTour.PERDANTS),),
    )

    # Aucune source lisible : la phase retombe sur le classement reçu, sans rien résoudre.
    retenus = preleves(phase, qualification.classement, _resolveur_qui_explose)

    assert [ligne.archer_id for ligne in retenus] == [10, 20]
