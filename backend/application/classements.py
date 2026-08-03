"""Service applicatif Classement (E06US001) — lecture du classement de qualification.

Cas d'usage de **lecture** : charge les archers, leurs **séries** de saisie (E04US002) et les
catégories d'un tournoi via les ports, puis délègue le calcul (cumul, départage FFTA, deux rangs)
à la fonction pure du domaine (`calculer_classement`). Sans écriture, il s'exécute hors de la file
d'écriture (lecture concurrente, mode WAL).

Le classement se calcule **toujours en entier** (rang scratch global + rang par catégorie) ; le
paramètre `categorie_id` ne fait que **filtrer l'affichage** à une catégorie, sans recalculer : un
archer filtré garde donc son vrai rang scratch (sa place réelle dans le tournoi) et son rang de
catégorie. C'est le sens du CA « filtrage/segmentation par catégorie » — voir une catégorie sans
perdre la position d'ensemble.
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.barrage import PorteeBarrage, VerdictBarrage
from domain.categorie import CategorieId
from domain.classement import Classement, calculer_classement
from domain.erreurs import ConfigurationBarrageInvalide
from domain.forfait import Forfait
from domain.phase import Phase, TypePhase
from domain.politiques import (
    RegistrePolitiques,
    Tiebreak,
    TiebreakFftaDefaut,
    assembler_politiques,
    registre_par_defaut,
)
from domain.ports import (
    ArcherRepository,
    BarrageRepository,
    CategorieRepository,
    ForfaitRepository,
    PhaseRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceClassement:
    """Cas d'usage du classement : consulter le classement de qualification d'un tournoi."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        series: SerieRepository,
        categories: CategorieRepository,
        phases: PhaseRepository,
        forfaits: ForfaitRepository,
        barrages: BarrageRepository | None = None,
        registre: RegistrePolitiques | None = None,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._series = series
        self._categories = categories
        self._phases = phases
        self._forfaits = forfaits
        # `barrages` et `registre` sont **facultatifs** (E06US003) : le harnais de simulation
        # (ADR-0054) ne persiste aucun barrage et n'a donc rien à en lire. Absents, le classement
        # retombe sur le défaut d'E06US001 — ex æquo partagés, aucune égalité signalée —, qui est
        # exactement ce que la simulation attend.
        self._barrages = barrages
        self._registre = registre if registre is not None else registre_par_defaut()

    def pour_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None
    ) -> Classement:
        """Renvoie le classement d'un tournoi, éventuellement **filtré** à une catégorie.

        Lève `TournoiIntrouvable` si le tournoi manque. `categorie_id=None` → toutes catégories
        (ordre scratch) ; sinon, seules les lignes de cette catégorie sont conservées, leurs rangs
        (scratch **et** catégorie) restant ceux du classement complet.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        archers = self._archers.par_tournoi(tournoi_id)
        series = self._series.par_tournoi(tournoi_id)
        categories = self._categories.par_tournoi(tournoi_id)
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        classement = calculer_classement(
            archers,
            series,
            categories,
            self._forfaits_qualif(tournoi_id),
            tiebreak=self._tiebreak(phase),
            verdicts=self._verdicts_qualif(tournoi_id),
        )
        if categorie_id is not None:
            classement = Classement(
                lignes=tuple(
                    ligne for ligne in classement.lignes if ligne.categorie_id == categorie_id
                ),
                # Le filtre ne restreint que l'**affichage** : les égalités à départager restent
                # celles du classement entier. Les filtrer sur la catégorie ferait disparaître de
                # l'écran un barrage à organiser dès que l'organisateur cadre sa vue.
                egalites_a_departager=classement.egalites_a_departager,
            )
        return classement

    def _tiebreak(self, phase: Phase | None) -> Tiebreak:
        """La politique de départage de la phase de qualification (ADR-0004, ADR-0066).

        Sans phase ou sans seuil réglé : le départage FFTA **nu** (§8.1), donc l'ex æquo par défaut
        — E06US001 à l'identique. Réglé, le seuil se résout **par le registre**, sur la forme
        `config.policies` d'ADR-0046 : c'est le point d'injection, et le contourner en instanciant
        la stratégie à la main ferait de la politique une décoration.
        """
        if phase is None or phase.barrage_jusqu_au is None:
            return TiebreakFftaDefaut()
        politiques = assembler_politiques(
            {"tiebreak": {"nom": "barrage", "jusqu_au": phase.barrage_jusqu_au}},
            self._registre,
        )
        return politiques.tiebreak if politiques.tiebreak is not None else TiebreakFftaDefaut()

    def _verdicts_qualif(self, tournoi_id: TournoiId) -> list[VerdictBarrage]:
        """Les verdicts des barrages **de qualification** de ce tournoi.

        Les barrages **clos comme ouverts** sont lus : un barrage résolu mais non encore clos a déjà
        un verdict exploitable, et attendre la clôture pour l'appliquer laisserait le classement
        afficher un ex æquo que les archers viennent de départager sous les yeux du public. Un
        barrage non résolu rend un verdict vide, donc sans effet.
        """
        if self._barrages is None:
            return []
        verdicts: list[VerdictBarrage] = []
        for barrage in self._barrages.par_tournoi(tournoi_id):
            if barrage.portee is not PorteeBarrage.QUALIFICATION:
                continue
            try:
                verdicts.append(barrage.verdict())
            except ConfigurationBarrageInvalide:
                # ⚠️ **Le classement ne tombe jamais à cause d'un barrage.** Le verdict se recalcule
                # à chaque lecture : un barrage incohérent en base ferait lever *toutes* les
                # lectures : `GET /classement` est **public et projeté en salle**, et le panneau qui
                # permettrait de réparer meurt avec lui. Le service valide désormais chaque manche
                # **avant** de l'écrire (`_exiger_manche_jouable`), si bien qu'un tel état
                # ne devrait plus naître ; ce filet couvre les lignes antérieures et toute
                # écriture directe en base. Un barrage illisible dégrade donc en **rang partagé** —
                # le défaut d'E06US001, faux mais lisible — plutôt qu'en écran noir.
                continue
        return verdicts

    # DETTE-022 : même résolution que la complétude (deux fois) et la saisie — extraction en US
    # dédiée.
    def _forfaits_qualif(self, tournoi_id: TournoiId) -> list[Forfait]:
        """Les forfaits déclarés **en phase de qualification** (relégation/exclusion, ADR-0050).

        Filtrés par phase : un forfait déclaré **en duels** ne touche pas le classement de qualif
        (l'archer avait bien qualifié). Phase de qualif absente → aucun forfait applicable ici.
        """
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        if phase is None or phase.id is None:
            return []
        return self._forfaits.par_phase(phase.id)
