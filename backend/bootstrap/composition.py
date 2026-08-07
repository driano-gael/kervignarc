"""Composition root — câblage explicite de l'application (guide §2.2, ADR-0003).

Point **unique et lisible** où sont assemblés adapters, services applicatifs et routers,
**sans conteneur DI**. `create_app()` construit l'instance FastAPI et branche ses dépendances ;
tout ce qui est câblé est visible ici, en un seul endroit.

Les services applicatifs sont **injectés** dans les routers via `app.state` (pas d'accès
global, pas de magie DI) ; les erreurs typées sont traduites à la frontière API.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import cast

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from api.erreurs import enregistrer_gestionnaires_erreurs
from api.health import router as health_router
from api.realtime import router as realtime_router
from api.realtime_simulation import router as realtime_simulation_router
from api.spa import frontend_dist_dir, monter_spa
from api.v1.archive import router as archive_router
from api.v1.audit import router as audit_router
from api.v1.auth import router as auth_router
from api.v1.bareme_qualification import router as bareme_qualification_router
from api.v1.barrages import router as barrages_router
from api.v1.blasons import router as blasons_router
from api.v1.categories import router as categories_router
from api.v1.clubs import router as clubs_router
from api.v1.competition import router as competition_router
from api.v1.completude import router as completude_router
from api.v1.departs import router as departs_router
from api.v1.deroule import router as deroule_router
from api.v1.documents_salle import router as documents_salle_router
from api.v1.ecrans import router as ecrans_router
from api.v1.ecrans import session_router as ecran_session_router
from api.v1.feuille_de_marque import router as feuille_de_marque_router
from api.v1.forfaits import router as forfaits_router
from api.v1.formats import router as formats_router
from api.v1.gabarits import router as gabarits_router
from api.v1.grain_validation import router as grain_validation_router
from api.v1.inscriptions import router as inscriptions_router
from api.v1.jeu_essai import router as jeu_essai_router
from api.v1.listes_impression import router as listes_impression_router
from api.v1.paiements import router as paiements_router
from api.v1.palmares import router as palmares_router
from api.v1.patrimoine import router as patrimoine_router
from api.v1.phases import router as phases_router
from api.v1.pilotage import router as pilotage_router
from api.v1.placement import router as placement_router
from api.v1.placement_duels import router as placement_duels_router
from api.v1.postes import router as postes_router
from api.v1.postes import session_router as poste_session_router
from api.v1.remboursements import router as remboursements_router
from api.v1.routage import router as routage_router
from api.v1.saisie import router as saisie_router
from api.v1.saisie_duels import router as saisie_duels_router
from api.v1.scoreurs import router as scoreurs_router
from api.v1.scoreurs import session_router as scoreur_session_router
from api.v1.simulation import router as simulation_router
from api.v1.suivi_deroule import router as suivi_deroule_router
from api.v1.supervision import heartbeat_router as poste_heartbeat_router
from api.v1.supervision import router as supervision_router
from api.v1.tableaux import router as tableaux_router
from api.v1.tournois import router as tournois_router
from application.archers import ServiceArchers
from application.archive import ServiceArchive
from application.audit import ServiceAudit
from application.auth import ServiceAuth
from application.bareme_qualification import ServiceBaremeQualification
from application.barrages import ServiceBarrage
from application.blasons import ServiceBlasons
from application.categories import ServiceCategories
from application.classements import ServiceClassement
from application.clubs import ServiceClubs
from application.completude import ServiceCompletude
from application.departs import ServiceDeparts
from application.documents_salle import ServiceDocumentsSalle
from application.ecrans import ServiceEcrans
from application.feuille_de_marque import ServiceFeuilleDeMarque
from application.forfaits import ServiceForfait
from application.formats import ServiceFormats
from application.gabarits import ServiceGabarits
from application.generateur_scores import GenerateurScoresPlausibles
from application.grain_validation import ServiceGrainValidation
from application.inscriptions import ServiceInscriptions
from application.jeu_essai import ServiceJeuEssai
from application.listes_impression import ServiceListesImpression
from application.paiements import ServicePaiements
from application.palmares import ServicePalmares
from application.patrimoine import ServicePatrimoine
from application.phases import ServicePhases
from application.pilotage_simulation import (
    RegistreSessionsSimulation,
    ServicePilotageSimulation,
)
from application.pilotage_tour import ServicePilotageTour
from application.placement import ServicePlacement
from application.placement_duels import ServicePlacementDuels
from application.postes import ServicePostes
from application.remboursements import ServiceRemboursements
from application.routage import ServiceRoutage
from application.saisie import ServiceSaisie
from application.saisie_duels import ServiceSaisieDuels
from application.scoreurs import ServiceScoreurs
from application.simulation import HarnaisSimulation, ServiceSimulation
from application.simulation_format import ServiceSimulationFormat
from application.suivi_deroule import CompteurEngagesRepository, ServiceSuiviDeroule
from application.supervision import ServiceSupervision
from application.tableaux_publics import ServiceTableauxPublics
from application.tournois import ServiceTournois
from domain.duel import ResolveurBaremeDuelFfta
from domain.politiques import (
    Aggregation,
    ByesAuxMieuxClasses,
    FamillePolitique,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from infrastructure.archive.constructeur import ConstructeurArchiveZip
from infrastructure.auth import AdminCredentialsStore, SessionStore, default_env_path
from infrastructure.backup.config import (
    dossier_sauvegardes,
    intervalle_secondes,
    retention,
)
from infrastructure.backup.sauvegarde import SauvegardeSQLite
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BarrageRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    Database,
    DepartRepositorySQL,
    DerouleEtapeRepositorySQL,
    DuelRepositorySQL,
    ForfaitRepositorySQL,
    FormatTournoiRepositorySQL,
    GabaritSalleRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    PlacementRepositorySQL,
    PlacementTableauRepositorySQL,
    PosteRepositorySQL,
    RemboursementRepositorySQL,
    ScoreRepositorySQL,
    ScoreurRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
    WriteQueue,
    default_database_url,
)
from infrastructure.horloge import HorlogeSysteme
from infrastructure.idempotence import RegistreIdempotence
from infrastructure.memory.repositories import (
    InMemoryArcherRepository,
    InMemoryBlasonRepository,
    InMemoryCategorieRepository,
    InMemoryDepartRepository,
    InMemoryDerouleRepository,
    InMemoryDuelRepository,
    InMemoryForfaitRepository,
    InMemoryGabaritSalleRepository,
    InMemoryInscriptionRepository,
    InMemoryPhaseRepository,
    InMemoryPlacementTableauRepository,
    InMemorySerieRepository,
    InMemoryTournoiRepository,
)
from infrastructure.pdf import (
    GenerateurDocumentsSallePdf,
    GenerateurFeuilleDeMarquePdf,
    GenerateurListesImpressionPdf,
    GenerateurPalmaresPdf,
)
from infrastructure.postes import (
    PosteSessionStore,
    RegistreConsignesMemoire,
    RegistrePresenceMemoire,
    generer_code_poste,
)
from infrastructure.realtime import Broadcaster, DiffusionSimulationBroadcaster, LiveEvent
from infrastructure.scoreurs import ScoreurSessionStore, generer_code_scoreur

_logger = logging.getLogger(__name__)

_SEUIL_POSTE_HORS_LIGNE_S = 30.0
"""Un poste sans heartbeat depuis plus de ce délai est réputé **hors ligne** (E12US001, ADR-0038).

Doit rester **strictement supérieur** à l'intervalle de heartbeat du front (~10 s), avec de la marge
pour absorber un ping manqué — sinon les postes clignoteraient (faux hors-ligne). Les deux valeurs
sont liées : les changer, c'est les changer ensemble (front + serveur).
"""


def fabriquer_harnais_simulation() -> HarnaisSimulation:
    """Fabrique un harnais de simulation **neuf** : adapters in-memory + services moteur câblés.

    Source **unique** du harnais (E15US002, ADR-0054) : mêmes services (`ServiceClassement`,
    `ServicePlacementDuels`, `ServiceSaisieDuels`) et **mêmes** politiques par défaut que la
    production, mais sur des magasins `dict` jetables. Hissée hors de `create_app` pour être
    **importable** — la composition root **et** les tests consomment cette même fonction, si bien
    que le harnais éprouvé par les tests **est** celui déployé (pas une copie qui dériverait en
    silence). Un harnais neuf par appel : aucune fuite d'état entre deux simulations.
    """
    tournois = InMemoryTournoiRepository()
    archers = InMemoryArcherRepository()
    categories = InMemoryCategorieRepository()
    blasons = InMemoryBlasonRepository()
    gabarits = InMemoryGabaritSalleRepository()
    inscriptions = InMemoryInscriptionRepository()
    # Les créneaux du harnais (E01US025, ADR-0075) : la portée sportive étant le départ, le
    # magasin de phases a besoin d'eux pour sa lecture transverse `par_tournoi`.
    departs = InMemoryDepartRepository()
    # Le déroulé du tournoi simulé (ADR-0076) : le magasin de phases s'en sert pour **assembler**
    # définition et avancement, exactement comme l'adapter SQL.
    deroules = InMemoryDerouleRepository()
    phases = InMemoryPhaseRepository(departs, deroules)
    series = InMemorySerieRepository()
    forfaits = InMemoryForfaitRepository()
    duels = InMemoryDuelRepository()
    placements_tableau = InMemoryPlacementTableauRepository()
    classement = ServiceClassement(
        tournois, archers, series, categories, phases, forfaits, departs, inscriptions
    )
    # **Un seul** registre pour les deux services (E06US006) : c'est lui qui résout la profondeur
    # lue sur chaque phase, et deux catalogues distincts laisseraient croire qu'ils divergent.
    registre = registre_par_defaut()
    placement_duels = ServicePlacementDuels(
        tournois,
        phases,
        gabarits,
        inscriptions,
        archers,
        categories,
        blasons,
        placements_tableau,
        classement,
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        registre,
    )
    saisie_duels = ServiceSaisieDuels(
        tournois,
        phases,
        categories,
        blasons,
        duels,
        forfaits,
        classement,
        ResolveurBaremeDuelFfta(),
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        registre,
    )
    return HarnaisSimulation(
        tournois,
        archers,
        categories,
        blasons,
        gabarits,
        inscriptions,
        departs,
        deroules,
        phases,
        series,
        classement,
        placement_duels,
        saisie_duels,
    )


def create_app(
    database_url: str | None = None,
    *,
    frontend_dist: Path | None = None,
    admin_env_path: Path | None = None,
) -> FastAPI:
    """Assemble et renvoie l'application FastAPI entièrement câblée.

    `database_url` : surcharge l'URL de la base (tests) ; sinon configuration applicative
    (variable d'environnement KERVIGNARC_DATABASE_URL, sinon défaut local).
    `frontend_dist` : surcharge le répertoire du build front à servir (tests) ; sinon
    résolu par défaut (`frontend/dist/`). Non monté s'il n'existe pas (E00US012).
    `admin_env_path` : surcharge le fichier `.env` des identifiants admin (tests) ; sinon
    résolu par défaut (variable KERVIGNARC_ENV_FILE, sinon `.env` local) (E10US002).
    """
    # --- Adapters sortants (infrastructure) : connexion SQLite WAL (E00US006). ---
    # Les repositories (E00US009) consommeront ce Database pour leurs lectures.
    database = Database(database_url or default_database_url())

    # File d'écriture (E00US007) : sérialise les écritures via un writer unique
    # (ADR-0005) ; démarrée/arrêtée avec le cycle de vie de l'app (lifespan ci-dessous).
    write_queue = WriteQueue()

    # Diffusion temps réel (E00US008) : hub d'abonnés WebSocket. La diffusion est
    # déclenchée **depuis le writer** — un listener post-commit publie tout LiveEvent
    # renvoyé par une commande d'écriture réussie (point de passage unique, ADR-0005).
    broadcaster = Broadcaster()

    # Canal de diffusion **isolé** de la simulation (E15US003, ADR-0055 §5) : un second hub,
    # distinct du temps réel réel, servi par `/ws/simulation`. Aucune écriture simulée ne passe
    # par la file, donc le canal réel reste muet pendant une simulation, et réciproquement —
    # l'isolement est structurel (deux hubs), pas un filtrage sur un canal partagé.
    broadcaster_simulation = Broadcaster()

    def _diffuser_apres_ecriture(result: object) -> None:
        # Walking skeleton (E00US011) : diffusion à **gros grain**. Une commande peut
        # renvoyer un LiveEvent typé (diffusé tel quel) ; à défaut, toute écriture réussie
        # émet un événement générique « données modifiées » invitant les clients à se
        # resynchroniser (le front invalide alors ses requêtes React Query). Les US métier
        # affineront en événements ciblés par sujet/tournoi (CDC §6.2).
        if isinstance(result, LiveEvent):
            broadcaster.publish(result)
        else:
            broadcaster.publish(LiveEvent("donnees_modifiees"))

    write_queue.add_post_commit_listener(_diffuser_apres_ecriture)

    # Sauvegarde périodique (E11US003, ADR-0044) : dépose une copie horodatée cohérente de la base
    # dans un dossier local, avec rétention simple. Une sauvegarde est une **lecture** (API sqlite3
    # backup) : elle ne passe donc **pas** par la file d'écriture (règle 7 — seules les écritures y
    # transitent) et s'exécute hors boucle dans un threadpool. Le paramétrage (intervalle,
    # rétention, dossier) vient de variables d'environnement (`infrastructure/backup/config.py`).
    intervalle_backup = intervalle_secondes()
    sauvegarde = SauvegardeSQLite(
        Path(database.engine.url.database or ""),
        dossier_sauvegardes(),
        retention(),
        HorlogeSysteme(),
    )

    async def _boucle_sauvegarde() -> None:
        # Première copie **après** un intervalle (jamais au démarrage) : ainsi une app montée le
        # temps d'un test — qui vit bien moins que l'intervalle — n'écrit aucune sauvegarde.
        # Best-effort : un échec est journalisé et la boucle continue.
        while True:
            await asyncio.sleep(intervalle_backup)
            try:
                await run_in_threadpool(sauvegarde.sauvegarder)
            except Exception:
                _logger.exception("Sauvegarde périodique en échec (la boucle continue).")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Cycle de vie : broadcaster + worker + tâche de sauvegarde périodique."""
        broadcaster.bind_loop(asyncio.get_running_loop())
        broadcaster_simulation.bind_loop(asyncio.get_running_loop())
        write_queue.start()
        # `intervalle <= 0` désactive la sauvegarde (aucune tâche lancée).
        tache_sauvegarde = (
            asyncio.create_task(_boucle_sauvegarde()) if intervalle_backup > 0 else None
        )
        try:
            yield
        finally:
            if tache_sauvegarde is not None:
                tache_sauvegarde.cancel()
                with suppress(asyncio.CancelledError):
                    await tache_sauvegarde
            write_queue.stop()
            broadcaster.unbind_loop()
            broadcaster_simulation.unbind_loop()

    app = FastAPI(title="Kervignarc", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.state.write_queue = write_queue
    app.state.broadcaster = broadcaster
    app.state.broadcaster_simulation = broadcaster_simulation

    # --- Services applicatifs (E00US009) : repository (adapter) → service, injectés via state. ---
    # Le repository lit via les sessions courtes du Database ; les écritures du service passent
    # par la file d'écriture (routage assuré côté router API).
    tournoi_repository = TournoiRepositorySQL(database.session_factory)
    categorie_repository = CategorieRepositorySQL(database.session_factory)
    blason_repository = BlasonRepositorySQL(database.session_factory)
    club_repository = ClubRepositorySQL(database.session_factory)
    gabarit_repository = GabaritSalleRepositorySQL(database.session_factory)
    format_repository = FormatTournoiRepositorySQL(database.session_factory)
    deroule_repository = DerouleEtapeRepositorySQL(database.session_factory)
    phase_repository = PhaseRepositorySQL(database.session_factory)
    archer_repository = ArcherRepositorySQL(database.session_factory)
    score_repository = ScoreRepositorySQL(database.session_factory)
    depart_repository = DepartRepositorySQL(database.session_factory)
    scoreur_repository = ScoreurRepositorySQL(database.session_factory)
    poste_repository = PosteRepositorySQL(database.session_factory)
    audit_repository = AuditRepositorySQL(database.session_factory)
    # L'inscription co-écrit sa trace de **paiement** (E08US002) dans une seule transaction
    # (ADR-0035) : l'adapter reçoit l'`audit_repository` (concret) pour `consigner_dans` sur la
    # session partagée — couplage **infra → infra**, comme la saisie et le placement.
    inscription_repository = InscriptionRepositorySQL(database.session_factory, audit_repository)
    # Registre de remboursements (E08US005, ADR-0057) : le traitement (marquer remboursé/reporté)
    # co-écrit sa trace `REMBOURSEMENT` dans une seule transaction (ADR-0035) — d'où
    # l'`audit_repository`
    # (concret) injecté, couplage **infra → infra** comme l'inscription et le placement. La
    # *création*
    # d'un poste, elle, se fait à la suppression d'une inscription payée (via les repos ci-dessus).
    remboursement_repository = RemboursementRepositorySQL(
        database.session_factory, audit_repository
    )
    # Le plan de cibles co-écrit sa trace d'audit d'une régénération **massive** dans une seule
    # transaction (E12US007, ADR-0035, ADR-0040) : l'adapter reçoit l'`audit_repository` (concret)
    # pour `consigner_dans` sur la session partagée — couplage **infra → infra**, comme la saisie.
    placement_repository = PlacementRepositorySQL(database.session_factory, audit_repository)
    placement_tableau_repository = PlacementTableauRepositorySQL(database.session_factory)
    duel_repository = DuelRepositorySQL(database.session_factory)
    # Forfaits — abandon / DSQ (E04US015, ADR-0050) : co-écrivent leur trace d'audit `FORFAIT` dans
    # une seule transaction (ADR-0035), d'où l'`audit_repository` (concret) injecté — couplage
    # infra → infra, comme la série, l'inscription et le placement.
    forfait_repository = ForfaitRepositorySQL(database.session_factory, audit_repository)
    # La série de saisie co-écrit son entrée d'audit dans **une seule transaction** (ADR-0035) :
    # l'adapter reçoit l'`audit_repository` (concret) pour appeler `consigner_dans` sur la session
    # partagée. Couplage **infra → infra** assumé — le port domaine `SerieRepository` l'ignore.
    # L'`Horloge` date le `created_at` des volées (métadonnée de persistance, le « quand » ex-017).
    serie_repository = SerieRepositorySQL(
        database.session_factory, audit_repository, HorlogeSysteme()
    )
    # Le compteur d'engagés (archers distincts, tous départs confondus) est monté **ici** parce que
    # deux services le lisent : la garde de démarrage d'E05US021 (juste en dessous) et le suivi de
    # déroulé (plus bas). Une seule instance, pour que « combien sommes-nous » ait une seule
    # définition — deux comptes divergents seraient invisibles et faux au même endroit.
    compteur_engages = CompteurEngagesRepository(depart_repository, inscription_repository)
    # `ServiceTournois` lit aussi les **départs** (port `depart_repository`) : le passage à `prêt`
    # exige au moins un créneau (garde `TournoiSansDepart`, E02US010). Depuis E05US021 il lit en
    # plus les **phases** et les **engagés** : démarrer exige assez d'inscrits pour que le déroulé
    # composé puisse se dérouler ([ADR-0069]).
    app.state.service_tournois = ServiceTournois(
        tournoi_repository, depart_repository, phase_repository, compteur_engages
    )
    # `service_departs` est câblé **plus bas**, après `service_completude` : son garde-fou de cycle
    # (E12US008) dépend du port étroit `LecteurAvancementDepart`, que réalise `ServiceCompletude`.
    # Catégories ↔ blasons se référencent mutuellement (E01US006) : la catégorie valide son
    # blason par défaut, le blason refuse sa suppression s'il est référencé. Chaque service ne
    # dépend que des **ports** repository (pas de l'autre service).
    app.state.service_categories = ServiceCategories(
        tournoi_repository, categorie_repository, blason_repository
    )
    app.state.service_blasons = ServiceBlasons(
        tournoi_repository, blason_repository, categorie_repository
    )
    # Référentiel des clubs (E02US001) : **global**, réutilisé d'une compétition à l'autre — seul
    # service à ne dépendre d'aucun tournoi. Clubs ↔ archers se référencent mutuellement, comme
    # catégories ↔ blasons : l'archer valide son club de rattachement, le club refuse sa
    # suppression s'il est référencé. Chaque service ne dépend que des **ports** repository (jamais
    # de l'autre service) — pas de cycle entre services.
    app.state.service_clubs = ServiceClubs(club_repository, archer_repository)
    # Gabarits de salle : bibliothèque de modèles (E01US007) + application à un tournoi (E01US008,
    # copie ajustable). Le service vérifie l'existence du tournoi (dépend du port tournoi).
    app.state.service_gabarits = ServiceGabarits(tournoi_repository, gabarit_repository)
    # Patrimoine du club (E01US023, ADR-0060) : la **bibliothèque** de briques hors tournoi,
    # l'assemblage d'un tournoi (copie) et la promotion (retour). Service **distinct** de
    # `service_categories` / `service_blasons`, qui restent cantonnés au périmètre d'un
    # tournoi : copier une catégorie exige de réattacher son `blason_id` à la copie du blason
    # du même tournoi — une règle qui traverse les **deux** collections, qu'aucun des deux
    # services existants ne voit en entier.
    app.state.service_patrimoine = ServicePatrimoine(
        tournoi_repository, categorie_repository, blason_repository
    )
    # Formats de tournoi (E01US023, ADR-0060 §5) : la brique « déroulé ». Traverse deux ports
    # — le sien et celui des **phases** — parce que la copie d'un format dans un tournoi n'est
    # pas un format rattaché, ce sont ses phases.
    # `forfait_repository` **et** `placement_tableau_repository` : la garde d'application d'un
    # format regarde ce qui **pend** aux phases, pas seulement leur statut. Un forfait déclaré au
    # pointage et un plan de duels ajusté à la main vivent tous deux sur des phases encore
    # `à venir`, et les deux FK sont en `ON DELETE CASCADE` — le remplacement les détruisait en
    # silence (revue E01US023, démontré à l'exécution).
    app.state.service_formats = ServiceFormats(
        tournoi_repository,
        format_repository,
        phase_repository,
        forfait_repository,
        placement_tableau_repository,
        depart_repository,
        deroule_repository,
    )
    # Barème de qualification (E01US009) : porté par la phase `qualification` du tournoi
    # (introduction minimale de `Phase`, ADR-0011). Le service vérifie l'existence du tournoi.
    app.state.service_bareme_qualification = ServiceBaremeQualification(
        tournoi_repository, phase_repository, depart_repository, deroule_repository
    )
    # Grain de validation (E01US015, `D-11`) : porté par la même **étape de déroulé** que le
    # barème, à la racine de sa `config` (`config.validation`) — ce n'est pas une politique de
    # moteur, il reste hors `config.policies` où E05US003 a rangé le barème (ADR-0046), sans
    # changement de schéma. Le port injecté est le **déroulé** et non les phases : depuis ADR-0076,
    # écrire une définition par `PhaseRepository` ne déplacerait rien.
    app.state.service_grain_validation = ServiceGrainValidation(
        tournoi_repository, deroule_repository
    )
    # Séquence de phases (E05US001, ADR-0045) : composer/éditer/ordonner/supprimer les phases d'un
    # tournoi et faire vivre leur cycle de vie. Le service vérifie l'existence du tournoi et arbitre
    # les conflits d'état ; la cohérence de la séquence (source, ordres) est une règle du domaine
    # (`SequencePhases`). Même port `phase_repository` que le barème/grain (une table `phase`).
    app.state.service_phases = ServicePhases(
        tournoi_repository, phase_repository, depart_repository, deroule_repository
    )
    # Registre des politiques injectables (E05US003, ADR-0004/ADR-0046) : le catalogue
    # nom → implémentation par famille (routing/scoring/seeding/byes/tiebreak/depth), peuplé **ici**
    # (règle 2 : le domaine définit les stratégies, la composition root les assemble). C'est le
    # socle qu'`assembler_politiques` consomme pour résoudre la `config.policies` d'une phase ; le
    # **moteur** qui l'exploite (dimensionnement/génération d'arbre) arrive en E05US005/E05US010.
    # On pourrait enregistrer ici des implémentations supplémentaires sans toucher au domaine.
    app.state.registre_politiques = registre_par_defaut()
    # Inscription d'un archer (E02US002) : le service valide le tournoi, sa **catégorie** (qui doit
    # être du même tournoi) et son club de rattachement s'il est fourni — d'où quatre ports pour un
    # seul agrégat. Le club reste facultatif (`NULL` = inconnu, ADR-0014), la catégorie non.
    # Le port inscription est injecté pour l'« engagé » élargi (E02US009) : un archer inscrit sur au
    # moins un départ est engagé, sa suppression se signale et efface ses inscriptions.
    # `serie_repository` porte « l'archer a-t-il tiré ? » (DETTE-013) : les gardes d'engagement
    # (suppression, changement de catégorie) dérivent de la vraie saisie (`Serie`, E04US002), plus
    # de l'agrégat `Score` que plus aucun flux produit n'alimente. `score_repository` ne sert plus
    # qu'au `saisir_score` du walking skeleton (endpoint sans appelant produit — DETTE-011).
    app.state.service_archers = ServiceArchers(
        tournoi_repository,
        archer_repository,
        score_repository,
        club_repository,
        categorie_repository,
        inscription_repository,
        serie_repository,
    )
    # Classement de qualification (E06US001) : lit les **séries** de saisie (E04US002), plus les
    # catégories pour libeller/segmenter — le walking skeleton `Score` ne portait pas le détail
    # flèche par flèche qu'exige le départage FFTA (nombre de 10 puis de 9).
    # E04US015 (ADR-0050) : le classement lit les forfaits **de la phase de qualification** — un
    # abandon y est **relégué**, une DSQ **exclue** (rang `None`), leurs flèches préservées. D'où le
    # port `phase` (résoudre la phase de qualif) et le port `forfait`.
    # E06US003 (ADR-0066) : le classement résout sa politique de départage **par le registre**
    # (seuil de barrage lu dans `config.policies.tiebreak`) et applique les verdicts des barrages
    # déjà tirés. Sans seuil réglé, il retombe mot pour mot sur E06US001 — ex æquo partagés.
    barrage_repository = BarrageRepositorySQL(database.session_factory)
    app.state.service_classement = ServiceClassement(
        tournoi_repository,
        archer_repository,
        serie_repository,
        categorie_repository,
        phase_repository,
        forfait_repository,
        depart_repository,
        inscription_repository,
        barrage_repository,
        app.state.registre_politiques,
    )
    # Organisation du barrage : annoncer sur une égalité **signalée par le classement** (jamais
    # recalculée ici, sous peine d'une seconde version qui dériverait), saisir ses manches, clore.
    app.state.service_barrage = ServiceBarrage(
        tournoi_repository,
        barrage_repository,
        app.state.service_classement,
        HorlogeSysteme(),
        archer_repository,
        phase_repository,
    )
    # Inscriptions archer↔départ (E02US009, ADR-0017) : inscrire sur des créneaux du tournoi de
    # l'archer (même tournoi, unicité), marquer payé, désinscrire ; le montant dû dérive du tarif.
    # `HorlogeSysteme` **date** l'ouverture d'un remboursement quand une désinscription paye est
    # confirmée (E08US005) : la désinscription supprime l'inscription **et** ouvre sa contrepartie
    # en une transaction (`supprimer_avec_remboursement`).
    app.state.service_inscriptions = ServiceInscriptions(
        inscription_repository, archer_repository, depart_repository, HorlogeSysteme()
    )
    # Traitement des remboursements (E08US005, ADR-0057) : lister les postes à traiter et les
    # marquer
    # remboursé/reporté (audité, `Horloge` date la trace `REMBOURSEMENT`). La création vit ailleurs
    # (suppression d'inscription payée) — ce service ne fait que consulter et clore.
    app.state.service_remboursements = ServiceRemboursements(
        remboursement_repository, tournoi_repository, HorlogeSysteme()
    )
    # Suivi des paiements (E08US002) : consulter (par archer, par club) et **marquer** le statut
    # (simple, par archer, par club — tout audité). Dérive dû/payé/reste du booléen `paye` par
    # inscription et des tarifs (E08US001, ADR-0017) ; le club sert les totaux et le bucket « sans
    # club » (ADR-0014). `HorlogeSysteme` date la trace `PAIEMENT` ; l'atomicité acte↔trace est dans
    # l'adapter d'inscription (ADR-0035). Le marquage a **quitté** `ServiceInscriptions` : une seule
    # voie d'écriture du paiement, toute tracée.
    app.state.service_paiements = ServicePaiements(
        tournoi_repository,
        archer_repository,
        depart_repository,
        inscription_repository,
        club_repository,
        HorlogeSysteme(),
    )
    # Placement (E03US001 lecture ; E03US004 matérialisation + ajustement, ADR-0024). Le service
    # joint archer → catégorie → blason par défaut pour nourrir le moteur pur (`domain/placement`),
    # d'où sept ports de jointure/gardes, **plus** le port `placement` qui persiste le plan
    # (matérialisé, ajustable au glisser-déposer). Les écritures (régénérer/déplacer/échanger/placer
    # les restants) passent par la file (routage API).
    # E12US007 (ADR-0040) : `serie_repository` alimente le **calcul d'impact** (« quelles cibles ont
    # des scores ») et `HorlogeSysteme` **date** la trace d'audit d'une régénération massive.
    app.state.service_placement = ServicePlacement(
        tournoi_repository,
        depart_repository,
        gabarit_repository,
        inscription_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        placement_repository,
        serie_repository,
        HorlogeSysteme(),
    )
    # Plan de duels (E03US009, ADR-0048) : placer les duellistes d'une phase de tableau côte à côte,
    # matérialisé par phase et ajustable au glisser-déposer. Assemble le classement (recalculé) →
    # l'arbre (`construire_tableau`, politiques par défaut : serpent / byes aux mieux classés /
    # placement en cascade) → les paires du 1er tour → le placement réordonné pour l'adjacence.
    # Réutilise `service_classement` (source d'ensemencement) ; scoppé par **phase** (≠ départ).
    #
    # ⚠️ **`PlacementEnCascade` et non `EliminationSeche`** (E05US010, ADR-0061), malgré le nom :
    # le format livré ici a une **petite finale**, donc les perdants des demies rejouent — ce n'est
    # pas une élimination sèche mais un placement **tronqué au rang 4**. C'est la paire
    # `PlacementEnCascade` + `ProfondeurPodium()` qui le dit, et les deux sont injectées **ici** :
    # le `routing` décide *où* descend un perdant, la `depth` *jusqu'où* l'on descend. L'arbre
    # produit est **identique** à celui d'avant l'US ; c'est le vocabulaire qui se met en accord
    # avec le comportement.
    #
    # ⚠️ **La profondeur n'est plus injectée ici depuis E06US006** ([ADR-0070]). Elle était figée à
    # `ProfondeurPodium()` sur cette ligne, en attendant « le levier qu'E01US024 exposera à
    # l'organisateur phase par phase » — E01US024 a livré le composeur de déroulé sans lui, et
    # E06US006 hérite donc de la promesse. Chaque phase porte désormais sa profondeur
    # (`Phase.profondeur`), résolue **par le registre** (`profondeur_de`) ; ce qui s'injecte ici est
    # le **catalogue**, pas le choix. Une phase qui ne règle rien retombe sur le preset de son type,
    # le podium — soit exactement ce que cette ligne câblait, pour que rien de déjà joué ne bouge.
    #
    # [ADR-0070]: ../../docs/adr/0070-profondeur-de-classement-reglee-par-phase.md
    app.state.service_placement_duels = ServicePlacementDuels(
        tournoi_repository,
        phase_repository,
        gabarit_repository,
        inscription_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        placement_tableau_repository,
        app.state.service_classement,
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        app.state.registre_politiques,
    )
    # Saisie en duels (E04US013, ADR-0049) : reconstruit le même arbre (classement → tableau) et
    # **rejoue** les duels validés pour la progression. Le barème est résolu par arme via le
    # résolveur FFTA par défaut (cumul en poulies, sets sinon) — E01US011 le remplacera par un
    # résolveur configuré au même point d'injection (règle 2). Mêmes politiques de tableau (MVP).
    # E04US015 (ADR-0050) : le port `forfait` fait **passer l'adversaire** d'un duelliste déclaré
    # forfait dans la phase de tableau (walkover à la reconstruction) ; les forfaits de qualif sont,
    # eux, exclus à l'ensemencement (via le classement).
    app.state.service_saisie_duels = ServiceSaisieDuels(
        tournoi_repository,
        phase_repository,
        categorie_repository,
        blason_repository,
        duel_repository,
        forfait_repository,
        app.state.service_classement,
        ResolveurBaremeDuelFfta(),
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        app.state.registre_politiques,
    )

    # Simulation éphémère (E15US002, ADR-0054) : rejoue le moteur (qualif → duels → classement) d'un
    # tournoi **avant démarrage** sur des adapters **in-memory**, sans rien persister ni diffuser.
    # L'usine `fabriquer_harnais_simulation` (module, ci-dessus) est le **seul** point qui connaît
    # les adapters in-memory concrets ; hissée hors de `create_app` pour être **importable** — les
    # tests consomment **la même** usine (source unique testée, pas une copie qui dériverait — cf.
    # revue E15US002). `ServiceSimulation` ne dépend que des ports **réels** (lecture, hydratation)
    # et de cette usine ; l'application ne connaît aucun adapter (règle 8). Aucune route exposée :
    # substrat pour le cockpit d'E15US003.
    app.state.service_simulation = ServiceSimulation(
        tournoi_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        gabarit_repository,
        inscription_repository,
        depart_repository,
        deroule_repository,
        phase_repository,
        serie_repository,
        fabriquer_harnais_simulation,
    )
    # Pilotage de simulation vivante (E15US003, ADR-0055) : le bot pausable + la reprise en main +
    # le cockpit se posent **sur** le substrat ci-dessus. Le service tient un **registre de
    # sessions** en mémoire (éphémère, hors file — règle 7 intacte), reçoit la **même** usine de
    # harnais que le rejeu one-shot (source unique), un **générateur de scores** injecté (stratégie
    # substituable sans toucher au domaine, règle 1/2) et le port de **diffusion isolée** (canal
    # `/ws/simulation`, broadcaster dédié). Aucune route n'écrit en base : tout se joue dans le
    # harnais jetable.
    app.state.registre_sessions_simulation = RegistreSessionsSimulation()
    app.state.service_pilotage_simulation = ServicePilotageSimulation(
        tournoi_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        gabarit_repository,
        inscription_repository,
        depart_repository,
        deroule_repository,
        phase_repository,
        serie_repository,
        fabriquer_harnais_simulation,
        GenerateurScoresPlausibles(),
        app.state.registre_sessions_simulation,
        DiffusionSimulationBroadcaster(broadcaster_simulation),
    )
    # Simulation de **format** (E01US024, ADR-0063) : « ce déroulé tient-il à N archers ? ». Ne
    # reçoit **aucun** repository SQL sinon la bibliothèque de formats, en lecture — le tournoi
    # simulé naît dans le harnais et meurt avec lui, donc la non-pollution reste structurelle
    # (ADR-0054). Réutilise le bot du cockpit (`ServicePilotageSimulation`) plutôt qu'un second
    # moteur : un seul bot, une seule dérive possible.
    app.state.service_simulation_format = ServiceSimulationFormat(
        format_repository,
        fabriquer_harnais_simulation,
        app.state.service_pilotage_simulation,
    )
    # Feuille de marque (E09US001) : premier document du socle PDF (ReportLab, ADR-0031). Le service
    # lit le plan persisté et joint archer → catégorie → blason (ports seuls, pas de
    # service→service), récupère la grille depuis le barème, puis délègue le rendu à l'adapter
    # ReportLab. Lecture pure (aucune écriture) : l'endpoint l'exécute via `run_in_threadpool`.
    app.state.service_feuille_de_marque = ServiceFeuilleDeMarque(
        tournoi_repository,
        depart_repository,
        placement_repository,
        inscription_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        phase_repository,
        GenerateurFeuilleDeMarquePdf(),
    )
    # Documents de salle (E09US008) : étiquettes de cible (QR de rattachement + code) et cartes de
    # scoreur (code personnel). Lecture pure comme la feuille de marque ; ports seuls (postes,
    # scoreurs, tournois). L'URL du QR est bâtie à la frontière API à partir de `request.base_url`.
    app.state.service_documents_salle = ServiceDocumentsSalle(
        tournoi_repository,
        poste_repository,
        scoreur_repository,
        GenerateurDocumentsSallePdf(),
    )
    # Listes imprimables (E09US003) : liste de placement (accueil) et liste club & paiement
    # (administratif). Le placement se reconstitue par ports seuls (comme la feuille de marque) ; la
    # vue club & paiement **réutilise `service_paiements`** (précédent `ServiceCompletude`) pour ne
    # pas dupliquer l'agrégation dû/payé ni le bucket « Sans club » (ADR-0014). Lecture pure comme
    # les autres documents ; l'endpoint l'exécute via `run_in_threadpool`.
    app.state.service_listes_impression = ServiceListesImpression(
        tournoi_repository,
        depart_repository,
        placement_repository,
        inscription_repository,
        archer_repository,
        categorie_repository,
        app.state.service_paiements,
        GenerateurListesImpressionPdf(),
    )
    # Palmarès (E06US004, ADR-0067) : le **classement final** du tournoi — les rangs décernés par
    # les tableaux fusionnés avec ceux de la qualification, par catégorie, plus l'export PDF affiché
    # au mur. Réutilise `service_saisie_duels` pour reconstruire chaque tableau (comme le routage et
    # le pilotage) : recoder la reconstruction la ferait diverger de l'écran de duels. La politique
    # `aggregation` — qui départage les archers sortis au même tour, qu'aucun match n'a séparés —
    # est **injectée ici**, au défaut `par_qualification` (usage World Archery), résolu **par le
    # registre** : la contourner en instanciant la stratégie à la main ferait de la politique une
    # décoration (même parti que le `tiebreak` du classement, ADR-0066).
    app.state.service_palmares = ServicePalmares(
        tournoi_repository,
        phase_repository,
        app.state.service_classement,
        app.state.service_saisie_duels,
        duel_repository,
        GenerateurPalmaresPdf(),
        depart_repository,
        cast(
            "Aggregation",
            app.state.registre_politiques.resoudre(
                FamillePolitique.AGGREGATION, "par_qualification", {}
            ),
        ),
    )
    # Archive de fin de tournoi (E11US003) : paquet ZIP réunissant l'instantané SQLite complet, un
    # dump CSV de toute la base, les PDF régénérés du tournoi (feuilles de marque par départ,
    # listes) et un manifeste — selon les parties cochées côté UI. L'assemblage mécanique délégué à
    # `ConstructeurArchiveZip` (infra) derrière le port `ConstructeurArchive` défini **au niveau
    # applicatif** : une archive est un concern d'exploitation, pas du domaine (règle 12). Lecture
    # pure comme les documents PDF ; l'endpoint l'exécute via `run_in_threadpool`.
    app.state.service_archive = ServiceArchive(
        tournoi_repository,
        depart_repository,
        app.state.service_feuille_de_marque,
        app.state.service_listes_impression,
        ConstructeurArchiveZip(Path(database.engine.url.database or "")),
        HorlogeSysteme(),
    )

    # --- Accès administrateur (E10US002) : identifiants dans un fichier `.env` local + jetons
    # de session en mémoire. Auth = concern technique (pas de domaine) ; la dépendance API
    # `exiger_admin` protège les routes admin (ici, la création de tournoi). ---
    credentials_store = AdminCredentialsStore(admin_env_path or default_env_path())
    session_store = SessionStore()
    app.state.service_auth = ServiceAuth(credentials_store, session_store)

    # --- Scoreurs (E10US003) : définition (admin) + session (scoreur). Le scoreur est identifié par
    # **la personne** (un code généré), à côté de l'admin (un secret) et du poste de cible (le lieu,
    # E10US007). Store de sessions **nominatif** en mémoire (jeton → scoreur, pour tracer qui
    # valide, E10US005) et générateur de code injecté (déterminisme des tests, règle 9). La
    # dépendance API `exiger_scoreur` protégera les endpoints de validation (E04US002). ---
    scoreur_session_store = ScoreurSessionStore()
    app.state.service_scoreurs = ServiceScoreurs(
        scoreur_repository, tournoi_repository, scoreur_session_store, generer_code_scoreur
    )

    # --- Postes de cible (E04US001, ADR-0029) : préparation des codes (admin) + session de poste
    # (rattacher une tablette à sa cible). Troisième mode d'identité (`D-13`, le **lieu**), à côté
    # du scoreur (la personne) et de l'admin (un secret). Store de sessions en mémoire (jeton →
    # poste)
    # et générateur de code injecté (déterminisme des tests, règle 9) ; le service lit le plan de
    # salle (gabarit) pour émettre un code par cible. La dépendance API `exiger_poste` protégera la
    # saisie (E04US002) et gardera « le poste ne saisit que pour SA cible » (E10US007). ---
    #
    # E07US004 élargit ce service aux **écrans de salle** : le CA en fait des postes, rattachés par
    # le même jeton, avec le même code — d'où la création/le réglage/la suppression d'écrans ici
    # plutôt que dans un service parallèle (`ServicePostes` possède déjà l'allocation de code). Il
    # reçoit pour cela le registre de consignes : supprimer un écran doit **aussi** retirer sa
    # consigne, sinon SQLite réattribuerait l'identifiant à un futur écran qui en hériterait. ---
    poste_session_store = PosteSessionStore()
    registre_consignes = RegistreConsignesMemoire()
    # Construit ici (et non plus à la supervision) : trois services nettoient désormais l'état
    # volatil d'un poste — supprimer un écran, le révoquer, le superviser.
    poste_presence = RegistrePresenceMemoire()
    app.state.service_postes = ServicePostes(
        poste_repository,
        tournoi_repository,
        gabarit_repository,
        depart_repository,
        poste_session_store,
        registre_consignes,
        poste_presence,
        generer_code_poste,
    )

    # --- Écrans de salle (E07US004, ADR-0064) : « que montre cet écran, maintenant ? ». Le pilotage
    # admin est un **état lu**, pas un ordre poussé — le hub temps réel est mono-canal (aucun
    # ciblage par destinataire) et, surtout, la **fin** d'une prise de contrôle naît du temps qui
    # passe, que nul événement ne peut pousser (même raisonnement qu'ADR-0038 §4, qui a mis la
    # supervision en poll). D'où ce registre **en mémoire** : le déroulé, lui, est persisté sur le
    # poste. Effet de bord voulu — un redémarrage **libère** les écrans au lieu de les figer. ---
    app.state.service_ecrans = ServiceEcrans(
        poste_repository,
        tournoi_repository,
        poste_session_store,
        registre_consignes,
        HorlogeSysteme(),
    )

    # --- Journal d'audit métier (E10US005, socle) : trace les actes sensibles (qui/quand/
    # avant-après) pour gérer les litiges. `consigner` est la primitive d'écriture qu'appelleront
    # les producteurs — validation/correction (E04US002), forfait (E12US004) — depuis leur
    # commande de file ; la consultation admin (`GET .../audit`) est livrée. L'horodatage passe
    # par le port `Horloge` (adapter système UTC), injecté pour des cas d'usage déterministes. ---
    app.state.service_audit = ServiceAudit(audit_repository, tournoi_repository, HorlogeSysteme())

    # --- Pilotage d'un tour (E12US002, ADR-0056) : feu vert + lancement. Compose les services de
    # duels **déjà câblés** — `service_saisie_duels` (reconstruction de l'arbre + noms),
    # `service_placement_duels` (le plan → la cible de chaque duelliste) — et `service_audit` (la
    # trace `LANCEMENT`). Aucun repo neuf : le feu vert **lit** le tableau reconstruit + le plan
    # persisté ; le lancement est un **événement** (aucun statut posé sur le tableau). Le
    # geste passe par la file et renvoie un `LiveEvent("tour_lance")` diffusé par le listener
    # post-commit — le point de branchement des 4 canaux (leurs récepteurs sont séquencés). ---
    app.state.service_pilotage_tour = ServicePilotageTour(
        app.state.service_saisie_duels,
        app.state.service_placement_duels,
        app.state.service_audit,
    )

    # --- Panneau de routage (E04US018) : **premier récepteur** du signal `tour_lance` émis
    # ci-dessus. Même composition que le pilotage, sans l'audit — un panneau de routage ne *décide*
    # de rien : il lit le tableau reconstruit (où va l'archer) et le plan de duels persisté (sur
    # quelle cible), et résout lui-même la phase de tableau (`phase_repository`) puisque la tablette
    # de qualification ne la connaît pas. Aucun repo neuf, aucune écriture (`D-08` : rien n'est
    # calculé au moment de la bascule). ---
    app.state.service_routage = ServiceRoutage(
        app.state.service_saisie_duels,
        app.state.service_placement_duels,
        archer_repository,
        phase_repository,
    )

    # --- Saisie de qualification (E04US002) : moteur métier `Serie`/`Volee` persisté. Le service
    # résout la config (blason → pavé, phase → barème/grain), pilote l'agrégat, date les entrées
    # d'audit (validation/correction) via `Horloge` ; l'adapter `SerieRepositorySQL` co-écrit série
    # + trace atomiquement (ADR-0035). Il **cloisonne** la saisie au triplet (tournoi, cible,
    # départ) du poste — via placement + inscriptions (ADR-0033 §3) — et reconstitue la grille des
    # affectations réelles. La garde vit **ici**, pas dans un `Depends`, pour tenir aussi face aux
    # appelants hors HTTP (writer WS E04US009, orchestrateur E12US002). ---
    service_saisie = ServiceSaisie(
        serie_repository,
        phase_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        placement_repository,
        inscription_repository,
        forfait_repository,
        HorlogeSysteme(),
    )
    app.state.service_saisie = service_saisie

    # --- Supervision des postes (E12US001, ADR-0038) : console du jour J. La présence par
    # **heartbeat** (registre en mémoire, volatil comme les sessions) donne l'état en ligne/hors
    # ligne ; l'**avancement** est lu sur `ServiceSaisie` (barème + séries, sans dupliquer grille,
    # ADR-0033), la « dernière saisie » sur les séries — jamais le heartbeat (ADR-0038 §2). Seuil
    # hors ligne injecté (30 s > l'intervalle de heartbeat ~10 s côté front). L'`Horloge` système
    # date/mesure la présence (déterminisme en test via injection). Révocation admin (`D-07`). ---
    # Depuis E07US004, la console montre aussi les **écrans de salle** — c'est le CA (« un écran
    # figé ne se plaint pas, seule la supervision le révèle ») — et leur prise de contrôle en
    # vigueur, lue par un port étroit sur `ServiceEcrans` (elle affiche, elle ne pilote pas).
    app.state.service_supervision = ServiceSupervision(
        poste_repository,
        tournoi_repository,
        poste_session_store,
        poste_presence,
        registre_consignes,
        service_saisie,
        app.state.service_ecrans,
        HorlogeSysteme(),
        _SEUIL_POSTE_HORS_LIGNE_S,
    )

    # --- Suivi du déroulé (E07US004, ADR-0064) : le schéma à braquets de l'atelier (E01US024)
    # **rempli par la réalité**. Ne recalcule rien : `domain.deroule.projeter` pour le dessin,
    # `ServiceSaisieDuels.reconstruire` pour les duels tranchés (une seule source de vérité de la
    # progression, déjà partagée par la saisie, le placement et le feu vert). L'effectif est le
    # nombre d'engagés — l'équivalent live du « je simule à N archers » de l'atelier. ---
    app.state.service_suivi_deroule = ServiceSuiviDeroule(
        tournoi_repository,
        phase_repository,
        compteur_engages,
        app.state.service_saisie_duels,
    )

    # --- Tableaux publics (E07US005) : « voir les arbres en direct », appli publique + écran de
    # salle. Lecture pure, **sans authentification**, montée sur le même `ServiceSaisieDuels` que
    # le routage, le palmarès et le suivi du déroulé — une seule source de vérité de la
    # progression. Service **distinct** de `ServiceSaisieDuels` (qui est celui du scoreur, protégé
    # par `exiger_scoreur`) : ce sont deux audiences, et la restriction de contenu se fait au DTO
    # de `api/v1/tableaux.py` (règle 6). Aucun repo neuf, aucune écriture. ---
    app.state.service_tableaux_publics = ServiceTableauxPublics(
        tournoi_repository,
        phase_repository,
        app.state.service_saisie_duels,
    )

    # --- Complétude du tournoi (E12US005) : « qu'est-ce qui manque pour finir ? », sportif et hors
    # sportif comptés **séparément** (`D-17`). Lecture pure : agrège les cibles de qualification
    # terminées (plan matérialisé + inscriptions + séries validées) et les archers réglés (port
    # étroit sur `ServicePaiements`, qui porte déjà la règle dû/payé/reste, E08US002), puis confie
    # le jugement à `domain.completude`. Les **phases éliminatoires** sont séquencées (EPIC-05 non
    # livré) : ligne « à venir » qui ne bloque pas. Le front poll (live) comme la supervision. ---
    app.state.service_completude = ServiceCompletude(
        tournoi_repository,
        depart_repository,
        placement_repository,
        inscription_repository,
        serie_repository,
        phase_repository,
        forfait_repository,
        app.state.service_paiements,
    )

    # Départs (créneaux) d'un tournoi (E02US004, ADR-0017) : le service vérifie l'existence du
    # tournoi (port tournoi), attribue le numéro du créneau, et dépend du port inscription pour le
    # garde-fou « supprimer un départ qui porte des inscriptions » (E02US009). Câblé **ici**, après
    # `service_completude` : son garde-fou de cycle de vie (E12US008) lit l'état du créneau via le
    # port étroit `LecteurAvancementDepart`, que `ServiceCompletude` réalise (`avancement_depart`).
    # `archer_repository` + `HorlogeSysteme` : à la suppression d'un départ **tarifé**, chaque
    # inscription **payée** effacée ouvre un remboursement (E08US005, ADR-0057) — il faut le nom de
    # l'archer (instantané figé) et la date d'ouverture. Suppression + ouvertures en une transaction
    # (`supprimer_avec_remboursements`).
    app.state.service_departs = ServiceDeparts(
        depart_repository,
        tournoi_repository,
        inscription_repository,
        app.state.service_completude,
        archer_repository,
        HorlogeSysteme(),
    )

    # Jeu d'essai — générateur d'inscrits + scénarios rejouables (E15US001) : outil admin de démo/QA
    # qui écrit de la **donnée réelle** (à distinguer de la simulation éphémère E15US002). Il ne
    # touche aucun repository directement : il **compose** les services existants (tournois,
    # catégories, départs, archers, inscriptions, clubs) — même patron que `ServicePlacementDuels`
    # au-dessus de `ServiceClassement`. Câblé **ici**, après `service_departs` (le dernier de ses
    # dépendances à être construit). Génération déterministe par graine injectée (règle 9).
    app.state.service_jeu_essai = ServiceJeuEssai(
        app.state.service_tournois,
        app.state.service_categories,
        app.state.service_departs,
        app.state.service_archers,
        app.state.service_inscriptions,
        app.state.service_clubs,
    )

    # --- Forfaits — abandon / disqualification (E04US015, ADR-0050) : le scoreur déclare/annule un
    # forfait en qualification (relégation/exclusion au classement) ou en duels (adversaire passe).
    # Réversible tant que le tournoi n'est pas terminé (`D-15`) ; chaque acte trace `FORFAIT` via
    # `Horloge` + co-écriture atomique (ADR-0035). La garde « scoreur de CE tournoi » est à l'API.
    app.state.service_forfait = ServiceForfait(
        forfait_repository,
        tournoi_repository,
        archer_repository,
        phase_repository,
        HorlogeSysteme(),
    )

    # Idempotence de la saisie (ADR-0036) : registre en mémoire consulté **dans** la commande de la
    # file (writer unique) par l'endpoint de saisie, pour qu'un rejeu réseau ne double ni une volée
    # ni une trace. Exposé sur l'app comme la `write_queue`.
    app.state.registre_idempotence = RegistreIdempotence()

    # --- Frontière API : traduction des erreurs typées en réponses HTTP (ADR-0007). ---
    enregistrer_gestionnaires_erreurs(app)

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)
    app.include_router(realtime_router)
    app.include_router(realtime_simulation_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(scoreurs_router)
    app.include_router(scoreur_session_router)
    app.include_router(postes_router)
    app.include_router(poste_session_router)
    app.include_router(supervision_router)
    app.include_router(ecrans_router)
    app.include_router(ecran_session_router)
    app.include_router(suivi_deroule_router)
    app.include_router(poste_heartbeat_router)
    app.include_router(tournois_router)
    app.include_router(departs_router)
    app.include_router(inscriptions_router)
    app.include_router(jeu_essai_router)
    app.include_router(simulation_router)
    app.include_router(paiements_router)
    app.include_router(remboursements_router)
    app.include_router(categories_router)
    app.include_router(blasons_router)
    app.include_router(clubs_router)
    app.include_router(patrimoine_router)
    app.include_router(formats_router)
    app.include_router(gabarits_router)
    app.include_router(bareme_qualification_router)
    app.include_router(grain_validation_router)
    app.include_router(phases_router)
    app.include_router(competition_router)
    app.include_router(completude_router)
    app.include_router(saisie_router)
    app.include_router(deroule_router)
    app.include_router(placement_router)
    app.include_router(placement_duels_router)
    app.include_router(saisie_duels_router)
    app.include_router(pilotage_router)
    app.include_router(routage_router)
    app.include_router(tableaux_router)
    app.include_router(forfaits_router)
    app.include_router(barrages_router)
    app.include_router(feuille_de_marque_router)
    app.include_router(documents_salle_router)
    app.include_router(listes_impression_router)
    app.include_router(palmares_router)
    app.include_router(archive_router)

    # --- Service du build front (E00US012) : monté EN DERNIER (racine `/`), et seulement
    # s'il existe, pour ne jamais masquer les routes API/WS/health ci-dessus. ---
    dist = frontend_dist if frontend_dist is not None else frontend_dist_dir()
    if dist.is_dir():
        monter_spa(app, dist)

    return app
