"""Tests du calcul d'impact (E12US007) — value object `ImpactRegeneration` **pur**.

Écrits **depuis le CA** (`stories/E12-pilotage-jour-j.md`, E12US007 + [ADR-0040]) **avant**
implémentation (règle 9) : la dérivation du **niveau** d'une régénération de plan est une règle
métier (« ce qui mérite un geste délibéré »), pas du câblage. La ligne de partage du CA — *est-ce
que
ça a déjà produit des données réelles ?* — se lit ici sur trois niveaux :

- **aucun** : rien n'est placé (plan jamais généré) → aucune alerte ;
- **confirmation** : des archers sont placés mais **aucun score** → config réversible, alerte
simple ;
- **massif** : des archers placés **et au moins un score** → données réelles en jeu, geste délibéré.

[ADR-0040]: ../../docs/adr/0040-alerte-par-calcul-d-impact.md
"""

from __future__ import annotations

from domain.impact import ImpactRegeneration, NiveauImpact


def test_aucune_affectation_est_sans_impact() -> None:
    """Plan jamais généré (0 archer placé) : impact nul, aucune alerte — première génération."""
    impact = ImpactRegeneration(archers_deplaces=0, cibles_avec_scores=0)
    assert impact.niveau is NiveauImpact.AUCUN


def test_archers_places_sans_score_demande_une_confirmation() -> None:
    """Des archers placés mais aucun score : on re-brasse une config réversible → confirmation
    simple.

    Pas de données réelles produites (aucune série) : c'est le niveau « confirmation » — chiffré
    côté
    UI, mais sans geste délibéré ni trace (la régénération auto est déterministe, ADR-0024).
    """
    impact = ImpactRegeneration(archers_deplaces=156, cibles_avec_scores=0)
    assert impact.niveau is NiveauImpact.CONFIRMATION


def test_un_score_existant_rend_l_action_massive() -> None:
    """Au moins une cible a des scores : données réelles en jeu → action **massive** (mot à taper).

    C'est l'exemple mot pour mot du CDC §9.1 : « 156 archers perdront leur place ; 4 cibles ont déjà
    des scores, conservés ». La présence de **scores** (pas le seul nombre d'archers) fait basculer
    en massif.
    """
    impact = ImpactRegeneration(archers_deplaces=156, cibles_avec_scores=4)
    assert impact.niveau is NiveauImpact.MASSIF


def test_un_seul_score_suffit_a_basculer_en_massif() -> None:
    """Le seuil du massif est **binaire** : une seule cible avec score suffit, peu importe le
    nombre."""
    impact = ImpactRegeneration(archers_deplaces=2, cibles_avec_scores=1)
    assert impact.niveau is NiveauImpact.MASSIF


def test_est_immuable() -> None:
    """Value object figé (règle 4) : un impact est une photo, il ne se modifie pas après coup."""
    impact = ImpactRegeneration(archers_deplaces=1, cibles_avec_scores=0)
    try:
        impact.archers_deplaces = 2  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("ImpactRegeneration devrait être immuable (frozen).")
