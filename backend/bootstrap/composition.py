"""Composition root — câblage explicite de l'application (guide §2.2, ADR-0003).

Point **unique et lisible** où sont assemblés adapters, services applicatifs et routers,
**sans conteneur DI**. `create_app()` construit l'instance FastAPI et branche ses dépendances ;
tout ce qui est câblé est visible ici, en un seul endroit.

Les services applicatifs sont **injectés** dans les routers via `app.state` (pas d'accès
global, pas de magie DI) ; les erreurs typées sont traduites à la frontière API.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from api.erreurs import enregistrer_gestionnaires_erreurs
from api.health import router as health_router
from api.realtime import router as realtime_router
from api.spa import frontend_dist_dir, monter_spa
from api.v1.audit import router as audit_router
from api.v1.auth import router as auth_router
from api.v1.bareme_qualification import router as bareme_qualification_router
from api.v1.blasons import router as blasons_router
from api.v1.categories import router as categories_router
from api.v1.clubs import router as clubs_router
from api.v1.competition import router as competition_router
from api.v1.departs import router as departs_router
from api.v1.documents_salle import router as documents_salle_router
from api.v1.feuille_de_marque import router as feuille_de_marque_router
from api.v1.gabarits import router as gabarits_router
from api.v1.grain_validation import router as grain_validation_router
from api.v1.inscriptions import router as inscriptions_router
from api.v1.placement import router as placement_router
from api.v1.postes import router as postes_router
from api.v1.postes import session_router as poste_session_router
from api.v1.scoreurs import router as scoreurs_router
from api.v1.scoreurs import session_router as scoreur_session_router
from api.v1.tournois import router as tournois_router
from application.archers import ServiceArchers
from application.audit import ServiceAudit
from application.auth import ServiceAuth
from application.bareme_qualification import ServiceBaremeQualification
from application.blasons import ServiceBlasons
from application.categories import ServiceCategories
from application.classements import ServiceClassement
from application.clubs import ServiceClubs
from application.departs import ServiceDeparts
from application.documents_salle import ServiceDocumentsSalle
from application.feuille_de_marque import ServiceFeuilleDeMarque
from application.gabarits import ServiceGabarits
from application.grain_validation import ServiceGrainValidation
from application.inscriptions import ServiceInscriptions
from application.placement import ServicePlacement
from application.postes import ServicePostes
from application.scoreurs import ServiceScoreurs
from application.tournois import ServiceTournois
from infrastructure.auth import AdminCredentialsStore, SessionStore, default_env_path
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    Database,
    DepartRepositorySQL,
    GabaritSalleRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    PlacementRepositorySQL,
    PosteRepositorySQL,
    ScoreRepositorySQL,
    ScoreurRepositorySQL,
    TournoiRepositorySQL,
    WriteQueue,
    default_database_url,
)
from infrastructure.horloge import HorlogeSysteme
from infrastructure.pdf import GenerateurDocumentsSallePdf, GenerateurFeuilleDeMarquePdf
from infrastructure.postes import PosteSessionStore, generer_code_poste
from infrastructure.realtime import Broadcaster, LiveEvent
from infrastructure.scoreurs import ScoreurSessionStore, generer_code_scoreur


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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Cycle de vie : lie la boucle au broadcaster, ouvre puis draine le worker."""
        broadcaster.bind_loop(asyncio.get_running_loop())
        write_queue.start()
        try:
            yield
        finally:
            write_queue.stop()
            broadcaster.unbind_loop()

    app = FastAPI(title="Kervignarc", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.state.write_queue = write_queue
    app.state.broadcaster = broadcaster

    # --- Services applicatifs (E00US009) : repository (adapter) → service, injectés via state. ---
    # Le repository lit via les sessions courtes du Database ; les écritures du service passent
    # par la file d'écriture (routage assuré côté router API).
    tournoi_repository = TournoiRepositorySQL(database.session_factory)
    categorie_repository = CategorieRepositorySQL(database.session_factory)
    blason_repository = BlasonRepositorySQL(database.session_factory)
    club_repository = ClubRepositorySQL(database.session_factory)
    gabarit_repository = GabaritSalleRepositorySQL(database.session_factory)
    phase_repository = PhaseRepositorySQL(database.session_factory)
    archer_repository = ArcherRepositorySQL(database.session_factory)
    score_repository = ScoreRepositorySQL(database.session_factory)
    depart_repository = DepartRepositorySQL(database.session_factory)
    inscription_repository = InscriptionRepositorySQL(database.session_factory)
    placement_repository = PlacementRepositorySQL(database.session_factory)
    scoreur_repository = ScoreurRepositorySQL(database.session_factory)
    poste_repository = PosteRepositorySQL(database.session_factory)
    audit_repository = AuditRepositorySQL(database.session_factory)
    app.state.service_tournois = ServiceTournois(tournoi_repository)
    # Départs (créneaux) d'un tournoi (E02US004, ADR-0017) : le service vérifie l'existence du
    # tournoi (dépend du port tournoi) et attribue le numéro du créneau. Il dépend aussi du port
    # inscription pour le garde-fou « supprimer un départ qui porte des inscriptions » (E02US009).
    app.state.service_departs = ServiceDeparts(
        depart_repository, tournoi_repository, inscription_repository
    )
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
    # Barème de qualification (E01US009) : porté par la phase `qualification` du tournoi
    # (introduction minimale de `Phase`, ADR-0011). Le service vérifie l'existence du tournoi.
    app.state.service_bareme_qualification = ServiceBaremeQualification(
        tournoi_repository, phase_repository
    )
    # Grain de validation (E01US015, `D-11`) : deuxième politique de la même phase
    # (`config.validation` à côté de `config.scoring`, sans changement de schéma — ADR-0011).
    app.state.service_grain_validation = ServiceGrainValidation(
        tournoi_repository, phase_repository
    )
    # Inscription d'un archer (E02US002) : le service valide le tournoi, sa **catégorie** (qui doit
    # être du même tournoi) et son club de rattachement s'il est fourni — d'où quatre ports pour un
    # seul agrégat. Le club reste facultatif (`NULL` = inconnu, ADR-0014), la catégorie non.
    # Le port inscription est injecté pour l'« engagé » élargi (E02US009) : un archer inscrit sur au
    # moins un départ est engagé, sa suppression se signale et efface ses inscriptions.
    app.state.service_archers = ServiceArchers(
        tournoi_repository,
        archer_repository,
        score_repository,
        club_repository,
        categorie_repository,
        inscription_repository,
    )
    app.state.service_classement = ServiceClassement(
        tournoi_repository, archer_repository, score_repository
    )
    # Inscriptions archer↔départ (E02US009, ADR-0017) : inscrire sur des créneaux du tournoi de
    # l'archer (même tournoi, unicité), marquer payé, désinscrire ; le montant dû dérive du tarif.
    app.state.service_inscriptions = ServiceInscriptions(
        inscription_repository, archer_repository, depart_repository
    )
    # Placement (E03US001 lecture ; E03US004 matérialisation + ajustement, ADR-0024). Le service
    # joint archer → catégorie → blason par défaut pour nourrir le moteur pur (`domain/placement`),
    # d'où sept ports de jointure/gardes, **plus** le port `placement` qui persiste le plan
    # (matérialisé, ajustable au glisser-déposer). Les écritures (régénérer/déplacer/échanger/placer
    # les restants) passent par la file (routage API).
    app.state.service_placement = ServicePlacement(
        tournoi_repository,
        depart_repository,
        gabarit_repository,
        inscription_repository,
        archer_repository,
        categorie_repository,
        blason_repository,
        placement_repository,
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
    poste_session_store = PosteSessionStore()
    app.state.service_postes = ServicePostes(
        poste_repository,
        tournoi_repository,
        gabarit_repository,
        poste_session_store,
        generer_code_poste,
    )

    # --- Journal d'audit métier (E10US005, socle) : trace les actes sensibles (qui/quand/
    # avant-après) pour gérer les litiges. `consigner` est la primitive d'écriture qu'appelleront
    # les producteurs — validation/correction (E04US002), forfait (E12US004) — depuis leur
    # commande de file ; la consultation admin (`GET .../audit`) est livrée. L'horodatage passe
    # par le port `Horloge` (adapter système UTC), injecté pour des cas d'usage déterministes. ---
    app.state.service_audit = ServiceAudit(audit_repository, tournoi_repository, HorlogeSysteme())

    # --- Frontière API : traduction des erreurs typées en réponses HTTP (ADR-0007). ---
    enregistrer_gestionnaires_erreurs(app)

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)
    app.include_router(realtime_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(scoreurs_router)
    app.include_router(scoreur_session_router)
    app.include_router(postes_router)
    app.include_router(poste_session_router)
    app.include_router(tournois_router)
    app.include_router(departs_router)
    app.include_router(inscriptions_router)
    app.include_router(categories_router)
    app.include_router(blasons_router)
    app.include_router(clubs_router)
    app.include_router(gabarits_router)
    app.include_router(bareme_qualification_router)
    app.include_router(grain_validation_router)
    app.include_router(competition_router)
    app.include_router(placement_router)
    app.include_router(feuille_de_marque_router)
    app.include_router(documents_salle_router)

    # --- Service du build front (E00US012) : monté EN DERNIER (racine `/`), et seulement
    # s'il existe, pour ne jamais masquer les routes API/WS/health ci-dessus. ---
    dist = frontend_dist if frontend_dist is not None else frontend_dist_dir()
    if dist.is_dir():
        monter_spa(app, dist)

    return app
