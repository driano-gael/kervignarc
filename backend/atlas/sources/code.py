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
from functools import cache
from pathlib import Path

from atlas.modele import AreteCode, AreteFeature, AtlasSourceInvalide, NoeudEnchevetre, Port

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
#: Deux autorisations vont au-delà de la lettre de la prose. Elles sont écrites ici **et** dans
#: l'amendement `E00US020` d'ADR-0086 — sans quoi un relecteur futur « corrigerait l'oubli » en
#: retirant une arête, et produirait des dizaines de faux bloquants le lendemain :
#:
#: - `infrastructure → application` : quelques ports techniques (l'authentification) sont déclarés
#:   dans `application/`, et leur adapter doit bien les importer. Étendue réelle : **un** import.
#:   Que ces ports ne soient pas dans le domaine est un écart à la règle 2 — mais il est
#:   **signalé** (`port-hors-domaine`), pas bloqué : trancher mécaniquement qu'un port
#:   d'authentification est du métier de tir à l'arc reviendrait à arbitrer seul une conception ;
#: - `api → infrastructure` : la règle 5 impose le mapping des erreurs à la frontière API, et les
#:   objets câblés par `bootstrap` sont typés dans les signatures `Depends` (règle 6). 39 imports
#:   répartis sur 32 fichiers à raison de un ou deux chacun — c'est le patron de câblage, pas une
#:   fuite. Cette arête n'est écrite ni dans la règle 2 ni dans le guide : c'est un **arbitrage**,
#:   pas une transcription, et il doit se lire comme tel.
#:
#: `test_domain_isolation.py` reste **complémentaire** et n'est pas subsumé : il couvre
#: `domain → {frameworks, outillage}`, que cette table ne regarde pas (elle ne retient que les
#: têtes appartenant aux couches). Les fusionner perdrait de la couverture.
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


def est_hors_domaine(port: Port) -> bool:
    """La règle 2 veut les ports **dans le domaine**. Écrit ici, et nulle part ailleurs.

    Ce prédicat et le suivant étaient recopiés dans `carte.py` **et** dans `controles.py` : la page
    et la porte pouvaient donc diverger en silence. C'est l'argument même que `carte.py` oppose à
    un recalcul en JavaScript — il vaut aussi entre deux modules Python.
    """
    return port.couche != "domain"


def est_sans_adapter(port: Port) -> bool:
    """Aucune classe du backend ne satisfait ce port. Le seul cas **exact** de l'inventaire."""
    return bool(port.methodes) and not port.adapters


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
    """Tous les modules des cinq couches, triés — l'ordre de sortie est comparé à l'octet en CI.

    ⚠️ **Une couche absente ou vide fait échouer la lecture**, elle ne rend pas zéro fichier.
    `rglob` sur un répertoire inexistant ne lève rien : renommer `bootstrap/` aurait fait fondre
    ses imports, vidé sa ligne de la matrice, rendu **invisible** tout futur `api → composition`
    — et la porte serait restée **verte**, parce qu'elle n'aurait rien regardé. Le plancher agrégé
    des tests ne l'aurait pas vu non plus : mesuré, le dépôt passe encore `imports >= 500` après
    la disparition de `bootstrap` (713), d'`infrastructure` (669) ou d'`api` (517).

    C'est le seul mode de défaillance dont on ne se relève pas : le diff de `carte.js` est replié
    par `.gitattributes`, la CI est verte, et l'atlas affirme une architecture saine pendant des
    mois. Un garde-fou doit échouer **bruyamment** quand il ne peut pas faire son travail.
    """
    backend = _racine_backend(racine)
    fichiers: list[tuple[Path, str]] = []
    for couche in COUCHES:
        dossier = backend / couche
        if not dossier.is_dir():
            raise AtlasSourceInvalide(
                f"{BACKEND}/{couche}/ est introuvable : la carte du code ne peut pas être "
                f"établie.\nUne couche renommée ou déplacée vide silencieusement la matrice de "
                f"dépendances — et la porte resterait verte faute d'avoir rien lu. Corrige "
                f"`COUCHES` dans atlas/sources/code.py si le découpage a réellement changé."
            )
        trouves = sorted(dossier.rglob("*.py"))
        if not trouves:
            raise AtlasSourceInvalide(
                f"{BACKEND}/{couche}/ ne contient aucun module Python : refus de conclure que "
                f"cette couche ne dépend de rien."
            )
        fichiers.extend((chemin, couche) for chemin in trouves)
    return fichiers


@cache
def _arbre(chemin: Path) -> ast.Module:
    """L'arbre d'un module, lu **une seule fois** et converti au contrat d'erreurs du générateur.

    Deux corrections en une, toutes deux relevées en revue :

    - `ast.parse` non gardé laissait remonter une `SyntaxError` ou une `UnicodeDecodeError`
      **nue**, avec sa trace, alors que tout le reste de l'atlas passe par `AtlasSourceInvalide`
      → sortie 2 → message lisible. `rendu.py` s'était déjà donné la règle : « un fichier tronqué
      doit produire le message prévu, pas une trace remontée depuis un hook pre-commit ». Le motif
      du hook couvrant désormais tout `backend/**.py`, le cas se rencontre en cours de refactor ;
    - les 217 modules étaient parsés **deux fois** (une passe pour les imports, une pour les
      classes) — ~0,8 s sur les ~5 s facturées à presque chaque commit, et le défaut exact
      qu'`E00US019` venait de corriger sur le tracker. Le cache est sûr ici : le générateur est
      mono-passe et le dépôt ne bouge pas sous lui.
    """
    try:
        return ast.parse(chemin.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as erreur:
        raise AtlasSourceInvalide(f"{chemin} n'est pas du Python lisible : {erreur}") from erreur


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


def _import_dynamique(noeud: ast.Call) -> str | None:
    """`importlib.import_module("api.v1")` ou `__import__("api")` — la cible, si elle est littérale.

    ⚠️ Ce n'est pas une exhaustivité de façade : un module calculé (`import_module(nom)`) reste
    hors de portée, et le restera. Mais `importlib.import_module` est **la** syntaxe qu'on écrit
    pour casser un cycle d'imports — c'est-à-dire dans la situation même que cette porte
    surveille. Laisser béante la seule échappatoire qu'un développeur a une raison d'emprunter,
    c'est garder l'apparence d'avoir regardé.
    """
    appele = noeud.func
    nom = (
        appele.attr
        if isinstance(appele, ast.Attribute)
        else appele.id
        if isinstance(appele, ast.Name)
        else ""
    )
    if nom not in {"import_module", "__import__"} or not noeud.args:
        return None
    premier = noeud.args[0]
    return (
        premier.value
        if isinstance(premier, ast.Constant) and isinstance(premier.value, str)
        else None
    )


def _modules_importes(arbre: ast.AST, paquet: str) -> list[str]:
    """Les modules importés — imports relatifs résolus, imports dynamiques littéraux compris.

    ⚠️ **La résolution des relatifs ne change aujourd'hui aucun verdict, et c'est écrit ici pour
    ne pas sur-vendre le garde-fou.** Les cinq couches sont des paquets de **premier niveau** (il
    n'existe pas de `backend/__init__.py`), donc un import relatif valide reste toujours à
    l'intérieur de son propre paquet, donc de sa propre couche — et le dépôt n'en contient
    d'ailleurs aucun. La résolution est une défense contre une **évolution de la racine de
    paquet**, pas contre un contournement d'aujourd'hui. La version précédente de ce commentaire
    affirmait le contraire (« sans elle, `from ..api import x` échapperait au contrôle ») : c'était
    faux — depuis `infrastructure/db/`, cet import désigne `infrastructure.api`. Le projet traite
    une justification sur-vendue comme un défaut, ADR-0017 lui a coûté treize mois.
    """
    trouves: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Call):
            dynamique = _import_dynamique(noeud)
            if dynamique:
                trouves.append(dynamique)
        elif isinstance(noeud, ast.Import):
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
        arbre = _arbre(chemin)
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


def _membres(noeud: ast.ClassDef) -> frozenset[str]:
    """Les membres **publics** d'une classe : méthodes **et attributs annotés**.

    ⚠️ Les attributs comptent, et c'est le correctif central de la revue. Un port déclare ses
    membres en `@property` (il le doit : c'est une interface) tandis que son implémentation les
    porte en **champs de dataclass `frozen`** — la règle 4 privilégie l'immutabilité dans le
    domaine, donc c'est le patron **dominant** ici. En ne lisant que les `FunctionDef`,
    l'appariement ratait systématiquement ce couple : les deux seuls signaux `port-sans-adapter`
    livrés (`EtapeSequencee`, `EtapeProjetable`) étaient **tous les deux faux**, et leurs propres
    docstrings disaient déjà que `Phase` et `ModelePhase` satisfont le contrat.

    Le précédent est dans le même fichier : ADR-0086 a **retiré** le contrôle « titre divergent »
    sur exactement ce ratio — « 0 vrai positif sur 2 signaux […] un signal à la fois bruyant et
    poreux n'apprend qu'à ignorer la page ». Ce contrôle-ci, lui, pouvait être rendu juste.
    """
    membres = {
        membre.name
        for membre in noeud.body
        if isinstance(membre, ast.FunctionDef | ast.AsyncFunctionDef)
        and not membre.name.startswith("_")
    }
    membres |= {
        membre.target.id
        for membre in noeud.body
        if isinstance(membre, ast.AnnAssign)
        and isinstance(membre.target, ast.Name)
        and not membre.target.id.startswith("_")
    }
    return frozenset(membres)


def _classes(racine: Path) -> tuple[_Classe, ...]:
    lues: list[_Classe] = []
    for chemin, couche in _fichiers_python(racine):
        arbre = _arbre(chemin)
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
                    methodes=_membres(noeud),
                    # `Protocol` ou `Protocol[T]`, importé sous son nom ou via `typing.Protocol` :
                    # l'appartenance textuelle couvre les trois formes employées par le dépôt.
                    est_protocole=any("Protocol" in base for base in bases),
                )
            )
    return tuple(lues)


def lire_ports(racine: Path) -> tuple[Port, ...]:
    """Les ports du dépôt et les classes qui les satisfont.

    L'appariement est **structurel** — une classe qui porte tous les membres publics du port.
    C'est le seul appariement qui fonctionne ici : un `Protocol` s'implémente **sans héritage**, et
    le dépôt ne compte aucun héritage de port par une implémentation. Un inventaire fondé sur les
    bases de classe rendrait donc une page **vide** en affirmant qu'elle est complète — le genre
    exact de « rendu qui affirme faux » qu'ADR-0086 veut empêcher.

    Un port **sans membre public** (un simple marqueur) n'apparie personne : tout le monde
    satisfait l'ensemble vide. Ses adapters restent vides et il n'est pas signalé pour autant — il
    n'y a rien à constater, seulement rien à dire.
    """
    classes = _classes(racine)
    ports = [classe for classe in classes if classe.est_protocole]
    # Un `Protocol` en satisfait souvent un autre par accident (mêmes membres) : les exclure évite
    # d'annoncer qu'un port est « implémenté » par une seconde interface, qui n'implémente rien.
    candidats = [classe for classe in classes if not classe.est_protocole]
    par_nom = {port.nom: port for port in ports}

    def contrat(port: _Classe, vus: frozenset[str] = frozenset()) -> frozenset[str]:
        """Les membres exigés par un port, **héritage de port compris**.

        Sans cette remontée, `EtapeProjetable(EtapeSequencee, Protocol)` était publié avec **3**
        membres alors qu'il en exige **7** — donc affiché comme plus facile à satisfaire qu'il ne
        l'est, et apparié à des classes qui ne l'implémentent pas. `vus` borne la récursion : une
        hiérarchie cyclique est impossible en Python, mais un lecteur ne doit pas en dépendre.
        """
        exiges = port.methodes
        for base in port.bases:
            nom = base.split("[")[0]
            herite = par_nom.get(nom)
            if herite is not None and nom not in vus:
                exiges |= contrat(herite, vus | {port.nom})
        return exiges

    return tuple(
        sorted(
            (
                Port(
                    nom=port.nom,
                    fichier=port.fichier,
                    couche=port.couche,
                    methodes=tuple(sorted(contrat(port))),
                    adapters=tuple(
                        sorted(
                            f"{candidat.fichier}::{candidat.nom}"
                            for candidat in candidats
                            if contrat(port) and contrat(port) <= candidat.methodes
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


def lister_features(racine: Path) -> tuple[str, ...]:
    """Les features telles que le **disque** les porte, pas telles que le graphe les révèle.

    ⚠️ Compter les extrémités d'arêtes donnait le bon nombre aujourd'hui — par coïncidence, les 44
    features participent toutes au graphe — mais une feature **autonome** n'a aucune arête, donc
    n'existait pas pour le compteur. Le jour où `E00US023` fait son travail, la page aurait annoncé
    « 38 features » **parce que six seraient devenues saines** : un chiffre qui décroît quand
    l'architecture s'améliore, publié en tête de page et repris dans la recette du journal.
    """
    dossier = _dossier_features(racine)
    _exiger_le_front(dossier)
    return tuple(sorted(enfant.name for enfant in dossier.iterdir() if enfant.is_dir()))


def _exiger_le_front(dossier: Path) -> None:
    """Même raison que pour les couches : ne jamais conclure « rien » d'un dossier qu'on n'a pas lu.

    `E00US023`, que cette US inscrit au backlog, **déplace précisément** `features/`. Un `return ()`
    silencieux aurait alors annoncé « 0 feature, 0 enchevêtrement » — c'est-à-dire exactement le
    résultat qu'`E00US023` cherche à produire, rendu indiscernable de sa réussite.
    """
    if not dossier.is_dir():
        raise AtlasSourceInvalide(
            f"{'/'.join(FEATURES)} est introuvable : la carte du front ne peut pas être établie.\n"
            f"Rendre « 0 feature » serait indiscernable d'un front parfaitement découpé."
        )


def _est_un_test(chemin: Path) -> bool:
    """`Saisie.test.ts`, `volees.spec.tsx` — du code de test, pas du couplage de production."""
    return ".test." in chemin.name or ".spec." in chemin.name


def lire_aretes_front(racine: Path) -> tuple[AreteFeature, ...]:
    """Les imports d'une feature vers une autre — la mesure de la règle 10.

    Lecture par expression régulière, donc **heuristique** : un import écrit autrement lui échappe.
    Elle attrape les trois formes que le front emploie (`from '…'`, `import '…'`, `import('…')`),
    ce qui suffit à mesurer une tendance — jamais à bloquer une CI.

    ⚠️ **Les fichiers de test sont exclus.** Ils ne pesaient que 3 arêtes sur 142 — mais ces 3
    suffisaient à faire naître un **nœud d'enchevêtrement entier** (`accueil ↔ completude ↔
    paiements`), soit un quart des nœuds annoncés. Or le grief fait à un nœud est qu'« aucune
    feature ne peut plus être lue, **testée** ni retirée seule » : le fonder sur le test lui-même
    n'a pas de sens. Sans eux : 139 arêtes, 3 nœuds.
    """
    dossier = _dossier_features(racine)
    _exiger_le_front(dossier)

    cumuls: dict[tuple[str, str], int] = {}
    reference = dossier.resolve()
    for chemin in sorted(dossier.rglob("*.ts*")):
        if _est_un_test(chemin):
            continue
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
