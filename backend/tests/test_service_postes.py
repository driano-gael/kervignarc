"""Tests du service applicatif Postes (E04US001) — repositories & store factices.

Écrits **depuis le CA/ADR-0029** (règle 9), en isolation (ni base ni serveur). On y vérifie ce qui
est **propre au service** : préparation d'**un code par cible** du plan (idempotente, sans doublon),
**rattachement** d'une tablette par code, **résolution de session** et surtout la **révocation** —
un jeton dont le tournoi est terminé cesse d'être valide (ancrage de « nouveau tournoi force le
re-rattachement ») — et la **coexistence multi-tournois** (intérieur + extérieur).

Les doublures sont **locales** (un seul consommateur). `par_code` applique `normaliser_code`, la
fonction de production. Les jetons factices sont déterministes (`sess-1`…) : le test ne dépend
pas de `secrets`.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable

import pytest

from application.erreurs import (
    CodePosteInconnu,
    RattachementTournoiTermine,
    TournoiIntrouvable,
)
from application.postes import ServicePostes
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.poste import Poste, PosteId, normaliser_code
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)


class FauxPosteRepository:
    """Repository de postes en mémoire conforme au port `PosteRepository`.

    `par_code` cherche **tous tournois confondus** (le code désigne un poste sans contexte).
    """

    def __init__(self) -> None:
        self._postes: dict[int, Poste] = {}
        self._sequence = 0

    def ajouter(self, poste: Poste) -> Poste:
        self._sequence += 1
        persiste = dataclasses.replace(poste, id=self._sequence)
        self._postes[self._sequence] = persiste
        return persiste

    def par_id(self, poste_id: PosteId) -> Poste | None:
        return self._postes.get(poste_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        return [p for p in self._postes.values() if p.tournoi_id == tournoi_id]

    def par_code(self, code: str) -> Poste | None:
        recherche = normaliser_code(code)
        for poste in self._postes.values():
            if poste.code == recherche:
                return poste
        return None


class FauxStoreSessionsPoste:
    """Store de sessions de poste en mémoire conforme au port `StoreSessionsPoste`."""

    def __init__(self) -> None:
        self._sessions: dict[str, PosteId] = {}
        self._sequence = 0

    def ouvrir(self, poste_id: PosteId) -> str:
        self._sequence += 1
        jeton = f"sess-{self._sequence}"
        self._sessions[jeton] = poste_id
        return jeton

    def poste_de(self, jeton: str | None) -> PosteId | None:
        return None if jeton is None else self._sessions.get(jeton)

    def fermer(self, jeton: str) -> None:
        self._sessions.pop(jeton, None)


class FauxTournoiRepository:
    """Repository de tournois en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id in self._tournois, "Tournoi à mettre à jour absent."
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class FauxGabaritRepository:
    """Repository de gabarits en mémoire conforme au port `GabaritSalleRepository`.

    Le service ne consomme que `par_tournoi` (les cibles du plan) ; les autres méthodes du port sont
    fournies pour la conformité structurelle mais restent triviales.
    """

    def __init__(self) -> None:
        self._instances: dict[int, GabaritSalle] = {}
        self._sequence = 0

    def definir_pour(self, tournoi_id: TournoiId, nb_cibles: int) -> None:
        """Attelage de test : applique au tournoi un plan de `nb_cibles` cibles."""
        modele = GabaritSalle.creer("Plan", nb_cibles=nb_cibles)
        self._instances[tournoi_id] = modele.pour_tournoi(tournoi_id)

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        self._sequence += 1
        return dataclasses.replace(gabarit, id=self._sequence)

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        return None

    def lister(self) -> list[GabaritSalle]:
        return []

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        return self._instances.get(tournoi_id)

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        return gabarit

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        return None


def _generateur(*codes: str) -> Callable[[], str]:
    """Générateur déterministe : renvoie les `codes` dans l'ordre, puis le dernier indéfiniment."""
    file = list(codes)

    def suivant() -> str:
        return file.pop(0) if len(file) > 1 else file[0]

    return suivant


class Montage:
    """Attelage d'un test : service + repos garnis à la main + un tournoi (brouillon) planté.

    `nb_cibles` fixe le plan du tournoi principal ; `codes` alimente le générateur déterministe.
    """

    def __init__(self, *codes: str, nb_cibles: int = 2) -> None:
        self.tournois = FauxTournoiRepository()
        self.postes = FauxPosteRepository()
        self.gabarits = FauxGabaritRepository()
        self.sessions = FauxStoreSessionsPoste()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.gabarits.definir_pour(self.tournoi_id, nb_cibles)
        self.service = ServicePostes(
            self.postes, self.tournois, self.gabarits, self.sessions, _generateur(*codes)
        )

    def statut(self, tournoi_id: TournoiId, statut: StatutTournoi) -> None:
        """Force le statut d'un tournoi (pour les tests de révocation/montage)."""
        tournoi = self.tournois.par_id(tournoi_id)
        assert tournoi is not None
        self.tournois.enregistrer(dataclasses.replace(tournoi, statut=statut))

    def autre_tournoi(self, nb_cibles: int) -> TournoiId:
        """Ajoute un second tournoi (brouillon) avec son plan — pour le cas multi-tournois."""
        tournoi = self.tournois.ajouter(Tournoi.creer("Extérieur", _DATE))
        assert tournoi.id is not None
        self.gabarits.definir_pour(tournoi.id, nb_cibles)
        return tournoi.id


# --- Préparation des codes de cible (admin) ---


def test_assurer_codes_cree_un_code_par_cible_du_plan() -> None:
    m = Montage("C1", "C2", "C3", nb_cibles=3)

    postes = m.service.assurer_codes(m.tournoi_id)

    assert [p.cible_index for p in postes] == [1, 2, 3]
    assert {p.code for p in postes} == {"C1", "C2", "C3"}
    assert all(p.tournoi_id == m.tournoi_id for p in postes)


def test_assurer_codes_est_idempotent() -> None:
    """Rejouer la préparation ne recrée rien et **ne change pas** les codes (QR déjà imprimés)."""
    m = Montage("C1", "C2", nb_cibles=2)
    premier = m.service.assurer_codes(m.tournoi_id)

    second = m.service.assurer_codes(m.tournoi_id)

    assert second == premier


def test_assurer_codes_complete_les_cibles_ajoutees() -> None:
    """Plan agrandi (2 → 3 cibles) : les codes déjà émis sont **préservés**, la nouvelle en a un.

    Cas réel du bouton « Compléter les codes manquants » : rejouer la préparation après avoir ajouté
    une cible au plan ne doit pas régénérer les QR déjà imprimés.
    """
    m = Montage("C1", "C2", "C3", nb_cibles=2)
    initial = m.service.assurer_codes(m.tournoi_id)
    assert [p.cible_index for p in initial] == [1, 2]

    m.gabarits.definir_pour(m.tournoi_id, 3)  # une cible ajoutée au plan
    complete = m.service.assurer_codes(m.tournoi_id)

    assert [p.cible_index for p in complete] == [1, 2, 3]
    # Les deux premiers postes (id + code) sont inchangés — pas de régénération.
    assert complete[0] == initial[0]
    assert complete[1] == initial[1]
    assert complete[2].code == "C3"


def test_assurer_codes_sans_plan_ne_cree_rien() -> None:
    """Un tournoi sans plan de salle (aucun gabarit) n'a pas de cible : rien à préparer."""
    m = Montage("C1", nb_cibles=2)
    sans_plan = m.tournois.ajouter(Tournoi.creer("Sans plan", _DATE))
    assert sans_plan.id is not None

    assert m.service.assurer_codes(sans_plan.id) == []


def test_assurer_codes_refuse_un_tournoi_inexistant() -> None:
    m = Montage("C1")
    with pytest.raises(TournoiIntrouvable):
        m.service.assurer_codes(404)


def test_assurer_codes_reessaie_sur_collision_de_code() -> None:
    m = Montage("DUP", "DUP", "NEW", nb_cibles=2)

    postes = m.service.assurer_codes(m.tournoi_id)

    assert {p.code for p in postes} == {"DUP", "NEW"}


def test_assurer_codes_echoue_si_aucun_code_libre() -> None:
    """Garde-fou : un générateur qui ne rend jamais de code libre sature la borne de ré-essai."""
    m = Montage("DUP", nb_cibles=2)
    with pytest.raises(AssertionError):
        m.service.assurer_codes(m.tournoi_id)


def test_lister_renvoie_les_postes_prepares_tries() -> None:
    m = Montage("C1", "C2", "C3", nb_cibles=3)
    m.service.assurer_codes(m.tournoi_id)

    assert [p.cible_index for p in m.service.lister(m.tournoi_id)] == [1, 2, 3]


def test_lister_est_vide_sans_preparation() -> None:
    """Aucun code préparé → liste vide, **sans** en créer (contrairement à `assurer_codes`)."""
    m = Montage("C1", nb_cibles=2)

    assert m.service.lister(m.tournoi_id) == []
    # Toujours rien créé : la liste reste vide après un second appel.
    assert m.service.lister(m.tournoi_id) == []


def test_lister_refuse_un_tournoi_inexistant() -> None:
    m = Montage("C1")
    with pytest.raises(TournoiIntrouvable):
        m.service.lister(404)


# --- Rattachement (poste) ---


def test_rattacher_ouvre_une_session_liee_a_la_cible() -> None:
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)

    connexion = m.service.rattacher("C1")

    assert connexion.poste.tournoi_id == m.tournoi_id
    assert connexion.poste.cible_index == 1
    assert m.service.session_valide(connexion.jeton) is True


def test_rattacher_normalise_la_saisie() -> None:
    """« c1 » (minuscules, espaces) rattache le poste « C1 » (code de secours retapé)."""
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)

    connexion = m.service.rattacher("  c1 ")

    assert connexion.poste.cible_index == 1


def test_rattacher_code_inconnu_est_refuse() -> None:
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)

    with pytest.raises(CodePosteInconnu):
        m.service.rattacher("ZZZZ")


def test_rattacher_reste_possible_au_montage_brouillon() -> None:
    """L'organisateur rattache **au montage**, avant de démarrer (`D-07`) : brouillon accepté."""
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    # tournoi laissé en brouillon (défaut du montage)

    connexion = m.service.rattacher("C1")

    assert m.service.session_valide(connexion.jeton) is True


def test_rattacher_refuse_un_tournoi_termine() -> None:
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    m.statut(m.tournoi_id, StatutTournoi.TERMINE)

    with pytest.raises(RattachementTournoiTermine):
        m.service.rattacher("C1")


# --- Session : résolution, révocation, déconnexion ---


def test_resoudre_session_rend_le_poste() -> None:
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    connexion = m.service.rattacher("C2")

    poste = m.service.resoudre_session(connexion.jeton)

    assert poste is not None
    assert poste.cible_index == 2


def test_terminer_le_tournoi_revoque_la_session() -> None:
    """CA/ADR-0029 : terminer un tournoi rend caducs **tous ses jetons de poste** (révocation)."""
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    connexion = m.service.rattacher("C1")
    assert m.service.session_valide(connexion.jeton) is True

    m.statut(m.tournoi_id, StatutTournoi.TERMINE)

    assert m.service.session_valide(connexion.jeton) is False
    assert m.service.resoudre_session(connexion.jeton) is None


def test_deconnexion_invalide_la_session() -> None:
    m = Montage("C1", "C2", nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    connexion = m.service.rattacher("C1")

    m.service.deconnexion(connexion.jeton)

    assert m.service.session_valide(connexion.jeton) is False


def test_session_valide_refuse_un_jeton_bidon() -> None:
    m = Montage("C1")
    assert m.service.session_valide(None) is False
    assert m.service.session_valide("jeton-bidon") is False


def test_deux_tournois_non_termines_coexistent() -> None:
    """CA/arbitrage : intérieur **et** extérieur en même temps — postes valides simultanément."""
    m = Montage("A1", "A2", "B1", "B2", nb_cibles=2)
    exterieur = m.autre_tournoi(nb_cibles=2)
    m.service.assurer_codes(m.tournoi_id)
    m.service.assurer_codes(exterieur)

    interieur_poste = m.service.rattacher("A1")
    exterieur_poste = m.service.rattacher("B1")

    assert interieur_poste.jeton != exterieur_poste.jeton
    assert m.service.session_valide(interieur_poste.jeton) is True
    assert m.service.session_valide(exterieur_poste.jeton) is True
    assert interieur_poste.poste.tournoi_id == m.tournoi_id
    assert exterieur_poste.poste.tournoi_id == exterieur
