"""Tests de l'agrégat `Equipe` et de sa conformité (E13US002) — sans infrastructure.

Écrits **depuis le CA** (règle 9), avant le code. Les règles d'**ensemble** — membre du même
tournoi, une équipe par type, nom unique — ne sont pas ici : le domaine ne voit qu'une équipe à la
fois, elles vivent dans `ServiceEquipes` (cf. `test_service_equipes`).
"""

from __future__ import annotations

import pytest

from domain.categorie import Categorie, SexeCategorie
from domain.equipe import (
    EcartComposition,
    Equipe,
    ProfilMembre,
    TypeEquipe,
    conflit_de_type,
    ecarts_de_composition,
)
from domain.erreurs import (
    ArcherDejaMembre,
    ArcherNonMembre,
    EffectifEquipeInvalide,
    NomEquipeInvalide,
)

H = SexeCategorie.HOMME
F = SexeCategorie.FEMME


def _profil(arme: str | None = "Classique", sexe: SexeCategorie | None = H) -> ProfilMembre:
    return ProfilMembre(arme=arme, sexe=sexe)


# --- CA 1 : création, effectif prérempli selon le type ---------------------------------------


def test_une_equipe_standard_attend_trois_archers_par_defaut() -> None:
    equipe = Equipe.creer(tournoi_id=1, nom="Kervignac 1", type=TypeEquipe.STANDARD)

    assert equipe.id is None
    assert equipe.tournoi_id == 1
    assert equipe.nom == "Kervignac 1"
    assert equipe.effectif_attendu == 3
    assert equipe.membres == ()


def test_une_equipe_mixte_attend_deux_archers_par_defaut() -> None:
    equipe = Equipe.creer(tournoi_id=1, nom="Mixte A", type=TypeEquipe.MIXTE)

    assert equipe.effectif_attendu == 2


def test_l_effectif_attendu_est_configurable() -> None:
    equipe = Equipe.creer(1, "Challenge", TypeEquipe.STANDARD, effectif_attendu=4)

    assert equipe.effectif_attendu == 4


@pytest.mark.parametrize("effectif", [0, -1])
def test_un_effectif_attendu_non_positif_est_refuse(effectif: int) -> None:
    with pytest.raises(EffectifEquipeInvalide):
        Equipe.creer(1, "Challenge", TypeEquipe.STANDARD, effectif_attendu=effectif)


def test_le_nom_est_normalise_et_ne_peut_pas_etre_vide() -> None:
    assert Equipe.creer(1, "  Kervignac 1  ", TypeEquipe.STANDARD).nom == "Kervignac 1"
    with pytest.raises(NomEquipeInvalide):
        Equipe.creer(1, "   ", TypeEquipe.STANDARD)


def test_modifier_change_nom_type_et_effectif_en_gardant_les_membres() -> None:
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD).ajouter_membre(10)

    modifiee = equipe.modifier(nom="B", type=TypeEquipe.MIXTE, effectif_attendu=2)

    assert (modifiee.nom, modifiee.type, modifiee.effectif_attendu) == ("B", TypeEquipe.MIXTE, 2)
    assert modifiee.membres == (10,)
    assert modifiee.tournoi_id == 1


def test_modifier_sans_effectif_reprend_le_defaut_du_type() -> None:
    """Changer de type sans dire l'effectif : on reprend le défaut FFTA du nouveau type."""
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD)

    assert equipe.modifier(nom="A", type=TypeEquipe.MIXTE).effectif_attendu == 2


def test_modifier_applique_les_memes_regles_que_creer() -> None:
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD)
    with pytest.raises(NomEquipeInvalide):
        equipe.modifier(nom=" ", type=TypeEquipe.STANDARD)
    with pytest.raises(EffectifEquipeInvalide):
        equipe.modifier(nom="A", type=TypeEquipe.STANDARD, effectif_attendu=0)


# --- CA 1 : membres ----------------------------------------------------------------------------


def test_ajouter_puis_retirer_un_membre() -> None:
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD).ajouter_membre(10).ajouter_membre(11)

    assert equipe.membres == (10, 11)
    assert equipe.retirer_membre(10).membres == (11,)


def test_un_archer_ne_figure_pas_deux_fois_dans_la_meme_equipe() -> None:
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD).ajouter_membre(10)

    with pytest.raises(ArcherDejaMembre):
        equipe.ajouter_membre(10)


def test_retirer_un_archer_absent_est_refuse() -> None:
    with pytest.raises(ArcherNonMembre):
        Equipe.creer(1, "A", TypeEquipe.STANDARD).retirer_membre(10)


def test_ajouter_au_dela_de_l_effectif_n_est_pas_bloque() -> None:
    """CA 4 : la composition est signalée, jamais bloquée — y compris le surnombre."""
    equipe = Equipe.creer(1, "Mixte", TypeEquipe.MIXTE)
    for archer_id in (10, 11, 12):
        equipe = equipe.ajouter_membre(archer_id)

    assert len(equipe.membres) == 3


# --- CA 4 : conformité ------------------------------------------------------------------------


def _standard(effectif: int = 3) -> Equipe:
    return Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=effectif)


def _mixte() -> Equipe:
    return Equipe.creer(1, "M", TypeEquipe.MIXTE)


def test_une_equipe_standard_complete_et_homogene_est_conforme() -> None:
    assert ecarts_de_composition(_standard(), [_profil(), _profil(), _profil()]) == ()


def test_une_equipe_mixte_un_homme_une_femme_est_conforme() -> None:
    assert ecarts_de_composition(_mixte(), [_profil(sexe=H), _profil(sexe=F)]) == ()


def test_trop_peu_de_membres() -> None:
    ecarts = ecarts_de_composition(_standard(), [_profil(), _profil()])

    assert ecarts == (EcartComposition.EFFECTIF_INSUFFISANT,)


def test_trop_de_membres() -> None:
    ecarts = ecarts_de_composition(_standard(), [_profil()] * 4)

    assert ecarts == (EcartComposition.EFFECTIF_EXCEDENTAIRE,)


def test_l_effectif_se_juge_contre_l_effectif_configure() -> None:
    assert ecarts_de_composition(_standard(effectif=4), [_profil()] * 4) == ()


def test_armes_differentes() -> None:
    ecarts = ecarts_de_composition(
        _standard(), [_profil("Classique"), _profil("Classique"), _profil("Poulies")]
    )

    assert ecarts == (EcartComposition.ARMES_DIFFERENTES,)


def test_l_arme_se_compare_sans_casse_ni_espaces() -> None:
    """L'arme est un texte libre de catégorie : « classique » et « Classique » sont la même."""
    profils = [_profil("Classique"), _profil("classique"), _profil(" CLASSIQUE ")]

    assert ecarts_de_composition(_standard(), profils) == ()


def test_une_arme_inconnue_rend_le_critere_non_verifiable() -> None:
    ecarts = ecarts_de_composition(_standard(), [_profil(), _profil(), _profil(arme=None)])

    assert ecarts == (EcartComposition.ARME_NON_VERIFIABLE,)


def test_deux_armes_connues_differentes_restent_signalees_malgre_une_inconnue() -> None:
    """Ce qui est su n'est pas effacé par ce qui ne l'est pas : on ne devine dans aucun sens."""
    profils = [_profil("Classique"), _profil("Poulies"), _profil(arme=None)]

    assert set(ecarts_de_composition(_standard(), profils)) == {
        EcartComposition.ARMES_DIFFERENTES,
        EcartComposition.ARME_NON_VERIFIABLE,
    }


def test_mixte_sans_femme() -> None:
    ecarts = ecarts_de_composition(_mixte(), [_profil(sexe=H), _profil(sexe=H)])

    assert ecarts == (EcartComposition.MIXITE_MANQUANTE,)


def test_mixte_sans_homme() -> None:
    ecarts = ecarts_de_composition(_mixte(), [_profil(sexe=F), _profil(sexe=F)])

    assert ecarts == (EcartComposition.MIXITE_MANQUANTE,)


def test_standard_de_sexes_differents() -> None:
    """FFTA §6.4 : l'épreuve standard se tire par sexe."""
    ecarts = ecarts_de_composition(_standard(), [_profil(sexe=H), _profil(sexe=H), _profil(sexe=F)])

    assert ecarts == (EcartComposition.SEXES_DIFFERENTS,)


@pytest.mark.parametrize("sexe_inconnu", [None, SexeCategorie.MIXTE])
def test_un_sexe_inconnu_rend_le_critere_non_verifiable(
    sexe_inconnu: SexeCategorie | None,
) -> None:
    """Catégorie sans sexe, ou catégorie « mixte » : le sexe de l'archer n'est pas connu."""
    ecarts = ecarts_de_composition(_standard(), [_profil(), _profil(), _profil(sexe=sexe_inconnu)])

    assert ecarts == (EcartComposition.SEXE_NON_VERIFIABLE,)


def test_mixte_avec_un_sexe_inconnu_ne_conclut_pas_a_une_mixite_manquante() -> None:
    """Le membre au sexe inconnu est peut-être la femme qui manque : on ne tranche pas."""
    ecarts = ecarts_de_composition(_mixte(), [_profil(sexe=H), _profil(sexe=None)])

    assert ecarts == (EcartComposition.SEXE_NON_VERIFIABLE,)


def test_une_equipe_vide_ne_signale_que_son_effectif() -> None:
    """Sans membre, arme et sexe n'ont rien à comparer : seul l'effectif est en défaut."""
    assert ecarts_de_composition(_mixte(), []) == (EcartComposition.EFFECTIF_INSUFFISANT,)


def test_les_ecarts_sont_cumules_dans_un_ordre_stable() -> None:
    ecarts = ecarts_de_composition(_standard(), [_profil("Classique", H), _profil("Poulies", F)])

    assert ecarts == (
        EcartComposition.EFFECTIF_INSUFFISANT,
        EcartComposition.ARMES_DIFFERENTES,
        EcartComposition.SEXES_DIFFERENTS,
    )


# --- Compléments de revue (01/10/2026) ---------------------------------------------------------


def test_standard_de_sexes_differents_et_un_sexe_inconnu() -> None:
    """CA 4 : la différence établie reste signalée, l'inconnu rend le critère non vérifiable."""
    profils = [_profil(sexe=H), _profil(sexe=F), _profil(sexe=SexeCategorie.MIXTE)]

    assert set(ecarts_de_composition(_standard(), profils)) == {
        EcartComposition.SEXES_DIFFERENTS,
        EcartComposition.SEXE_NON_VERIFIABLE,
    }


def test_une_arme_blanche_est_une_arme_inconnue() -> None:
    ecarts = ecarts_de_composition(_standard(), [_profil(), _profil(), _profil(arme="   ")])

    assert ecarts == (EcartComposition.ARME_NON_VERIFIABLE,)


def test_mixte_a_effectif_configure_ne_signale_que_l_effectif() -> None:
    """Seul l'effectif est configurable (arbitrage du 01/10/2026) : H, H, F reste mixte."""
    profils = [_profil(sexe=H), _profil(sexe=H), _profil(sexe=F)]
    a_quatre = Equipe.creer(1, "M", TypeEquipe.MIXTE, effectif_attendu=4)

    assert ecarts_de_composition(a_quatre, profils) == (EcartComposition.EFFECTIF_INSUFFISANT,)
    assert ecarts_de_composition(a_quatre.modifier("M", TypeEquipe.MIXTE, 3), profils) == ()


def test_l_effectif_attendu_est_borne_a_99() -> None:
    assert Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=99).effectif_attendu == 99
    with pytest.raises(EffectifEquipeInvalide):
        Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=100)
    with pytest.raises(EffectifEquipeInvalide):
        Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=2**63)


def test_modifier_sans_effectif_ni_changement_de_type_garde_l_effectif_configure() -> None:
    """Renommer une équipe ne doit pas ramener en douce son effectif au défaut FFTA."""
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=4)

    assert equipe.modifier(nom="B", type=TypeEquipe.STANDARD).effectif_attendu == 4


def test_modifier_sans_effectif_avec_changement_de_type_prend_le_defaut_du_nouveau_type() -> None:
    equipe = Equipe.creer(1, "A", TypeEquipe.STANDARD, effectif_attendu=4)

    assert equipe.modifier(nom="A", type=TypeEquipe.MIXTE).effectif_attendu == 2


def _persistee(equipe_id: int, type: TypeEquipe) -> Equipe:
    return Equipe(tournoi_id=1, nom=f"E{equipe_id}", type=type, effectif_attendu=3, id=equipe_id)


def test_conflit_de_type_trouve_deux_equipes_distinctes_du_meme_type() -> None:
    """CA 3 : au plus une équipe par type."""
    a = _persistee(1, TypeEquipe.STANDARD)
    b = _persistee(2, TypeEquipe.STANDARD)

    assert conflit_de_type([a], [_persistee(3, TypeEquipe.MIXTE), b]) == (a, b)


def test_conflit_de_type_ignore_la_meme_equipe() -> None:
    a = _persistee(1, TypeEquipe.STANDARD)

    assert conflit_de_type([a], [a]) is None


def test_conflit_de_type_ignore_les_types_differents() -> None:
    assert (
        conflit_de_type([_persistee(1, TypeEquipe.STANDARD)], [_persistee(2, TypeEquipe.MIXTE)])
        is None
    )


def test_conflit_de_type_sans_equipe() -> None:
    assert conflit_de_type([], []) is None
    assert conflit_de_type([_persistee(1, TypeEquipe.STANDARD)], []) is None


def test_le_profil_d_un_membre_sans_categorie_est_inconnu() -> None:
    assert ProfilMembre.de_categorie(None) == ProfilMembre(arme=None, sexe=None)


def test_le_profil_d_un_membre_est_lu_sur_sa_categorie() -> None:
    """CA 5 : l'arme et le sexe d'un archer sont ceux de sa catégorie."""
    categorie = Categorie.creer(1, "Femme arc classique", arme="Classique", sexe=F)

    assert ProfilMembre.de_categorie(categorie) == ProfilMembre(arme="Classique", sexe=F)
