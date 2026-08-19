"""Service applicatif **Arrêts programmés** — la salle peut s'arrêter (E05US033, [ADR-0091]).

Trois cas d'usage, et un seul écrit :

- **`evaluer`** — le **déclencheur**. Appelé après chaque validation de score, il regarde où en est
  chaque phase du créneau et met en pause celles dont un arrêt programmé vient d'être atteint.
  Idempotent : rappelé sans que rien n'ait changé, il ne fait rien.
- **`lever`** — le **geste de l'admin**. La salle repart, et un arrêt de portée départ relance
  **toutes** les phases qu'il a coupées d'un seul geste.
- **`en_attente_de_relance`** — la lecture que le pilotage affiche : les arrêts franchis et pas
encore
  levés.

**Pourquoi un service et non un automate.** Le projet ne persiste pas l'avancement : chaque service
de format le **recalcule à la lecture** (ADR-0090 §5), et le lancement d'un tour est un *événement*,
pas un état (ADR-0056). Il n'existe donc aucun endroit où l'on pourrait accrocher « le tour vient de
se terminer ». Ce service **constate** au lieu d'écouter : il compare le tour courant de chaque
phase à ce que les arrêts attendent, et n'écrit que la trace du franchissement.

⚠️ **La couture d'avancement passe par `ServiceSuiviDeroule`, délibérément.** C'est le seul endroit
du projet qui sait répondre « quel tour tourne » pour **tous** les formats : les poules, le suisse
et le Big Shoot Off répondent par le port `LecteurAvancementDePhase`, mais l'élimination directe —
le format le plus courant — n'a pas de lecteur et voit son avancement reconstruit sur place à partir
des braquets. Tenir ici un second registre par type aurait donc, d'une part, laissé le tableau hors
du mécanisme, et d'autre part été la **quatrième** occurrence d'une résolution par type — ce dont la
docstring du port met explicitement en garde.

**Coût de lecture assumé, et tracé** : la couture d'avancement recompose chaque phase qui tourne à
chaque appel, et ce service l'appelle après chaque validation de score. `DETTE-031` est élargie en
conséquence — le marqueur est posé au point d'appel, pas ici.

[ADR-0056]: ../docs/adr/0056-le-lancement-est-un-evenement-pas-un-etat.md
[ADR-0090]: ../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
[ADR-0091]: ../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Protocol

from application.erreurs import ArretIntrouvable
from application.phases import ServicePhases
from domain.arret_programme import (
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    arrets_atteints,
    phases_a_arreter,
)
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule
from domain.phase import Phase, PhaseId, StatutPhase
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    FranchissementArretRepository,
    PhaseRepository,
)
from domain.suivi_deroule import AvancementDePhase

_logger = logging.getLogger(__name__)


class LecteurAvancementDuDepart(Protocol):
    """Port étroit : « quel tour tourne dans chaque phase de ce créneau ? ».

    Réalisé par `ServiceSuiviDeroule`, et **volontairement plus large d'une maille** que
    `LecteurAvancementDePhase` : c'est le créneau entier qu'il faut, en un seul passage. Demander
    phase par phase obligerait ce service à connaître le cas particulier du tableau — dont personne
    ne réalise le port par phase — et rouvrirait la résolution par type que l'en-tête écarte.
    """

    def avancement_par_phase(self, depart_id: DepartId) -> dict[PhaseId, AvancementDePhase]:
        """L'avancement de chaque phase du créneau, par identifiant de phase."""
        ...


def _avancement_connu(avancement: AvancementDePhase) -> bool:
    """Sait-on où en est cette phase ? — le seul discriminant qui vaille (E05US033).

    ⚠️ **Trois rédactions ont été nécessaires**, et les deux premières étaient fausses. Le problème
    est que `tour_courant is None` a **deux** sens opposés :

    - *tout est joué* — la convention d'`AvancementDePhase` (ADR-0090). On sait, et la phase est
      finie : un arrêt de créneau peut l'arrêter tout de suite, elle ne tire plus ;
    - *je ne sais pas* — le repli d'`avancement_bloc` pour une phase sans lecteur et sans braquet,
      qui rend alors `nb_tours=1`. On ne sait pas, donc on ne coupe pas.

    `nb_tours` les sépare : un service qui a **répondu** annonce le nombre de tours qu'il connaît ;
    le repli, lui, retombe sur `1`. D'où la règle : l'avancement est connu si un tour tourne, **ou**
    si la phase annonce plus d'un tour.

    La 1ʳᵉ rédaction lisait tout `None` comme « fini » et **coupait la salle avant la première
    flèche** ; la 2ᵉ discriminait sur l'absence de clé dans le dictionnaire d'avancement, qui ne
    discrimine rien (le suivi rend une entrée par phase du créneau) ; la 3ᵉ excluait tout `None` et
    laissait `EN_COURS` une phase dont tout est joué. Les trois sont documentées ici parce que
    chacune paraissait juste en la lisant.
    """
    return avancement.tour_courant is not None or avancement.nb_tours > 1


class ServiceArretsProgrammes:
    """Cas d'usage : « la salle s'arrête après ce tour, et repart quand je le dis »."""

    def __init__(
        self,
        phases: PhaseRepository,
        deroules: DerouleRepository,
        departs: DepartRepository,
        franchissements: FranchissementArretRepository,
        suivi: LecteurAvancementDuDepart,
        cycle_de_vie: ServicePhases,
    ) -> None:
        self._phases = phases
        self._deroules = deroules
        self._departs = departs
        self._franchissements = franchissements
        self._suivi = suivi
        # ⚠️ **Le cycle de vie n'est pas réimplémenté ici** : `mettre_en_pause` et `reprendre` sont
        # les transitions gardées d'ADR-0045, et ce service les **appelle** (service→service, sur le
        # précédent de `ServicePilotageTour`). Muter le statut à la main dupliquerait l'automate, et
        # un automate en double finit toujours par diverger — c'est la leçon d'ADR-0076 appliquée au
        # comportement plutôt qu'à la donnée.
        self._cycle_de_vie = cycle_de_vie

    # --- Lecture ------------------------------------------------------------------------------

    def en_attente_de_relance(self, depart_id: DepartId) -> tuple[FranchissementArret, ...]:
        """Les arrêts qui **attendent un geste** dans ce créneau : tout ce qui a déjà coupé.

        Les `FRANCHI` — toutes les phases concernées sont arrêtées — **et** les `ARME` qui ont
        **déjà arrêté au moins une phase**.

        ⚠️ **Cette seconde catégorie est un correctif de bloquant de 2ᵉ passe** (axe C1). Ne rendre
        que les `FRANCHI` laissait un trou par lequel l'organisateur perdait la main : un arrêt de
        portée départ met **immédiatement** en pause sa phase déclenchante, mais reste `ARME` tant
        que toutes les phases photographiées n'ont pas changé de tour. Or une qualification **non
        découpée** compte un seul tour : son tour ne change qu'à la validation de la dernière volée
        du plateau entier. L'arrêt restait donc `ARME` pendant toute la qualification — donc
        **absent de la liste de relance** — pendant qu'une phase était déjà éteinte, sans un bouton
        pour la rallumer. Le CA dit « la qualification finit ses volées en cours » ;
        l'implémentation le lisait « toutes ses volées ».

        Rendre l'arrêt relançable dès qu'il a coupé quelque chose est le geste juste :
        l'organisateur récupère la main sur ce qui est arrêté, et `lever` ne relance que les phases
        qu'il a effectivement coupées — celles qui finissent encore leur tour ne sont pas dans
        `phases_arretees`, donc ne sont pas touchées.

        Reste dehors : un `ARME` qui n'a **rien** arrêté (la coupe est décidée, pas encore faite —
        annoncer une relance ferait cliquer sur un bouton sans effet) et les `LEVE`, consommés.
        """
        return tuple(
            franchissement
            for franchissement in self._franchissements.par_depart(depart_id)
            if franchissement.etat is EtatFranchissement.FRANCHI
            or (franchissement.etat is EtatFranchissement.ARME and franchissement.phases_arretees)
        )

    # --- Le déclencheur -----------------------------------------------------------------------

    def evaluer(self, depart_id: DepartId) -> tuple[PhaseId, ...]:
        """Applique les arrêts devenus dus. Renvoie les phases **mises en pause par cet appel**.

        Deux passes, dans cet ordre, et l'ordre compte :

        1. les arrêts déjà **armés** — un arrêt de portée départ attend que chaque phase finisse son
           tour. Passer en premier évite qu'un arrêt neuf ne prenne en photo un créneau où une phase
           aurait dû être arrêtée depuis la passe précédente ;
        2. les arrêts **atteints à l'instant**, phase par phase.

        Idempotent : sans changement d'avancement, le second appel ne trouve plus rien à faire, la
        mémoire étant portée par les franchissements persistés.
        """
        phases = {
            phase.id: phase for phase in self._phases.par_depart(depart_id) if phase.id is not None
        }
        if not phases:
            return ()
        # ⚠️ **Sortir AVANT la lecture lourde quand il n'y a rien à faire** (correctif de revue, axe
        # adversarial). Sans cette garde, un tournoi **sans aucune pause programmée** payait la
        # recomposition intégrale du créneau après chaque validation de score — ce qui contredisait
        # à la lettre la promesse de l'US (« une phase sans arrêt programmé se comporte exactement
        # comme avant »). Le comportement fonctionnel était bien identique ; le **coût** ne l'était
        # pas, et le coût est ici le sujet. Aggravant, et c'est ce qui rend la garde non négociable
        # : `evaluer` est appelé **depuis une commande de la file d'écriture**, donc cette lecture
        # occupait le **writer unique** qui sérialise toutes les écritures de l'application (règle 7
        # : « pas de logique métier longue »). Avec ~30 tablettes, chaque validation retardait
        # toutes les autres. Deux requêtes légères (le déroulé du tournoi, les franchissements du
        # créneau) contre une recomposition complète : le cas « aucun arrêt nulle part » est le cas
        # normal du dépôt.
        etapes = self._etapes_du_depart(depart_id)
        franchissements = self._franchissements.par_depart(depart_id)
        aucun_arret = not any(etape.arrets for etape in etapes.values())
        aucun_arme = not any(f.etat is EtatFranchissement.ARME for f in franchissements)
        if aucun_arret and aucun_arme:
            return ()
        # DETTE-031 : cette lecture recompose **intégralement** chaque phase qui tourne, chaîne
        # de sources amont comprise. Jusqu'ici seuls le pilotage et l'écran de salle la payaient,
        # toutes les 10 s ; ce service la paie après **chaque validation de score**. Le facteur
        # d'appel a donc changé de nature. L'ordre de grandeur reste tenable — une ou deux phases
        # actives par créneau, ~30 tablettes, SQLite en local — et la dette est **élargie** plutôt
        # que contournée par une mémoïsation locale, qui serait un remède structurel posé au
        # mauvais endroit (§ Dette). Cf. docs/dette.md.
        #
        # ⚠️ **L'`AvancementDePhase` entier, pas seulement `tour_courant`** (correctif de revue,
        # relevé par les quatre axes). La première rédaction ne gardait que le tour courant, et
        # perdait donc `nb_tours` — or c'est lui qui distingue « la phase est finie » de « je ne
        # sais pas où elle en est ». La distinction se fait dans `_avancement_connu`, et nulle
        # part ailleurs.
        #
        # ⚠️ **Ne pas croire discriminer sur la présence de la clé.** Une première rédaction le
        # croyait ; c'est faux, `avancement_par_phase` rend une entrée pour **chaque** phase du
        # créneau. L'axe adversarial l'a démontré contre l'arbre de travail, et le commentaire
        # rassurant d'alors est ce qui avait masqué le défaut.
        avancements = self._suivi.avancement_par_phase(depart_id)
        arretees: list[PhaseId] = []
        arretees.extend(self._resoudre_les_arrets_armes(depart_id, phases, avancements))
        arretees.extend(self._declencher_les_arrets_atteints(depart_id, phases, avancements))
        # ⚠️ **Une seconde résolution, et une boucle bornée** (correctif de revue, axe C1 §5 puis
        # test de non-régression). Mettre une phase en pause peut **débloquer** un arrêt armé qui
        # l'attendait : deux arrêts de portée départ dus au même appel s'attendaient mutuellement,
        # et le premier restait `ARME` — donc absent de la liste de relance, donc la salle arrêtée
        # **sans aucun bouton pour la repartir**. Une seule passe ne suffit pas, parce que l'ordre
        # d'itération décide qui voit quoi. La boucle est **bornée par le nombre de phases** :
        # chaque tour supplémentaire met au moins une phase en pause, et il y en a un nombre fini.
        # Une borne plutôt qu'un `while True` — cette fonction tourne sur le thread du writer
        # unique.
        for _ in range(len(phases)):
            de_plus = self._resoudre_les_arrets_armes(depart_id, phases, avancements)
            if not de_plus:
                break
            arretees.extend(de_plus)
        return tuple(arretees)

    def _resoudre_les_arrets_armes(
        self,
        depart_id: DepartId,
        phases: dict[PhaseId, Phase],
        avancements: dict[PhaseId, AvancementDePhase],
    ) -> list[PhaseId]:
        """Arrête les phases d'un arrêt armé qui viennent de finir leur tour, et clôt l'arrêt.

        Une phase déjà en pause n'est pas re-mise en pause mais **compte** comme arrêtée : c'est ce
        qui permet à l'arrêt de passer à `FRANCHI` au tour suivant sans attendre un changement qui
        n'aura plus lieu.
        """
        arretees: list[PhaseId] = []
        for franchissement in self._franchissements.par_depart(depart_id):
            if franchissement.etat is not EtatFranchissement.ARME:
                continue
            attendues = dict(franchissement.tours_a_finir)
            # ⚠️ **Seules les phases encore `EN_COURS` fournissent un tour à comparer** (correctif
            # de revue, axe C1 §5). Une phase mise en pause **après** l'armement — par un autre
            # arrêt, ou à la main — voit son tour se figer : `phases_a_arreter` ne l'aurait jamais
            # déclarée finie, l'arrêt serait resté `ARME` pour toujours, donc **absent** de
            # `en_attente_de_relance` et non relançable d'un geste. Deux arrêts de portée départ
            # armés en même temps s'attendaient mutuellement sans fin. L'exclure de `tours_courants`
            # la fait tomber dans la branche « phase disparue » de `phases_a_arreter`, qui la compte
            # finie — ce qui est le sens voulu : elle est arrêtée.
            tours = {
                phase_id: avancements[phase_id].tour_courant
                for phase_id, phase in phases.items()
                if phase.statut is StatutPhase.EN_COURS and phase_id in avancements
            }
            finies = phases_a_arreter(attendues, tours)
            deja_en_pause = list(franchissement.phases_arretees)
            for phase_id in finies:
                if phase_id in deja_en_pause:
                    continue
                if self._mettre_en_pause(depart_id, phase_id, phases):
                    arretees.append(phase_id)
                deja_en_pause.append(phase_id)
            if len(finies) == len(attendues):
                self._franchissements.enregistrer(franchissement.franchir(deja_en_pause))
            elif deja_en_pause != list(franchissement.phases_arretees):
                # Encore armé, mais on retient déjà ce qui est arrêté : sans cette écriture
                # intermédiaire, une phase arrêtée puis reprise à la main sortirait de la liste de
                # relance, et le geste d'admin ne la rendrait jamais.
                self._franchissements.enregistrer(
                    FranchissementArret(
                        phase_id=franchissement.phase_id,
                        apres_tour=franchissement.apres_tour,
                        etat=EtatFranchissement.ARME,
                        tours_a_finir=franchissement.tours_a_finir,
                        phases_arretees=tuple(deja_en_pause),
                        id=franchissement.id,
                    )
                )
        return arretees

    def _declencher_les_arrets_atteints(
        self,
        depart_id: DepartId,
        phases: dict[PhaseId, Phase],
        avancements: dict[PhaseId, AvancementDePhase],
    ) -> list[PhaseId]:
        """Repère les arrêts que l'avancement vient d'atteindre, et les applique."""
        etapes = self._etapes_du_depart(depart_id)
        deja = self._traites_par_phase(depart_id)
        arretees: list[PhaseId] = []
        for phase_id, phase in phases.items():
            if phase.statut is not StatutPhase.EN_COURS:
                continue
            etape = etapes.get(phase.ordre)
            if etape is None or not etape.arrets:
                continue
            tour_acheve = self._tour_acheve(avancements.get(phase_id), etape)
            if tour_acheve is None:
                continue
            dus = arrets_atteints(etape.arrets, tour_acheve, deja.get(phase_id, ()))
            if not dus:
                continue
            arretees.extend(self._appliquer(depart_id, phase_id, phases, avancements, dus))
        return arretees

    def _appliquer(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        phases: dict[PhaseId, Phase],
        avancements: dict[PhaseId, AvancementDePhase],
        dus: tuple[ArretProgramme, ...],
    ) -> list[PhaseId]:
        """Applique **un seul** arrêt — le plus ancien dû — et consomme les autres.

        ⚠️ **Une phase ne peut pas être mise en pause deux fois.** Quand plusieurs arrêts sont dus
        au même instant (l'avancement a sauté plusieurs tours entre deux évaluations : correction en
        cascade, lot de validations, reprise après incident), on crédite le **plus ancien** — c'est
        la pause que l'organisateur voulait, appliquée en retard — et l'on **consomme** les
        suivants.

        Les laisser en attente serait le piège : ils se déclencheraient l'un après l'autre à chaque
        reprise, et l'organisateur devrait relancer trois fois pour une seule coupe. Ils sont donc
        marqués `LEVE` sans avoir rien arrêté, et **journalisés** : une pause manquée est un fait
        d'exploitation, pas un détail. La rendre visible à l'écran est le périmètre d'`E05US034`.
        """
        applique, *manques = dus
        arretees: list[PhaseId] = []
        if applique.portee is PorteeArret.PHASE:
            # ⚠️ **La trace AVANT la pause, et l'ordre compte** (correctif de 2ᵉ passe, axe C2).
            # Les deux écritures sont dans des transactions distinctes : si le franchissement
            # échouait après la mise en pause (SQLite occupé, conflit d'unicité), l'exception était
            # avalée par le signalement et la phase restait `EN_PAUSE` **sans franchissement** —
            # donc absente de la liste de relance, donc **aucun bouton** pour la rallumer. Le mode
            # de panne que tout cet ADR est écrit pour empêcher, atteint par la porte de l'`except`.
            #
            # Dans cet ordre, la panne symétrique est bénigne : une trace écrite sans pause laisse
            # un bouton qui ne trouve aucune phase `EN_PAUSE` à rendre (`lever` les ignore déjà),
            # et le déclencheur suivant remettra la phase en pause, l'arrêt étant tracé.
            self._franchissements.ajouter(
                FranchissementArret(
                    phase_id=phase_id,
                    apres_tour=applique.apres_tour,
                    etat=EtatFranchissement.FRANCHI,
                    phases_arretees=(phase_id,),
                )
            )
            if self._mettre_en_pause(depart_id, phase_id, phases):
                arretees.append(phase_id)
        else:
            arretees.extend(
                self._armer_sur_le_depart(depart_id, phase_id, phases, avancements, applique)
            )
        for manque in manques:
            _logger.warning(
                "Arrêt programmé après le tour %s de la phase %s manqué : l'avancement l'a "
                "dépassé avant évaluation, il est consommé sans mise en pause.",
                manque.apres_tour,
                phase_id,
            )
            self._franchissements.ajouter(
                FranchissementArret(
                    phase_id=phase_id,
                    apres_tour=manque.apres_tour,
                    etat=EtatFranchissement.LEVE,
                )
            )
        return arretees

    def _armer_sur_le_depart(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        phases: dict[PhaseId, Phase],
        avancements: dict[PhaseId, AvancementDePhase],
        arret: ArretProgramme,
    ) -> list[PhaseId]:
        """Arme un arrêt de portée départ : la phase déclenchante s'arrête, les autres finissent.

        La photo des tours à finir ne retient que les phases **en cours**, et les deux exclusions
        ont chacune leur raison :

        - une phase **à venir** n'a rien à interrompre, et la marquer gèlerait l'avenir du créneau —
          l'organisateur qui démarre une phase pendant une pause fait un geste explicite qu'on n'a
          pas à contredire ;
        - une phase **déjà en pause** — suspendue à la main pour une autre raison — est déjà
        arrêtée.
          ⚠️ **L'inclure produisait un interblocage**, trouvé par
          `test_relancer_ne_touche_pas_une_phase_suspendue_a_la_main` : son tour courant ne bouge
          plus (rien ne se joue), donc `phases_a_arreter` ne la déclare jamais finie, donc l'arrêt
          reste `ARME` **pour toujours** — et un arrêt armé n'est pas relançable. L'organisateur
          perdait la main sur tout le créneau à cause d'une phase qu'il avait suspendue lui-même. La
          première rédaction filtrait sur `STATUTS_DEMARRES` (`EN_COURS` **ou** `EN_PAUSE`), qui est
          le bon ensemble pour *lire* un avancement et le mauvais pour *décider d'arrêter*.

        La phase déclenchante est notée avec `None`, c'est-à-dire « rien à finir » : son tour vient
        précisément de s'achever. C'est ce qui la fait passer en pause dès la résolution ci-dessous,
        sans cas particulier.
        """
        a_finir: dict[PhaseId, int | None] = {}
        for autre_id, autre in phases.items():
            if autre.statut is not StatutPhase.EN_COURS:
                continue
            if autre_id == phase_id:
                a_finir[autre_id] = None
                continue
            # ⚠️ **Seule une phase dont on LIT le tour entre dans la photo** (correctif de revue,
            # quatre axes — puis **second** correctif, l'axe adversarial ayant démontré que le
            # premier ne fermait rien). Le défaut : `phases_a_arreter` lit un `tour_a_finir` à
            # `None` comme « cette phase n'avait plus rien en cours, elle s'arrête tout de suite ».
            # La photo enregistrait donc `None` pour une phase dont le tour est simplement
            # **inconnu**, et un arrêt de créneau la coupait **en plein tir** — l'exact contraire de
            # l'arbitrage du commanditaire du 18/08/2026, et du scénario que la fiche de recette
            # désigne comme le plus important. ⚠️ **Le premier correctif discriminait sur l'absence
            # de clé dans `avancements`, et ne discriminait rien** :
            # `ServiceSuiviDeroule.avancement_par_phase` rend une entrée pour **chaque** phase du
            # créneau (un bloc par étape projetée), donc la clé est toujours là. Le commentaire
            # rassurait, le code ne changeait pas. C'est le seul signal qui marche : `tour_courant
            # is not None`, c'est-à-dire « un tour tourne, on peut le laisser finir ». Conséquence
            # assumée : un arrêt de portée départ ne coupe que les phases dont on sait lire le tour.
            # C'est le seul comportement honnête — on ne peut pas « laisser finir son tour » une
            # phase dont on ignore le tour. Les types sans lecteur (barrage, placement, colline) ne
            # comptent de toute façon aucun tour jouable aujourd'hui, et l'atelier refuse désormais
            # d'y poser un arrêt.
            avancement = avancements.get(autre_id)
            if avancement is None or not _avancement_connu(avancement):
                continue
            a_finir[autre_id] = avancement.tour_courant
        # L'écriture compte, pas la valeur rendue : la résolution ci-dessous **relit** les
        # franchissements du créneau, ce qui garantit qu'un arrêt neuf et un arrêt déjà armé suivent
        # exactement le même chemin. Garder la valeur ouvrirait deux traitements à maintenir.
        self._franchissements.ajouter(
            FranchissementArret(
                phase_id=phase_id,
                apres_tour=arret.apres_tour,
                etat=EtatFranchissement.ARME,
                tours_a_finir=tuple(a_finir.items()),
            )
        )
        # Résolution immédiate : la phase déclenchante, et toute phase qui n'avait déjà plus rien en
        # cours, s'arrêtent dans le même appel. Réutiliser la passe 1 plutôt que de dupliquer sa
        # logique garantit qu'un arrêt armé et un arrêt neuf se comportent exactement pareil.
        return self._resoudre_les_arrets_armes(depart_id, phases, avancements)

    # --- Le geste de l'admin ------------------------------------------------------------------

    def lever(self, depart_id: DepartId, franchissement_id: int) -> tuple[PhaseId, ...]:
        """Relance la salle : toutes les phases coupées par cet arrêt repartent, d'un seul geste.

        `ArretIntrouvable` (→ 404) si l'identifiant est inconnu, s'il appartient à un autre créneau,
        s'il est encore `ARME` (la coupe n'est pas faite, il n'y a rien à relancer) ou s'il a déjà
        été levé — un double-clic ne doit pas relancer une seconde fois, car entre les deux clics
        l'organisateur peut avoir suspendu une phase à la main.

        Ne relance que les phases **effectivement en pause** : une phase clôturée entre-temps ne
        redémarre pas, et `reprendre` la refuserait de toute façon (ADR-0045).
        """
        franchissement = next(
            (
                item
                for item in self.en_attente_de_relance(depart_id)
                if item.id == franchissement_id
            ),
            None,
        )
        if franchissement is None:
            raise ArretIntrouvable(
                f"Aucun arrêt à relancer sous l'identifiant {franchissement_id} dans ce créneau."
            )
        relancees: list[PhaseId] = []
        for phase_id in franchissement.phases_arretees:
            phase = self._phases.par_id(phase_id)
            if phase is None or phase.statut is not StatutPhase.EN_PAUSE:
                continue
            self._cycle_de_vie.reprendre(depart_id, phase_id)
            relancees.append(phase_id)
        self._franchissements.enregistrer(franchissement.lever())
        return tuple(relancees)

    # --- Rouages ------------------------------------------------------------------------------

    def _mettre_en_pause(
        self, depart_id: DepartId, phase_id: PhaseId, phases: dict[PhaseId, Phase]
    ) -> bool:
        """Met la phase en pause si elle est en cours. Renvoie `True` si le statut a changé.

        Silencieux sur une phase absente, déjà en pause, à venir ou terminée : le déclencheur est
        rejoué en permanence et sur un créneau qui bouge, donc il **constate** au lieu d'exiger.
        Lever `TransitionStatutInvalide` ici ferait échouer la validation de score qui l'a appelé —
        un archer verrait sa volée refusée parce qu'une phase voisine a été clôturée entre-temps.

        ⚠️ **Le statut est RELU au dépôt, pas lu dans le cliché** (correctif de revue, axes A et C1
        — bloquant). `evaluer` prend son cliché des phases une seule fois, mais la passe 1 **change
        des statuts en base** avant que la passe 2 ne les relise : une phase mise en pause par un
        arrêt de départ y apparaissait encore `EN_COURS`, et si elle portait son propre arrêt dû au
        même tour, `ServicePhases.mettre_en_pause` levait `TransitionStatutInvalide` (`EN_PAUSE →
        EN_PAUSE`).

        Ce que ça coûtait est pire que l'exception : elle sortait d'`evaluer`, était **avalée** par
        le `except Exception` de `_signaler_validation`, et **abandonnait la boucle** — les arrêts
        des phases suivantes n'étaient ni appliqués ni tracés, donc l'arrêt sans franchissement se
        redéclenchait à la relance. C'est-à-dire précisément le « l'organisateur perd la main » que
        tout cet ADR est construit pour empêcher. La configuration n'était pas exotique : le CA
        autorise « un arrêt à chaque tour ».

        Le cliché est **rafraîchi** au passage, pour que le filtre de la passe 2 et la photo d'un
        arrêt de départ voient l'état réel — relire ne suffit pas si l'appelant continue de décider
        sur du périmé.
        """
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.id is None or phase.statut is not StatutPhase.EN_COURS:
            return False
        self._cycle_de_vie.mettre_en_pause(depart_id, phase.id)
        if phase_id in phases:
            phases[phase_id] = replace(phases[phase_id], statut=StatutPhase.EN_PAUSE)
        return True

    def _etapes_du_depart(self, depart_id: DepartId) -> dict[int, EtapeDeroule]:
        """Le déroulé du tournoi de ce créneau, indexé par rang (ADR-0076)."""
        depart = self._departs.par_id(depart_id)
        if depart is None:
            return {}
        return {etape.ordre: etape for etape in self._deroules.par_tournoi(depart.tournoi_id)}

    def _traites_par_phase(self, depart_id: DepartId) -> dict[PhaseId, tuple[int, ...]]:
        """Pour chaque phase, les `apres_tour` déjà franchis — **quel qu'en soit l'état**.

        `ARME`, `FRANCHI` et `LEVE` comptent tous les trois. C'est la mémoire qui empêche un arrêt
        levé de se redéclencher, et donc la salle de se rebloquer aussitôt relancée.
        """
        traites: dict[PhaseId, list[int]] = {}
        for franchissement in self._franchissements.par_depart(depart_id):
            traites.setdefault(franchissement.phase_id, []).append(franchissement.apres_tour)
        return {phase_id: tuple(tours) for phase_id, tours in traites.items()}

    @staticmethod
    def _tour_acheve(avancement: AvancementDePhase | None, etape: EtapeDeroule) -> int | None:
        """Quel tour vient de s'achever pour cette phase. `None` si aucun, ou si on ne sait pas.

        ⚠️ **C'est ici que se jouait le bloquant central de l'US**, relevé par les quatre axes de
        revue. La première rédaction lisait `tour_courant is None` comme « tout est joué, donc le
        dernier tour est achevé » et rendait `max(apres_tour)`. Or `None` a **au moins cinq**
        provenances, dont une seule signifie « fini » :

        1. *tout est joué* — la convention d'`AvancementDePhase` (ADR-0090). La seule qui autorise à
           couper ;
        2. *aucun lecteur branché pour ce type* — `ServiceSuiviDeroule._avancement_lu` le rend sans
           rien tenter, et sa docstring nomme les cas : qualification, échauffement, barrage,
           placement, colline ;
        3. *le service du format a refusé* — `PhasePasReglee`, `KeyError` : journalisés puis avalés,
           donc indistinguables d'un succès ;
        4. *rien n'est encore composé* — un suisse dont l'amont n'a classé personne
           (`rondes_maximales == 0`, cas « normal et durable » selon sa propre docstring), des
           poules dont les rencontres ne sont pas montées ;
        5. *phase sans braquet* — `avancement_bloc` retombe sur `nb_tours=1, tour_courant=None`, ce
           que sa docstring appelle « dégradation lisible », c'est-à-dire **on ne sait pas**.

        Les cas 2 à 5 faisaient donc **couper la salle au premier score validé du créneau**, avant
        que personne ait tiré son tour. Deux signaux distinguent désormais les situations :

        - **avancement absent** (`None` ici) — la phase n'était pas dans `avancement_par_phase`,
        donc
          son avancement est *inconnu*. On ne coupe pas. C'est le repli sûr : une US qui n'arrête
          rien est inerte, une US qui arrête au mauvais moment casse une compétition ;
        - **`nb_tours <= 1` avec `tour_courant is None`** — c'est la signature exacte du repli
          d'`avancement_bloc` (cas 5) et de tout format à un seul tour dont on n'a rien lu. On ne
          coupe pas non plus : un arrêt sur une phase d'un seul tour est de toute façon refusé à la
          composition, donc il n'y a rien à y déclencher.

        Le `min(nb_tours, …)` de la branche « tout est joué » évite de créditer un arrêt posé
        au-delà du dernier tour **réellement joué** : un suisse réglé à 9 rondes qui n'en apparie
        que 5 ne doit pas voir se déclencher, à la fin, la pause qu'on avait prévue « après le tour
        7 » — elle mettrait en pause une phase dont tout est tiré, et il faudrait la relancer pour
        pouvoir la clôturer.

        Au tour 1 en cours, aucun tour n'est achevé : la phase vient de démarrer.
        """
        if avancement is None or not _avancement_connu(avancement):
            return None
        if avancement.tour_courant is None:
            return min(avancement.nb_tours, max(arret.apres_tour for arret in etape.arrets))
        if avancement.tour_courant <= 1:
            return None
        return avancement.tour_courant - 1
