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
from api.v1.competition import router as competition_router
from api.v1.tournois import router as tournois_router
from application.archers import ServiceArchers
from application.classements import ServiceClassement
from application.tournois import ServiceTournois
from infrastructure.db import (
    ArcherRepositorySQL,
    Database,
    ScoreRepositorySQL,
    TournoiRepositorySQL,
    WriteQueue,
    default_database_url,
)
from infrastructure.realtime import Broadcaster, LiveEvent


def create_app(database_url: str | None = None, *, frontend_dist: Path | None = None) -> FastAPI:
    """Assemble et renvoie l'application FastAPI entièrement câblée.

    `database_url` : surcharge l'URL de la base (tests) ; sinon configuration applicative
    (variable d'environnement KERVIGNARC_DATABASE_URL, sinon défaut local).
    `frontend_dist` : surcharge le répertoire du build front à servir (tests) ; sinon
    résolu par défaut (`frontend/dist/`). Non monté s'il n'existe pas (E00US012).
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
    archer_repository = ArcherRepositorySQL(database.session_factory)
    score_repository = ScoreRepositorySQL(database.session_factory)
    app.state.service_tournois = ServiceTournois(tournoi_repository)
    app.state.service_archers = ServiceArchers(
        tournoi_repository, archer_repository, score_repository
    )
    app.state.service_classement = ServiceClassement(
        tournoi_repository, archer_repository, score_repository
    )

    # --- Frontière API : traduction des erreurs typées en réponses HTTP (ADR-0007). ---
    enregistrer_gestionnaires_erreurs(app)

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)
    app.include_router(realtime_router)
    app.include_router(tournois_router)
    app.include_router(competition_router)

    # --- Service du build front (E00US012) : monté EN DERNIER (racine `/`), et seulement
    # s'il existe, pour ne jamais masquer les routes API/WS/health ci-dessus. ---
    dist = frontend_dist if frontend_dist is not None else frontend_dist_dir()
    if dist.is_dir():
        monter_spa(app, dist)

    return app
