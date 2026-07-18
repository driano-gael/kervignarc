"""Tests du service applicatif Scoreurs (E10US003) — repositories & store factices.

Écrits **depuis le CA** (règle 9). Le service est testé **en isolation** : de faux repositories en
mémoire (conformes aux ports) et un faux store de sessions suffisent — ni base ni serveur. On y
vérifie ce qui est **propre au service** : génération d'un code **unique** (ré-essai sur collision),
existence du tournoi/scoreur, tri de la liste, et le lien **session ↔ suppression** (supprimer un
scoreur invalide sa session). La normalisation du nom/code est couverte par le domaine
(`test_domain_scoreur`).

Les doublures restent **locales** : `FauxScoreurRepository` et `FauxStoreSessionsScoreur` n'ont
qu'un consommateur (ce module) — la doctrine du `conftest` ne les y héberge qu'au 2ᵉ. `par_code`
applique `normaliser_code`, **la fonction de production**, jamais une réimplémentation.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable

import pytest

from application.erreurs import CodeScoreurInconnu, ScoreurIntrouvable, TournoiIntrouvable
from application.scoreurs import ServiceScoreurs
from domain.erreurs import NomScoreurInvalide
from domain.scoreur import Scoreur, ScoreurId, normaliser_code
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)


class FauxScoreurRepository:
    """Repository de scoreurs en mémoire conforme au port `ScoreurRepository`.

    `par_code` applique `normaliser_code` (production) et cherche **tous tournois confondus** : le
    code est unique dans toute la base.
    """

    def __init__(self) -> None:
        self._scoreurs: dict[int, Scoreur] = {}
        self._sequence = 0

    def ajouter(self, scoreur: Scoreur) -> Scoreur:
        self._sequence += 1
        persiste = dataclasses.replace(scoreur, id=self._sequence)
        self._scoreurs[self._sequence] = persiste
        return persiste

    def par_id(self, scoreur_id: ScoreurId) -> Scoreur | None:
        return self._scoreurs.get(scoreur_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Scoreur]:
        return [s for s in self._scoreurs.values() if s.tournoi_id == tournoi_id]

    def par_code(self, code: str) -> Scoreur | None:
        recherche = normaliser_code(code)
        for scoreur in self._scoreurs.values():
            if scoreur.code == recherche:
                return scoreur
        return None

    def enregistrer(self, scoreur: Scoreur) -> Scoreur:
        assert scoreur.id in self._scoreurs, "Scoreur à mettre à jour absent."
        self._scoreurs[scoreur.id] = scoreur
        return scoreur

    def supprimer(self, scoreur_id: ScoreurId) -> None:
        del self._scoreurs[scoreur_id]


class FauxStoreSessionsScoreur:
    """Store de sessions scoreur en mémoire conforme au port `StoreSessionsScoreur`.

    Nominatif (jeton → `scoreur_id`) : c'est ce qui rend testable la **purge** à la suppression
    (`invalider_scoreur`). Les jetons sont déterministes (`sess-1`, `sess-2`…) — le test ne doit
    pas dépendre de `secrets`.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ScoreurId] = {}
        self._sequence = 0

    def ouvrir(self, scoreur_id: ScoreurId) -> str:
        self._sequence += 1
        jeton = f"sess-{self._sequence}"
        self._sessions[jeton] = scoreur_id
        return jeton

    def scoreur_de(self, jeton: str | None) -> ScoreurId | None:
        return None if jeton is None else self._sessions.get(jeton)

    def fermer(self, jeton: str) -> None:
        self._sessions.pop(jeton, None)

    def invalider_scoreur(self, scoreur_id: ScoreurId) -> None:
        for jeton in [j for j, sid in self._sessions.items() if sid == scoreur_id]:
            del self._sessions[jeton]


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


def _generateur(*codes: str) -> Callable[[], str]:
    """Générateur déterministe : renvoie les `codes` dans l'ordre, puis le dernier indéfiniment.

    Répéter le dernier code (au lieu de lever `StopIteration`) laisse au service le soin de sa
    propre borne de ré-essai — un `_generateur("DUP")` sature ainsi la boucle d'allocation.
    """
    file = list(codes)

    def suivant() -> str:
        return file.pop(0) if len(file) > 1 else file[0]

    return suivant


class Montage:
    """Attelage d'un test : service + repos garnis à la main + `tournoi_id`."""

    def __init__(self, *codes: str) -> None:
        self.tournois = FauxTournoiRepository()
        self.scoreurs = FauxScoreurRepository()
        self.sessions = FauxStoreSessionsScoreur()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.service = ServiceScoreurs(
            self.scoreurs, self.tournois, self.sessions, _generateur(*codes)
        )


def _id(scoreur: Scoreur) -> ScoreurId:
    assert scoreur.id is not None
    return scoreur.id


# --- Définition (admin) ---


def test_creer_declare_un_scoreur_avec_un_code_genere() -> None:
    m = Montage("AB12CD")
    scoreur = m.service.creer(m.tournoi_id, "Camille Dubois")

    assert scoreur.id is not None
    assert scoreur.tournoi_id == m.tournoi_id
    assert scoreur.nom == "Camille Dubois"
    assert scoreur.code == "AB12CD"
    assert m.service.lister(m.tournoi_id) == [scoreur]


def test_creer_refuse_un_tournoi_inexistant() -> None:
    m = Montage("AB12CD")
    with pytest.raises(TournoiIntrouvable):
        m.service.creer(404, "Camille")


def test_creer_refuse_un_nom_vide() -> None:
    m = Montage("AB12CD")
    with pytest.raises(NomScoreurInvalide):
        m.service.creer(m.tournoi_id, "   ")


def test_creer_attribue_des_codes_distincts() -> None:
    m = Montage("AB12CD", "EF34GH")
    premier = m.service.creer(m.tournoi_id, "Alice")
    second = m.service.creer(m.tournoi_id, "Bob")

    assert {premier.code, second.code} == {"AB12CD", "EF34GH"}


def test_creer_reessaie_sur_collision_de_code() -> None:
    """Un code déjà pris est ré-essayé (pré-contrôle `par_code`), comme le nom d'un club."""
    m = Montage("DUP111", "DUP111", "NEW222")
    m.service.creer(m.tournoi_id, "Alice")
    second = m.service.creer(m.tournoi_id, "Bob")

    assert second.code == "NEW222"


def test_creer_code_unique_meme_entre_tournois() -> None:
    """Le code est unique dans **toute la base** : deux tournois ne peuvent pas partager un code.

    C'est ce qui permet au scoreur d'ouvrir sa session par son seul code, sans désigner de tournoi.
    """
    m = Montage("DUP111", "DUP111", "NEW222")
    autre_tournoi = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre_tournoi.id is not None
    m.service.creer(m.tournoi_id, "Alice")

    second = m.service.creer(autre_tournoi.id, "Bob")

    assert second.code == "NEW222"


def test_creer_echoue_si_aucun_code_libre() -> None:
    """Garde-fou : un générateur qui ne rend jamais de code libre sature la borne de ré-essai."""
    m = Montage("DUP111")
    m.service.creer(m.tournoi_id, "Alice")

    with pytest.raises(AssertionError):
        m.service.creer(m.tournoi_id, "Bob")


def test_creer_reste_possible_tournoi_en_cours() -> None:
    """Redéfinissable **même tournoi en cours** (`D-15`) : aucune garde sur le statut."""
    m = Montage("AB12CD")
    tournoi = m.tournois.par_id(m.tournoi_id)
    assert tournoi is not None
    m.tournois.enregistrer(dataclasses.replace(tournoi, statut=StatutTournoi.EN_COURS))

    scoreur = m.service.creer(m.tournoi_id, "Camille")

    assert scoreur.id is not None


def test_lister_ne_renvoie_que_les_scoreurs_du_tournoi() -> None:
    m = Montage("AB12CD", "EF34GH")
    autre = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre.id is not None
    du_tournoi = m.service.creer(m.tournoi_id, "Alice")
    m.service.creer(autre.id, "Bob")

    assert m.service.lister(m.tournoi_id) == [du_tournoi]


def test_lister_trie_par_nom_casse_et_accents_replies() -> None:
    m = Montage("C1", "C2", "C3")
    m.service.creer(m.tournoi_id, "Zoé")
    m.service.creer(m.tournoi_id, "Élodie")
    m.service.creer(m.tournoi_id, "bob")

    assert [s.nom for s in m.service.lister(m.tournoi_id)] == ["bob", "Élodie", "Zoé"]


def test_lister_refuse_un_tournoi_inexistant() -> None:
    m = Montage("AB12CD")
    with pytest.raises(TournoiIntrouvable):
        m.service.lister(404)


def test_modifier_renomme_en_gardant_le_code() -> None:
    m = Montage("AB12CD")
    scoreur = m.service.creer(m.tournoi_id, "Camile")

    corrige = m.service.modifier(m.tournoi_id, _id(scoreur), "Camille Dubois")

    assert corrige.id == scoreur.id
    assert corrige.code == "AB12CD"
    assert corrige.nom == "Camille Dubois"


def test_modifier_refuse_un_scoreur_d_un_autre_tournoi() -> None:
    m = Montage("AB12CD")
    autre = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre.id is not None
    scoreur = m.service.creer(m.tournoi_id, "Camille")

    with pytest.raises(ScoreurIntrouvable):
        m.service.modifier(autre.id, _id(scoreur), "Autre nom")


def test_modifier_refuse_un_identifiant_inconnu() -> None:
    m = Montage("AB12CD")
    with pytest.raises(ScoreurIntrouvable):
        m.service.modifier(m.tournoi_id, 404, "Camille")


def test_supprimer_retire_le_scoreur() -> None:
    m = Montage("AB12CD")
    scoreur = m.service.creer(m.tournoi_id, "Camille")

    m.service.supprimer(m.tournoi_id, _id(scoreur))

    assert m.service.lister(m.tournoi_id) == []


def test_supprimer_refuse_un_scoreur_d_un_autre_tournoi() -> None:
    m = Montage("AB12CD")
    autre = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre.id is not None
    scoreur = m.service.creer(m.tournoi_id, "Camille")

    with pytest.raises(ScoreurIntrouvable):
        m.service.supprimer(autre.id, _id(scoreur))


def test_supprimer_invalide_la_session_du_scoreur() -> None:
    """CA : supprimer un scoreur **invalide sa session** (il ne peut plus valider)."""
    m = Montage("AB12CD")
    scoreur = m.service.creer(m.tournoi_id, "Camille")
    connexion = m.service.connexion("AB12CD")
    assert m.service.session_valide(connexion.jeton) is True

    m.service.supprimer(m.tournoi_id, _id(scoreur))

    assert m.service.session_valide(connexion.jeton) is False


# --- Session (scoreur) ---


def test_connexion_ouvre_une_session_nominative() -> None:
    m = Montage("AB12CD")
    scoreur = m.service.creer(m.tournoi_id, "Camille")

    connexion = m.service.connexion("AB12CD")

    assert connexion.scoreur.id == scoreur.id
    assert connexion.scoreur.nom == "Camille"
    assert m.service.session_valide(connexion.jeton) is True


def test_connexion_normalise_la_saisie() -> None:
    """« ab12cd » (minuscules, espaces) ouvre la session de « AB12CD »."""
    m = Montage("AB12CD")
    m.service.creer(m.tournoi_id, "Camille")

    connexion = m.service.connexion("  ab12cd ")

    assert m.service.session_valide(connexion.jeton) is True


def test_connexion_code_inconnu_est_refusee() -> None:
    m = Montage("AB12CD")
    m.service.creer(m.tournoi_id, "Camille")

    with pytest.raises(CodeScoreurInconnu):
        m.service.connexion("ZZ99ZZ")


def test_deux_scoreurs_ouvrent_des_sessions_distinctes() -> None:
    m = Montage("AB12CD", "EF34GH")
    m.service.creer(m.tournoi_id, "Alice")
    m.service.creer(m.tournoi_id, "Bob")

    session_alice = m.service.connexion("AB12CD")
    session_bob = m.service.connexion("EF34GH")

    assert session_alice.jeton != session_bob.jeton
    assert session_alice.scoreur.nom == "Alice"
    assert session_bob.scoreur.nom == "Bob"


def test_deconnexion_invalide_la_session() -> None:
    m = Montage("AB12CD")
    m.service.creer(m.tournoi_id, "Camille")
    connexion = m.service.connexion("AB12CD")

    m.service.deconnexion(connexion.jeton)

    assert m.service.session_valide(connexion.jeton) is False


def test_session_valide_refuse_un_jeton_bidon() -> None:
    m = Montage("AB12CD")
    assert m.service.session_valide(None) is False
    assert m.service.session_valide("jeton-bidon") is False
