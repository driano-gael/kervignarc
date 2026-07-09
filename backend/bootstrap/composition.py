"""Composition root — câblage explicite de l'application (guide §2.2, ADR-0003).

Point **unique et lisible** où sont assemblés adapters, services applicatifs et routers,
**sans conteneur DI**. `create_app()` construit l'instance FastAPI et branche ses dépendances ;
tout ce qui est câblé est visible ici, en un seul endroit.

Extension prévue : les adapters sortants (connexion SQLite + file d'écriture — E00US006/007)
et les services applicatifs (E00US009) s'instancieront ici, puis seront **injectés** dans les
routers et les use cases (pas d'accès global, pas de magie DI).
"""

from fastapi import FastAPI

from api.health import router as health_router


def create_app() -> FastAPI:
    """Assemble et renvoie l'application FastAPI entièrement câblée."""
    app = FastAPI(title="Kervignarc", version="0.1.0")

    # --- Adapters sortants (infrastructure) : à instancier ici (E00US006/007). ---
    # --- Services applicatifs : à assembler ici et injecter dans les routers (E00US009). ---

    # --- Adapters entrants (routers API). ---
    app.include_router(health_router)

    return app
