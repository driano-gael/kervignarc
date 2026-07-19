"""Service applicatif Saisie (E04US002) — saisir, valider, corriger la qualification d'un archer.

Orchestre le moteur métier `Serie`/`Volee` : il **résout la configuration** depuis la phase et le
blason (le pavé se déduit du blason tiré — `Blason.zones` — pas du barème), pilote l'agrégat, et
**bâtit les entrées d'audit** de validation et de correction (« qui / quand / avant-après »,
E10US005). Le « quand » est lu via le port `Horloge` (jamais dans le domaine, resté déterministe).

Frontières de cette tranche (**moteur métier**, cf. `stories/E04-saisie-scores.md`) :

- L'**autorisation par le poste** (le poste ne saisit que pour sa cible, `SaisieHorsCible`) et la
  résolution des archers via le **départ courant** (ADR-0030/0033/0034) vivent avec l'API et le
  départ de poste — **tranche plomberie (PR2)**. Ici, l'archer visé est déjà connu ; le service
  résout *sa* configuration de saisie et agit sur *sa* série.
- Le **nom** de qui agit (scoreur en validation, rôle habilité en correction) est **fourni** au
  service (résolu par `exiger_scoreur` côté API, PR2) : le service reste pur, sans jeton ni session.
- L'**atomicité acte↔trace** (validation/correction) passe par le port
  `SerieRepository.enregistrer_avec_trace` (série + audit en une transaction, ADR-0035) ; la couture
  réelle est dans l'adapter (PR2).
"""

from __future__ import annotations

from application.erreurs import (
    ArcherIntrouvable,
    BlasonIntrouvable,
    CategorieIntrouvable,
    PhaseQualificationAbsente,
)
from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.phase import Phase, TypePhase
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    Horloge,
    PhaseRepository,
    SerieRepository,
)
from domain.serie import Serie
from domain.tournoi import TournoiId


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
        horloge: Horloge,
    ) -> None:
        self._series = series
        self._phases = phases
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._horloge = horloge

    def saisir_volee(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        saisie_par: str | None = None,
    ) -> Serie:
        """Saisit ou réédite (avant validation) la volée `numero` de l'archer.

        Le pavé (zones admises) se déduit du **blason** de l'archer, le nombre de flèches du
        **barème** de la phase. Persiste sans trace (une saisie ordinaire n'est pas un acte de fin).
        """
        archer = self._charger_archer(tournoi_id, archer_id)
        zones = self._zones_du_blason(archer)
        phase = self._phase_qualification(tournoi_id)
        serie = self._series.par_archer(tournoi_id, archer_id) or Serie.vide(tournoi_id, archer_id)
        serie = serie.saisir_volee(
            numero,
            valeurs,
            zones_admises=zones,
            nb_fleches_par_volee=phase.bareme.nb_fleches_par_volee,
            saisie_par=saisie_par,
        )
        return self._series.enregistrer(serie)

    def valider(self, tournoi_id: TournoiId, archer_id: ArcherId, scoreur: str) -> Serie:
        """Valide la série de l'archer selon le grain de la phase, au nom du `scoreur`.

        Verrouille les volées concernées (fin de série ou lot de N, cf. `Serie.valider`) et laisse
        une **trace** `VALIDATION` (sans avant/après) dans la même transaction que l'écriture.
        """
        self._charger_archer(tournoi_id, archer_id)
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
    ) -> Serie:
        """Corrige une volée **verrouillée** de l'archer, au nom de l'`auteur` (rôle habilité).

        Chemin d'écriture unique sur une volée validée. Laisse une trace `CORRECTION_SCORE` portant
        l'**avant** et l'**après**, dans la même transaction que la réécriture (ADR-0035). Le cumul
        se recalcule mécaniquement.
        """
        archer = self._charger_archer(tournoi_id, archer_id)
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

    def _charger_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Archer:
        """L'archer du tournoi ; `ArcherIntrouvable` s'il est inconnu ou d'un autre tournoi."""
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")
        return archer

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
