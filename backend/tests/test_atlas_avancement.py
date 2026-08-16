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
