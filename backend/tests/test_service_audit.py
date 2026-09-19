"""Tests du service applicatif Audit (E10US005, socle) — repositories & horloge factices.

Écrits **depuis le CA** (règle 9). Le service est testé **en isolation** : un faux repository en
mémoire (conforme au port `AuditRepository`), un faux tournoi et une **horloge figée** suffisent —
ni base ni serveur. On vérifie ce qui est propre au service : l'horodatage **daté par l'horloge**
(déterminisme, règle 9), la consultation restreinte au tournoi et son ordre chronologique, et le
404 sur tournoi inconnu. Les invariants de l'entrée (auteur/objet non vides) sont couverts par le
domaine (`test_domain_entree_audit`).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.audit import ServiceAudit, ServiceExportAudit
from application.erreurs import FormatExportIndisponible, TournoiIntrouvable
from application.exports import FormatExport, RegistreDeFormats
from domain.entree_audit import ActionAuditee, EntreeAudit, JournalAudit
from domain.erreurs import AuteurAuditInvalide
from domain.tournoi import DescendanceTournoi, Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


class FauxAuditRepository:
    """Journal en mémoire conforme au port `AuditRepository` (ajout seul, ordre chronologique)."""

    def __init__(self) -> None:
        self._entrees: list[EntreeAudit] = []
        self._sequence = 0

    def consigner(self, entree: EntreeAudit) -> EntreeAudit:
        self._sequence += 1
        persiste = dataclasses.replace(entree, id=self._sequence)
        self._entrees.append(persiste)
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        # Conservées dans l'ordre d'insertion (chronologique) : l'adapter SQL, lui, ordonne par id.
        return [e for e in self._entrees if e.tournoi_id == tournoi_id]


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

    def compter_descendance(self, tournoi_id: TournoiId) -> DescendanceTournoi:
        # Vide par défaut : ces tests ne portent pas sur la suppression (E01US026). Le dépôt
        # partagé de `conftest.py` la rend réglable pour ceux qui en ont besoin.
        return DescendanceTournoi()


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` : renvoie toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class Montage:
    """Attelage d'un test : service + repos + horloge figée + `tournoi_id`."""

    def __init__(self, instant: datetime.datetime = _QUAND) -> None:
        self.audit = FauxAuditRepository()
        self.tournois = FauxTournoiRepository()
        self.horloge = HorlogeFigee(instant)
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.service = ServiceAudit(self.audit, self.tournois, self.horloge)


def test_consigner_date_l_entree_par_l_horloge() -> None:
    """CA « quand » : l'horodatage vient de l'**horloge injectée**, pas de `datetime.now`."""
    m = Montage()

    entree = m.service.consigner(
        m.tournoi_id, ActionAuditee.VALIDATION, "DURAND Jean", "Série 3 — cible 4A"
    )

    assert entree.id is not None
    assert entree.horodatage == _QUAND
    assert entree.action is ActionAuditee.VALIDATION
    assert entree.auteur == "DURAND Jean"


def test_consigner_une_correction_conserve_avant_apres() -> None:
    m = Montage()

    entree = m.service.consigner(
        m.tournoi_id,
        ActionAuditee.CORRECTION_SCORE,
        "ROUX Sophie",
        "Série 3, flèche 2",
        avant="8",
        apres="9",
    )

    assert (entree.avant, entree.apres) == ("8", "9")


def test_consigner_propage_un_auteur_vide() -> None:
    """L'invariant domaine remonte tel quel (pas de garde applicative qui l'avalerait)."""
    m = Montage()
    with pytest.raises(AuteurAuditInvalide):
        m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "  ", "Série 3")


def test_lister_ne_renvoie_que_les_entrees_du_tournoi() -> None:
    m = Montage()
    autre = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre.id is not None
    du_tournoi = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 3")
    m.service.consigner(autre.id, ActionAuditee.VALIDATION, "MARTIN", "Série 1")

    assert m.service.lister(m.tournoi_id) == [du_tournoi]


def test_lister_rend_l_ordre_chronologique() -> None:
    """Un journal se lit dans le sens du temps (ordre d'insertion préservé)."""
    m = Montage()
    a = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 1")
    b = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 2")
    c = m.service.consigner(m.tournoi_id, ActionAuditee.CORRECTION_SCORE, "ROUX", "Série 1, f2")

    assert m.service.lister(m.tournoi_id) == [a, b, c]


def test_lister_vide_sans_entree() -> None:
    m = Montage()
    assert m.service.lister(m.tournoi_id) == []


def test_lister_refuse_un_tournoi_inexistant() -> None:
    m = Montage()
    with pytest.raises(TournoiIntrouvable):
        m.service.lister(404)


# --- E16US016 : « le journal d'audit se consulte, PUIS s'exporte » -------------------------------
#
# Tests écrits **depuis le CA, avant implémentation** (règle 9). Le CA d'E16US016 tient en deux
# temps : on consulte (écran, testé côté front), et on exporte. Ce qui se vérifie ici est le
# **second** temps, côté service — la composition du document et la résolution du format.
#
# ⚠️ Pourquoi un service à part et non une méthode de plus sur `ServiceAudit` : `ServiceAudit` est
# le **socle d'écriture** de la trace, appelé par huit chemins de production. Lui injecter un
# registre de formats de fichier ferait dépendre l'écriture d'une trace de l'outillage
# d'exploitation qui la relit. Le service d'export lit le journal par un **port étroit**
# (`LecteurJournalAudit`), même discipline de ségrégation d'interface que `LecteurRecapClub`
# (`application.listes_impression`) : un faux lecteur suffit en test, et l'export n'écrit rien.


class _FauxGenerateurJournal:
    """Générateur sentinelle : retient le document reçu, rend des octets reconnaissables."""

    def __init__(self, marque: str) -> None:
        self.marque = marque
        self.recu: JournalAudit | None = None

    def journal(self, journal: JournalAudit) -> bytes:
        self.recu = journal
        return f"<{self.marque}>".encode()


class _LecteurFige:
    """Réalise `LecteurJournalAudit` : rend un journal figé, ou lève sur tournoi inconnu."""

    def __init__(self, entrees: list[EntreeAudit], tournoi_connu: TournoiId) -> None:
        self._entrees = entrees
        self._tournoi_connu = tournoi_connu

    def lister(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        if tournoi_id != self._tournoi_connu:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return list(self._entrees)


def _montage_export(
    formats: dict[FormatExport, _FauxGenerateurJournal] | None = None,
) -> tuple[Montage, ServiceExportAudit, dict[FormatExport, _FauxGenerateurJournal]]:
    m = Montage()
    m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND Jean", "Série 1")
    m.service.consigner(
        m.tournoi_id, ActionAuditee.CORRECTION_SCORE, "ROUX Ana", "Série 1, f2", "8", "9"
    )
    generateurs = formats or {
        FormatExport.CSV: _FauxGenerateurJournal("csv"),
        FormatExport.XLSX: _FauxGenerateurJournal("xlsx"),
    }
    export = ServiceExportAudit(
        _LecteurFige(m.service.lister(m.tournoi_id), m.tournoi_id),
        m.tournois,
        RegistreDeFormats(generateurs),
    )
    return m, export, generateurs


def test_l_export_rend_les_octets_du_format_demande() -> None:
    """CA « au format de mon choix » : le format **résout un adapter**, il ne branche rien."""
    m, export, _ = _montage_export()

    assert export.exporter(m.tournoi_id, FormatExport.CSV) == b"<csv>"
    assert export.exporter(m.tournoi_id, FormatExport.XLSX) == b"<xlsx>"


def test_le_document_porte_le_nom_du_tournoi_et_ses_entrees_chronologiques() -> None:
    """Le document se suffit à lui-même : un fichier détaché de l'écran doit dire de quoi il parle.

    L'ordre est celui du journal — un journal d'audit qui réordonnerait ses lignes cesserait de
    servir à ce pour quoi il existe (prouver l'enchaînement des actes).
    """
    m, export, generateurs = _montage_export()

    export.exporter(m.tournoi_id, FormatExport.CSV)

    document = generateurs[FormatExport.CSV].recu
    assert document is not None
    assert document.tournoi == "Salle 18m"
    assert [entree.objet for entree in document.entrees] == ["Série 1", "Série 1, f2"]
    assert document.entrees[1].avant == "8"
    assert document.entrees[1].apres == "9"


def test_le_contenu_compose_ne_depend_pas_du_format() -> None:
    """Garde-fou jumeau de celui des listes (ADR-0101) : le format n'agit **qu'au rendu**.

    ⚠️ Sans lui, une divergence de *données* entre le CSV et le tableur passerait pour une
    divergence de *présentation*, qui est voulue — et personne ne saurait lequel des deux fichiers
    fait foi dans un litige, c'est-à-dire le seul usage de ce document.
    """
    m, export, generateurs = _montage_export()

    export.exporter(m.tournoi_id, FormatExport.CSV)
    export.exporter(m.tournoi_id, FormatExport.XLSX)

    assert generateurs[FormatExport.CSV].recu == generateurs[FormatExport.XLSX].recu


def test_un_format_non_cable_est_refuse() -> None:
    """Le PDF n'est pas câblé pour ce document : le refus est explicite (→ 400), pas un PDF vide."""
    m, export, _ = _montage_export()

    with pytest.raises(FormatExportIndisponible):
        export.exporter(m.tournoi_id, FormatExport.PDF)


def test_l_export_refuse_un_tournoi_inexistant() -> None:
    m, export, _ = _montage_export()

    with pytest.raises(TournoiIntrouvable):
        export.exporter(404, FormatExport.CSV)


def test_les_formats_disponibles_derivent_du_cablage() -> None:
    """ADR-0101 §3 : ce que le catalogue publie pour ce document vient du registre, pas d'une liste.

    Le décor **mono-format** est délibéré : une liste écrite à la main en annoncerait deux.
    """
    _, export, _ = _montage_export({FormatExport.CSV: _FauxGenerateurJournal("csv")})

    assert export.formats_disponibles == (FormatExport.CSV,)


def test_un_journal_vide_s_exporte_quand_meme() -> None:
    """Un tournoi sans acte tracé rend un document **vide mais valide**, pas une erreur.

    ⚠️ L'inverse serait lu comme une panne par l'organisateur, alors que « rien ne s'est passé »
    est une réponse d'audit parfaitement légitime — et c'est l'état d'un tournoi le matin.
    """
    m = Montage()
    generateur = _FauxGenerateurJournal("csv")
    export = ServiceExportAudit(
        _LecteurFige([], m.tournoi_id),
        m.tournois,
        RegistreDeFormats({FormatExport.CSV: generateur}),
    )

    assert export.exporter(m.tournoi_id, FormatExport.CSV) == b"<csv>"
    assert generateur.recu is not None
    assert generateur.recu.entrees == ()
