"""Garde-fou de la règle 13 — un bloc de commentaire ne dépasse pas huit lignes (ADR-0099).

Ce test **est** la règle : les trois « tests de survie » d'ADR-0099 reposent sur une appréciation,
le plafond se compte. ⚠️ Le compte porte sur les **blocs contigus**, docstrings comprises — ce
qu'un lecteur avale d'un trait, pas le nombre de `#`. ⚠️ Périmètre : **tout le code de production**
(les cinq couches, `atlas/`, `release/`, les points d'entrée) ; `tests/` et `migrations/` en sont
**hors**, c'est `DETTE-088` — le front, lui, couvre ses propres tests.
"""

from __future__ import annotations

import tokenize
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
# DETTE-088 — `tests/` et `migrations/` restent hors porte ; le front, lui, couvre ses tests.
_COUVERTS = ("domain", "application", "api", "infrastructure", "bootstrap", "atlas", "release")
_EXCLUS = ("tests", "migrations", ".venv", "__pycache__")

PLAFOND = 8

_FICHIER_CLIQUET = Path(__file__).with_name("commentaires_cliquet.txt")


def _charger_cliquet(fichier: Path = _FICHIER_CLIQUET) -> dict[str, int]:
    """Lit la baseline depuis un fichier plat : un chemin, une espace, un compte.

    Hors du code du test délibérément : mille entrées dans un littéral Python rendraient le
    garde-fou illisible, et chaque résorption produirait un diff de test au lieu d'un diff de
    donnée.
    """
    if not fichier.exists():
        return {}
    entrees: dict[str, int] = {}
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        nette = ligne.strip()
        if not nette or nette.startswith("#"):
            continue
        chemin, _, compte = nette.rpartition(" ")
        entrees[chemin.strip()] = int(compte)
    return entrees


# ⚠️ **Cliquet, et non exemption.** La valeur est le nombre de blocs trop longs *tolérés* par
# fichier : le test échoue dès qu'il en compte **plus**. Un fichier peut donc s'améliorer, jamais se
# dégrader, et un fichier absent du cliquet n'a droit à aucun bloc long. Ne jamais relever un
# chiffre — le faire descendre est le seul geste autorisé.
_CLIQUET: dict[str, int] = _charger_cliquet()


def _blocs_trop_longs(chemin: Path) -> list[tuple[int, int]]:
    """Les blocs de commentaire contigus dépassant `PLAFOND`, en `(première ligne, longueur)`."""
    with open(chemin, encoding="utf-8") as source:
        try:
            jetons = list(tokenize.generate_tokens(source.readline))
        except (tokenize.TokenError, SyntaxError) as illisible:
            # ⚠️ On relève : un module de production que le tokenizer refuse passerait sinon la
            # porte en silence. `atlas/sources/code.py` a tranché de même (relevé en revue).
            raise AssertionError(f"{chemin} illisible : {illisible}") from illisible

    blocs: list[tuple[int, int]] = []
    courant: tuple[int, int] | None = None
    precedent: int | None = None
    for jeton in jetons:
        # Une docstring est une chaîne en position d'instruction : c'est ce que teste `precedent`.
        # ⚠️ Un `#` posé APRÈS du code n'ouvre pas de bloc — sinon neuf lignes commentées une à une
        # (une table de constantes) rougissaient, et le front, lui, ne les compte pas (revue).
        seul_sur_sa_ligne = not jeton.line[: jeton.start[1]].strip()
        est_commentaire = (jeton.type == tokenize.COMMENT and seul_sur_sa_ligne) or (
            jeton.type == tokenize.STRING
            and precedent in (None, tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT)
        )
        if est_commentaire:
            if courant is not None and jeton.start[0] <= courant[1] + 1:
                courant = (courant[0], jeton.end[0])
            else:
                if courant is not None:
                    blocs.append(courant)
                courant = (jeton.start[0], jeton.end[0])
        if jeton.type not in (tokenize.NL, tokenize.COMMENT):
            precedent = jeton.type
    if courant is not None:
        blocs.append(courant)

    return [(debut, fin - debut + 1) for debut, fin in blocs if fin - debut + 1 > PLAFOND]


def _fichiers_de_production() -> list[Path]:
    # ⚠️ `_EXCLUS` se teste sur le chemin **relatif** : sur l'absolu, un dépôt cloné sous un
    # répertoire nommé `tests` ou `.venv` vidait le balayage en silence (relevé en revue).
    fichiers = list(_BACKEND_ROOT.glob("*.py"))
    for couche in _COUVERTS:
        trouves = [
            chemin
            for chemin in (_BACKEND_ROOT / couche).rglob("*.py")
            if not any(part in _EXCLUS for part in chemin.relative_to(_BACKEND_ROOT).parts)
        ]
        # ⚠️ Une couche vide ou renommee ne rend pas zero fichier : `rglob` ne leve pas. Le plancher
        # agrege ne l'attrape pas non plus — retirer `domain` laisse 188 fichiers sur 255.
        assert trouves, f"couche « {couche} » vide ou absente — périmètre cassé"
        fichiers.extend(trouves)
    return fichiers


def test_aucun_fichier_ne_gagne_de_bloc_trop_long() -> None:
    """Règle 13 : huit lignes au plus par bloc — au-delà, le raisonnement va en ADR."""
    fichiers = _fichiers_de_production()
    # ⚠️ Sans cette borne, un périmètre cassé rend la porte **verte et vide** : `rglob` sur un
    # dossier absent ne lève pas, il rend une liste vide (relevé en revue).
    assert len(fichiers) > 150, f"le balayage n'a lu que {len(fichiers)} fichiers — périmètre cassé"

    regressions: list[str] = []
    for chemin in fichiers:
        relatif = chemin.relative_to(_BACKEND_ROOT).as_posix()
        trop_longs = _blocs_trop_longs(chemin)
        tolere = _CLIQUET.get(relatif, 0)
        if len(trop_longs) > tolere:
            ou = ", ".join(f"l.{ligne} ({taille})" for ligne, taille in trop_longs[:5])
            regressions.append(
                f"{relatif} : {len(trop_longs)} blocs > {PLAFOND} lignes "
                f"(toléré {tolere}) — {ou}"
            )

    assert not regressions, (
        f"{len(regressions)} fichier(s) gagnent un bloc de commentaire trop long.\n"
        f"Un bloc de plus de {PLAFOND} lignes n'est plus un avertissement : son raisonnement va en "
        "ADR / story / registre, et le code garde un renvoi d'une ligne (ADR-0099, règle 13).\n"
        "Le cliquet ne se relève pas — faire descendre un chiffre est le seul geste autorisé.\n\n"
        + "\n".join(regressions[:30])
    )


def test_le_detecteur_voit_la_borne(tmp_path: Path) -> None:
    """Neuf lignes rougissent, huit passent — le pendant backend des cas du détecteur front.

    ⚠️ Sans lui, un détecteur cassé rend `[]` partout et la porte reste **verte** sur un dépôt déjà
    à zéro. C'est la panne exacte qui a laissé 13 blocs JSX passer côté front (relevé en revue).
    """
    neuf = tmp_path / "neuf.py"
    neuf.write_text("# x\n" * 9 + "a = 1\n", encoding="utf-8")
    assert _blocs_trop_longs(neuf) == [(1, 9)]

    huit = tmp_path / "huit.py"
    huit.write_text("# x\n" * 8 + "a = 1\n", encoding="utf-8")
    assert _blocs_trop_longs(huit) == []


def test_le_detecteur_compte_les_docstrings_et_pas_les_chaines(tmp_path: Path) -> None:
    """Une docstring compte, une chaîne **affectée** non — c'est la condition `precedent`.

    La mesure d'entrée de l'US était fausse d'un facteur trois pour n'avoir pas vu les docstrings :
    c'est la frontière la plus coûteuse du détecteur, et elle n'était figée nulle part.
    """
    doc = tmp_path / "doc.py"
    doc.write_text('"""' + "x\n" * 9 + '"""' + "\na = 1\n", encoding="utf-8")
    assert _blocs_trop_longs(doc) == [(1, 10)]

    affectee = tmp_path / "affectee.py"
    affectee.write_text("X = " + '"""' + "x\n" * 11 + '"""' + "\n", encoding="utf-8")
    assert _blocs_trop_longs(affectee) == []


def test_le_detecteur_ignore_les_dieses_de_fin_de_ligne(tmp_path: Path) -> None:
    """Neuf lignes de code commentées une à une ne font pas un bloc — le front ne les compte pas."""
    fin_de_ligne = tmp_path / "fin.py"
    fin_de_ligne.write_text("a = 1  # x\n" * 9, encoding="utf-8")
    assert _blocs_trop_longs(fin_de_ligne) == []

    # ⚠️ Limite assumée, `DETTE-088` : une ligne vide coupe le bloc, des deux côtés.
    coupe = tmp_path / "coupe.py"
    coupe.write_text("# x\n" * 5 + "\n" + "# x\n" * 5 + "a = 1\n", encoding="utf-8")
    assert _blocs_trop_longs(coupe) == []


def test_le_chargeur_de_cliquet_lit_une_entree(tmp_path: Path) -> None:
    """La soupape est vide, donc son parseur dort — il servirait le jour où on l'ouvrirait."""
    fichier = tmp_path / "cliquet.txt"
    fichier.write_text("# un commentaire\n\ndomain/x.py 3\n", encoding="utf-8")
    assert _charger_cliquet(fichier) == {"domain/x.py": 3}


def test_aucun_paquet_de_production_hors_perimetre() -> None:
    """`_COUVERTS` est une liste blanche : un paquet neuf y serait **hors porte en silence**."""
    paquets = {
        chemin.parent.name
        for chemin in _BACKEND_ROOT.glob("*/__init__.py")
        if chemin.parent.name not in _EXCLUS
    }
    hors = sorted(paquets - set(_COUVERTS))
    assert not hors, f"paquets de production hors du plafond — {hors}"


def test_le_cliquet_est_vide() -> None:
    """Vidé en E00US027 : `CLAUDE.md` règle 13 annonce le plafond « sans tolérance ».

    ⚠️ Sans ce test, rouvrir la soupape est un diff d'une ligne dans un fichier de **données**, que
    rien ne fait rougir. Avec lui, c'est un diff de **test** — donc un geste que la revue voit.
    """
    assert not _CLIQUET, f"cliquet rouvert — {sorted(_CLIQUET)}"


def test_le_cliquet_ne_contient_que_des_fichiers_existants() -> None:
    """Une baseline ne tient que si elle ne peut pas pourrir.

    Une entrée orpheline laisserait une tolérance recyclable par un fichier neuf portant le même
    chemin — exactement ce que le cliquet interdit.
    """
    manquants = [relatif for relatif in _CLIQUET if not (_BACKEND_ROOT / relatif).exists()]
    assert not manquants, f"cliquet : entrées sans fichier — {manquants}"
