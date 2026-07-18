"""Service applicatif Postes (E04US001, ADR-0029) — **préparation** des codes de cible &
**session** de poste (rattacher une tablette à sa cible).

Deux volets d'une même capacité, portés par un seul service (même parti que `ServiceScoreurs`) :

- **Préparation** (admin, `D-07` « tout se prépare à l'avance ») : `assurer_codes` garantit **un
  code par cible** du plan de salle du tournoi, de façon **idempotente** (les codes déjà émis ne
  changent pas — les QR sont imprimés). C'est le contrat que E09US008 imprimera.
- **Session** (le poste, `D-13` : identité = le *lieu*) : `rattacher` par code → jeton opaque en
  mémoire lié à la **cible** ; `resoudre_session` le retrouve à la réouverture (« sans rien demander
  à personne ») ; `deconnexion`. Le jeton n'est valide que tant que **son tournoi n'est pas
  terminé** — ancrage de la révocation « nouveau tournoi force le re-rattachement », compatible avec
  **plusieurs tournois non terminés** simultanés (intérieur + extérieur).

Le code est **attribué par le service** (le domaine ne voit qu'un poste, il ne peut garantir
l'unicité). La génération est **injectée** (`generer_code`) pour rester déterministe en test
(règle 9) ; elle **ré-essaie** en cas de collision (pré-contrôle `par_code`), la contrainte
`UNIQUE(code)` en base restant le garde-fou d'intégrité ultime.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import (
    CodePosteInconnu,
    RattachementTournoiTermine,
    TournoiIntrouvable,
)
from domain.ports import GabaritSalleRepository, PosteRepository, TournoiRepository
from domain.poste import Poste, PosteId, normaliser_code
from domain.tournoi import StatutTournoi, TournoiId

_MAX_TENTATIVES_CODE = 100
"""Plafond de ré-essais de génération d'un code libre (cf. `ServiceScoreurs`).

Sur ~10^9 codes pour quelques dizaines de cibles, une collision est quasi impossible ; ce plafond
n'est qu'un garde-fou contre un générateur défectueux. L'atteindre est une **incohérence
technique** (`AssertionError` → 500 générique), jamais rencontrée en exploitation.
"""


class StoreSessionsPoste(Protocol):
    """Port : délivrance/validation de jetons de session de poste (en mémoire).

    Un jeton est lié à l'**identité de la cible** (l'`id` du poste). En mémoire, invalidé au
    redémarrage serveur (cohérent ADR-0025) et à la déconnexion ; la révocation « tournoi terminé »
    est appliquée à la **résolution** (le store ignore le cycle de vie du tournoi).
    """

    def ouvrir(self, poste_id: PosteId) -> str:
        """Ouvre une session pour un poste et renvoie son jeton opaque."""

    def poste_de(self, jeton: str | None) -> PosteId | None:
        """Identifiant du poste derrière un jeton valide, ou `None`."""

    def fermer(self, jeton: str) -> None:
        """Ferme la session (déconnexion) ; sans effet si le jeton est inconnu."""


@dataclass(frozen=True)
class ConnexionPoste:
    """Résultat d'un rattachement : le jeton de session **et** le poste rattaché (sa cible).

    Le `poste` accompagne le jeton pour que le client sache **quelle cible** il sert (tournoi +
    numéro de cible), sans avoir à le redemander.
    """

    jeton: str
    poste: Poste


class ServicePostes:
    """Cas d'usage des postes : préparation des codes (admin) et session (poste)."""

    def __init__(
        self,
        poste_repository: PosteRepository,
        tournoi_repository: TournoiRepository,
        gabarit_repository: GabaritSalleRepository,
        sessions: StoreSessionsPoste,
        generer_code: Callable[[], str],
    ) -> None:
        self._postes = poste_repository
        self._tournois = tournoi_repository
        self._gabarits = gabarit_repository
        self._sessions = sessions
        self._generer_code = generer_code

    # --- Préparation des codes (admin) ---

    def assurer_codes(self, tournoi_id: TournoiId) -> list[Poste]:
        """Garantit **un code par cible** du plan et renvoie tous ses postes (triés par cible).

        **Idempotent** : ne crée que les postes manquants ; les codes déjà émis (QR imprimés) sont
        **préservés**. Un tournoi **sans plan de salle** (aucun gabarit) n'a pas de cible : la liste
        est vide. Lève `TournoiIntrouvable` si le tournoi n'existe pas. Aucune garde de statut : les
        codes se préparent **à l'avance** (`D-07`), y compris sur un brouillon. Lecture du plan,
        pré-contrôle des codes et insertions tiennent dans **une seule commande** en file (règle 7).
        """
        self._verifier_tournoi(tournoi_id)
        existants = {poste.cible_index: poste for poste in self._postes.par_tournoi(tournoi_id)}
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is not None:
            for cible in gabarit.cibles:
                if cible.index not in existants:
                    code = self._allouer_code()
                    existants[cible.index] = self._postes.ajouter(
                        Poste.creer(tournoi_id, cible.index, code)
                    )
        return [existants[index] for index in sorted(existants)]

    def lister(self, tournoi_id: TournoiId) -> list[Poste]:
        """Renvoie les postes déjà préparés d'un tournoi (triés par cible), **sans rien créer**.

        Lecture pour l'admin (afficher les codes à distribuer/imprimer). Lève `TournoiIntrouvable`
        si le tournoi n'existe pas ; liste vide tant qu'aucun code n'a été préparé.
        """
        self._verifier_tournoi(tournoi_id)
        return sorted(self._postes.par_tournoi(tournoi_id), key=lambda poste: poste.cible_index)

    # --- Session (poste) ---

    def rattacher(self, code: str) -> ConnexionPoste:
        """Rattache une tablette à la cible dont c'est le code (scan du QR ou code de secours).

        Lève `CodePosteInconnu` (→ 401) si aucun poste ne porte ce code,
        `RattachementTournoiTermine` (→ 409) si le tournoi de la cible est terminé (piège « le jeton
        survit trop bien »). La saisie est **normalisée** (casse, espaces) : « c1 » rattache « C1 ».
        """
        poste = self._postes.par_code(normaliser_code(code))
        if poste is None or poste.id is None:
            raise CodePosteInconnu("Code de cible inconnu.")
        self._refuser_si_termine(poste.tournoi_id)
        jeton = self._sessions.ouvrir(poste.id)
        return ConnexionPoste(jeton=jeton, poste=poste)

    def resoudre_session(self, jeton: str | None) -> Poste | None:
        """Poste derrière un jeton **encore valide**, ou `None` (réouverture « retrouve sa cible »).

        Renvoie `None` si le jeton est inconnu, si le poste a disparu, **ou si son tournoi est
        terminé** (révocation) : le front purge alors le jeton et redemande un rattachement.
        """
        poste_id = self._sessions.poste_de(jeton)
        if poste_id is None:
            return None
        poste = self._postes.par_id(poste_id)
        if poste is None:
            return None
        tournoi = self._tournois.par_id(poste.tournoi_id)
        if tournoi is None or tournoi.statut is StatutTournoi.TERMINE:
            return None
        return poste

    def session_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton correspond à une session de poste encore valide (`exiger_poste`)."""
        return self.resoudre_session(jeton) is not None

    def deconnexion(self, jeton: str) -> None:
        """Ferme la session associée au jeton."""
        self._sessions.fermer(jeton)

    # --- Gardes internes ---

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _refuser_si_termine(self, tournoi_id: TournoiId) -> None:
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None or tournoi.statut is StatutTournoi.TERMINE:
            raise RattachementTournoiTermine(
                "Le tournoi de cette cible est terminé : rattachement impossible."
            )

    def _allouer_code(self) -> str:
        """Génère un code libre (ré-essai en cas de collision, cf. `_MAX_TENTATIVES_CODE`)."""
        for _ in range(_MAX_TENTATIVES_CODE):
            code = normaliser_code(self._generer_code())
            if self._postes.par_code(code) is None:
                return code
        raise AssertionError("Impossible de générer un code de poste unique.")
