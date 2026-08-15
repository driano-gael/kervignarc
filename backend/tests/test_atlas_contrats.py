"""Les promesses de l'US, écrites depuis le CA — pas depuis le code.

Ces tests sont nés d'un constat de revue : le seul défaut **bloquant** d'E00US018 se trouvait
exactement là où les tests avaient été dérivés de l'implémentation. Trois phrases du CA étaient
mécaniquement testables et n'étaient couvertes par rien :

- « les chemins et symboles cités par les sections *Porté dans le code par* sont vérifiés » — le
  lecteur ignorait les sections écrites en **tableau**, soit un tiers des promesses, et la fiche
  affichait « cette décision ne nomme aucun module » sur les ADR les plus rigoureux du dépôt ;
- « un chemin disparu est **bloquant**, un symbole introuvable est un **signal** » — aucune
  assertion ne le vérifiait, un `verifier()` n'émettant jamais de bloquant passait au vert ;
- « la page affiche, pour chaque ADR, ce qui l'a amendé depuis » — le test du graphe restait vert
  **avec les arêtes inversées**.

D'où ce fichier séparé : il n'exerce que des objets construits à la main, jamais le dépôt réel.
Un test qui lit le dépôt prouve l'état du jour ; celui-ci prouve la règle.
"""

from __future__ import annotations

from pathlib import Path

from atlas import controles as controles_module
from atlas.modele import Decision, Lien, Portage, Sens, Severite, Statut, TypeLien
from atlas.sources import adr


def _decision(
    identifiant: str = "0001",
    *,
    liens: tuple[Lien, ...] = (),
    portage: tuple[Portage, ...] = (),
    date: str = "2026-01-01",
) -> Decision:
    return Decision(
        identifiant=identifiant,
        titre=f"Décision {identifiant}",
        statut=Statut.ACCEPTE,
        statut_brut="Accepté",
        remplace_par="",
        date=date,
        date_brute=date,
        fichier=f"docs/adr/{identifiant}-essai.md",
        liens=liens,
        portage=portage,
        us=(),
        extrait="",
    )


# --- CA : « l'écrit confronté au code » -------------------------------------------------------


SECTION_EN_TABLEAU = """## Porté dans le code par

| Module | Rôle |
|---|---|
| `backend/domain/phase.py` | le contrat, porté par `ContratPhase` |
| `backend/api/v1/poules.py` | l'exposition |
"""

SECTION_EN_PUCES = """## Porté dans le code par

- `backend/domain/phase.py` — `ContratPhase` et sa validation
"""


def test_une_section_de_portage_en_tableau_est_lue() -> None:
    """Le registre a adopté le tableau en cours de route, sans que personne ne le décide."""
    entrees = adr._entrees(SECTION_EN_TABLEAU.split("## Porté dans le code par")[1])

    chemins = [e for e in entrees if "backend/" in e]
    assert len(chemins) == 2
    assert not any("---" in e for e in entrees), "la ligne de séparation n'est pas une entrée"
    assert not any("Rôle" in e for e in entrees), "la ligne d'en-tête n'est pas une entrée"


def test_une_section_de_portage_en_puces_reste_lue() -> None:
    entrees = adr._entrees(SECTION_EN_PUCES.split("## Porté dans le code par")[1])

    assert len(entrees) == 1
    assert "backend/domain/phase.py" in entrees[0]


def test_un_chemin_a_accolades_se_developpe() -> None:
    """`{a,b}.py` est une notation du registre ; la lire telle quelle fabriquerait de faux
    « chemins disparus », donc de faux bloquants."""
    assert adr._developper("backend/domain/{phase,deroule_etape}.py") == [
        "backend/domain/phase.py",
        "backend/domain/deroule_etape.py",
    ]
    assert adr._developper("backend/domain/phase.py") == ["backend/domain/phase.py"]


def test_un_chemin_qui_sort_du_depot_est_ecarte(tmp_path: Path) -> None:
    assert adr._cible_sure(tmp_path, "backend/../../secrets.py") is None
    assert adr._cible_sure(tmp_path, "backend/domain/phase.py") is not None


# --- CA : « un chemin disparu est bloquant, un symbole introuvable est un signal » -------------


def test_un_chemin_disparu_est_bloquant(tmp_path: Path) -> None:
    decision = _decision(portage=(Portage(chemin="backend/parti.py", existe=False),))

    (controle,) = controles_module.verifier(tmp_path, (), (decision,))

    assert controle.severite is Severite.BLOQUANT
    assert controle.code == "portage-inexistant"


def test_un_symbole_introuvable_n_est_qu_un_signal(tmp_path: Path) -> None:
    decision = _decision(
        portage=(
            Portage(
                chemin="backend/present.py",
                existe=True,
                symboles=("Equipe",),
                symboles_absents=("Equipe",),
            ),
        )
    )

    (controle,) = controles_module.verifier(tmp_path, (), (decision,))

    assert controle.severite is Severite.SIGNAL
    assert controle.code == "portage-symbole-absent"


def test_une_promesse_non_verifiable_se_dit_au_lieu_de_se_taire(tmp_path: Path) -> None:
    """Une cible non lisible rendait « aucun symbole absent » — donc s'affichait comme tenue."""
    decision = _decision(
        portage=(
            Portage(chemin="backend/tests/", existe=True, symboles=("podium",), verifiable=False),
        )
    )

    (controle,) = controles_module.verifier(tmp_path, (), (decision,))

    assert controle.severite is Severite.SIGNAL
    assert controle.code == "portage-non-verifiable"


def test_un_portage_tenu_ne_produit_aucun_controle(tmp_path: Path) -> None:
    decision = _decision(
        portage=(Portage(chemin="backend/present.py", existe=True, symboles=("ContratPhase",)),)
    )

    assert controles_module.verifier(tmp_path, (), (decision,)) == ()


# --- CA : « ce qui l'a amendée depuis » -------------------------------------------------------


def test_une_arete_sortante_designe_la_decision_amendee() -> None:
    """A déclare « Amende : B » ⇒ c'est **B** qui est amendé, pas A."""
    amendeur = _decision("0002", liens=(Lien(TypeLien.AMENDE, Sens.SORTANT, "0001", "Amende"),))
    amende = _decision("0001")

    resultat = {d.identifiant: d for d in adr._avec_amendements_entrants([amende, amendeur])}

    assert resultat["0001"].amende_par == ("0002",)
    assert resultat["0002"].amende_par == ()


def test_une_arete_entrante_designe_la_decision_qui_la_porte() -> None:
    """« Complété et partiellement révisé par : B » ⇒ c'est **A** qui est amendé, par B.

    Le seul libellé entrant du registre. Traité comme sortant, il inverserait la chronologie —
    l'atlas raconterait l'histoire à l'envers, et le graphe resterait « vert ».
    """
    porteur = _decision(
        "0001",
        liens=(
            Lien(TypeLien.AMENDE, Sens.ENTRANT, "0002", "Complété et partiellement révisé par"),
        ),
    )
    autre = _decision("0002")

    resultat = {d.identifiant: d for d in adr._avec_amendements_entrants([porteur, autre])}

    assert resultat["0001"].amende_par == ("0002",)
    assert resultat["0002"].amende_par == ()


def test_une_relation_de_voisinage_ne_fait_pas_un_amendement() -> None:
    """`Lie` et `S'appuie sur` relient presque tout : les compter noierait le signal."""
    voisine = _decision("0002", liens=(Lien(TypeLien.VOISIN, Sens.SYMETRIQUE, "0001", "Lie"),))
    autre = _decision("0001")

    resultat = {d.identifiant: d for d in adr._avec_amendements_entrants([autre, voisine])}

    assert resultat["0001"].amende_par == ()
    assert resultat["0002"].amende_par == ()
