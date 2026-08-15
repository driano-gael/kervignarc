"""Sérialisation des données de l'atlas — déterministe, sinon rien.

La sortie est **commitée puis comparée en CI**. Le moindre indéterminisme (horodatage, ordre de
parcours d'un `set`, chemin absolu, fin de ligne selon la plateforme) ferait clignoter la porte,
et une porte qui clignote est désactivée sous quinze jours — on perdrait alors aussi les contrôles
qui, eux, étaient justes. D'où les partis pris ci-dessous, tous non négociables :

- `sort_keys=True` et listes triées à la construction ;
- `indent=1` : un jeton par ligne, donc un **diff à la ligne** plutôt qu'un pavé de 400 Ko sur une
  seule ligne — c'est ce qui rend le choix « données commitées » vivable en revue ;
- **aucun horodatage, aucune empreinte de commit du dépôt, aucun chemin absolu** ;
- `newline="\\n"` et `encoding="utf-8"` explicites — poste Windows, CI Linux, dépôt en LF.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

DOSSIER = ("atlas", "donnees")

# Comparées à l'octet près : ce sont des fonctions pures de l'arbre de travail.
CLES_STRICTES = ("reglement", "decisions", "controles", "corpus")
# Comparée avec tolérance d'ajout : dérivée de git, donc en retard d'un commit au pre-commit.
CLE_TOLERANTE = "historique"

_PROLOGUE = (
    "/* GÉNÉRÉ par `cd backend && python -m atlas` — ne pas éditer à la main.\n"
    "   Toute modification sera écrasée à la régénération et rejetée par la CI. */\n"
    "window.ATLAS = window.ATLAS || {};\n"
)


def _brut(valeur: Any) -> Any:
    if dataclasses.is_dataclass(valeur) and not isinstance(valeur, type):
        return dataclasses.asdict(valeur)
    return valeur


def serialiser(cle: str, charge: Any) -> str:
    """Le contenu d'un fichier de données, prêt à écrire.

    Sortie en `.js` et non en `.json` : sur `file://`, `fetch()` est bloqué par la politique
    d'origine. Déclarer `window.ATLAS.<clé>` permet d'ouvrir le site d'un simple double-clic,
    sans serveur — c'est la seule façon d'honorer « je navigue librement au navigateur ».
    """
    corps = json.dumps(charge, ensure_ascii=False, indent=1, sort_keys=True, default=_brut)
    # `json.dumps` n'échappe pas `<` : un ADR contenant `</script>` fermerait la balise qui porte
    # ces données. Les séparateurs de ligne U+2028/U+2029 sont, eux, illégaux dans un littéral JS.
    corps = corps.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"{_PROLOGUE}window.ATLAS.{cle} = {corps};\n"


def _chemin(racine: Path, cle: str) -> Path:
    return racine.joinpath(*DOSSIER, f"{cle}.js")


def ecrire(racine: Path, fichiers: dict[str, str]) -> None:
    dossier = racine.joinpath(*DOSSIER)
    dossier.mkdir(parents=True, exist_ok=True)
    for cle, contenu in sorted(fichiers.items()):
        _chemin(racine, cle).write_text(contenu, encoding="utf-8", newline="\n")


def _charge_utile(contenu: str, cle: str) -> Any:
    marqueur = f"window.ATLAS.{cle} = "
    debut = contenu.find(marqueur)
    if debut < 0:
        return None
    return json.loads(contenu[debut + len(marqueur) :].rstrip().removesuffix(";"))


def ecarts(racine: Path, fichiers: dict[str, str]) -> list[str]:
    """Ce qui sépare le dépôt de ce que le générateur produirait aujourd'hui.

    Les clés strictes se comparent à l'octet près. `historique` se compare par **tolérance
    d'ajout** : la régénération peut contenir des entrées de plus — au moment du hook pre-commit,
    le commit en cours n'existe pas encore, alors que la CI le verra. Elle ne peut en revanche pas
    en **perdre** : une entrée commitée qui disparaît signale que les bornes d'une règle ont bougé,
    et mérite une régénération.
    """
    problemes: list[str] = []
    for cle, attendu in sorted(fichiers.items()):
        cible = _chemin(racine, cle)
        if not cible.is_file():
            problemes.append(f"{cle}.js : absent — l'atlas n'a jamais été généré.")
            continue
        present = cible.read_text(encoding="utf-8")
        if cle == CLE_TOLERANTE:
            problemes.extend(_ecarts_historique(present, attendu))
        elif present != attendu:
            problemes.append(
                f"{cle}.js : périmé — le contenu diffère de ce que les sources donnent."
            )
    return problemes


def _ecarts_historique(present: str, attendu: str) -> list[str]:
    commite = _charge_utile(present, CLE_TOLERANTE)
    frais = _charge_utile(attendu, CLE_TOLERANTE)
    if not isinstance(commite, dict) or not isinstance(frais, dict):
        return [f"{CLE_TOLERANTE}.js : illisible — régénère."]
    if not frais:
        return []  # git indisponible : on ne peut rien affirmer, donc on n'affirme rien
    perdues = [
        f"{CLE_TOLERANTE}.js : la règle « {identifiant} » a perdu des entrées d'historique"
        for identifiant, entrees in sorted(commite.items())
        if not _inclus(entrees, frais.get(identifiant, []))
    ]
    return perdues


def _inclus(anciennes: Any, nouvelles: Any) -> bool:
    if not isinstance(anciennes, list) or not isinstance(nouvelles, list):
        return False
    references = {e.get("reference") for e in nouvelles if isinstance(e, dict)}
    return all(e.get("reference") in references for e in anciennes if isinstance(e, dict))
