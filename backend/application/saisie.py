"""Service applicatif Saisie (E04US002) — saisir, valider, corriger la qualification d'un archer.

Orchestre le moteur métier `Serie`/`Volee` : il **résout la configuration** depuis la phase et le
blason (le pavé se déduit du blason tiré — `Blason.zones` — pas du barème), pilote l'agrégat, et
**bâtit les entrées d'audit** de validation et de correction (« qui / quand / avant-après »,
E10US005). Le « quand » est lu via le port `Horloge` (jamais dans le domaine, resté déterministe).

Frontières (cf. `stories/E04-saisie-scores.md`) :

- L'**autorisation par le poste** vit **ici**, pas dans un `Depends` d'API : les méthodes d'écriture
  reçoivent un `ContexteSaisie | None` (cible + départ courant) et cloisonnent la saisie au triplet
  `(tournoi, cible, départ)` — `SaisieHorsCible` sinon (ADR-0033 §3). Au service car un appelant
  **hors HTTP** (writer WS E04US009, orchestrateur E12US002) contournerait une garde d'API. Les
  archers de la grille se reconstituent depuis les `Affectation` (`archers_du_poste`), pas depuis le
  champ hérité `Archer.cible` (ADR-0033 §1). `contexte=None` = saisie **admin**, sans contrainte.
- Le **nom** de qui agit (scoreur en validation, rôle habilité en correction) est **fourni** au
  service (résolu par `exiger_scoreur` côté API) : le service reste pur, sans jeton ni session.
- L'**atomicité acte↔trace** (validation/correction) passe par le port
  `SerieRepository.enregistrer_avec_trace` (série + audit en une transaction, ADR-0035).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from application.erreurs import (
    ArcherIntrouvable,
    BlasonIntrouvable,
    CategorieIntrouvable,
    PhaseQualificationAbsente,
    SaisieHorsCible,
)
from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.depart import DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.phase import Phase, TypePhase
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    Horloge,
    InscriptionRepository,
    PhaseRepository,
    PlacementRepository,
    SerieRepository,
)
from domain.serie import Serie
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class ContexteSaisie:
    """Contexte d'autorisation d'une saisie **par un poste** : sa cible et son départ courant.

    Passé aux méthodes d'écriture pour cloisonner la saisie au **triplet** `(tournoi, cible,
    départ)` (ADR-0033 §3) : un poste ne saisit que pour un archer affecté à `(cible, départ)`.
    `None` (contexte absent) = saisie **admin**, sans contrainte de cible (E10US001) — l'admin, lui,
    n'est pas rattaché à un lieu.
    """

    cible_index: int
    depart_id: DepartId


@dataclass(frozen=True)
class ArcherPositionne:
    """Un archer et sa **position** (A..D) sur une cible — une ligne de la grille de saisie.

    Reconstitué depuis les `Affectation` du placement réel (ADR-0033), pas depuis `Archer.cible`.
    """

    position: str
    archer: Archer


@dataclass(frozen=True)
class EtatSerie:
    """État persisté d'une série, en **lecture** : l'agrégat `Serie` et le « quand » de ses volées.

    Le `created_at` de chaque volée (ex-017) vit **hors** du domaine `Volee` (arbitrage de revue) :
    il accompagne la série ici, par numéro, pour la consultation « volée N saisie par … à HH:MM ».
    """

    serie: Serie
    horodatages: dict[int, datetime.datetime]


def _valeurs_lisibles(serie: Serie, numero: int) -> str | None:
    """Rend les valeurs d'une volée sous forme lisible (« 10, 9, 8 ») pour l'audit, ou `None`."""
    volee = serie.volee(numero)
    return ", ".join(v.value for v in volee.valeurs) if volee is not None else None


class ServiceSaisie:
    """Cas d'usage de la saisie de qualification : saisir une volée, valider, corriger (tracé)."""

    def __init__(
        self,
        series: SerieRepository,
        phases: PhaseRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        placements: PlacementRepository,
        inscriptions: InscriptionRepository,
        horloge: Horloge,
    ) -> None:
        self._series = series
        self._phases = phases
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._placements = placements
        self._inscriptions = inscriptions
        self._horloge = horloge

    def archers_du_poste(
        self, tournoi_id: TournoiId, cible_index: int, depart_id: DepartId
    ) -> list[ArcherPositionne]:
        """Les archers **placés** sur `(cible, départ)`, avec leur position A..D, triés.

        La source de la grille de saisie (CA « grille ») : reconstituée depuis les `Affectation` du
        placement **réel** et ajustable (ADR-0033), donc un glisser-déposer d'archer (E03US004)
        déplace aussi *où il saisit*, sans code ici. Un archer en **réserve** (aucune affectation)
        n'apparaît pas. L'appelant fournit le départ courant du poste (déjà validé, ADR-0034).
        """
        inscriptions = {i.id: i for i in self._inscriptions.par_depart(depart_id)}
        grille: list[ArcherPositionne] = []
        for affectation in self._placements.par_depart(depart_id):
            if affectation.cible_index != cible_index:
                continue
            inscription = inscriptions.get(affectation.inscription_id)
            if inscription is None:
                continue  # défensif : affectation sans inscription correspondante
            archer = self._archers.par_id(inscription.archer_id)
            if archer is None or archer.tournoi_id != tournoi_id:
                continue
            grille.append(ArcherPositionne(position=affectation.position, archer=archer))
        grille.sort(key=lambda ligne: ligne.position)
        return grille

    def etat_serie(self, tournoi_id: TournoiId, archer_id: ArcherId) -> EtatSerie | None:
        """L'état persisté de la série de l'archer (volées + « quand »), ou `None` si rien de saisi.

        Chemin de lecture de la grille : la série (valeurs, marqueurs, verrou, cumul) **et** le
        `created_at` de chaque volée (ex-017), joints par numéro. Ne cloisonne pas à la cible : une
        lecture, l'appelant (API) a déjà établi le droit d'accès du poste.
        """
        serie = self._series.par_archer(tournoi_id, archer_id)
        if serie is None:
            return None
        return EtatSerie(serie=serie, horodatages=self._series.horodatages(tournoi_id, archer_id))

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        """Le « quand » (`created_at`) de chaque volée de l'archer, par numéro (`{}` sans série).

        Chemin de lecture **léger** pour bâtir la réponse d'un acte d'écriture depuis la `Serie`
        qu'il renvoie déjà, sans re-lire la série entière (`etat_serie`) : l'API dédoublonne
        l'**écriture** seule, puis lit ce « quand » **hors** de l'unité idempotente (ADR-0036).
        """
        return self._series.horodatages(tournoi_id, archer_id)

    def saisir_volee(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        saisie_par: str | None = None,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Saisit ou réédite (avant validation) la volée `numero` de l'archer.

        Le pavé (zones admises) se déduit du **blason** de l'archer, le nombre de flèches du
        **barème** de la phase. Persiste sans trace (une saisie ordinaire n'est pas un acte de fin).
        `contexte` cloisonne la saisie à la cible/départ du poste (ADR-0033 §3) ; `None` = admin.
        """
        archer = self._charger_archer(tournoi_id, archer_id, contexte)
        zones = self._zones_du_blason(archer)
        phase = self._phase_qualification(tournoi_id)
        serie = self._series.par_archer(tournoi_id, archer_id) or Serie.vide(tournoi_id, archer_id)
        serie = serie.saisir_volee(
            numero,
            valeurs,
            zones_admises=zones,
            nb_fleches_par_volee=phase.bareme.nb_fleches_par_volee,
            nb_volees_bareme=phase.bareme.nb_volees,
            saisie_par=saisie_par,
        )
        return self._series.enregistrer(serie)

    def valider(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        scoreur: str,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Valide la série de l'archer selon le grain de la phase, au nom du `scoreur`.

        Verrouille les volées concernées (fin de série ou lot de N, cf. `Serie.valider`) et laisse
        une **trace** `VALIDATION` (sans avant/après) dans la même transaction que l'écriture.
        `contexte` cloisonne au poste (ADR-0033 §3) — la garde vaut pour **tout** chemin d'écriture.

        ⚠️ Le `scoreur` est un **nom** (pour l'audit) : ce service **ne peut pas** vérifier que le
        scoreur officie dans **ce** tournoi. Cette garde (`ScoreurHorsTournoi`, 403) vit **à l'API**
        (`exiger_scoreur` résout le `Scoreur` + `_exiger_meme_tournoi`) — asymétrique avec la garde
        poste, descendue ici. Aucun appelant hors HTTP ne valide aujourd'hui ; **E04US009 (writer
        WS) devra la répliquer** — ou passer le tournoi du scoreur — s'il ouvre un tel chemin.
        """
        self._charger_archer(tournoi_id, archer_id, contexte)
        phase = self._phase_qualification(tournoi_id)
        serie = self._series.par_archer(tournoi_id, archer_id) or Serie.vide(tournoi_id, archer_id)
        serie = serie.valider(
            scoreur, grain=phase.validation, nb_volees_bareme=phase.bareme.nb_volees
        )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.VALIDATION,
            auteur=scoreur,
            horodatage=self._horloge.maintenant(),
            objet=f"série de qualification de l'archer {archer_id}",
        )
        return self._series.enregistrer_avec_trace(serie, entree)

    def corriger_volee(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        numero: int,
        nouvelles_valeurs: tuple[ZoneScore, ...],
        auteur: str,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Corrige une volée **verrouillée** de l'archer, au nom de l'`auteur` (rôle habilité).

        Chemin d'écriture unique sur une volée validée. Laisse une trace `CORRECTION_SCORE` portant
        l'**avant** et l'**après**, dans la même transaction que la réécriture (ADR-0035). Le cumul
        se recalcule mécaniquement. `contexte` cloisonne au poste (ADR-0033 §3) ; `None` = admin.
        """
        archer = self._charger_archer(tournoi_id, archer_id, contexte)
        zones = self._zones_du_blason(archer)
        phase = self._phase_qualification(tournoi_id)
        serie = self._series.par_archer(tournoi_id, archer_id) or Serie.vide(tournoi_id, archer_id)
        avant = _valeurs_lisibles(serie, numero)
        serie = serie.corriger_volee(
            numero,
            nouvelles_valeurs,
            par=auteur,
            zones_admises=zones,
            nb_fleches_par_volee=phase.bareme.nb_fleches_par_volee,
        )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.CORRECTION_SCORE,
            auteur=auteur,
            horodatage=self._horloge.maintenant(),
            objet=f"volée {numero} de l'archer {archer_id}",
            avant=avant,
            apres=_valeurs_lisibles(serie, numero),
        )
        return self._series.enregistrer_avec_trace(serie, entree)

    def _charger_archer(
        self, tournoi_id: TournoiId, archer_id: ArcherId, contexte: ContexteSaisie | None
    ) -> Archer:
        """L'archer du tournoi ; `ArcherIntrouvable` s'il est inconnu ou d'un autre tournoi.

        Si un `contexte` de poste est fourni, cloisonne en plus au triplet `(tournoi, cible,
        départ)` (ADR-0033 §3) : l'archer doit être **affecté** à cette cible sur ce départ, sinon
        `SaisieHorsCible` (403). `contexte=None` (admin) laisse la saisie ouverte, sans contrainte.
        """
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")
        if contexte is not None:
            self._verifier_archer_sur_poste(archer_id, contexte)
        return archer

    def _verifier_archer_sur_poste(self, archer_id: ArcherId, contexte: ContexteSaisie) -> None:
        """Refuse (`SaisieHorsCible`) un archer non affecté à la cible/départ courant du poste.

        Reconstitue l'appartenance depuis le placement réel (ADR-0033) : l'archer doit être inscrit
        **sur ce départ** et son affectation porter **cette cible**. Non inscrit, en réserve, ou
        placé ailleurs → éconduit. Numéros de cible répétés d'un tournoi à l'autre : le départ (donc
        le tournoi) et la cible ferment la faille (ADR-0033 §3, triplet).
        """
        inscription = self._inscriptions.par_archer_et_depart(archer_id, contexte.depart_id)
        if inscription is not None and inscription.id is not None:
            for affectation in self._placements.par_depart(contexte.depart_id):
                if (
                    affectation.inscription_id == inscription.id
                    and affectation.cible_index == contexte.cible_index
                ):
                    return
        raise SaisieHorsCible(f"Ce poste ne sert pas l'archer {archer_id} sur cette cible.")

    def _phase_qualification(self, tournoi_id: TournoiId) -> Phase:
        """La phase de qualification ; `PhaseQualificationAbsente` si elle n'existe pas."""
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        if phase is None:
            raise PhaseQualificationAbsente(
                "La qualification n'est pas encore configurée pour ce tournoi."
            )
        return phase

    def _zones_du_blason(self, archer: Archer) -> tuple[ZoneScore, ...]:
        """Les zones admises du blason par défaut de la catégorie de l'archer (le pavé de saisie).

        `CategorieIntrouvable` si la catégorie manque ; `BlasonIntrouvable` si la catégorie n'a pas
        de blason par défaut (pavé indéterminable) ou si ce blason n'existe pas.
        """
        categorie = self._categories.par_id(archer.categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Catégorie {archer.categorie_id} introuvable.")
        if categorie.blason_id is None:
            raise BlasonIntrouvable(
                "L'archer n'a pas de blason par défaut : le pavé de saisie est indéterminable."
            )
        blason = self._blasons.par_id(categorie.blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Blason {categorie.blason_id} introuvable.")
        return blason.zones
