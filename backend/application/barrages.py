"""Service applicatif Barrage (E06US003, ADR-0066) — organiser un départage au tir.

Cas d'usage d'**écriture** (donc consommés par la file du writer unique, règle 7) : annoncer un
barrage sur une égalité que la politique `tiebreak` a signalée, saisir ses manches, le clore. La
lecture (« quelles égalités restent à départager ? ») appartient au **classement**, qui les calcule
déjà : les recalculer ici en produirait une seconde version, qui dériverait.

**Le service ne décide pas qu'un barrage est nécessaire — il l'organise.** C'est la politique qui
signale (`Classement.egalites_a_departager`, seuil d'ADR-0066) et l'organisateur qui déclenche. Le
service se contente de vérifier que l'égalité annoncée est bien l'une de celles-là : sans ce
contrôle, on pourrait faire retirer trois archers qui ne sont pas à égalité, et publier le résultat.

⚠️ **Les trois portées sont servies, mais pas de la même façon — et la nuance compte.** En
**qualification**, les tireurs sont *dérivés* du classement et le verdict y **retourne** : la boucle
est fermée. En **poule** et en **Big Shoot Off**, les tireurs sont *désignés* par l'organisateur,
parce qu'il n'existe aujourd'hui aucun classement de poule ni aucun état de Big Shoot Off calculé
quelque part — ni `poule.py` ni `big_shoot_off.py` n'ont de consommateur de production (DETTE-028).
Le barrage y est donc pleinement opérationnel (annonce, manches, verdict, correction, annulation),
mais son verdict **ne retourne dans aucun classement**, faute de classement à alimenter. La boucle
se fermera quand le chantier moteur livrera l'exécution de ces phases ; d'ici là, l'organisateur qui
fait tourner une poule sur papier peut conduire et enregistrer son barrage dans l'application.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from application.classements import ServiceClassement
from application.erreurs import (
    BarrageDejaClos,
    BarrageIntrouvable,
    EgaliteNonDepartageable,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.barrage import (
    BarrageDePlaces,
    BarrageId,
    PorteeBarrage,
    TirBarrage,
)
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.phase import PhaseId
from domain.ports import (
    ArcherRepository,
    BarrageRepository,
    Horloge,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceBarrage:
    """Cas d'usage du barrage de places : annoncer, saisir une manche, clore."""

    def __init__(
        self,
        tournois: TournoiRepository,
        barrages: BarrageRepository,
        classements: ServiceClassement,
        horloge: Horloge,
        archers: ArcherRepository | None = None,
        phases: PhaseRepository | None = None,
    ) -> None:
        self._tournois = tournois
        self._barrages = barrages
        self._classements = classements
        self._horloge = horloge
        # Requis par les portées **poule** et **Big Shoot Off**, où les tireurs sont *désignés* et
        # non dérivés d'un classement : il faut alors vérifier qu'ils appartiennent au tournoi, et
        # que la phase citée aussi. Facultatifs pour ne pas casser un câblage qui n'annoncerait que
        # des barrages de qualification.
        self._archers = archers
        self._phases = phases

    def lister(self, tournoi_id: TournoiId) -> list[BarrageDePlaces]:
        """Tous les barrages d'un tournoi, clos compris (les verdicts acquis en font partie)."""
        self._exiger_tournoi(tournoi_id)
        return self._barrages.par_tournoi(tournoi_id)

    def annoncer(
        self,
        tournoi_id: TournoiId,
        rang: int | None = None,
        portee: PorteeBarrage = PorteeBarrage.QUALIFICATION,
        archer_ids: Sequence[ArcherId] = (),
        phase_id: PhaseId | None = None,
        reference: str | None = None,
    ) -> BarrageDePlaces:
        """Annonce un barrage. **Deux régimes, selon d'où viennent les tireurs.**

        **Qualification** — les tireurs sont *dérivés* du classement : on exige que `rang` désigne
        une égalité **actuellement signalée** par la politique. Sans ce contrôle, on ferait retirer
        des archers que plus rien n'oppose. Le cas n'est pas théorique : entre l'affichage et le
        clic, une volée validée en retard peut avoir défait l'égalité (`EgaliteNonDepartageable`).

        **Poule et Big Shoot Off** — les tireurs sont *désignés* par l'organisateur, parce qu'il
        n'existe aujourd'hui **aucun classement de poule ni aucun état de Big Shoot Off calculé**
        où les lire : ni `poule.py` ni `big_shoot_off.py` n'ont de consommateur de production
        (DETTE-028). Le barrage y est donc pleinement opérationnel — annonce, manches, verdict,
        correction — mais son verdict ne retourne dans aucun classement, faute de classement à
        alimenter. C'est la limite exacte, et elle disparaîtra quand le chantier moteur livrera
        l'exécution de ces phases.

        Dans les deux cas les tireurs sont **figés** à l'annonce : c'est ce qui empêche la liste de
        changer sous les pieds du juge. Et l'annonce est **idempotente** — un double clic sur
        « faire tirer » ne doit pas ouvrir deux barrages sur la même place.
        """
        self._exiger_tournoi(tournoi_id)
        existant = self._ouvert_equivalent(tournoi_id, portee, rang, phase_id, reference)
        if existant is not None:
            return existant
        if portee is PorteeBarrage.QUALIFICATION:
            participants = self._egalite_signalee(tournoi_id, rang)
        else:
            participants = self._participants_designes(tournoi_id, archer_ids, phase_id)
        return self._barrages.ouvrir(
            BarrageDePlaces(
                tournoi_id=tournoi_id,
                portee=portee,
                participants=participants,
                cree_le=self._horloge.maintenant(),
                rang_dispute=rang,
                phase_id=phase_id,
                reference=reference,
            )
        )

    def _egalite_signalee(self, tournoi_id: TournoiId, rang: int | None) -> tuple[Participant, ...]:
        """Les tireurs d'une égalité **que la politique réclame** — régime qualification."""
        if rang is None:
            raise EgaliteNonDepartageable(
                "Un barrage de qualification départage une place : indiquez son rang."
            )
        egalite = next(
            (
                candidate
                for candidate in self._classements.pour_tournoi(tournoi_id).egalites_a_departager
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
        archer_ids: Sequence[ArcherId],
        phase_id: PhaseId | None,
    ) -> tuple[Participant, ...]:
        """Les tireurs **désignés** — régime poule / Big Shoot Off, avec ses gardes propres.

        Aucun classement ne les valide ici : c'est donc au service de vérifier ce que le régime
        qualification obtenait gratuitement — des archers **de ce tournoi**, distincts, au moins
        deux, et une phase qui appartient elle aussi au tournoi. Sans cela, un identifiant deviné
        ferait tirer l'archer d'un autre tournoi (deux tournois tournent en parallèle par
        conception).
        """
        distincts: list[ArcherId] = []
        for archer_id in archer_ids:
            if archer_id not in distincts:
                distincts.append(archer_id)
        if len(distincts) < 2:
            raise EgaliteNonDepartageable("Un barrage départage au moins deux archers distincts.")
        if self._archers is not None:
            connus = {archer.id for archer in self._archers.par_tournoi(tournoi_id) if archer.id}
            etrangers = [archer_id for archer_id in distincts if archer_id not in connus]
            if etrangers:
                raise EgaliteNonDepartageable(
                    f"{len(etrangers)} archer(s) désigné(s) n'appartiennent pas à ce tournoi."
                )
        if phase_id is not None and self._phases is not None:
            phases = {phase.id for phase in self._phases.par_tournoi(tournoi_id)}
            if phase_id not in phases:
                raise EgaliteNonDepartageable(f"La phase {phase_id} n'appartient pas à ce tournoi.")
        return tuple(Participant.individuel(archer_id) for archer_id in distincts)

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        barrage_id: BarrageId,
        tirs: Sequence[TirBarrage],
        manche: int | None = None,
    ) -> BarrageDePlaces:
        """Saisit (ou **corrige**) une manche, puis rend le barrage rechargé.

        `manche` absent = la **suivante** ; fourni, il désigne la manche à réécrire — c'est le mode
        de correction d'une flèche mal notée, le verdict n'étant jamais stocké mais recalculé.

        ⚠️ **La manche est validée AVANT d'être écrite, en rejouant le moteur sur l'agrégat
        projeté.** C'est le correctif d'un défaut qui coûtait cher : les gardes du moteur (tireur
        déjà départagé, groupe retiré à moitié, manche 1 incomplète, doublon) ne se déclenchaient
        qu'au moment de **relire** le verdict, donc **après** le commit. La requête était refusée et
        la ligne écrite ; ensuite, chaque lecture rejouait le moteur et levait — donc
        `GET /classement`, **public et affiché en salle**, tombait en 422 pour tout le tournoi, et
        le panneau d'organisation avec lui : plus aucun écran pour réparer. Le raisonnement initial
        (« ne pas dupliquer une garde ») confondait *dupliquer la règle* et *la jouer avant
        d'écrire*.

        ⚠️ **Corriger une manche tronque les suivantes.** Réécrire la manche 1 change la partition,
        donc les retirs qui en découlaient n'ont plus d'objet — les garder produirait un agrégat
        incohérent que le moteur refuserait à la lecture. Le règlement fait retirer ; il ne recycle
        pas un tir devenu sans objet.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        if barrage.clos:
            raise BarrageDejaClos(
                "Ce barrage est clos : annulez-le ou ouvrez-en un nouveau pour faire retirer."
            )
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
        return self._barrages.enregistrer_manche(barrage_id, numero, tirs)

    def annuler(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> None:
        """Supprime un barrage annoncé par erreur, et ses tirs.

        Sans cette porte de sortie, un barrage ouvert au mauvais rang était **définitif** :
        `clore` exige un barrage résolu, et un barrage qu'on ne veut pas faire tirer ne le sera
        jamais. Il restait affiché indéfiniment, et son rang bloquait toute nouvelle annonce.

        Un barrage **clos** ne s'annule pas : son verdict est acquis et appliqué au classement.
        Le défaire demanderait de re-signaler l'égalité, ce qui est le travail d'une correction de
        manche, pas d'une suppression.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        if barrage.clos:
            raise BarrageDejaClos(
                "Ce barrage est clos : son verdict est acquis. Corrigez une manche si le résultat "
                "saisi est faux."
            )
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

    def _ouvert_equivalent(
        self,
        tournoi_id: TournoiId,
        portee: PorteeBarrage,
        rang: int | None,
        phase_id: PhaseId | None,
        reference: str | None,
    ) -> BarrageDePlaces | None:
        """Le barrage **non clos** qui dispute déjà la même chose, s'il y en a un.

        L'identité d'un barrage, c'est le quadruplet `(portée, phase, référence, rang)` : c'est lui
        qui rend l'annonce idempotente. La `référence` porte le numéro de poule ou de manche —
        deux poules du même tournoi disputent des places distinctes, elles ne se confondent pas.
        """
        return next(
            (
                barrage
                for barrage in self._barrages.par_tournoi(tournoi_id)
                if barrage.portee is portee
                and barrage.rang_dispute == rang
                and barrage.phase_id == phase_id
                and barrage.reference == reference
                and not barrage.clos
            ),
            None,
        )

    def _exiger_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_barrage(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> BarrageDePlaces:
        """Le barrage, à condition qu'il appartienne bien à **ce** tournoi.

        Le contrôle d'appartenance n'est pas cosmétique : sans lui, un identifiant deviné laisserait
        saisir des flèches dans le barrage d'un autre tournoi — et deux tournois tournent en
        parallèle par conception (intérieur et extérieur).
        """
        self._exiger_tournoi(tournoi_id)
        barrage = self._barrages.par_id(barrage_id)
        if barrage is None or barrage.tournoi_id != tournoi_id:
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
