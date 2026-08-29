"""Tests du **niveau d'alerte** d'une préparation (E16US010) — dérivés du CA, avant impl.

Source : `stories/E16-retours-maquettes.md`, E16US010, puce « **CA — pastille de complétude en
liste** » : *« deux niveaux — incomplet (avertissement) et **impossible à lancer** (alerte
forte) »*, et le questionnaire A02 dont elle vient : *« sur cette liste laisse une pastille
d'alerte si tout n'est pas complet ; alerte forte si impossible de lancer en l'état »*.

Le niveau se **dérive** d'une `PreparationJalon` déjà évaluée (E16US012, ADR-0096) : le CA
d'E16US012 interdit nommément une seconde source de complétude, donc la pastille ne recalcule
aucune garde — elle traduit en **niveau d'alerte** ce que le jalon a déjà répondu.

Domaine pur : aucune I/O, on part de préparations construites par les politiques existantes.
"""

from __future__ import annotations

from domain.completude import Completude, EtatSection, LigneCompletude
from domain.jalon import (
    CLE_EFFECTIF,
    Jalon,
    NiveauPreparation,
    PreparationJalon,
    evaluer_demarrer,
    evaluer_terminer,
    niveau_de_preparation,
    resume_du_manque,
)
from domain.tournoi import MESSAGE_SANS_DEPART, StatutTournoi


def _demarrer(
    *,
    statut: StatutTournoi = StatutTournoi.BROUILLON,
    nb_creneaux: int = 2,
    nb_etapes_deroule: int = 3,
    effectif_suffisant: bool = True,
    inscrits: int = 40,
    minimum: int = 34,
) -> PreparationJalon:
    """Un « prêt à démarrer » dont rien ne manque — base des variations."""
    return evaluer_demarrer(
        statut=statut,
        nb_creneaux=nb_creneaux,
        nb_etapes_deroule=nb_etapes_deroule,
        effectif_suffisant=effectif_suffisant,
        inscrits=inscrits,
        minimum=minimum,
        cause_effectif=None if effectif_suffisant else "Il manque 26 inscrits sur 34.",
    )


def test_rien_ne_manque_ne_porte_aucune_pastille() -> None:
    """Le cas nominal : la ligne de liste reste nue.

    Une pastille sur tous les tournois ne dit plus rien — c'est la définition d'une alerte qui
    ne sert à rien.
    """
    assert niveau_de_preparation(_demarrer()) is NiveauPreparation.AUCUN


def test_sans_creneau_le_lancement_est_impossible_donc_alerte_forte() -> None:
    """« Impossible de lancer en l'état » (A02) → **alerte forte**.

    Sans créneau, `vers_pret` refusera : le tournoi ne peut pas partir, ce n'est pas un
    avertissement.
    """
    preparation = _demarrer(nb_creneaux=0)

    assert preparation.pret is False
    assert niveau_de_preparation(preparation) is NiveauPreparation.ALERTE


def test_effectif_insuffisant_est_une_alerte_forte() -> None:
    """L'autre garde bloquante du feu vert (E05US021) donne le même niveau.

    Le niveau se lit sur `pret`/`bloquant`, jamais sur l'identité de la garde qui a échoué : un
    membre ajouté plus tard n'aura rien à déclarer ici.
    """
    preparation = _demarrer(effectif_suffisant=False, inscrits=8)

    assert niveau_de_preparation(preparation) is NiveauPreparation.ALERTE


def test_deroule_non_compose_avertit_sans_alerter() -> None:
    """« Si tout n'est pas complet » (A02) → **avertissement**, le niveau faible.

    Un tournoi sans déroulé composé **démarre** aujourd'hui (CA d'E16US012, `D-15`) : la ligne
    est en attente, mais l'action passera. C'est exactement le premier des deux niveaux.
    """
    preparation = _demarrer(nb_etapes_deroule=0)

    assert preparation.pret is True
    assert niveau_de_preparation(preparation) is NiveauPreparation.AVERTISSEMENT


def test_un_tournoi_deja_lance_ne_porte_aucune_pastille() -> None:
    """La question ne se pose plus : il n'y a plus rien à préparer, donc rien à signaler.

    ⚠️ Ne **pas** dériver ce cas de `pret`, qui vaut `False` ici : une alerte forte sur tous les
    tournois en cours de la liste serait le contresens exact de la demande.
    """
    preparation = _demarrer(statut=StatutTournoi.EN_COURS)

    assert preparation.question_posee is False
    assert preparation.pret is False
    assert niveau_de_preparation(preparation) is NiveauPreparation.AUCUN


def test_un_tournoi_annule_ou_archive_ne_porte_aucune_pastille() -> None:
    """Même raison, sur les deux statuts terminaux — un historique ne s'alerte pas."""
    for statut in (StatutTournoi.ANNULE, StatutTournoi.ARCHIVE):
        preparation = _demarrer(statut=statut)

        assert niveau_de_preparation(preparation) is NiveauPreparation.AUCUN, statut


def test_avertir_sans_bloquer_reste_un_avertissement() -> None:
    """`D-15` : quand l'action passe malgré un manque, le niveau ne monte pas à l'alerte.

    Aucun membre ne produit ce cas aujourd'hui (*démarrer* est toujours `bloquant`), mais c'est
    la règle qui décide, pas la table des membres du jour.
    """
    preparation = PreparationJalon(
        jalon=Jalon.DEMARRER,
        lignes=(LigneCompletude(cle="x", libelle="X", etat=EtatSection.ALERTE),),
        pret=False,
        bloquant=False,
        question_posee=True,
    )

    assert niveau_de_preparation(preparation) is NiveauPreparation.AVERTISSEMENT


def test_une_ligne_a_venir_n_est_pas_un_manque() -> None:
    """`A_VENIR` marque un **séquencement**, pas une préparation en retard.

    `evaluer_completude` en pose une pour les phases éliminatoires. La compter comme un manque
    ferait porter une pastille perpétuelle à tout tournoi, que rien ne pourrait éteindre.
    """
    completude = Completude(
        sportif=(
            LigneCompletude(cle="qualification", libelle="Qualification", etat=EtatSection.OK),
            LigneCompletude(cle="phases", libelle="Phases", etat=EtatSection.A_VENIR),
        ),
        hors_sportif=(),
        sportif_complet=True,
    )
    preparation = evaluer_terminer(completude=completude, statut=StatutTournoi.EN_COURS)

    assert niveau_de_preparation(preparation) is NiveauPreparation.AUCUN


# --- Ce que la pastille dit (`D-16` : une alerte chiffre son impact) ----------------------------


def test_une_pastille_eteinte_ne_dit_rien() -> None:
    """Pas de niveau, pas de phrase — sans quoi le front aurait une bulle à masquer lui-même."""
    assert resume_du_manque(_demarrer()) is None


def test_l_alerte_forte_reprend_la_phrase_du_refus() -> None:
    """La bulle dit **ce que le serveur opposera au clic**, pas une seconde rédaction.

    C'est le même principe que `PreparationJalon.detail` (E16US012) : deux formulations d'un même
    refus finissent par diverger.
    """
    assert resume_du_manque(_demarrer(nb_creneaux=0)) == MESSAGE_SANS_DEPART


def test_l_avertissement_nomme_ce_qui_reste_a_preparer() -> None:
    """Un tournoi qui démarrera quand même n'a aucun message de refus : il faut le rédiger.

    Sans cela, la pastille faible serait un point de couleur sans explication — le « clic de
    plus » que `D-16` refuse.

    ⚠️ **`minimum=0` est la combinaison RÉELLE**, et c'est tout l'objet de la correction de revue :
    `nb_etapes_deroule` et `minimum` viennent du **même** dépôt d'étapes — sans étape, il n'y a
    aucune exigence d'effectif. La 1ʳᵉ rédaction gardait le `minimum=34` du helper, une
    combinaison que le service ne peut pas produire : le test décrivait un chemin inexistant.
    """
    resume = resume_du_manque(_demarrer(nb_etapes_deroule=0, minimum=0, inscrits=40))

    assert resume is not None
    assert "Déroulé composé" in resume


def test_un_tournoi_qui_a_ses_inscrits_ne_se_voit_pas_reclamer_des_inscrits() -> None:
    """Le défaut que la revue a trouvé : une phrase **plausible et fausse**.

    Sans exigence (aucune étape composée), la ligne « Inscrits » est `EN_ATTENTE` — juste sur
    l'écran du jalon, où le décompte est à côté. Promue dans « il reste à préparer : … », elle
    réclamait des inscriptions à un tournoi qui en compte 40, dans la seule phrase que la pastille
    affiche. `D-16` demande exactement l'inverse.
    """
    resume = resume_du_manque(_demarrer(nb_etapes_deroule=0, minimum=0, inscrits=40))

    assert resume is not None
    assert "Inscrits" not in resume


def test_sans_exigence_le_nombre_d_inscrits_ne_change_rien_au_reste_a_preparer() -> None:
    """Zéro inscrit ou quarante : sans règle à comparer, ce n'est pas un manque à énoncer.

    Apparié au test ci-dessus — sinon une correction qui masquerait la ligne « Inscrits » en toute
    circonstance passerait aussi.
    """
    vide = resume_du_manque(_demarrer(nb_etapes_deroule=0, minimum=0, inscrits=0))
    garni = resume_du_manque(_demarrer(nb_etapes_deroule=0, minimum=0, inscrits=40))

    assert vide == garni


def test_une_ligne_d_effectif_chiffree_reste_un_manque() -> None:
    """**La garde contre la sur-correction** — et cette fois elle atteint vraiment le prédicat.

    ⚠️ La 1ʳᵉ rédaction passait par `_demarrer(effectif_suffisant=False)` : `pret` valait alors
    `False`, donc `niveau_de_preparation` sortait en `ALERTE` **avant** `_est_un_manque`, et
    `resume_du_manque` rendait `detail` **avant** la branche `restants`. Deux axes de revue l'ont
    démontré par mutation — masquer la ligne « Inscrits » en toute circonstance laissait 40 tests
    verts. D'où une préparation construite à la main, seul moyen d'atteindre la branche gardée.
    """
    preparation = PreparationJalon(
        jalon=Jalon.DEMARRER,
        lignes=(
            LigneCompletude(
                cle=CLE_EFFECTIF, libelle="Inscrits", etat=EtatSection.ALERTE, fait=8, total=34
            ),
        ),
        pret=True,
        bloquant=False,
        question_posee=True,
    )

    assert niveau_de_preparation(preparation) is NiveauPreparation.AVERTISSEMENT
    assert resume_du_manque(preparation) == "Il reste à préparer : Inscrits."


def test_le_refus_chiffre_prime_sur_l_enumeration() -> None:
    """Quand le serveur a une phrase de refus, c'est elle qui parle — pas la liste des lignes.

    C'est ce que l'ancien `test_une_exigence_non_tenue_reste_nommee` vérifiait réellement ; il est
    conservé sous le nom de ce qu'il fait.
    """
    preparation = _demarrer(effectif_suffisant=False, inscrits=8, minimum=34)

    assert niveau_de_preparation(preparation) is NiveauPreparation.ALERTE
    assert resume_du_manque(preparation) == "Il manque 26 inscrits sur 34."
