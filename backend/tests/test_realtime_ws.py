"""Test d'intégration bout-en-bout du canal WebSocket (E00US008).

Vérifie les critères d'acceptation, en traversant toutes les couches :
- un client **s'abonne** via `/ws` (accusé `connected`) ;
- **après commit** d'une écriture par le writer unique, l'événement est **diffusé** à
  l'abonné — le pont thread (writer) → boucle asyncio (WebSocket) fonctionne.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from infrastructure.realtime import LiveEvent


def test_evenement_post_commit_diffuse_a_l_abonne(tmp_path: Path) -> None:
    """Une écriture committée par le writer diffuse son `LiveEvent` au client abonné."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url)

    database = app.state.database
    with database.engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE evenement (id INTEGER PRIMARY KEY, type TEXT)")

    def ecrire_et_notifier() -> LiveEvent:
        # Écriture réelle committée par le writer, puis événement à diffuser (post-commit).
        with database.engine.begin() as conn:
            conn.exec_driver_sql("INSERT INTO evenement (type) VALUES ('score')")
        return LiveEvent("score", {"cible": "A", "total": 30})

    try:
        with TestClient(app) as client, client.websocket_connect("/ws") as ws:
            # L'accusé `connected` garantit que l'abonnement est actif avant l'écriture.
            assert ws.receive_json() == {"type": "connected", "data": {}}

            future = app.state.write_queue.submit(ecrire_et_notifier)
            assert future.result(timeout=2) == LiveEvent("score", {"cible": "A", "total": 30})

            assert ws.receive_json() == {"type": "score", "data": {"cible": "A", "total": 30}}

        # L'écriture a bien été committée (post-commit = après persistance).
        with database.engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT count(*) FROM evenement").scalar() == 1
    finally:
        database.engine.dispose()
