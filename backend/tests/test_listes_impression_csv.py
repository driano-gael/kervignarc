"""Tests de l'adapter CSV des listes (E16US007) — **rendu**, écrit après l'implémentation.

Le contenu composé est l'affaire du service (`test_service_listes_impression.py`, oracle du CA) ;
ici on vérifie ce que l'adapter met dans les octets, et surtout les quatre partis d'ADR-0101 §4 —
BOM, point-virgule, montants sommables, aucune ligne de total. ⚠️ Chacun de ces quatre est
invisible à l'œil dans un tableur qui « marche presque » : c'est ce qui justifie de les épingler.
"""

from __future__ import annotations

from domain.listes_impression import (
    GroupePaiementClub,
    LignePaiementImpression,
    LignePlacement,
    ListeClubPaiement,
    ListePlacement,
    TriPlacement,
)
from infrastructure.tableur.listes_impression import GenerateurListesImpressionCsv


def _ligne_placement(nom: str, prenom: str, cible: int, position: str) -> LignePlacement:
    return LignePlacement(
        nom=nom,
        prenom=prenom,
        categorie="Sénior Homme",
        depart_numero=1,
        cible_index=cible,
        position=position,
    )


def _texte(octets: bytes) -> str:
    return octets.decode("utf-8-sig")


def _lignes(octets: bytes) -> list[str]:
    return _texte(octets).strip().split("\r\n")


# --- Placement -----------------------------------------------------------------------------------


def test_placement_rend_une_ligne_par_archer_avec_en_tete() -> None:
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(
            _ligne_placement("Durand", "Marie", 1, "A"),
            _ligne_placement("Martin", "Léo", 2, "B"),
        ),
    )

    lignes = _lignes(GenerateurListesImpressionCsv().placement(liste))

    assert lignes == [
        "Départ;Cible;Couloir;Nom;Prénom;Catégorie",
        "1;1;A;Durand;Marie;Sénior Homme",
        "1;2;B;Martin;Léo;Sénior Homme",
    ]


def test_placement_ne_porte_aucun_en_tete_de_document() -> None:
    """ADR-0101 §4 : un titre au-dessus de l'en-tête décalerait toute l'importation d'un cran."""
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=2,
        tri=TriPlacement.NOM,
        lignes=(_ligne_placement("Durand", "Marie", 1, "A"),),
    )

    texte = _texte(GenerateurListesImpressionCsv().placement(liste))

    assert texte.startswith("Départ;")
    assert "Trophée" not in texte


def test_placement_vide_garde_son_en_tete() -> None:
    """Un fichier à zéro octet se lit comme une panne ; l'en-tête dit « aucun archer placé »."""
    liste = ListePlacement(tournoi="Trophée", depart_numero=None, tri=TriPlacement.CIBLE, lignes=())

    assert _lignes(GenerateurListesImpressionCsv().placement(liste)) == [
        "Départ;Cible;Couloir;Nom;Prénom;Catégorie"
    ]


def test_le_bom_utf8_est_en_tete() -> None:
    """Sans BOM, Excel lit l'UTF-8 en ANSI : « Léo » devient « LÃ©o » (ADR-0101 §4)."""
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement("Martin", "Léo", 1, "A"),),
    )

    octets = GenerateurListesImpressionCsv().placement(liste)

    assert octets.startswith(b"\xef\xbb\xbf")
    assert "Léo" in _texte(octets)


def test_un_nom_contenant_le_separateur_est_echappe() -> None:
    """⚠️ Un club « Kervignarc; section jeunes » décalerait toutes les colonnes suivantes."""
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement('Du;rand "le grand"', "Marie", 1, "A"),),
    )

    ligne = _lignes(GenerateurListesImpressionCsv().placement(liste))[1]

    assert '"Du;rand ""le grand"""' in ligne


# --- Club & paiement -----------------------------------------------------------------------------


def _groupe(club: str, nom: str, du: int, paye: int) -> GroupePaiementClub:
    return GroupePaiementClub(
        club=club,
        lignes=(
            LignePaiementImpression(
                nom=nom, prenom="Marie", departs=(1, 2), du_centimes=du, paye_centimes=paye
            ),
        ),
        total_du_centimes=du,
        total_paye_centimes=paye,
    )


def test_club_paiement_met_le_club_en_colonne_et_ne_totalise_pas() -> None:
    """ADR-0101 §4 : une ligne « Total » au milieu des données casse le tri et le filtre."""
    liste = ListeClubPaiement(
        tournoi="Trophée",
        groupes=(
            _groupe("Kervignarc", "Durand", 1600, 1600),
            _groupe("Sans club", "Martin", 800, 0),
        ),
    )

    lignes = _lignes(GenerateurListesImpressionCsv().club_paiement(liste))

    assert lignes[0] == "Club;Nom;Prénom;Départs;Nb départs;Dû;Payé;Reste;Réglé"
    assert lignes[1] == "Kervignarc;Durand;Marie;1 2;2;16,00;16,00;0,00;payé"
    assert lignes[2] == "Sans club;Martin;Marie;1 2;2;8,00;0,00;8,00;dû"
    assert len(lignes) == 3


def test_les_montants_sont_sommables() -> None:
    """Virgule décimale et **aucun symbole** : un « 8,00 € » resterait du texte au tableur."""
    liste = ListeClubPaiement(tournoi="Trophée", groupes=(_groupe("Kervignarc", "Durand", 850, 0),))

    ligne = _lignes(GenerateurListesImpressionCsv().club_paiement(liste))[1]

    assert ";8,50;0,00;8,50;" in ligne
    assert "€" not in ligne


def test_les_numeros_de_depart_ne_contiennent_pas_de_separateur_decimal() -> None:
    """⚠️ Séparés par une **espace**, pas par « , » : une virgule ferait lire « 1,2 » en nombre."""
    liste = ListeClubPaiement(tournoi="Trophée", groupes=(_groupe("Kervignarc", "Durand", 800, 0),))

    assert ";1 2;" in _lignes(GenerateurListesImpressionCsv().club_paiement(liste))[1]


# --- Injection de formule (CWE-1236) --------------------------------------------------------------


def test_un_club_nomme_comme_une_formule_n_est_pas_execute() -> None:
    """⚠️ Relevé par les cinq axes de revue. Le chemin est complet : un nom de club entre par
    l'import FFTA, ressort au CSV, et le fichier est fait pour être ouvert dans un tableur."""
    liste = ListeClubPaiement(
        tournoi="Trophée", groupes=(_groupe('=cmd|"/c calc"!A1', "Durand", 800, 0),)
    )

    ligne = _lignes(GenerateurListesImpressionCsv().club_paiement(liste))[1]

    assert ligne.startswith("\"'=cmd")


def test_un_nom_commencant_par_un_signe_est_neutralise() -> None:
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement("+33 6 12", "@Marie", 1, "A"),),
    )

    ligne = _lignes(GenerateurListesImpressionCsv().placement(liste))[1]

    assert ";'+33 6 12;'@Marie;" in ligne


def test_un_nom_ordinaire_n_est_pas_touche() -> None:
    """La neutralisation ne doit pas défigurer les 99,9 % de noms normaux."""
    liste = ListePlacement(
        tournoi="Trophée",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement("Durand", "Marie", 1, "A"),),
    )

    assert _lignes(GenerateurListesImpressionCsv().placement(liste))[1] == (
        "1;1;A;Durand;Marie;Sénior Homme"
    )


def test_les_montants_ne_sont_jamais_neutralises() -> None:
    """⚠️ Un montant préfixé d'une apostrophe cesse d'être sommable — ADR-0101 §4 l'interdit.

    Le décor force un `paye` supérieur au `du` pour produire un reste **négatif**, seul montant
    qui commence par un caractère d'amorce de formule.
    """
    liste = ListeClubPaiement(tournoi="Trophée", groupes=(_groupe("Kervignarc", "Durand", 0, 500),))

    ligne = _lignes(GenerateurListesImpressionCsv().club_paiement(liste))[1]

    assert ";-5,00;" in ligne
    assert "'-5,00" not in ligne


def test_un_archer_sans_depart_ni_du_rend_des_cellules_vides() -> None:
    """Cas courant (archer saisi, pas encore inscrit) : le PDF écrit « — », le CSV laisse vide.

    Parti **voulu** : une cellule vide se filtre au tableur, un tiret non. Épinglé pour qu'un
    futur `or "—"` recopié du PDF ne passe pas en silence.
    """
    groupe = GroupePaiementClub(
        club="Kervignarc",
        lignes=(
            LignePaiementImpression(
                nom="Durand", prenom="Marie", departs=(), du_centimes=0, paye_centimes=0
            ),
        ),
        total_du_centimes=0,
        total_paye_centimes=0,
    )

    ligne = _lignes(
        GenerateurListesImpressionCsv().club_paiement(ListeClubPaiement("Trophée", (groupe,)))
    )[1]

    assert ligne == "Kervignarc;Durand;Marie;;0;0,00;0,00;0,00;"
