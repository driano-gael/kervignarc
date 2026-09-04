"""Tests unitaires du **classement des clubs entre eux** (E16US017) — domaine pur.

Dérivés du **CA** de `stories/E16-retours-maquettes.md` § E16US017, écrits **avant**
l'implémentation (règle 9) :

- **CA « le barème est le décompte de médailles »** : or, puis argent, puis bronze (ordre
  olympique) ; au-delà du bronze, une place de podium n'est pas une médaille ;
- **CA « la portée du décompte suit le réglage des podiums »** : seules les médailles que le
  tournoi **décerne** comptent — et l'or décerné deux fois compte deux fois (arbitrage du
  04/09/2026) ;
- **CA « la portée *club* ne compare pas les clubs entre eux »** : elle est exclue du décompte, et
  sans portée inter-club il n'y a pas de classement du tout (arbitrage du 04/09/2026) ;
- **CA « les clubs à égalité parfaite sont *ex æquo* »** : même décompte, même rang, sans
  départage inventé ;
- **Notes « aucun effectif minimum »** : un club sans médaille est classé, à zéro.

Le rang **des archers** (y compris « club par club ») n'est pas ici : c'est `E16US014`,
`test_domain_podiums.py`.
"""

from __future__ import annotations

from dataclasses import replace

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.classement_clubs import ClassementClubs, classer_clubs
from domain.palmares import Palmares, PositionPhase, ResultatPhase, calculer_palmares
from domain.podium import PorteePodium, ReglagePodiums

_CLUBS = {
    1: "Compagnie de Kervignarc",
    2: "Arc Club de Vannes",
    3: "Les Archers du Golfe",
    4: "Zenith Archerie",
}

_SCRATCH = ReglagePodiums(portees=frozenset({PorteePodium.SCRATCH}))


def _ligne(
    archer_id: int,
    rang: int,
    categorie_id: int,
    club_id: int | None,
) -> LigneClassement:
    """Une ligne de qualification réduite à ce que le palmarès en lit."""
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang,
        archer_id=archer_id,
        nom=f"Archer{archer_id}",
        prenom="Jean",
        categorie_id=categorie_id,
        categorie_libelle=f"Categorie {categorie_id}",
        cible=None,
        club_id=club_id,
        total=600 - archer_id,
        nb_dix=0,
        nb_neuf=0,
        statut=StatutClassement.EN_LICE,
    )


def _tableau_de_huit_joue() -> ResultatPhase:
    """Un tableau de 8 entièrement joué : le 1ᵉʳ de qualification l'emporte.

    Rangs 1-4 décernés par les matchs terminaux ; les quatre battus des quarts sortent *ex æquo*
    sur `[5..8]` (ADR-0065). ⚠️ **Ils n'en restent pas moins classés au rang exact** : la politique
    câblée par défaut (`AggregationParQualification`) les départage à la qualification. Les huit
    archers occupent donc huit rangs distincts, et **la profondeur du réglage est le seul frein**
    — plusieurs tests ci-dessous la fixent à 2 pour que les archers de remplissage ne ramassent
    pas de médaille au passage.
    """
    return ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=3),
            PositionPhase(archer_id=4, rang_min=4, rang_max=4),
            PositionPhase(archer_id=5, rang_min=5, rang_max=8),
            PositionPhase(archer_id=6, rang_min=5, rang_max=8),
            PositionPhase(archer_id=7, rang_min=5, rang_max=8),
            PositionPhase(archer_id=8, rang_min=5, rang_max=8),
        ),
    )


def _palmares(
    clubs: dict[int, int | None],
    categories: dict[int, int] | None = None,
) -> Palmares:
    """Le tableau de huit joué, chaque archer rattaché au club (et à la catégorie) voulus.

    `clubs` va de l'`archer_id` au `club_id` — l'archer 1 est l'or scratch, le 2 l'argent, etc.
    """
    par_categorie = categories or {}
    qualification = Classement(
        lignes=tuple(
            _ligne(i, i, categorie_id=par_categorie.get(i, 1), club_id=clubs.get(i, 1))
            for i in range(1, 9)
        )
    )
    return calculer_palmares(qualification, (_tableau_de_huit_joue(),), libelles_club=_CLUBS)


def _decompte(classement: ClassementClubs, club_id: int) -> tuple[int, int, int]:
    """Le triplet (or, argent, bronze) d'un club, ou `(0, 0, 0)` s'il n'est pas classé."""
    for ligne in classement.lignes:
        if ligne.club_id == club_id:
            return (ligne.medailles_or, ligne.medailles_argent, ligne.medailles_bronze)
    return (0, 0, 0)


# --- CA « le barème est le décompte de médailles » ------------------------------------------------


def test_l_or_prime_sur_toute_quantite_d_argent_et_de_bronze() -> None:
    """CA : les clubs se comparent à l'or **d'abord** — l'ordre olympique, pas une somme de points.

    Le club 2 rafle l'argent ET le bronze, le club 1 n'a que l'or : le club 1 passe devant. C'est
    ce qui distingue ce barème d'un barème de points par rang, écarté le 31/08/2026.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 2, 4: 3})

    classement = classer_clubs(palmares, _SCRATCH)

    assert [ligne.club_id for ligne in classement.lignes[:2]] == [1, 2]
    assert [ligne.rang for ligne in classement.lignes[:2]] == [1, 2]


def test_l_argent_departage_a_or_egal() -> None:
    """CA : à or égal, on compare l'argent. Ici aucun club n'a d'or (le 1ᵉʳ est sans club)."""
    palmares = _palmares({1: None, 2: 1, 3: 2, 4: 3})

    classement = classer_clubs(palmares, _SCRATCH)

    assert classement.lignes[0].club_id == 1, "l'argent passe devant le bronze"
    assert _decompte(classement, 1) == (0, 1, 0)


def test_le_bronze_departage_a_or_et_argent_egaux() -> None:
    """CA : le bronze est le troisième critère, et le dernier — après lui, c'est l'*ex æquo*."""
    palmares = _palmares({1: None, 2: None, 3: 1, 4: 2})

    classement = classer_clubs(palmares, _SCRATCH)

    assert classement.lignes[0].club_id == 1
    assert _decompte(classement, 1) == (0, 0, 1)
    assert _decompte(classement, 2) == (0, 0, 0), "la 4ᵉ place n'est pas une médaille"


def test_au_dela_du_bronze_une_place_de_podium_n_est_pas_une_medaille() -> None:
    """CA : le barème ne connaît que trois métaux, quelle que soit la profondeur réglée.

    ⚠️ Piège de conjonction : la profondeur par défaut est **4** (ADR-0103), donc un podium
    décerne couramment une 4ᵉ place. La compter aurait inventé un quatrième métal.
    """
    palmares = _palmares({1: 2, 2: 2, 3: 2, 4: 1})
    reglage = replace(_SCRATCH, profondeur=8)

    classement = classer_clubs(palmares, reglage)

    assert _decompte(classement, 1) == (0, 0, 0), "le club du 4ᵉ n'a aucune médaille"
    assert _decompte(classement, 2) == (1, 1, 1)


# --- CA « la portée du décompte suit le réglage des podiums » -------------------------------------


def test_seules_les_medailles_effectivement_decernees_comptent() -> None:
    """CA : un tournoi qui ne récompense que par catégorie alimente son classement de clubs
    avec **ces** médailles-là — pas avec un classement scratch que personne ne remet.

    L'archer 3 est **3ᵉ scratch** mais **1ᵉʳ de sa catégorie** : son club récolte un bronze ou un
    or selon le réglage. C'est la démonstration que le décompte suit ce qui est décerné.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4}, categories={1: 1, 2: 1, 3: 2, 4: 2})
    par_categorie = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}), profondeur=2)

    assert _decompte(classer_clubs(palmares, replace(_SCRATCH, profondeur=2)), 3) == (0, 0, 0)
    assert _decompte(classer_clubs(palmares, par_categorie), 3) == (1, 0, 0)


def test_l_or_decerne_deux_fois_compte_deux_fois() -> None:
    """Arbitrage du 04/09/2026 : *scratch* et *catégorie* cumulés décernent deux ors au même
    archer, et son club encaisse les deux — le décompte colle aux médailles **remises**.

    ⚠️ Effet assumé, énoncé avant l'arbitrage : un club à un seul archer très fort double son
    score. L'alternative (dédoublonner par archer) aurait fait diverger le décompte affiché du
    nombre de médailles physiquement remises au pied du podium.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.SCRATCH, PorteePodium.CATEGORIE}))

    classement = classer_clubs(palmares, reglage)

    assert _decompte(classement, 1) == (2, 0, 0), "or scratch + or de catégorie"
    assert _decompte(classement, 2) == (0, 2, 0)


# --- CA « la portée *club* ne compare pas les clubs entre eux » -----------------------------------


def test_la_portee_club_n_alimente_pas_le_decompte() -> None:
    """Arbitrage du 04/09/2026 : une médaille gagnée contre ses propres coéquipiers ne dit rien
    de la performance du club **face aux autres**.

    ⚠️ La compter mesurerait l'**effectif** : la portée *club* décerne un or à **chaque** club,
    ce que les Notes de la fiche excluent explicitement du barème retenu.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})
    sans = classer_clubs(palmares, _SCRATCH)
    avec = classer_clubs(
        palmares, replace(_SCRATCH, portees=_SCRATCH.portees | {PorteePodium.CLUB})
    )

    assert [(ligne.club_id, ligne.rang) for ligne in avec.lignes] == [
        (ligne.club_id, ligne.rang) for ligne in sans.lignes
    ]
    assert _decompte(avec, 4) == (0, 0, 0), "le 4ᵉ scratch est pourtant 1ᵉʳ de son propre club"


def test_sans_aucune_portee_inter_club_il_n_y_a_pas_de_classement() -> None:
    """Arbitrage du 04/09/2026 : réglé sur la seule portée *club*, le classement n'a **aucune
    base** — tous les clubs seraient à égalité, ce qui se lit comme un bug et non comme un choix.

    L'état est **porté** (`portees_comptees` vide), jamais déduit d'une liste vide par l'écran :
    c'est la leçon des trois passes de revue d'ADR-0103 §6.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CLUB}))

    classement = classer_clubs(palmares, reglage)

    assert classement.portees_comptees == ()
    assert classement.lignes == ()


def test_un_tournoi_qui_ne_recompense_rien_n_a_pas_de_classement_de_clubs() -> None:
    """L'ensemble vide de portées est un réglage valide (ADR-0103 §1) : aucune médaille remise,
    donc aucun trophée de club à décerner."""
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})

    classement = classer_clubs(palmares, ReglagePodiums(portees=frozenset()))

    assert classement.portees_comptees == ()
    assert classement.lignes == ()


def test_les_portees_comptees_nomment_ce_qui_a_nourri_le_decompte() -> None:
    """L'écran doit pouvoir dire **sur quoi** le classement repose : la portée *club* réglée n'y
    figure pas, alors qu'elle reste affichée parmi les podiums d'archers."""
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})
    reglage = ReglagePodiums(portees=frozenset(PorteePodium))

    classement = classer_clubs(palmares, reglage)

    assert classement.portees_comptees == (PorteePodium.SCRATCH, PorteePodium.CATEGORIE)


# --- CA « les clubs à égalité parfaite sont *ex æquo* » -------------------------------------------


def test_les_clubs_a_egalite_parfaite_partagent_le_rang_et_sautent_le_suivant() -> None:
    """CA : même décompte = même rang, sans départage inventé — et le rang suivant saute
    (arithmétique 1-2-2-4 du projet, `DETTE-029`).

    Deux catégories, un podium chacune : les clubs 1 et 2 prennent chacun **un or**, les clubs 3
    et 4 chacun **un argent**. Les deux paires sont strictement identiques, donc rangs 1-1-3-3.
    """
    palmares = _palmares(
        {1: 1, 2: 2, 3: 3, 4: 4},
        categories={1: 1, 2: 2, 3: 1, 4: 2},
    )
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}), profondeur=2)

    classement = classer_clubs(palmares, reglage)

    assert _decompte(classement, 1) == (1, 0, 0)
    assert _decompte(classement, 2) == (1, 0, 0)
    assert [ligne.rang for ligne in classement.lignes] == [1, 1, 3, 3]


def test_les_clubs_ex_aequo_sont_ordonnes_par_libelle() -> None:
    """Aucun départage n'est inventé, mais l'**ordre d'affichage** doit être déterministe : deux
    lectures du même palmarès ne doivent pas rendre deux listes différentes (règle 9)."""
    # Les quatre médaillés sont sans club ; les quatre *ex æquo* du tableau, eux, ont chacun le
    # leur — donc quatre clubs bredouilles, rencontrés dans un ordre (3, 1, 4, 2) qui n'est pas
    # l'ordre alphabétique. Un tri absent se verrait.
    palmares = _palmares({1: None, 2: None, 3: None, 4: None, 5: 3, 6: 1, 7: 4, 8: 2})

    classement = classer_clubs(palmares, _SCRATCH)

    assert [ligne.club_libelle for ligne in classement.lignes] == [
        "Arc Club de Vannes",
        "Compagnie de Kervignarc",
        "Les Archers du Golfe",
        "Zenith Archerie",
    ]
    assert {ligne.rang for ligne in classement.lignes} == {1}, "tous à zéro, tous 1ᵉʳˢ"


# --- Notes « aucun effectif minimum » -------------------------------------------------------------


def test_un_club_sans_aucune_medaille_est_classe_a_zero() -> None:
    """Notes (arbitrage du 31/08/2026) : pas de seuil d'effectif — un seuil masquerait des clubs
    en silence. Un club présent au tournoi apparaît, même bredouille."""
    palmares = _palmares({1: 1, 2: 1, 3: 1, 4: 1, 5: 4, 6: 4, 7: 4, 8: 4})

    classement = classer_clubs(palmares, _SCRATCH)

    assert _decompte(classement, 4) == (0, 0, 0)
    assert [ligne.club_id for ligne in classement.lignes] == [1, 4]


def test_un_archer_sans_club_n_apporte_sa_medaille_a_personne() -> None:
    """ADR-0014 : « club inconnu » est une anomalie à signaler, pas un club de rattachement.

    ⚠️ Son or ne va donc **nulle part** — il ne crée pas non plus une ligne « sans club ».
    """
    palmares = _palmares({1: None, 2: 1, 3: 1, 4: 1})

    classement = classer_clubs(palmares, _SCRATCH)

    assert [ligne.club_id for ligne in classement.lignes] == [1]
    assert _decompte(classement, 1) == (0, 1, 1)


def test_un_palmares_sans_ligne_ne_classe_aucun_club() -> None:
    """Le cas du tournoi qui n'a pas commencé : pas de ligne, donc pas de club à classer.

    ⚠️ À distinguer de l'absence de base (`portees_comptees` vide) : ici la portée **est**
    réglée, c'est la population qui manque. L'écran ne dit pas la même chose dans les deux cas.
    """
    classement = classer_clubs(Palmares(lignes=()), _SCRATCH)

    assert classement.lignes == ()
    assert classement.portees_comptees == (PorteePodium.SCRATCH,)


# --- État du classement --------------------------------------------------------------------------


def test_le_classement_est_provisoire_tant_qu_un_bloc_compte_attend() -> None:
    """Même leçon qu'ADR-0103 §6 : ne jamais annoncer le définitif pendant que le tournoi peut
    encore changer. Le trophée du club se remet une fois, on ne le promet pas à 9 h du matin.

    ⚠️ L'état est porté par le classement, pas recalculé par ses lecteurs sur une autre
    population — c'est exactement la faute que trois passes de revue ont corrigée sur `BlocPodium`.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})

    acquis = classer_clubs(palmares, _SCRATCH)
    en_cours = classer_clubs(replace(palmares, duels_non_commences=True), _SCRATCH)

    assert acquis.provisoire is False
    assert en_cours.provisoire is True
