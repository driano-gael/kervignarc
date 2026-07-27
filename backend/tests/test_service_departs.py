"""Tests du service applicatif Departs (E02US004, ADR-0017 ; E02US010) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent. On y vérifie ce qui est propre au service — l'**attribution du numéro** (max + 1, jamais
réutilisé après suppression), la vérification d'**existence** du tournoi et du départ dans ce
tournoi, et le refus de supprimer le **dernier** départ d'un tournoi non-brouillon (E02US010) — le
reste (bornes du tarif, format `HH:MM` de l'horaire) étant couvert par le domaine.
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import NamedTuple

import pytest

from application.departs import ServiceDeparts
from application.erreurs import (
    DepartAvecInscriptions,
    DepartEnCoursNonConfirme,
    DepartIntrouvable,
    DernierDepartNonSupprimable,
    TournoiIntrouvable,
)
from domain.cycle_depart import AvancementDepart, EtatDepart
from domain.depart import DepartId
from domain.erreurs import TarifDepartInvalide
from domain.inscription import Inscription
from domain.tournoi import StatutTournoi, Tournoi, TournoiId
from tests.conftest import FauxDepartRepository, FauxInscriptionRepository

_DATE = datetime.date(2026, 3, 14)

# Avancement par défaut d'un créneau : aucun tir → **ouvert**. Les tests de cycle (E12US008)
# posent explicitement un avancement lancé/clos ; tous les autres (E02US004/E02US009) restent
# ouverts, donc librement éditables — leur comportement est inchangé.
_OUVERT = AvancementDepart(nb_places=0, nb_ayant_tire=0, nb_series_closes=0)


class FauxLecteurAvancement:
    """Faux `LecteurAvancementDepart` : renvoie l'avancement qu'on lui pose, ouvert par défaut.

    Le vrai lecteur est `ServiceCompletude` (il agrège placements/séries/forfaits) ; ici on injecte
    directement l'état voulu, le service des départs n'ayant à connaître que le **verdict**, pas la
    façon de le calculer (port étroit, comme `LecteurPaiements`).
    """

    def __init__(self) -> None:
        self._par_depart: dict[DepartId, AvancementDepart] = {}

    def poser(self, depart_id: DepartId, avancement: AvancementDepart) -> None:
        self._par_depart[depart_id] = avancement

    def avancement_depart(self, tournoi_id: TournoiId, depart_id: DepartId) -> AvancementDepart:
        return self._par_depart.get(depart_id, _OUVERT)


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


class Montage(NamedTuple):
    """Attelage d'un test de départs : le service et les repos qu'on doit garnir à la main.

    Le garde-fou « départ avec inscriptions » (E02US009) suppose de poser des inscriptions dans le
    repo avant de supprimer — d'où l'exposition des repos, invisible dans le n-uplet initial
    `(service, tournoi_id)`.
    """

    service: ServiceDeparts
    departs: FauxDepartRepository
    inscriptions: FauxInscriptionRepository
    avancements: FauxLecteurAvancement
    tournois: FauxTournoiRepository
    tournoi_id: TournoiId


def _monter() -> Montage:
    """Fabrique un service câblé sur des repos factices et un tournoi (brouillon) déjà créé."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    inscriptions = FauxInscriptionRepository()
    avancements = FauxLecteurAvancement()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return Montage(
        ServiceDeparts(departs, tournois, inscriptions, avancements),
        departs,
        inscriptions,
        avancements,
        tournois,
        tournoi.id,
    )


def _service_avec_tournoi() -> tuple[ServiceDeparts, TournoiId]:
    """Raccourci `(service, tournoi_id)` pour les tests qui ignorent les repos."""
    montage = _monter()
    return montage.service, montage.tournoi_id


def test_creer_attribue_les_numeros_dans_l_ordre() -> None:
    """Le premier créneau porte le n° 1, le suivant le n° 2, etc. — attribués par le service."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.creer(tournoi_id, 810, "09:00").numero == 1
    assert service.creer(tournoi_id, 810, "09:00").numero == 2
    assert service.creer(tournoi_id, 1000, "09:00").numero == 3


def test_creer_persiste_tarif_et_horaire() -> None:
    """Le tarif et l'horaire fournis sont conservés."""
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "09:00")
    assert (depart.tarif_centimes, depart.horaire, depart.tournoi_id) == (810, "09:00", tournoi_id)


def test_creer_persiste_le_quota() -> None:
    """Le quota fourni est conservé ; absent, le départ n'a pas de plafond (E02US006)."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.creer(tournoi_id, 810, "09:00", quota=20).quota == 20
    assert service.creer(tournoi_id, 810, "09:00").quota is None


def test_creer_leve_si_tournoi_introuvable() -> None:
    """Créer un départ sur un tournoi inexistant lève `TournoiIntrouvable` (→ 404)."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(TournoiIntrouvable):
        service.creer(999, 810, "09:00")


def test_creer_propage_l_erreur_de_tarif() -> None:
    """Un tarif hors plage fait remonter l'erreur du domaine (rien n'est persisté)."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(TarifDepartInvalide):
        service.creer(tournoi_id, -1, "09:00")
    assert service.lister(tournoi_id) == []


def test_supprimer_un_creneau_intermediaire_laisse_un_trou_definitif() -> None:
    """Supprimer un créneau **du milieu** laisse un trou : le suivant prend max + 1, pas le trou.

    Le numéro est toujours max + 1 (pas un rang recalculé) : le n° 2 supprimé n'est pas réattribué,
    le suivant prend 4.
    """
    service, tournoi_id = _service_avec_tournoi()
    service.creer(tournoi_id, 810, "09:00")  # n° 1
    deuxieme = service.creer(tournoi_id, 810, "09:00")  # n° 2
    service.creer(tournoi_id, 810, "09:00")  # n° 3
    assert deuxieme.id is not None
    service.supprimer(tournoi_id, deuxieme.id)

    assert service.creer(tournoi_id, 810, "09:00").numero == 4
    assert [d.numero for d in service.lister(tournoi_id)] == [1, 3, 4]


def test_supprimer_le_dernier_creneau_libere_son_numero() -> None:
    """Supprimer **le dernier** créneau (plus grand n°) libère son numéro : max + 1 le reprend.

    Conséquence assumée de « toujours max + 1 » (pas un rang recalculé). Sans effet : inscriptions
    et placement référencent l'`id` technique, pas le `numero`. (Le tournoi est en brouillon, donc
    supprimer le dernier départ reste permis — E02US010.)
    """
    service, tournoi_id = _service_avec_tournoi()
    service.creer(tournoi_id, 810, "09:00")  # n° 1
    dernier = service.creer(tournoi_id, 810, "09:00")  # n° 2
    assert dernier.id is not None
    service.supprimer(tournoi_id, dernier.id)

    assert service.creer(tournoi_id, 810, "09:00").numero == 2
    assert [d.numero for d in service.lister(tournoi_id)] == [1, 2]


def test_lister_trie_par_numero_et_isole_le_tournoi() -> None:
    """`lister` renvoie les départs du tournoi, triés par numéro — pas ceux d'un autre tournoi."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(
        departs, tournois, FauxInscriptionRepository(), FauxLecteurAvancement()
    )
    service.creer(a.id, 810, "09:00")
    service.creer(a.id, 810, "09:00")
    service.creer(b.id, 810, "09:00")

    assert [d.numero for d in service.lister(a.id)] == [1, 2]
    assert [d.numero for d in service.lister(b.id)] == [1]


def test_lister_leve_si_tournoi_introuvable() -> None:
    service, _ = _service_avec_tournoi()
    with pytest.raises(TournoiIntrouvable):
        service.lister(999)


def test_modifier_change_tarif_et_horaire_garde_le_numero() -> None:
    """`modifier` édite tarif et horaire ; le numéro et le rattachement ne bougent pas."""
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "09:00")
    assert depart.id is not None

    modifie = service.modifier(tournoi_id, depart.id, 1250, "14:00")
    assert (modifie.numero, modifie.tarif_centimes, modifie.horaire) == (1, 1250, "14:00")


def test_modifier_remplace_le_quota_et_l_omission_le_retire() -> None:
    """Remplacement complet : `modifier` pose le quota fourni ; l'omettre **retire** le plafond
    existant (CA E02US006). L'horaire, lui, reste obligatoire."""
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "09:00", quota=20)
    assert depart.id is not None

    assert service.modifier(tournoi_id, depart.id, 810, "09:00", quota=30).quota == 30
    assert service.modifier(tournoi_id, depart.id, 810, "09:00").quota is None  # omis → retiré


def test_modifier_leve_si_depart_d_un_autre_tournoi() -> None:
    """Éditer un départ via le mauvais tournoi → `DepartIntrouvable` (on ne fuite pas le voisin)."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(
        departs, tournois, FauxInscriptionRepository(), FauxLecteurAvancement()
    )
    depart = service.creer(a.id, 810, "09:00")
    assert depart.id is not None

    with pytest.raises(DepartIntrouvable):
        service.modifier(b.id, depart.id, 900, "09:00")


def test_modifier_leve_si_introuvable() -> None:
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(DepartIntrouvable):
        service.modifier(tournoi_id, 999, 900, "09:00")


def test_supprimer_retire_le_depart() -> None:
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "09:00")
    assert depart.id is not None
    service.supprimer(tournoi_id, depart.id)
    assert service.lister(tournoi_id) == []


def test_supprimer_leve_si_depart_d_un_autre_tournoi() -> None:
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(
        departs, tournois, FauxInscriptionRepository(), FauxLecteurAvancement()
    )
    depart = service.creer(a.id, 810, "09:00")
    assert depart.id is not None

    with pytest.raises(DepartIntrouvable):
        service.supprimer(b.id, depart.id)


def test_supprimer_leve_si_introuvable() -> None:
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(DepartIntrouvable):
        service.supprimer(tournoi_id, 999)


def test_supprimer_depart_avec_inscriptions_signale() -> None:
    """Un créneau qui porte des inscriptions ne se supprime pas d'un clic (CA E02US009, ADR-0018).

    Un **signalement** (`DepartAvecInscriptions`), pas un refus : l'admin peut confirmer. Tant qu'il
    ne l'a pas fait, rien n'est détruit — le départ survit.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer_id=1, depart_id=depart.id))

    with pytest.raises(DepartAvecInscriptions):
        m.service.supprimer(m.tournoi_id, depart.id)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [depart.id]


def test_signalement_depart_decompte_les_inscriptions_dont_payees() -> None:
    """Le message énumère le nombre d'inscriptions **et** de payées (CA E02US009, ADR-0018).

    Les payées sont une somme encaissée qui deviendra un remboursement (E08US005) : l'admin doit la
    voir avant de trancher. Un message vague ferait disparaître l'argent en silence.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))
    m.inscriptions.ajouter(Inscription.creer(2, depart.id).marquer_paye(True))

    with pytest.raises(DepartAvecInscriptions) as leve:
        m.service.supprimer(m.tournoi_id, depart.id)
    assert "2 inscriptions" in leve.value.message
    assert "1 déjà payée" in leve.value.message


def test_signalement_depart_accorde_au_singulier() -> None:
    """Une seule inscription, aucune payée : « 1 inscription », sans mention de payée.

    Non-régression de lisibilité (patron du message d'`ArcherEngage`) : un message lu au moment de
    détruire des données se lit, il ne se décode pas.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))

    with pytest.raises(DepartAvecInscriptions) as leve:
        m.service.supprimer(m.tournoi_id, depart.id)
    assert "1 inscription" in leve.value.message
    # Aucune payée : ni décompte « dont N déjà payée », ni clause de remboursement — cette dernière
    # ne s'affiche que si au moins une inscription était réglée (sinon elle évoquerait un
    # remboursement fictif, corrigé en revue E02US009).
    assert "dont" not in leve.value.message
    assert "rembourser" not in leve.value.message


def test_supprimer_depart_avec_inscriptions_confirme_efface() -> None:
    """`autoriser_suppression_inscrits=True` : l'admin confirme, le créneau part (CA E02US009)."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))

    m.service.supprimer(m.tournoi_id, depart.id, autoriser_suppression_inscrits=True)
    assert m.service.lister(m.tournoi_id) == []


# --- Dernier départ d'un tournoi non-brouillon (E02US010) --------------------------------------
# CA : un tournoi ne peut passer prêt/en_cours sans ≥ 1 départ (garde côté ServiceTournois) ;
# supprimer le **dernier** départ d'un tournoi non-brouillon est **refusé** (`DernierDepart-
# NonSupprimable`). Sur un brouillon, aucune borne. Aucun drapeau ne lève ce refus dur.


def _passer_statut(m: Montage, statut: StatutTournoi) -> None:
    """Force le statut du tournoi du montage (raccourci : on ne rejoue pas les transitions)."""
    tournoi = m.tournois.par_id(m.tournoi_id)
    assert tournoi is not None
    m.tournois.enregistrer(dataclasses.replace(tournoi, statut=statut))


def test_supprimer_le_dernier_depart_d_un_tournoi_non_brouillon_est_refuse() -> None:
    """Le dernier créneau d'un tournoi engagé (prêt/en_cours…) ne se supprime pas (E02US010)."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    _passer_statut(m, StatutTournoi.EN_COURS)

    with pytest.raises(DernierDepartNonSupprimable):
        m.service.supprimer(m.tournoi_id, depart.id)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [depart.id]


def test_supprimer_un_depart_non_dernier_d_un_tournoi_non_brouillon_passe() -> None:
    """Tant qu'il reste un autre créneau, la suppression d'un départ d'un tournoi engagé passe."""
    m = _monter()
    premier = m.service.creer(m.tournoi_id, 810, "09:00")
    second = m.service.creer(m.tournoi_id, 810, "10:00")
    assert premier.id is not None and second.id is not None
    _passer_statut(m, StatutTournoi.EN_COURS)

    m.service.supprimer(m.tournoi_id, second.id)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [premier.id]


def test_supprimer_le_dernier_depart_d_un_brouillon_reste_permis() -> None:
    """Sur un tournoi **brouillon**, supprimer le dernier créneau reste permis (non engagé)."""
    m = _monter()  # tournoi en brouillon par défaut
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None

    m.service.supprimer(m.tournoi_id, depart.id)
    assert m.service.lister(m.tournoi_id) == []


def test_le_refus_du_dernier_depart_ne_se_leve_par_aucun_drapeau() -> None:
    """`DernierDepartNonSupprimable` est un **refus dur** : ni `autoriser_suppression_inscrits` ni
    `confirme_cycle` ne le contournent (E02US010). Il prime aussi sur ces confirmations."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    _passer_statut(m, StatutTournoi.PRET)

    with pytest.raises(DernierDepartNonSupprimable):
        m.service.supprimer(
            m.tournoi_id, depart.id, autoriser_suppression_inscrits=True, confirme_cycle=True
        )


# --- Cycle de vie du créneau (E12US008) --------------------------------------------------------
# CA : un créneau *ouvert* (aucun score) reste librement éditable ; *lancé* (au moins une flèche) ou
# *clos* (toutes séries closes), le modifier ou le supprimer est **contrôlé** — signalé et
# confirmable (réutilise le mécanisme d'alerte chiffrée d'E12US007). L'état est **dérivé** d'un fait
# réel, jamais saisi.


def _lance(nb_tireurs: int = 8) -> AvancementDepart:
    """Un créneau lancé : des archers ont tiré, aucune série close."""
    return AvancementDepart(nb_places=12, nb_ayant_tire=nb_tireurs, nb_series_closes=0)


def _clos() -> AvancementDepart:
    """Un créneau clos : toutes les séries des archers placés sont closes."""
    return AvancementDepart(nb_places=12, nb_ayant_tire=12, nb_series_closes=12)


def test_modifier_creneau_ouvert_reste_libre() -> None:
    """Aucun score consigné : éditer le créneau ne demande **aucune** confirmation (E02US009)."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    # avancement ouvert par défaut
    modifie = m.service.modifier(m.tournoi_id, depart.id, 1250, "14:00")
    assert modifie.tarif_centimes == 1250


def test_modifier_creneau_lance_exige_confirmation() -> None:
    """Un créneau **lancé** ne se modifie pas d'un clic : `DepartEnCoursNonConfirme` (→ 409).

    Signalement chiffré, pas un refus : l'admin peut forcer avec `confirme_cycle=True`. Tant qu'il
    ne l'a pas fait, rien n'est écrit — le tarif d'origine survit.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.avancements.poser(depart.id, _lance())

    with pytest.raises(DepartEnCoursNonConfirme):
        m.service.modifier(m.tournoi_id, depart.id, 1250, "14:00")
    assert m.service.lister(m.tournoi_id)[0].tarif_centimes == 810


def test_modifier_creneau_lance_confirme_passe() -> None:
    """Avec `confirme_cycle=True`, l'admin assume et la modification s'applique (E12US008)."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.avancements.poser(depart.id, _lance())

    modifie = m.service.modifier(m.tournoi_id, depart.id, 1250, "14:00", confirme_cycle=True)
    assert modifie.tarif_centimes == 1250


def test_modifier_creneau_clos_exige_aussi_confirmation() -> None:
    """Un créneau **clos** (session finie) est protégé comme un lancé : confirmation requise."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.avancements.poser(depart.id, _clos())

    with pytest.raises(DepartEnCoursNonConfirme):
        m.service.modifier(m.tournoi_id, depart.id, 1250, "14:00")


def test_details_du_signalement_cycle_chiffrent_etat_et_tireurs() -> None:
    """Le signalement porte l'**état** et le **nombre d'archers ayant tiré** (canal `details`).

    Comme `ReplacementNonConfirme` (E12US007), l'alerte est **chiffrée au moment d'agir** — le front
    dit « ce créneau est lancé, 8 archers ont déjà tiré » sans reconstituer l'impact lui-même.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.avancements.poser(depart.id, _lance(nb_tireurs=8))

    with pytest.raises(DepartEnCoursNonConfirme) as leve:
        m.service.modifier(m.tournoi_id, depart.id, 1250, "09:00")
    assert leve.value.details == {"etat": EtatDepart.LANCE.value, "archers_ayant_tire": 8}


def test_supprimer_creneau_ouvert_garde_le_comportement_e02us009() -> None:
    """Non-régression : un créneau **ouvert** avec inscriptions signale toujours l'inscription.

    Le garde-fou de cycle ne s'ajoute qu'aux créneaux lancés/clos ; sur un ouvert, seul le
    signalement d'inscriptions (E02US009) joue — comportement strictement inchangé.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))

    with pytest.raises(DepartAvecInscriptions):
        m.service.supprimer(m.tournoi_id, depart.id)


def test_supprimer_creneau_lance_exige_la_confirmation_de_cycle() -> None:
    """Supprimer un créneau **lancé** lève `DepartEnCoursNonConfirme`, pas le signalement
    d'inscriptions : le fait dominant est qu'on va détruire une **session de tir**, pas juste des
    inscriptions.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))
    m.avancements.poser(depart.id, _lance())

    with pytest.raises(DepartEnCoursNonConfirme):
        m.service.supprimer(m.tournoi_id, depart.id)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [depart.id]


def test_lister_avec_etat_expose_l_etat_derive_par_creneau() -> None:
    """`lister_avec_etat` propage l'état dérivé de chaque créneau — c'est le badge du CA.

    La dérivation LANCE/CLOS est prouvée au domaine (`AvancementDepart.etat`) ; ici on verrouille
    la **propagation** service → liste (le livrable visible), qui repose sur le port d'avancement.
    """
    m = _monter()
    ouvert = m.service.creer(m.tournoi_id, 810, "09:00")
    lance = m.service.creer(m.tournoi_id, 810, "10:00")
    assert ouvert.id is not None and lance.id is not None
    m.avancements.poser(lance.id, _lance())

    etats = {depart.id: etat for depart, etat in m.service.lister_avec_etat(m.tournoi_id)}
    assert etats[ouvert.id] is EtatDepart.OUVERT
    assert etats[lance.id] is EtatDepart.LANCE
    # L'accès unitaire (utilisé après édition) donne le même verdict.
    assert m.service.etat(m.tournoi_id, lance.id) is EtatDepart.LANCE


def test_supprimer_creneau_lance_ne_se_contourne_pas_par_inscriptions() -> None:
    """`autoriser_suppression_inscrits` **seul** ne contourne pas le garde-fou de cycle (E12US008).

    Verrouille l'**ordre des gardes** : sur un créneau lancé, la confirmation de cycle passe avant
    le signalement d'inscriptions. Un refactor qui inverserait l'ordre supprimerait en silence une
    session de tir — ce test l'attrape. (Le tournoi reste en brouillon : le refus « dernier départ »
    d'E02US010 ne s'y applique pas, seul le garde-fou de cycle est en jeu.)
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))
    m.avancements.poser(depart.id, _lance())

    with pytest.raises(DepartEnCoursNonConfirme):
        m.service.supprimer(m.tournoi_id, depart.id, autoriser_suppression_inscrits=True)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [depart.id]


def test_supprimer_creneau_lance_confirme_subsume_les_inscriptions() -> None:
    """`confirme_cycle=True` **subsume** le garde-fou d'inscriptions : le créneau part sans exiger,
    en plus, `autoriser_suppression_inscrits`.

    Confirmer qu'on détruit une session de tir en cours couvre *a fortiori* ses inscriptions —
    exiger une seconde confirmation serait un double dialogue (arbitrage E12US008). (Le tournoi
    reste en brouillon : le refus « dernier départ » d'E02US010 ne s'applique pas.)
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810, "09:00")
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))
    m.avancements.poser(depart.id, _lance())

    m.service.supprimer(m.tournoi_id, depart.id, confirme_cycle=True)
    assert m.service.lister(m.tournoi_id) == []
