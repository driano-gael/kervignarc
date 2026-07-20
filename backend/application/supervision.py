"""Service applicatif de **supervision des postes** (E12US001, ADR-0038).

Console du jour J : pour chaque poste de cible d'un tournoi, agrège son **état** (en ligne / hors
ligne / non rattaché — politique pure `domain.supervision.etat_poste`), sa **dernière saisie** et
son **avancement**, plus un compteur global (« 28/30 en ligne »). Deux horloges, deux questions
(ADR-0038 §2) : le **heartbeat** (présence) dit *vivant / mort* ; la **saisie** dit *avance /
stagne*. L'admin peut **révoquer** un poste (`D-07`).

Lecture synchrone hors boucle événementielle (règle 7) : sessions et présence sont en mémoire, les
postes et séries en base (lectures courtes). Seule écriture, la **révocation**, ne touche que des
états de session **en mémoire** — pas la file d'écriture.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import PosteIntrouvable, TournoiIntrouvable
from application.postes import StoreSessionsPoste
from application.saisie import AvancementCible
from domain.depart import DepartId
from domain.ports import Horloge, PosteRepository, RegistrePresence, TournoiRepository
from domain.poste import Poste, PosteId
from domain.supervision import EtatPoste, etat_poste
from domain.tournoi import TournoiId


class LecteurAvancement(Protocol):
    """Port étroit : lire l'avancement d'une cible (réalisé par `ServiceSaisie.avancement_cible`).

    La supervision ne dépend pas de tout `ServiceSaisie` : juste de sa capacité à composer
    l'avancement d'une cible (barème + séries des archers placés). Découplage utile en test — un
    faux lecteur suffit — et honnête : la supervision n'écrit jamais de saisie.
    """

    def avancement_cible(
        self, tournoi_id: TournoiId, cible_index: int, depart_id: DepartId
    ) -> AvancementCible:
        """Compose l'avancement (volée courante / total) et la dernière saisie d'une cible."""
        ...


@dataclass(frozen=True)
class Avancement:
    """Avancement affichable d'un poste : la volée en cours sur le total attendu (« 8/12 »)."""

    volee_courante: int
    nb_volees: int


@dataclass(frozen=True)
class LigneSupervision:
    """Une ligne de la console : un poste de cible et tout ce qu'on en sait à cet instant.

    `derniere_saisie`, `ip` et `avancement` sont `None` quand ils n'ont pas de sens (poste non
    rattaché, ou rattaché sans départ courant fixé — pas encore en saisie). `ip` est un indice de
    **diagnostic** (`D-06`), jamais une identité. Le **code** de cible (credential du QR) n'est
    volontairement **pas** exposé ici : la console est un écran admin toujours ouvert, on n'y étale
    pas un secret de rattachement — le poste se désigne par son **numéro de cible**.
    """

    poste_id: PosteId
    cible_index: int
    etat: EtatPoste
    derniere_saisie: datetime.datetime | None
    ip: str | None
    avancement: Avancement | None


@dataclass(frozen=True)
class EtatSupervision:
    """Instantané complet de la console : les lignes triées par cible + le compteur global."""

    postes: tuple[LigneSupervision, ...]
    nb_en_ligne: int
    nb_total: int


class ServiceSupervision:
    """Cas d'usage de la supervision des postes : instantané, heartbeat, révocation."""

    def __init__(
        self,
        poste_repository: PosteRepository,
        tournoi_repository: TournoiRepository,
        sessions: StoreSessionsPoste,
        presence: RegistrePresence,
        avancement: LecteurAvancement,
        horloge: Horloge,
        seuil_hors_ligne_s: float,
    ) -> None:
        self._postes = poste_repository
        self._tournois = tournoi_repository
        self._sessions = sessions
        self._presence = presence
        self._avancement = avancement
        self._horloge = horloge
        self._seuil = seuil_hors_ligne_s

    def enregistrer_heartbeat(self, poste_id: PosteId, ip: str | None) -> None:
        """Consigne le heartbeat d'un poste : dernière vue = maintenant (`Horloge`) + IP diagnostic.

        Le poste a déjà été authentifié par son jeton à la frontière API ; on ne reçoit ici que son
        identité résolue. Écrit uniquement en mémoire (aucune transaction, aucune diffusion).
        """
        self._presence.enregistrer(poste_id, self._horloge.maintenant(), ip)

    def etat(self, tournoi_id: TournoiId) -> EtatSupervision:
        """Instantané de supervision : une ligne par poste de cible + compteur « en ligne / total ».

        Lève `TournoiIntrouvable` si le tournoi n'existe pas (cf. `ServicePostes.lister`).
        Les postes sont triés par numéro de cible. L'état de chacun est dérivé par la **politique
        pure** du domaine à partir du rattachement (session ouverte ?) et de l'écart au dernier
        heartbeat (calculé ici via `Horloge`, jamais dans le domaine).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        maintenant = self._horloge.maintenant()
        rattaches = self._sessions.postes_rattaches()
        departs = self._sessions.depart_courant_par_poste()
        lignes: list[LigneSupervision] = []
        for poste in sorted(self._postes.par_tournoi(tournoi_id), key=lambda p: p.cible_index):
            assert poste.id is not None  # un poste lu en base a toujours un id
            rattache = poste.id in rattaches
            activite = self._presence.derniere_activite(poste.id) if rattache else None
            secondes = (
                (maintenant - activite.instant).total_seconds() if activite is not None else None
            )
            etat = etat_poste(
                rattache=rattache,
                secondes_depuis_heartbeat=secondes,
                seuil_hors_ligne_s=self._seuil,
            )
            avancement, derniere = self._lire_avancement(tournoi_id, poste, rattache, departs)
            lignes.append(
                LigneSupervision(
                    poste_id=poste.id,
                    cible_index=poste.cible_index,
                    etat=etat,
                    derniere_saisie=derniere,
                    ip=activite.ip if activite is not None else None,
                    avancement=avancement,
                )
            )
        nb_en_ligne = sum(1 for ligne in lignes if ligne.etat is EtatPoste.EN_LIGNE)
        return EtatSupervision(postes=tuple(lignes), nb_en_ligne=nb_en_ligne, nb_total=len(lignes))

    def revoquer_poste(self, tournoi_id: TournoiId, poste_id: PosteId) -> None:
        """Révoque un poste : ferme **toutes** ses sessions et oublie sa présence (`D-07`).

        `PosteIntrouvable` si le poste n'existe pas **ou** relève d'un autre tournoi (même parti que
        `DepartIntrouvable` : un poste d'un tournoi voisin n'existe pas ici). Idempotent — révoquer
        un poste déjà non rattaché est sans effet supplémentaire. La tablette repasse *non
        rattachée* et retombe, à la prochaine résolution, sur l'écran de rattachement.
        """
        poste = self._postes.par_id(poste_id)
        if poste is None or poste.tournoi_id != tournoi_id:
            raise PosteIntrouvable(f"Aucun poste d'identifiant {poste_id} dans ce tournoi.")
        self._sessions.invalider_poste(poste_id)
        self._presence.oublier(poste_id)

    def _lire_avancement(
        self,
        tournoi_id: TournoiId,
        poste: Poste,
        rattache: bool,
        departs: dict[PosteId, DepartId],
    ) -> tuple[Avancement | None, datetime.datetime | None]:
        """Avancement + dernière saisie si poste rattaché et départ fixé, sinon (None, None).

        Un poste non rattaché — ou rattaché mais sans départ courant fixé (ADR-0034) — n'a pas
        encore de grille : ni avancement ni dernière activité à afficher (« — » côté console).
        """
        if not rattache or poste.id is None:
            return None, None
        depart_id = departs.get(poste.id)
        if depart_id is None:
            return None, None
        av = self._avancement.avancement_cible(tournoi_id, poste.cible_index, depart_id)
        return (
            Avancement(volee_courante=av.volee_courante, nb_volees=av.nb_volees),
            av.derniere_saisie,
        )
