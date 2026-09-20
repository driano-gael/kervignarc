"""Rendu tableur du **palmarès** (E16US016) — écrit en 2ᵉ passe de revue.

⚠️ Ce fichier existe parce que deux axes ont constaté le même trou : `_rang` et `_statut` portent
la logique la moins triviale du lot côté palmarès, et **aucune assertion ne les atteignait**. Les
tests de service s'arrêtent au faux générateur ; ceux d'API n'assèrent que la ligne d'en-tête et un
compte de lignes, sur un décor à quatre archers sans ex æquo ni forfait. Une inversion des colonnes
*Rang catégorie* / *Rang club*, ou un `_rang` rendant « 5-5 », passait toute la suite au vert — sur
un document **public**, affiché au mur et repris par la presse.
"""

from __future__ import annotations

import datetime

from domain.classement import StatutClassement
from domain.entree_audit import ActionAuditee, EntreeAudit, JournalAudit
from domain.palmares import LignePalmares, Palmares, SectionPalmares
from domain.podium import ReglagePodiums
from infrastructure.tableur.audit import _LIBELLES_ACTION, GenerateurJournalAuditTableur
from infrastructure.tableur.grille import rendre_csv
from infrastructure.tableur.palmares import _LIBELLES_STATUT, GenerateurPalmaresTableur


def _ligne(**surcharges: object) -> LignePalmares:
    defauts: dict[str, object] = {
        "rang_min": 1,
        "rang_max": 1,
        "rang_categorie_min": 1,
        "rang_categorie_max": 1,
        "rang_club_min": None,
        "rang_club_max": None,
        "decerne": True,
        "en_lice": False,
        "archer_id": 1,
        "nom": "MARTIN",
        "prenom": "Sophie",
        "categorie_id": 1,
        "categorie_libelle": "Senior",
        "club_id": None,
        "club_libelle": None,
        "origine": None,
        "statut": StatutClassement.EN_LICE,
    }
    defauts.update(surcharges)
    return LignePalmares(**defauts)  # type: ignore[arg-type]


_CRENEAU = "Départ n°1 — 09:00"
"""Le libellé rendu par `Depart.libelle_creneau` — recopié ici, ces tests n'ayant pas de départ."""


def _section(complet: Palmares, affiche: Palmares) -> SectionPalmares:
    return SectionPalmares(depart_id=41, libelle=_CRENEAU, complet=complet, affiche=affiche)


def _lignes_csv(*lignes: LignePalmares) -> list[list[str]]:
    """Les rangs du CSV, **colonne « Départ » retirée** (E06US009).

    ⚠️ **Retirée, et non renumérotée dans douze assertions** : ce que ces tests gardent est le
    rendu d'une *ligne d'archer* — fourchettes de rang, statuts, club. Décaler chaque index de un
    aurait risqué un décalage muet sur l'un d'eux. La colonne elle-même a son propre test
    (`test_la_colonne_depart_nomme_le_creneau_de_chaque_ligne`), qui est le seul endroit où son
    existence est affirmée.
    """
    palmares = Palmares(lignes=tuple(lignes))
    octets = GenerateurPalmaresTableur(rendre_csv).palmares(
        "Trophée", sections=[_section(palmares, palmares)], reglage=ReglagePodiums()
    )
    return [rang.split(";")[1:] for rang in octets.decode("utf-8-sig").splitlines()]


def test_la_colonne_depart_nomme_le_creneau_de_chaque_ligne() -> None:
    """CA « chaque podium est nommé » — au tableur, le créneau est une **colonne**, pas un onglet.

    ⚠️ **Deux créneaux, pas un** : à une seule section, un bug qui écrirait le libellé du premier
    partout resterait invisible. C'est précisément le raccourci que cette US retire.
    """
    matin = Palmares(lignes=(_ligne(nom="MARTIN"),))
    apres_midi = Palmares(lignes=(_ligne(archer_id=2, nom="CADIOU"),))

    octets = GenerateurPalmaresTableur(rendre_csv).palmares(
        "Trophée",
        sections=[
            _section(matin, matin),
            SectionPalmares(
                depart_id=42,
                libelle="Départ n°2 — 14:00",
                complet=apres_midi,
                affiche=apres_midi,
            ),
        ],
        reglage=ReglagePodiums(),
    )

    rangs = [rang.split(";") for rang in octets.decode("utf-8-sig").splitlines()]
    assert rangs[0][0] == "Départ"
    assert [(rang[0], rang[2]) for rang in rangs[1:]] == [
        (_CRENEAU, "MARTIN"),
        ("Départ n°2 — 14:00", "CADIOU"),
    ]


def test_un_rang_exact_sort_sans_fourchette() -> None:
    (_, ligne) = _lignes_csv(_ligne(rang_min=5, rang_max=5))

    assert ligne[0] == "5"


def test_un_ex_aequo_sort_en_fourchette() -> None:
    """Deux bornes distinctes disent *combien* partagent la place — l'écrire « 5 » le perdrait."""
    (_, ligne) = _lignes_csv(_ligne(rang_min=5, rang_max=8))

    assert ligne[0] == "5-8"


def test_un_archer_hors_classement_a_ses_trois_rangs_vides() -> None:
    """Un disqualifié n'a **pas** de rang (ADR-0050) : la case est vide, jamais un zéro."""
    (_, ligne) = _lignes_csv(
        _ligne(
            rang_min=None,
            rang_max=None,
            rang_categorie_min=None,
            rang_categorie_max=None,
            statut=StatutClassement.DISQUALIFIE,
        )
    )

    assert (ligne[0], ligne[4], ligne[6]) == ("", "", "")
    assert ligne[7] == "Disqualifié"


def test_les_trois_rangs_ne_sont_pas_intervertis() -> None:
    """⚠️ Trois valeurs **distinctes** exprès : avec des rangs égaux, une inversion passerait.

    L'ordre des colonnes est *Rang · Nom · Prénom · Catégorie · Rang catégorie · Club · Rang club*.
    """
    (_, ligne) = _lignes_csv(
        _ligne(
            rang_min=7,
            rang_max=7,
            rang_categorie_min=3,
            rang_categorie_max=3,
            rang_club_min=2,
            rang_club_max=2,
            club_libelle="Compagnie de Kervignarc",
        )
    )

    assert ligne[0] == "7"
    assert ligne[3] == "Senior"
    assert ligne[4] == "3"
    assert ligne[5] == "Compagnie de Kervignarc"
    assert ligne[6] == "2"


def test_un_archer_sans_club_rend_une_case_vide_et_non_none() -> None:
    (_, ligne) = _lignes_csv(_ligne(club_libelle=None))

    assert ligne[5] == ""


def test_les_statuts_emploient_les_mots_du_pdf() -> None:
    """Règle 3 : le même archer est « Abandon » sur l'affiche du mur et dans le classeur.

    ⚠️ La 1ʳᵉ livraison rendait ici les slugs bruts (`abandon`, `disqualifie`), pendant que le PDF
    du **même** palmarès écrivait « Abandon » et « Disqualifié » — relevé en revue.
    """
    (_, abandon) = _lignes_csv(_ligne(statut=StatutClassement.ABANDON))
    (_, en_cours) = _lignes_csv(_ligne(en_lice=True, decerne=False))
    (_, acquis) = _lignes_csv(_ligne(decerne=True))

    assert abandon[7] == "Abandon"
    assert en_cours[7] == "En cours"
    assert acquis[7] == "Acquis"


def test_le_tableur_rend_le_palmares_affiche_et_non_le_complet() -> None:
    """⚠️ Rendre `complet` exporterait le tournoi entier à qui a demandé une seule catégorie."""
    affiche = Palmares(lignes=(_ligne(nom="MARTIN"),))
    complet = Palmares(lignes=(_ligne(nom="MARTIN"), _ligne(archer_id=2, nom="CADIOU")))

    octets = GenerateurPalmaresTableur(rendre_csv).palmares(
        "Trophée", sections=[_section(complet, affiche)], reglage=ReglagePodiums()
    )

    texte = octets.decode("utf-8-sig")
    assert "MARTIN" in texte
    assert "CADIOU" not in texte


# --- Journal d'audit : l'horodatage dit son fuseau (E16US016, 2ᵉ passe) -------------------------
#
# ⚠️ `docs/fonctionnel/E16US016.md` promet noir sur blanc que l'heure exportée est en UTC « et le
# dit ». Le seul test qui voyait une ligne du journal sautait la colonne d'horodatage, faute
# d'horloge maîtrisée : le suffixe, qui est tout l'intérêt de la colonne dans un litige, pouvait
# disparaître sans rien faire rougir (relevé en revue, axe B).


def test_l_horodatage_du_journal_exporte_porte_son_fuseau() -> None:
    quand = datetime.datetime(2026, 9, 18, 8, 12, 4, tzinfo=datetime.UTC)
    journal = JournalAudit(
        tournoi="Trophée",
        entrees=(
            EntreeAudit(
                tournoi_id=1,
                action=ActionAuditee.CORRECTION_SCORE,
                auteur="ROUX Ana",
                horodatage=quand,
                objet="Série 1, flèche 2",
                avant="8",
                apres="9",
            ),
        ),
    )

    octets = GenerateurJournalAuditTableur(rendre_csv).journal(journal)

    (_, ligne) = octets.decode("utf-8-sig").splitlines()
    assert ligne.split(";")[0] == "2026-09-18 08:12:04 UTC"
    # Et l'acte est en clair, comme à l'écran — pas le slug `correction_score` (règle 3).
    assert ligne.split(";")[2] == "Correction"


# --- Registres jumeaux : exhaustivité prouvée, pas seulement repliée (2ᵉ passe de revue) --------
#
# ⚠️ Les deux tables de libellés doublent des énumérations du domaine, et leur repli `.get(…, value)`
# **éteint le signal** : un membre ajouté demain sortirait en slug dans l'export pendant que l'écran
# écrirait le libellé — soit exactement la divergence que cette US a corrigée. Trois axes l'ont
# relevé : ici les deux listes sont en Python dans le même processus, l'argument « deux langages »
# du jumeau front ne vaut pas. Même patron que `MEDIA_TYPES` ↔ `FormatExport` (`api/documents.py`).


def test_chaque_acte_du_domaine_a_son_libelle_a_l_export() -> None:
    assert set(_LIBELLES_ACTION) == set(ActionAuditee)


def test_chaque_statut_de_forfait_a_son_libelle_a_l_export() -> None:
    """`EN_LICE` est à part : il n'a pas de libellé de forfait, il se résout sur l'avancement."""
    assert set(_LIBELLES_STATUT) == set(StatutClassement) - {StatutClassement.EN_LICE}
