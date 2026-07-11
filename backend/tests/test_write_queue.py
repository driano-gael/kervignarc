"""Tests de la file d'écriture à writer unique (E00US007, ADR-0005).

Vérifie les critères d'acceptation :
- une commande d'écriture est **mise en file** et **exécutée par un seul worker** ;
- l'appelant **obtient le résultat** via une `Future` (succès *ou* exception) ;
- les **écritures sont sérialisées** (ordre préservé, jamais deux en parallèle) ;
- le pont **async→sync** fonctionne (`asyncio.wrap_future`) ;
- les **lectures restent concurrentes** : une écriture en cours ne les bloque pas (WAL).
"""

from __future__ import annotations

import asyncio
import threading
from functools import partial
from pathlib import Path

import pytest

from infrastructure.db import Database, WriteQueue, WriteQueueClosedError


def test_submit_renvoie_le_resultat_de_la_commande() -> None:
    """L'appelant récupère la valeur de retour de sa commande via la Future."""
    with WriteQueue() as wq:
        future = wq.submit(lambda: 21 * 2)
        assert future.result(timeout=2) == 42


def test_l_exception_est_propagee_via_la_future() -> None:
    """Une commande qui échoue transmet son exception à l'appelant (pas de perte)."""

    def boom() -> None:
        raise ValueError("écriture invalide")

    with WriteQueue() as wq:
        future = wq.submit(boom)
        with pytest.raises(ValueError, match="écriture invalide"):
            future.result(timeout=2)


def test_les_ecritures_sont_serialisees_dans_l_ordre() -> None:
    """Un unique worker exécute les commandes en série : ordre FIFO, jamais deux en parallèle."""
    lock = threading.Lock()
    en_cours = 0
    max_paralleles = 0
    ordre: list[int] = []

    def commande(i: int) -> int:
        nonlocal en_cours, max_paralleles
        with lock:
            en_cours += 1
            max_paralleles = max(max_paralleles, en_cours)
        # Fenêtre où un 2e worker se manifesterait en incrémentant `en_cours`.
        threading.Event().wait(0.005)
        with lock:
            en_cours -= 1
            ordre.append(i)
        return i

    with WriteQueue() as wq:
        futures = [wq.submit(partial(commande, i)) for i in range(20)]
        resultats = [f.result(timeout=5) for f in futures]

    assert resultats == list(range(20))
    assert ordre == list(range(20))
    assert max_paralleles == 1


def test_pont_async_vers_sync() -> None:
    """Un handler async attend le résultat via asyncio.wrap_future sans bloquer sa boucle."""

    async def scenario() -> int:
        with WriteQueue() as wq:
            return await asyncio.wrap_future(wq.submit(lambda: 7))

    assert asyncio.run(scenario()) == 7


def test_submit_apres_arret_est_refuse() -> None:
    """Une fois la file arrêtée, toute soumission est refusée (garde-fou de cycle de vie)."""
    wq = WriteQueue()
    wq.start()
    wq.stop()
    with pytest.raises(WriteQueueClosedError):
        wq.submit(lambda: None)


def test_arret_draine_les_commandes_en_attente() -> None:
    """`stop()` laisse s'exécuter les commandes déjà en file avant d'arrêter le worker."""
    executees: list[int] = []
    porte = threading.Event()

    def enregistrer(i: int) -> int:
        executees.append(i)
        return i

    def premiere_commande() -> int:
        porte.wait(2)  # bloque le worker le temps d'empiler les commandes suivantes
        return enregistrer(0)

    wq = WriteQueue()
    wq.start()
    premiere = wq.submit(premiere_commande)
    futures = [wq.submit(partial(enregistrer, i)) for i in range(1, 5)]
    porte.set()
    wq.stop(timeout=5)  # doit drainer les commandes déjà en file avant d'arrêter

    assert premiere.result(timeout=2) == 0
    for f in futures:
        assert f.done()
    assert executees == [0, 1, 2, 3, 4]


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_les_lectures_restent_concurrentes_pendant_une_ecriture(tmp_path: Path) -> None:
    """Une écriture en cours (transaction ouverte) ne bloque pas une lecture (mode WAL)."""
    db = Database(_sqlite_url(tmp_path / "kervignarc.db"))
    with db.engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE t (id INTEGER PRIMARY KEY)")

    ecriture_engagee = threading.Event()
    liberer = threading.Event()

    def ecriture_lente() -> str:
        with db.engine.begin() as conn:
            conn.exec_driver_sql("INSERT INTO t (id) VALUES (1)")
            ecriture_engagee.set()  # transaction ouverte, non commitée
            liberer.wait(2)
        return "commité"

    try:
        with WriteQueue() as wq:
            future = wq.submit(ecriture_lente)
            assert ecriture_engagee.wait(2)

            # La lecture doit aboutir immédiatement, sur le snapshot d'avant l'écriture.
            with db.engine.connect() as conn:
                pendant = conn.exec_driver_sql("SELECT count(*) FROM t").scalar()
            assert pendant == 0

            liberer.set()
            assert future.result(timeout=2) == "commité"

        with db.engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT count(*) FROM t").scalar() == 1
    finally:
        db.engine.dispose()
