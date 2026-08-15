"""Tests unitaires des parseurs de l'atlas, sur des chaînes littérales.

Même patron que `test_domain_isolation.py`, qui éprouve son détecteur sur des extraits en dur
plutôt que sur le dépôt : un test qui lit le dépôt réel devient vert « par chance » le jour où la
source change, alors qu'un extrait figé continue de décrire ce que le parseur doit savoir faire.
Les garde-fous sur le dépôt réel vivent dans `test_atlas_corpus.py`, et c'est un autre métier.
"""

from __future__ import annotations

import pytest

from atlas import markdown
from atlas.modele import AtlasSourceInvalide, Sens, Statut, TypeLien
from atlas.normalisation import normaliser_statut, relation
from atlas.sources import reglement

ENTETE_ADR = """# ADR-0075 — Le départ est la portée sportive

- **Statut** : Accepté
- **Date** : 2026-08-06
- **Amende** : [ADR-0017](0017-le-depart.md) (dont la décision n'avait été
  portée que par la logistique) ; [ADR-0045](0045-sequence.md)
- **Introduit par** : E01US025

## Contexte et problème

Du texte qui ne doit pas être lu comme un champ d'en-tête.
"""


def test_entete_recolle_les_continuations_indentees() -> None:
    champs = dict(markdown.entete_a_puces(ENTETE_ADR))

    assert champs["Statut"] == "Accepté"
    assert champs["Date"] == "2026-08-06"
    assert "0017" in champs["Amende"] and "0045" in champs["Amende"]
    assert "portée que par la logistique" in champs["Amende"]


def test_entete_s_arrete_au_premier_titre_de_section() -> None:
    assert "ne doit pas être lu" not in " ".join(v for _, v in markdown.entete_a_puces(ENTETE_ADR))


def test_entete_survit_a_un_encadre_avant_l_en_tete() -> None:
    """`ADR-0016` ouvre par un avertissement en citation, son en-tête vient après."""
    texte = "# ADR-0016 — Titre\n\n> ⚠️ **Amendé par ADR-0050.**\n\n- **Statut** : Accepté\n"

    assert dict(markdown.entete_a_puces(texte))["Statut"] == "Accepté"


def test_section_s_arrete_au_titre_suivant() -> None:
    texte = "## Décision\n\nOn tranche ceci.\n\n## Conséquences\n\nEt il en découle cela.\n"

    assert markdown.section(texte, "Décision") == "On tranche ceci."


def test_section_absente_rend_une_chaine_vide() -> None:
    assert markdown.section("## Décision\n\nx\n", "Porté dans le code par") == ""


@pytest.mark.parametrize(
    ("brut", "attendu", "remplacant"),
    [
        ("Accepté", Statut.ACCEPTE, ""),
        ("accepté", Statut.ACCEPTE, ""),
        ("Accepté (forme de `config` **amendée** par [ADR-0046](x.md))", Statut.ACCEPTE, ""),
        ("**Remplacé par [ADR-0059](0059-routage.md)** (30/07/2026)", Statut.REMPLACE, "0059"),
    ],
)
def test_statuts_normalises(brut: str, attendu: Statut, remplacant: str) -> None:
    assert normaliser_statut(brut, fichier="x.md") == (attendu, remplacant)


def test_statut_inconnu_leve() -> None:
    with pytest.raises(AtlasSourceInvalide, match="statut d'ADR non reconnu"):
        normaliser_statut("En cours de rédaction", fichier="x.md")


def test_relation_normalisee_vers_son_sens() -> None:
    assert relation("Amende", fichier="x.md") == (TypeLien.AMENDE, Sens.SORTANT)
    assert relation("Raffine", fichier="x.md") == (TypeLien.AMENDE, Sens.SORTANT)


def test_relation_inversee_est_entrante() -> None:
    """« Prolongé par » désigne ce qui agit **sur** l'ADR : l'arête est entrante."""
    assert relation("Prolongé par", fichier="x.md") == (TypeLien.COMPLETE, Sens.ENTRANT)
    assert relation("Prolonge", fichier="x.md") == (TypeLien.COMPLETE, Sens.SORTANT)


def test_libelle_de_relation_inconnu_leve_avec_la_ligne_a_ajouter() -> None:
    """Le garde-fou central : un verbe neuf doit forcer une décision, pas disparaître."""
    with pytest.raises(AtlasSourceInvalide) as echec:
        relation("Contredit", fichier="docs/adr/0099-x.md")

    message = str(echec.value)
    assert "docs/adr/0099-x.md" in message
    assert "Contredit" in message
    assert '"contredit"' in message  # la ligne à coller est donnée telle quelle


# --- Le règlement -----------------------------------------------------------------------------

REGLE_AVEC_DEUX_INCISES = """- **Autonomie.** Du texte.
  *(Ajouté le 29/07/2026 : la règle antérieure ne parlait que d'« arbitrage ».)*
  Et encore du texte. *(Cas réel, tranché le 15/07/2026 en E02US002 : cf. ADR-0014.)*
"""


def test_deux_incises_datees_donnent_deux_amendements() -> None:
    amendements = reglement._amendements(REGLE_AVEC_DEUX_INCISES)

    assert [a.date for a in amendements] == ["2026-07-15", "2026-07-29"]
    assert {a.nature for a in amendements} == {"cas réel", "ajout"}


def test_une_incise_datee_retient_son_us_et_son_adr() -> None:
    (amendement,) = reglement._amendements(
        "*(Cas réel, tranché le 15/07/2026 en E02US002 : cf. ADR-0014.)*"
    )

    assert amendement.us == ("E02US002",)
    assert amendement.adr == ("0014",)


def test_une_parenthese_en_italique_sans_date_n_est_pas_un_amendement() -> None:
    assert reglement._amendements("Du texte *(une simple précision de style)* et la suite.") == ()


def test_le_gras_qui_ouvre_la_regle_fait_le_titre() -> None:
    assert reglement._titre("1. **Isolation du domaine.** Le reste du corps.") == (
        "Isolation du domaine"
    )


def test_un_gras_au_milieu_de_la_phrase_ne_fait_pas_le_titre() -> None:
    """Sinon la règle « …doit être **redécoupée** » s'intitulerait « redécoupée »."""
    titre = reglement._titre("- Une US trop grosse doit être **redécoupée** (maille INVEST).")

    assert titre.startswith("Une US trop grosse")


def test_un_titre_en_gras_sur_deux_lignes_avec_un_lien_est_remis_en_clair() -> None:
    titre = reglement._titre(
        "- **Le suivi des US ([`journal-d-avancement/SUIVI-US.md`](x.md)) est tenu\n"
        "  à jour dès que nécessaire** : la suite."
    )

    assert titre.startswith("Le suivi des US")
    assert "](" not in titre and "**" not in titre


def test_tronquer_coupe_sur_un_mot_et_signale_la_coupe() -> None:
    assert markdown.tronquer("un deux trois quatre", 10) == "un deux […]"
    assert markdown.tronquer("court", 10) == "court"
