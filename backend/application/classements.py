"""Service de **classement** — délègue au domaine, s'exécute hors file (lecture concurrente).

⚠️ **Le classement se calcule TOUJOURS en entier** ; `categorie_id` ne fait que **filtrer
l'affichage**, sans recalculer. Un archer filtré garde donc son vrai rang scratch — voir une
catégorie sans perdre la position d'ensemble.
"""

from __future__ import annotations

from collections.abc import Collection

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from application.portee import qualification_du_tournoi
from domain.archer import ArcherId
from domain.barrage import PorteeBarrage, VerdictBarrage
from domain.categorie import CategorieId
from domain.classement import Classement, calculer_classement
from domain.depart import DepartId
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
    DepartRepository,
    ForfaitRepository,
    InscriptionRepository,
    PhaseRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceClassement:
    """Cas d'usage du classement : consulter le classement de qualification **d'un départ**.

    ⚠️ **D'un départ, pas d'un tournoi** (E01US025, ADR-0075). Un départ rejoue le tournoi en
    entier : ses archers ne sont jamais comparés à ceux d'un autre créneau. Un tournoi de 4 départs
    de 100 archers produit donc **4 classements de 100**, et non un de 400 — ce que ce service
    faisait jusqu'au 06/08/2026, en contradiction avec ADR-0017 qui l'avait pourtant décidé.
    """

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        series: SerieRepository,
        categories: CategorieRepository,
        phases: PhaseRepository,
        forfaits: ForfaitRepository,
        departs: DepartRepository,
        inscriptions: InscriptionRepository,
        barrages: BarrageRepository | None = None,
        registre: RegistrePolitiques | None = None,
    ) -> None:
        # `departs` et `inscriptions` sont **obligatoires** (et non facultatifs comme `barrages`) :
        # sans eux, le service ne sait pas *qui* tire dans ce créneau, donc ne peut pas classer.
        # Les rendre optionnels rouvrirait la porte au classement tous-départs-confondus.
        self._departs = departs
        self._inscriptions = inscriptions
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

    def pour_depart(
        self, depart_id: DepartId, categorie_id: CategorieId | None = None
    ) -> Classement:
        """Le classement de la **première** qualification d'un créneau, filtré ou non.

        Lève `DepartIntrouvable`. `categorie_id=None` → toutes catégories ; sinon le filtre garde
        les rangs du classement complet. ⚠️ **Le périmètre se lit sur les inscriptions**, pas sur
        le tournoi : `Archer.tournoi_id` ne sait pas *qui tire quand*, et c'est ce raccourci qui
        produisait le classement fusionné. « La » qualification n'existe plus (ADR-0082) — pour un
        second tour, passer par `pour_phase`.
        """
        return self.pour_phase(depart_id, self._premiere_qualification(depart_id), categorie_id)

    def pour_phase(
        self,
        depart_id: DepartId,
        phase: Phase | None,
        categorie_id: CategorieId | None = None,
        admis: Collection[ArcherId] | None = None,
    ) -> Classement:
        """Le classement **d'une phase de qualification** donnée (E05US025, ADR-0082).

        `admis` restreint la population à ceux que la phase a **prélevés** ; `None` = tous les
        inscrits (cas de la tête). ⚠️ **La population vient de l'appelant** : la résoudre ici
        demanderait de reconstruire les tableaux amont et créerait un cycle avec
        `ServiceSaisieDuels`. ⚠️ **Les séries se lisent par phase**, jamais par tournoi — confondre
        les 3x20 et les 3x15 rendrait un cumul que personne n'a tiré.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        tournoi_id = depart.tournoi_id
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        engages = {i.archer_id for i in self._inscriptions.par_depart(depart_id)}
        if admis is not None:
            engages &= set(admis)
        archers = [a for a in self._archers.par_tournoi(tournoi_id) if a.id in engages]
        # Phase absente ou non persistée : aucune feuille ne peut lui être rattachée (la clé de
        # `Serie` est `(phase, archer)`), donc aucune série à lire. Les archers figurent quand même
        # au classement, à zéro — CA « un archer sans flèche apparaît quand même ».
        series = (
            [s for s in self._series.par_phase(phase.id) if s.archer_id in engages]
            if phase is not None and phase.id is not None
            else []
        )
        categories = self._categories.par_tournoi(tournoi_id)
        classement = calculer_classement(
            archers,
            series,
            categories,
            [f for f in self._forfaits_qualif(tournoi_id) if f.archer_id in engages],
            tiebreak=self._tiebreak(phase),
            verdicts=self._verdicts_qualif(depart_id),
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

    def _premiere_qualification(self, depart_id: DepartId) -> Phase | None:
        """La qualification de **plus petit ordre** de ce créneau, ou `None`.

        Remplace `PhaseRepository.par_depart_et_type(depart_id, QUALIFICATION)`, dont le contrat
        (« la » phase de ce type) n'a plus de sens depuis qu'un créneau peut en porter plusieurs.
        Le tri par `ordre` rend le choix **explicite et stable** ; s'en remettre à l'ordre du
        repository ferait changer le classement affiché d'un rafraîchissement à l'autre.
        """
        qualifications = [
            phase
            for phase in self._phases.par_depart(depart_id)
            if phase.type is TypePhase.QUALIFICATION
        ]
        return min(qualifications, key=lambda phase: phase.ordre) if qualifications else None

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

    def _verdicts_qualif(self, depart_id: DepartId) -> list[VerdictBarrage]:
        """Les verdicts des barrages **de qualification** de ce créneau.

        ⚠️ **`par_depart` et non `par_tournoi`** : une place se dispute dans le classement d'**un**
        départ (ADR-0075), et lire le tournoi entier appliquait au créneau de l'après-midi le
        verdict d'une égalité départagée le matin, les rangs se répétant d'un créneau à l'autre.
        Les barrages **clos comme ouverts** sont lus : un verdict acquis mais non clos est
        exploitable, et l'attendre laisserait le public voir un ex æquo déjà départagé.
        """
        if self._barrages is None:
            return []
        verdicts: list[VerdictBarrage] = []
        for barrage in self._barrages.par_depart(depart_id):
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
    # DETTE-047 : et cette résolution est à la maille **tournoi** alors que le classement est celui
    # d'un créneau. Ce n'est pas corrigeable ici seul : `ServiceForfait` **écrit** par le même
    # chemin, si bien que ne changer que la lecture rendrait les forfaits invisibles au lieu de les
    # rendre justes. Les deux côtés se portent au départ ensemble, dans l'US de résorption.
    def _forfaits_qualif(self, tournoi_id: TournoiId) -> list[Forfait]:
        """Les forfaits déclarés **en phase de qualification** (relégation/exclusion, ADR-0050).

        Filtrés par phase : un forfait déclaré **en duels** ne touche pas le classement de qualif
        (l'archer avait bien qualifié). Phase de qualif absente → aucun forfait applicable ici.
        """
        phase = qualification_du_tournoi(self._phases, tournoi_id)
        if phase is None or phase.id is None:
            return []
        return self._forfaits.par_phase(phase.id)
