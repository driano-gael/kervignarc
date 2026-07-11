"""Tests du hub de diffusion temps réel (E00US008, ADR-0005).

Vérifie le pont **thread → boucle asyncio** (le writer publie depuis un thread, les
abonnés reçoivent sur la boucle) et le fan-out à plusieurs abonnés.
"""

from __future__ import annotations

import asyncio
import threading

from infrastructure.realtime import Broadcaster, LiveEvent


def test_publie_depuis_un_autre_thread_vers_un_abonne() -> None:
    """`publish()` appelé depuis un thread (comme le writer) atteint l'abonné asyncio."""

    async def scenario() -> LiveEvent:
        broadcaster = Broadcaster()
        broadcaster.bind_loop(asyncio.get_running_loop())
        with broadcaster.subscribe() as subscription:
            # Publication depuis un thread distinct : simule le worker d'écriture.
            threading.Thread(
                target=broadcaster.publish,
                args=(LiveEvent("demo", {"n": 1}),),
            ).start()
            return await asyncio.wait_for(subscription.receive(), timeout=2)

    assert asyncio.run(scenario()) == LiveEvent("demo", {"n": 1})


def test_fan_out_vers_tous_les_abonnes() -> None:
    """Un événement publié est distribué à tous les abonnés connectés."""

    async def scenario() -> list[LiveEvent]:
        broadcaster = Broadcaster()
        broadcaster.bind_loop(asyncio.get_running_loop())
        with broadcaster.subscribe() as a, broadcaster.subscribe() as b:
            assert broadcaster.subscriber_count() == 2
            broadcaster.publish(LiveEvent("tick"))
            return [
                await asyncio.wait_for(a.receive(), timeout=2),
                await asyncio.wait_for(b.receive(), timeout=2),
            ]

    recus = asyncio.run(scenario())
    assert recus == [LiveEvent("tick"), LiveEvent("tick")]


def test_desabonnement_retire_l_abonne() -> None:
    """`close()` retire l'abonné du hub (plus de fan-out vers lui)."""

    async def scenario() -> int:
        broadcaster = Broadcaster()
        broadcaster.bind_loop(asyncio.get_running_loop())
        subscription = broadcaster.subscribe()
        assert broadcaster.subscriber_count() == 1
        subscription.close()
        return broadcaster.subscriber_count()

    assert asyncio.run(scenario()) == 0


def test_publish_sans_boucle_liee_est_ignore() -> None:
    """Sans boucle liée (app arrêtée), publier ne lève pas et ne fait rien."""
    broadcaster = Broadcaster()
    broadcaster.publish(LiveEvent("perdu"))  # ne doit pas lever
