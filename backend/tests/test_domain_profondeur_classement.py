"""Profondeur de classement configurable & rang unique 1→N (E06US006) — tests **depuis le CA**.

Règle 9 : ces tests dérivent des deux CA de `stories/E06-classements.md` § E06US006, écrits
**avant** l'implémentation :

- **CA « rang unique »** : chaque archer a un rang unique 1→N, alimenté par les **matchs
  terminaux** (E05US010). Sous placement intégral, aucune fourchette ne subsiste : tout rang est
  décerné par un tir, donc `decerne` vaut vrai partout et aucune politique `aggregation` n'a à
  trancher ;
- **CA « profondeur configurable »** : mode 1→N (défaut) **ou** top N + regroupement du reliquat,
  porté par la politique `depth`.

⚠️ **Arbitrage du 04/08/2026, reversé dans `stories/`** : le CA dit « 1→N (**défaut**) », ce que
les tests ci-dessous **ne vérifient pas** — et c'est délibéré. Le défaut du *catalogue*
(ADR-0004) n'est pas le défaut d'une *phase déjà écrite en base* : jusqu'à cette US, toutes les
phases se jouaient en `ProfondeurPodium` figée au câblage. Faire de 1→N le preset d'une phase qui
ne règle rien convertirait **tous les tournois existants** au placement intégral — un tableau de
120 passerait d'une trentaine de duels à plus d'une centaine, sans que personne ne l'ait demandé.
Le preset d'une phase non réglée reste donc `podium(4)` (mécanisme « politique sans migration »,
ADR-0011), et 1→N est ce que l'organisateur **choisit**. Cf. ADR-0070.

Vocabulaire (règle 3) : la **profondeur** dit *jusqu'où l'on classe* ; le **routing** dit *où
descend un perdant*. Les deux sont orthogonales — une cascade tronquée au rang 4 est exactement le
tableau à petite finale livré depuis E05US005.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.bareme import BaremeQualification
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.erreurs import ProfondeurInvalide
from domain.palmares import OriginePalmares, PositionPhase, ResultatPhase, calculer_palmares
from domain.participant import Participant
from domain.phase import Phase, TypePhase, profondeur_par_defaut
from domain.politiques import (
    ByesAuxMieuxClasses,
    Depth,
    NomProfondeur,
    PlacementEnCascade,
    ProfondeurClassement,
    ProfondeurPodium,
    ProfondeurUnVersN,
    SeedingSerpent,
    assembler_politiques,
    registre_par_defaut,
)
from domain.tableau import Tableau, construire_tableau

SEEDING = SeedingSerpent()
BYES = ByesAuxMieuxClasses()
CASCADE = PlacementEnCascade()
TOURNOI = 1


def _construire(effectif: int, depth: Depth) -> Tableau:
    """Un tableau en cascade pour `effectif` participants classés 1..effectif."""
    return construire_tableau(
        [Participant.individuel(rang) for rang in range(1, effectif + 1)],
        seeding=SEEDING,
        byes=BYES,
        routing=CASCADE,
        depth=depth,
    )


def _jouer_tout(tableau: Tableau) -> Tableau:
    """Joue tous les matchs en faisant gagner le mieux classé — déroulé sans surprise.

    Même oracle qu'`test_domain_placement_integral` : chaque participant finit à son rang de
    départ, donc toute erreur de profondeur ou de routage déplace un rang de façon visible.
    """
    courant = tableau
    encore = True
    while encore:
        encore = False
        for match in courant.matchs:
            if match.est_jouable and match.haut is not None and match.bas is not None:
                mieux = match.haut if match.haut.ref_id < match.bas.ref_id else match.bas
                courant = courant.jouer(match.numero, mieux)
                encore = True
                break
    return courant


# --- CA « profondeur configurable » : le descripteur porté par la phase --------------------------


def test_le_classement_integral_ne_s_arrete_a_aucun_rang() -> None:
    """« Mode 1→N » : il n'y a pas de seuil à déclarer, et en déclarer un serait contradictoire."""
    integrale = ProfondeurClassement.integrale()
    assert integrale.jusqu_au is None
    with pytest.raises(ProfondeurInvalide):
        ProfondeurClassement(nom=NomProfondeur.UN_VERS_N, jusqu_au=4)


def test_un_top_n_declare_le_rang_ou_il_s_arrete() -> None:
    assert ProfondeurClassement.top(8).jusqu_au == 8


@pytest.mark.parametrize("seuil", [0, -1])
def test_un_top_n_exige_un_rang_positif(seuil: int) -> None:
    """« Top 0 » ne veut pas dire « 1→N » — cela se dit en choisissant 1→N."""
    with pytest.raises(ProfondeurInvalide):
        ProfondeurClassement.top(seuil)


def test_une_phase_en_tableau_porte_la_profondeur_choisie() -> None:
    phase = Phase.creer(
        TOURNOI,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        profondeur=ProfondeurClassement.integrale(),
    )
    assert phase.profondeur == ProfondeurClassement.integrale()


def test_une_phase_qui_ne_regle_rien_garde_le_preset_de_son_type() -> None:
    """Absence ≠ 1→N : le preset d'un tableau reste le podium (ADR-0070, cf. en-tête)."""
    phase = Phase.creer(TOURNOI, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
    assert phase.profondeur is None
    assert profondeur_par_defaut(TypePhase.ELIMINATION_DIRECTE) == ProfondeurClassement.top(4)


def test_une_qualification_ne_regle_aucune_profondeur() -> None:
    """Une qualification classe toujours tout le monde : le réglage n'a pas de sens pour elle,
    et l'offrir laisserait croire à un levier qui n'agit sur rien.

    Passe par `replace()` — la porte d'entrée que `__post_init__` doit garder autant que les
    fabriques, et celle qu'un service emprunte pour éditer une phase existante.
    """
    qualification = Phase.qualification(TOURNOI, BaremeQualification.creer(20, 3))
    with pytest.raises(ProfondeurInvalide):
        replace(qualification, profondeur=ProfondeurClassement.integrale())


def test_un_type_sans_tableau_n_a_pas_de_profondeur_par_defaut() -> None:
    with pytest.raises(ProfondeurInvalide):
        profondeur_par_defaut(TypePhase.ECHAUFFEMENT)


def test_la_profondeur_se_resout_par_le_registre_et_non_a_la_main() -> None:
    """Point d'injection (règle 2) : le descripteur est de la **donnée**, la stratégie sort du
    registre — le même parti que le `tiebreak` d'E06US003 (ADR-0066)."""
    registre = registre_par_defaut()
    integral = assembler_politiques(
        {"depth": ProfondeurClassement.integrale().en_config()}, registre
    )
    top = assembler_politiques({"depth": ProfondeurClassement.top(8).en_config()}, registre)
    assert integral.depth == ProfondeurUnVersN()
    assert top.depth == ProfondeurPodium(jusqu_au=8)


# --- CA « rang unique » : sous placement intégral, tout rang est décerné -------------------------


def test_sous_classement_integral_chaque_participant_a_un_rang_exact() -> None:
    """Le cœur du CA : 1→N, sans trou ni fourchette, et chaque rang vient d'un match terminal."""
    joue = _jouer_tout(_construire(8, ProfondeurUnVersN()))
    positions = joue.positions_acquises()
    assert len(positions) == 8
    assert all(p.rang_min == p.rang_max for p in positions.values())
    assert sorted(p.rang_min for p in positions.values()) == list(range(1, 9))


def test_sous_profondeur_podium_le_reliquat_reste_en_fourchette() -> None:
    """L'autre mode : seuls les quatre premiers sont départagés, les battus des quarts restent
    groupés sur `[5..8]` — c'est le « regroupement du reliquat » du CA."""
    joue = _jouer_tout(_construire(8, ProfondeurPodium()))
    positions = joue.positions_acquises()
    exacts = sorted(p.rang_min for p in positions.values() if p.rang_min == p.rang_max)
    reliquat = [p for p in positions.values() if p.rang_min != p.rang_max]
    assert exacts == [1, 2, 3, 4]
    assert all((p.rang_min, p.rang_max) == (5, 8) and not p.en_lice for p in reliquat)


def test_le_palmares_d_un_classement_integral_n_a_ni_ex_aequo_ni_rang_emprunte() -> None:
    """Bout en bout du CA « rang unique » : les positions d'un tableau intégral, fusionnées,
    donnent un palmarès 1→N dont **chaque** rang est décerné par un tir.

    C'est ce qui distingue les deux modes à l'écran : ici la politique `aggregation` n'a rien à
    départager, donc aucun rang n'est « rangé » plutôt que gagné.
    """
    joue = _jouer_tout(_construire(8, ProfondeurUnVersN()))
    positions = tuple(
        PositionPhase(
            archer_id=participant.ref_id,
            rang_min=position.rang_min,
            rang_max=position.rang_max,
            en_lice=position.en_lice,
        )
        for participant, position in joue.positions_acquises().items()
    )
    palmares = calculer_palmares(
        _qualification_de_huit(), (ResultatPhase(ordre=2, positions=positions),)
    )
    assert [ligne.rang_min for ligne in palmares.lignes] == list(range(1, 9))
    assert all(ligne.rang_min == ligne.rang_max for ligne in palmares.lignes)
    assert all(ligne.decerne for ligne in palmares.lignes)
    assert all(ligne.origine is OriginePalmares.DUELS for ligne in palmares.lignes)


def _qualification_de_huit() -> Classement:
    """Huit archers d'une même catégorie, qualifiés du 1ᵉʳ au 8ᵉ rang."""
    return Classement(
        lignes=tuple(
            LigneClassement(
                rang_scratch=rang,
                rang_categorie=rang,
                archer_id=rang,
                nom=f"Archer{rang}",
                prenom="Jean",
                categorie_id=1,
                categorie_libelle="Senior Homme",
                cible=None,
                club_id=1,
                total=600 - rang,
                nb_dix=0,
                nb_neuf=0,
                statut=StatutClassement.EN_LICE,
            )
            for rang in range(1, 9)
        )
    )
