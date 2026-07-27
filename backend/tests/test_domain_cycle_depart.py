"""Tests du cycle de vie d'un départ (E12US008) — value object `AvancementDepart` **pur**.

Écrits **depuis le CA** (`stories/E12-pilotage-jour-j.md`, E12US008) **avant** implémentation
(règle 9) : la dérivation de l'**état** d'un créneau est une règle métier (« ce qui distingue un
créneau qu'on peut encore éditer librement d'une session de tir en cours »), pas du câblage.

Le CA impose un état **dérivé d'un fait réel** — jamais saisi — et une échelle à trois crans :

- **ouvert** : aucun score consigné dans le créneau → librement éditable (comportement E02US009) ;
- **lancé** : au moins une flèche consignée, mais toutes les séries ne sont pas encore closes ;
- **clos** : toutes les séries des archers placés sont closes (barème validé **ou** forfait).

Arbitrage reversé dans `stories/` (E12US008, puce « Notes ») : « lancé » se dérive de la **présence
d'un score** (le seul fait réel disponible — `horaire` est un libellé libre, pas une heure
comparable), et l'échelle **s'appuie sur un tir réel** : un créneau où la seule « activité » serait
un forfait sans aucune flèche reste **ouvert** (rien n'a été tiré, rien à protéger). L'échelle reste
ainsi monotone : *clos* implique que le créneau a été *lancé*.
"""

from __future__ import annotations

from domain.cycle_depart import AvancementDepart, EtatDepart


def test_creneau_vide_est_ouvert() -> None:
    """Aucun archer placé : rien n'a été tiré, le créneau est **ouvert** (librement éditable)."""
    avancement = AvancementDepart(nb_places=0, nb_ayant_tire=0, nb_series_closes=0)
    assert avancement.etat is EtatDepart.OUVERT


def test_archers_places_sans_score_reste_ouvert() -> None:
    """Des archers sont placés mais **personne n'a tiré** : le créneau est encore **ouvert**.

    La ligne de partage du CA n'est pas « des gens sont inscrits » (ça, c'est E02US009) mais « un
    score a-t-il été consigné ». Sans flèche validée, le créneau se modifie librement.
    """
    avancement = AvancementDepart(nb_places=12, nb_ayant_tire=0, nb_series_closes=0)
    assert avancement.etat is EtatDepart.OUVERT


def test_un_seul_score_bascule_de_ouvert_a_lance() -> None:
    """Borne stricte `OUVERT → LANCÉ` : dès **une** flèche consignée, le créneau est **lancé**."""
    avancement = AvancementDepart(nb_places=12, nb_ayant_tire=1, nb_series_closes=0)
    assert avancement.etat is EtatDepart.LANCE


def test_tous_ont_tire_mais_series_incompletes_reste_lance() -> None:
    """Tout le monde a tiré mais aucune série n'est close : la session est **lancée**, pas close."""
    avancement = AvancementDepart(nb_places=12, nb_ayant_tire=12, nb_series_closes=0)
    assert avancement.etat is EtatDepart.LANCE


def test_toutes_series_closes_ferme_le_creneau() -> None:
    """Toutes les séries des archers placés sont closes (barème validé ou forfait) : **clos**."""
    avancement = AvancementDepart(nb_places=12, nb_ayant_tire=12, nb_series_closes=12)
    assert avancement.etat is EtatDepart.CLOS


def test_une_seule_serie_non_close_empeche_le_clos() -> None:
    """Borne `LANCÉ → CLOS` : une seule série non close suffit à maintenir le créneau lancé."""
    avancement = AvancementDepart(nb_places=12, nb_ayant_tire=12, nb_series_closes=11)
    assert avancement.etat is EtatDepart.LANCE


def test_forfaits_sans_aucun_tir_laissent_le_creneau_ouvert() -> None:
    """Cas dégénéré : toutes les séries « closes » par forfait, mais **personne n'a tiré**.

    L'échelle s'appuie sur un **tir réel** (arbitrage reversé dans `stories/`) : sans flèche
    consignée, le créneau reste **ouvert** — on n'a pas détruit de session de tir en l'éditant, et
    l'échelle demeure monotone (on ne saute pas *ouvert → clos* sans passer par *lancé*).
    """
    avancement = AvancementDepart(nb_places=6, nb_ayant_tire=0, nb_series_closes=6)
    assert avancement.etat is EtatDepart.OUVERT


def test_est_immuable() -> None:
    """Value object figé (règle 4) : un avancement est une photo, il ne se modifie pas."""
    avancement = AvancementDepart(nb_places=1, nb_ayant_tire=1, nb_series_closes=0)
    try:
        avancement.nb_ayant_tire = 2  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("AvancementDepart devrait être immuable (frozen).")
