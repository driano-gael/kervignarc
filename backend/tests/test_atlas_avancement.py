"""La règle de comptage du tracker, écrite depuis le CA — avant l'implémentation.

`journal-d-avancement/SUIVI-US.md` porte sa propre règle de comptage, instituée le 08/08/2026
**parce que trois compteurs sur cinq étaient faux**, chacun d'un mode différent. Cette règle est
l'oracle de cette US : ces tests la transcrivent à la lettre, sur des extraits littéraux, avant
qu'une ligne du lecteur n'existe.

C'est délibéré. Sur `E00US018`, le seul défaut **bloquant** de la revue se trouvait exactement là
où les tests avaient été dérivés du code : ils décrivaient ce que le lecteur faisait, donc ils ne
pouvaient pas voir ce qu'il oubliait de faire.
"""

from __future__ import annotations

import pytest

from atlas.modele import AtlasSourceInvalide
from atlas.sources import suivi

# Un jalon : le tableau porte une colonne `Seq`. Cet extrait contient **un cas de chaque** clause
# de la règle de comptage.
JALON = """## J9 — Un jalon d'essai — 🔶 **en cours (2/3)**

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | E09US001 | Livrée | ✅ |
| 2 | E09US002 | Livrée aussi | ✅ |
| 3 | E09US003 | À faire | ⬜ |
| — | E09US004 | Hors séquence, comptée ailleurs | ⬜ |
| ~~5~~ | ~~E09US005~~ | Absorbée par une autre | ⛔ |
| 6 | — | Relevé d'écarts — travail livré, mais pas une US | ✅ |
"""

# Une section d'ajouts : pas de colonne `Seq`, comme celle de J0.
AJOUTS = """## Ajout du 09/09/2026 — ✅ **livrée (1/1)**

| US | Titre | Jalon | État |
|---|---|---|---|
| E09US004 | Hors séquence, comptée ici | J9 | ✅ |
"""


def _section(texte: str) -> suivi.Section:
    (section,) = suivi.lire_sections_du_texte(texte)
    return section


# --- CA : « les compteurs sont recalculés, et un écart bloque » --------------------------------


def test_le_compteur_ne_retient_que_les_lignes_portant_un_identifiant_d_us() -> None:
    """« Relevé d'écarts » est du travail livré, pas une US : ni numérateur ni dénominateur."""
    section = _section(JALON)

    assert suivi.compter(section) == (2, 3)


def test_une_us_absorbee_est_hors_decompte() -> None:
    """⛔ n'est ni ✅ ni ⬜ : la capacité a été livrée par une autre US."""
    section = _section(JALON)

    assert "E09US005" not in {ligne.identifiant for ligne in section.comptees}


def test_une_us_hors_sequence_ne_compte_pas_dans_le_jalon() -> None:
    """`Seq = —` : elle est remontée d'une section d'ajouts et y est déjà comptée.

    Sans cette clause, la même US serait comptée deux fois — c'est l'un des trois modes de panne
    qui ont fait écrire la règle.
    """
    section = _section(JALON)

    assert "E09US004" not in {ligne.identifiant for ligne in section.comptees}


def test_une_us_hors_sequence_compte_dans_sa_section_d_origine() -> None:
    section = _section(AJOUTS)

    assert suivi.compter(section) == (1, 1)
    assert "E09US004" in {ligne.identifiant for ligne in section.comptees}


def test_le_compteur_ecrit_dans_le_titre_est_relu() -> None:
    """C'est lui qu'on confronte au recalcul : sans lecture, aucun écart n'est détectable."""
    assert _section(JALON).compteur_ecrit == (2, 3)
    assert _section(AJOUTS).compteur_ecrit == (1, 1)


def test_un_ecart_entre_le_compteur_ecrit_et_le_recalcul_est_detecte() -> None:
    section = _section(JALON.replace("(2/3)", "(2/4)"))

    assert suivi.compter(section) != section.compteur_ecrit


# --- CA : « le lecteur se cale sur les colonnes présentes, jamais sur une position » -----------


def test_les_colonnes_sont_reperees_par_leur_nom() -> None:
    """Sept variantes d'en-tête coexistent dans le fichier ; seule la position varie."""
    variante = """## Section — ✅ **livrée (1/1)**

| US | Titre | Épic | État |
|---|---|---|---|
| E09US009 | Un titre | EPIC-09 | ✅ |
"""
    (ligne,) = _section(variante).lignes

    assert ligne.identifiant == "E09US009"
    assert ligne.titre == "Un titre"
    assert ligne.etat == "✅"


def test_une_table_sans_colonne_etat_fait_echouer_bruyamment() -> None:
    """Un décompte silencieusement faux est pire que pas de vue du tout."""
    boiteuse = """## Section — ✅ **livrée (1/1)**

| US | Titre |
|---|---|
| E09US009 | Un titre |
"""
    with pytest.raises(AtlasSourceInvalide, match="État"):
        _section(boiteuse)


def test_une_ligne_plus_courte_que_son_en_tete_fait_echouer_bruyamment() -> None:
    """Trouvé en écrivant ces tests : une ligne courte décalait les colonnes **en silence**.

    L'état se lisait vide, donc « non livrée », et le compteur devenait faux sans un mot — soit
    exactement la panne que la règle de comptage a été instituée pour éliminer.
    """
    decalee = """## Section — ✅ **livrée (1/1)**

| US | Titre | Jalon | État |
|---|---|---|---|
| E09US009 | Un titre | ✅ |
"""
    with pytest.raises(AtlasSourceInvalide, match="cellules"):
        _section(decalee)


def test_une_section_sans_compteur_est_lue_sans_etre_comptee() -> None:
    """`## Légende`, `## 🎯 Prochaine US` n'ont pas de `n/N` — et n'ont pas à en avoir."""
    sans_compteur = """## US caduque

| US | Titre | Motif |
|---|---|---|
| E09US010 | Une US sans objet | la capacité a disparu |
"""
    section = _section(sans_compteur)

    assert section.compteur_ecrit is None


def test_le_glyphe_barre_ne_masque_pas_l_identifiant() -> None:
    """Le texte barré est conservé pour que la référence reste trouvable, jamais supprimé."""
    section = _section(JALON)
    barree = [ligne for ligne in section.lignes if ligne.etat == "⛔"]

    assert [ligne.identifiant for ligne in barree] == ["E09US005"]


# --- Les formes du fichier qu'aucun test ne couvrait --------------------------------------------


CITATION = """## \U0001f3af Prochaine US

> | Rang | US | Pourquoi à ce rang |
> |---|---|---|
> | **1** | `E05US030` | à prendre ensuite |
"""


def test_un_tableau_en_citation_n_est_ni_lu_ni_compte() -> None:
    """L'angle mort qui a caché deux US **livrées** — une vue de priorité, pas un inventaire.

    Son exclusion est portante, et elle tenait à un seul `startswith("|")` qu'un refactor
    « tolérons l'indentation » aurait cassé sans faire rougir quoi que ce soit.
    """
    (section,) = suivi.lire_sections_du_texte(CITATION)

    assert section.lignes == ()
    assert section.compteur_ecrit is None


def test_une_ligne_plus_longue_que_son_entete_est_refusee() -> None:
    """Le décalage de colonnes, dans **les deux sens**.

    Le garde ne fermait que la moitié courte ; côté long, l'état se lisait sur la mauvaise cellule
    et le compteur devenait faux en silence — alors même que le commentaire décrivait les deux.
    """
    trop_long = """## J0 — essai (1/1)

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | `E00US001` | Un titre | et une cellule de trop | ✅ |
"""
    with pytest.raises(AtlasSourceInvalide, match="cellules pour"):
        suivi.lire_sections_du_texte(trop_long)


def test_un_tube_echappe_ne_decale_pas_les_colonnes() -> None:
    """`\\|` est la convention Markdown : le tube appartient à la cellule.

    Sans elle, un titre parfaitement légitime faisait **rougir la porte** — et le message poussait
    à corriger un compteur juste vers une valeur fausse. Le faux positif est le pire des défauts
    pour un garde-fou : c'est lui qui le fait désactiver.
    """
    avec_tube = """## J0 — essai (1/1)

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | `E00US001` | Boutons \\| champs | ✅ |
"""
    (section,) = suivi.lire_sections_du_texte(avec_tube)

    assert suivi.compter(section) == (1, 1)
    assert section.lignes[0].titre == "Boutons | champs"


def test_un_second_tableau_ferme_le_premier() -> None:
    """Deux tableaux dans une même section : le second était lu avec les colonnes du premier.

    Ses lignes sortaient avec un identifiant vide, donc hors décompte — l'US **disparaissait**,
    et le compteur concordait quand même. Perte silencieuse, dans le module qui refuse justement
    de compter faux sans le dire.
    """
    deux_tableaux = """## J9 — essai (1/2)

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | `E09US001` | Première | ✅ |

Un paragraphe qui sépare les deux tableaux.

| US | Titre | Épic | État |
|---|---|---|---|
| `E09US050` | Seconde | 09 | ⬜ |
"""
    (section,) = suivi.lire_sections_du_texte(deux_tableaux)

    assert [ligne.identifiant for ligne in section.lignes] == ["E09US001", "E09US050"]
    assert suivi.compter(section) == (1, 2)


def test_un_titre_dans_un_bloc_de_code_n_ouvre_pas_de_section() -> None:
    """Ce fichier documente son propre format : il cite ses propres titres."""
    avec_exemple = """## J0 — essai (1/1)

```md
## Fausse section (9/9)
```

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | `E00US001` | Une US | ✅ |
"""
    sections = suivi.lire_sections_du_texte(avec_exemple)

    assert [s.titre for s in sections] == ["J0 — essai (1/1)"]
    assert suivi.compter(sections[0]) == (1, 1)


def test_un_compteur_n_est_lu_qu_en_fin_de_titre() -> None:
    """Une date en `AAAA/MM` au milieu d'un libellé n'est pas un compteur.

    Non ancrée, la regex la lisait comme `(2026, 8)` et rendait la section divergente — bloquante,
    sur un titre parfaitement légitime.
    """
    piegeux = """## Lot du 12/03 (2026/08) — fini

| US | Titre | État |
|---|---|---|
| `E00US001` | Une US | ✅ |
"""
    (section,) = suivi.lire_sections_du_texte(piegeux)

    assert section.compteur_ecrit is None


def test_une_us_bloquee_compte_au_denominateur() -> None:
    """La Légende tranche : 🔒 compte comme une ⬜. Seule ⛔ sort du décompte."""
    bloquee = """## J0 — essai (1/2)

| Seq | US | Titre | État |
|---|---|---|---|
| 1 | `E00US001` | Livrée | ✅ |
| 2 | `E00US002` | Bloquée | 🔒 |
"""
    (section,) = suivi.lire_sections_du_texte(bloquee)

    assert suivi.compter(section) == (1, 2)


# --- L'annonce de tête : elle ne peut plus s'éteindre en silence ---------------------------------


ENTETE = """# Suivi des US

**Dernière mise à jour : 16/08/2026** · **112 US livrées** · dernière : `E00US019`
*(le résumé de l'US, qui cite ADR-0086 et rien d'autre.)*

Précédente : `E00US018`
*(le résumé de la précédente, qui cite ADR-0084.)*

## Légende

C'est cette règle qui donne J0 12/12, J1 46/46 et J3 16/18.
"""


def test_l_annonce_de_tete_se_lit_en_entier() -> None:
    entete = suivi.lire_entete_du_texte(ENTETE)

    assert (entete.derniere, entete.livrees) == ("E00US019", 112)
    assert entete.adr_du_resume == ("0086",)
    assert entete.recapitulatif == (("J0", 12, 12), ("J1", 46, 46), ("J3", 16, 18))


def test_le_resume_s_arrete_a_la_ligne_vide() -> None:
    """Borne **locale**. Le marqueur distant « Précédente : » a déjà été réécrit une fois.

    S'il disparaissait, le résumé couvrait tout le fichier, tous les ADR étaient réputés cités, et
    `derniere-us-orpheline` ne pouvait plus **jamais** parler — sans se signaler comme désactivé.
    """
    entete = suivi.lire_entete_du_texte(ENTETE.replace("Précédente :", "Avant elle :"))

    assert entete.adr_du_resume == ("0086",)


@pytest.mark.parametrize(
    "deforme",
    [
        pytest.param("**112** US livrées", id="gras déplacé sur le total"),
        pytest.param("112 US **livrées**", id="gras déplacé sur le mot"),
    ],
)
def test_un_total_illisible_fait_echouer_la_lecture(deforme: str) -> None:
    """Le silence ne vaut pas accord : sans total lisible, le contrôle s'éteignait sans un mot.

    Mesuré en revue : un tracker annonçant « 999 US livrées » passait la porte au vert.
    """
    with pytest.raises(AtlasSourceInvalide, match="n'annonce pas de total"):
        suivi.lire_entete_du_texte(ENTETE.replace("**112 US livrées**", deforme))


def test_une_annonce_absente_fait_echouer_la_lecture() -> None:
    sans_accents_graves = ENTETE.replace("dernière : `E00US019`", "dernière : **E00US019**")

    with pytest.raises(AtlasSourceInvalide, match="aucune ligne d'annonce"):
        suivi.lire_entete_du_texte(sans_accents_graves)


def test_les_deux_champs_se_lisent_dans_n_importe_quel_ordre() -> None:
    """Ils sont sur la même ligne : c'est la forme du fichier, pas l'ordre des mots, qui compte."""
    echange = ENTETE.replace(
        "**112 US livrées** · dernière : `E00US019`",
        "dernière : `E00US019` · **112 US livrées**",
    )
    entete = suivi.lire_entete_du_texte(echange)

    assert (entete.derniere, entete.livrees) == ("E00US019", 112)
