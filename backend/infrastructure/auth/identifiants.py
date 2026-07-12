"""Adapter : identifiants admin persistés dans un fichier `.env` local (E10US002).

Compromis de sécurité **assumé** (outil mono-club LAN, cf. story E10US002) : le login et le
mot de passe admin vivent en clair dans un fichier `.env` (clés `KERVIGNARC_ADMIN_LOGIN` /
`KERVIGNARC_ADMIN_PASSWORD`), lisible/éditable sur la machine serveur. Ce fichier est aussi la
**porte de secours** en cas d'oubli : l'éditer (ou vider les clés) redéclenche la définition au
prochain accès. `.env` est **hors versionnage** (`.gitignore`).

Lecture/écriture en **bibliothèque standard** (parcimonie, ADR-0009) : un mini-parseur
`KEY=VALEUR` suffisant pour ces deux clés. L'écriture fait un **upsert** ligne à ligne : elle
remplace les deux clés visées et **préserve** le reste du fichier (autres clés, commentaires).
"""

from __future__ import annotations

from pathlib import Path

from application.auth import IdentifiantsAdmin
from infrastructure.erreurs import InfrastructureError

CLE_LOGIN = "KERVIGNARC_ADMIN_LOGIN"
CLE_MOT_DE_PASSE = "KERVIGNARC_ADMIN_PASSWORD"


def _cle_de_ligne(ligne: str) -> str | None:
    """Nom de clé d'une ligne `KEY=VALEUR`, ou `None` (ligne vide, commentaire, sans `=`)."""
    depouillee = ligne.strip()
    if depouillee == "" or depouillee.startswith("#") or "=" not in depouillee:
        return None
    return depouillee.split("=", 1)[0].strip()


def _valeur_de_ligne(ligne: str) -> str:
    """Valeur brute d'une ligne `KEY=VALEUR` : espaces et un éventuel guillemet englobant ôtés."""
    valeur = ligne.split("=", 1)[1].strip()
    if _est_encadree_de_guillemets(valeur):
        valeur = valeur[1:-1]
    return valeur


def _est_encadree_de_guillemets(valeur: str) -> bool:
    return len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in ("'", '"')


def _formater_valeur(valeur: str) -> str:
    """Sérialise une valeur pour `.env`, fidèle à l'aller-retour du lecteur.

    Entoure de guillemets doubles quand une écriture brute serait relue différemment — valeur à
    espaces de bord (le lecteur `strip()`), ou déjà encadrée de guillemets (le lecteur en retire
    une paire). Sinon écrit la valeur telle quelle. Les sauts de ligne sont exclus en amont
    (couche service), donc aucun échappement n'est nécessaire ici.
    """
    if valeur != valeur.strip() or _est_encadree_de_guillemets(valeur):
        return f'"{valeur}"'
    return valeur


class AdminCredentialsStore:
    """Lit/écrit les identifiants admin dans un fichier `.env` (adapter sortant)."""

    def __init__(self, env_path: Path) -> None:
        self._env_path = env_path

    def lire(self) -> IdentifiantsAdmin | None:
        """Identifiants configurés, ou `None` si login ou mot de passe est absent/vide."""
        valeurs = self._lire_valeurs()
        login = valeurs.get(CLE_LOGIN, "")
        mot_de_passe = valeurs.get(CLE_MOT_DE_PASSE, "")
        if login == "" or mot_de_passe == "":
            return None
        return IdentifiantsAdmin(login=login, mot_de_passe=mot_de_passe)

    def ecrire(self, identifiants: IdentifiantsAdmin) -> None:
        """Écrit (upsert) les deux clés dans `.env` en préservant le reste du fichier."""
        self._upsert(
            {
                CLE_LOGIN: identifiants.login,
                CLE_MOT_DE_PASSE: identifiants.mot_de_passe,
            }
        )

    def _lignes(self) -> list[str]:
        if not self._env_path.exists():
            return []
        try:
            return self._env_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise InfrastructureError(f"Lecture de {self._env_path} impossible.") from exc

    def _lire_valeurs(self) -> dict[str, str]:
        valeurs: dict[str, str] = {}
        for ligne in self._lignes():
            cle = _cle_de_ligne(ligne)
            if cle is not None:
                valeurs[cle] = _valeur_de_ligne(ligne)
        return valeurs

    def _upsert(self, nouvelles: dict[str, str]) -> None:
        restantes = dict(nouvelles)
        sortie: list[str] = []
        for ligne in self._lignes():
            cle = _cle_de_ligne(ligne)
            if cle in restantes:
                sortie.append(f"{cle}={_formater_valeur(restantes.pop(cle))}")
            else:
                sortie.append(ligne)
        sortie.extend(f"{cle}={_formater_valeur(valeur)}" for cle, valeur in restantes.items())
        contenu = "\n".join(sortie) + "\n"
        try:
            self._env_path.write_text(contenu, encoding="utf-8")
        except OSError as exc:
            raise InfrastructureError(f"Écriture de {self._env_path} impossible.") from exc
