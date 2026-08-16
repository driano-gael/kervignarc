"""Primitives de lecture du Markdown du dépôt.

Règle de conduite de tout l'atlas : **on ne parse jamais de la prose.** On ne lit que des formes
tenues par une convention — en-tête à puces, titre de section, chemin entre accents graves. Le
reste se **lie** (un lien vers le fichier source), il ne s'extrait pas. Un parseur qui devine finit
par affirmer, et un atlas qui affirme faux est pire qu'un atlas absent.
"""

from __future__ import annotations

import re
from pathlib import Path

from atlas.modele import AtlasSourceInvalide
from atlas.normalisation import cle


# ⚠️ `encoding="utf-8"` n'est pas décoratif : le poste de développement est sous Windows, où
# `read_text()` sans encodage explicite retombe sur cp1252 et massacre un corpus intégralement
# francophone. Même raison pour `newline="\n"` à l'écriture (cf. `rendu.py`).
def lire(chemin: Path) -> str:
    """Le texte d'une source — ou un refus qui nomme le fichier manquant.

    Un `FileNotFoundError` nu remonté depuis un hook pre-commit est un piège à trois heures
    perdues, et il se déclenche pendant une US urgente. `AtlasSourceInvalide` sort en code 2
    (« source invalide ») avec le chemin en clair : le générateur déclare ainsi ce dont il dépend.
    """
    try:
        return chemin.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AtlasSourceInvalide(
            f"source absente : « {chemin} ». L'atlas lit des fichiers versionnés du dépôt ; "
            f"celui-ci manque, et rien ne peut être déduit de son absence."
        ) from None


_H1 = re.compile(r"^# +(?P<titre>.+?)\s*$", re.MULTILINE)
_PUCE_ENTETE = re.compile(r"^- \*\*(?P<libelle>[^*]+?)\*\*\s*:?\s*(?P<valeur>.*)$")


def titre(texte: str) -> str:
    """Le titre de niveau 1 du document."""
    trouve = _H1.search(texte)
    return trouve.group("titre").strip() if trouve else ""


def avant_premiere_section(texte: str) -> str:
    """Le préambule : tout ce qui précède le premier titre `## `.

    C'est là que vivent les en-têtes à puces des ADR. Attention : certains ADR ouvrent par un
    encadré d'avertissement (`> ⚠️ Amendé par…`) **avant** leur en-tête — d'où l'usage d'une borne
    de fin plutôt que d'un décalage fixe depuis le début du fichier.
    """
    coupe = re.search(r"^## ", texte, re.MULTILINE)
    return texte[: coupe.start()] if coupe else texte


def entete_a_puces(texte: str) -> list[tuple[str, str]]:
    """Les champs `- **Libellé** : valeur` du préambule, dans l'ordre du fichier.

    Les valeurs courent souvent sur plusieurs lignes indentées ; elles sont recollées en une seule
    chaîne. Les puces indentées (sous-listes) ne sont pas des champs et sont donc ignorées.
    """
    champs: list[tuple[str, list[str]]] = []
    for ligne in avant_premiere_section(texte).split("\n"):
        entete = _PUCE_ENTETE.match(ligne)
        if entete:
            champs.append((entete.group("libelle").strip(), [entete.group("valeur").strip()]))
        elif champs and ligne.startswith((" ", "\t")) and ligne.strip():
            champs[-1][1].append(ligne.strip())
    return [(libelle, " ".join(m for m in morceaux if m).strip()) for libelle, morceaux in champs]


def section(texte: str, nom: str) -> str:
    """Le corps d'une section `## nom`, comparaison insensible à la casse et aux accents.

    Rend une chaîne vide si la section n'existe pas — l'absence d'une section est une information
    que l'appelant traite (cf. le contrôle « ADR structurant sans portage »), pas une erreur.
    """
    recherche = cle(nom)
    lignes = texte.split("\n")
    debut: int | None = None
    for index, ligne in enumerate(lignes):
        if ligne.startswith("## "):
            if debut is not None:
                return "\n".join(lignes[debut:index]).strip()
            if cle(ligne[3:]) == recherche:
                debut = index + 1
    return "\n".join(lignes[debut:]).strip() if debut is not None else ""


_LIEN_MD = re.compile(r"\[(?P<texte>[^\]]*)\]\((?P<cible>[^)]*)\)")
# Le tiret bas est **volontairement absent** : Markdown en fait un marqueur d'italique, mais dans
# ce corpus c'est presque toujours un identifiant de code (`depart_id`, `_TRANSITIONS`). Le retirer
# transformait « depart_id » en « departid » — un nom qui n'existe nulle part.
_BALISE = re.compile(r"[*`]")


def en_clair(markdown: str) -> str:
    """Le texte sans son balisage — pour la recherche et les résumés, pas pour l'affichage."""
    return re.sub(r"\s+", " ", _BALISE.sub("", _LIEN_MD.sub(r"\g<texte>", markdown))).strip()


_SEPARATEUR_DE_TABLEAU = re.compile(r"^[\s|:-]+$")


def tableaux(texte: str) -> list[tuple[list[str], list[list[str]]]]:
    """Les tableaux Markdown de premier niveau, sous forme (en-tête, lignes).

    Les tableaux **en citation** (`> | … |`) sont ignorés : dans ce dépôt, ce sont des vues de
    priorité ou des encadrés, jamais des inventaires. Une ligne plus courte que son en-tête est
    rendue telle quelle — c'est à l'appelant de décider si le décalage est tolérable, parce que la
    réponse dépend de ce qu'il compte : un tableau d'états ne le tolère pas, un tableau descriptif
    s'en accommode.
    """
    trouves: list[tuple[list[str], list[list[str]]]] = []
    entete: list[str] | None = None
    lignes: list[list[str]] = []

    def fermer() -> None:
        if entete is not None:
            trouves.append((entete, lignes))

    for brute in texte.split("\n"):
        if not brute.strip():
            # ⚠️ Une ligne **vide** n'interrompt pas le tableau. Les registres écrits à la main en
            # contiennent, pour aérer des lignes de plusieurs centaines de caractères : les traiter
            # comme une fin de tableau coupait « Dette ouverte » en trois, et le lecteur ne voyait
            # plus que 4 des 53 dettes — silencieusement, puisqu'un morceau de table reste une
            # table bien formée.
            continue
        if not brute.startswith("|"):
            if entete is not None:
                fermer()
                entete, lignes = None, []
            continue
        if _SEPARATEUR_DE_TABLEAU.match(brute):
            continue
        cellules = [c.strip() for c in brute.strip().strip("|").split("|")]
        if entete is None:
            entete, lignes = cellules, []
        else:
            lignes.append(cellules)
    fermer()
    return trouves


def tronquer(texte: str, taille: int) -> str:
    """Coupe sur une frontière de mot, en signalant la coupe."""
    if len(texte) <= taille:
        return texte
    coupe = texte[:taille].rsplit(" ", 1)[0]
    return f"{coupe} […]"
