"""Découverte réseau du binaire : adresse LAN + annonce mDNS (E11US001).

Le jour J il n'y a **pas d'internet** : les ~30 tablettes rejoignent un routeur dédié. Deux chemins
d'accès (`docs/deploiement.md`) — par IP locale, toujours disponible ; par nom mDNS
`kervignarc.local`, publié ici via zeroconf sans rien configurer sur le routeur. ⚠️ La publication
mDNS est **best-effort** : une pile absente, un pare-feu ou un réseau capricieux ne doivent jamais
empêcher le serveur de démarrer — l'accès par IP est le filet, affiché au lancement.
"""

from __future__ import annotations

import socket
from types import TracebackType

from zeroconf import ServiceInfo, Zeroconf

# Nom d'hôte annoncé : `kervignarc.local` (le suffixe `.local` est celui du domaine mDNS).
NOM_HOTE = "kervignarc"
_TYPE_SERVICE = "_http._tcp.local."
_NOM_SERVICE = f"{NOM_HOTE}.{_TYPE_SERVICE}"


def adresse_lan() -> str:
    """Meilleure IP LAN de la machine, **sans émettre de paquet**.

    Astuce classique : on « connecte » un socket UDP vers une adresse externe. UDP étant
    sans connexion, aucune trame n'est réellement envoyée, mais l'OS choisit l'interface de
    sortie dont on lit l'IP locale. Repli sur `127.0.0.1` si tout échoue (machine sans réseau).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))  # TEST-NET-1 (RFC 5737) : jamais routé sur un vrai réseau
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class PublicationMdns:
    """Publie `kervignarc.local` en mDNS pendant la durée de vie du serveur.

    Gestionnaire de contexte : `with PublicationMdns(port): uvicorn.run(...)`. La
    publication est tentée à l'entrée et retirée proprement à la sortie. Toute défaillance
    (pas de pile mDNS, port occupé, pare-feu, **collision du nom `kervignarc.local`**) est
    **avalée** : le serveur tourne quand même, accessible par IP. `actif` dit si le nom a
    effectivement été publié.
    """

    def __init__(self, port: int, ip: str | None = None) -> None:
        self._port = port
        self._ip = ip or adresse_lan()
        self._zc: Zeroconf | None = None

    @property
    def actif(self) -> bool:
        """Vrai si le service mDNS est effectivement publié (sinon : replié sur l'accès par IP)."""
        return self._zc is not None

    def __enter__(self) -> PublicationMdns:
        try:
            # `self._zc` est assigné **avant** `register_service` : si l'enregistrement échoue,
            # `_fermer()` doit pouvoir refermer la pile déjà construite (threads + sockets
            # multicast), sinon elle fuite jusqu'à la fin du processus.
            self._zc = Zeroconf()
            info = ServiceInfo(
                _TYPE_SERVICE,
                _NOM_SERVICE,
                addresses=[socket.inet_aton(self._ip)],
                port=self._port,
                server=f"{NOM_HOTE}.local.",
            )
            self._zc.register_service(info)
        except Exception:
            # Best-effort **littéral** : aucune défaillance mDNS ne doit empêcher le serveur de
            # démarrer le jour J. Capture volontairement large — au-delà d'`OSError` (pas de pile
            # mDNS, port pris, pare-feu), zeroconf lève ses propres `zeroconf.Error` qui n'en
            # dérivent pas : collision du nom `kervignarc.local` (double-lancement, redémarrage
            # rapide) ou boucle d'événements bloquée (Wi-Fi saturé). L'accès par IP reste le filet.
            # `KeyboardInterrupt`/`SystemExit` (BaseException) ne sont pas avalés.
            self._fermer()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._fermer()

    def _fermer(self) -> None:
        if self._zc is not None:
            self._zc.close()
            self._zc = None
