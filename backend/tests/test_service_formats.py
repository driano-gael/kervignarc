"""Tests du service applicatif Formats de tournoi (E01US023 / ADR-0060 §5) — dépôts factices.

**Écrits depuis la puce « CA — format de tournoi »** de `stories/E01-configuration.md` (règle 9) :
« un format est une brique nommée portant une séquence de modèles de phases ; il ne porte ni statut
ni tournoi ; l'appliquer à un tournoi **crée ses phases** (ordre 1..N, statut `à venir`), qui
restent ensuite ajustables sans altérer le format » — complétée des puces « copie à l'assemblage »
et « promotion », qui valent pour toutes les briques.

`FauxPhaseRepository` et `FauxTournoiRepository` viennent des suites de service existantes : un faux
partagé se déclare une fois.
"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass

import pytest

from application.erreurs import (
    FormatIntrouvable,
    NomFormatDejaPris,
    PhasesEngagees,
    TournoiIntrouvable,
    TournoiSansPhase,
)
from application.formats import ServiceFormats
from domain.bareme import BaremeQualification
from domain.forfait import Forfait
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.patrimoine import OrigineBrique
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
from domain.phase import PhaseId as _PhaseId
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.test_service_blasons import FauxTournoiRepository
from tests.test_service_phases import FauxPhaseRepository


class FauxLecteurForfaits:
    """Réalise le port **étroit** `LecteurForfaitsDePhase` — une seule méthode à écrire.

    Il **filtre réellement** par phase : un faux qui renverrait toujours `[]` ferait passer au vert
    une garde incapable de voir les forfaits pendants, c'est-à-dire exactement le défaut que la
    revue a relevé.
    """

    def __init__(self) -> None:
        self.forfaits: dict[int, list[Forfait]] = {}

    def par_phase(self, phase_id: _PhaseId) -> list[Forfait]:
        return self.forfaits.get(phase_id, [])


_DATE = datetime.date(2026, 3, 14)


class FauxFormatTournoiRepository:
    """Dépôt en mémoire conforme au port `FormatTournoiRepository`.

    `par_nom` compare **exactement**, comme la contrainte `UNIQUE` en base — c'est ce qui rend
    testable l'idempotence de la promotion sans inventer un repli que l'adapter SQL ne fait pas.
    """

    def __init__(self) -> None:
        self._formats: dict[int, FormatTournoi] = {}
        self._sequence = 0

    def ajouter(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        self._sequence += 1
        persiste = dataclasses.replace(format_tournoi, id=self._sequence)
        self._formats[self._sequence] = persiste
        return persiste

    def par_id(self, format_id: FormatTournoiId) -> FormatTournoi | None:
        return self._formats.get(format_id)

    def lister(self) -> list[FormatTournoi]:
        return list(self._formats.values())

    def par_nom(self, nom: str) -> FormatTournoi | None:
        for format_tournoi in self._formats.values():
            if format_tournoi.nom == nom:
                return format_tournoi
        return None

    def enregistrer(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        assert format_tournoi.id in self._formats
        self._formats[format_tournoi.id] = format_tournoi
        return format_tournoi

    def supprimer(self, format_id: FormatTournoiId) -> None:
        del self._formats[format_id]


@dataclass
class Contexte:
    service: ServiceFormats
    tournois: FauxTournoiRepository
    formats: FauxFormatTournoiRepository
    phases: FauxPhaseRepository
    forfaits: FauxLecteurForfaits
    tournoi_id: TournoiId


def _id(valeur: int | None) -> int:
    assert valeur is not None, "un agrégat persisté porte toujours un identifiant"
    return valeur


@pytest.fixture
def ctx() -> Contexte:
    tournois = FauxTournoiRepository()
    formats = FauxFormatTournoiRepository()
    phases = FauxPhaseRepository()
    forfaits = FauxLecteurForfaits()
    tournoi = tournois.ajouter(
        Tournoi.creer(nom="Kervignac 2026", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
    )
    return Contexte(
        service=ServiceFormats(tournois, formats, phases, forfaits),
        tournois=tournois,
        formats=formats,
        phases=phases,
        forfaits=forfaits,
        tournoi_id=_id(tournoi.id),
    )


def _qualification(ordre: int = 1, effectif: int | None = None) -> ModelePhase:
    return ModelePhase.qualification(
        BaremeQualification.preset_ffta_18m(), ordre=ordre, effectif=effectif
    )


# --- CA « bibliothèque » : le format vit hors tournoi ------------------------------------------


def test_creer_un_format_ne_demande_aucun_tournoi(ctx: Contexte) -> None:
    format_tournoi = ctx.service.creer("Mon format", [_qualification()])

    assert format_tournoi.id is not None
    assert ctx.service.lister() == [format_tournoi]


def test_deux_formats_ne_peuvent_pas_porter_le_meme_nom(ctx: Contexte) -> None:
    """Une bibliothèque à homonymes est une bibliothèque où l'on ne sait plus ce qu'on applique."""
    ctx.service.creer("Mon format", [_qualification()])

    with pytest.raises(NomFormatDejaPris):
        ctx.service.creer("Mon format", [_qualification()])


def test_le_prechargement_pose_les_presets_et_reste_rejouable(ctx: Contexte) -> None:
    ctx.service.precharger_presets()
    attendu = len(ctx.service.lister())

    ctx.service.precharger_presets()

    assert attendu > 0
    assert len(ctx.service.lister()) == attendu


def test_le_preset_officiel_est_marque_ffta_le_preset_club_non(ctx: Contexte) -> None:
    """`origine` dit la provenance (ADR-0060 §4) : le format club est maison, pas officiel."""
    ctx.service.precharger_presets()

    origines = {f.nom: f.origine for f in ctx.service.lister()}
    assert origines["FFTA officiel 18 m"] is OrigineBrique.FFTA
    assert origines["Format club"] is OrigineBrique.UTILISATEUR


# --- CA « modifier un officiel : sur place ou en copie » ---------------------------------------


def test_dupliquer_un_officiel_laisse_l_original_intact(ctx: Contexte) -> None:
    ctx.service.precharger_presets()
    officiel = ctx.formats.par_nom("FFTA officiel 18 m")
    assert officiel is not None

    copie = ctx.service.dupliquer(_id(officiel.id), "Ma variante")

    assert copie.origine is OrigineBrique.UTILISATEUR
    assert copie.id != officiel.id
    assert ctx.formats.par_nom("FFTA officiel 18 m") == officiel


def test_modifier_un_officiel_sur_place_le_laisse_officiel(ctx: Contexte) -> None:
    """« Le règlement peut évoluer » — l'issue « intégrer au FFTA officiel »."""
    ctx.service.precharger_presets()
    officiel = ctx.formats.par_nom("FFTA officiel 18 m")
    assert officiel is not None

    modifie = ctx.service.modifier(
        _id(officiel.id),
        "FFTA officiel 18 m",
        [ModelePhase.qualification(BaremeQualification.creer(18, 3))],
    )

    assert modifie.origine is OrigineBrique.FFTA
    assert modifie.etapes[0].bareme == BaremeQualification.creer(18, 3)


# --- CA « appliquer crée les phases du tournoi » -----------------------------------------------


def test_appliquer_cree_les_phases_a_venir_dans_l_ordre(ctx: Contexte) -> None:
    format_tournoi = ctx.service.creer(
        "Deux étapes",
        [
            _qualification(ordre=1, effectif=16),
            ModelePhase(
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),
                effectif=8,
            ),
        ],
    )

    phases = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert [p.ordre for p in phases] == [1, 2]
    assert all(p.statut is StatutPhase.A_VENIR for p in phases)
    assert all(p.tournoi_id == ctx.tournoi_id for p in phases)
    assert ctx.phases.par_tournoi(ctx.tournoi_id) == phases


def test_appliquer_remplace_les_phases_a_venir_existantes(ctx: Contexte) -> None:
    """Reconfigurer un tournoi non engagé ne doit pas empiler deux séquences."""
    ctx.phases.ajouter(
        Phase.qualification(
            ctx.tournoi_id, BaremeQualification.creer(nb_volees=2, nb_fleches_par_volee=3)
        )
    )
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    restantes = ctx.phases.par_tournoi(ctx.tournoi_id)
    assert len(restantes) == 1
    assert restantes[0].bareme == BaremeQualification.preset_ffta_18m()


def test_appliquer_refuse_si_une_phase_est_engagee(ctx: Contexte) -> None:
    """Remplacer un déroulé **en cours**, ce serait jeter les séries qui y pendent."""
    posee = ctx.phases.ajouter(
        Phase.qualification(ctx.tournoi_id, BaremeQualification.preset_ffta_18m())
    )
    ctx.phases.enregistrer(posee.demarrer())
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    with pytest.raises(PhasesEngagees):
        ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))


def test_appliquer_refuse_un_format_inconnu(ctx: Contexte) -> None:
    with pytest.raises(FormatIntrouvable):
        ctx.service.appliquer(ctx.tournoi_id, 404)


def test_appliquer_refuse_un_tournoi_inconnu(ctx: Contexte) -> None:
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    with pytest.raises(TournoiIntrouvable):
        ctx.service.appliquer(404, _id(format_tournoi.id))


def test_ajuster_une_phase_appliquee_n_altere_pas_le_format(ctx: Contexte) -> None:
    """La promesse « ajustable sans altérer le modèle », vue depuis le service."""
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])
    (phase,) = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    ctx.phases.enregistrer(phase.avec_bareme(BaremeQualification.creer(1, 1)))

    relu = ctx.formats.par_id(_id(format_tournoi.id))
    assert relu is not None
    assert relu.etapes[0].bareme == BaremeQualification.preset_ffta_18m()


def test_modifier_le_format_n_altere_pas_un_tournoi_deja_assemble(ctx: Contexte) -> None:
    """L'autre sens — la raison d'être de la copie (ADR-0060 §2)."""
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])
    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    ctx.service.modifier(
        _id(format_tournoi.id),
        "Officiel",
        [ModelePhase.qualification(BaremeQualification.creer(1, 1))],
    )

    (phase,) = ctx.phases.par_tournoi(ctx.tournoi_id)
    assert phase.bareme == BaremeQualification.preset_ffta_18m()


def test_supprimer_un_format_laisse_les_phases_deja_appliquees(ctx: Contexte) -> None:
    """Les phases ne **référencent** pas le format : elles en portent une copie (ADR-0060 §2)."""
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])
    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    ctx.service.supprimer(_id(format_tournoi.id))

    assert len(ctx.phases.par_tournoi(ctx.tournoi_id)) == 1


# --- CA « promotion » --------------------------------------------------------------------------


def test_promouvoir_capture_le_deroule_du_tournoi(ctx: Contexte) -> None:
    ctx.phases.ajouter(
        Phase.qualification(
            ctx.tournoi_id, BaremeQualification.creer(nb_volees=12, nb_fleches_par_volee=3)
        )
    )

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    assert promu.etapes[0].bareme == BaremeQualification.creer(12, 3)
    assert ctx.service.lister() == [promu]


def test_promouvoir_deux_fois_sous_le_meme_nom_met_a_jour(ctx: Contexte) -> None:
    """Idempotence : la bibliothèque ne doit pas accumuler trois « Le format 2026 »."""
    posee = ctx.phases.ajouter(
        Phase.qualification(ctx.tournoi_id, BaremeQualification.creer(12, 3))
    )
    premier = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")
    ctx.phases.enregistrer(posee.avec_bareme(BaremeQualification.creer(20, 3)))

    second = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    assert second.id == premier.id
    assert second.etapes[0].bareme == BaremeQualification.creer(20, 3)
    assert len(ctx.service.lister()) == 1


def test_promouvoir_ne_retroagit_pas_sur_les_tournois_deja_assembles(ctx: Contexte) -> None:
    """Seuls les **prochains** assemblages héritent (ADR-0060 §3)."""
    autre = ctx.tournois.ajouter(
        Tournoi.creer(nom="Édition 2025", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
    )
    ancien_id = _id(autre.id)
    ctx.phases.ajouter(Phase.qualification(ancien_id, BaremeQualification.creer(5, 3)))
    ctx.phases.ajouter(Phase.qualification(ctx.tournoi_id, BaremeQualification.creer(20, 3)))

    ctx.service.promouvoir(ctx.tournoi_id, "Le format du club")

    (phase_ancienne,) = ctx.phases.par_tournoi(ancien_id)
    assert phase_ancienne.bareme == BaremeQualification.creer(5, 3)


def test_promouvoir_un_tournoi_sans_phase_est_refuse(ctx: Contexte) -> None:
    """Il n'y a pas de déroulé à capturer — et un format vide n'aurait rien à appliquer."""
    with pytest.raises(TournoiSansPhase):
        ctx.service.promouvoir(ctx.tournoi_id, "Vide")


def test_promouvoir_oublie_l_avancement(ctx: Contexte) -> None:
    """On promeut un déroulé, pas un état : une phase terminée ne remonte pas « terminée ».

    Le format promu est réappliqué à une **autre** édition — le tournoi d'origine, lui, a une phase
    engagée, et le service refuserait à juste titre d'y remplacer quoi que ce soit.
    """
    posee = ctx.phases.ajouter(
        Phase.qualification(ctx.tournoi_id, BaremeQualification.preset_ffta_18m())
    )
    ctx.phases.enregistrer(posee.demarrer().terminer())
    edition_suivante = _id(
        ctx.tournois.ajouter(
            Tournoi.creer(nom="Édition 2027", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
        ).id
    )

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    phases = ctx.service.appliquer(edition_suivante, _id(promu.id))
    assert all(p.statut is StatutPhase.A_VENIR for p in phases)


def test_supprimer_un_format_inconnu_est_refuse(ctx: Contexte) -> None:
    with pytest.raises(FormatIntrouvable):
        ctx.service.supprimer(404)


def test_les_phases_supprimees_au_remplacement_ne_laissent_pas_de_trace(ctx: Contexte) -> None:
    """Garde-fou de l'implémentation du remplacement : pas d'orphelin dans le dépôt."""
    ancienne = ctx.phases.ajouter(
        Phase.qualification(ctx.tournoi_id, BaremeQualification.creer(2, 3))
    )
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert ctx.phases.par_id(_id(ancienne.id)) is None
