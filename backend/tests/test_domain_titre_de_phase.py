"""E16US002 — le **titre** d'une étape de déroulé, saisi à la fiche de phase.

Tests dérivés du **CA** (`stories/E16-retours-maquettes.md` → E16US002, puce « CA — fiche ») :
« *ouvrir une ligne ouvre la fiche de la phase — son **titre** et ses **réglages propres au
type*** », et du questionnaire A07 qui l'a demandé : « *sur chaque ligne du tableau on peut ouvrir
une fiche de la phase, qui reprend son titre et ses réglages* ».

**Pourquoi un titre.** Le CA voisin — « *plusieurs phases de type qualification, ou duel, qui n'ont
pas les mêmes réglages* » — a été livré par E05US024/E05US025 côté moteur. Mais une fois deux
qualifications composables, l'écran les présente identiquement : même `LIBELLE_TYPE`, seul le rang
diffère. Le titre est ce qui rend la capacité **utilisable**, pas seulement possible.

⚠️ **Écrits depuis le CA, avant l'implémentation** (règle 9) — et la formulation compte. Une
première rédaction affirmait « ce fichier a été **committé** avant que `titre` n'existe » : c'était
**faux**, la branche ne portant qu'un seul commit, et un relecteur l'a relevé. Une affirmation de
provenance invérifiable est pire qu'aucune : elle décourage la re-vérification qu'elle prétend
rendre inutile. Ce qui est vérifiable, et ce que la revue a vérifié sur pièces : aucune assertion
ici ne colle à `titre_normalise` ni ne recopie un comportement observé — elles dérivent des puces
« CA — liste » et « CA — fiche » de `stories/E16-retours-maquettes.md`.

Ce que le CA ne dit pas a été tranché ici et **reversé à la fiche** dans le même commit — un CA muet
qu'on complète en silence est un CA périmé pour l'US suivante.
"""

from __future__ import annotations

from dataclasses import replace

from domain.deroule_etape import EtapeDeroule
from domain.format_tournoi import ModelePhase
from domain.phase import TypePhase


def _etape(*, titre: str | None = None, ordre: int = 1) -> EtapeDeroule:
    """Une étape d'élimination directe — le type qui ne demande ni barème ni grain."""
    return EtapeDeroule(
        tournoi_id=1,
        ordre=ordre,
        type=TypePhase.ELIMINATION_DIRECTE,
        titre=titre,
    )


def test_une_etape_porte_le_titre_quon_lui_donne() -> None:
    """CA « fiche » : la fiche *reprend son titre* — encore faut-il que l'étape le porte."""
    assert _etape(titre="Tableau des jeunes").titre == "Tableau des jeunes"


def test_une_etape_sans_titre_reste_valide() -> None:
    """Le titre est **facultatif**, et ce n'est pas un confort : les déroulés déjà composés n'en
    ont aucun. L'exiger aurait rendu invalide, à la première lecture, tout tournoi existant —
    une migration de données là où le CA ne demande qu'un libellé."""
    assert _etape().titre is None


def test_le_titre_est_normalise_espaces_de_bord_retires() -> None:
    """Aligné sur `Tournoi._nom_valide`, qui strippe déjà nom et lieu : deux conventions de
    normalisation pour deux libellés saisis au clavier seraient une incohérence gratuite."""
    assert _etape(titre="  Tableau des jeunes  ").titre == "Tableau des jeunes"


def test_un_titre_vide_vaut_absence_de_titre_et_non_un_refus() -> None:
    """**Tranché ici, le CA est muet.** Effacer le champ est le geste par lequel l'organisateur
    *retire* un titre ; le traiter en erreur lui interdirait de revenir au libellé automatique
    sans supprimer la phase. Un titre blanc n'est donc pas invalide — il est absent."""
    assert _etape(titre="   ").titre is None
    assert _etape(titre="").titre is None


def test_deux_etapes_du_meme_deroule_peuvent_porter_le_meme_titre() -> None:
    """**Tranché ici, le CA est muet.** Le titre est un **libellé**, pas une clé : l'identité
    d'une étape reste son `id` et son rang dans la séquence 1..N (ADR-0045 §3). Imposer l'unicité
    aurait fait échouer la composition sur une gêne d'affichage, et déplacé dans le domaine une
    règle que rien du métier ne réclame."""
    premier = _etape(titre="Qualification", ordre=1)
    second = _etape(titre="Qualification", ordre=2)

    assert premier.titre == second.titre


def test_le_titre_survit_a_la_promotion_en_format() -> None:
    """CA « réutilisable d'une année sur l'autre » : ce qui se range en bibliothèque est le
    **format** (ADR-0060 §5). Un titre perdu à la promotion, c'est le défaut `barrage_jusqu_au`
    d'ADR-0076 rejoué — un champ présent d'un côté de la traversée et absent de l'autre."""
    modele = ModelePhase.d_etape(_etape(titre="Tableau des jeunes"))

    assert modele.titre == "Tableau des jeunes"


def test_le_titre_revient_quand_le_format_est_applique() -> None:
    """L'autre sens de la même traversée : le format rejoué d'une année sur l'autre rend ses
    titres, sinon la brique remonte amputée de ce qui la rendait lisible."""
    modele = ModelePhase(ordre=1, type=TypePhase.ELIMINATION_DIRECTE, titre="Tableau des jeunes")

    assert modele.pour_tournoi(tournoi_id=7).titre == "Tableau des jeunes"


def test_un_modele_de_format_normalise_son_titre_comme_une_etape() -> None:
    """**L'autre porte d'entrée**, et elle était ouverte (correctif de revue, quatre axes).

    La première livraison ne normalisait que dans `EtapeDeroule`. Un titre posté sur un *format*
    (`EtapeDTO.titre` → `ModelePhase`) traversait donc sans strip, était stocké tel quel, et
    resservi avec ses espaces — pendant que le même texte passé par `/tournois/{id}/phases`
    revenait normalisé. **Une saisie, deux valeurs selon l'écran.**

    Le cas `"   "` est le pire des deux : sans normalisation, c'est un titre *non vide* qui masque
    le libellé du type, donc une ligne d'atelier visuellement anonyme — et le même format appliqué
    à un tournoi retombe, lui, sur le type.
    """
    assert ModelePhase(ordre=1, type=TypePhase.ELIMINATION_DIRECTE, titre="  Jeunes  ").titre == (
        "Jeunes"
    )
    assert ModelePhase(ordre=1, type=TypePhase.ELIMINATION_DIRECTE, titre="   ").titre is None


def test_le_titre_survit_a_un_retypage_contrairement_aux_reglages() -> None:
    """CA « fiche », point *(c)* reversé à la fiche : le titre n'appartient à **aucun** type.

    ⚠️ **Ce point de CA n'avait aucun test** (relevé en revue). Il ne tenait qu'à l'absence de garde
    de type sur deux lignes de front — un futur « aligner `titre` sur ses voisins », qui sont tous
    effacés au retypage, aurait supprimé la propriété sans qu'aucune porte ne bronche.

    « Tableau des jeunes » reste juste si la phase devient des poules ; c'est la différence entre un
    **libellé** et un **réglage**.
    """
    tableau = EtapeDeroule(
        tournoi_id=1,
        ordre=1,
        type=TypePhase.ELIMINATION_DIRECTE,
        titre="Tableau des jeunes",
    )

    devenu_poules = replace(tableau, type=TypePhase.POULES)

    assert devenu_poules.titre == "Tableau des jeunes"
