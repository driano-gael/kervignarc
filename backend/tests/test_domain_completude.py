"""Tests de la politique pure de **complétude** d'un tournoi (E12US005) — dérivés du CA, avant impl.

Source : `stories/E12-pilotage-jour-j.md`, E12US005, puce « CA » (répond à « qu'est-ce qui manque »,
**pas** une barre ; sportif et hors sportif comptés **séparément** — `D-17` ; qualification en
cibles, classement *prêt / en attente*, paiements N/total ; `sportif_complet` pilote l'avertissement
avant *terminé*) et l'arbitrage de **séquencement** des phases éliminatoires (EPIC-05 non livré :
ligne `À_VENIR` qui ne bloque pas). Domaine pur : on appelle `evaluer_completude` sur des décomptes.
"""

from __future__ import annotations

from domain.completude import (
    CLE_CLASSEMENT,
    CLE_PAIEMENTS,
    CLE_PHASES_ELIMINATOIRES,
    CLE_QUALIFICATION,
    EtatSection,
    LigneCompletude,
    evaluer_completude,
)


def _ligne(completude_lignes: tuple[LigneCompletude, ...], cle: str) -> LigneCompletude:
    """La ligne d'une clé dans une section (échoue si absente : le contrat garantit sa présence)."""
    return next(ligne for ligne in completude_lignes if ligne.cle == cle)


# --- Séparation sportif / hors sportif (`D-17`) -----------------------------------------------


def test_le_sportif_et_le_hors_sportif_sont_deux_sections_distinctes() -> None:
    """`D-17` : « terminé » fige le sportif, pas les paiements — les deux sont comptés à part."""
    c = evaluer_completude(qualif=(30, 30), paiements=(144, 156))

    cles_sportif = {ligne.cle for ligne in c.sportif}
    cles_hors = {ligne.cle for ligne in c.hors_sportif}
    assert cles_sportif == {CLE_QUALIFICATION, CLE_PHASES_ELIMINATOIRES, CLE_CLASSEMENT}
    assert cles_hors == {CLE_PAIEMENTS}


# --- Qualification (en cibles) ----------------------------------------------------------------


def test_qualification_complete_est_ok() -> None:
    """« Qualification OK 30/30 cibles » : toutes les cibles terminées."""
    c = evaluer_completude(qualif=(30, 30), paiements=(0, 0))

    qualif = _ligne(c.sportif, CLE_QUALIFICATION)
    assert qualif.etat is EtatSection.OK
    assert (qualif.fait, qualif.total) == (30, 30)


def test_qualification_partielle_est_en_alerte() -> None:
    """« 3/4 duels ⚠️ » côté qualification : des cibles restent — alerte, avec le décompte."""
    c = evaluer_completude(qualif=(28, 30), paiements=(0, 0))

    qualif = _ligne(c.sportif, CLE_QUALIFICATION)
    assert qualif.etat is EtatSection.ALERTE
    assert (qualif.fait, qualif.total) == (28, 30)


def test_qualification_sans_cible_placee_est_en_attente() -> None:
    """Aucune cible placée : rien à terminer encore — « en attente », pas un « 0/0 OK » trompeur."""
    c = evaluer_completude(qualif=(0, 0), paiements=(0, 0))

    assert _ligne(c.sportif, CLE_QUALIFICATION).etat is EtatSection.EN_ATTENTE


# --- Classement : dérivé de la qualification --------------------------------------------------


def test_classement_pret_quand_la_qualification_est_complete() -> None:
    """Le classement est *prêt* (définitif) dès que toutes les séries sont closes."""
    c = evaluer_completude(qualif=(30, 30), paiements=(0, 0))

    assert _ligne(c.sportif, CLE_CLASSEMENT).etat is EtatSection.OK


def test_classement_en_attente_tant_que_la_qualification_n_est_pas_finie() -> None:
    """« Classement en attente » tant que la qualification tourne — pas encore définitif."""
    c = evaluer_completude(qualif=(28, 30), paiements=(0, 0))

    assert _ligne(c.sportif, CLE_CLASSEMENT).etat is EtatSection.EN_ATTENTE


# --- Phases éliminatoires : séquencées (EPIC-05) ----------------------------------------------


def test_phases_eliminatoires_sont_a_venir_et_ne_bloquent_pas_le_sportif() -> None:
    """Séquencement : les duels (EPIC-05) sont `À_VENIR` — présents sans jamais figer le sportif.

    Sinon aucun tournoi (qualification seule, courant en salle 18 m) ne pourrait être « complet ».
    """
    c = evaluer_completude(qualif=(30, 30), paiements=(0, 0))

    phases = _ligne(c.sportif, CLE_PHASES_ELIMINATOIRES)
    assert phases.etat is EtatSection.A_VENIR
    assert c.sportif_complet is True  # les phases à venir n'empêchent pas la complétude sportive


# --- Paiements (hors sportif) -----------------------------------------------------------------


def test_paiements_tous_regles_est_ok() -> None:
    c = evaluer_completude(qualif=(30, 30), paiements=(156, 156))

    paie = _ligne(c.hors_sportif, CLE_PAIEMENTS)
    assert paie.etat is EtatSection.OK
    assert (paie.fait, paie.total) == (156, 156)


def test_paiements_incomplets_sont_en_alerte_avec_le_decompte() -> None:
    """« Paiements ! 144/156 » : 12 archers n'ont pas réglé — alerte, décompte préservé."""
    c = evaluer_completude(qualif=(30, 30), paiements=(144, 156))

    paie = _ligne(c.hors_sportif, CLE_PAIEMENTS)
    assert paie.etat is EtatSection.ALERTE
    assert (paie.fait, paie.total) == (144, 156)


def test_aucun_archer_les_paiements_sont_ok_a_vide() -> None:
    """Rien à encaisser : les paiements ne sont pas une alerte (0/0 réglé)."""
    c = evaluer_completude(qualif=(0, 0), paiements=(0, 0))

    assert _ligne(c.hors_sportif, CLE_PAIEMENTS).etat is EtatSection.OK


# --- `sportif_complet` : le verrou de l'avertissement avant « terminer » ----------------------


def test_sportif_complet_ne_depend_que_du_sportif_pas_des_paiements() -> None:
    """`D-17` : des paiements en retard n'empêchent pas de terminer — le sportif seul décide.

    Qualification complète mais 12 impayés : `sportif_complet` reste vrai (les paiements resteront
    modifiables après *terminé*), l'écran signale les impayés sans bloquer.
    """
    c = evaluer_completude(qualif=(30, 30), paiements=(144, 156))

    assert c.sportif_complet is True


def test_sportif_incomplet_quand_la_qualification_n_est_pas_finie() -> None:
    """Qualification en cours : `sportif_complet` faux → l'écran avertira avant de terminer."""
    c = evaluer_completude(qualif=(28, 30), paiements=(156, 156))

    assert c.sportif_complet is False
