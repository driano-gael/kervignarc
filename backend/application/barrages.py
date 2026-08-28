"""Barrages — le service ne décide pas qu'un barrage est nécessaire, il l'**organise**.

La politique signale, l'organisateur déclenche, le service vérifie que l'égalité annoncée est bien
l'une de celles-là : sans ce contrôle, on ferait retirer trois archers qui ne sont pas à égalité.

⚠️ **En poule et en Big Shoot Off, le verdict ne retourne dans AUCUN classement** — faute de
classement calculé à alimenter (`DETTE-028`). Le barrage y est conduit et enregistré, pas reversé.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from application.classements import ServiceClassement
from application.erreurs import (
    BarrageIntrouvable,
    BarragePerime,
    DepartIntrouvable,
    EgaliteNonDepartageable,
    TireursDesignesInvalides,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.barrage import (
    BarrageDePlaces,
    BarrageId,
    PorteeBarrage,
    TirBarrage,
)
from domain.depart import DepartId
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.phase import PhaseId
from domain.ports import (
    ArcherRepository,
    BarrageRepository,
    DepartRepository,
    Horloge,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class BarrageAffiche:
    """Un barrage tel que l'écran doit le voir : l'agrégat, plus ce que seul le service sait."""

    barrage: BarrageDePlaces
    perime: bool


class ServiceBarrage:
    """Cas d'usage du barrage de places : annoncer, saisir une manche, clore."""

    def __init__(
        self,
        tournois: TournoiRepository,
        barrages: BarrageRepository,
        classements: ServiceClassement,
        horloge: Horloge,
        archers: ArcherRepository,
        phases: PhaseRepository,
        departs: DepartRepository,
    ) -> None:
        self._tournois = tournois
        self._barrages = barrages
        self._classements = classements
        self._horloge = horloge
        # Le **cloisonnement** du créneau : `annoncer` reçoit un `depart_id` du corps de la requête
        # et doit vérifier qu'il relève bien du tournoi de la route (`_exiger_depart_du_tournoi`).
        self._departs = departs
        # Requis par les portées **poule** et **Big Shoot Off**, où les tireurs sont *désignés*
        # et non dérivés d'un classement : ce sont les **seules** protections de ce régime. Rendus
        # obligatoires après revue — il n'existe qu'un site de construction (composition root,
        # règle 8), donc l'optionalité n'achetait rien et laissait une garde de sécurité s'éteindre
        # sans le moindre signal.
        self._archers = archers
        self._phases = phases

    def lister(self, tournoi_id: TournoiId) -> list[BarrageAffiche]:
        """Tous les barrages d'un tournoi, **clos compris**, avec leur état de péremption.

        Les clos sont rendus parce qu'ils portent les verdicts acquis — et surtout parce qu'ils
        doivent rester **corrigeables** : un verdict acté par erreur n'a aucun autre chemin de
        réparation. La **péremption** est calculée ici : elle demande le classement courant, que
        seul le service sait obtenir. Un barrage périmé garde ses tirs, mais son verdict sera
        **écarté** — l'écran doit le dire.
        """
        self._exiger_tournoi(tournoi_id)
        barrages = self._barrages.par_tournoi(tournoi_id)
        if not barrages:
            return []
        # La péremption se juge **dans le départ** du barrage (ADR-0075) : un verdict écarté du
        # classement du matin ne dit rien de celui de l'après-midi. Le classement est calculé une
        # fois par créneau concerné, et non une fois par barrage — un tournoi de 4 départs peut
        # porter des dizaines de barrages.
        ecartes_par_depart = {
            depart_id: self._verdicts_ecartes(depart_id)
            for depart_id in {barrage.depart_id for barrage in barrages}
        }
        return [
            BarrageAffiche(
                barrage=barrage,
                perime=self._est_perime(barrage, ecartes_par_depart[barrage.depart_id]),
            )
            for barrage in barrages
        ]

    @staticmethod
    def _est_perime(barrage: BarrageDePlaces, ecartes: set[frozenset[Participant]]) -> bool:
        """Ce barrage a-t-il produit un verdict que le classement **n'a pas retenu** ?

        ⚠️ **On lit la réponse du domaine, on ne la recalcule pas.** Comparer les tireurs à
        l'égalité signalée au même rang manquait deux cas — le groupe qui **glisse de rang** et
        celui dont le rang **sort du seuil** —, laissant un « Départagé » vert au-dessus de rangs
        redevenus partagés. Ne vaut que pour la qualification (DETTE-028), et vaut pour un barrage
        **clos** : le verdict n'est jamais stocké mais recalculé.
        """
        if barrage.portee is not PorteeBarrage.QUALIFICATION:
            return False
        try:
            verdict = barrage.verdict()
        except ConfigurationBarrageInvalide:
            # Agrégat illisible : il est déjà signalé `incoherent`, et son verdict n'existe pas —
            # donc il n'a rien pu faire écarter. Le laisser lever ferait retomber `GET /barrages`
            # en 422, c'est-à-dire rouvrir le trou que le filet de `de_agregat` vient de fermer.
            return False
        return bool(verdict.ordre) and frozenset(verdict.ordre) in ecartes

    def annoncer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        rang: int | None = None,
        portee: PorteeBarrage = PorteeBarrage.QUALIFICATION,
        archer_ids: Sequence[ArcherId] = (),
        phase_id: PhaseId | None = None,
        reference: str | None = None,
    ) -> BarrageDePlaces:
        """Annonce un barrage. **Deux régimes, selon d'où viennent les tireurs.**

        **Qualification** — ils sont *dérivés* du classement : on exige que `rang` désigne une
        égalité **actuellement signalée**, sans quoi on ferait retirer des archers que plus rien
        n'oppose. **Poule et Big Shoot Off** — ils sont *désignés*, faute de classement calculé où
        les lire (DETTE-028), et le verdict ne retourne alors nulle part. Dans les deux cas les
        tireurs sont **figés**, et l'annonce est **idempotente**.
        """
        self._exiger_tournoi(tournoi_id)
        self._exiger_depart_du_tournoi(tournoi_id, depart_id)
        if portee is PorteeBarrage.QUALIFICATION:
            participants = self._egalite_signalee(depart_id, rang)
        else:
            participants = self._participants_designes(tournoi_id, depart_id, archer_ids, phase_id)
        # ⚠️ **Les barrages CLOS comptent ici aussi, dès qu'ils sont périmés.** Une première
        # version ne regardait que les non-clos : sur une place où un barrage acté était devenu
        # périmé, l'alerte disait « annulez-le puis relancez » **et** le bouton « Faire tirer »
        # restait offert, et le serveur acceptait. On obtenait deux cartes « acté » au même rang,
        # aux verdicts **inversés**, sans le moindre signal — et annuler la mauvaise détruisait le
        # verdict réellement appliqué.
        ecartes = (
            self._verdicts_ecartes(depart_id) if portee is PorteeBarrage.QUALIFICATION else set()
        )
        # ⚠️ **`par_depart` et non `par_tournoi`** (revue E01US025) : deux créneaux ayant
        # chacun une égalité au même **rang** se voyaient comme « le même endroit », et le second
        # se faisait refuser son barrage en `BarragePerime` — avec un message désignant une cause
        # qui n'existait pas. Une place se dispute dans le classement d'**un** départ (ADR-0075).
        #
        # ⚠️ Une première rédaction affirmait que ce bloc était **le seul** resté à la portée
        # tournoi. C'était faux. Un correctif qui se déclare exhaustif ferme la recherche chez le
        # relecteur suivant — on décrit ce qu'on a corrigé, jamais ce qui resterait.
        meme_endroit = [
            barrage
            for barrage in self._barrages.par_depart(depart_id)
            if barrage.portee is portee
            and barrage.rang_dispute == rang
            and barrage.phase_id == phase_id
            and barrage.reference == reference
            and (not barrage.clos or self._est_perime(barrage, ecartes))
        ]
        attendus = set(participants)
        existant = next(
            (
                b
                for b in meme_endroit
                if set(b.participants) == attendus
                and not b.clos
                and not self._est_perime(b, ecartes)
            ),
            None,
        )
        if existant is not None:
            return existant
        if meme_endroit and portee is PorteeBarrage.QUALIFICATION:
            # Hors qualification, « même place, tireurs différents » n'est pas un barrage périmé
            # mais **un autre barrage** : deux égalités d'une même poule se disputent séparément.
            # C'est en qualification seulement que le rang identifie la place de façon unique.
            raise BarragePerime(
                "Un barrage est deja ouvert ici, mais il ne porte plus sur les memes tireurs "
                "- le classement a bouge depuis son annonce. Annulez-le avant d'en ouvrir un "
                "nouveau : les archers qu'il designait ne sont plus ceux a departager."
            )
        return self._barrages.ouvrir(
            BarrageDePlaces(
                depart_id=depart_id,
                portee=portee,
                participants=participants,
                cree_le=self._horloge.maintenant(),
                rang_dispute=rang,
                phase_id=phase_id,
                reference=reference,
            )
        )

    def _egalite_signalee(self, depart_id: DepartId, rang: int | None) -> tuple[Participant, ...]:
        """Les tireurs d'une égalité **que la politique réclame** — régime qualification."""
        if rang is None:
            raise EgaliteNonDepartageable(
                "Un barrage de qualification départage une place : indiquez son rang."
            )
        egalite = next(
            (
                candidate
                for candidate in self._classements.pour_depart(depart_id).egalites_a_departager
                if candidate.rang == rang
            ),
            None,
        )
        if egalite is None:
            raise EgaliteNonDepartageable(
                f"Aucune égalité à départager au rang {rang} : soit elle n'existe plus, soit le "
                "format de ce tournoi ne prévoit pas de barrage à cette place."
            )
        return egalite.participants

    def _participants_designes(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        archer_ids: Sequence[ArcherId],
        phase_id: PhaseId | None,
    ) -> tuple[Participant, ...]:
        """Les tireurs **désignés** — régime poule / Big Shoot Off, avec ses gardes propres.

        Aucun classement ne les valide ici : c'est au service de vérifier ce que le régime
        qualification obtenait gratuitement — des archers **de ce tournoi**, distincts, au moins
        deux, et une phase **de ce créneau**. ⚠️ La phase se valide `par_depart` (ADR-0075) :
        accepter celle d'un autre créneau laissait le barrage pointer une phase que la suppression
        du créneau purge, donc une `IntegrityError` sur la suppression du départ.
        """
        distincts: list[ArcherId] = []
        for archer_id in archer_ids:
            if archer_id not in distincts:
                distincts.append(archer_id)
        if len(distincts) < 2:
            raise TireursDesignesInvalides("Un barrage départage au moins deux archers distincts.")
        connus = {
            archer.id for archer in self._archers.par_tournoi(tournoi_id) if archer.id is not None
        }
        etrangers = [archer_id for archer_id in distincts if archer_id not in connus]
        if etrangers:
            raise TireursDesignesInvalides(
                f"{len(etrangers)} archer(s) désigné(s) n'appartiennent pas à ce tournoi."
            )
        if phase_id is not None:
            phases = {phase.id for phase in self._phases.par_depart(depart_id)}
            if phase_id not in phases:
                raise TireursDesignesInvalides(
                    f"La phase {phase_id} n'appartient pas à ce créneau."
                )
        return tuple(Participant.individuel(archer_id) for archer_id in distincts)

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        barrage_id: BarrageId,
        tirs: Sequence[TirBarrage],
        manche: int | None = None,
    ) -> BarrageDePlaces:
        """Saisit (ou **corrige**) une manche, puis rend le barrage rechargé.

        `manche` absent = la **suivante** ; fourni, il désigne la manche à réécrire. ⚠️ **La manche
        est validée AVANT d'être écrite** : sinon les gardes ne se déclenchaient qu'à la
        **relecture**, donc après le commit, et `GET /classement` — public et affiché en salle —
        tombait en 422 pour tout le tournoi. ⚠️ Corriger une manche **tronque les suivantes** : les
        retirs qui en découlaient n'ont plus d'objet.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        numero = manche if manche is not None else len(barrage.manches) + 1
        if numero < 1:
            raise ConfigurationBarrageInvalide(
                "Les manches d'un barrage se comptent à partir de 1."
            )
        if numero > len(barrage.manches) + 1:
            # Sans cette garde, un `manche: 5` sur un barrage vierge créerait un trou : le
            # repository relit les manches **triées puis renumérotées positionnellement**, si bien
            # que la saisie suivante s'écrirait « manche 2 » et passerait *avant* le tir réellement
            # effectué en premier.
            raise ConfigurationBarrageInvalide(
                f"Ce barrage compte {len(barrage.manches)} manche(s) : la suivante porte le numéro "
                f"{len(barrage.manches) + 1}, pas {numero}."
            )
        self._exiger_tireurs_du_barrage(barrage, tirs)
        self._exiger_manche_jouable(barrage, numero, tirs)
        enregistre = self._barrages.enregistrer_manche(barrage_id, numero, tirs)
        if barrage.clos:
            # Saisir une manche sur un barrage clos le **rouvre** : on vient de dire que son
            # résultat n'était pas le bon, donc « le juge a acté » ne tient plus. Le laisser clos
            # afficherait un barrage réglé dont le verdict vient de changer.
            return self._barrages.rouvrir(barrage_id)
        return enregistre

    def annuler(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> None:
        """Supprime un barrage annoncé par erreur, et ses tirs.

        Sans cette porte de sortie, un barrage ouvert au mauvais rang était **définitif** : `clore`
        exige un barrage résolu, et un barrage qu'on ne veut pas faire tirer ne le sera jamais. ⚠️
        **Un barrage clos s'annule aussi** : garder les deux portes fermées laissait un juge ayant
        acté un verdict inversé sur la dernière place qualificative envoyer le mauvais archer au
        tableau, **définitivement**. Le verdict n'est jamais stocké, `clos` dit « le juge a acté ».
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        assert barrage.id is not None, "Un barrage relu est persisté."
        self._barrages.supprimer(barrage.id)

    def _exiger_manche_jouable(
        self, barrage: BarrageDePlaces, numero: int, tirs: Sequence[TirBarrage]
    ) -> None:
        """Rejoue le moteur sur l'agrégat **projeté** : rien n'est écrit si le verdict ne tient pas.

        La projection **tronque** les manches postérieures à celle qu'on écrit, exactement comme le
        fera le repository — sans quoi on validerait un état qui ne sera pas celui persisté.
        """
        manches = list(barrage.manches)[: numero - 1]
        manches.append(tuple(tirs))
        replace(barrage, manches=tuple(manches)).resultat()

    def clore(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> BarrageDePlaces:
        """Clôt un barrage **résolu** — le juge acte le verdict, plus de retir attendu.

        Clore un barrage non résolu est refusé : sa clôture signifierait « c'est tranché » alors que
        des tireurs restent à égalité, et le classement afficherait un ex æquo que l'écran
        présenterait comme réglé.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        if not barrage.resultat().est_resolu:
            raise EgaliteNonDepartageable(
                "Ce barrage n'a pas départagé tout le monde : il reste au moins un groupe à faire "
                "retirer avant de le clore."
            )
        return self._barrages.clore(barrage_id)

    def _verdicts_ecartes(self, depart_id: DepartId) -> set[frozenset[Participant]]:
        """Les verdicts que le classement **du départ** n'a pas retenus, par ensemble de tireurs."""
        return {
            frozenset(verdict.ordre)
            for verdict in self._classements.pour_depart(depart_id).verdicts_ecartes
        }

    def _exiger_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_depart_du_tournoi(self, tournoi_id: TournoiId, depart_id: DepartId) -> None:
        """Le créneau doit appartenir **au tournoi de la route**. `DepartIntrouvable` sinon.

        ⚠️ **Garde de cloisonnement, pas de commodité** : `annoncer` reçoit le `tournoi_id` du
        chemin et le `depart_id` du **corps**, sans rien qui les relie — un `depart_id` deviné
        ouvrait un barrage sur le créneau d'un **autre tournoi**, deux tournois `EN_COURS` en
        parallèle étant une capacité **voulue**. Le contrôle existait déjà pour les barrages et les
        phases ; c'est le départ qui y échappait.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )

    def _exiger_barrage(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> BarrageDePlaces:
        """Le barrage, à condition qu'il appartienne bien à **ce** tournoi.

        Le contrôle d'appartenance n'est pas cosmétique : sans lui, un identifiant deviné laisserait
        saisir des flèches dans le barrage d'un autre tournoi — et deux tournois tournent en
        parallèle par conception (intérieur et extérieur).
        """
        self._exiger_tournoi(tournoi_id)
        barrage = self._barrages.par_id(barrage_id)
        # Appartenance au tournoi par `depart → tournoi` : un barrage ne connaît plus que son
        # créneau (ADR-0075). La garde reste indispensable — deux tournois tournent en parallèle
        # par conception (intérieur et extérieur).
        connus = {b.id for b in self._barrages.par_tournoi(tournoi_id)}
        if barrage is None or barrage.id not in connus:
            raise BarrageIntrouvable(
                f"Aucun barrage d'identifiant {barrage_id} dans le tournoi {tournoi_id}."
            )
        return barrage

    def _exiger_tireurs_du_barrage(
        self, barrage: BarrageDePlaces, tirs: Sequence[TirBarrage]
    ) -> None:
        """Refuse une manche où figure quelqu'un qui n'a jamais été annoncé sur ce barrage.

        Le moteur attrape déjà le tireur **déjà départagé** ; il ne peut pas attraper l'archer
        parfaitement **étranger** au barrage, puisqu'il ne connaît que les tirs qu'on lui donne. Le
        laisser passer classerait un tiers à une place qu'il n'a pas disputée.
        """
        etrangers = [tir.participant for tir in tirs if tir.participant not in barrage.participants]
        if etrangers:
            raise ConfigurationBarrageInvalide(
                f"{len(etrangers)} tireur(s) de cette manche ne font pas partie du barrage annoncé."
            )

    @staticmethod
    def tir(archer_id: int, score: int | None, distance_au_centre: int | None = None) -> TirBarrage:
        """Fabrique un tir depuis un identifiant d'archer — la frontière API parle archers.

        La conversion vit ici et non dans le DTO : `Participant` est l'abstraction du moteur
        (ADR-0028), et c'est la couche applicative qui résout « archer ↔ participant » — pas l'API.
        """
        return TirBarrage(
            participant=Participant.individuel(archer_id),
            score=score,
            distance_au_centre=distance_au_centre,
        )
