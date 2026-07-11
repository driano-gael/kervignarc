"""Composition root — câblage explicite de l'application (guide §2.2, ADR-0003).

Point **unique et lisible** où sont assemblés adapters, services applicatifs et routers,
**sans conteneur DI**. `create_app()` construit l'instance FastAPI et branche ses dépendances ;
tout ce qui est câblé est visible ici, en un seul endroit.

Extension prévue : les services applicatifs (E00US009) s'instancieront ici, puis seront
**injectés** dans les routers et les use cases (pas d'accès global, pas de magie DI).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from infrastructure.db import Database, WriteQueue, default_database_url


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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Cycle de vie : ouvre le worker d'écriture au démarrage, le draine à l'arrêt."""
        write_queue.start()
        try:
            yield
        finally:
            write_queue.stop()

    app = FastAPI(title="Kervignarc", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.state.write_queue = write_queue

    # --- Services applicatifs : à assembler ici et injecter dans les routers (E00US009). ---

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)

    return app
