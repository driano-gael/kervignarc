"""Les contradictions entre livrables de suivi — tests écrits depuis le CA d'E00US019.

Quatre fichiers écrits à la main se citent les uns les autres sans que rien ne vérifie qu'ils
concordent. Ces tests fixent, cas par cas, ce que l'atlas doit constater — et surtout **avec quelle
sévérité** : un constat sans ambiguïté bloque, un jugement ou une heuristique s'affiche.

Fixtures littérales, jamais le dépôt réel : un test qui lit `SUIVI-US.md` prouve l'état du jour, pas
la règle. Le dépôt réel est couvert séparément par `test_atlas_corpus.py`.
"""

from __future__ import annotations

from atlas.controles import verifier_avancement
from atlas.modele import Controle, Decision, Severite, Statut
from atlas.sources.backlog import Dette, Epic, UsSpecifiee
from atlas.sources.suivi import Entete, LigneUS, Section


def _section(
    titre: str = "J0 — le socle (2/2)",
    compteur: tuple[int, int] | None = (2, 2),
    lignes: tuple[LigneUS, ...] = (),
) -> Section:
    return Section(titre=titre, compteur_ecrit=compteur, lignes=lignes, a_colonne_seq=True)


def _ligne(identifiant: str, etat: str = "✅", titre: str = "Peu importe") -> LigneUS:
    return LigneUS(identifiant=identifiant, titre=titre, etat=etat, hors_sequence=False)


def _us(identifiant: str, titre: str = "Peu importe") -> UsSpecifiee:
    return UsSpecifiee(identifiant=identifiant, titre=titre, fichier="stories/E00-socle.md")


def _decision(identifiant: str, us: tuple[str, ...] = ()) -> Decision:
    return Decision(
        identifiant=identifiant,
        titre="Une décision",
        statut=Statut.ACCEPTE,
        statut_brut="Accepté",
        remplace_par="",
        date="2026-08-16",
        date_brute="2026-08-16",
        fichier=f"docs/adr/{identifiant}-une-decision.md",
        liens=(),
        portage=(),
        us=us,
        extrait="",
    )


_RIEN = Entete(derniere="", adr_du_resume=())


def _codes(controles: tuple[Controle, ...]) -> list[str]:
    return [c.code for c in controles]


# --- Le compteur de section : recalculé, et tout écart bloque -----------------------------------


def test_compteur_exact_ne_produit_rien() -> None:
    section = _section(compteur=(1, 2), lignes=(_ligne("E00US001"), _ligne("E00US002", "⬜")))
    assert (
        verifier_avancement((section,), (), (), (_us("E00US001"), _us("E00US002")), (), _RIEN) == ()
    )


def test_compteur_divergent_est_bloquant() -> None:
    """Le tracker est le point de reprise : un compteur faux fait repartir sur une base fausse."""
    section = _section(
        titre="J3 — les duels (12/15)", compteur=(12, 15), lignes=(_ligne("E05US001"),)
    )
    trouves = verifier_avancement((section,), (), (), (_us("E05US001"),), (), _RIEN)

    assert _codes(trouves) == ["compteur-divergent"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "12/15" in trouves[0].message and "1/1" in trouves[0].message


def test_section_sans_compteur_ecrit_nest_pas_controlee() -> None:
    section = _section(titre="Ajouts de la démo", compteur=None, lignes=(_ligne("E00US001"),))
    assert verifier_avancement((section,), (), (), (_us("E00US001"),), (), _RIEN) == ()


def test_le_total_annonce_en_tete_est_recalcule() -> None:
    """L'en-tête annonce « N US livrées » : c'est un compteur, et il se trompe autrement.

    Une US **livrée mais jamais insérée dans un jalon** — elle n'existe que dans la file d'attente,
    un tableau en citation qu'aucune section ne compte — gonfle ce total sans faire bouger un seul
    `n/N`. Cas réel du 16/08/2026 : `E05US026` et `E05US028`, livrées, restées dans la file.
    """
    section = _section(compteur=(1, 1), lignes=(_ligne("E00US001"),))
    entete = Entete(derniere="", adr_du_resume=(), livrees=3)
    trouves = verifier_avancement((section,), (), (), (_us("E00US001"),), (), entete)

    assert _codes(trouves) == ["total-annonce-divergent"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "3" in trouves[0].message and "1" in trouves[0].message


def test_le_total_annonce_compte_les_us_distinctes() -> None:
    """Une US listée ✅ dans deux sections est **une** US livrée, pas deux.

    Deux US sont légitimement re-listées dans un lot d'ajouts postérieur : compter les lignes
    ferait dériver le total de deux, et le tracker aurait raison contre l'atlas.
    """
    lignes = (_ligne("E00US001"),)
    sections = (
        _section(titre="J0 (1/1)", compteur=(1, 1), lignes=lignes),
        _section(titre="Ajouts (1/1)", compteur=(1, 1), lignes=lignes),
    )
    entete = Entete(derniere="", adr_du_resume=(), livrees=1)

    assert verifier_avancement(sections, (), (), (_us("E00US001"),), (), entete) == ()


# --- Une US livrée doit être spécifiée ----------------------------------------------------------


def test_us_livree_absente_de_stories_est_bloquante() -> None:
    section = _section(compteur=(1, 1), lignes=(_ligne("E09US042"),))
    trouves = verifier_avancement((section,), (), (), (), (), _RIEN)

    assert _codes(trouves) == ["us-hors-stories"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "E09US042" in trouves[0].sujet


def test_us_non_livree_absente_de_stories_ne_produit_rien() -> None:
    """Une US planifiée mais pas encore spécifiée est un état normal du backlog, pas un défaut.

    Le contrôle ne vaut que sur les ✅ : c'est là que l'absence de spécification est un constat
    sans ambiguïté — on ne peut pas avoir livré ce qui n'a jamais été écrit.
    """
    section = _section(compteur=(0, 1), lignes=(_ligne("E00US030", "🎯"),))
    assert verifier_avancement((section,), (), (), (), (), _RIEN) == ()


def test_us_absorbee_est_hors_decompte_et_hors_controle() -> None:
    section = _section(compteur=(0, 0), lignes=(_ligne("E05US016", "⛔"),))
    assert verifier_avancement((section,), (), (), (), (), _RIEN) == ()


# --- Les epics ----------------------------------------------------------------------------------


def test_dependance_vers_un_epic_inexistant_est_bloquante() -> None:
    epics = (
        Epic(identifiant="04", titre="Saisie", priorite="P1", depend_de=()),
        Epic(identifiant="05", titre="Moteur", priorite="P1", depend_de=("04", "99")),
    )
    trouves = verifier_avancement((), epics, (), (), (), _RIEN)

    assert _codes(trouves) == ["epic-inexistant"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "EPIC-99" in trouves[0].message


def test_dependance_vers_un_epic_existant_ne_produit_rien() -> None:
    epics = (
        Epic(identifiant="04", titre="Saisie", priorite="P1", depend_de=()),
        Epic(identifiant="05", titre="Moteur", priorite="P1", depend_de=("04",)),
    )
    assert verifier_avancement((), epics, (), (), (), _RIEN) == ()


# --- Le registre de dette -----------------------------------------------------------------------


def test_dette_presente_dans_les_deux_tables_est_bloquante() -> None:
    """Une dette résorbée **change de table** : y figurer deux fois, c'est deux vérités opposées."""
    dettes = (
        Dette(
            identifiant="028", ouverte=True, severite="majeur", introduite_par=(), resorption_us=()
        ),
        Dette(identifiant="028", ouverte=False, severite="", introduite_par=(), resorption_us=()),
    )
    trouves = verifier_avancement((), (), dettes, (), (), _RIEN)

    assert _codes(trouves) == ["dette-dans-les-deux-tables"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "DETTE-028" in trouves[0].sujet


def test_us_de_resorption_absente_de_stories_est_un_signal() -> None:
    dettes = (
        Dette(
            identifiant="028",
            ouverte=True,
            severite="majeur",
            introduite_par=(),
            resorption_us=("E09US042",),
        ),
    )
    trouves = verifier_avancement((), (), dettes, (), (), _RIEN)

    assert _codes(trouves) == ["resorption-hors-stories"]
    assert trouves[0].severite is Severite.SIGNAL


# --- Les titres ---------------------------------------------------------------------------------


def test_titre_divergent_entre_tracker_et_stories_est_un_signal() -> None:
    section = _section(compteur=(1, 1), lignes=(_ligne("E00US001", titre="Le socle CI"),))
    trouves = verifier_avancement(
        (section,), (), (), (_us("E00US001", "La CI bloquante"),), (), _RIEN
    )

    assert _codes(trouves) == ["titre-divergent"]
    assert trouves[0].severite is Severite.SIGNAL


def test_titre_reformule_ne_produit_rien() -> None:
    """Le même travail dit deux fois : c'est le cas ordinaire, il ne doit pas faire de bruit.

    Cas réel du dépôt (E00US009). Un contrôle qui signalerait cette paire signalerait un cinquième
    des US livrées, et personne ne lirait plus la page.
    """
    section = _section(
        compteur=(1, 1), lignes=(_ligne("E00US009", titre="Repository + endpoint bout-en-bout"),)
    )
    us = (_us("E00US009", "Repository + endpoint de bout en bout"),)
    assert verifier_avancement((section,), (), (), us, (), _RIEN) == ()


def test_titre_identique_aux_accents_et_a_la_casse_pres_ne_produit_rien() -> None:
    section = _section(
        compteur=(1, 1), lignes=(_ligne("E00US001", titre="L'ATLAS : l'avancement"),)
    )
    us = (_us("E00US001", "L'atlas : l'avancement"),)
    assert verifier_avancement((section,), (), (), us, (), _RIEN) == ()


# --- L'en-tête du tracker -----------------------------------------------------------------------


def test_derniere_us_dont_le_resume_cite_un_adr_qui_lignore_est_un_signal() -> None:
    """Le défaut réel trouvé sur `main` le 16/08 : en-tête « E05US026 », résumé sur E05US028."""
    entete = Entete(derniere="E05US026", adr_du_resume=("0084",))
    trouves = verifier_avancement((), (), (), (), (_decision("0084", us=("E05US028",)),), entete)

    assert _codes(trouves) == ["derniere-us-orpheline"]
    assert trouves[0].severite is Severite.SIGNAL
    assert "ADR-0084" in trouves[0].message


def test_derniere_us_citee_par_l_adr_de_son_resume_ne_produit_rien() -> None:
    entete = Entete(derniere="E00US018", adr_du_resume=("0086",))
    assert verifier_avancement((), (), (), (), (_decision("0086", us=("E00US018",)),), entete) == ()


def test_resume_sans_adr_ne_produit_rien() -> None:
    """Le contrôle a besoin d'un ADR pour recouper : sans lui, il n'a rien à dire — et se tait."""
    entete = Entete(derniere="E02US010", adr_du_resume=())
    assert verifier_avancement((), (), (), (), (_decision("0086", us=("E00US018",)),), entete) == ()
