"""Tests de la découverte réseau (E11US001) : adresse LAN + robustesse mDNS.

Tests **après implémentation** (câblage). Volontairement **sans réseau réel** (règle 9,
déterminisme) : on ne démarre **pas** une vraie pile zeroconf en test — on vérifie que
`adresse_lan` renvoie une IPv4 valide et que la publication mDNS est **best-effort**, c.-à-d.
qu'une pile indisponible n'empêche **jamais** le serveur de démarrer.
"""

from __future__ import annotations

import socket

import pytest

from release import reseau


def test_adresse_lan_est_une_ipv4_valide() -> None:
    """`adresse_lan` renvoie une IPv4 bien formée (parseable par `inet_aton`), réseau ou non."""
    ip = reseau.adresse_lan()
    socket.inet_aton(ip)  # lève si la chaîne n'est pas une IPv4 → test rouge


def test_publication_mdns_avale_l_echec(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pile mDNS KO → aucune exception ne remonte, le contexte s'ouvre sans service publié."""

    class ZeroconfIndisponible:
        def __init__(self) -> None:
            raise OSError("aucune pile mDNS")

    monkeypatch.setattr(reseau, "Zeroconf", ZeroconfIndisponible)

    with reseau.PublicationMdns(8000, ip="127.0.0.1") as publication:
        assert publication._zc is None  # rien de publié, mais pas d'exception : démarrage garanti
