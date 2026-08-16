"""Ce que le code fait réellement des règles d'architecture — lu dans le code, pas dans les docs.

Les autres sources de l'atlas lisent des documents ; celle-ci lit le **dépôt**. Elle répond à trois
questions que rien ne posait :

1. **quelle couche dépend de quelle autre** — la règle 2 (« tout pointe vers le domaine ») n'était
   vérifiée que **pour le domaine** (`tests/test_domain_isolation.py`). Les quatre autres sens ne
   l'étaient par rien : un `application/` important `api/` passait le hook, la CI et la revue ;
2. **où sont les ports, et qui les implémente** — la règle 2 veut les ports dans le domaine et les
   adapters dans l'infrastructure ; l'inventaire dit si c'est tenu ;
3. **comment le front est découpé** — la règle 10 impose une organisation par features, sans qu'un
   contrôle ne dise jamais si les features sont encore autonomes.

Deux techniques, et l'écart entre elles est **la** propriété importante de ce module :

- le backend est lu à l'**AST** (`ast`, bibliothèque standard). C'est exact, y compris sur les
  imports relatifs, multi-lignes ou sous `if TYPE_CHECKING`. C'est ce qui autorise un contrôle
  **bloquant** : on ne bloque pas une CI sur une approximation ;
- le front est lu à l'**expression régulière**. L'atlas n'a aucune dépendance (ADR-0086) et la
  bibliothèque standard ne sait pas lire du TypeScript. Un import écrit autrement (concaténation,
  chemin calculé) échappe à la lecture. Conséquence assumée et écrite sur la page elle-même :
  **aucun constat côté front n'est bloquant**.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from atlas.modele import AreteCode, AreteFeature, NoeudEnchevetre, Port

BACKEND = "backend"
FEATURES = ("frontend", "src", "features")

#: Les cinq couches, dans l'ordre où les dépendances les traversent (le domaine au centre).
COUCHES: tuple[str, ...] = ("domain", "application", "infrastructure", "api", "bootstrap")

#: Ce que chaque couche a le droit d'importer. Dérivé des **règles écrites**, et de rien d'autre :
#: règle 1 (le domaine n'importe aucune couche), règle 2 (tout pointe vers le domaine, les ports
#: dans le domaine et les adapters dans l'infrastructure), règle 8 (`bootstrap/` est la racine de
#: composition, elle câble tout le monde à la main).
#:
#: ⚠️ **`bootstrap` n'apparaît dans aucune valeur** — ce n'est pas un oubli : la racine de
#: composition est un consommateur **terminal**. Quiconque l'importe inverse le câblage et fait
#: d'un point d'assemblage une dépendance, ce qui rend la composition impossible à relire.
#:
#: `infrastructure → application` est **autorisé** : quelques ports techniques (l'authentification)
#: sont déclarés dans `application/`, et leur adapter doit bien les importer. Que ces ports ne
#: soient pas dans le domaine est un écart à la règle 2 — mais il est **signalé** (`port-hors-
#: domaine`), pas bloqué : trancher mécaniquement qu'un port d'authentification est du métier de
#: tir à l'arc reviendrait à arbitrer seul une question de conception.
SENS_AUTORISE: dict[str, frozenset[str]] = {
    "domain": frozenset(),
    "application": frozenset({"domain"}),
    "infrastructure": frozenset({"domain", "application"}),
    "api": frozenset({"domain", "application", "infrastructure"}),
    "bootstrap": frozenset({"domain", "application", "infrastructure", "api"}),
}


def autorise(couche_source: str, couche_cible: str) -> bool:
    """Une couche a-t-elle le droit d'importer l'autre ? **La seule** écriture de la règle 2.

    Une couche s'importe toujours elle-même : `infrastructure/db` → `infrastructure`, `domain` →
    `domain/erreurs`. La règle 2 porte sur le sens **entre** couches, pas sur l'organisation
    interne de l'une d'elles. Sans cette clause, la porte annonçait neuf violations bloquantes le
    jour de sa livraison — toutes fausses, toutes intra-couche. Un garde-fou dont le premier
    verdict est faux ne se corrige pas : il se désactive.
    """
    if couche_source == couche_cible:
        return True
    return couche_cible in SENS_AUTORISE.get(couche_source, frozenset())


@dataclass(frozen=True, slots=True)
class _Classe:
    """Une classe lue dans le backend — de quoi apparier un port à ses adapters."""

    nom: str
    fichier: str
    couche: str
    bases: tuple[str, ...]
    methodes: frozenset[str]
    est_protocole: bool


def _racine_backend(racine: Path) -> Path:
    return racine / BACKEND


def _fichiers_python(racine: Path) -> list[tuple[Path, str]]:
    """Tous les modules des cinq couches, triés — l'ordre de sortie est comparé à l'octet en CI."""
    backend = _racine_backend(racine)
    return [
        (chemin, couche)
        for couche in COUCHES
        for chemin in sorted((backend / couche).rglob("*.py"))
    ]


def _chemin_relatif(chemin: Path, racine: Path) -> str:
    """Toujours en `/`, jamais en `\\` : poste Windows, CI Linux, et la sortie est commitée."""
    return chemin.relative_to(racine).as_posix()


def _paquet_du_fichier(chemin: Path, backend: Path) -> str:
    """`infrastructure/db/serie.py` → `infrastructure/db` ; `domain/archer.py` → `domain`.

    Deux niveaux, pas plus : au grain du module la matrice compterait 217 lignes et 217 colonnes,
    et une matrice qu'on ne peut pas embrasser du regard ne se lit pas — elle se scrolle.
    """
    morceaux = chemin.relative_to(backend).parts
    return f"{morceaux[0]}/{morceaux[1]}" if len(morceaux) > 2 else morceaux[0]


def _paquet_du_module(module: str, backend: Path) -> str:
    """`infrastructure.db.serie` → `infrastructure/db`, mais `domain.archer` → `domain`.

    Le second niveau n'est retenu que s'il est bien un **répertoire** : sinon `domain.archer`
    deviendrait un paquet `domain/archer` qui n'existe pas, et la matrice inventerait des colonnes.
    """
    morceaux = module.split(".")
    if len(morceaux) > 1 and (backend / morceaux[0] / morceaux[1]).is_dir():
        return f"{morceaux[0]}/{morceaux[1]}"
    return morceaux[0]


def _module_du_fichier(chemin: Path, backend: Path) -> str:
    morceaux = list(chemin.relative_to(backend).with_suffix("").parts)
    if morceaux and morceaux[-1] == "__init__":
        morceaux.pop()
    return ".".join(morceaux)


def _paquet_courant(chemin: Path, backend: Path) -> str:
    """Le paquet **contenant** le module — la base des imports relatifs."""
    module = _module_du_fichier(chemin, backend)
    if chemin.name == "__init__.py":
        return module
    return module.rpartition(".")[0]


def _modules_importes(arbre: ast.AST, paquet: str) -> list[str]:
    """Les modules importés, **imports relatifs résolus**.

    La résolution n'est pas un raffinement : sans elle, `from ..api import x` échapperait à un
    contrôle **bloquant**. Un garde-fou qu'une syntaxe alternative contourne ne garde rien — il
    donne seulement l'impression d'avoir regardé.
    """
    trouves: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            trouves.extend(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom):
            if noeud.level == 0:
                if noeud.module:
                    trouves.append(noeud.module)
                continue
            morceaux = paquet.split(".") if paquet else []
            if noeud.level > 1:
                morceaux = morceaux[: -(noeud.level - 1)]
            if noeud.module:
                morceaux = [*morceaux, noeud.module]
            if morceaux:
                trouves.append(".".join(morceaux))
    return trouves


def lire_aretes(racine: Path) -> tuple[AreteCode, ...]:
    """Les imports du backend qui franchissent une frontière de paquet, agrégés et triés.

    Les imports **internes à un paquet** sont écartés : ils ne disent rien du sens des dépendances,
    et les compter noierait la diagonale de la matrice sous le trafic local.
    """
    backend = _racine_backend(racine)
    cumuls: dict[tuple[str, str, str, str], list[str]] = {}

    for chemin, couche in _fichiers_python(racine):
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        source = _paquet_du_fichier(chemin, backend)
        origine = _chemin_relatif(chemin, racine)
        for module in _modules_importes(arbre, _paquet_courant(chemin, backend)):
            tete = module.split(".")[0]
            if tete not in COUCHES:
                continue
            cible = _paquet_du_module(module, backend)
            if cible == source:
                continue
            cumuls.setdefault((couche, tete, source, cible), []).append(origine)

    return tuple(
        AreteCode(
            couche_source=couche_source,
            couche_cible=couche_cible,
            paquet_source=paquet_source,
            paquet_cible=paquet_cible,
            occurrences=len(origines),
            # Dédoublonné : un module qui importe trois fois le même paquet n'est cité qu'une fois
            # dans la liste des origines, mais compte bien trois dans `occurrences`.
            origines=tuple(sorted(set(origines))),
        )
        for (couche_source, couche_cible, paquet_source, paquet_cible), origines in sorted(
            cumuls.items()
        )
    )


def _methodes(noeud: ast.ClassDef) -> frozenset[str]:
    """Les méthodes **publiques** d'une classe. Le privé ne fait pas partie d'un contrat."""
    return frozenset(
        membre.name
        for membre in noeud.body
        if isinstance(membre, ast.FunctionDef | ast.AsyncFunctionDef)
        and not membre.name.startswith("_")
    )


def _classes(racine: Path) -> tuple[_Classe, ...]:
    lues: list[_Classe] = []
    for chemin, couche in _fichiers_python(racine):
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.ClassDef):
                continue
            bases = tuple(ast.unparse(base) for base in noeud.bases)
            lues.append(
                _Classe(
                    nom=noeud.name,
                    fichier=_chemin_relatif(chemin, racine),
                    couche=couche,
                    bases=bases,
                    methodes=_methodes(noeud),
                    # `Protocol` ou `Protocol[T]`, importé sous son nom ou via `typing.Protocol` :
                    # l'appartenance textuelle couvre les trois formes employées par le dépôt.
                    est_protocole=any("Protocol" in base for base in bases),
                )
            )
    return tuple(lues)


def lire_ports(racine: Path) -> tuple[Port, ...]:
    """Les ports du dépôt et les classes qui les satisfont.

    L'appariement est **structurel** — une classe qui porte toutes les méthodes publiques du port.
    C'est le seul appariement qui fonctionne ici : un `Protocol` s'implémente sans héritage, et le
    dépôt ne compte qu'un héritage explicite pour des dizaines de ports. Un inventaire fondé sur
    les bases de classe rendrait donc une page **vide** en affirmant qu'elle est complète — le
    genre exact de « rendu qui affirme faux » qu'ADR-0086 veut empêcher.

    Un port **sans méthode publique** (un simple marqueur) n'apparie personne : tout le monde
    satisfait l'ensemble vide. Ses adapters restent vides et il n'est pas signalé pour autant — il
    n'y a rien à constater, seulement rien à dire.
    """
    classes = _classes(racine)
    ports = [classe for classe in classes if classe.est_protocole]
    # Un `Protocol` en satisfait souvent un autre par accident (mêmes méthodes) : les exclure évite
    # d'annoncer qu'un port est « implémenté » par une seconde interface, qui n'implémente rien.
    candidats = [classe for classe in classes if not classe.est_protocole]

    return tuple(
        sorted(
            (
                Port(
                    nom=port.nom,
                    fichier=port.fichier,
                    couche=port.couche,
                    methodes=tuple(sorted(port.methodes)),
                    adapters=tuple(
                        sorted(
                            f"{candidat.fichier}::{candidat.nom}"
                            for candidat in candidats
                            if port.methodes and port.methodes <= candidat.methodes
                        )
                    ),
                    herite=tuple(
                        sorted(
                            f"{candidat.fichier}::{candidat.nom}"
                            for candidat in candidats
                            if any(port.nom == base.split("[")[0] for base in candidat.bases)
                        )
                    ),
                )
                for port in ports
            ),
            key=lambda port: (port.nom, port.fichier),
        )
    )


_IMPORT_TS = re.compile(r"""(?:from|import)\s*\(?\s*['"]([^'"]+)['"]""")


def _dossier_features(racine: Path) -> Path:
    return racine.joinpath(*FEATURES)


def lire_aretes_front(racine: Path) -> tuple[AreteFeature, ...]:
    """Les imports d'une feature vers une autre — la mesure de la règle 10.

    Lecture par expression régulière, donc **heuristique** : un import écrit autrement lui échappe.
    Elle attrape les trois formes que le front emploie (`from '…'`, `import '…'`, `import('…')`),
    ce qui suffit à mesurer une tendance — jamais à bloquer une CI.
    """
    dossier = _dossier_features(racine)
    if not dossier.is_dir():
        return ()

    cumuls: dict[tuple[str, str], int] = {}
    reference = dossier.resolve()
    for chemin in sorted(dossier.rglob("*.ts*")):
        feature = chemin.relative_to(dossier).parts[0]
        for specificateur in _IMPORT_TS.findall(chemin.read_text(encoding="utf-8")):
            if not specificateur.startswith("."):
                continue  # `shared/…`, `react` : hors du graphe des features
            try:
                vise = (chemin.parent / specificateur).resolve().relative_to(reference)
            except ValueError:
                continue  # sort de `features/` — c'est `shared/` ou `app/`, pas une arête
            autre = vise.parts[0]
            if autre != feature:
                cumuls[(feature, autre)] = cumuls.get((feature, autre), 0) + 1

    return tuple(
        AreteFeature(de=de, vers=vers, occurrences=occurrences)
        for (de, vers), occurrences in sorted(cumuls.items())
    )


def enchevetrements(aretes: tuple[AreteFeature, ...]) -> tuple[NoeudEnchevetre, ...]:
    """Les groupes de features qui s'importent mutuellement — Tarjan, composantes de taille > 1.

    On rend des **composantes fortement connexes**, jamais « le nombre de cycles » : ce dernier
    dépend de l'ordre de parcours, donc deux exécutions du même code sur le même dépôt pourraient
    en annoncer des comptes différents. Sur une sortie commitée et comparée à l'octet, une mesure
    qui dépend de l'ordre de parcours n'est pas une mesure — c'est un clignotant.
    """
    voisins: dict[str, list[str]] = {}
    for arete in aretes:
        voisins.setdefault(arete.de, []).append(arete.vers)
        voisins.setdefault(arete.vers, [])

    index: dict[str, int] = {}
    bas: dict[str, int] = {}
    pile: list[str] = []
    sur_pile: set[str] = set()
    composantes: list[list[str]] = []
    compteur = 0

    def parcourir(sommet: str) -> None:
        nonlocal compteur
        index[sommet] = bas[sommet] = compteur
        compteur += 1
        pile.append(sommet)
        sur_pile.add(sommet)
        for voisin in sorted(voisins.get(sommet, ())):
            if voisin not in index:
                parcourir(voisin)
                bas[sommet] = min(bas[sommet], bas[voisin])
            elif voisin in sur_pile:
                bas[sommet] = min(bas[sommet], index[voisin])
        if bas[sommet] == index[sommet]:
            composante: list[str] = []
            while True:
                dernier = pile.pop()
                sur_pile.discard(dernier)
                composante.append(dernier)
                if dernier == sommet:
                    break
            composantes.append(sorted(composante))

    for sommet in sorted(voisins):
        if sommet not in index:
            parcourir(sommet)

    return tuple(
        NoeudEnchevetre(features=tuple(composante))
        for composante in sorted(composantes, key=lambda c: (-len(c), c))
        if len(composante) > 1
    )
