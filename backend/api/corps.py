"""Lecture d'un corps de requête **borné en flux** — partagée par les dépôts de fichier."""

from __future__ import annotations

from fastapi import Request

from application.erreurs import CorpsHorsDeProportion


async def lire_le_corps_borne(request: Request, plafond_octets: int) -> bytes:
    """Lit le corps de la requête **en s'arrêtant** au plafond, au lieu de le borner après coup.

    ⚠️ `Request.body()` accumule **tout** le flux avant de rendre la main : borner après coup
    mettait bel et bien 20 Mo en mémoire avant de refuser. Deux contrôles et non un :
    `Content-Length` refuse sans lire quand il est annoncé, le cumul en flux couvre le transfert
    **chunké**. C'est le serveur **unique** du gymnase qui paierait.
    """
    annonce = request.headers.get("content-length")
    if annonce is not None and annonce.isdigit() and int(annonce) > plafond_octets:
        raise CorpsHorsDeProportion("Corps de requête hors de proportion.")
    morceaux = bytearray()
    async for morceau in request.stream():
        morceaux.extend(morceau)
        if len(morceaux) > plafond_octets:
            raise CorpsHorsDeProportion("Corps de requête hors de proportion.")
    return bytes(morceaux)
