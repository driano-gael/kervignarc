"""Tests du service de supervision des postes (E12US001) — **dérivés du CA**, avant impl.

Source : `stories/E12-pilotage-jour-j.md`, E12US001, puce « CA » (états *en ligne* / *hors ligne* /
*non rattaché*, compteur global, dernière activité, avancement, révocation, IP diagnostic) et
l'arbitrage heartbeat (ADR-0038). On isole le service : **vrais** store de sessions et registre de
présence (en mémoire, déterministes) — ce qui couvre aussi les nouvelles méthodes du store —, faux
repositories, **horloge réglable** (le temps qui passe rend un poste hors ligne sans qu'aucun
événement ne survienne), et **faux lecteur d'avancement** (l'agrégation volée-par-volée est prouvée
côté `ServiceSaisie`).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import PosteIntrouvable, TournoiIntrouvable
from application.saisie import AvancementCible
from application.supervision import Avancement, LigneSupervision, ServiceSupervision
from domain.depart import DepartId
from domain.poste import Poste, PosteId
from domain.supervision import EtatPoste
from domain.tournoi import Tournoi, TournoiId
from infrastructure.postes.presence import RegistrePresenceMemoire
from infrastructure.postes.sessions import PosteSessionStore

_DATE = datetime.date(2026, 3, 14)
_T0 = datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.UTC)
_SEUIL = 30.0


class HorlogeReglable:
    """Horloge conforme au port `Horloge`, avançable à la main (déterminisme, règle 9)."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant

    def avancer(self, secondes: float) -> None:
        self._instant += datetime.timedelta(seconds=secondes)


class FauxLecteurAvancement:
    """Faux lecteur d'avancement : réponse pré-réglée par cible, sinon « rien saisi »."""

    def __init__(self) -> None:
        self.reponses: dict[int, AvancementCible] = {}

    def regler(self, cible_index: int, avancement: AvancementCible) -> None:
        self.reponses[cible_index] = avancement

    def avancement_cible(
        self, tournoi_id: TournoiId, cible_index: int, depart_id: DepartId
    ) -> AvancementCible:
        return self.reponses.get(cible_index, AvancementCible(0, 0, None))


class FauxPosteRepository:
    """Repository de postes en mémoire conforme au port `PosteRepository`."""

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
        return next((p for p in self._postes.values() if p.code == code), None)


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
        assert tournoi.id in self._tournois
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class Montage:
    """Attelage : service + repos garnis, un tournoi et ses postes préparés (sans session)."""

    def __init__(self, nb_cibles: int = 3) -> None:
        self.tournois = FauxTournoiRepository()
        self.postes = FauxPosteRepository()
        self.sessions = PosteSessionStore()
        self.presence = RegistrePresenceMemoire()
        self.avancement = FauxLecteurAvancement()
        self.horloge = HorlogeReglable(_T0)
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self._postes_par_cible: dict[int, PosteId] = {}
        for index in range(1, nb_cibles + 1):
            poste = self.postes.ajouter(Poste.creer(self.tournoi_id, index, f"C{index}"))
            assert poste.id is not None
            self._postes_par_cible[index] = poste.id
        self.service = ServiceSupervision(
            self.postes,
            self.tournois,
            self.sessions,
            self.presence,
            self.avancement,
            self.horloge,
            _SEUIL,
        )

    def poste_id(self, cible_index: int) -> PosteId:
        return self._postes_par_cible[cible_index]

    def rattacher(self, cible_index: int) -> str:
        """Ouvre une session sur la cible (comme un rattachement) et renvoie le jeton."""
        return self.sessions.ouvrir(self.poste_id(cible_index))

    def ligne(self, cible_index: int) -> LigneSupervision:
        """La ligne de supervision d'une cible dans l'instantané courant."""
        etat = self.service.etat(self.tournoi_id)
        return next(ligne for ligne in etat.postes if ligne.cible_index == cible_index)


# --- États (en ligne / hors ligne / non rattaché) ---


def test_poste_sans_session_est_non_rattache() -> None:
    """Code de cible préparé mais aucune tablette dessus : troisième état, à part entière."""
    m = Montage(nb_cibles=1)

    ligne = m.ligne(1)

    assert ligne.etat is EtatPoste.NON_RATTACHE
    assert ligne.ip is None
    assert ligne.avancement is None
    assert ligne.derniere_saisie is None


def test_poste_rattache_et_pinge_est_en_ligne_avec_son_ip() -> None:
    m = Montage(nb_cibles=1)
    m.rattacher(1)

    m.service.enregistrer_heartbeat(m.poste_id(1), "192.168.1.10")

    ligne = m.ligne(1)
    assert ligne.etat is EtatPoste.EN_LIGNE
    assert ligne.ip == "192.168.1.10"


def test_poste_silencieux_au_dela_du_seuil_passe_hors_ligne() -> None:
    """« Tablette morte » : rattachée et vue une fois, puis plus rien — le temps la fait basculer.

    Aucun événement ne survient : c'est l'horloge qui avance. L'IP du dernier heartbeat **reste**
    affichée — c'est justement le diagnostic pour aller débrancher/rebrancher la bonne tablette.
    """
    m = Montage(nb_cibles=1)
    m.rattacher(1)
    m.service.enregistrer_heartbeat(m.poste_id(1), "192.168.1.10")

    m.horloge.avancer(_SEUIL + 1)

    ligne = m.ligne(1)
    assert ligne.etat is EtatPoste.HORS_LIGNE
    assert ligne.ip == "192.168.1.10"


def test_poste_rattache_jamais_pinge_est_hors_ligne() -> None:
    """Session ouverte mais aucun heartbeat encore reçu : hors ligne (prudence, ADR-0038 §1)."""
    m = Montage(nb_cibles=1)
    m.rattacher(1)

    ligne = m.ligne(1)
    assert ligne.etat is EtatPoste.HORS_LIGNE


def test_poste_vu_juste_avant_le_seuil_reste_en_ligne() -> None:
    m = Montage(nb_cibles=1)
    m.rattacher(1)
    m.service.enregistrer_heartbeat(m.poste_id(1), "10.0.0.1")

    m.horloge.avancer(_SEUIL - 1)

    assert m.ligne(1).etat is EtatPoste.EN_LIGNE


# --- Compteur global ---


def test_compteur_global_en_ligne_sur_total() -> None:
    """« 28/30 en ligne » à l'échelle du test : 2 pingés récemment, 1 muet, 3 cibles au total."""
    m = Montage(nb_cibles=3)
    m.rattacher(1)
    m.rattacher(2)
    m.rattacher(3)
    m.service.enregistrer_heartbeat(m.poste_id(1), "10.0.0.1")
    m.service.enregistrer_heartbeat(m.poste_id(2), "10.0.0.2")
    # cible 3 rattachée mais jamais pingée → hors ligne

    etat = m.service.etat(m.tournoi_id)

    assert etat.nb_total == 3
    assert etat.nb_en_ligne == 2


def test_lignes_triees_par_numero_de_cible() -> None:
    m = Montage(nb_cibles=3)
    etat = m.service.etat(m.tournoi_id)
    assert [ligne.cible_index for ligne in etat.postes] == [1, 2, 3]


# --- Avancement & dernière saisie ---


def test_avancement_et_derniere_saisie_d_un_poste_en_saisie() -> None:
    """Poste rattaché, départ fixé, en saisie : « volée 8/12 » et l'heure du dernier tir."""
    m = Montage(nb_cibles=1)
    jeton = m.rattacher(1)
    m.sessions.fixer_depart(jeton, 42)
    m.service.enregistrer_heartbeat(m.poste_id(1), "10.0.0.1")
    tir = datetime.datetime(2026, 3, 14, 8, 46, tzinfo=datetime.UTC)
    m.avancement.regler(1, AvancementCible(volee_courante=8, nb_volees=12, derniere_saisie=tir))

    ligne = m.ligne(1)

    assert ligne.avancement == Avancement(volee_courante=8, nb_volees=12)
    assert ligne.derniere_saisie == tir


def test_poste_rattache_sans_depart_courant_na_pas_d_avancement() -> None:
    """Rattaché mais aucun départ fixé (ADR-0034) : pas encore de grille → avancement « — »."""
    m = Montage(nb_cibles=1)
    m.rattacher(1)  # pas de fixer_depart
    m.service.enregistrer_heartbeat(m.poste_id(1), "10.0.0.1")

    ligne = m.ligne(1)
    assert ligne.etat is EtatPoste.EN_LIGNE
    assert ligne.avancement is None
    assert ligne.derniere_saisie is None


# --- Révocation ---


def test_revoquer_fait_repasser_le_poste_non_rattache() -> None:
    """CA/`D-07` : l'admin révoque un poste — sa session tombe, sa présence est oubliée."""
    m = Montage(nb_cibles=1)
    m.rattacher(1)
    m.service.enregistrer_heartbeat(m.poste_id(1), "10.0.0.1")
    assert m.ligne(1).etat is EtatPoste.EN_LIGNE

    m.service.revoquer_poste(m.tournoi_id, m.poste_id(1))

    ligne = m.ligne(1)
    assert ligne.etat is EtatPoste.NON_RATTACHE
    assert ligne.ip is None
    # La présence a bien été oubliée (pas seulement masquée par l'état).
    assert m.presence.derniere_activite(m.poste_id(1)) is None


def test_revoquer_est_idempotent() -> None:
    """Révoquer un poste déjà non rattaché ne lève rien (idempotent)."""
    m = Montage(nb_cibles=1)
    m.service.revoquer_poste(m.tournoi_id, m.poste_id(1))
    m.service.revoquer_poste(m.tournoi_id, m.poste_id(1))
    assert m.ligne(1).etat is EtatPoste.NON_RATTACHE


def test_revoquer_un_poste_inexistant_leve_introuvable() -> None:
    m = Montage(nb_cibles=1)
    with pytest.raises(PosteIntrouvable):
        m.service.revoquer_poste(m.tournoi_id, 999)


def test_revoquer_un_poste_d_un_autre_tournoi_leve_introuvable() -> None:
    """Un poste d'un tournoi voisin n'existe pas ici (même parti que `DepartIntrouvable`)."""
    m = Montage(nb_cibles=1)
    autre = m.tournois.ajouter(Tournoi.creer("Extérieur", _DATE))
    assert autre.id is not None
    poste_voisin = m.postes.ajouter(Poste.creer(autre.id, 1, "X1"))
    assert poste_voisin.id is not None

    with pytest.raises(PosteIntrouvable):
        m.service.revoquer_poste(m.tournoi_id, poste_voisin.id)


# --- Tournoi ---


def test_etat_d_un_tournoi_inexistant_leve_introuvable() -> None:
    m = Montage(nb_cibles=1)
    with pytest.raises(TournoiIntrouvable):
        m.service.etat(999)
