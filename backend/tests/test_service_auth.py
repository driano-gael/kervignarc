"""Tests du service applicatif d'accès admin (E10US002).

Couvre le cycle : non configuré → configurer (ouvre une session) → connexion (bonne/mauvaise) →
déconnexion. Utilise les adapters réels (store `.env` sur `tmp_path`, store de sessions en
mémoire) pour un test proche de l'intégration, sans DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from application.auth import ServiceAuth
from application.erreurs import (
    AccesDejaConfigure,
    AccesNonConfigure,
    IdentifiantsInvalides,
)
from infrastructure.auth import AdminCredentialsStore, SessionStore


def _service(tmp_path: Path) -> ServiceAuth:
    return ServiceAuth(AdminCredentialsStore(tmp_path / ".env"), SessionStore())


def test_non_configure_au_depart(tmp_path: Path) -> None:
    """Aucun identifiant → `est_configure` faux."""
    assert _service(tmp_path).est_configure() is False


def test_configurer_ouvre_une_session_valide(tmp_path: Path) -> None:
    """Configurer définit l'accès et renvoie un jeton de session valide."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "secret")
    assert service.est_configure() is True
    assert service.session_valide(jeton) is True


def test_configurer_deux_fois_refuse(tmp_path: Path) -> None:
    """Reconfigurer un accès déjà défini est refusé (la modif relève d'E10US006)."""
    service = _service(tmp_path)
    service.configurer("admin", "secret")
    with pytest.raises(AccesDejaConfigure):
        service.configurer("autre", "autre")


@pytest.mark.parametrize("login, mot_de_passe", [("admin", ""), ("", "secret"), ("   ", "secret")])
def test_configurer_champs_vides_refuse(tmp_path: Path, login: str, mot_de_passe: str) -> None:
    """Login ou mot de passe vide → identifiants invalides."""
    with pytest.raises(IdentifiantsInvalides):
        _service(tmp_path).configurer(login, mot_de_passe)


def test_connexion_avant_configuration_refuse(tmp_path: Path) -> None:
    """Se connecter sans accès défini → `AccesNonConfigure`."""
    with pytest.raises(AccesNonConfigure):
        _service(tmp_path).connexion("admin", "secret")


def test_connexion_mauvais_identifiants_refuse(tmp_path: Path) -> None:
    """Un login ou mot de passe erroné → `IdentifiantsInvalides`."""
    service = _service(tmp_path)
    service.configurer("admin", "secret")
    with pytest.raises(IdentifiantsInvalides):
        service.connexion("admin", "faux")
    with pytest.raises(IdentifiantsInvalides):
        service.connexion("intrus", "secret")


def test_connexion_bons_identifiants_ouvre_session(tmp_path: Path) -> None:
    """Les bons identifiants ouvrent une session valide (persistée entre instances)."""
    _service(tmp_path).configurer("admin", "secret")
    # Nouvelle instance : lit l'accès depuis `.env`, indépendamment de la session initiale.
    service = _service(tmp_path)
    jeton = service.connexion("admin", "secret")
    assert service.session_valide(jeton) is True


def test_deconnexion_invalide_le_jeton(tmp_path: Path) -> None:
    """Après déconnexion, le jeton n'est plus valide."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "secret")
    service.deconnexion(jeton)
    assert service.session_valide(jeton) is False


def test_session_valide_refuse_jeton_absent(tmp_path: Path) -> None:
    """Un jeton `None` ou inconnu n'est jamais valide."""
    service = _service(tmp_path)
    service.configurer("admin", "secret")
    assert service.session_valide(None) is False
    assert service.session_valide("jeton-bidon") is False


def test_connexion_identifiants_non_ascii(tmp_path: Path) -> None:
    """Un mot de passe accentué (public FR) doit fonctionner à la reconnexion (garde-fou B1).

    `hmac.compare_digest` sur des `str` non-ASCII lève `TypeError` : la comparaison passe par des
    octets. On reconfigure via une nouvelle instance pour forcer le vrai chemin de `connexion`.
    """
    _service(tmp_path).configurer("délégué", "Décembre-2026")
    service = _service(tmp_path)
    jeton = service.connexion("délégué", "Décembre-2026")
    assert service.session_valide(jeton) is True
    with pytest.raises(IdentifiantsInvalides):
        service.connexion("délégué", "decembre-2026")


# Sauts de ligne construits via chr() (pas d'échappement littéral en source).
@pytest.mark.parametrize("valeur", [f"a{chr(10)}b", f"ab{chr(10)}", f"a{chr(13)}b"])
def test_configurer_rejette_saut_de_ligne(tmp_path: Path, valeur: str) -> None:
    """Un saut de ligne dans le mot de passe est refusé (anti-injection de clé `.env`, M1)."""
    with pytest.raises(IdentifiantsInvalides):
        _service(tmp_path).configurer("admin", valeur)


def test_configurer_accepte_espace_interne(tmp_path: Path) -> None:
    """Un espace interne dans le mot de passe reste autorisé (ce n'est pas un saut de ligne)."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "mot de passe long")
    assert service.session_valide(jeton) is True
