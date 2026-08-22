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
from domain.depart import Depart
from domain.erreurs import PhaseQualificationIncomplete, ProfondeurInvalide
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.patrimoine import OrigineBrique
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase, grain_par_defaut
from domain.phase import PhaseId as _PhaseId
from domain.politiques import ProfondeurClassement
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxPhaseRepository,
    poser_phase_factice,
)
from tests.test_service_blasons import FauxTournoiRepository


class FauxLecteurDonneesDePhase:
    """Réalise le port **étroit** `LecteurDonneesDePhase` — une seule méthode à écrire.

    Il **filtre réellement** par phase, et deux tests l'exercent dans les deux sens (une donnée sur
    la phase visée → refus ; une donnée sur la phase d'un autre tournoi → passage). Sans le second,
    un faux qui renverrait n'importe quoi pour n'importe quel identifiant passerait aussi, et le
    filtrage annoncé ne serait prouvé par rien.

    ⚠️ La première version de ce faux était écrite, câblée, documentée — et **jamais alimentée** :
    la garde qu'il devait protéger pouvait être supprimée en entier sans qu'aucune porte ne bronche.
    C'est le défaut que la revue avait relevé un cran plus haut, reproduit ici.
    """

    def __init__(self) -> None:
        self.par_identifiant: dict[int, list[object]] = {}

    def par_phase(self, phase_id: _PhaseId) -> list[object]:
        return self.par_identifiant.get(phase_id, [])


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
    forfaits: FauxLecteurDonneesDePhase
    placements_tableau: FauxLecteurDonneesDePhase
    tournoi_id: TournoiId
    depart_id: int
    departs: FauxDepartRepository
    deroules: FauxDerouleRepository


def _id(valeur: int | None) -> int:
    assert valeur is not None, "un agrégat persisté porte toujours un identifiant"
    return valeur


@pytest.fixture
def ctx() -> Contexte:
    tournois = FauxTournoiRepository()
    formats = FauxFormatTournoiRepository()
    departs = FauxDepartRepository()
    deroules = FauxDerouleRepository()
    phases = FauxPhaseRepository(departs)
    forfaits = FauxLecteurDonneesDePhase()
    placements_tableau = FauxLecteurDonneesDePhase()
    tournoi = tournois.ajouter(
        Tournoi.creer(nom="Kervignac 2026", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
    )
    assert tournoi.id is not None
    # Appliquer un format crée **une séquence par départ** : sans créneau, il n'y a rien à créer.
    departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    return Contexte(
        service=ServiceFormats(
            tournois, formats, phases, forfaits, placements_tableau, departs, deroules
        ),
        tournois=tournois,
        formats=formats,
        phases=phases,
        forfaits=forfaits,
        placements_tableau=placements_tableau,
        departs=departs,
        deroules=deroules,
        tournoi_id=_id(tournoi.id),
        depart_id=_id(departs.par_tournoi(_id(tournoi.id))[0].id),
    )


def _poser(ctx: Contexte, phase: Phase) -> Phase:
    """Pose l'**étape** puis son avancement dans le créneau — les deux gestes d'ADR-0076.

    Les décors de ce fichier posaient une `Phase` complète en un seul appel. Depuis la séparation
    déroulé / avancement, cela laisserait le tournoi **sans déroulé** : `promouvoir`, qui capture
    la définition, n'y trouverait rien à promouvoir.
    """
    return poser_phase_factice(ctx.departs, ctx.deroules, ctx.phases, phase)


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
                sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),),
                effectif=8,
            ),
        ],
    )

    etapes = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    # `appliquer` rend le **déroulé** (la définition, une fois) — ADR-0076.
    assert [e.ordre for e in etapes] == [1, 2]
    assert all(e.tournoi_id == ctx.tournoi_id for e in etapes)
    # Et il en pose l'**avancement** dans chaque créneau : ici un seul départ, donc deux phases,
    # toutes `à venir`, toutes rattachées à ce créneau.
    phases = ctx.phases.par_tournoi(ctx.tournoi_id)
    assert [p.ordre for p in phases] == [1, 2]
    assert all(p.statut is StatutPhase.A_VENIR for p in phases)
    assert all(p.depart_id == ctx.depart_id for p in phases)


def test_appliquer_recopie_le_minimum_exige_sur_le_tournoi(ctx: Contexte) -> None:
    """E05US021 : le tournoi ne garde aucun lien vers son format — l'exigence doit **voyager**.

    Sans cette copie, la garde de démarrage n'aurait rien à lire : elle ne connaît que le tournoi et
    ses phases.
    """
    format_tournoi = ctx.service.creer(
        "Salle 120", [_qualification(ordre=1)], effectif_minimum_exige=40
    )

    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    tournoi = ctx.tournois.par_id(ctx.tournoi_id)
    assert tournoi is not None
    assert tournoi.effectif_minimum_exige == 40


def test_appliquer_un_format_sans_exigence_efface_la_precedente(ctx: Contexte) -> None:
    """Rechanger de format doit **remplacer** la règle, pas laisser traîner celle d'avant : le
    tournoi porte le déroulé qu'on vient de lui appliquer, exigence comprise."""
    exigeant = ctx.service.creer("Exigeant", [_qualification(ordre=1)], effectif_minimum_exige=40)
    ctx.service.appliquer(ctx.tournoi_id, _id(exigeant.id))

    sobre = ctx.service.creer("Sobre", [_qualification(ordre=1)])
    ctx.service.appliquer(ctx.tournoi_id, _id(sobre.id))

    tournoi = ctx.tournois.par_id(ctx.tournoi_id)
    assert tournoi is not None
    assert tournoi.effectif_minimum_exige is None


def test_promouvoir_fait_remonter_lexigence_du_tournoi(ctx: Contexte) -> None:
    """E05US021 : l'exigence est une propriété du **déroulé** qu'on promeut, pas de l'édition.

    Elle n'est pas lisible depuis les phases — le tournoi la porte —, donc rien ne la ferait
    remonter sans le paramètre explicite de `de_phases`. La fiche de recette liste nommément
    « une exigence qui disparaît après promotion » parmi les défauts à signaler.
    """
    exigeant = ctx.service.creer("Exigeant", [_qualification(ordre=1)], effectif_minimum_exige=40)
    ctx.service.appliquer(ctx.tournoi_id, _id(exigeant.id))

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Déroulé promu")

    assert promu.effectif_minimum_exige == 40


def test_repromouvoir_ne_detruit_pas_lexigence_du_format_existant(ctx: Contexte) -> None:
    """La promotion est **idempotente par nom** : la seconde met à jour la première.

    Un tournoi sans exigence propre ne doit pas, en repassant par là, effacer la règle de club du
    format cible — la promotion capture des *phases*, elle n'exprime rien sur l'exigence.
    """
    sobre = ctx.service.creer("Sobre", [_qualification(ordre=1)])
    ctx.service.appliquer(ctx.tournoi_id, _id(sobre.id))
    ctx.service.promouvoir(ctx.tournoi_id, "Déroulé promu")
    # Le format promu reçoit ensuite une règle de club, réglée à l'atelier.
    promu = ctx.formats.par_nom("Déroulé promu")
    assert promu is not None
    ctx.service.modifier(_id(promu.id), "Déroulé promu", promu.etapes, 40)

    republie = ctx.service.promouvoir(ctx.tournoi_id, "Déroulé promu")

    assert republie.effectif_minimum_exige == 40


def test_appliquer_remplace_les_phases_a_venir_existantes(ctx: Contexte) -> None:
    """Reconfigurer un tournoi non engagé ne doit pas empiler deux séquences."""
    _poser(
        ctx,
        Phase.qualification(
            ctx.depart_id, BaremeQualification.creer(nb_volees=2, nb_fleches_par_volee=3)
        ),
    )
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    restantes = ctx.phases.par_tournoi(ctx.tournoi_id)
    assert len(restantes) == 1
    assert restantes[0].bareme == BaremeQualification.preset_ffta_18m()


def test_appliquer_refuse_si_une_phase_est_engagee(ctx: Contexte) -> None:
    """Remplacer un déroulé **en cours**, ce serait jeter les séries qui y pendent."""
    posee = _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.preset_ffta_18m()))
    ctx.phases.enregistrer(posee.demarrer())
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    with pytest.raises(PhasesEngagees):
        ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))


def test_appliquer_refuse_si_un_forfait_pend_sur_une_phase_a_venir(ctx: Contexte) -> None:
    """Le statut ne suffit pas : `forfait.phase_id` est en `ON DELETE CASCADE`, et un forfait
    déclaré au pointage vit sur une phase encore « à venir ». Le remplacement l'effacerait."""
    posee = _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.preset_ffta_18m()))
    ctx.forfaits.par_identifiant[_id(posee.id)] = [object()]
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    with pytest.raises(PhasesEngagees):
        ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert ctx.phases.par_tournoi(ctx.tournoi_id) == [posee], "la séquence est intacte"


def test_un_forfait_sur_la_phase_d_un_autre_tournoi_ne_bloque_pas(ctx: Contexte) -> None:
    """Le pendant négatif — sans lui, un faux qui répondrait à n'importe quel identifiant passerait
    aussi, et le **filtrage** par phase ne serait prouvé par rien."""
    autre = ctx.tournois.ajouter(
        Tournoi.creer(nom="Autre", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
    )
    depart_ailleurs = _id(
        ctx.departs.ajouter(
            Depart.creer(tournoi_id=_id(autre.id), numero=1, tarif_centimes=800, horaire="09:00")
        ).id
    )
    phase_ailleurs = _poser(
        ctx, Phase.qualification(depart_ailleurs, BaremeQualification.preset_ffta_18m())
    )
    ctx.forfaits.par_identifiant[_id(phase_ailleurs.id)] = [object()]
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    phases = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert len(phases) == 1


def test_appliquer_refuse_si_des_duellistes_sont_poses(ctx: Contexte) -> None:
    """`placement_tableau.phase_id` est aussi en `ON DELETE CASCADE`, et un plan de duels ajusté à
    la main la veille pend sur une phase « à venir » — l'ajustement manuel *est* la fonctionnalité
    (E03US009). La garde le nommait sans le compter ; la revue l'a démontré à l'exécution."""
    posee = _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.preset_ffta_18m()))
    ctx.placements_tableau.par_identifiant[_id(posee.id)] = [object(), object()]
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    with pytest.raises(PhasesEngagees):
        ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert ctx.phases.par_tournoi(ctx.tournoi_id) == [posee]


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
    (etape,) = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    # La définition s'ajuste sur l'**étape** (ADR-0076) : c'est là qu'elle vit désormais.
    ctx.deroules.enregistrer(dataclasses.replace(etape, bareme=BaremeQualification.creer(1, 1)))

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
    _poser(
        ctx,
        Phase.qualification(
            ctx.depart_id, BaremeQualification.creer(nb_volees=12, nb_fleches_par_volee=3)
        ),
    )

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    assert promu.etapes[0].bareme == BaremeQualification.creer(12, 3)
    assert ctx.service.lister() == [promu]


def test_promouvoir_deux_fois_sous_le_meme_nom_met_a_jour(ctx: Contexte) -> None:
    """Idempotence : la bibliothèque ne doit pas accumuler trois « Le format 2026 »."""
    _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.creer(12, 3)))
    premier = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")
    # Le barème s'édite sur l'**étape** (ADR-0076) : le passer à `phases.enregistrer` ne
    # changerait rien, et la seconde promotion recapturerait l'ancien réglage.
    (etape,) = ctx.deroules.par_tournoi(ctx.tournoi_id)
    ctx.deroules.enregistrer(dataclasses.replace(etape, bareme=BaremeQualification.creer(20, 3)))

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
    # L'édition passée a **son** créneau : c'est lui qui porte sa phase (ADR-0075), et c'est par
    # lui que la vue transverse la retrouvera pour vérifier qu'elle n'a pas bougé.
    ancien_depart = _id(
        ctx.departs.ajouter(
            Depart.creer(tournoi_id=ancien_id, numero=1, tarif_centimes=800, horaire="09:00")
        ).id
    )
    _poser(ctx, Phase.qualification(ancien_depart, BaremeQualification.creer(5, 3)))
    _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.creer(20, 3)))

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
    posee = _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.preset_ffta_18m()))
    ctx.phases.enregistrer(posee.demarrer().terminer())
    edition_suivante = _id(
        ctx.tournois.ajouter(
            Tournoi.creer(nom="Édition 2027", date=_DATE, type_tournoi=TypeTournoi.OFFICIEL)
        ).id
    )
    # L'édition suivante a aussi ses créneaux : un format s'applique **à des départs** (ADR-0075).
    ctx.departs.ajouter(
        Depart.creer(tournoi_id=edition_suivante, numero=1, tarif_centimes=800, horaire="09:00")
    )

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    etapes = ctx.service.appliquer(edition_suivante, _id(promu.id))
    # Le déroulé promu se réapplique tel quel ; ses avancements naissent `à venir` dans le créneau.
    assert [e.ordre for e in etapes] == [1]
    assert all(p.statut is StatutPhase.A_VENIR for p in ctx.phases.par_tournoi(edition_suivante))


def test_supprimer_un_format_inconnu_est_refuse(ctx: Contexte) -> None:
    with pytest.raises(FormatIntrouvable):
        ctx.service.supprimer(404)


def test_les_phases_supprimees_au_remplacement_ne_laissent_pas_de_trace(ctx: Contexte) -> None:
    """Garde-fou de l'implémentation du remplacement : pas d'orphelin dans le dépôt."""
    ancienne = _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.creer(2, 3)))
    format_tournoi = ctx.service.creer("Officiel", [_qualification()])

    ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert ctx.phases.par_id(_id(ancienne.id)) is None


def test_appliquer_un_format_incoherent_laisse_la_sequence_intacte(ctx: Contexte) -> None:
    """⚠️ **Régression fermée en revue** : `appliquer` détruisait avant de valider.

    Depuis E01US024 un format incohérent s'enregistre, donc `FormatTournoi.appliquer` peut lever —
    ce qui était impossible avant. Or le service supprimait les phases existantes **d'abord**, et
    les suppressions sont committées (DETTE-025) : le tournoi perdait sa séquence *et* son barème
    de qualification, alors même que l'opération lui était refusée. Les trois gardes de
    `_exiger_sequence_remplacable` ne voyaient rien — c'est l'exception du domaine qui survenait
    après elles.
    """
    tournoi_id = ctx.tournoi_id
    sain = ctx.service.creer("Sain", [_qualification(ordre=1)])
    ctx.service.appliquer(tournoi_id, _id(sain.id))
    avant = ctx.phases.par_tournoi(tournoi_id)
    assert avant, "le préalable du test : le tournoi a bien une séquence à protéger."

    brouillon = ctx.service.creer(
        "Brouillon incohérent", [ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)]
    )

    with pytest.raises(PhaseQualificationIncomplete):
        ctx.service.appliquer(tournoi_id, _id(brouillon.id))

    apres = ctx.phases.par_tournoi(tournoi_id)
    assert [p.ordre for p in apres] == [p.ordre for p in avant]
    assert [p.type for p in apres] == [p.type for p in avant]
    assert [p.bareme for p in apres] == [p.bareme for p in avant]


def test_appliquer_transporte_la_profondeur_du_format_vers_les_phases(ctx: Contexte) -> None:
    """E06US006 : un format composé en classement intégral produit des phases en intégral.

    C'est la moitié « bibliothèque » du CA, et rien ne la couvrait : l'aller-retour de persistance
    des **phases** était testé, celui des **formats** ne l'était pas, ni la propagation
    `ModelePhase → Phase`. Un format enregistré en 1→N pouvait donc rendre des phases au preset
    sans qu'aucun test ne bronche — relevé en revue (axe B).
    """
    format_tournoi = ctx.service.creer(
        "Placement intégral",
        [
            _qualification(ordre=1, effectif=16),
            ModelePhase(
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),),
                effectif=8,
                profondeur=ProfondeurClassement.integrale(),
            ),
        ],
    )

    # Relu depuis le repository : c'est le round-trip de `format_tournoi.config`, la seule table où
    # la clé `depth` cohabite avec le régime `marquer_absences` des brouillons.
    relu = next(f for f in ctx.service.lister() if f.id == format_tournoi.id)
    assert relu.etapes[1].profondeur == ProfondeurClassement.integrale()
    assert relu.etapes[0].profondeur is None

    phases = ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))

    assert phases[1].profondeur == ProfondeurClassement.integrale()
    assert phases[0].profondeur is None


def test_un_brouillon_incoherent_s_enregistre_mais_refuse_de_s_appliquer(ctx: Contexte) -> None:
    """Le régime **brouillon** d'ADR-0063 vaut aussi pour la profondeur (E06US006, ADR-0070 §2).

    Une profondeur posée sur une qualification est un modèle **licite** — un format s'enregistre à
    tout moment — mais `pour_tournoi` construit une vraie `Phase`, dont l'invariant refuse. Ce CA a
    été reversé dans `stories/` au cours de l'US sans qu'aucun test ne l'exerce (relevé en revue).
    """
    format_tournoi = ctx.service.creer(
        "Brouillon incohérent",
        [
            ModelePhase(
                ordre=1,
                type=TypePhase.QUALIFICATION,
                bareme=BaremeQualification.creer(20, 3),
                validation=grain_par_defaut(TypePhase.QUALIFICATION),
                profondeur=ProfondeurClassement.integrale(),
            )
        ],
    )
    relu = next(f for f in ctx.service.lister() if f.id == format_tournoi.id)
    assert relu.etapes[0].profondeur == ProfondeurClassement.integrale()

    with pytest.raises(ProfondeurInvalide):
        ctx.service.appliquer(ctx.tournoi_id, _id(format_tournoi.id))


def test_promouvoir_transporte_la_profondeur_des_phases(ctx: Contexte) -> None:
    """La promotion « ce déroulé devient un format » ne doit pas perdre le réglage.

    Sans elle, un organisateur qui remonte son tournoi en brique de bibliothèque perdrait le
    classement intégral **en silence** — et c'est précisément la boucle que la fiche recommande.
    """
    _poser(
        ctx,
        Phase.creer(
            ctx.depart_id,
            ordre=1,
            type=TypePhase.ELIMINATION_DIRECTE,
            profondeur=ProfondeurClassement.integrale(),
        ),
    )

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Déroulé du jour")

    assert promu.etapes[0].profondeur == ProfondeurClassement.integrale()


def test_promouvoir_capture_le_titre_des_etapes_et_le_rend_a_lapplication(ctx: Contexte) -> None:
    """E16US002 — le titre traverse l'agrégat dans les deux sens (`d_etape` ↔ `pour_tournoi`).

    Ce qui se range en bibliothèque est le **format** (ADR-0060 §5) : un titre perdu à la promotion
    ferait remonter, l'année suivante, des phases anonymes.

    ⚠️ **Ce test ne prouve PAS l'aller-retour persistant, et sa première docstring le prétendait**
    (relevé par trois axes de revue). `ctx` monte un `FauxFormatTournoiRepository` en mémoire : rien
    ici n'atteint `_config_format`, où le titre était **effectivement** perdu à l'écriture. Le test
    était vert pendant que la propriété qu'il annonçait était absente — le mode de panne exact que
    la règle 9 vise. La traversée **persistante** est gardée par
    `test_phase_repository.py::test_un_format_conserve_le_titre_de_ses_etapes`, seul endroit où elle
    se vérifie.
    """
    # Décor posé explicitement : la fixture `ctx` ne pose aucune étape. Une première rédaction
    # portait un `or (None,)` défensif dont la branche « déjà posée » était **morte** — elle faisait
    # croire au lecteur que le décor pouvait déjà porter une étape (relevé en revue).
    _poser(ctx, Phase.qualification(ctx.depart_id, BaremeQualification.creer(12, 3)))
    (etape,) = ctx.deroules.par_tournoi(ctx.tournoi_id)
    ctx.deroules.enregistrer(dataclasses.replace(etape, titre="Qualification des jeunes"))

    promu = ctx.service.promouvoir(ctx.tournoi_id, "Le format 2026")

    assert promu.etapes[0].titre == "Qualification des jeunes"
    # L'autre sens : rejoué sur un tournoi, le format rend son titre.
    assert promu.etapes[0].pour_tournoi(ctx.tournoi_id).titre == "Qualification des jeunes"
