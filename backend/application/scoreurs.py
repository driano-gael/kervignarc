"""Service des **scoreurs** — un code court imprimé, une session **nominative** (`D-12`, `D-13`).
Le scoreur est **itinérant** : sa session n'est rattachée à aucune cible. La supprimer invalide ses
jetons mais laisse intacte la **trace** de ses validations passées, qui portent son nom.

⚠️ **Le code est attribué par le SERVICE et figé** (imprimé, distribué) : le domaine ne voit qu'un
scoreur, il ne peut garantir l'unicité. Génération injectée pour rester déterministe en test.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import CodeScoreurInconnu, ScoreurIntrouvable, TournoiIntrouvable
from domain.club import cle_nom
from domain.ports import ScoreurRepository, TournoiRepository
from domain.scoreur import Scoreur, ScoreurId, normaliser_code
from domain.tournoi import TournoiId

_MAX_TENTATIVES_CODE = 100
"""Plafond de ré-essais de génération d'un code libre.

Sur un alphabet de 32 symboles et 6 caractères (~10^9 codes) pour une poignée de scoreurs, une
collision est quasi impossible ; ce plafond n'est qu'un garde-fou contre un générateur défectueux
(qui renverrait sans cesse le même code). L'atteindre est une **incohérence technique**, pas un cas
métier — d'où l'`AssertionError` (→ 500 générique), jamais rencontrée en exploitation.
"""


class StoreSessionsScoreur(Protocol):
    """Port : délivrance/validation de jetons de session **nominatifs** (en mémoire).

    Un jeton est lié à l'**identité** du scoreur (son `id`) — ce qui distingue ce store du
    `StoreSessions` admin (un simple ensemble de jetons anonymes). Le lien sert à **purger** les
    jetons d'un scoreur supprimé (`invalider_scoreur`) et, plus tard, à tracer la validation
    (E10US005).
    """

    def ouvrir(self, scoreur_id: ScoreurId) -> str:
        """Ouvre une session pour un scoreur et renvoie son jeton opaque."""

    def scoreur_de(self, jeton: str | None) -> ScoreurId | None:
        """Identifiant du scoreur derrière un jeton valide, ou `None`."""

    def fermer(self, jeton: str) -> None:
        """Ferme la session (déconnexion) ; sans effet si le jeton est inconnu."""

    def invalider_scoreur(self, scoreur_id: ScoreurId) -> None:
        """Ferme **toutes** les sessions d'un scoreur (à sa suppression)."""


@dataclass(frozen=True)
class ConnexionScoreur:
    """Résultat d'une connexion : le jeton de session **et** le scoreur identifié (contrat
    inter-couches).

    Le `scoreur` accompagne le jeton pour que le client affiche **son** nom et connaisse **son**
    tournoi — la session n'est rattachée à aucune cible (scoreur itinérant, `D-12`).
    """

    jeton: str
    scoreur: Scoreur


class ServiceScoreurs:
    """Cas d'usage des scoreurs : définition (admin) et session (scoreur)."""

    def __init__(
        self,
        scoreur_repository: ScoreurRepository,
        tournoi_repository: TournoiRepository,
        sessions: StoreSessionsScoreur,
        generer_code: Callable[[], str],
    ) -> None:
        self._scoreurs = scoreur_repository
        self._tournois = tournoi_repository
        self._sessions = sessions
        self._generer_code = generer_code

    # --- Définition (admin) ---

    def creer(self, tournoi_id: TournoiId, nom: str) -> Scoreur:
        """Déclare un scoreur du tournoi, avec un code court généré unique.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `NomScoreurInvalide` (domaine) si le
        nom est vide. **Aucune garde sur le statut** du tournoi : redéfinissable même en cours
        (`D-15`). Le pré-contrôle du code et l'insertion tiennent dans **une seule commande** en
        file (règle 7) : aucune création concurrente ne se glisse entre la génération et l'écriture.
        """
        self._verifier_tournoi(tournoi_id)
        code = self._allouer_code()
        return self._scoreurs.ajouter(Scoreur.creer(tournoi_id, nom, code))

    def lister(self, tournoi_id: TournoiId) -> list[Scoreur]:
        """Renvoie les scoreurs d'un tournoi, **triés par nom** (liste éventuellement vide).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas. Tri sur `domain.club.cle_nom` (casse
        et accents repliés), la règle de repli des noms propres du projet (DETTE-006) : un tri par
        code point classerait « Élodie » après « Zoé ».
        """
        self._verifier_tournoi(tournoi_id)
        return sorted(self._scoreurs.par_tournoi(tournoi_id), key=lambda s: cle_nom(s.nom))

    def modifier(self, tournoi_id: TournoiId, scoreur_id: ScoreurId, nom: str) -> Scoreur:
        """Renomme un scoreur (le code reste figé).

        Lève `ScoreurIntrouvable` si le scoreur n'existe pas dans ce tournoi, `NomScoreurInvalide`
        (domaine) si le nom est vide.
        """
        scoreur = self._scoreur_du_tournoi(tournoi_id, scoreur_id)
        return self._scoreurs.enregistrer(scoreur.modifier(nom))

    def supprimer(self, tournoi_id: TournoiId, scoreur_id: ScoreurId) -> None:
        """Retire un scoreur du tournoi **et invalide sa session** (E10US003).

        Lève `ScoreurIntrouvable` si le scoreur n'existe pas dans ce tournoi. Ses validations
        passées **restent tracées** (elles portent son nom, E10US005) — seul le droit de valider
        (la session) lui est retiré : un scoreur qui ne vient plus, ça arrive (`D-14`).
        """
        scoreur = self._scoreur_du_tournoi(tournoi_id, scoreur_id)
        assert scoreur.id is not None, "Un scoreur relu est persisté."
        self._scoreurs.supprimer(scoreur.id)
        self._sessions.invalider_scoreur(scoreur.id)

    # --- Session (scoreur) ---

    def connexion(self, code: str) -> ConnexionScoreur:
        """Ouvre une session nominative pour le scoreur dont c'est le code.

        Lève `CodeScoreurInconnu` (→ 401) si aucun scoreur ne porte ce code. La saisie est
        **normalisée** (casse, espaces de bord) : « ab12cd » ouvre la session de « AB12CD ».
        """
        scoreur = self._scoreurs.par_code(normaliser_code(code))
        if scoreur is None or scoreur.id is None:
            raise CodeScoreurInconnu("Code de scoreur inconnu.")
        jeton = self._sessions.ouvrir(scoreur.id)
        return ConnexionScoreur(jeton=jeton, scoreur=scoreur)

    def deconnexion(self, jeton: str) -> None:
        """Ferme la session associée au jeton."""
        self._sessions.fermer(jeton)

    def session_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton correspond à une session scoreur ouverte."""
        return self._sessions.scoreur_de(jeton) is not None

    def resoudre_session(self, jeton: str | None) -> Scoreur | None:
        """Le **scoreur** derrière un jeton de session valide, ou `None` (`exiger_scoreur`).

        Va au-delà de `session_valide` : rend l'**identité** (nom, tournoi) — nécessaire pour tracer
        « qui a validé » (E10US005) et pour borner l'action du scoreur à **son** tournoi. Le store
        purge les jetons d'un scoreur supprimé (`invalider_scoreur`), donc un jeton valide résout
        toujours un scoreur existant ; par prudence, un `id` orphelin rend `None`.
        """
        scoreur_id = self._sessions.scoreur_de(jeton)
        if scoreur_id is None:
            return None
        return self._scoreurs.par_id(scoreur_id)

    # --- Gardes internes ---

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _scoreur_du_tournoi(self, tournoi_id: TournoiId, scoreur_id: ScoreurId) -> Scoreur:
        scoreur = self._scoreurs.par_id(scoreur_id)
        if scoreur is None or scoreur.tournoi_id != tournoi_id:
            raise ScoreurIntrouvable(
                f"Aucun scoreur d'identifiant {scoreur_id} dans le tournoi {tournoi_id}."
            )
        return scoreur

    def _allouer_code(self) -> str:
        """Génère un code libre (ré-essai en cas de collision, cf. `_MAX_TENTATIVES_CODE`)."""
        for _ in range(_MAX_TENTATIVES_CODE):
            code = normaliser_code(self._generer_code())
            if self._scoreurs.par_code(code) is None:
                return code
        raise AssertionError("Impossible de générer un code de scoreur unique.")
