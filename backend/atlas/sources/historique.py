"""L'historique réel d'une règle, lu dans git.

`git log -L <debut>,<fin>:CLAUDE.md` suit un **bloc de lignes** à travers l'historique, y compris
quand le bloc se déplace. C'est ce qui donne l'historique complet d'une règle : les incises datées
écrites à la main n'en couvrent que six, alors que dix-neuf commits ont touché le fichier. Les
sujets de commit portent le périmètre d'US (`feat(e02us002): …`), donc le lien règle → US se déduit
sans heuristique.

⚠️ **Pourquoi cette sortie est isolée dans son propre fichier.** Le reste des données générées est
une fonction pure de l'arbre de travail, donc comparable à l'octet près en CI. L'historique, lui,
ne l'est pas : au moment du hook pre-commit, le commit en cours **n'existe pas encore**, alors que
la CI — qui tourne une fois la branche poussée — le voit. Une comparaison stricte serait donc
**rouge en permanence**, et une porte toujours rouge finit désactivée. D'où la vérification par
**tolérance d'ajout** (cf. `rendu.py`) : la régénération peut contenir des entrées de plus, jamais
en contredire une déjà commitée.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from atlas.modele import Amendement, Regle

_SEPARATEUR = "\x1f"
_FORMAT = f"%H{_SEPARATEUR}%ad{_SEPARATEUR}%s"
_US_CITEE = re.compile(r"[Ee]\d{2}[Uu][Ss]\d{3}")
_ADR_CITE = re.compile(r"ADR-(\d{4})", re.IGNORECASE)


def _git(racine: Path, *arguments: str) -> str:
    """Appelle git en lecture seule. Rend une chaîne vide si git est indisponible.

    L'atlas doit rester consultable dans une archive sans `.git` : l'absence d'historique dégrade
    la fiche d'une règle, elle ne casse pas la génération.
    """
    try:
        # Arguments littéraux, jamais d'entrée utilisateur : pas de `shell=True`, pas de format.
        acheve = subprocess.run(
            ["git", "-C", str(racine), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            # Ce code tourne dans un hook pre-commit et dans un job de CI : un `git` qui pend
            # (verrou `index.lock`, invite d'authentification) doit dégrader, pas bloquer jusqu'au
            # délai de la plateforme.
            timeout=60,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return ""
    return acheve.stdout if acheve.returncode == 0 else ""


def disponible(racine: Path) -> bool:
    return bool(_git(racine, "rev-parse", "--git-dir").strip())


def _amendements_du_bloc(
    racine: Path, fichier: str, debut: int, fin: int
) -> tuple[Amendement, ...]:
    sortie = _git(
        racine,
        "log",
        "--no-patch",
        f"-L{debut},{max(fin, debut)}:{fichier}",
        f"--format={_FORMAT}",
        "--date=short",
    )
    trouves: list[Amendement] = []
    for ligne in sortie.split("\n"):
        morceaux = ligne.split(_SEPARATEUR)
        if len(morceaux) != 3:
            continue
        empreinte, date, sujet = morceaux
        trouves.append(
            Amendement(
                date=date.strip(),
                nature="commit",
                motif=sujet.strip(),
                us=tuple(dict.fromkeys(u.upper() for u in _US_CITEE.findall(sujet))),
                adr=tuple(dict.fromkeys(_ADR_CITE.findall(sujet))),
                origine="git",
                reference=empreinte.strip()[:10],
            )
        )
    return tuple(trouves)


def historique(racine: Path, regles: tuple[Regle, ...]) -> dict[str, tuple[Amendement, ...]]:
    """L'historique de chaque règle, indexé par son ancre — dans l'ordre que git rend.

    ⚠️ **On ne retrie pas.** Une version antérieure ordonnait par `(date, empreinte)` : la date
    étant au jour près, tous les commits d'une même journée se retrouvaient classés par **hash**,
    donc dans un ordre arbitraire qui n'a rien de chronologique. Sur ce dépôt — 781 commits en
    cinq semaines — le cas est la règle, pas l'exception. `git log` rend déjà l'antichronologie
    exacte, et il la rend de façon déterministe : la garder est à la fois plus juste et plus
    simple.
    """
    if not disponible(racine):
        return {}
    return {
        regle.identifiant: _amendements_du_bloc(racine, regle.fichier, regle.ligne, regle.ligne_fin)
        for regle in regles
    }
