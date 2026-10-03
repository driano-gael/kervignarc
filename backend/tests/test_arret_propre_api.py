"""Arrêt propre de l'application (E11US006, CA « drain à l'arrêt ») — câblage du `lifespan`.

`test_write_queue` prouve que la file draine ; ici, que l'arrêt **de l'application** la draine
avant de rendre la main, avec des écritures encore en attente au moment de l'arrêt.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base


def test_l_arret_de_l_application_commite_les_ecritures_en_attente(tmp_path: Path) -> None:
    base = tmp_path / "kervignarc.db"
    preparer_base(f"sqlite:///{base.as_posix()}")
    connexion = sqlite3.connect(base)
    connexion.execute("CREATE TABLE drain (n INTEGER)")
    connexion.commit()
    connexion.close()
    app = create_app(f"sqlite:///{base.as_posix()}", admin_env_path=tmp_path / ".env")
    premiere_commencee = threading.Event()

    def ecriture(n: int) -> None:
        premiere_commencee.set()
        time.sleep(0.05)
        cx = sqlite3.connect(base)
        cx.execute("INSERT INTO drain VALUES (?)", (n,))
        cx.commit()
        cx.close()

    try:
        with TestClient(app):
            futures = [app.state.write_queue.submit(lambda n=n: ecriture(n)) for n in range(5)]
            premiere_commencee.wait(5)
            assert not all(f.done() for f in futures)  # l'arrêt survient bien file non vide
        # Sortie du bloc = arrêt du `lifespan`.
        connexion = sqlite3.connect(base)
        assert connexion.execute("SELECT count(*) FROM drain").fetchone() == (5,)
        connexion.close()
    finally:
        app.state.database.engine.dispose()
