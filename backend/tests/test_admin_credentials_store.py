"""Tests du store d'identifiants admin sur fichier `.env` (E10US002).

Vérifie : absence d'accès quand le fichier ou une clé manque ; aller-retour écriture→lecture ;
**upsert** préservant les autres clés/commentaires ; tolérance à une valeur éditée à la main
(avec/sans guillemets englobants).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from application.auth import IdentifiantsAdmin
from infrastructure.auth import AdminCredentialsStore


def test_lire_non_configure_si_fichier_absent(tmp_path: Path) -> None:
    """Aucun fichier `.env` → aucun accès configuré."""
    store = AdminCredentialsStore(tmp_path / ".env")
    assert store.lire() is None


def test_lire_non_configure_si_cle_manquante(tmp_path: Path) -> None:
    """Login présent mais mot de passe absent → non configuré."""
    env = tmp_path / ".env"
    env.write_text("KERVIGNARC_ADMIN_LOGIN=admin\n", encoding="utf-8")
    store = AdminCredentialsStore(env)
    assert store.lire() is None


def test_ecrire_puis_lire_aller_retour(tmp_path: Path) -> None:
    """Écriture puis relecture renvoient les mêmes identifiants."""
    store = AdminCredentialsStore(tmp_path / ".env")
    store.ecrire(IdentifiantsAdmin(login="orga", mot_de_passe="mdp très secret"))
    relu = store.lire()
    assert relu == IdentifiantsAdmin(login="orga", mot_de_passe="mdp très secret")


def test_upsert_preserve_les_autres_lignes(tmp_path: Path) -> None:
    """Écrire les identifiants ne détruit ni les commentaires ni les autres clés."""
    env = tmp_path / ".env"
    env.write_text(
        "# Config locale\nKERVIGNARC_DATABASE_URL=sqlite:///kervignarc.db\n",
        encoding="utf-8",
    )
    store = AdminCredentialsStore(env)
    store.ecrire(IdentifiantsAdmin(login="orga", mot_de_passe="secret"))
    contenu = env.read_text(encoding="utf-8")
    assert "# Config locale" in contenu
    assert "KERVIGNARC_DATABASE_URL=sqlite:///kervignarc.db" in contenu
    assert "KERVIGNARC_ADMIN_LOGIN=orga" in contenu
    assert store.lire() == IdentifiantsAdmin(login="orga", mot_de_passe="secret")


def test_upsert_remplace_sans_dupliquer(tmp_path: Path) -> None:
    """Réécrire remplace la valeur existante en place (pas de doublon de clé)."""
    env = tmp_path / ".env"
    store = AdminCredentialsStore(env)
    store.ecrire(IdentifiantsAdmin(login="orga", mot_de_passe="v1"))
    store.ecrire(IdentifiantsAdmin(login="orga", mot_de_passe="v2"))
    contenu = env.read_text(encoding="utf-8")
    assert contenu.count("KERVIGNARC_ADMIN_PASSWORD=") == 1
    assert store.lire() == IdentifiantsAdmin(login="orga", mot_de_passe="v2")


def test_ecriture_atomique_ne_laisse_aucun_temporaire(tmp_path: Path) -> None:
    """L'écriture atomique (`.tmp` voisin puis `os.replace`) ne laisse **aucun résidu** au succès.

    `.env` est la porte de secours de l'accès admin : on l'écrit atomiquement pour qu'un crash ne
    le tronque jamais. Mais le temporaire ne doit pas subsister — ni polluer le dossier, ni laisser
    croire à une écriture en cours. On vérifie qu'aucun `*.tmp` ne reste et que le `.env` final est
    bien relu.
    """
    env = tmp_path / ".env"
    AdminCredentialsStore(env).ecrire(IdentifiantsAdmin(login="orga", mot_de_passe="secret"))
    assert list(tmp_path.glob("*.tmp")) == []
    assert AdminCredentialsStore(env).lire() == IdentifiantsAdmin(
        login="orga", mot_de_passe="secret"
    )


@pytest.mark.parametrize(
    "mot_de_passe",
    ["  espaces autour  ", '"déjà entre guillemets"', "avec = et # dedans", "simple"],
)
def test_ecrire_puis_lire_fidelite(tmp_path: Path, mot_de_passe: str) -> None:
    """L'écriture puis la relecture rendent la valeur **à l'identique**, même ambiguë (espaces de
    bord, guillemets englobants, caractères spéciaux) — garde-fou contre un lockout silencieux."""
    store = AdminCredentialsStore(tmp_path / ".env")
    store.ecrire(IdentifiantsAdmin(login="orga", mot_de_passe=mot_de_passe))
    assert store.lire() == IdentifiantsAdmin(login="orga", mot_de_passe=mot_de_passe)


def test_lire_valeur_editee_a_la_main_avec_guillemets(tmp_path: Path) -> None:
    """Une valeur saisie à la main avec des guillemets englobants est correctement dé-quotée."""
    env = tmp_path / ".env"
    env.write_text(
        'KERVIGNARC_ADMIN_LOGIN="admin"\nKERVIGNARC_ADMIN_PASSWORD="secret"\n',
        encoding="utf-8",
    )
    assert AdminCredentialsStore(env).lire() == IdentifiantsAdmin(
        login="admin", mot_de_passe="secret"
    )
