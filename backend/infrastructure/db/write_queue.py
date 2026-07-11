"""File d'écriture SQLite — sérialisation par un writer unique (guide §7, ADR-0005).

SQLite n'accepte **qu'un seul écrivain** : plutôt que de risquer des `database is
locked` sous ~30 clients, **toutes les écritures transitent par une file**
(`queue.Queue`) consommée par **un unique thread worker**. Les commandes sont donc
exécutées **séquentiellement**, dans leur ordre de soumission — sérialisation *par
construction*, sans verrou applicatif.

L'appelant (handler FastAPI, `async`) **soumet une commande** et récupère une
`Future` (`concurrent.futures.Future`) : il en attend le résultat sans bloquer la
boucle événementielle (`asyncio.wrap_future`). Les **lectures ne passent pas** par
cette file : directes et synchrones, elles restent concurrentes (mode WAL).

Ce **point de passage unique** est l'endroit où brancher, après commit, les traitements
transverses via des **listeners post-commit** : chaque commande réussie notifie les
listeners enregistrés avec son résultat — c'est ainsi que la diffusion WebSocket est
déclenchée (E00US008), et où viendra le journal d'audit. Un seul endroit à instrumenter.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any, TypeVar

_logger = logging.getLogger(__name__)

_T = TypeVar("_T")

WriteCommand = Callable[[], _T]
"""Unité d'écriture : un callable synchrone, sans argument, renvoyant son résultat."""

PostCommitListener = Callable[[Any], None]
"""Rappel exécuté après une écriture réussie, avec le résultat de la commande."""

# Élément de file : (commande, future) à exécuter, ou `None` = sentinelle d'arrêt.
_QueueItem = tuple["WriteCommand[Any]", "Future[Any]"] | None


class WriteQueueClosedError(RuntimeError):
    """Soumission refusée : la file est fermée (pas encore démarrée ou déjà arrêtée)."""


class WriteQueue:
    """File d'écriture à writer unique : sérialise les commandes d'écriture.

    Cycle de vie : `start()` lance le thread worker ; `stop()` draine les commandes
    déjà en file, puis arrête le worker. Utilisable comme gestionnaire de contexte.
    """

    def __init__(self, name: str = "kervignarc-writer") -> None:
        self._queue: queue.Queue[_QueueItem] = queue.Queue()
        self._name = name
        self._thread: threading.Thread | None = None
        self._closed = False
        self._lock = threading.Lock()
        self._post_commit: list[PostCommitListener] = []

    def add_post_commit_listener(self, listener: PostCommitListener) -> None:
        """Enregistre un rappel exécuté après chaque écriture réussie (avant `start()`).

        Le listener reçoit le résultat de la commande ; il doit être **rapide et
        non bloquant** (il s'exécute sur le thread du writer). Une exception qu'il lève
        est journalisée et **n'interrompt pas** le writer ni la `Future` de l'appelant.
        """
        self._post_commit.append(listener)

    def start(self) -> None:
        """Démarre le thread worker (idempotent)."""
        with self._lock:
            if self._thread is not None:
                return
            self._closed = False
            self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
            self._thread.start()

    def submit(self, command: WriteCommand[_T]) -> Future[_T]:
        """Met `command` en file et renvoie une `Future` portant son résultat.

        La commande est exécutée par l'unique worker, **après** les commandes déjà en
        file (FIFO). Lève `WriteQueueClosedError` si la file n'est pas démarrée ou est
        en cours d'arrêt.
        """
        future: Future[_T] = Future()
        with self._lock:
            if self._closed or self._thread is None:
                raise WriteQueueClosedError("La file d'écriture n'accepte plus de commandes.")
            self._queue.put((command, future))
        return future

    def stop(self, timeout: float | None = None) -> None:
        """Arrête le worker après avoir drainé les commandes en attente (idempotent).

        La sentinelle est mise en file **après** les commandes déjà soumises : le worker
        les exécute toutes avant de s'arrêter (drain naturel). `timeout` borne l'attente
        de la fin du thread.
        """
        with self._lock:
            if self._thread is None:
                return
            self._closed = True
            thread = self._thread
        self._queue.put(None)
        thread.join(timeout)
        with self._lock:
            self._thread = None

    def _run(self) -> None:
        """Boucle du worker : exécute les commandes une à une, jusqu'à la sentinelle."""
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                command, future = item
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    result = command()
                except Exception as exc:  # propagé à l'appelant via la Future
                    future.set_exception(exc)
                else:
                    self._notify_post_commit(result)
                    future.set_result(result)
            finally:
                self._queue.task_done()

    def _notify_post_commit(self, result: Any) -> None:
        """Notifie les listeners post-commit ; isole leurs erreurs du writer."""
        for listener in self._post_commit:
            try:
                listener(result)
            except Exception:
                _logger.exception("Listener post-commit en échec (écriture déjà commitée).")

    def __enter__(self) -> WriteQueue:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
