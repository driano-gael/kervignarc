"""Tests du **réglage** d'une phase de poules — écrits depuis le CA d'E05US023 (règle 9).

Source : `stories/E05-moteur-phases.md`, E05US023, puces « CA — composer et régler une phase de
poules à l'atelier », « CA — la taille commande » et « CA — deux régimes d'ex æquo ».

L'objet de ce fichier est la distinction que l'US introduit et qui n'existait pas avant :

- `ReglageDePoules` — ce que l'organisateur **saisit à l'atelier**, avant que les inscriptions
  soient closes. Il porte une **taille visée**, indépendante de l'effectif.
- `ConfigurationPoules` — ce que le **moteur** consomme le jour J. Il porte un **nombre de poules**,
  qui n'est calculable qu'une fois l'effectif connu.

Confondre les deux serait figer le nombre de poules à un effectif supposé : un tournoi réglé pour
32 inscrits et joué à 30 monterait 8 poules dont deux à 3 archers, en silence.
"""

from __future__ import annotations

import pytest

from domain.erreurs import ConfigurationPouleInvalide
from domain.poule import BaremePoule, ReglageDePoules


def test_le_reglage_par_defaut_suit_les_arbitrages_du_31_07() -> None:
    """Barème 3/1/0, round-robin complet, et **aucun** nombre de qualifiés pré-rempli.

    Le commanditaire a explicitement demandé le 31/07/2026 qu'aucune valeur ne soit proposée pour
    les qualifiés : ce nombre dépend de ce que la phase **suivante** attend, pas du format de poule.
    """
    reglage = ReglageDePoules(taille_visee=4)

    assert reglage.bareme == BaremePoule(victoire=3, nul=1, defaite=0)
    assert reglage.nb_qualifies is None
    assert reglage.rencontres_par_archer is None


def test_la_taille_visee_est_bornee_comme_le_calcul_qui_la_consomme() -> None:
    """Une poule apparie au moins deux archers : 1 n'est pas un réglage, c'est une erreur."""
    with pytest.raises(ConfigurationPouleInvalide):
        ReglageDePoules(taille_visee=1)
    with pytest.raises(ConfigurationPouleInvalide):
        ReglageDePoules(taille_visee=0)


def test_le_reglage_produit_la_configuration_du_moteur_pour_un_effectif_donne() -> None:
    """CA — la taille commande : le réglage + l'effectif du jour donnent la config du moteur.

    30 inscrits, poules de 4 → 7 poules. C'est ici que la conversion a lieu, **une seule fois**,
    plutôt que dans chaque service qui aurait besoin du nombre de groupes.
    """
    reglage = ReglageDePoules(taille_visee=4, nb_qualifies=2)

    configuration = reglage.pour_effectif(30)

    assert configuration.nb_poules == 7
    assert configuration.nb_qualifies == 2
    assert configuration.bareme == reglage.bareme


def test_le_reglage_reporte_le_bareme_et_les_rencontres_au_moteur() -> None:
    """Rien du réglage ne doit se perdre en route vers `ConfigurationPoules`."""
    reglage = ReglageDePoules(
        taille_visee=6,
        bareme=BaremePoule(victoire=2, nul=1, defaite=0),
        nb_qualifies=3,
        rencontres_par_archer=3,
    )

    configuration = reglage.pour_effectif(24)

    assert configuration.nb_poules == 4
    assert configuration.bareme == BaremePoule(victoire=2, nul=1, defaite=0)
    assert configuration.nb_qualifies == 3
    assert configuration.rencontres_par_archer == 3


# --------------------------------------------------------------------------------------------
# CA — deux régimes d'ex æquo, selon ce que la poule produit
# --------------------------------------------------------------------------------------------


def test_une_poule_sans_qualifies_produit_un_classement() -> None:
    """`nb_qualifies` vide = « la poule classe, elle ne qualifie pas » (docstring d'origine).

    Le CA du 09/08 rend ce régime **explicite** plutôt que déduit d'un champ laissé vide : c'est le
    régime qui exige de départager **tout** ex æquo irréductible, puisque le classement est le
    livrable.
    """
    assert ReglageDePoules(taille_visee=4).produit_un_classement is True
    assert ReglageDePoules(taille_visee=4).produit_des_qualifies is False


def test_une_poule_avec_qualifies_ne_produit_pas_un_classement() -> None:
    """Régime « qualifiés » : seul le franchissement de la barre compte.

    Deux archers à égalité aux rangs 3-4 d'une poule qui en qualifie 2 **restent à égalité** —
    l'outil ne les départage pas, parce que le classement n'est pas le livrable.
    """
    assert ReglageDePoules(taille_visee=4, nb_qualifies=2).produit_des_qualifies is True
    assert ReglageDePoules(taille_visee=4, nb_qualifies=2).produit_un_classement is False


def test_un_nombre_de_qualifies_incoherent_est_refuse_des_le_reglage() -> None:
    """Qualifier plus d'archers qu'une poule n'en compte est un réglage faux, pas un cas limite.

    Le refuser **à l'atelier** vaut mieux que de le laisser exploser le jour J dans
    `qualifies_de_poule` : à l'atelier l'organisateur corrige, en salle il est bloqué.
    """
    with pytest.raises(ConfigurationPouleInvalide):
        ReglageDePoules(taille_visee=4, nb_qualifies=5)
    with pytest.raises(ConfigurationPouleInvalide):
        ReglageDePoules(taille_visee=4, nb_qualifies=0)


def test_qualifier_toute_la_poule_reste_licite() -> None:
    """Cas limite haut : qualifier les 4 d'une poule de 4 est inutile mais pas incohérent.

    On ne l'interdit pas — c'est un réglage de transition légitime (« tout le monde passe, la poule
    ne sert qu'à ordonner l'entrée du tableau »), et l'interdire supposerait connaître l'intention.
    """
    assert ReglageDePoules(taille_visee=4, nb_qualifies=4).nb_qualifies == 4
