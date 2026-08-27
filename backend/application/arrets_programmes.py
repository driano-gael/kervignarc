"""Service applicatif **Arrêts programmés** — la salle peut s'arrêter ([ADR-0091], [ADR-0092]).

Quatre gestes, un seul écrit :

- **`evaluer`** — le **déclencheur**, appelé après chaque validation de score : il met en pause les
  phases dont un arrêt vient d'être atteint. **Idempotent** — rappelé sans changement, il ne fait
  rien.
- **`lever`** — le geste de l'admin : un arrêt de portée départ relance **toutes** les phases qu'il
  a coupées, d'un seul geste.
- **`en_attente_de_relance`** — la lecture qu'affiche le pilotage.
- **`poser_arret_relatif`** — le geste du jour J (« bloque-moi dans deux tours »). Il écrit un
  `ArretDeCirconstance`, qui appartient au **créneau** et n'est rejoué par aucun autre — à la
  différence d'un arrêt d'atelier, qui est du déroulé.

⚠️ **Ce service CONSTATE, il n'écoute pas.** Le projet ne persiste aucun avancement — chaque service
de format le recalcule à la lecture (ADR-0090 §5) et le lancement d'un tour est un *événement*, pas
un état (ADR-0056) : il n'existe nulle part où accrocher « le tour vient de se terminer ». D'où la
comparaison à chaque appel plutôt qu'une réaction.

⚠️ **Passer par `ServiceSuiviDeroule` pour l'avancement, jamais par un registre local.** C'est le
seul endroit qui sait répondre « quel tour tourne » pour **tous** les formats : poules, suisse et
Big Shoot Off répondent par le port `LecteurAvancementDePhase`, mais l'élimination directe — le
format le plus courant — n'en a pas et voit son avancement reconstruit depuis les braquets. Un
second registre par type laisserait donc le tableau hors du mécanisme, et serait la **quatrième**
résolution par type du dépôt.

**Coût de lecture assumé** : la couture recompose chaque phase qui tourne à chaque validation de
score — `DETTE-031`, marqueur au point d'appel.

[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
[ADR-0092]: ../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
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
    # `# DETTE-074` — c'est **ici** que la limite de `avancement_bloc` produit son effet. Une phase
    # en tableau à sources multiples ne projette aucun braquet, retombe sur `(nb_tours=1,
    # tour_courant=None)`, et ce prédicat la déclare donc *inconnue* : son arrêt ne se déclenche
    # jamais. Le repli est sûr — on ne coupe pas au mauvais moment — mais silencieux. Cf.
    # `docs/dette.md`, `DETTE-074`, qui porte les deux voies de résorption.
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
        annoncer une relance ferait cliquer sur un bouton sans effet), les `LEVE`, consommés, et
        — troisième catégorie, **correctif de bloquant de revue E05US034** (axe adversarial) —
        ceux dont **aucune phase arrêtée n'est encore en pause**.

        ⚠️ **Pourquoi cette troisième catégorie, et pourquoi maintenant.** Le pilotage offre, sur
        la ligne d'une phase en pause, le bouton **« Reprendre »** du cycle de vie à côté de
        « Relancer ». Le premier remet la phase `EN_COURS` sans jamais marquer le franchissement
        `LEVE` : l'arrêt restait donc « en attente de relance » **pour toujours**, sur une salle
        qui tire. Le trou existait depuis E05US033, confiné au panneau de pilotage, à côté de la
        phase, là où la contradiction se voyait ; cette US le **hisse au tableau de bord** avec un
        chrono croissant (« Une phase attend votre relance depuis 47 min »). Un rappel qu'on ne
        peut pas éteindre est pire que pas de rappel : c'est le filet de sécurité qui devient la
        source de fatigue d'alarme, et il aurait usé la vigilance sur *tous* les autres.

        Le critère est **l'état réel de la salle**, pas l'état du franchissement : si plus rien
        n'est éteint, il n'y a plus de geste à réclamer — quel que soit le chemin par lequel la
        phase est repartie.

        ⚠️ **`phases_arretees` est PROJETÉ sur ce qui est encore éteint** (2ᵉ correctif, axe
        adversarial), et c'est la moitié du geste précédent. Ne filtrer que l'appartenance à la
        liste déplaçait le trou de l'allumage vers le **comptage** : `phases_arretees` est la trace
        **historique** — jamais élaguée, et délibérément (`_resoudre_les_arrets_armes` l'écrit
        exprès pour ne pas la perdre). Sur un arrêt de créneau qui a éteint deux phases dont une a
        été reprise à la main, le tableau de bord annonçait donc « **2 phases** attendent votre
        relance », le pilotage « tout le créneau (2 phases) », et `lever` n'en repartait qu'une.
        Un chiffre faux dans le sens qui **alarme** — exactement ce que `resumeDeRelance` s'interdit
        dans sa propre docstring, et qui use la vigilance le plus vite.

        ⚠️ **Ce que cette projection oblige, et qu'il ne faut pas défaire** : `lever` ne peut plus
        prendre son franchissement ici. Il le **relit au dépôt**, sinon il repersisterait une trace
        amputée — la mémoire anti-redéclenchement (`_traites_par_phase`) s'en sert.
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

        Le geste appartient au **créneau** et à lui seul ([ADR-0092]) : ce que l'organisateur décide
        à 14 h pour une panne de chauffage n'a aucune raison d'être rejoué par le départ du soir.
        C'est ce qui interdit d'écrire ici dans l'`EtapeDeroule` — ce serait éditer le déroulé du
        tournoi, donc **propager** une décision locale (ADR-0076 §4 contre §5).

        Quatre refus, et chacun ferme un mode de panne distinct :

        1. **la phase n'est pas de ce créneau** → `ArretIntrouvable` (404). Sans ce contrôle, une
           route de pilotage laisserait poser un arrêt sur le créneau du voisin ;
        2. **le type n'annonce pas ses tours** → même règle qu'à l'atelier, et c'est *la même
           fonction* (`verifier_type_arretable`) : deux copies auraient divergé ;
        3. **le tour courant n'est pas lisible** → « dans x tours » n'a pas d'origine. Deviner
           couperait la salle au mauvais endroit (cf. `tour_d_un_arret_relatif`) ;
        4. **un arrêt occupe déjà ce tour**, ou **le tour visé dépasse la phase** →
           `verifier_arrets`, deux fois, **et la séparation est le correctif d'un bloquant de
           revue** (E05US034, trois axes) :
           - la **collision** se juge sur l'**union** des deux natures — c'est le seul endroit où
             on connaît les deux, et le seul moment où l'on a quelqu'un à qui répondre ;
           - l'**inertie** (`tour >= nb_tours`) se juge sur le **seul arrêt demandé**, avec le
             `nb_tours` du jour.

           ⚠️ **Passer le `nb_tours` du jour à l'union était un cul-de-sac.** Les arrêts de
           l'étape ont été composés avec `nb_tours=None` — la docstring de `verifier_arrets` dit
           pourquoi : « un système suisse réglé à 7 rondes n'en joue que 5 si l'effectif ne permet
           pas plus ». Un arrêt d'atelier après le tour 6 sur une phase qui n'en joue que 5 est
           donc **légitime et inerte**, et il faisait échouer **toute** pose du jour J sur cette
           phase, avec un message nommant un tour que l'organisateur n'a pas demandé et qu'il ne
           peut pas retirer depuis le pilotage (l'éditer irait dans le déroulé du **tournoi**,
           donc dans tous les créneaux — ce qu'ADR-0092 interdit). Le geste central de l'US
           mourait sur un réglage de la veille.

        ⚠️ **Strict ici, tolérant au déclencheur**, et l'asymétrie est voulue : `arrets_applicables`
        fusionne une collision au lieu de lever, parce qu'elle peut naître **après** la pose — un
        arrêt ajouté au déroulé du tournoi pendant que le créneau tourne, ce que l'atelier ne peut
        pas voir (ADR-0076 le lui interdit). Lever à l'évaluation gèlerait tout le mécanisme du
        créneau ; refuser ici ne coûte qu'un message à quelqu'un qui a l'écran devant lui.

        [ADR-0092]: ../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
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
        # toutes les autres.
        #
        # ⚠️ **Le prix de la garde, compté honnêtement** (correctif de 2ᵉ passe, axe
        # adversarial — une rédaction antérieure annonçait « deux requêtes légères ») : le
        # chemin court fait **quatre** lectures, et non deux — les phases du créneau, le
        # créneau lui-même, le déroulé de son tournoi, les franchissements du créneau. Quatre
        # `SELECT` indexés contre une recomposition complète de chaque phase qui tourne : le
        # rapport reste largement favorable, et « aucun arrêt nulle part » est le cas normal du
        # dépôt. Mais annoncer un chiffre faux dans le commentaire qui justifie une
        # optimisation, c'est retirer au lecteur suivant le moyen de la remettre en cause.
        etapes = self._etapes_du_depart(depart_id)
        franchissements = self._franchissements.par_depart(depart_id)
        # ⚠️ **La garde compte les deux natures d'arrêt** (E05US034). Ne regarder que celles de
        # l'étape rendrait tout arrêt posé le jour J **inerte** : le chemin court sortirait avant
        # de lire l'avancement, donc avant de pouvoir constater quoi que ce soit. C'est le mode de
        # panne le plus vicieux du mécanisme — la pose répond 200, l'écran affiche l'arrêt, et
        # l'heure passe sans que rien ne coupe. Une cinquième lecture au chemin court : le rapport
        # reste celui qu'établit le commentaire ci-dessus.
        #
        # ⚠️ **Lue une fois, puis passée en aval** (correctif de revue, axes A et C1). La première
        # rédaction relisait `par_depart` dans `_circonstance_par_phase`, soit **deux** `SELECT`
        # identiques par validation de score sur le thread du writer unique — pendant que la
        # docstring de ce helper annonçait « une seule lecture », vraie de la fonction et fausse du
        # parcours. C'est le même écart de comptage que la garde ci-dessus a déjà eu à corriger.
        circonstance = self._arrets_de_circonstance.par_depart(depart_id)
        aucun_arret = not any(etape.arrets for etape in etapes.values()) and not circonstance
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
        arretees.extend(
            self._declencher_les_arrets_atteints(depart_id, phases, avancements, circonstance)
        )
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
            # ⚠️ **Les deux natures d'arrêt se lisent ensemble** (E05US034) : celles de l'étape, que
            # tous les créneaux rejouent, et celles que le pilotage a posées **dans ce créneau-ci**.
            # Les traiter en deux passes aurait ouvert un second chemin de déclenchement, donc une
            # seconde occasion de diverger sur la question la plus délicate du module (« ce tour
            # est-il fini ? ») — celle qui a produit trois bloquants en revue d'`E05US033`.
            # ⚠️ **`etape is None` ne fait plus sortir** (correctif de revue, axe C1). L'asymétrie
            # était réelle : `poser_arret_relatif` accepte une phase sans étape et persiste
            # l'arrêt, tandis qu'ici le `continue` l'aurait rendu **inerte** — posé, répondu 201,
            # affiché, et sans effet. Le cas est aujourd'hui inatteignable (`ServicePhases`
            # supprime la phase avec son étape), d'où une suggestion et non un bloquant ; le rendre
            # robuste coûte une ligne, et la garde `if not arrets` juste en dessous fait déjà le
            # travail que faisait le `continue`.
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
        au même instant (l'avancement a sauté plusieurs tours entre deux évaluations : correction en
        cascade, lot de validations, reprise après incident), on crédite le **plus ancien** — c'est
        la pause que l'organisateur voulait, appliquée en retard — et l'on **consomme** les
        suivants.

        Les laisser en attente serait le piège : ils se déclencheraient l'un après l'autre à chaque
        reprise, et l'organisateur devrait relancer trois fois pour une seule coupe. Ils sont donc
        marqués `LEVE` sans avoir rien arrêté, et **journalisés** : une pause manquée est un fait
        d'exploitation, pas un détail.
        ⚠️ **Toujours pas visible à l'écran**, et E05US034 ne l'a pas repris : cette tranche
        rend visible la pause **qui a eu lieu**, pas celle qui a été *manquée*. Une pause
        manquée reste donc un fait de journal — acceptable parce qu'elle ne bloque personne
        (rien n'a été arrêté), mais à ne pas confondre avec « c'est traité ».

        ⚠️ **Un arrêt de portée phase sur une phase dont tout est tiré est consommé de la même
        façon** — voir le commentaire ci-dessous. C'est le second chemin vers « pause manquée », et
        il se traite comme le premier plutôt que d'inventer un troisième état.
        """
        applique, *manques = dus
        arretees: list[PhaseId] = []
        # ⚠️ **Une phase dont tout est tiré ne se met pas en pause** (correctif de 2ᵉ passe, axe
        # adversarial). La branche « tout est joué » de `_tour_acheve` crédite l'arrêt le plus
        # tardif réellement atteint : c'est ce qu'il faut pour qu'un arrêt de portée **départ**
        # arrête bien
        # les autres phases. Mais appliqué à la phase déclenchante elle-même, quand elle n'a plus
        # rien en cours, cela la figeait en `EN_PAUSE` alors qu'il ne restait **rien à interrompre**
        # — et l'organisateur devait la relancer pour pouvoir la clôturer. Une pause qui ne suspend
        # rien et ajoute un geste obligatoire est une régression, pas un service.
        #
        # Le cas se produit quand le déclencheur n'a **pas vu** la frontière de tour : évaluation
        # sautée (le signalement avale ses exceptions), lot de validations, reprise après incident.
        # L'arrêt est alors traité comme un **manqué** — tracé `LEVE`, journalisé, jamais réarmé —
        # ce qui est exactement sa nature : la pause n'a pas eu lieu.
        avancement = avancements.get(phase_id)
        plus_rien_en_cours = avancement is not None and avancement.tour_courant is None
        if applique.portee is PorteeArret.PHASE and plus_rien_en_cours:
            manques = [applique, *manques]
        elif applique.portee is PorteeArret.PHASE:
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

        ⚠️ **La source est le dépôt, pas `en_attente_de_relance`** (correctif de revue, axe
        adversarial). Deux raisons, et la seconde est un piège :
        1. cette lecture **projette** `phases_arretees` sur ce qui est encore éteint ; repersister
           l'objet qu'elle rend amputerait la trace en base, dont `_traites_par_phase` se sert
           comme mémoire anti-redéclenchement ;
        2. elle écarte aussi les arrêts dont plus rien n'est en pause — un organisateur qui clique
           « Relancer » sur une liste vieille de dix secondes, après avoir repris la dernière phase
           à la main, recevait un **404** alors que les quatre cas énumérés ci-dessus étaient les
           seuls prévus. Il n'y a rien à relancer, mais ce n'est pas « introuvable » : `lever`
           consomme l'arrêt et rend une relance vide.
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

        Deux conditions, et il faut les deux : quelque chose est éteint (`phases_arretees`), et rien
        n'a encore été daté (`arrete_depuis is None`). La seconde est ce qui empêche la pastille de
        **rajeunir** quand un arrêt de créneau coupe une seconde phase dix minutes plus tard — elle
        annoncerait alors « depuis 1 min » sur une salle arrêtée depuis vingt, c'est-à-dire qu'elle
        mentirait dans le sens qui endort la vigilance.

        La première interdit de dater un arrêt **manqué** : la trace d'une pause consommée sans
        mise en pause (avancement sauté, phase déjà tout tirée) n'a éteint personne, et lui donner
        une heure ferait apparaître une attente qui n'a jamais existé.
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

        ⚠️ **C'est ici que se jouait le bloquant central de l'US**, relevé par les quatre axes de
        revue. La première rédaction lisait `tour_courant is None` comme « tout est joué, donc le
        dernier tour est achevé » et rendait `max(apres_tour)`. Or `None` a **au moins cinq**
        provenances, dont une seule signifie « fini » :

        1. *tout est joué* — la convention d'`AvancementDePhase` (ADR-0090). La seule qui autorise à
           couper ;
        2. *aucun lecteur branché pour ce type* — `ServiceSuiviDeroule._avancement_lu` le rend sans
           rien tenter, et sa docstring nomme les cas : échauffement, barrage, placement, colline
           (la **qualification** en est sortie en E05US035, elle a désormais son lecteur) ;
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

          ⚠️ **Cette dernière phrase a été FAUSSE le temps d'une revue**, et elle sert de prémisse
          de sûreté à toute la branche : E05US035 a rendu la qualification arrêtable **par type**
          alors que son nombre de tours est un réglage d'instance, si bien qu'une qualification non
          découpée — un seul tour — pouvait porter un arrêt accepté à l'atelier. Le refus est
          rétabli à la composition (`EtapeDeroule._nb_tours_a_la_composition`), donc la phrase
          redevient exacte. Le noter parce que le prochain qui lira cette branche pourrait la
          croire morte et la supprimer : elle ne l'est pas, elle est **gardée en amont**.

        Le `min(nb_tours, …)` de la branche « tout est joué » évite de créditer un arrêt posé
        au-delà du dernier tour **réellement joué** : un suisse réglé à 9 rondes qui n'en apparie
        que 5 ne doit pas voir se déclencher, à la fin, la pause qu'on avait prévue « après le tour
        7 » — elle mettrait en pause une phase dont tout est tiré, et il faudrait la relancer pour
        pouvoir la clôturer.

        Au tour 1 en cours, aucun tour n'est achevé : la phase vient de démarrer.

        ⚠️ **Reçoit les arrêts, plus l'étape** (E05US034). La branche « tout est joué » se borne au
        plus tardif des arrêts *applicables* : lui passer `etape.arrets` ignorait ceux posés le jour
        J, si bien qu'une phase terminée créditait la pause de l'atelier et **jamais** celle que
        l'organisateur venait de poser. Le paramètre dit maintenant ce dont la fonction a besoin —
        un jeu d'arrêts —, pas d'où il vient.
        """
        if avancement is None or not _avancement_connu(avancement):
            return None
        if avancement.tour_courant is None:
            return min(avancement.nb_tours, max(arret.apres_tour for arret in arrets))
        if avancement.tour_courant <= 1:
            return None
        return avancement.tour_courant - 1
