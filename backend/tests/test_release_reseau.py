"""Tests de la découverte réseau (E11US001) : adresse LAN + robustesse mDNS.

Tests **après implémentation** (câblage). Volontairement **sans réseau réel** (règle 9,
déterminisme) : on ne démarre **pas** une vraie pile zeroconf en test — on vérifie que
`adresse_lan` renvoie une IPv4 valide et que la publication mDNS est **best-effort**, c.-à-d.
qu'une pile indisponible n'empêche **jamais** le serveur de démarrer.
"""

from __future__ import annotations

import socket

import pytest
from zeroconf import NonUniqueNameException

from release import reseau


def test_adresse_lan_est_une_ipv4_valide() -> None:
    """`adresse_lan` renvoie une IPv4 bien formée (parseable par `inet_aton`), réseau ou non."""
    ip = reseau.adresse_lan()
    socket.inet_aton(ip)  # lève si la chaîne n'est pas une IPv4 → test rouge


def test_publication_mdns_avale_l_echec_de_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pas de pile mDNS (`Zeroconf()` lève `OSError`) → contexte ouvert, rien publié."""

    class ZeroconfIndisponible:
        def __init__(self) -> None:
            raise OSError("aucune pile mDNS")

    monkeypatch.setattr(reseau, "Zeroconf", ZeroconfIndisponible)

    with reseau.PublicationMdns(8000, ip="127.0.0.1") as publication:
        assert publication.actif is False  # pas d'exception : démarrage garanti


def test_publication_mdns_avale_la_collision_de_nom(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collision `kervignarc.local` : `register_service` lève une `zeroconf.Error` (PAS `OSError`).

    C'est le vrai chemin de panne du jour J (2ᵉ instance / redémarrage rapide) : le serveur doit
    démarrer quand même, et la pile Zeroconf déjà construite doit être fermée (pas de fuite).
    """
    ferme = {"appele": False}

    class ZeroconfCollision:
        def __init__(self) -> None:
            pass

        def register_service(self, info: object) -> None:
            raise NonUniqueNameException()  # sous-classe de zeroconf.Error, pas d'OSError

        def close(self) -> None:
            ferme["appele"] = True

    monkeypatch.setattr(reseau, "Zeroconf", ZeroconfCollision)

    with reseau.PublicationMdns(8000, ip="127.0.0.1") as publication:
        assert publication.actif is False  # défaillance non-OSError avalée : démarrage garanti
    assert ferme["appele"] is True  # la pile construite a bien été refermée (pas de fuite)
