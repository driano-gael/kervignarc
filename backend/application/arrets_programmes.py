"""Service **Arrêts programmés** — la salle peut s'arrêter (ADR-0091, ADR-0092). Quatre gestes,
un seul écrit ; `evaluer` est **idempotent**.

⚠️ **Passer par `ServiceSuiviDeroule` pour l'avancement, jamais par un registre local** : c'est le
seul endroit qui sache « quel tour tourne » pour **tous** les formats — l'élimination directe n'a
pas de lecteur et voit le sien reconstruit depuis les braquets. Un second registre par type
laisserait le tableau hors du mécanisme. Coût de lecture assumé : `DETTE-031`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol

from application.erreurs import ArretIntrouvable
from application.phases import ServicePhases
from domain.arret_programme import (
    ArretDeCirconstance,
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    arrets_applicables,
    arrets_atteints,
    phases_a_arreter,
    tour_d_un_arret_relatif,
    verifier_arrets,
    verifier_type_arretable,
)
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule
from domain.phase import Phase, PhaseId, StatutPhase
from domain.ports import (
    ArretDeCirconstanceRepository,
    DepartRepository,
    DerouleRepository,
    FranchissementArretRepository,
    Horloge,
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

    ⚠️ `tour_courant is None` a **deux sens opposés** : *tout est joué* (convention
    d'`AvancementDePhase`, ADR-0090) et *je ne sais pas* (repli d'`avancement_bloc`, qui rend alors
    `nb_tours=1`). `nb_tours` les sépare — un service qui a **répondu** annonce le nombre de tours
    qu'il connaît. D'où la règle : l'avancement est connu si un tour tourne, **ou** si la phase
    annonce plus d'un tour. Trois rédactions ont été nécessaires, chacune paraissant juste.
    """

    # `# DETTE-074` — une phase en tableau à sources multiples ne projette aucun braquet, retombe
    # sur `(nb_tours=1, tour_courant=None)` et est donc déclarée *inconnue* : son arrêt ne se
    # déclenche jamais. Repli sûr, mais silencieux — cf. `docs/dette.md`.
    return avancement.tour_courant is not None or avancement.nb_tours > 1


def _par_phase(
    arrets: Sequence[ArretDeCirconstance],
) -> dict[PhaseId, tuple[ArretDeCirconstance, ...]]:
    """Indexe par phase des arrêts de circonstance **déjà lus**.

    Pure et sans dépôt, délibérément : la lecture appartient à `evaluer`, qui en a besoin de toute
    façon pour sa garde de chemin court. La version antérieure était une méthode qui relisait le
    dépôt, et sa docstring promettait « une seule lecture » — vrai d'elle, faux du parcours, qui en
    faisait deux par validation de score sur le thread du writer unique (correctif de revue).
    """
    par_phase: dict[PhaseId, list[ArretDeCirconstance]] = {}
    for arret in arrets:
        par_phase.setdefault(arret.phase_id, []).append(arret)
    return {phase_id: tuple(liste) for phase_id, liste in par_phase.items()}


class ServiceArretsProgrammes:
    """Cas d'usage : « la salle s'arrête après ce tour, et repart quand je le dis »."""

    def __init__(
        self,
        phases: PhaseRepository,
        deroules: DerouleRepository,
        departs: DepartRepository,
        franchissements: FranchissementArretRepository,
        arrets_de_circonstance: ArretDeCirconstanceRepository,
        suivi: LecteurAvancementDuDepart,
        cycle_de_vie: ServicePhases,
        horloge: Horloge,
    ) -> None:
        self._phases = phases
        self._deroules = deroules
        self._departs = departs
        self._franchissements = franchissements
        self._arrets_de_circonstance = arrets_de_circonstance
        self._suivi = suivi
        # L'heure passe par un port (règle 2) : un `datetime.now()` ici rendrait non déterministe
        # tout test qui lit `arrete_depuis` (règle 9). Le service ne s'en sert qu'à un endroit —
        # `_horodate` —, et jamais pour décider : l'instant est une **donnée d'affichage**, aucune
        # règle du mécanisme n'en dépend.
        self._horloge = horloge
        # ⚠️ **Le cycle de vie n'est pas réimplémenté ici** : `mettre_en_pause` et `reprendre` sont
        # les transitions gardées d'ADR-0045, et ce service les **appelle** (service→service, sur le
        # précédent de `ServicePilotageTour`). Muter le statut à la main dupliquerait l'automate, et
        # un automate en double finit toujours par diverger — c'est la leçon d'ADR-0076 appliquée au
        # comportement plutôt qu'à la donnée.
        self._cycle_de_vie = cycle_de_vie

    # --- Lecture ------------------------------------------------------------------------------

    def en_attente_de_relance(self, depart_id: DepartId) -> tuple[FranchissementArret, ...]:
        """Les arrêts qui **attendent un geste** dans ce créneau : tout ce qui a déjà coupé.

        Les `FRANCHI`, **et** les `ARME` qui ont déjà arrêté au moins une phase — sans quoi la
        salle reste éteinte sans bouton. Dehors : un `ARME` qui n'a rien arrêté, les `LEVE`, et
        ceux dont aucune phase arrêtée n'est encore en pause. ⚠️ `phases_arretees` est **projeté**
        sur ce qui est encore éteint (la trace persistée n'est jamais élaguée), donc `lever` doit
        **relire** son franchissement au dépôt sous peine de repersister une trace amputée.
        """
        statuts = {
            phase.id: phase.statut
            for phase in self._phases.par_depart(depart_id)
            if phase.id is not None
        }
        en_attente: list[FranchissementArret] = []
        for franchissement in self._franchissements.par_depart(depart_id):
            if franchissement.etat is EtatFranchissement.LEVE:
                continue
            if (
                franchissement.etat is EtatFranchissement.ARME
                and not franchissement.phases_arretees
            ):
                continue
            eteintes = tuple(
                phase_id
                for phase_id in franchissement.phases_arretees
                if statuts.get(phase_id) is StatutPhase.EN_PAUSE
            )
            if not eteintes:
                continue
            en_attente.append(replace(franchissement, phases_arretees=eteintes))
        return tuple(en_attente)

    # --- Le geste du jour J -------------------------------------------------------------------

    def poser_arret_relatif(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        dans_x_tours: int,
        portee: PorteeArret = PorteeArret.PHASE,
    ) -> ArretDeCirconstance:
        """« Bloque-moi dans x tours » — l'arrêt posé **pendant** que la salle tire (E05US034).

        Le geste appartient au **créneau** et à lui seul (ADR-0092) : l'écrire dans
        l'`EtapeDeroule` propagerait une décision locale à tous les créneaux (ADR-0076 §4 contre
        §5). Quatre refus : hors créneau, type sans tours, tour illisible, collision ou inertie. ⚠️
        La **collision** se juge sur l'**union** des deux natures, l'**inertie** sur le **seul**
        arrêt demandé — sinon un arrêt d'atelier inerte faisait échouer toute pose du jour J.
        """
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.depart_id != depart_id:
            raise ArretIntrouvable(
                f"Aucune phase {phase_id} dans ce créneau : impossible d'y poser une pause."
            )
        verifier_type_arretable(phase.type)
        # DETTE-031 : la lecture lourde, ici **sur le thread du writer unique** (la commande passe
        # par la file d'écriture). Le coût est accepté : c'est un geste humain, quelques fois par
        # jour, et lire hors de la file ouvrirait un TOCTOU sur le tour courant — « dans 1 tour »
        # se compterait depuis un tour déjà terminé. Le marqueur est posé au **point d'appel**,
        # convention du module (ajouté en revue : la ligne du registre ne citait que le
        # déclencheur). Cf. docs/dette.md.
        avancement = self._suivi.avancement_par_phase(depart_id).get(phase_id)
        apres_tour = tour_d_un_arret_relatif(
            avancement.tour_courant if avancement is not None else None, dans_x_tours
        )
        etape = self._etapes_du_depart(depart_id).get(phase.ordre)
        voulu = ArretProgramme(apres_tour=apres_tour, portee=portee)
        verifier_arrets(
            (
                *(etape.arrets if etape is not None else ()),
                *(arret.definition() for arret in self._circonstance_de(depart_id, phase_id)),
                voulu,
            )
        )
        verifier_arrets((voulu,), nb_tours=avancement.nb_tours if avancement is not None else None)
        return self._arrets_de_circonstance.ajouter(
            ArretDeCirconstance(
                depart_id=depart_id,
                phase_id=phase_id,
                apres_tour=apres_tour,
                portee=portee,
            )
        )

    # --- Le déclencheur -----------------------------------------------------------------------

    def evaluer(self, depart_id: DepartId) -> tuple[PhaseId, ...]:
        """Applique les arrêts devenus dus. Renvoie les phases **mises en pause par cet appel**.

        Deux passes, et l'ordre compte : les arrêts déjà **armés** d'abord (un arrêt de portée
        départ attend que chaque phase finisse son tour), puis ceux **atteints à l'instant**. Sinon
        un arrêt neuf photographierait un créneau où une phase aurait dû être arrêtée avant.

        Idempotent : la mémoire est portée par les franchissements persistés.
        """
        phases = {
            phase.id: phase for phase in self._phases.par_depart(depart_id) if phase.id is not None
        }
        if not phases:
            return ()
        # ⚠️ **Sortir AVANT la lecture lourde quand il n'y a rien à faire.** Sans cette garde, un
        # tournoi **sans aucune pause programmée** payait la recomposition intégrale du créneau
        # après chaque validation de score — et `evaluer` est appelé **depuis une commande de la
        # file d'écriture**, donc cette lecture occupait le writer unique (règle 7). Avec ~30
        # tablettes, chaque validation retardait toutes les autres.
        #
        # Le prix de la garde, compté honnêtement : le chemin court fait **quatre** lectures (les
        # phases, le créneau, le déroulé, les franchissements), pas deux.
        etapes = self._etapes_du_depart(depart_id)
        franchissements = self._franchissements.par_depart(depart_id)
        # ⚠️ **La garde compte les deux natures d'arrêt** (E05US034). Ne regarder que celles de
        # l'étape rendrait tout arrêt posé le jour J **inerte** : le chemin court sortirait avant
        # de lire l'avancement. Mode de panne vicieux : la pose répond 200, l'écran affiche
        # l'arrêt, et rien ne coupe. Cinquième lecture, le rapport reste celui d'au-dessus.
        #
        # ⚠️ **Lue une fois, puis passée en aval** : la relire dans `_circonstance_par_phase`
        # faisait deux `SELECT` identiques par validation, sur le thread du writer unique.
        circonstance = self._arrets_de_circonstance.par_depart(depart_id)
        aucun_arret = not any(etape.arrets for etape in etapes.values()) and not circonstance
        aucun_arme = not any(f.etat is EtatFranchissement.ARME for f in franchissements)
        if aucun_arret and aucun_arme:
            return ()
        # DETTE-031 : cette lecture recompose **intégralement** chaque phase qui tourne, chaîne de
        # sources amont comprise — et ce service la paie après **chaque validation de score**, quand
        # seuls le pilotage et l'écran de salle la payaient toutes les 10 s. L'ordre de grandeur
        # reste tenable (une ou deux phases actives, ~30 tablettes, SQLite local) ; la dette est
        # élargie plutôt que contournée par une mémoïsation locale.
        #
        # ⚠️ **L'`AvancementDePhase` entier, pas seulement `tour_courant`** : c'est `nb_tours` qui
        # distingue « la phase est finie » de « je ne sais pas », dans `_avancement_connu`.
        avancements = self._suivi.avancement_par_phase(depart_id)
        arretees: list[PhaseId] = []
        arretees.extend(self._resoudre_les_arrets_armes(depart_id, phases, avancements))
        arretees.extend(
            self._declencher_les_arrets_atteints(depart_id, phases, avancements, circonstance)
        )
        # ⚠️ **Une seconde résolution, et une boucle bornée.** Mettre une phase en pause peut
        # **débloquer** un arrêt armé qui l'attendait : deux arrêts de portée départ dus au même
        # appel s'attendaient mutuellement, et le premier restait `ARME` — donc absent de la liste
        # de relance, donc la salle arrêtée **sans bouton**. Une seule passe ne suffit pas, l'ordre
        # d'itération décidant qui voit quoi. La boucle est **bornée par le nombre de phases**
        # plutôt qu'un `while True` : cette fonction tourne sur le thread du writer unique.
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
                self._franchissements.enregistrer(
                    self._horodate(franchissement.franchir(deja_en_pause))
                )
            elif deja_en_pause != list(franchissement.phases_arretees):
                # Encore armé, mais on retient déjà ce qui est arrêté : sans cette écriture
                # intermédiaire, une phase arrêtée puis reprise à la main sortirait de la liste de
                # relance, et le geste d'admin ne la rendrait jamais.
                self._franchissements.enregistrer(
                    self._horodate(
                        FranchissementArret(
                            phase_id=franchissement.phase_id,
                            apres_tour=franchissement.apres_tour,
                            etat=EtatFranchissement.ARME,
                            tours_a_finir=franchissement.tours_a_finir,
                            phases_arretees=tuple(deja_en_pause),
                            arrete_depuis=franchissement.arrete_depuis,
                            id=franchissement.id,
                        )
                    )
                )
        return arretees

    def _declencher_les_arrets_atteints(
        self,
        depart_id: DepartId,
        phases: dict[PhaseId, Phase],
        avancements: dict[PhaseId, AvancementDePhase],
        arrets_de_circonstance: Sequence[ArretDeCirconstance],
    ) -> list[PhaseId]:
        """Repère les arrêts que l'avancement vient d'atteindre, et les applique.

        `arrets_de_circonstance` est **passé** et non relu : `evaluer` en a déjà besoin pour sa
        garde de chemin court, et la relecture faisait deux `SELECT` identiques par validation de
        score (correctif de revue).
        """
        etapes = self._etapes_du_depart(depart_id)
        deja = self._traites_par_phase(depart_id)
        circonstance = _par_phase(arrets_de_circonstance)
        arretees: list[PhaseId] = []
        for phase_id, phase in phases.items():
            if phase.statut is not StatutPhase.EN_COURS:
                continue
            etape = etapes.get(phase.ordre)
            # ⚠️ **Les deux natures d'arrêt se lisent ensemble** (E05US034) : celles de l'étape et
            # celles posées dans ce créneau. Deux passes auraient ouvert un second chemin de
            # déclenchement, donc une seconde occasion de diverger sur « ce tour est-il fini ? ».
            #
            # ⚠️ **`etape is None` ne fait plus sortir** : `poser_arret_relatif` accepte une phase
            # sans étape, et le `continue` aurait rendu l'arrêt **inerte** — posé, 201, affiché,
            # sans effet. Cas inatteignable aujourd'hui ; la garde `if not arrets` suffit.
            arrets = arrets_applicables(
                etape.arrets if etape is not None else (), circonstance.get(phase_id, ())
            )
            if not arrets:
                continue
            tour_acheve = self._tour_acheve(avancements.get(phase_id), arrets)
            if tour_acheve is None:
                continue
            dus = arrets_atteints(arrets, tour_acheve, deja.get(phase_id, ()))
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
        au même instant (avancement sauté, lot de validations, reprise), on crédite le **plus
        ancien** et l'on **consomme** les suivants : les laisser en attente les ferait tomber l'un
        après l'autre à chaque reprise. Ils sont marqués `LEVE` sans avoir rien arrêté et
        **journalisés** — une pause manquée n'est **pas** visible à l'écran, seulement au journal.
        """
        applique, *manques = dus
        arretees: list[PhaseId] = []
        # ⚠️ **Une phase dont tout est tiré ne se met pas en pause.** La branche « tout est joué »
        # de `_tour_acheve` crédite l'arrêt le plus tardif atteint — nécessaire pour qu'un arrêt de
        # portée **départ** arrête les autres phases —, mais appliquée à la phase déclenchante
        # elle-même elle la figeait en `EN_PAUSE` alors qu'il ne restait rien à interrompre, et
        # l'organisateur devait la relancer pour pouvoir la clôturer.
        #
        # Le cas se produit quand le déclencheur n'a pas vu la frontière de tour ; l'arrêt est alors
        # traité comme un **manqué** — tracé `LEVE`, journalisé, jamais réarmé.
        avancement = avancements.get(phase_id)
        plus_rien_en_cours = avancement is not None and avancement.tour_courant is None
        if applique.portee is PorteeArret.PHASE and plus_rien_en_cours:
            manques = [applique, *manques]
        elif applique.portee is PorteeArret.PHASE:
            # ⚠️ **La trace AVANT la pause, et l'ordre compte.** Les deux écritures sont dans des
            # transactions distinctes : un franchissement qui échouerait après la mise en pause
            # laissait la phase `EN_PAUSE` **sans franchissement**, donc hors liste de relance,
            # donc **aucun bouton** — le mode de panne que tout cet ADR interdit, atteint par la
            # porte de l'`except`. Dans cet ordre la panne symétrique est bénigne : une trace sans
            # pause laisse un bouton sans effet, et le déclencheur suivant remet la phase en pause.
            self._franchissements.ajouter(
                self._horodate(
                    FranchissementArret(
                        phase_id=phase_id,
                        apres_tour=applique.apres_tour,
                        etat=EtatFranchissement.FRANCHI,
                        phases_arretees=(phase_id,),
                    )
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
                "Arrêt programmé après le tour %s de la phase %s manqué : la phase l'a dépassé "
                "(avancement sauté, ou tout est déjà tiré), il est consommé sans mise en pause.",
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

        La photo ne retient que les phases **en cours** : une phase **à venir** n'a rien à
        interrompre. ⚠️ Une phase **déjà en pause** produisait un interblocage — son tour ne bouge
        plus, donc `phases_a_arreter` ne la déclare jamais finie, donc l'arrêt reste `ARME` pour
        toujours, et un arrêt armé n'est pas relançable. La phase déclenchante est notée `None` («
        rien à finir »), ce qui la met en pause sans cas particulier.
        """
        a_finir: dict[PhaseId, int | None] = {}
        for autre_id, autre in phases.items():
            if autre.statut is not StatutPhase.EN_COURS:
                continue
            if autre_id == phase_id:
                a_finir[autre_id] = None
                continue
            # ⚠️ **Seule une phase dont on LIT le tour entre dans la photo.** `phases_a_arreter`
            # lit un `tour_a_finir` à `None` comme « plus rien en cours, elle s'arrête tout de
            # suite » : enregistrer `None` pour une phase dont le tour est **inconnu** la faisait
            # couper en plein tir. Le seul signal qui marche est `tour_courant is not None`.
            #
            # Conséquence assumée : un arrêt de portée départ ne coupe que les phases dont on sait
            # lire le tour. C'est le seul comportement honnête — on ne peut pas « laisser finir son
            # tour » une phase dont on ignore le tour.
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

        `ArretIntrouvable` (404) si l'identifiant est inconnu, appartient à un autre créneau, est
        encore `ARME`, ou a déjà été levé. Ne relance que les phases **effectivement en pause**. ⚠️
        **La source est le dépôt, pas `en_attente_de_relance`** : cette lecture *projette*
        `phases_arretees` sur ce qui est encore éteint, et repersister l'objet amputerait la trace
        dont `_traites_par_phase` se sert comme mémoire anti-redéclenchement.
        """
        franchissement = next(
            (
                item
                for item in self._franchissements.par_depart(depart_id)
                if item.id == franchissement_id
                and item.etat is not EtatFranchissement.LEVE
                and not (item.etat is EtatFranchissement.ARME and not item.phases_arretees)
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
        rejoué en permanence, donc il **constate** au lieu d'exiger. ⚠️ **Le statut est RELU au
        dépôt, pas lu dans le cliché** : la passe 1 change des statuts avant que la passe 2 ne les
        relise, et `TransitionStatutInvalide` sortait d'`evaluer`, avalée par
        `_signaler_validation`, en abandonnant la boucle. Le cliché est rafraîchi au passage.
        """
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.id is None or phase.statut is not StatutPhase.EN_COURS:
            return False
        self._cycle_de_vie.mettre_en_pause(depart_id, phase.id)
        if phase_id in phases:
            phases[phase_id] = replace(phases[phase_id], statut=StatutPhase.EN_PAUSE)
        return True

    def _circonstance_de(
        self, depart_id: DepartId, phase_id: PhaseId
    ) -> tuple[ArretDeCirconstance, ...]:
        """Les arrêts posés le jour J **sur cette phase**, dans ce créneau."""
        return tuple(
            arret
            for arret in self._arrets_de_circonstance.par_depart(depart_id)
            if arret.phase_id == phase_id
        )

    def _horodate(self, franchissement: FranchissementArret) -> FranchissementArret:
        """Date la **première** extinction d'un arrêt, et une seule fois (E05US034).

        Deux conditions, et il faut les deux : quelque chose est éteint (`phases_arretees`) et rien
        n'a encore été daté (`arrete_depuis is None`). La seconde empêche la pastille de
        **rajeunir** quand un arrêt coupe une seconde phase dix minutes plus tard ; la première
        interdit de dater un arrêt **manqué**, qui n'a éteint personne.
        """
        if franchissement.phases_arretees and franchissement.arrete_depuis is None:
            return replace(franchissement, arrete_depuis=self._horloge.maintenant())
        return franchissement

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
    def _tour_acheve(
        avancement: AvancementDePhase | None, arrets: Sequence[ArretProgramme]
    ) -> int | None:
        """Quel tour vient de s'achever pour cette phase. `None` si aucun, ou si on ne sait pas.

        ⚠️ **Le bloquant central de l'US était ici.** `tour_courant is None` a **cinq** provenances
        dont une seule signifie « fini » (ADR-0090) : les autres — pas de lecteur, service qui
        refuse, rien de composé, phase sans braquet — faisaient couper la salle au premier score
        validé. Avancement **absent** ⇒ on ne coupe pas ; `nb_tours <= 1` avec `tour_courant is
        None` ⇒ non plus. Le `min(nb_tours, …)` évite de créditer un arrêt au-delà du dernier tour.
        """
        if avancement is None or not _avancement_connu(avancement):
            return None
        if avancement.tour_courant is None:
            return min(avancement.nb_tours, max(arret.apres_tour for arret in arrets))
        if avancement.tour_courant <= 1:
            return None
        return avancement.tour_courant - 1
