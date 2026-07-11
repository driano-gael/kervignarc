"""Composition root — câblage explicite de l'application (guide §2.2, ADR-0003).

Point **unique et lisible** où sont assemblés adapters, services applicatifs et routers,
**sans conteneur DI**. `create_app()` construit l'instance FastAPI et branche ses dépendances ;
tout ce qui est câblé est visible ici, en un seul endroit.

Extension prévue : les services applicatifs (E00US009) s'instancieront ici, puis seront
**injectés** dans les routers et les use cases (pas d'accès global, pas de magie DI).
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from api.realtime import router as realtime_router
from infrastructure.db import Database, WriteQueue, default_database_url
from infrastructure.realtime import Broadcaster, LiveEvent


def create_app(database_url: str | None = None) -> FastAPI:
    """Assemble et renvoie l'application FastAPI entièrement câblée.

    `database_url` : surcharge l'URL de la base (tests) ; sinon configuration applicative
    (variable d'environnement KERVIGNARC_DATABASE_URL, sinon défaut local).
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

    def _broadcast_if_event(result: object) -> None:
        if isinstance(result, LiveEvent):
            broadcaster.publish(result)

    write_queue.add_post_commit_listener(_broadcast_if_event)

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

    # --- Services applicatifs : à assembler ici et injecter dans les routers (E00US009). ---

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)
    app.include_router(realtime_router)

    return app
