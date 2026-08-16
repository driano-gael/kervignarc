"""La carte du code, écrite depuis le CA d'`E00US020` — avant l'implémentation.

L'oracle est la fiche de l'US, elle-même adossée aux règles 1, 2, 8 et 10 de `CLAUDE.md`. Deux
propriétés y sont non négociables, et ce sont elles que ces tests protègent :

1. **le bloquant est exact.** `sens-des-dependances` fait rougir la CI ; il est donc lu à l'AST,
   imports relatifs résolus. Un garde-fou qu'un `from ..api import x` contourne ne garde rien ;
2. **l'appariement port → adapter est structurel.** Un `Protocol` s'implémente sans héritage : un
   inventaire fondé sur les bases de classe rendrait une page vide en affirmant qu'elle est
   complète — un atlas qui affirme faux, ce que cette famille d'US existe pour empêcher.

Les arborescences d'essai sont **synthétiques** : un test qui ne lirait que le dépôt réel ne
saurait pas dire ce que le lecteur fait d'un cas qui ne s'y trouve pas encore — c'est-à-dire
exactement le cas qu'il devra attraper un jour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas import carte, controles
from atlas.modele import AreteFeature, Severite
from atlas.sources import code

RACINE_REELLE = Path(__file__).resolve().parents[2]


def _ecrire(racine: Path, chemin: str, contenu: str) -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(contenu, encoding="utf-8")


def _depot(tmp_path: Path, fichiers: dict[str, str]) -> Path:
    """Un dépôt d'essai : les cinq couches existent (`rglob` ne bute pas), le reste est écrit."""
    for couche in code.COUCHES:
        (tmp_path / code.BACKEND / couche).mkdir(parents=True, exist_ok=True)
    for chemin, contenu in fichiers.items():
        _ecrire(tmp_path, chemin, contenu)
    return tmp_path


# --- CA « le sens des dépendances est constaté, pas supposé » ---------------------------------


@pytest.mark.parametrize(
    ("source", "cible", "attendu"),
    [
        ("domain", "application", False),
        ("domain", "infrastructure", False),
        ("domain", "api", False),
        ("application", "domain", True),
        ("application", "infrastructure", False),
        ("application", "api", False),
        ("infrastructure", "domain", True),
        ("infrastructure", "application", True),
        ("infrastructure", "api", False),
        ("api", "domain", True),
        ("api", "application", True),
        ("api", "infrastructure", True),
        ("bootstrap", "api", True),
    ],
)
def test_le_sens_autorise_est_celui_des_regles(source: str, cible: str, attendu: bool) -> None:
    """La table du CA, transcrite à la lettre. Règles 1, 2 et 8."""
    assert code.autorise(source, cible) is attendu


@pytest.mark.parametrize("couche", code.COUCHES)
def test_personne_n_importe_la_racine_de_composition(couche: str) -> None:
    """Règle 8 : `bootstrap/` câble tout le monde et n'est câblé par personne.

    L'importer inverse le sens du câblage et fait d'un point d'assemblage une dépendance. Le cas
    n'apparaît dans aucune valeur de `SENS_AUTORISE` — ce test dit que c'est **voulu**, et non un
    oubli qu'une relecture distraite « corrigerait » en l'ajoutant.
    """
    if couche == "bootstrap":
        return
    assert code.autorise(couche, "bootstrap") is False


@pytest.mark.parametrize(
    ("source", "cible"),
    [("domain", "domain"), ("infrastructure", "infrastructure"), ("api", "api")],
)
def test_une_couche_a_le_droit_de_s_importer_elle_meme(source: str, cible: str) -> None:
    """`infrastructure/db` → `infrastructure` n'est pas une violation : la règle 2 porte sur le
    sens **entre** couches. Sans cette clause, la porte annonçait neuf violations bloquantes le
    jour de sa livraison — toutes fausses."""
    assert code.autorise(source, cible) is True


def test_un_import_relatif_est_resolu_et_ne_contourne_pas_la_porte(tmp_path: Path) -> None:
    """Le contournement le plus simple d'un garde-fou d'imports, et le seul qui ne se voit pas."""
    racine = _depot(
        tmp_path,
        {
            "backend/application/__init__.py": "",
            "backend/application/services/__init__.py": "",
            "backend/application/services/inscription.py": "from ...api.v1 import routes\n",
        },
    )

    aretes = code.lire_aretes(racine)

    assert [(a.couche_source, a.couche_cible) for a in aretes] == [("application", "api")]
    assert carte.violations(aretes)


def test_un_import_sous_type_checking_compte_aussi(tmp_path: Path) -> None:
    """Le couplage de conception existe même si l'import ne s'exécute pas à l'exécution."""
    racine = _depot(
        tmp_path,
        {
            "backend/application/service.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    from api.v1.dto import ArcherDTO\n"
            )
        },
    )

    assert [(a.couche_source, a.couche_cible) for a in code.lire_aretes(racine)] == [
        ("application", "api")
    ]


def test_les_imports_internes_a_un_paquet_ne_polluent_pas_la_matrice(tmp_path: Path) -> None:
    """Ils ne disent rien du sens des dépendances, et noieraient la diagonale de la matrice."""
    racine = _depot(
        tmp_path,
        {
            "backend/domain/archer.py": "from domain.club import Club\n",
            "backend/domain/club.py": "",
        },
    )

    assert code.lire_aretes(racine) == ()


def test_la_matrice_agrege_les_occurrences_et_nomme_ses_origines(tmp_path: Path) -> None:
    """Un nombre invérifiable ne se corrige jamais : chaque cellule doit nommer ses fichiers."""
    racine = _depot(
        tmp_path,
        {
            "backend/application/a.py": "from domain.archer import A\nfrom domain.club import C\n",
            "backend/application/b.py": "from domain.archer import A\n",
        },
    )

    (arete,) = code.lire_aretes(racine)

    assert arete.occurrences == 3
    assert arete.origines == ("backend/application/a.py", "backend/application/b.py")


def test_un_sous_paquet_est_distingue_mais_pas_invente(tmp_path: Path) -> None:
    """`domain.erreurs` est un répertoire → paquet ; `domain.archer` est un module → couche."""
    racine = _depot(
        tmp_path,
        {
            "backend/domain/erreurs/__init__.py": "",
            "backend/domain/archer.py": "",
            "backend/application/service.py": (
                "from domain.erreurs import DomainError\nfrom domain.archer import Archer\n"
            ),
        },
    )

    assert sorted(a.paquet_cible for a in code.lire_aretes(racine)) == ["domain", "domain/erreurs"]


# --- CA « les ports et leurs adapters » -------------------------------------------------------

_PORT = """from typing import Protocol


class ArcherRepository(Protocol):
    def enregistrer(self, archer: object) -> None: ...
    def lire(self, identifiant: int) -> object: ...
"""


def test_un_adapter_est_apparie_sans_heritage(tmp_path: Path) -> None:
    """La propriété centrale : le dépôt ne compte qu'un héritage explicite pour des dizaines de
    ports. Un inventaire par bases de classe rendrait une page vide en se disant complète."""
    racine = _depot(
        tmp_path,
        {
            "backend/domain/ports.py": _PORT,
            "backend/infrastructure/db/archer.py": (
                "class ArcherRepositorySQL:\n"
                "    def enregistrer(self, archer: object) -> None: ...\n"
                "    def lire(self, identifiant: int) -> object: ...\n"
                "    def _interne(self) -> None: ...\n"
            ),
        },
    )

    (port,) = code.lire_ports(racine)

    assert port.adapters == ("backend/infrastructure/db/archer.py::ArcherRepositorySQL",)
    assert port.herite == ()


def test_une_classe_a_qui_il_manque_une_methode_n_est_pas_un_adapter(tmp_path: Path) -> None:
    racine = _depot(
        tmp_path,
        {
            "backend/domain/ports.py": _PORT,
            "backend/infrastructure/db/archer.py": (
                "class Partiel:\n    def lire(self, identifiant: int) -> object: ...\n"
            ),
        },
    )

    (port,) = code.lire_ports(racine)

    assert port.adapters == ()


def test_un_port_n_est_jamais_l_adapter_d_un_autre_port(tmp_path: Path) -> None:
    """Deux `Protocol` de même forme s'appariraient l'un l'autre — et l'atlas annoncerait un port
    « implémenté » par une seconde interface, qui n'implémente rien."""
    racine = _depot(
        tmp_path,
        {
            "backend/domain/ports.py": _PORT,
            "backend/application/ports.py": _PORT.replace("ArcherRepository", "ArcherStore"),
        },
    )

    ports = code.lire_ports(racine)

    assert [p.nom for p in ports] == ["ArcherRepository", "ArcherStore"]
    assert all(port.adapters == () for port in ports)


def test_un_port_sans_methode_publique_n_apparie_personne_et_ne_se_plaint_pas(
    tmp_path: Path,
) -> None:
    """Tout le monde satisfait l'ensemble vide : l'apparier rendrait un inventaire absurde. Et il
    n'y a rien à signaler pour autant — rien n'est constaté, il n'y a rien à dire."""
    racine = _depot(
        tmp_path,
        {
            "backend/domain/ports.py": (
                "from typing import Protocol\n\n\nclass Marqueur(Protocol): ...\n"
            ),
            "backend/infrastructure/db/x.py": (
                "class Quelconque:\n    def peu_importe(self) -> None: ...\n"
            ),
        },
    )

    (port,) = code.lire_ports(racine)

    assert port.adapters == ()
    assert [c.code for c in controles.verifier_code((), (port,), ())] == []


def test_un_port_hors_du_domaine_est_signale_jamais_bloque(tmp_path: Path) -> None:
    """Règle 2 : les ports vivent dans le domaine. L'écart peut être légitime (l'authentification
    n'est pas du métier de tir à l'arc) — un humain tranche, pas la porte."""
    racine = _depot(tmp_path, {"backend/application/auth.py": _PORT})

    verdicts = controles.verifier_code((), code.lire_ports(racine), ())
    (verdict,) = [v for v in verdicts if v.code == "port-hors-domaine"]

    assert verdict.severite is Severite.SIGNAL
    assert controles.bloquants(verdicts) == ()


def test_un_port_sans_adapter_est_signale(tmp_path: Path) -> None:
    racine = _depot(tmp_path, {"backend/domain/ports.py": _PORT})

    verdicts = controles.verifier_code((), code.lire_ports(racine), ())

    assert [(v.code, v.severite) for v in verdicts] == [("port-sans-adapter", Severite.SIGNAL)]


# --- CA « le front est mesuré, en signal » ----------------------------------------------------


def _front(tmp_path: Path, fichiers: dict[str, str]) -> Path:
    for chemin, contenu in fichiers.items():
        _ecrire(tmp_path, f"frontend/src/features/{chemin}", contenu)
    return tmp_path


def test_seuls_les_imports_entre_features_font_une_arete(tmp_path: Path) -> None:
    """Un import de `shared/`, d'une bibliothèque, ou interne à la feature, n'en est pas une."""
    racine = _front(
        tmp_path,
        {
            "saisie/Saisie.tsx": (
                "import { useQuery } from '@tanstack/react-query'\n"
                "import { fetchJson } from '../../shared/api/client'\n"
                "import { volees } from './volees'\n"
                "import { Depart } from '../departs/api'\n"
            ),
            "departs/api.ts": "export interface Depart {}\n",
        },
    )

    assert code.lire_aretes_front(racine) == (
        AreteFeature(de="saisie", vers="departs", occurrences=1),
    )


def test_l_import_dynamique_est_vu(tmp_path: Path) -> None:
    racine = _front(
        tmp_path,
        {
            "salle/Salle.tsx": "const m = await import('../ecrans/api')\n",
            "ecrans/api.ts": "",
        },
    )

    assert [(a.de, a.vers) for a in code.lire_aretes_front(racine)] == [("salle", "ecrans")]


def test_les_features_enchevetrees_sont_une_composante_pas_un_compte_de_cycles() -> None:
    """La mesure doit être **unique** : la sortie est commitée et comparée à l'octet en CI. Le
    nombre de cycles dépend de l'ordre de parcours ; la composante fortement connexe, non."""
    aretes = (
        AreteFeature(de="a", vers="b", occurrences=1),
        AreteFeature(de="b", vers="c", occurrences=1),
        AreteFeature(de="c", vers="a", occurrences=1),
        AreteFeature(de="c", vers="b", occurrences=1),  # un 2e cycle dans la même composante
        AreteFeature(de="d", vers="a", occurrences=1),  # entrant, hors composante
    )

    noeuds = code.enchevetrements(aretes)

    assert [noeud.features for noeud in noeuds] == [("a", "b", "c")]


def test_une_dependance_lineaire_n_enchevetre_rien() -> None:
    aretes = (
        AreteFeature(de="a", vers="b", occurrences=1),
        AreteFeature(de="b", vers="c", occurrences=1),
    )

    assert code.enchevetrements(aretes) == ()


def test_l_enchevetrement_du_front_est_un_signal(tmp_path: Path) -> None:
    """Lecture par expression régulière : jamais bloquante — c'est écrit au CA."""
    noeuds = code.enchevetrements(
        (
            AreteFeature(de="a", vers="b", occurrences=1),
            AreteFeature(de="b", vers="a", occurrences=1),
        )
    )

    (verdict,) = controles.verifier_code((), (), noeuds)

    assert verdict.code == "features-enchevetrees"
    assert verdict.severite is Severite.SIGNAL


# --- CA « la porte » --------------------------------------------------------------------------


def test_une_violation_du_sens_des_dependances_bloque(tmp_path: Path) -> None:
    racine = _depot(tmp_path, {"backend/domain/archer.py": "from infrastructure.db import x\n"})

    verdicts = controles.verifier_code(code.lire_aretes(racine), (), ())

    assert [(v.code, v.severite) for v in verdicts] == [("sens-des-dependances", Severite.BLOQUANT)]
    assert controles.bloquants(verdicts)


def test_le_depot_reel_ne_porte_aucune_violation_du_sens_des_dependances() -> None:
    """La porte doit être **verte à la livraison** : elle verrouille un invariant tenu, elle ne
    dénonce pas une dette. Si ce test rougit un jour, c'est le code qui a dérivé — pas lui."""
    violations = carte.violations(code.lire_aretes(RACINE_REELLE))

    assert [(v.paquet_source, v.paquet_cible) for v in violations] == []


def test_la_carte_du_depot_reel_est_deterministe() -> None:
    """Sortie commitée et comparée à l'octet : deux passes doivent rendre le même objet."""

    def passe() -> dict[str, object]:
        aretes_front = code.lire_aretes_front(RACINE_REELLE)
        return carte.construire(
            code.lire_aretes(RACINE_REELLE),
            code.lire_ports(RACINE_REELLE),
            aretes_front,
            code.enchevetrements(aretes_front),
        )

    assert passe() == passe()


def test_le_plancher_de_ce_que_la_carte_trouve() -> None:
    """Un plancher, pas une valeur exacte : le dépôt grossit à chaque US, et un test qui fige un
    compte se corrige au lieu de se lire. Ce qui est vérifié, c'est que le lecteur **trouve** —
    une régression silencieuse (un `rglob` qui ne balaie plus rien) rendrait zéro sans un mot."""
    aretes_front = code.lire_aretes_front(RACINE_REELLE)
    charge = carte.construire(
        code.lire_aretes(RACINE_REELLE),
        code.lire_ports(RACINE_REELLE),
        aretes_front,
        code.enchevetrements(aretes_front),
    )

    assert charge["resume"]["imports"] >= 500
    assert charge["resume"]["ports"] >= 40
    assert charge["resume"]["features"] >= 30
