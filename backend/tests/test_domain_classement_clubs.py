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
from domain.classement_clubs import PORTEES_INTER_CLUBS, ClassementClubs, classer_clubs
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
    # ⚠️ Un seul podium ne décerne qu'**une** médaille par métal : il faut deux catégories pour
    # que deux clubs soient à égalité. Les clubs sont rencontrés dans l'ordre 3-1-4-2 (l'ordre du
    # palmarès), qui n'est pas l'ordre alphabétique — un tri absent se verrait donc.
    # ⚠️ Le cas « personne n'a de médaille » ne rend plus aucune ligne depuis la revue (axe C1) :
    # cette fixture doit donc réellement en décerner.
    palmares = _palmares(
        {1: 3, 2: 1, 3: 4, 4: 2},
        categories={1: 1, 2: 2, 3: 1, 4: 2},
    )
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}), profondeur=2)

    classement = classer_clubs(palmares, reglage)

    argents = [ligne for ligne in classement.lignes if ligne.medailles_argent == 1]
    assert [ligne.club_libelle for ligne in argents] == [
        "Arc Club de Vannes",
        "Zenith Archerie",
    ], "les ex æquo sortent par libellé, pas dans l'ordre de rencontre (4 puis 2)"
    assert [ligne.rang for ligne in argents] == [
        3,
        3,
    ], "même décompte, même rang, et le 2 est sauté"
    assert [ligne.club_id for ligne in classement.lignes[:2]] == [1, 3], "les deux ors, triés aussi"


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


def test_un_tournoi_sans_medaille_ne_classe_pas_les_clubs_a_zero() -> None:
    """⚠️ **Relevé en revue (axe C1)** — le défaut le plus visible de la 1ʳᵉ livraison.

    Toute la matinée, aucune médaille n'est décernée : le décompte de chaque club vaut `(0, 0, 0)`,
    la clé de tri est donc identique pour tous, et l'arithmétique d'*ex æquo* leur donnait à tous
    le **rang 1**. Les trois surfaces projetaient « 1ᵉʳ » à côté de chaque club pendant des heures
    — mot pour mot l'état que le CA interdit (« pas un classement où tout le monde est premier »),
    atteint par la porte du **décompte** au lieu de celle de la **portée**.
    """
    qualification = Classement(
        lignes=tuple(_ligne(i, i, categorie_id=1, club_id=i) for i in range(1, 5))
    )
    # Aucun résultat de phase : personne n'a de rang issu des duels, donc aucune place décernée.
    palmares = calculer_palmares(qualification, (), libelles_club=_CLUBS)

    classement = classer_clubs(palmares, _SCRATCH)

    assert classement.lignes == (), "pas de classement, et surtout pas quatre clubs 1ᵉʳˢ"
    assert classement.portees_comptees == (PorteePodium.SCRATCH,), "la base existe, elle"
    assert classement.portees_reglees == (PorteePodium.SCRATCH,)


def test_le_reglage_vide_se_distingue_de_l_absence_de_base() -> None:
    """Deux vides que `portees_comptees` seul **confond**, et que l'écran ne dit pas pareil.

    ⚠️ Relevé en revue (axe C2) : le front les séparait en lisant `podiums`, ce que `VuePalmares`
    interdit en toutes lettres — quatre gardes l'avaient déjà tenté et raté. `portees_reglees`
    porte le fait, il ne se déduit plus.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})

    rien = classer_clubs(palmares, ReglagePodiums(portees=frozenset()))
    club_seul = classer_clubs(palmares, ReglagePodiums(portees=frozenset({PorteePodium.CLUB})))

    assert rien.portees_comptees == () and club_seul.portees_comptees == (), "même absence de base"
    assert rien.portees_reglees == (), "le tournoi ne récompense rien"
    assert club_seul.portees_reglees == (PorteePodium.CLUB,), "il récompense, mais pas entre clubs"


def test_chaque_metal_est_compte_dans_sa_propre_colonne() -> None:
    """⚠️ **Relevé en revue (axe B)** : aucune surface n'ancrait *quelle colonne porte quel métal*.

    Une permutation `medailles_argent` ↔ `medailles_bronze` restait verte partout. Ici les trois
    compteurs d'un même club sont **distincts** (3 / 2 / 1), donc toute permutation tombe.
    """
    # Quatre catégories : la 1 et la 4 ont trois archers (donc un bronze à décerner), la 2 et la 3
    # un seul. Le club 1 rafle trois ors et un bronze — trois compteurs distincts sur une ligne.
    palmares = _palmares(
        {1: 1, 2: 2, 3: 1, 4: 1, 5: 1, 6: 3, 7: 3, 8: 2},
        categories={1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 6: 4, 7: 4, 8: 4},
    )
    par_categorie = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}))

    classement = classer_clubs(palmares, par_categorie)

    assert _decompte(classement, 1) == (3, 0, 1), "ors des cat. 1/2/3, bronze de la cat. 1"
    assert _decompte(classement, 2) == (0, 1, 1), "argent de la cat. 1, bronze de la cat. 4"
    assert _decompte(classement, 3) == (1, 1, 0), "or et argent de la cat. 4"


def test_toute_portee_est_rangee_dans_un_camp() -> None:
    """⚠️ **Relevé en revue (axe D)** : `PORTEES_INTER_CLUBS` est une liste **positive**, et rien
    ne la reliait à l'énumération. Ajouter `EQUIPE` (annoncée en attente — EPIC-13, ADR-0028) la
    ferait entrer aux podiums, au PDF et à l'écran, et le décompte l'ignorerait **en silence**.

    Un commentaire d'avertissement existe dans `podium.py`, mais c'est le seul artefact que rien ne
    vérifie (règle 13). Ce test, lui, rougit — quatre lignes contre une US de diagnostic.
    """
    assert PORTEES_INTER_CLUBS | {PorteePodium.CLUB} == set(PorteePodium)


def test_le_decompte_double_quand_le_tournoi_n_a_qu_une_categorie() -> None:
    """⚠️ **Limite trouvée en revue (axe D)**, et elle borne l'arbitrage du 04/09/2026.

    Cumuler *scratch* et *catégorie* compte deux fois l'or, au motif que l'organisateur remet bien
    deux médailles. **Faux si le tournoi n'a qu'une catégorie** : les deux blocs contiennent alors
    les mêmes archers aux mêmes rangs — un seul jeu de médailles est remis, deux sont comptés.

    Le cas est **visible à l'écran** (deux blocs de podium aux mêmes noms) et l'organisateur qui
    règle deux portées identiques a demandé cette duplication. Il est donc **documenté** (ADR-0104
    §4, CA, fiche de recette) plutôt que corrigé — dédoublonner casserait le cas nominal, où deux
    médailles sont réellement remises. Ce test existe pour que la limite ne se redécouvre pas au
    pied du podium.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})  # une seule catégorie : le défaut de `_ligne`
    deux_portees = ReglagePodiums(portees=frozenset({PorteePodium.SCRATCH, PorteePodium.CATEGORIE}))

    classement = classer_clubs(palmares, deux_portees)

    assert _decompte(classement, 1) == (2, 0, 0), "deux ors comptés, un seul remis"


def test_le_decompte_n_est_plus_provisoire_quand_les_trois_metaux_sont_decernes() -> None:
    """⚠️ **Relevé en revue (axe D)** : `bloc.en_attente` est vrai dès qu'un archer du groupe est
    en lice, **fût-ce pour la 5ᵉ place**.

    Le classement annonçait « décompte provisoire » sous des podiums qui n'affichaient, eux, aucune
    réserve : l'écran se contredisait sur la même page, et l'organisateur retenait le trophée.
    """
    palmares = _palmares({1: 1, 2: 2, 3: 3, 4: 4})
    # Un archer encore en lice pour un rang **au-delà du bronze** : le podium est complet, le
    # décompte ne peut plus bouger.
    en_lice_hors_medaille = tuple(
        replace(ligne, en_lice=True) if ligne.archer_id == 8 else ligne for ligne in palmares.lignes
    )

    classement = classer_clubs(replace(palmares, lignes=en_lice_hors_medaille), _SCRATCH)

    assert classement.provisoire is False, "les trois métaux sont décernés, plus rien ne bouge"
