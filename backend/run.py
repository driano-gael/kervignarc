"""Point d'entrée du binaire de release (E11US001).

Pendant « production » de `run_dev.py`. Différences avec l'entrée de dev :

- **pas de build front** : le front est déjà embarqué dans le binaire (spec PyInstaller) ;
- **écoute `0.0.0.0`** et non `127.0.0.1` : les tablettes du réseau local doivent atteindre
  le serveur — sur la boucle locale elles ne le pourraient pas. C'est le sens même de
  « mise en réseau » de l'US ;
- **base à côté de l'exécutable**, migrée au **1er lancement** (créée si absente) ;
- **annonce mDNS** `kervignarc.local` pendant toute la vie du serveur.

Séquence : résoudre les chemins → publier base/front via l'environnement (source unique lue
par la composition root ET par Alembic) → migrer → annoncer mDNS → servir API + WS + SPA.
"""

from __future__ import annotations

import os

import uvicorn

from infrastructure.db.migrate import appliquer_migrations
from release import chemins, reseau

# Port **fixe** documenté, visé par les tablettes. Écoute sur **toutes** les interfaces
# (`0.0.0.0`) : exposition LAN volontaire du jour J — cf. docs/deploiement.md.
HOST = "0.0.0.0"
PORT = 8000


def _configurer_environnement() -> None:
    """Fixe la base (à côté de l'exe) et le front embarqué, sans écraser une surcharge.

    `setdefault` : si l'exploitant a déjà positionné `KERVIGNARC_DATABASE_URL` ou
    `KERVIGNARC_FRONTEND_DIST` (chemin réseau, base de test), on respecte son choix.
    """
    os.environ.setdefault("KERVIGNARC_DATABASE_URL", chemins.url_base_donnees())
    os.environ.setdefault("KERVIGNARC_FRONTEND_DIST", str(chemins.dossier_front()))


def main() -> None:
    """Migrations (base au 1er lancement) → annonce mDNS → serveur unique sur le port fixe."""
    _configurer_environnement()

    print("-> Migrations de la base (création au 1er lancement si absente)...")
    appliquer_migrations(chemins.dossier_migrations())

    # Import tardif : la composition root lit l'environnement fixé ci-dessus au câblage.
    from bootstrap.composition import create_app

    ip = reseau.adresse_lan()
    with reseau.PublicationMdns(PORT, ip=ip) as publication:
        # On n'annonce `kervignarc.local` que s'il a **vraiment** été publié : sinon (mDNS
        # indisponible) l'afficher induirait l'exploitant en erreur — seul l'accès par IP marche.
        acces = f"http://{ip}:{PORT}"
        if publication.actif:
            acces += f"  et  http://{reseau.NOM_HOTE}.local:{PORT}"
        print(f"-> Serveur prêt sur {acces}  (API + WebSocket + SPA)")
        if not publication.actif:
            # Indice de diagnostic : sans ce message, une publication mDNS avalée (best-effort)
            # laisserait l'exploitant sans explication du « pourquoi » — l'accès par IP reste sûr.
            print(
                f"   (nom {reseau.NOM_HOTE}.local non publié — mDNS indisponible sur ce réseau ; "
                f"utiliser l'adresse IP ci-dessus)"
            )
        uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
