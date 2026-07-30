"""Tests du service applicatif Patrimoine (E01US023 / ADR-0060) — repositories factices.

**Écrits depuis le CA** de `stories/E01-configuration.md` (règle 9), puce par puce :

- *CA — bibliothèque* : catégories et blasons existent sans tournoi ;
- *CA — copie à l'assemblage* : appliquer crée une copie ; modifier la copie n'altère pas le
  modèle ; modifier le modèle n'altère aucun tournoi déjà assemblé ;
- *CA — promotion* : une modification déclarée permanente remonte, **sans** rétroagir sur les
  éditions déjà assemblées ;
- *CA — deux listes séparées* : l'origine distingue l'officiel de la création du club.

Le service est testé **en isolation** : de faux repositories en mémoire suffisent — ni base ni
serveur. `FauxCategorieRepository` vient de `conftest`, `FauxBlasonRepository` et
`FauxTournoiRepository` de `test_service_blasons` (un faux partagé se déclare une fois).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pytest

from application.erreurs import (
    BriqueDejaEnBibliotheque,
    BriqueHorsBibliotheque,
    CategorieIntrouvable,
    TournoiIntrouvable,
)
from application.patrimoine import ServicePatrimoine
from domain.blason import ZONES_DEFAUT, Blason
from domain.patrimoine import OrigineBrique
from domain.tournoi import Tournoi, TypeTournoi
from tests.conftest import FauxCategorieRepository
from tests.test_service_blasons import FauxBlasonRepository, FauxTournoiRepository

_DATE = datetime.date(2026, 3, 14)


@dataclass
class Contexte:
    """Le service et ses trois dépôts, exposés pour observer l'effet des cas d'usage."""

    service: ServicePatrimoine
    tournois: FauxTournoiRepository
    categories: FauxCategorieRepository
    blasons: FauxBlasonRepository

    def tournoi(self, nom: str = "Kervignac 2026") -> int:
        return _id(
            self.tournois.ajouter(
                Tournoi.creer(
                    nom=nom, date=_DATE, lieu="Kervignac", type_tournoi=TypeTournoi.OFFICIEL
                )
            ).id
        )


def _id(valeur: int | None) -> int:
    """Resserre l'identifiant d'un agrégat **persisté** — mypy strict ne le sait pas, le test si."""
    assert valeur is not None, "un agrégat persisté porte toujours un identifiant"
    return valeur


@pytest.fixture
def ctx() -> Contexte:
    tournois = FauxTournoiRepository()
    categories = FauxCategorieRepository()
    blasons = FauxBlasonRepository()
    return Contexte(
        service=ServicePatrimoine(tournois, categories, blasons),
        tournois=tournois,
        categories=categories,
        blasons=blasons,
    )


# --- CA « bibliothèque » -----------------------------------------------------------------------


def test_une_brique_de_bibliotheque_existe_sans_aucun_tournoi(ctx: Contexte) -> None:
    """La promesse de l'atelier : créer sans qu'aucun tournoi n'ait été choisi."""
    blason = ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)

    assert blason.tournoi_id is None
    assert ctx.service.lister_blasons() == [blason]


def test_la_bibliotheque_ignore_les_copies_des_tournois(ctx: Contexte) -> None:
    """Les deux lectures sont **de nature différente** : une copie n'est pas un modèle."""
    tournoi_id = ctx.tournoi()
    ctx.blasons.ajouter(Blason.creer(tournoi_id, "Copie", 1.0, 1))
    modele = ctx.service.creer_blason("Modèle", taille=1.0, capacite=1)

    assert ctx.service.lister_blasons() == [modele]


def test_une_categorie_de_bibliotheque_peut_pointer_un_blason_de_bibliotheque(
    ctx: Contexte,
) -> None:
    blason = ctx.service.creer_blason("Blason 60 cm", taille=0.5, capacite=1)

    categorie = ctx.service.creer_categorie("Benjamin", blason_id=blason.id)

    assert categorie.tournoi_id is None
    assert categorie.blason_id == blason.id


# --- CA « copie à l'assemblage » ---------------------------------------------------------------


def test_assembler_copie_la_bibliotheque_dans_le_tournoi(ctx: Contexte) -> None:
    tournoi_id = ctx.tournoi()
    ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.creer_categorie("Senior 1 Homme")

    rapport = ctx.service.assembler(tournoi_id)

    assert rapport.blasons_copies == 1
    assert rapport.categories_copiees == 1
    assert [b.nom for b in ctx.blasons.par_tournoi(tournoi_id)] == ["Blason 40 cm"]
    assert [c.libelle for c in ctx.categories.par_tournoi(tournoi_id)] == ["Senior 1 Homme"]


def test_assembler_reporte_le_lien_categorie_blason_sur_la_copie_du_tournoi(
    ctx: Contexte,
) -> None:
    """Le piège de la copie : `blason_id` est une **FK**, la recopier telle quelle ferait pointer
    la catégorie du tournoi vers le blason de la **bibliothèque**."""
    tournoi_id = ctx.tournoi()
    modele_blason = ctx.service.creer_blason("Triple 40 cm", taille=0.25, capacite=1)
    ctx.service.creer_categorie("Poulies", blason_id=modele_blason.id)

    ctx.service.assembler(tournoi_id)

    (copie_blason,) = ctx.blasons.par_tournoi(tournoi_id)
    (copie_categorie,) = ctx.categories.par_tournoi(tournoi_id)
    assert copie_categorie.blason_id == copie_blason.id
    assert copie_categorie.blason_id != modele_blason.id


def test_assembler_deux_fois_ne_duplique_pas(ctx: Contexte) -> None:
    """Même régime que `precharger_ffta` : rejouable sans doublonner (dédup par nom)."""
    tournoi_id = ctx.tournoi()
    ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.creer_categorie("Senior 1 Homme")
    ctx.service.assembler(tournoi_id)

    rapport = ctx.service.assembler(tournoi_id)

    assert rapport.blasons_copies == 0
    assert rapport.blasons_ignores == 1
    assert rapport.categories_copiees == 0
    assert rapport.categories_ignorees == 1
    assert len(ctx.blasons.par_tournoi(tournoi_id)) == 1
    assert len(ctx.categories.par_tournoi(tournoi_id)) == 1


def test_modifier_la_copie_n_altere_pas_le_modele(ctx: Contexte) -> None:
    """La promesse centrale de l'US, dans un sens."""
    tournoi_id = ctx.tournoi()
    modele = ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.assembler(tournoi_id)
    (copie,) = ctx.blasons.par_tournoi(tournoi_id)

    ctx.blasons.enregistrer(copie.modifier("Renommé sur le tournoi", 1.0, 2, ZONES_DEFAUT))

    assert ctx.blasons.par_id(_id(modele.id)) == modele


def test_modifier_le_modele_n_altere_pas_un_tournoi_deja_assemble(ctx: Contexte) -> None:
    """L'autre sens — **la raison d'être** de la copie : l'archive de 2026 ne bouge pas si le
    barème change en 2027 (ADR-0060 §2)."""
    tournoi_id = ctx.tournoi()
    modele = ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.assembler(tournoi_id)

    ctx.blasons.enregistrer(modele.modifier("Blason 40 cm", 1.0, 4, ZONES_DEFAUT))

    (copie,) = ctx.blasons.par_tournoi(tournoi_id)
    assert copie.taille == 0.25
    assert copie.capacite == 1


def test_appliquer_un_blason_seul_cree_sa_copie(ctx: Contexte) -> None:
    tournoi_id = ctx.tournoi()
    modele = ctx.service.creer_blason("Blason 80 cm", taille=1.0, capacite=1)

    copie = ctx.service.appliquer_blason(tournoi_id, _id(modele.id))

    assert copie.tournoi_id == tournoi_id
    assert copie.id != modele.id
    assert ctx.blasons.par_bibliotheque() == [modele]


def test_appliquer_une_categorie_entraine_son_blason(ctx: Contexte) -> None:
    """`blason_id` pointe vers un blason **du tournoi** : sans cascade, la copie serait bancale."""
    tournoi_id = ctx.tournoi()
    modele_blason = ctx.service.creer_blason("Blason 60 cm", taille=0.5, capacite=1)
    modele_categorie = ctx.service.creer_categorie("Minime", blason_id=modele_blason.id)

    copie = ctx.service.appliquer_categorie(tournoi_id, _id(modele_categorie.id))

    (copie_blason,) = ctx.blasons.par_tournoi(tournoi_id)
    assert copie.blason_id == copie_blason.id


def test_appliquer_refuse_une_brique_qui_n_est_pas_un_modele(ctx: Contexte) -> None:
    """Viser la copie d'un autre tournoi recopierait le matériau d'une autre édition."""
    tournoi_id = ctx.tournoi()
    autre = ctx.tournoi("Autre tournoi")
    copie_ailleurs = ctx.blasons.ajouter(Blason.creer(autre, "Pas un modèle", 1.0, 1))

    with pytest.raises(BriqueHorsBibliotheque):
        ctx.service.appliquer_blason(tournoi_id, _id(copie_ailleurs.id))


def test_assembler_refuse_un_tournoi_inconnu(ctx: Contexte) -> None:
    with pytest.raises(TournoiIntrouvable):
        ctx.service.assembler(404)


# --- CA « promotion » --------------------------------------------------------------------------


def test_promouvoir_met_a_jour_le_modele_de_bibliotheque(ctx: Contexte) -> None:
    """« Si les modifications sont permanentes, on doit pouvoir le dire. »"""
    tournoi_id = ctx.tournoi()
    modele = ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.assembler(tournoi_id)
    (copie,) = ctx.blasons.par_tournoi(tournoi_id)
    ctx.blasons.enregistrer(copie.modifier("Blason 40 cm", 0.5, 2, ZONES_DEFAUT))

    promu = ctx.service.promouvoir_blason(_id(copie.id))

    assert promu.id == modele.id, "la promotion met à jour le modèle, elle n'en crée pas un second"
    assert promu.tournoi_id is None
    assert promu.taille == 0.5
    assert promu.capacite == 2


def test_promouvoir_ne_retroagit_pas_sur_les_tournois_deja_assembles(ctx: Contexte) -> None:
    """Le pendant exact de la copie : seuls les **prochains** assemblages héritent (ADR-0060 §3)."""
    ancien = ctx.tournoi("Édition 2025")
    nouveau = ctx.tournoi("Édition 2026")
    ctx.service.creer_blason("Blason 40 cm", taille=0.25, capacite=1)
    ctx.service.assembler(ancien)
    ctx.service.assembler(nouveau)
    (copie_nouvelle,) = ctx.blasons.par_tournoi(nouveau)
    ctx.blasons.enregistrer(copie_nouvelle.modifier("Blason 40 cm", 0.5, 1, ZONES_DEFAUT))

    ctx.service.promouvoir_blason(_id(copie_nouvelle.id))

    (copie_ancienne,) = ctx.blasons.par_tournoi(ancien)
    assert copie_ancienne.taille == 0.25, "l'édition passée garde sa copie"


def test_promouvoir_cree_le_modele_s_il_n_existe_pas(ctx: Contexte) -> None:
    """Une brique née dans un tournoi peut entrer au patrimoine sans y avoir d'ancêtre."""
    tournoi_id = ctx.tournoi()
    nee_dans_le_tournoi = ctx.blasons.ajouter(Blason.creer(tournoi_id, "Blason maison", 0.5, 3))

    promu = ctx.service.promouvoir_blason(_id(nee_dans_le_tournoi.id))

    assert promu.tournoi_id is None
    assert promu.nom == "Blason maison"
    assert ctx.service.lister_blasons() == [promu]


def test_promouvoir_une_categorie_relie_le_blason_de_la_bibliotheque(ctx: Contexte) -> None:
    """Symétrique du report de FK à l'assemblage : au retour, le lien doit viser la bibliothèque."""
    tournoi_id = ctx.tournoi()
    modele_blason = ctx.service.creer_blason("Blason 60 cm", taille=0.5, capacite=1)
    ctx.service.creer_categorie("Minime", blason_id=modele_blason.id)
    ctx.service.assembler(tournoi_id)
    (copie,) = ctx.categories.par_tournoi(tournoi_id)

    promue = ctx.service.promouvoir_categorie(_id(copie.id))

    assert promue.blason_id == modele_blason.id


def test_promouvoir_refuse_une_brique_deja_en_bibliotheque(ctx: Contexte) -> None:
    """Geste sans objet : un modèle n'a pas de modèle au-dessus de lui."""
    modele = ctx.service.creer_blason("Déjà un modèle", taille=1.0, capacite=1)

    with pytest.raises(BriqueDejaEnBibliotheque):
        ctx.service.promouvoir_blason(_id(modele.id))


def test_promouvoir_une_categorie_inconnue_est_refuse(ctx: Contexte) -> None:
    with pytest.raises(CategorieIntrouvable):
        ctx.service.promouvoir_categorie(404)


# --- CA « deux listes séparées » ---------------------------------------------------------------


def test_le_prechargement_ffta_alimente_la_bibliotheque_et_marque_l_origine(
    ctx: Contexte,
) -> None:
    """« Le pré-chargement FFTA alimente **la bibliothèque**, une fois pour toutes. »"""
    ctx.service.precharger_ffta()

    blasons = ctx.service.lister_blasons()
    categories = ctx.service.lister_categories()
    assert blasons, "le référentiel officiel doit peupler la bibliothèque"
    assert all(b.tournoi_id is None for b in blasons)
    assert all(b.origine is OrigineBrique.FFTA for b in blasons)
    assert all(c.origine is OrigineBrique.FFTA for c in categories)


def test_le_prechargement_ffta_est_rejouable_sans_doublonner(ctx: Contexte) -> None:
    ctx.service.precharger_ffta()
    attendu = len(ctx.service.lister_categories())

    ctx.service.precharger_ffta()

    assert len(ctx.service.lister_categories()) == attendu


def test_une_creation_manuelle_n_est_pas_marquee_officielle(ctx: Contexte) -> None:
    """`origine` dit la provenance, pas la conformité (ADR-0060 §4)."""
    categorie = ctx.service.creer_categorie("Ma catégorie maison")

    assert categorie.origine is OrigineBrique.UTILISATEUR


def test_les_copies_d_un_tournoi_gardent_l_origine_du_modele(ctx: Contexte) -> None:
    """Assembler ne blanchit pas la provenance : une copie d'officiel reste marquée officielle."""
    tournoi_id = ctx.tournoi()
    ctx.service.precharger_ffta()

    ctx.service.assembler(tournoi_id)

    copies = ctx.categories.par_tournoi(tournoi_id)
    assert copies
    assert all(c.origine is OrigineBrique.FFTA for c in copies)


def test_une_brique_officielle_reste_supprimable(ctx: Contexte) -> None:
    """RG-8 : le référentiel est un **template**, jamais un verrou — modifiable et supprimable."""
    ctx.service.precharger_ffta()
    (premiere, *_) = ctx.service.lister_categories()

    ctx.categories.supprimer(_id(premiere.id))

    assert premiere.id not in {c.id for c in ctx.service.lister_categories()}
