"""Primitives de lecture du Markdown du dépôt.

Règle de conduite de tout l'atlas : **on ne parse jamais de la prose.** On ne lit que des formes
tenues par une convention — en-tête à puces, titre de section, chemin entre accents graves. Le
reste se **lie** (un lien vers le fichier source), il ne s'extrait pas. Un parseur qui devine finit
par affirmer, et un atlas qui affirme faux est pire qu'un atlas absent.
"""

from __future__ import annotations

import re
from pathlib import Path

from atlas.normalisation import cle


# ⚠️ `encoding="utf-8"` n'est pas décoratif : le poste de développement est sous Windows, où
# `read_text()` sans encodage explicite retombe sur cp1252 et massacre un corpus intégralement
# francophone. Même raison pour `newline="\n"` à l'écriture (cf. `rendu.py`).
def lire(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8")


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


def tronquer(texte: str, taille: int) -> str:
    """Coupe sur une frontière de mot, en signalant la coupe."""
    if len(texte) <= taille:
        return texte
    coupe = texte[:taille].rsplit(" ", 1)[0]
    return f"{coupe} […]"
