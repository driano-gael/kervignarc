"""La vue assemblée — `avancement.construire`, qui rapproche les quatre sources.

Elle n'était couverte que par la comparaison octet de la CI : une régression y serait apparue sous
la forme de quelques centaines de `"comptee": true → false` noyés dans un fichier généré de près de
5 000 lignes. Filet réel, mais illisible — donc pas un test.
"""

from __future__ import annotations

from typing import Any

from atlas import avancement
from atlas.modele import Decision, Statut
from atlas.sources.backlog import Dette, Epic, UsSpecifiee
from atlas.sources.suivi import Entete, LigneUS, Section


def _ligne(
    identifiant: str, etat: str = "✅", titre: str = "Un titre", seq: bool = True
) -> LigneUS:
    return LigneUS(identifiant=identifiant, titre=titre, etat=etat, hors_sequence=not seq)


def _section(titre: str, lignes: tuple[LigneUS, ...], compteur: tuple[int, int] | None) -> Section:
    return Section(titre=titre, compteur_ecrit=compteur, lignes=lignes, a_colonne_seq=True)


def _entete() -> Entete:
    return Entete(derniere="E09US001", adr_du_resume=("0086",), livrees=1)


def _construire(
    sections: tuple[Section, ...],
    epics: tuple[Epic, ...] = (),
    dettes: tuple[Dette, ...] = (),
    us: tuple[UsSpecifiee, ...] = (),
    decisions: tuple[Decision, ...] = (),
) -> dict[str, Any]:
    return avancement.construire(sections, epics, dettes, us, decisions, _entete())


def _fiches(rendu: dict[str, Any]) -> list[dict[str, Any]]:
    fiches: list[dict[str, Any]] = rendu["fiches"]
    return fiches


def test_le_drapeau_hors_decompte_suit_la_regle_de_comptage() -> None:
    """C'est lui qui affiche « hors décompte » : il ne peut pas diverger du compteur.

    Il se déduisait de l'**identité mémoire** des objets rendus par `comptees` — correct, mais
    faux en silence le jour où cette propriété rendrait des copies. Il passe désormais par le
    prédicat, qui est la seule définition de la règle.
    """
    section = _section(
        "J9 (1/2)",
        (_ligne("E09US001"), _ligne("E09US002", "⬜"), _ligne("E09US003", "⛔")),
        (1, 2),
    )
    rendu = _construire((section,))
    sections: list[dict[str, Any]] = rendu["sections"]
    lignes = sections[0]["lignes"]

    assert [ligne["comptee"] for ligne in lignes] == [True, True, False]
    assert sections[0]["calcule"] == [1, 2]


def test_le_titre_de_la_fiche_est_celui_que_le_controle_compare() -> None:
    """Cas réel `E00US015` : la fiche montrait le libellé d'une ligne **hors décompte**.

    Le titre affiché n'était donc pas celui que le contrôle de concordance regardait — sur une
    page dont le sujet est précisément que les libellés concordent.
    """
    sections = (
        _section("J3 (0/0)", (_ligne("E00US015", titre="Libellé du jalon", seq=False),), (0, 0)),
        _section("Ajouts (1/1)", (_ligne("E00US015", titre="Libellé d'origine"),), (1, 1)),
    )
    (fiche,) = _fiches(_construire(sections))

    assert fiche["titre"] == "Libellé d'origine"
    assert fiche["sections"] == ["J3 (0/0)", "Ajouts (1/1)"]


def test_l_etat_le_plus_avance_gagne_entre_deux_sections() -> None:
    sections = (
        _section("J1 (0/1)", (_ligne("E01US017", "⬜"),), (0, 1)),
        _section("Ajouts (1/1)", (_ligne("E01US017"),), (1, 1)),
    )
    (fiche,) = _fiches(_construire(sections))

    assert fiche["etat"] == "✅"


def test_le_resume_ne_compte_ni_les_absorbees_ni_les_doublons() -> None:
    """Les nombres de la page sont calculés **ici**, par la même règle que les contrôles.

    Les recalculer en JavaScript en aurait fait une troisième écriture — sur la page dont le sujet
    est que les compteurs ne se contredisent pas.
    """
    lignes = (_ligne("E09US001"),)
    sections = (
        _section("J9 (1/1)", lignes, (1, 1)),
        _section(
            "Ajouts (1/2)",
            (*lignes, _ligne("E09US009", "⛔"), _ligne("E09US010", "⬜")),
            (1, 2),
        ),
    )

    assert _construire(sections)["resume"] == {"livrees": 1, "vivantes": 2}


def test_la_fiche_relie_les_quatre_sources() -> None:
    """Le CA : « une fiche par US relie ce que les quatre sources en disent »."""
    section = _section("J9 (1/1)", (_ligne("E09US001"),), (1, 1))
    rendu = _construire(
        (section,),
        epics=(Epic(identifiant="09", titre="Exports", priorite="P2", depend_de=()),),
        us=(UsSpecifiee(identifiant="E09US001", titre="Le vrai titre", fichier="stories/E09.md"),),
        dettes=(
            Dette(
                identifiant="042",
                ouverte=True,
                severite="mineur",
                introduite_par=("E09US001",),
                resorption_us=(),
            ),
        ),
        decisions=(
            Decision(
                identifiant="0086",
                titre="Une décision",
                statut=Statut.ACCEPTE,
                statut_brut="Accepté",
                remplace_par="",
                date="2026-08-16",
                date_brute="2026-08-16",
                fichier="docs/adr/0086.md",
                liens=(),
                portage=(),
                us=("E09US001",),
                extrait="",
            ),
        ),
    )
    (fiche,) = _fiches(rendu)

    assert fiche["epic"] == "09" and fiche["epic_titre"] == "Exports"
    assert fiche["story"] == "stories/E09.md" and fiche["titre_story"] == "Le vrai titre"
    assert fiche["adr"] == ["0086"]
    assert fiche["dettes_introduites"] == ["042"]


def test_aucune_cle_interne_ne_fuit_dans_la_sortie() -> None:
    """La sortie est comparée à l'octet par la CI et lue par le site : c'est un contrat."""
    section = _section("J9 (1/1)", (_ligne("E09US001"),), (1, 1))
    (fiche,) = _fiches(_construire((section,)))

    assert "titre_retenu" not in fiche
