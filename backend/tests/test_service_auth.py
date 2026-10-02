"""Tests du service applicatif d'accès admin (E10US002, E10US006).

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
    MotDePasseActuelIncorrect,
    NonAuthentifie,
    NouveauxIdentifiantsInvalides,
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


# --- E10US006 : modifier les identifiants depuis une session admin ---------------------------
# Tests écrits depuis la puce CA de `stories/E10-acces-roles.md` (E10US006), avant le code.


def test_modifier_mot_de_passe_remplace_l_ancien(tmp_path: Path) -> None:
    """Nouveau mot de passe : l'ancien ne connecte plus, le nouveau oui (`.env` réécrit)."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "secret")
    service.modifier(jeton, "secret", nouveau_login=None, nouveau_mot_de_passe="neuf")
    relu = _service(tmp_path)
    with pytest.raises(IdentifiantsInvalides):
        relu.connexion("admin", "secret")
    assert relu.session_valide(relu.connexion("admin", "neuf")) is True


def test_modifier_login_seul_garde_le_mot_de_passe(tmp_path: Path) -> None:
    """Login seul : le mot de passe est conservé, l'ancien login ne connecte plus."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "secret")
    service.modifier(jeton, "secret", nouveau_login="arbitre", nouveau_mot_de_passe=None)
    relu = _service(tmp_path)
    with pytest.raises(IdentifiantsInvalides):
        relu.connexion("admin", "secret")
    assert relu.session_valide(relu.connexion("arbitre", "secret")) is True


def test_modifier_les_deux_a_la_fois(tmp_path: Path) -> None:
    """Login et mot de passe changés ensemble."""
    service = _service(tmp_path)
    jeton = service.configurer("admin", "secret")
    service.modifier(jeton, "secret", nouveau_login="arbitre", nouveau_mot_de_passe="neuf")
    relu = _service(tmp_path)
    assert relu.session_valide(relu.connexion("arbitre", "neuf")) is True


def test_modifier_garde_la_session_courante_et_ferme_les_autres(tmp_path: Path) -> None:
    """Faire tourner l'accès éjecte les autres sessions ; celle qui a fait le changement reste."""
    service = _service(tmp_path)
    courante = service.configurer("admin", "secret")
    autre_tablette = service.connexion("admin", "secret")
    service.modifier(courante, "secret", nouveau_login=None, nouveau_mot_de_passe="neuf")
    assert service.session_valide(courante) is True
    assert service.session_valide(autre_tablette) is False


def test_modifier_mot_de_passe_actuel_faux_refuse_sans_rien_toucher(tmp_path: Path) -> None:
    """Mot de passe actuel faux : refus dédié, `.env` intact, aucune session fermée."""
    service = _service(tmp_path)
    courante = service.configurer("admin", "secret")
    autre = service.connexion("admin", "secret")
    with pytest.raises(MotDePasseActuelIncorrect):
        service.modifier(courante, "faux", nouveau_login=None, nouveau_mot_de_passe="neuf")
    assert service.session_valide(courante) is True
    assert service.session_valide(autre) is True
    assert _service(tmp_path).connexion("admin", "secret")


def test_modifier_mot_de_passe_actuel_non_ascii(tmp_path: Path) -> None:
    """Le mot de passe actuel accentué est comparé en octets (même piège qu'à la connexion)."""
    service = _service(tmp_path)
    jeton = service.configurer("délégué", "Décembre-2026")
    service.modifier(jeton, "Décembre-2026", nouveau_login=None, nouveau_mot_de_passe="Été")
    assert _service(tmp_path).connexion("délégué", "Été")


@pytest.mark.parametrize(
    "nouveau_login, nouveau_mot_de_passe",
    [
        (None, None),  # rien demandé
        ("admin", None),  # login identique
        (None, "secret"),  # mot de passe identique
        ("admin", "secret"),  # les deux identiques
    ],
)
def test_modifier_sans_changement_refuse(
    tmp_path: Path, nouveau_login: str | None, nouveau_mot_de_passe: str | None
) -> None:
    """Une demande qui ne change rien est refusée, et ne ferme aucune autre session."""
    service = _service(tmp_path)
    courante = service.configurer("admin", "secret")
    autre = service.connexion("admin", "secret")
    with pytest.raises(NouveauxIdentifiantsInvalides):
        service.modifier(courante, "secret", nouveau_login, nouveau_mot_de_passe)
    assert service.session_valide(autre) is True


@pytest.mark.parametrize(
    "nouveau_login, nouveau_mot_de_passe",
    [("", None), ("   ", None), (None, ""), (f"a{chr(10)}b", None), (None, f"a{chr(13)}b")],
)
def test_modifier_nouvelles_valeurs_mal_formees_refuse(
    tmp_path: Path, nouveau_login: str | None, nouveau_mot_de_passe: str | None
) -> None:
    """Vide ou saut de ligne : refus dédié (pas `IdentifiantsInvalides`, un 401), `.env` intact."""
    service = _service(tmp_path)
    courante = service.configurer("admin", "secret")
    with pytest.raises(NouveauxIdentifiantsInvalides):
        service.modifier(courante, "secret", nouveau_login, nouveau_mot_de_passe)
    assert service.session_valide(courante) is True
    assert _service(tmp_path).connexion("admin", "secret")


def test_modifier_sans_session_valide_refuse(tmp_path: Path) -> None:
    """Hors session admin valide, rien n'est modifié."""
    service = _service(tmp_path)
    service.configurer("admin", "secret")
    with pytest.raises(NonAuthentifie):
        service.modifier("jeton-bidon", "secret", nouveau_login=None, nouveau_mot_de_passe="neuf")
    assert _service(tmp_path).connexion("admin", "secret")
