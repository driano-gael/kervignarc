"""Tests de la **préséance de rôle** sur une écriture concurrente (E16US020, ADR-0107).

Dérivés des **CA** d'E16US020 (`stories/E16-retours-maquettes.md`) et des décisions d'ADR-0107,
**avant** l'implémentation (règle 9) : le rôle supérieur écrase, l'inférieur est refusé, à rôles
égaux la règle n'arbitre rien, le rôle est celui de la **garde** et jamais du message, et une
annulation de validation remet la préséance à zéro.

⚠️ **Le rang du MILIEU s'écrit par `POST /corrections`, et par lui seul** — pas par la saisie, qui
n'admet que l'admin et le poste. C'est son unique site d'inscription en base : les tests qui
l'exercent (§ « Le rang du milieu ») sont donc les seuls à prouver l'ordre décidé par ADR-0107 §1
ailleurs que dans l'énumération. *(Rédaction corrigée en 2ᵉ passe : la précédente affirmait
qu'aucune route ne faisait écrire un scoreur — c'était faux, et c'est ce qui avait laissé
`corriger_volee` sans préséance.)*
"""

from __future__ import annotations

import pytest

from application.erreurs import EcritureDeRoleInferieur
from application.saisie import _LIBELLE_ROLE, ContexteSaisie, _refuser_role_inferieur
from domain.erreurs import VoleeNonVerrouillee, VoleeVerrouillee
from domain.grain_validation import GrainValidation
from domain.role import Role
from domain.serie import Serie, Volee
from tests.test_service_saisie import _DEPART, ZONES_SIMPLE, Montage, _v

_PHASE = 4
"""La phase où se tire la feuille (ADR-0082) — inerte ici, cf. `test_domain_serie.py`."""


def _saisir(serie: Serie, numero: int, role: Role | None, *, bareme: int = 2) -> Serie:
    """Saisit une volée au nom de `role` ; valeurs sans importance pour la préséance."""
    return serie.saisir_volee(
        numero,
        _v("10", "9", "8"),
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        nb_volees_bareme=bareme,
        role_de_saisie=role,
    )


def _contexte_poste() -> ContexteSaisie:
    """Le contexte que la garde construit pour un **poste de cible** (`autoriser_saisie`)."""
    return ContexteSaisie(cible_index=1, depart_id=_DEPART)


# --- L'ordre décidé par ADR-0107 §1 ---------------------------------------------------------


def test_l_ordre_des_roles_est_poste_puis_scoreur_puis_admin() -> None:
    """ADR-0107 §1 : `poste de cible < scoreur < admin`, les trois identités réelles du dépôt.

    ⚠️ Cet ordre est la **décision** ; l'écrire en assertion l'épingle contre une renumérotation
    silencieuse de l'énumération, que rien d'autre ne verrait.
    """
    assert Role.POSTE_DE_CIBLE < Role.SCOREUR < Role.ADMIN


# --- Ce que le domaine retient : le rôle du dernier écrivain ---------------------------------


def test_la_volee_retient_le_role_de_qui_l_a_ecrite() -> None:
    """La préséance suppose un état persisté (ADR-0107 § Conséquences) : la volée le porte."""
    serie = _saisir(Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7), 1, Role.POSTE_DE_CIBLE)

    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.POSTE_DE_CIBLE


def test_une_reecriture_remplace_le_role_retenu() -> None:
    """La préséance est celle de la **dernière** écriture, pas de la première."""
    serie = _saisir(Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7), 1, Role.POSTE_DE_CIBLE)

    serie = _saisir(serie, 1, Role.ADMIN)

    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.ADMIN


def test_une_volee_ecrite_sans_role_n_en_retient_aucun() -> None:
    """Les surfaces mono-rôle (Big Shoot Off) n'ont aucune préséance à revendiquer.

    ⚠️ C'est ce qui rend la règle **inerte hors qualification** par construction, et non par un cas
    particulier : `role_de_saisie=None` ne revendique rien, donc n'oppose rien.
    """
    serie = _saisir(Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7), 1, None)

    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is None


# --- CA « une annulation de validation remet la préséance à ZÉRO » ---------------------------


def test_annuler_une_validation_efface_la_preseance_du_lot() -> None:
    """CA d'E16US020 : sans cette remise à zéro, qui annule verrouille contre qui doit corriger."""
    serie = Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7)
    serie = _saisir(serie, 1, Role.ADMIN)
    serie = _saisir(serie, 2, Role.ADMIN)
    serie = serie.valider("MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=2)

    serie = serie.annuler_validation(1, par="MARTIN")

    assert [v.role_de_saisie for v in serie.volees] == [None, None]


def test_annuler_n_efface_pas_la_preseance_des_autres_lots() -> None:
    """La remise à zéro suit **le lot rouvert**, comme l'annulation elle-même (E16US019)."""
    grain = GrainValidation.toutes_les_n_volees(1)
    serie = Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7)
    serie = _saisir(serie, 1, Role.ADMIN, bareme=4)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    serie = _saisir(serie, 2, Role.ADMIN, bareme=4)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)

    serie = serie.annuler_validation(1, par="MARTIN")

    assert [v.role_de_saisie for v in serie.volees] == [None, Role.ADMIN]


# --- CA « le rôle supérieur écrase, l'inférieur est refusé » ---------------------------------


def test_un_role_inferieur_est_refuse() -> None:
    """CA : l'admin a écrit, le poste de cible ne peut plus l'écraser → `EcritureDeRoleInferieur`.

    C'est le **cas adverse arbitré le 12/09/2026** : la cible ne se corrige plus elle-même, le
    recours est l'organisateur. Refus assumé, pas effet de bord.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))  # admin

    with pytest.raises(EcritureDeRoleInferieur):
        m.service.saisir_volee(
            m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
        )


def test_le_refus_laisse_la_volee_intacte() -> None:
    """Un refus ne doit rien écrire : sinon l'écrasement refusé aurait lieu quand même."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))

    with pytest.raises(EcritureDeRoleInferieur):
        m.service.saisir_volee(
            m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
        )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("10", "9", "8")


def test_un_role_superieur_ecrase() -> None:
    """CA : le poste a écrit, l'admin corrige — l'écriture passe, la préséance devient la sienne."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
    )

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("10", "9", "8")
    assert volee.role_de_saisie is Role.ADMIN


def test_une_volee_neuve_n_oppose_aucune_preseance() -> None:
    """Aucune écriture antérieure : le rang le plus bas écrit sans rien avoir à franchir."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")

    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None and serie.volee(1) is not None


# --- CA « à rôles égaux, la règle n'arbitre rien » (test NÉGATIF, ADR-0107 §3) ----------------


def test_a_roles_egaux_le_second_gagne_sans_conflit() -> None:
    """ADR-0107 §3 : deux postes de cible écrivent, le second gagne — **aucun** refus.

    ⚠️ **Test négatif exigé par la décision elle-même** : c'est le renoncement le plus coûteux de
    l'US (le cas le plus fréquent en salle), et sans cette assertion il serait invisible dans le
    code. Le faire rougir un jour signifie qu'on a livré le refus symétrique **écarté** par le
    commanditaire, pas qu'on a corrigé un bug. Critère de réouverture : ADR-0107 §3.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
    )

    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("10", "10", "10"), contexte=_contexte_poste()
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("10", "10", "10")


def test_deux_ecritures_admin_ne_se_refusent_pas() -> None:
    """Même règle au sommet de l'ordre : l'égalité n'arbitre pas davantage chez l'admin."""
    m = Montage()
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"))

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "10", "10"))

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("10", "10", "10")


# --- CA « le rôle est celui de la GARDE, jamais celui du message » ---------------------------


def test_un_poste_ne_gagne_aucune_autorite_en_se_declarant_admin() -> None:
    """CA + ADR-0107 §2 : `saisie_par` est **déclaratif**, donc sans effet sur la préséance.

    ⚠️ **C'est le piège central de l'US** : dériver le rôle du corps de requête livrerait une
    hiérarchie qu'un poste contourne en signant « Administrateur ».
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))  # admin

    with pytest.raises(EcritureDeRoleInferieur):
        m.service.saisir_volee(
            m.tournoi_id,
            m.archer_id,
            1,
            _v("6", "6", "6"),
            "Administrateur",  # marqueur déclaratif, sans aucune autorité
            _contexte_poste(),
        )


def test_le_marqueur_declare_ne_confere_pas_la_preseance_retenue() -> None:
    """Le rôle retenu est celui de la garde, même quand le marqueur déclare autre chose."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")

    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), "Administrateur", _contexte_poste()
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.POSTE_DE_CIBLE


# --- Conjonction avec les gardes existantes --------------------------------------------------


def test_une_volee_verrouillee_refuse_tout_le_monde_avant_la_preseance() -> None:
    """Le verrou prime la préséance : une volée validée se refuse en `VoleeVerrouillee`, pas en 409.

    ⚠️ **Défaut de conjonction** : intervertir les deux gardes rendrait un 409 « rôle inférieur » là
    où l'écran doit lire « validée, passez par une correction » — deux recours différents.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 2, _v("10", "9", "8"))
    m.service.valider(m.tournoi_id, m.archer_id, "MARTIN")

    with pytest.raises(VoleeVerrouillee):
        m.service.saisir_volee(
            m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
        )


def test_apres_annulation_le_poste_peut_ressaisir_ce_qu_un_admin_avait_ecrit() -> None:
    """CA d'E16US020, bout en bout : l'annulation rend la volée à ceux qui doivent la corriger.

    Sans la remise à zéro, l'admin qui annule resterait le dernier écrivain et verrouillerait la
    volée contre le poste de cible — l'US contredirait alors le CA d'E16US019.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 2, _v("10", "9", "8"))
    m.service.valider(m.tournoi_id, m.archer_id, "MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")

    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"), contexte=_contexte_poste()
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("6", "6", "6")


def test_la_preseance_se_reconstitue_apres_une_ressaisie_en_correction() -> None:
    """Remise à zéro ≠ immunité permanente : la première écriture d'après repose une préséance."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 2, _v("10", "9", "8"))
    m.service.valider(m.tournoi_id, m.archer_id, "MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"))  # admin reprend la main

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.ADMIN


# --- Le rang du MILIEU, par sa seule route d'écriture (E16US020, 2ᵉ passe) ----------------------
#
# ⚠️ Ces tests n'existaient pas en 1ʳᵉ passe, et quatre axes de revue ont trouvé le même trou :
# `corriger_volee` n'apposait aucune préséance, donc `Role.SCOREUR` n'était jamais écrit et la
# comparaison n'était exercée qu'avec le couple poste/admin. Remplacer la garde par
# `role < existante.role_de_saisie and role is Role.POSTE_DE_CIBLE` laissait alors tout vert.


def test_corriger_repose_une_preseance_de_scoreur() -> None:
    """`POST /corrections` est une écriture de rang 2 : elle revendique, comme toute écriture.

    ⚠️ C'est le **seul** site où `Role.SCOREUR` s'inscrit en base : sans lui, le rang du milieu
    décidé par ADR-0107 §1 n'existerait que dans l'énumération.
    """
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")

    m.service.corriger_volee(
        m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="MARTIN", role=Role.SCOREUR
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.SCOREUR


def test_le_poste_ne_peut_plus_ecraser_une_correction_de_scoreur() -> None:
    """Le croisement (scoreur, poste) — celui que le questionnaire S09 visait en premier.

    ⚠️ **C'était le défaut de la 1ʳᵉ passe** : le scoreur corrigeait une volée rouverte, sa
    correction ne revendiquait rien, et la tablette l'écrasait en silence — le défaut même que
    l'US existe pour fermer, déplacé d'un endpoint à l'autre.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")
    m.service.corriger_volee(
        m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="MARTIN", role=Role.SCOREUR
    )

    with pytest.raises(EcritureDeRoleInferieur):
        m.service.saisir_volee(
            m.tournoi_id, m.archer_id, 1, _v("1", "1", "1"), contexte=_contexte_poste()
        )


def test_l_admin_ecrase_une_correction_de_scoreur() -> None:
    """L'autre moitié du couple haut : le rang 3 passe par-dessus le rang 2."""
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")
    m.service.corriger_volee(
        m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="MARTIN", role=Role.SCOREUR
    )

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "10", "10"))

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.ADMIN


# --- CA « l'écran dit POURQUOI le refus tombe » : le message nomme le rôle ----------------------


@pytest.mark.parametrize(
    ("role_qui_a_ecrit", "attendu"),
    [(Role.SCOREUR, "un scoreur"), (Role.ADMIN, "l'organisateur")],
)
def test_le_refus_nomme_le_role_qui_a_ecrit(role_qui_a_ecrit: Role, attendu: str) -> None:
    """CA : « un refus muet serait pire que l'écrasement qu'il remplace ».

    ⚠️ Sans cette assertion, `_LIBELLE_ROLE` n'est couvert par rien : remplacer le message par
    « Écriture refusée. » laissait les suites vertes — l'écran affichait alors un refus anonyme,
    exactement ce que le CA écarte. Relevé en revue (axe B).
    """
    volee = Volee(numero=1, valeurs=_v("10", "9", "8"), role_de_saisie=role_qui_a_ecrit)

    with pytest.raises(EcritureDeRoleInferieur) as refus:
        _refuser_role_inferieur(volee, Role.POSTE_DE_CIBLE)

    assert attendu in str(refus.value)


def test_chaque_rang_sait_se_nommer_dans_un_refus() -> None:
    """Un rang ajouté sans libellé transformerait un 409 métier en 500 (axe A).

    ⚠️ `mypy` ne vérifie pas l'exhaustivité d'un `dict[Role, str]` : l'écart se voit ici, pas en
    salle.
    """
    assert set(_LIBELLE_ROLE) == set(Role)


# --- CA « le sens descendant » : quel est le VRAI recours (E16US020, 2ᵉ passe) ------------------


def test_le_recours_au_refus_vers_le_bas_est_la_ressaisie_par_l_organisateur() -> None:
    """⚠️ **Le recours annoncé en 1ʳᵉ passe n'existait pas**, et cinq artefacts l'affirmaient.

    « L'organisateur annule la validation » échoue dans les deux seuls états où le 409 tombe : une
    volée non validée n'a **rien à annuler**. Le recours réel est qu'il ressaisisse lui-même — rang
    égal, donc accepté. Ce test épingle les deux moitiés, sans quoi la doc redivergera.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))  # admin, par erreur

    with pytest.raises(VoleeNonVerrouillee):
        m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("6", "6", "6"))  # il se corrige

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("6", "6", "6")


# --- CORRIGER respecte la préséance autant qu'elle en pose une (2ᵉ passe de revue) --------------


def test_un_scoreur_ne_peut_pas_corriger_par_dessus_une_ecriture_de_l_organisateur() -> None:
    """ADR-0107 §1 vaut pour **les deux** chemins d'écriture, pas seulement pour la saisie.

    ⚠️ **Défaut de la 2ᵉ passe** : `corriger_volee` *posait* un rang sans en *respecter* aucun. La
    règle se contournait alors par le **choix de l'endpoint** — un rang 2 écrasait un rang 3, et le
    rang stocké redescendait. Trois axes l'ont relevé indépendamment.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "10", "10"))  # admin ressaisit

    with pytest.raises(EcritureDeRoleInferieur):
        m.service.corriger_volee(
            m.tournoi_id, m.archer_id, 1, _v("1", "1", "1"), auteur="MARTIN", role=Role.SCOREUR
        )


def test_corriger_une_volee_verrouillee_reste_permis_a_tout_rang_habilite() -> None:
    """Le chemin NOMINAL de correction est inchangé : la garde sort tôt sur une volée verrouillée.

    ⚠️ Sans ce jumeau, resserrer la garde d'un cran fermerait le seul chemin de réparation d'une
    feuille signée — et rien ne le dirait.
    """
    m = Montage()
    m.saisir_serie_complete()  # saisie admin, donc rang ADMIN
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")

    m.service.corriger_volee(
        m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="MARTIN", role=Role.SCOREUR
    )

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.valeurs == _v("9", "9", "9")


def test_la_sortie_du_blocage_existe_et_tient_en_deux_gestes() -> None:
    """ADR-0107 §4 : la préséance ne verrouille **jamais** une volée pour toujours — la sortie.

    ⚠️ **Trouvé en 2ᵉ passe de revue (axe D) et non couvert jusque-là.** Quand le scoreur corrige
    une volée rouverte, la tablette est refusée — et `annuler_validation` refuse à son tour, la
    volée étant *déjà en correction*. Le geste de remise à zéro est donc **indisponible depuis
    l'état où le blocage se produit**. La sortie réelle tient en deux gestes, tous deux offerts par
    l'écran du scoreur : **refermer** la correction, puis **annuler** la validation. Sans ce test,
    la décision 4 serait fausse et rien ne le dirait.
    """
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")
    m.service.corriger_volee(
        m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="MARTIN", role=Role.SCOREUR
    )
    with pytest.raises(EcritureDeRoleInferieur):
        m.service.saisir_volee(
            m.tournoi_id, m.archer_id, 1, _v("1", "1", "1"), contexte=_contexte_poste()
        )
    with pytest.raises(VoleeNonVerrouillee):  # le geste de remise à zéro n'est pas disponible ICI
        m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")

    m.service.refermer_correction(m.tournoi_id, m.archer_id, 1, scoreur="MARTIN")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, auteur="MARTIN")

    m.service.saisir_volee(
        m.tournoi_id, m.archer_id, 1, _v("1", "1", "1"), contexte=_contexte_poste()
    )
    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None and volee.role_de_saisie is Role.POSTE_DE_CIBLE
