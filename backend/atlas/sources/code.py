"""Ce que le code fait réellement des règles d'architecture — lu dans le code, pas dans les docs.

Les autres sources lisent des documents ; celle-ci lit le **dépôt** : quelle couche dépend de quelle
autre (la règle 2 n'était vérifiée **que pour le domaine**), où sont les ports et qui les
implémente, comment le front est découpé (règle 10). ⚠️ Le backend est lu à l'**AST**, exact y
compris sous `if TYPE_CHECKING` — c'est ce qui autorise un contrôle **bloquant** ; le front est lu
à l'**expression régulière** (l'atlas n'a aucune dépendance, ADR-0086), donc **rien n'y bloque**.
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

#: Ce que chaque couche a le droit d'importer. Dérivé des **règles écrites** : règle 1, règle 2,
#: règle 8. ⚠️ **`bootstrap` n'apparaît dans aucune valeur** — la racine de composition est un
#: consommateur **terminal** : quiconque l'importe inverse le câblage. Deux autorisations vont
#: au-delà de la lettre de la prose, et sont écrites ici **et** dans l'amendement `E00US020`
#: d'ADR-0086 : `infrastructure → application` (un seul import, ports techniques déclarés dans
#: `application/`, signalés par `port-hors-domaine` et non bloqués) et `api → infrastructure`
#: (39 imports, patron de câblage des `Depends`, règle 5 et règle 6 — c'est un **arbitrage**, pas
#: une transcription). `test_domain_isolation.py` reste complémentaire : il couvre les frameworks.
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

    ⚠️ **Une couche absente ou vide fait échouer la lecture**, elle ne rend pas zéro fichier :
    `rglob` sur un répertoire inexistant ne lève rien, donc renommer `bootstrap/` aurait vidé sa
    ligne de la matrice et laissé la porte **verte** parce qu'elle n'aurait rien regardé. Le
    plancher agrégé ne l'aurait pas vu non plus (le dépôt passe `imports >= 500` même sans
    `bootstrap`). Un garde-fou doit échouer **bruyamment** quand il ne peut pas travailler.
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

    Deux corrections relevées en revue : `ast.parse` non gardé laissait remonter une `SyntaxError`
    **nue** au lieu d'`AtlasSourceInvalide` → sortie 2 → message lisible, alors que le motif du hook
    couvre désormais tout `backend/**.py` ; et les 217 modules étaient parsés **deux fois** (~0,8 s
    sur les ~5 s facturées à presque chaque commit). Le cache est sûr : le générateur est mono-passe
    et le dépôt ne bouge pas sous lui.
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

    ⚠️ **La résolution des relatifs ne change aujourd'hui aucun verdict**, et c'est écrit pour ne
    pas sur-vendre le garde-fou : les cinq couches sont des paquets de premier niveau, donc un
    import relatif valide reste dans sa propre couche — et le dépôt n'en contient aucun. C'est une
    défense contre une **évolution de la racine de paquet**. La version précédente affirmait le
    contraire ; le projet traite une justification sur-vendue comme un défaut (ADR-0017).
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

    ⚠️ Les attributs comptent, et c'est le correctif central de la revue : un port déclare ses
    membres en `@property` tandis que son implémentation les porte en **champs de dataclass
    `frozen`** — le patron dominant ici (règle 4). En ne lisant que les `FunctionDef`, l'appariement
    ratait ce couple : les deux seuls signaux `port-sans-adapter` livrés étaient **tous deux faux**.
    Le précédent est dans le même fichier — ADR-0086 a retiré « titre divergent » sur ce ratio.
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

    L'appariement est **structurel** — une classe qui porte tous les membres publics du port. C'est
    le seul qui fonctionne ici : un `Protocol` s'implémente **sans héritage**, et le dépôt ne compte
    aucun héritage de port. Un inventaire fondé sur les bases de classe rendrait une page **vide**
    en affirmant qu'elle est complète (ADR-0086). Un port **sans membre public** n'apparie personne
    et n'est pas signalé pour autant : il n'y a rien à constater.
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

    Lecture par expression régulière, donc **heuristique** : elle attrape les trois formes que le
    front emploie, ce qui suffit à mesurer une tendance, jamais à bloquer une CI. ⚠️ **Les fichiers
    de test sont exclus** : ils ne pesaient que 3 arêtes sur 142, mais ces 3 suffisaient à faire
    naître un **nœud d'enchevêtrement entier** — or le grief fait à un nœud est qu'aucune feature
    ne peut plus être lue, **testée** ni retirée seule. Sans eux : 139 arêtes, 3 nœuds.
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
