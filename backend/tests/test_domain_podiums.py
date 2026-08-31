"""Tests unitaires des **podiums configurables** (E16US014) — fonction de domaine pure.

Dérivés du **CA** de `stories/E16-retours-maquettes.md` § E16US014, écrits **avant**
l'implémentation (règle 9) :

- **CA « plusieurs portées cohabitent »** : *catégorie*, *scratch* et *club* se cumulent ; n'en
  cocher aucune est valide ; le défaut est *catégorie* seule (comportement d'E06US004) ;
- **CA « la profondeur se règle »** : défaut 4, une profondeur < 1 est refusée ;
- **CA « les trois portées obéissent aux mêmes conditions »** : rang issu des duels, plus en lice,
  rang **exact**, chacune sur **son** rang ;
- **CA « un archer sans club n'entre dans aucun podium de club »** (ADR-0014).

Le classement des **clubs entre eux** n'est pas ici : c'est `E16US017`, un classement neuf.
"""

from __future__ import annotations

import pytest

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.erreurs import ProfondeurPodiumInvalide
from domain.palmares import Palmares, PositionPhase, ResultatPhase, calculer_palmares
from domain.podium import PROFONDEUR_PODIUM_PAR_DEFAUT, PorteePodium, ReglagePodiums
from domain.politiques import AggregationExAequo

_CLUBS = {1: "Compagnie de Kervignarc", 2: "Arc Club de Vannes", 3: "Les Archers du Golfe"}


def _ligne(
    archer_id: int,
    rang: int,
    categorie_id: int = 1,
    categorie_libelle: str = "Senior Homme",
    club_id: int | None = 1,
) -> LigneClassement:
    """Une ligne de qualification réduite à ce que le palmarès en lit."""
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang,
        archer_id=archer_id,
        nom=f"Archer{archer_id}",
        prenom="Jean",
        categorie_id=categorie_id,
        categorie_libelle=categorie_libelle,
        cible=None,
        club_id=club_id,
        total=600 - archer_id,
        nb_dix=0,
        nb_neuf=0,
        statut=StatutClassement.EN_LICE,
    )


def _tableau_de_huit_joue() -> ResultatPhase:
    """Un tableau de 8 entièrement joué : le 6ᵉ de qualification l'emporte.

    Rangs 1-4 décernés par les matchs terminaux ; les quatre battus des quarts sortent *ex æquo*
    sur `[5..8]`, qu'aucun match ne départage (Règle R, ADR-0065).
    """
    return ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=6, rang_min=1, rang_max=1),
            PositionPhase(archer_id=1, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=3),
            PositionPhase(archer_id=2, rang_min=4, rang_max=4),
            PositionPhase(archer_id=4, rang_min=5, rang_max=8),
            PositionPhase(archer_id=5, rang_min=5, rang_max=8),
            PositionPhase(archer_id=7, rang_min=5, rang_max=8),
            PositionPhase(archer_id=8, rang_min=5, rang_max=8),
        ),
    )


def _palmares_de_huit(clubs: dict[int, int | None] | None = None) -> Palmares:
    """Le tableau de huit joué, chaque archer rattaché à son club (tous au club 1 par défaut)."""
    par_archer: dict[int, int | None] = clubs if clubs is not None else {}
    qualification = Classement(
        lignes=tuple(_ligne(i, i, club_id=par_archer.get(i, 1)) for i in range(1, 9))
    )
    return calculer_palmares(qualification, (_tableau_de_huit_joue(),), libelles_club=_CLUBS)


def _archers(palmares: Palmares, portee: PorteePodium, cle: int | None) -> list[int]:
    """Les archers du bloc de podium `(portee, cle)`, ou `[]` si ce bloc n'existe pas."""
    reglage = ReglagePodiums(portees=frozenset({portee}))
    for bloc in palmares.podiums(reglage):
        if bloc.cle == cle:
            return [place.ligne.archer_id for place in bloc.places]
    return []


# --- CA « la profondeur se règle » ---------------------------------------------------------------


def test_le_reglage_par_defaut_reproduit_e06us004() -> None:
    """Le défaut est *catégorie* seule sur quatre places : un tournoi existant ne bouge pas.

    C'est la seule garantie de non-régression du réglage — tout tournoi déjà en base hérite de ce
    défaut, et son palmarès doit s'afficher exactement comme avant l'US.
    """
    reglage = ReglagePodiums()

    assert reglage.portees == frozenset({PorteePodium.CATEGORIE})
    assert reglage.profondeur == PROFONDEUR_PODIUM_PAR_DEFAUT == 4


@pytest.mark.parametrize("profondeur", [0, -1])
def test_une_profondeur_inferieure_a_un_est_refusee(profondeur: int) -> None:
    """« Ne rien récompenser » se dit en ne cochant **aucune portée**, pas en demandant zéro place.

    Sans cet invariant, deux écritures diraient la même chose et l'écran devrait trancher laquelle
    croire.
    """
    with pytest.raises(ProfondeurPodiumInvalide):
        ReglagePodiums(profondeur=profondeur)


def test_la_profondeur_borne_chaque_bloc() -> None:
    """CA : le nombre de places d'un podium est le réglage, pas une constante."""
    palmares = _palmares_de_huit()
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.SCRATCH}), profondeur=2)

    (bloc,) = palmares.podiums(reglage)

    assert [place.ligne.archer_id for place in bloc.places] == [6, 1]


# --- CA « plusieurs portées cohabitent » ---------------------------------------------------------


def test_aucune_portee_cochee_est_un_reglage_valide() -> None:
    """Le tournoi qui ne remet rien affiche son classement **sans podium** — et sans erreur."""
    palmares = _palmares_de_huit()

    assert palmares.podiums(ReglagePodiums(portees=frozenset())) == ()


def test_les_portees_se_cumulent_et_sortent_dans_un_ordre_stable() -> None:
    """CA : les portées s'empilent (A16, « tout doit être possible »).

    L'ordre des blocs suit la **déclaration** de `PorteePodium`, pas l'ordre où l'organisateur a
    coché : deux réglages équivalents doivent rendre le même écran.
    """
    palmares = _palmares_de_huit({i: 1 if i <= 4 else 2 for i in range(1, 9)})
    reglage = ReglagePodiums(
        portees=frozenset({PorteePodium.CLUB, PorteePodium.SCRATCH, PorteePodium.CATEGORIE})
    )

    blocs = palmares.podiums(reglage)

    assert [bloc.portee for bloc in blocs] == [
        PorteePodium.SCRATCH,
        PorteePodium.CATEGORIE,
        PorteePodium.CLUB,
        PorteePodium.CLUB,
    ]


def test_le_bloc_porte_le_libelle_de_ce_qu_il_recompense() -> None:
    """Le libellé vient du serveur : le PDF doit **nommer** les clubs et n'a pas d'écran pour le
    faire à sa place. « Scratch » est du vocabulaire FFTA (règle 3), pas de la copie d'interface."""
    palmares = _palmares_de_huit({i: 1 if i <= 4 else 2 for i in range(1, 9)})
    reglage = ReglagePodiums(
        portees=frozenset({PorteePodium.SCRATCH, PorteePodium.CATEGORIE, PorteePodium.CLUB})
    )

    libelles = [(bloc.portee, bloc.cle, bloc.libelle) for bloc in palmares.podiums(reglage)]

    # Le club 2 passe devant le club 1 : les groupes sortent dans l'ordre du palmarès, donc un club
    # est situé par son **meilleur** archer — ici le vainqueur du tableau (archer 6).
    assert libelles == [
        (PorteePodium.SCRATCH, None, "Scratch"),
        (PorteePodium.CATEGORIE, 1, "Senior Homme"),
        (PorteePodium.CLUB, 2, "Arc Club de Vannes"),
        (PorteePodium.CLUB, 1, "Compagnie de Kervignarc"),
    ]


# --- CA « les trois portées obéissent aux mêmes conditions » -------------------------------------


def test_le_podium_scratch_lit_le_rang_absolu() -> None:
    """Le podium scratch est celui du tournoi : les quatre places décernées par les matchs."""
    palmares = _palmares_de_huit()

    assert _archers(palmares, PorteePodium.SCRATCH, None) == [6, 1, 3, 2]


def test_le_podium_par_club_renumerote_les_archers_du_club_depuis_un() -> None:
    """CA : un podium par club classe **les archers d'un club entre eux**.

    Le rang de club se lit dans l'espace du club, comme le rang de catégorie dans celui de sa
    catégorie : le 2ᵉ du tournoi (archer 1) est **1ᵉʳ de son club**, et l'archer 4 — *ex æquo* 5ᵉ-8ᵉ
    au scratch, mais **seul de son club** dans ce paquet — y décroche un rang exact. Le vainqueur
    du tableau (archer 6) est au club 2 : personne ne monte deux fois sur le même podium.
    """
    palmares = _palmares_de_huit({i: 1 if i <= 4 else 2 for i in range(1, 9)})

    assert _archers(palmares, PorteePodium.CLUB, 1) == [1, 3, 2, 4]
    assert _archers(palmares, PorteePodium.CLUB, 2) == [6, 5, 7, 8]


def test_un_ex_aequo_de_club_n_entre_pas_au_podium_de_son_club() -> None:
    """Les mêmes trois conditions valent pour les trois portées : personne ne saurait quelle
    médaille remettre à deux archers du même club que rien ne départage.

    Les archers 4 et 5 sont *ex æquo* 5ᵉ-8ᵉ et seuls représentants du club 3 : leur rang de club
    reste une fourchette, donc aucun des deux n'est sur le podium de ce club.
    """
    clubs: dict[int, int | None] = {1: 1, 2: 1, 3: 1, 4: 3, 5: 3, 6: 1, 7: 2, 8: 2}
    qualification = Classement(lignes=tuple(_ligne(i, i, club_id=clubs[i]) for i in range(1, 9)))

    palmares = calculer_palmares(
        qualification,
        (_tableau_de_huit_joue(),),
        aggregation=AggregationExAequo(),
        libelles_club=_CLUBS,
    )

    assert _archers(palmares, PorteePodium.CLUB, 3) == []


# --- CA « un archer sans club n'entre dans aucun podium de club » --------------------------------


def test_un_archer_sans_club_n_entre_dans_aucun_bloc_de_club() -> None:
    """`club_id is None` est l'anomalie « club inconnu » (ADR-0014), pas un club de rattachement.

    L'archer reste au classement complet — le palmarès ne le perd pas — mais aucun bloc « sans
    club » n'est fabriqué : ce serait donner corps à ce que le référentiel signale comme un trou.
    """
    clubs: dict[int, int | None] = {i: 1 for i in range(1, 9)}
    clubs[6] = None
    palmares = _palmares_de_huit(clubs)
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CLUB}))

    blocs = palmares.podiums(reglage)

    assert [bloc.cle for bloc in blocs] == [1]
    assert 6 not in [place.ligne.archer_id for place in blocs[0].places]
    assert 6 in [ligne.archer_id for ligne in palmares.lignes]
