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


def _entete(
    livrees: int = 0,
    derniere: str = "",
    adr: tuple[str, ...] = (),
    recapitulatif: tuple[tuple[str, int, int], ...] = (),
) -> Entete:
    """Un en-tête de tracker. `livrees` n'est **jamais** optionnel — cf. `lire_entete_du_texte`."""
    return Entete(
        derniere=derniere, adr_du_resume=adr, livrees=livrees, recapitulatif=recapitulatif
    )


_RIEN = _entete()


def _codes(controles: tuple[Controle, ...]) -> list[str]:
    return [c.code for c in controles]


# --- Le compteur de section : recalculé, et tout écart bloque -----------------------------------


def test_compteur_exact_ne_produit_rien() -> None:
    section = _section(compteur=(1, 2), lignes=(_ligne("E00US001"), _ligne("E00US002", "⬜")))
    us = (_us("E00US001"), _us("E00US002"))
    assert verifier_avancement((section,), (), (), us, (), _entete(1)) == ()


def test_compteur_divergent_est_bloquant() -> None:
    """Le tracker est le point de reprise : un compteur faux fait repartir sur une base fausse."""
    section = _section(
        titre="J3 — les duels (12/15)", compteur=(12, 15), lignes=(_ligne("E05US001"),)
    )
    trouves = verifier_avancement((section,), (), (), (_us("E05US001"),), (), _entete(1))

    assert _codes(trouves) == ["compteur-divergent"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "12/15" in trouves[0].message and "1/1" in trouves[0].message


def test_section_sans_compteur_ecrit_nest_pas_controlee() -> None:
    section = _section(titre="Ajouts de la démo", compteur=None, lignes=(_ligne("E00US001"),))
    assert verifier_avancement((section,), (), (), (_us("E00US001"),), (), _entete(1)) == ()


def test_le_total_annonce_en_tete_est_recalcule() -> None:
    """L'en-tête annonce « N US livrées » : c'est un compteur, et il se trompe autrement.

    Une US **livrée mais jamais insérée dans un jalon** — elle n'existe que dans la file d'attente,
    un tableau en citation qu'aucune section ne compte — gonfle ce total sans faire bouger un seul
    `n/N`. Cas réel du 16/08/2026 : `E05US026` et `E05US028`, livrées, restées dans la file.
    """
    section = _section(compteur=(1, 1), lignes=(_ligne("E00US001"),))
    entete = _entete(3)
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
    entete = _entete(1)

    assert verifier_avancement(sections, (), (), (_us("E00US001"),), (), entete) == ()


# --- Une US livrée doit être spécifiée ----------------------------------------------------------


def test_us_livree_absente_de_stories_est_bloquante() -> None:
    section = _section(compteur=(1, 1), lignes=(_ligne("E09US042"),))
    trouves = verifier_avancement((section,), (), (), (), (), _entete(1))

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

    # Les deux constats sont voulus : l'identifiant est à la fois **dupliqué** et **des deux
    # côtés du registre**. Deux défauts distincts ; le second ne subsume pas le premier.
    assert _codes(trouves) == ["dette-dans-les-deux-tables", "dette-numero-en-double"]
    assert all(c.severite is Severite.BLOQUANT for c in trouves)
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


def test_un_meme_numero_de_dette_inscrit_deux_fois_est_bloquant() -> None:
    """Le défaut **réellement survenu** : deux `DETTE-065` dans la même table, sur `main`.

    Deux agents ont pris le même numéro libre et, chacun l'ayant écrit loin de l'autre **pour
    éviter un conflit**, git les a fusionnées sans un mot. `dette-dans-les-deux-tables` ne pouvait
    pas le voir : les deux lignes étaient du même côté du registre.
    """
    ligne = Dette(
        identifiant="065", ouverte=True, severite="mineur", introduite_par=(), resorption_us=()
    )
    trouves = verifier_avancement((), (), (ligne, ligne), (), (), _RIEN)

    assert _codes(trouves) == ["dette-numero-en-double"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "DETTE-065" in trouves[0].sujet


def test_trois_dettes_reclamant_la_meme_us_absente_font_trois_signaux() -> None:
    """Trois faits distincts, pas un : le sujet du contrôle est la **dette**, pas l'US."""
    dettes = tuple(
        Dette(
            identifiant=numero,
            ouverte=True,
            severite="majeur",
            introduite_par=(),
            resorption_us=("E09US042",),
        )
        for numero in ("001", "002", "003")
    )
    trouves = verifier_avancement((), (), dettes, (), (), _RIEN)

    assert _codes(trouves) == ["resorption-hors-stories"] * 3
    assert [c.sujet for c in trouves] == ["DETTE-001", "DETTE-002", "DETTE-003"]


# --- Les cycles d'epics -------------------------------------------------------------------------


def test_un_cycle_entre_epics_est_bloquant() -> None:
    """Le seul défaut du tableau des epics que le **schéma** ne peut pas montrer.

    Sur un cycle, la réduction transitive efface toutes les arêtes — chacune est impliquée par le
    chemin qui passe par les autres. Le graphe faux devient la seule chose invisible ; c'est donc
    au contrôle de parler, pas au dessin.
    """
    epics = (
        Epic(identifiant="01", titre="Un", priorite="P1", depend_de=("02",)),
        Epic(identifiant="02", titre="Deux", priorite="P1", depend_de=("01",)),
    )
    trouves = verifier_avancement((), epics, (), (), (), _RIEN)

    assert _codes(trouves) == ["cycle-entre-epics"] * 2
    assert all(c.severite is Severite.BLOQUANT for c in trouves)


def test_un_cycle_indirect_est_vu() -> None:
    epics = (
        Epic(identifiant="01", titre="Un", priorite="P1", depend_de=("03",)),
        Epic(identifiant="02", titre="Deux", priorite="P1", depend_de=("01",)),
        Epic(identifiant="03", titre="Trois", priorite="P1", depend_de=("02",)),
    )
    trouves = verifier_avancement((), epics, (), (), (), _RIEN)

    assert _codes(trouves) == ["cycle-entre-epics"] * 3


def test_un_losange_n_est_pas_un_cycle() -> None:
    """Deux chemins vers le même ancêtre : le cas le plus banal d'un backlog, jamais un défaut."""
    epics = (
        Epic(identifiant="00", titre="Socle", priorite="P0", depend_de=()),
        Epic(identifiant="01", titre="Un", priorite="P1", depend_de=("00",)),
        Epic(identifiant="02", titre="Deux", priorite="P1", depend_de=("00",)),
        Epic(identifiant="03", titre="Trois", priorite="P1", depend_de=("01", "02")),
    )
    assert verifier_avancement((), epics, (), (), (), _RIEN) == ()


# --- Les états contradictoires ------------------------------------------------------------------


def test_deux_etats_pour_une_meme_us_est_un_signal() -> None:
    """Cas réel : `E05US023` est ✅ en J3 et ⬜ dans « Résorptions de dette planifiées ».

    **Signal et non bloquant** : la colonne « État » ne dit pas partout la même chose — là-bas elle
    dit si la résorption est faite, pas si l'US est livrée. Trancher mécaniquement entre les deux
    lectures reviendrait à arbitrer un sens que le tracker n'a jamais fixé.
    """
    sections = (
        _section(titre="J3 (1/1)", compteur=(1, 1), lignes=(_ligne("E05US023"),)),
        _section(titre="Résorptions", compteur=None, lignes=(_ligne("E05US023", "⬜"),)),
    )
    trouves = verifier_avancement(sections, (), (), (_us("E05US023"),), (), _entete(1))

    assert _codes(trouves) == ["etat-contradictoire"]
    assert trouves[0].severite is Severite.SIGNAL
    assert "J3 (1/1)" in trouves[0].message and "Résorptions" in trouves[0].message


def test_un_meme_etat_dans_deux_sections_ne_produit_rien() -> None:
    lignes = (_ligne("E01US017"),)
    sections = (
        _section(titre="J1 (1/1)", compteur=(1, 1), lignes=lignes),
        _section(titre="Ajouts (1/1)", compteur=(1, 1), lignes=lignes),
    )
    assert verifier_avancement(sections, (), (), (_us("E01US017"),), (), _entete(1)) == ()


# --- Le rappel de la Légende --------------------------------------------------------------------


def _jalon() -> Section:
    return _section(
        titre="J3 — les duels (1/2)",
        compteur=(1, 2),
        lignes=(_ligne("E05US001"), _ligne("E05US002", "⬜")),
    )


def test_le_recapitulatif_de_la_legende_est_recalcule() -> None:
    """« C'est cette règle qui donne J0 12/12, J1 46/46, … » — 5ᵉ écriture des mêmes nombres.

    Elle est éditée à la main dans le fichier même qui édicte la règle de comptage, et se périme
    exactement comme les en-têtes de section qu'elle récapitule.
    """
    entete = _entete(1, recapitulatif=(("J3", 9, 9),))
    trouves = verifier_avancement((_jalon(),), (), (), (_us("E05US001"),), (), entete)

    assert _codes(trouves) == ["recapitulatif-divergent"]
    assert trouves[0].severite is Severite.BLOQUANT
    assert "9/9" in trouves[0].message and "1/2" in trouves[0].message


def test_un_recapitulatif_exact_ne_produit_rien() -> None:
    entete = _entete(1, recapitulatif=(("J3", 1, 2),))

    assert verifier_avancement((_jalon(),), (), (), (_us("E05US001"),), (), entete) == ()


# --- L'en-tête du tracker -----------------------------------------------------------------------


def test_derniere_us_dont_le_resume_cite_un_adr_qui_lignore_est_un_signal() -> None:
    """Le défaut réel trouvé sur `main` le 16/08 : en-tête « E05US026 », résumé sur E05US028."""
    entete = _entete(derniere="E05US026", adr=("0084",))
    trouves = verifier_avancement((), (), (), (), (_decision("0084", us=("E05US028",)),), entete)

    assert _codes(trouves) == ["derniere-us-orpheline"]
    assert trouves[0].severite is Severite.SIGNAL
    assert "ADR-0084" in trouves[0].message


def test_derniere_us_citee_par_l_adr_de_son_resume_ne_produit_rien() -> None:
    entete = _entete(derniere="E00US018", adr=("0086",))
    assert verifier_avancement((), (), (), (), (_decision("0086", us=("E00US018",)),), entete) == ()


def test_resume_sans_adr_ne_produit_rien() -> None:
    """Le contrôle a besoin d'un ADR pour recouper : sans lui, il n'a rien à dire — et se tait."""
    entete = _entete(derniere="E02US010")
    assert verifier_avancement((), (), (), (), (_decision("0086", us=("E00US018",)),), entete) == ()
