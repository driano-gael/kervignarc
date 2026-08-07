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

⚠️ **[ADR-0076] nuance la portée sans la contredire** : le départ est la portée d'**exécution**
(avancement, classements, tableaux), le tournoi celle d'**édition** (le déroulé, défini une fois).
Ce fichier garde donc les deux mailles — et ajoute le contrôle qui rend la nuance tenable : la
définition d'une étape n'est **pas** dupliquée par créneau.

[ADR-0017]: ../../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md
[ADR-0076]: ../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md
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
from infrastructure.db.models import DerouleEtapeORM, PhaseORM

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


def test_le_deroule_se_compose_au_tournoi_et_se_pilote_au_depart() -> None:
    """`ServicePhases` porte **deux mailles**, et le premier paramètre dit laquelle (ADR-0076).

    Nuance apportée à ADR-0075 : le départ est la portée **d'exécution**, pas d'**édition**. On
    compose **un** déroulé au tournoi (atelier) — une écriture, plus d'éventail — et on le fait
    vivre **par créneau** (pilotage), le matin pouvant être en duels pendant que l'après-midi
    qualifie. Se tromper de maille est invisible au typage (`TournoiId` et `DepartId` sont tous
    deux `int`), d'où ce contrôle sur le **nom** du paramètre.
    """
    for operation in ("lister", "ajouter", "modifier", "supprimer", "reordonner"):
        methode = getattr(ServicePhases, operation)
        premier = methode.__code__.co_varnames[1]
        assert premier == "tournoi_id", (
            f"`ServicePhases.{operation}` doit prendre un `tournoi_id` (reçu « {premier} ») : le "
            "déroulé se définit **une fois** pour le tournoi, jamais par créneau (ADR-0076). "
            "Composer par départ rouvrirait la divergence silencieuse entre copies."
        )

    for operation in ("demarrer", "mettre_en_pause", "reprendre", "terminer"):
        methode = getattr(ServicePhases, operation)
        premier = methode.__code__.co_varnames[1]
        assert premier == "depart_id", (
            f"`ServicePhases.{operation}` doit prendre un `depart_id` (reçu « {premier} ») : "
            "l'avancement appartient au créneau qui joue l'étape, pas au tournoi (ADR-0076)."
        )


def test_la_definition_d_une_etape_n_est_pas_dupliquee_par_depart() -> None:
    """La table `phase` ne porte que l'**avancement** : ni type, ni barème, ni `config`.

    C'est le garde-fou structurel d'ADR-0076. La décision n'était pas « ne pas laisser diverger les
    copies » — une garde contournable n'est pas un invariant — mais « rendre la divergence
    **impossible** » en n'ayant qu'une définition. Cela ne tient que tant que `PhaseORM` reste
    vide de définition : le jour où quelqu'un y rajoute une colonne « pour éviter une jointure »,
    les N créneaux redeviennent libres de s'écarter les uns des autres, en silence.

    Le contrôle est **structurel** (les colonnes) et non comportemental : c'est la seule forme qui
    résiste à un code de lecture qu'on réécrirait pour s'accommoder de la colonne fautive.
    """
    colonnes_avancement = {"id", "depart_id", "ordre", "statut"}
    colonnes = {colonne.name for colonne in PhaseORM.__table__.columns}
    assert colonnes == colonnes_avancement, (
        "`phase` ne porte que l'avancement d'une étape dans un créneau (ADR-0076) ; sa définition "
        f"vit dans `deroule_etape`, une seule fois par tournoi. Colonnes en trop : "
        f"{sorted(colonnes - colonnes_avancement)} — les remettre ici rétablit N copies libres de "
        "diverger. Une définition qui doit changer se change sur l'étape."
    )

    definition = {"type", "config"}
    etape = {colonne.name for colonne in DerouleEtapeORM.__table__.columns}
    assert definition <= etape, (
        "`deroule_etape` doit porter la définition (type et politiques) : c'est le pendant du "
        f"contrôle ci-dessus — manquants : {sorted(definition - etape)}."
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
