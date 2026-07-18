"""Tests de l'adapter ReportLab (E09US001) — **après** l'implémentation (infra, pas d'oracle).

On prouve que le socle PDF fonctionne : la génération produit un vrai document PDF (en-tête `%PDF`),
tient sur des cas limites (aucun archer, caractères spéciaux dans les noms) et enveloppe ses échecs
en `InfrastructureError` sans laisser fuir d'exception ReportLab brute.
"""

from __future__ import annotations

import pytest

from domain.feuille_marque import FeuilleDeMarque, LigneArcher
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf import GenerateurFeuilleDeMarquePdf


def _feuille(*archers: LigneArcher, nb_volees: int = 20, nb_fleches: int = 3) -> FeuilleDeMarque:
    return FeuilleDeMarque(
        tournoi="Tournoi Test",
        depart_numero=1,
        nb_volees=nb_volees,
        nb_fleches_par_volee=nb_fleches,
        archers=archers,
    )


def test_genere_un_pdf_valide() -> None:
    feuille = _feuille(
        LigneArcher(1, "A", "Durand", "Marie", "Sénior Homme", "Blason 40"),
        LigneArcher(2, "B", "Zola", "Émile", "Sénior Homme", "Blason 40"),
    )

    octets = GenerateurFeuilleDeMarquePdf().generer(feuille)

    assert octets.startswith(b"%PDF")
    assert octets.rstrip().endswith(b"%%EOF")
    assert len(octets) > 1000  # un document non trivial, pas un stub vide


def test_feuille_sans_archer_reste_un_pdf_valide() -> None:
    """Un départ sans plan produit tout de même un document (socle robuste), pas une erreur."""
    octets = GenerateurFeuilleDeMarquePdf().generer(_feuille())

    assert octets.startswith(b"%PDF")


def test_caracteres_speciaux_dans_les_noms_ne_cassent_pas_le_rendu() -> None:
    """`&`, `<`, `>` dans une donnée ne doivent pas casser le balisage des `Paragraph`."""
    feuille = _feuille(LigneArcher(1, "A", "Dupont & <fils>", "Jean-Éric", "Cat <U18>", "Blason"))

    octets = GenerateurFeuilleDeMarquePdf().generer(feuille)

    assert octets.startswith(b"%PDF")


def test_grille_dimensionnee_par_le_bareme() -> None:
    """Une grille plus grande (barème plus long) produit un document plus lourd — la grille suit
    bien le barème passé, pas une taille fixe."""
    generateur = GenerateurFeuilleDeMarquePdf()
    archer = LigneArcher(1, "A", "Durand", "Marie", "Sénior Homme", "Blason 40")

    petite = generateur.generer(_feuille(archer, nb_volees=5, nb_fleches=3))
    grande = generateur.generer(_feuille(archer, nb_volees=40, nb_fleches=6))

    assert len(grande) > len(petite)


def test_echec_de_rendu_enveloppe_en_infrastructure_error() -> None:
    """N'importe quelle défaillance **pendant le rendu** ressort en `InfrastructureError`, jamais en
    exception brute (contrat ADR-0007). On la provoque ici par un `nb_volees` invalide (`None`) qui
    casse la construction de la grille *à l'intérieur* du `try` — honnêtement une `TypeError`, pas
    une panne interne de ReportLab, mais elle exerce bien le seul chemin qui compte : tout ce qui
    lève sous `_rendre` doit être enveloppé. En pratique un barème réel ne peut pas atteindre ce
    point (`BaremeQualification.creer` refuse `< 1`), d'où l'injection d'un `None` mal typé."""
    feuille = FeuilleDeMarque(
        tournoi="T",
        depart_numero=1,
        nb_volees=None,  # type: ignore[arg-type]
        nb_fleches_par_volee=3,
        archers=(LigneArcher(1, "A", "Durand", "Marie", "Cat", "Blason"),),
    )
    with pytest.raises(InfrastructureError):
        GenerateurFeuilleDeMarquePdf().generer(feuille)
