"""Garde-fou **mécanique** de la portée sportive : le départ, jamais le tournoi (ADR-0075).

Sur le modèle du garde-fou d'isolation du domaine (`test_domain_isolation.py`, règle 1) : une règle
d'architecture que rien ne vérifie automatiquement **diverge**, et d'autant plus vite que le projet
grossit. C'est exactement ce qui est arrivé à [ADR-0017] — il avait décidé qu'« un départ rejoue
le tournoi », seule la logistique l'a porté, et le moteur est resté à la portée tournoi **treize
mois**, produisant un classement de 400 là où il en fallait quatre de 100.

**Pourquoi un test et pas une relecture.** La confusion est *invisible au typage* :
`TournoiId = int` et `DepartId = int` sont le même type pour mypy. Un service qui reçoit un
identifiant de tournoi là où on attend un départ compile parfaitement et se trompe silencieusement
(cf. `DETTE-044`, qui propose des `NewType` pour fermer la classe entière). Le renommage des
méthodes de port (`par_tournoi` → `par_depart`) a été le seul levier de détection lors de la
bascule : il a révélé **157 appels** que mypy laissait passer. Ce fichier fige le résultat.

Ces tests échouent si quelqu'un rebranche une phase, un classement ou un barrage sur le tournoi —
y compris « juste pour dépanner ». Le message d'échec dit quoi faire à la place.

[ADR-0017]: ../../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from application.classements import ServiceClassement
from application.phases import ServicePhases
from domain.barrage import BarrageDePlaces
from domain.phase import Phase
from domain.ports import BarrageRepository, PhaseRepository

_BACKEND = pathlib.Path(__file__).resolve().parent.parent

# Les couches de **production** : le domaine décide, les autres l'appliquent. `tests/` est exclu —
# un décor de test peut légitimement nommer un tournoi à côté d'un départ.
_COUCHES = ("domain", "application", "api", "infrastructure", "bootstrap")

# Les agrégats dont la portée **est** le départ (ADR-0075 §1 et §3), et le champ qu'ils doivent
# porter. La valeur dit aussi ce qu'ils ne doivent **plus** porter : `tournoi_id`.
_AGREGATS_DE_DEPART = (Phase, BarrageDePlaces)


@pytest.mark.parametrize("agregat", _AGREGATS_DE_DEPART, ids=lambda a: a.__name__)
def test_un_agregat_de_portee_sportive_pend_au_depart(agregat: type) -> None:
    """`Phase` et `BarrageDePlaces` portent `depart_id` — et **pas** `tournoi_id`.

    Les deux à la fois seraient pire qu'un seul mauvais : deux portées coexistantes obligeraient
    chaque lecture à choisir laquelle honorer, et la première qui se tromperait rétablirait le bug
    en silence (ADR-0075, « ce qui a été écarté »). Le tournoi reste atteignable par la jointure
    `depart → tournoi`.
    """
    champs = {champ.name for champ in dataclasses.fields(agregat)}
    assert (
        "depart_id" in champs
    ), f"{agregat.__name__} doit porter `depart_id` : la portée sportive est le départ (ADR-0075)."
    assert "tournoi_id" not in champs, (
        f"{agregat.__name__} ne doit **pas** porter `tournoi_id` en plus de `depart_id`. Deux "
        "portées coexistantes laissent chaque lecture choisir la mauvaise, sans erreur visible. "
        "Pour remonter au tournoi, joindre par le départ."
    )


@pytest.mark.parametrize("port", (PhaseRepository, BarrageRepository), ids=lambda p: p.__name__)
def test_un_port_de_portee_sportive_lit_par_depart(port: type) -> None:
    """Les ports exposent `par_depart` : c'est la lecture du moteur.

    `par_tournoi` **subsiste** sur ces ports, et c'est voulu : c'est la vue **transverse**
    (concaténation des séquences de tous les créneaux), réservée aux écrans d'ensemble. Ce test ne
    l'interdit donc pas — il exige seulement que la lecture par départ existe, faute de quoi le
    moteur n'aurait d'autre choix que la transverse, et refermerait la confusion.
    """
    assert hasattr(port, "par_depart"), (
        f"{port.__name__} doit exposer `par_depart` — le moteur raisonne toujours dans un départ "
        "(ADR-0075). `par_tournoi` ne rend pas une séquence mais la concaténation de plusieurs."
    )


def test_le_classement_se_calcule_par_depart() -> None:
    """`ServiceClassement` expose `pour_depart` et **plus** `pour_tournoi`.

    C'était le défaut le plus visible d'avant ADR-0075 : un tournoi de 4 départs de 100 archers
    rendait **un** classement de 400, où l'archer du matin était rangé contre celui du soir qu'il
    n'a jamais affronté. Restaurer `pour_tournoi` restaurerait le bug.
    """
    assert hasattr(
        ServiceClassement, "pour_depart"
    ), "Le classement se calcule par départ : `ServiceClassement.pour_depart` (ADR-0075)."
    assert not hasattr(ServiceClassement, "pour_tournoi"), (
        "`ServiceClassement.pour_tournoi` mêlerait les archers de créneaux qui ne se sont jamais "
        "affrontés. Un tournoi de N départs produit N classements ; s'il faut une vue d'ensemble, "
        "elle s'assemble à partir d'eux, elle ne les fusionne pas."
    )


def test_la_sequence_de_phases_se_compose_par_depart() -> None:
    """`ServicePhases` compose la séquence **d'un départ**.

    Le contrôle porte sur le nom du premier paramètre : c'est lui qui dit la maille. Le service
    lisait `par_tournoi` — devenue la concaténation de N suites 1..M —, et la passer à
    `SequencePhases` lève `SequenceOrdreInvalide`, les ordres repartant de 1 à chaque créneau.
    """
    for operation in ("lister", "ajouter", "supprimer", "reordonner"):
        methode = getattr(ServicePhases, operation)
        premier = methode.__code__.co_varnames[1]
        assert premier == "depart_id", (
            f"`ServicePhases.{operation}` doit prendre un `depart_id` (reçu « {premier} ») : une "
            "séquence 1..N appartient à un créneau, pas au tournoi (ADR-0075)."
        )


def _modules_de_production() -> list[pathlib.Path]:
    return [
        chemin
        for couche in _COUCHES
        for chemin in (_BACKEND / couche).rglob("*.py")
        if "__pycache__" not in chemin.parts
    ]


def test_aucun_code_de_production_ne_lit_phase_point_tournoi_id() -> None:
    """Balayage AST : personne ne lit `<qqch>.tournoi_id` sur une phase ou un barrage.

    Heuristique **par le nom de la variable** (`phase`, `barrage`, `qualification`, `tableau`…) :
    l'analyse statique ne connaît pas les types ici, mais ces noms sont ceux du projet, et un
    accès `phase.tournoi_id` ne compilerait de toute façon plus. Le test attrape donc surtout la
    **réintroduction** — le jour où quelqu'un rajoute `tournoi_id` « pour simplifier une jointure ».

    C'est le complément du contrôle structurel ci-dessus : celui-là interdit le champ, celui-ci
    interdit l'habitude de le chercher.
    """
    suspects = {"phase", "phases", "barrage", "barrages", "qualification", "tableau"}
    fautes: list[str] = []
    for chemin in _modules_de_production():
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.Attribute) or noeud.attr != "tournoi_id":
                continue
            porteur = noeud.value
            nom = porteur.id if isinstance(porteur, ast.Name) else None
            if isinstance(porteur, ast.Attribute):
                nom = porteur.attr
            if nom in suspects:
                fautes.append(f"{chemin.relative_to(_BACKEND)}:{noeud.lineno} — {nom}.tournoi_id")
    assert not fautes, (
        "Une phase ou un barrage ne connaît que son **départ** (ADR-0075). Pour remonter au "
        "tournoi, joindre par le départ.\n  " + "\n  ".join(fautes)
    )
