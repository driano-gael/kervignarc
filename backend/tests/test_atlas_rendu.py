"""Propriétés de la sortie générée — déterminisme, échappement, porte de fraîcheur.

Ces tests protègent le compromis « données commitées » : sans eux, la sortie se mettrait à varier
d'une génération à l'autre, la CI rougirait sans raison lisible, et la porte finirait désactivée.
"""

from __future__ import annotations

import re
from pathlib import Path

from atlas import rendu
from atlas.__main__ import construire

RACINE = Path(__file__).resolve().parents[2]

# Écrits par point de code : ces caractères sont invisibles dans un éditeur, et un littéral collé
# tel quel se laisse « corriger » en silence par un outil de formatage.
SEPARATEUR_DE_LIGNE_JS = chr(0x2028)
SEPARATEUR_DE_PARAGRAPHE_JS = chr(0x2029)


def _charge_rendue(valeur: object) -> str:
    return rendu.serialiser("essai", valeur).split("window.ATLAS.essai = ", 1)[1]


def test_deux_generations_donnent_des_octets_identiques() -> None:
    """Le déterminisme n'est pas une élégance : c'est ce qui empêche la porte de clignoter."""
    assert construire(RACINE) == construire(RACINE)


def test_la_sortie_ne_porte_ni_horodatage_ni_chemin_absolu() -> None:
    """Un horodatage produirait un diff à chaque régénération, donc du bruit à chaque US."""
    suspects = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:|[A-Z]:\\\\|/home/|/Users/")

    for cle, contenu in construire(RACINE).items():
        assert not suspects.search(contenu), f"{cle}.js porte un horodatage ou un chemin absolu"


def test_aucun_chevron_brut_ne_survit_dans_la_charge() -> None:
    """Un ADR contenant une balise fermante casserait la balise qui porte ces données.

    `json.dumps` n'échappe pas `<` : sans post-traitement, le site se casserait en silence le jour
    où quelqu'un cite une balise dans un titre d'ADR — et le registre en cite déjà.
    """
    charge = _charge_rendue({"titre": "une balise </script> au milieu du texte"})

    assert "<" not in charge


def test_aucun_separateur_de_ligne_javascript_ne_survit() -> None:
    """U+2028 et U+2029 terminent une ligne pour JavaScript : illégaux dans un littéral."""
    charge = _charge_rendue(
        {"a": f"avant{SEPARATEUR_DE_LIGNE_JS}après", "b": f"x{SEPARATEUR_DE_PARAGRAPHE_JS}y"}
    )

    assert SEPARATEUR_DE_LIGNE_JS not in charge
    assert SEPARATEUR_DE_PARAGRAPHE_JS not in charge


def test_l_echappement_ne_perd_rien() -> None:
    """La contrepartie du test précédent : échapper ne doit pas altérer la donnée.

    C'est la propriété qui compte vraiment — vérifier l'orthographe exacte de l'échappement
    figerait un détail d'implémentation, alors que la fidélité de l'aller-retour est ce dont le
    site dépend réellement.
    """
    original = {
        "balise": "</script>",
        "separateurs": f"{SEPARATEUR_DE_LIGNE_JS}{SEPARATEUR_DE_PARAGRAPHE_JS}",
        "accents": "portée sportive — déjà amendé",
        "imbrique": {"liste": [1, 2, "trois"]},
    }

    assert rendu._charge_utile(rendu.serialiser("essai", original), "essai") == original


def test_la_porte_signale_des_donnees_absentes(tmp_path: Path) -> None:
    problemes = rendu.ecarts(tmp_path, {"reglement": rendu.serialiser("reglement", {"x": 1})})

    assert problemes and "absent" in problemes[0]


def test_la_porte_signale_des_donnees_perimees(tmp_path: Path) -> None:
    rendu.ecrire(tmp_path, {"reglement": rendu.serialiser("reglement", {"x": 1})})

    problemes = rendu.ecarts(tmp_path, {"reglement": rendu.serialiser("reglement", {"x": 2})})

    assert problemes and "périmé" in problemes[0]


def test_la_porte_est_verte_sur_des_donnees_a_jour(tmp_path: Path) -> None:
    fichiers = {"reglement": rendu.serialiser("reglement", {"x": 1})}
    rendu.ecrire(tmp_path, fichiers)

    assert rendu.ecarts(tmp_path, fichiers) == []


def test_l_historique_tolere_les_entrees_ajoutees(tmp_path: Path) -> None:
    """Le commit en cours n'existe pas encore au pre-commit, mais la CI le verra.

    Sans cette tolérance, la porte serait rouge **en permanence** dès qu'une règle est touchée :
    le hook génère sans le commit, la CI régénère avec. C'est la raison d'être de l'exception.
    """
    commite = {"une-regle": [{"reference": "aaa", "date": "2026-01-01"}]}
    frais = {
        "une-regle": [
            {"reference": "bbb", "date": "2026-02-01"},
            {"reference": "aaa", "date": "2026-01-01"},
        ]
    }
    rendu.ecrire(tmp_path, {"historique": rendu.serialiser("historique", commite)})

    assert rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", frais)}) == []


def test_l_historique_vide_est_signale(tmp_path: Path) -> None:
    """La tolérance porte sur l'ajout, pas sur l'effacement.

    Un `historique.js` vidé à `{}` passait au vert — le fichier étant par ailleurs soustrait à la
    relecture par `.gitattributes`, la panne était invisible sur les trois canaux à la fois.
    """
    rendu.ecrire(tmp_path, {"historique": rendu.serialiser("historique", {})})
    frais = {"une-regle": [{"reference": "aaa", "date": "2026-01-01"}]}

    problemes = rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", frais)})

    assert problemes and "aucune entrée commitée" in problemes[0]


def test_l_historique_falsifie_est_signale(tmp_path: Path) -> None:
    """Comparer les seules empreintes laissait réécrire dates et motifs sans que rien ne bronche."""
    commite = {"une-regle": [{"reference": "aaa", "date": "1999-01-01", "motif": "MENSONGE"}]}
    frais = {"une-regle": [{"reference": "aaa", "date": "2026-01-01", "motif": "la vérité"}]}
    rendu.ecrire(tmp_path, {"historique": rendu.serialiser("historique", commite)})

    problemes = rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", frais)})

    assert problemes and "diffère de ce que l'historique dit" in problemes[0]


def test_un_fichier_tronque_donne_un_message_pas_une_trace(tmp_path: Path) -> None:
    """Le message « illisible — régénère » existait mais n'était jamais atteint."""
    cible = tmp_path / "atlas" / "donnees" / "historique.js"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text('window.ATLAS.historique = {"a": [', encoding="utf-8", newline="\n")

    problemes = rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", {"a": []})})

    assert problemes and "illisible" in problemes[0]


def test_l_historique_signale_une_entree_perdue(tmp_path: Path) -> None:
    """Perdre une entrée signale que les bornes d'une règle ont bougé : à régénérer."""
    commite = {"une-regle": [{"reference": "aaa"}, {"reference": "bbb"}]}
    frais = {"une-regle": [{"reference": "aaa"}]}
    rendu.ecrire(tmp_path, {"historique": rendu.serialiser("historique", commite)})

    problemes = rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", frais)})

    assert problemes and "a perdu l'entrée bbb" in problemes[0]


def test_l_historique_absent_ne_condamne_rien(tmp_path: Path) -> None:
    """L'atlas doit rester générable dans une archive sans `.git`."""
    commite = {"une-regle": [{"reference": "aaa"}]}
    rendu.ecrire(tmp_path, {"historique": rendu.serialiser("historique", commite)})

    assert rendu.ecarts(tmp_path, {"historique": rendu.serialiser("historique", {})}) == []
