"""Les garanties d'ADR-0013 décision 8, éprouvées au lieu d'être déclarées.

L'amendement du 16/08/2026 vend deux propriétés comme des garanties : les cinq relecteurs de
`/revue-us` tournent sur le **modèle fort** (`model: opus`, épinglé au lieu d'être hérité de la
session), et ils **ne peuvent pas écrire** (ni `Edit` ni `Write` dans `tools:`). Rien ne les
vérifiait : une édition future qui rétrograde un axe en `sonnet` dégraderait la barrière qualité en
silence — et le diff qui la porte serait relu par l'axe dégradé.

C'est le mode de panne que décrit `test_atlas_porte.py` : un correctif livré sans rien qui prouve
qu'il rougit. Le précédent du projet est `test_domain_isolation.py`, qui transforme une convention
d'architecture en preuve machine ; ces tests font la même chose pour la conduite de la revue.

Le troisième test aurait attrapé, seul, le bloquant relevé en revue sur ce lot même : `npm ci`
était dans la *denylist* du dépôt alors que la porte devait l'exécuter.

Stdlib pure, comme le générateur d'atlas (règle 11, ADR-0086) : un frontmatter YAML minimal se lit
au `re`, et faire entrer PyYAML au dépôt pour cinq en-têtes serait une lib « plaisir ».
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
AGENTS = RACINE / ".claude" / "agents"
COMMANDE = RACINE / ".claude" / "commands" / "revue-us.md"
REGLAGES = RACINE / ".claude" / "settings.json"

AXES = ("revue-axe-a", "revue-axe-b", "revue-axe-c1", "revue-axe-c2", "revue-axe-d")

# Le plancher de sécurité, dupliqué à dessein dans les cinq grilles (ADR-0013 décision 4 : « la
# seule règle partagée par tous les axes »). On n'y teste pas la prose entière — elle diverge
# légitimement d'un axe à l'autre — mais les vecteurs dont l'absence serait silencieuse.
VECTEURS_SECURITE = (
    "exiger_admin",
    "localStorage",
    "dangerouslySetInnerHTML",
    "import.meta.env",
)


def _frontmatter(fichier: Path) -> dict[str, str]:
    """Extrait le frontmatter d'un `.md` : le bloc entre les deux premières lignes `---`.

    Volontairement naïf — un frontmatter d'agent est une poignée de paires `clé: valeur` sur une
    ligne. Une valeur entre guillemets est déquotée ; le reste est pris tel quel.
    """
    texte = fichier.read_text(encoding="utf-8")
    bloc = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", texte, re.DOTALL)
    assert bloc is not None, f"{fichier.name} : frontmatter absent ou mal délimité"
    champs: dict[str, str] = {}
    for ligne in bloc.group(1).splitlines():
        paire = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", ligne)
        if paire:
            champs[paire.group(1)] = paire.group(2).strip().strip('"').strip("'")
    return champs


@pytest.mark.parametrize("axe", AXES)
def test_un_relecteur_garde_le_modele_fort_et_ne_peut_pas_ecrire(axe: str) -> None:
    """ADR-0013 décision 8 — le premier garde-fou de la revue est son propre modèle.

    « Optimiser une barrière qualité, c'est la supprimer » (options écartées d'ADR-0013). Ce test
    est ce qui empêche cette phrase de rester une intention.
    """
    fichier = AGENTS / f"{axe}.md"
    assert fichier.exists(), f"{axe} : grille disparue — la revue tournerait sans cet axe"

    champs = _frontmatter(fichier)
    assert champs.get("name") == axe, f"{axe} : `name` ne correspond pas au nom de fichier"
    assert champs.get("model") == "opus", (
        f"{axe} : `model` vaut {champs.get('model')!r} au lieu de `opus`. Un relecteur qui hérite "
        "du modèle de session dégrade la barrière qualité sans le dire."
    )

    outils = {o.strip() for o in champs.get("tools", "").split(",")}
    interdits = outils & {"Edit", "Write", "NotebookEdit"}
    assert not interdits, f"{axe} : un relecteur ne modifie rien, or il dispose de {interdits}"


@pytest.mark.parametrize("axe", AXES)
def test_un_relecteur_porte_le_plancher_de_securite(axe: str) -> None:
    """ADR-0013 décision 4 — le seul doublon voulu du dispositif.

    La règle a vécu un temps dans le seul préambule, que l'agent auteur retranscrit à la main : elle
    y a été transmise **amputée** dès la première passe. Sa perte ne produit aucun symptôme — un axe
    qui ne cherche pas un secret en dur rend le même rapport qu'un axe qui n'en trouve pas.
    """
    texte = (AGENTS / f"{axe}.md").read_text(encoding="utf-8")
    manquants = [v for v in VECTEURS_SECURITE if v not in texte]
    assert not manquants, (
        f"{axe} : plancher de sécurité incomplet, vecteurs absents : {manquants}. "
        "Cette règle est dupliquée à dessein dans les cinq grilles (ADR-0013 décision 4)."
    )


def test_tout_agent_cite_par_la_commande_existe() -> None:
    """Un agent cité mais introuvable rend l'axe injoignable — sans erreur visible à la lecture."""
    cites = set(re.findall(r"`(revue-axe-[a-z0-9]+|porte-mecanique)`", COMMANDE.read_text("utf-8")))
    assert cites, "aucun agent cité dans /revue-us : la commande n'orchestre plus rien"

    for nom in sorted(cites):
        fichier = AGENTS / f"{nom}.md"
        assert fichier.exists(), f"/revue-us cite `{nom}`, mais {fichier} n'existe pas"
        assert (
            _frontmatter(fichier).get("name") == nom
        ), f"{fichier.name} : le champ `name` ne vaut pas `{nom}` — l'agent serait injoignable"


def test_la_porte_ne_prescrit_aucune_commande_refusee_par_le_depot() -> None:
    """Le garde-fou qui manquait : une porte qu'on n'a pas le droit d'exécuter.

    `porte-mecanique` prescrit des commandes shell ; `.claude/settings.json` est versionné et peut
    en refuser. Une commande refusée ne produit **aucun** code de sortie : elle tombe en « non
    exécuté », et sans ce test rien ne signalait que la porte tournait amputée.
    """
    reglages = json.loads(REGLAGES.read_text(encoding="utf-8"))
    refuses = {
        entree[len("Bash(") : -len(":*)")]
        for entree in reglages["permissions"]["deny"]
        if entree.startswith("Bash(") and entree.endswith(":*)")
    }

    texte = (AGENTS / "porte-mecanique.md").read_text(encoding="utf-8")
    prescrites = set(re.findall(r"`(npm [a-z]+|pytest|mypy|ruff [a-z]+|pip-audit)`", texte))

    collisions = {c for c in prescrites for r in refuses if c == r or c.startswith(f"{r} ")}
    assert not collisions, (
        f"la porte prescrit {sorted(collisions)}, que .claude/settings.json refuse. "
        "Soit la permission s'ouvre, soit l'omission se déclare dans porte-mecanique.md."
    )
