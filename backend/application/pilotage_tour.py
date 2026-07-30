"""Service applicatif Pilotage du tour — feu vert + lancement (E12US002, ADR-0056).

C'est la **valeur du jour J** (EPIC-12) : ne jamais découvrir un blocage en appuyant sur le bouton,
et faire partir la suite **d'un geste** pour que 150 archers sachent où aller en moins de deux
minutes. Deux cas d'usage, **tous deux en lecture** sur le tableau reconstruit, plus une écriture
minimale pour le geste de lancement :

- **`feu_vert`** — l'état de préparation **affiché en continu** (`P-3` : l'appli n'empêche rien,
  elle montre). Pour chaque **duel à venir** (non tranché, pas un bye) : *participants connus ?*
  (occupants propagés), *cible attribuée ?* (jointure occupant → plan de duels persisté), et, quand
  un occupant manque, *quelle source* on attend (« en attente du duel n°3 ») — **ce qui bloque est
  nommé**, pas seulement signalé.
- **`impact_lancement`** — la **prévisualisation** que le bouton affiche : « N duels, cibles X et
  Y — K archers ». Lecture pure, comme `impact_regeneration` d'E12US007.
- **`lancer`** — le geste. **Le bouton ne calcule rien** : le tour suivant est déjà prêt (le
  placement l'a posé, la progression l'a peuplé). Lancer, c'est **faire partir** un ou plusieurs
  duels **prêts** — l'unité lançable est le **duel**, pas le tour (`D-23` : deux prêts et un qui
  attend sa source ⇒ on fait partir les deux). L'acte laisse une **trace d'audit** `LANCEMENT`
  (daté/attribué) qui, à la frontière API, **déclenche la diffusion** d'un `LiveEvent` typé aux 4
  canaux (`D-09`). **Aucun statut n'est posé** sur le tableau (il reste reconstruit du classement +
  duels validés, ADR-0049) : le lancement est un **événement**, pas un état (ADR-0056).

**Ce service ne calcule pas le tour suivant** (routage/seeding = EPIC-05), ne place pas (EPIC-03) :
il **agrège** ce que le classement, l'arbre et le plan tiennent séparés, et **émet** le geste. Il
compose donc `ServiceSaisieDuels` (reconstruction de l'arbre + noms), `ServicePlacementDuels` (le
plan → la cible de chaque duelliste) et `ServiceAudit` (la trace) — service→service, sur le
précédent de `ServiceClassement`.

**Séquencement assumé (règle 9, comme E12US005/E12US006 face à EPIC-05)** : le placement des tours
≥ 2 est E05US010 (non livré) — un duel de tour ≥ 2, même jouable, ressort donc « cible non
attribuée » tant que ce placement n'existe pas. Et les 3 canaux récepteurs (tablette E04US018,
public E07US008, écran de salle E07US004) ne sont pas construits : le lancement **émet** le signal,
mais seuls leurs futurs écrans le **recevront** de façon ciblée. Aucun comportement perdu, séquencé.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.audit import ServiceAudit
from application.erreurs import AucunDuelALancer, GabaritDuTournoiAbsent
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.classement import LigneClassement
from domain.entree_audit import ActionAuditee
from domain.erreurs import EffectifTableauInvalide
from domain.participant import GenreParticipant, Participant
from domain.phase import PhaseId
from domain.tableau import Match, PerdantDe, VainqueurDe
from domain.tournoi import TournoiId

# Auteur de la trace de lancement : l'organisateur agit sous le rôle **admin**, un secret partagé
# (E10US002, `D-13`), pas une personne nommée — on fige le rôle, comme la trace `REPLACEMENT`.
_AUTEUR_ADMIN = "Administrateur"


@dataclass(frozen=True)
class DuelAVenir:
    """Un duel **non encore tranché** et son état de préparation (les trois questions du CA).

    `participants_connus` = les deux occupants sont propagés (sources amont tranchées).
    `cible_attribuee` = les deux ont une cible dans le plan de duels persisté.
    `sources_en_attente` = les numéros des duels amont dont on attend l'issue (pour **nommer** le
    blocage). `pret_a_lancer` = jouable **et** placé : le seul état qui peut effectivement partir.
    `blocage` nomme ce qui manque (`None` si prêt) — jamais un simple drapeau (`P-3`).
    """

    numero: int
    tour: int
    haut: Duelliste | None
    bas: Duelliste | None
    participants_connus: bool
    cible_haut: int | None
    cible_bas: int | None
    cible_attribuee: bool
    sources_en_attente: tuple[int, ...]
    pret_a_lancer: bool
    blocage: str | None


@dataclass(frozen=True)
class FeuVert:
    """La photo du feu vert : les duels à venir avec leur état, et combien sont prêts à partir."""

    phase_id: int
    est_termine: bool
    duels: tuple[DuelAVenir, ...]
    nb_prets: int


@dataclass(frozen=True)
class ResumeLancement:
    """Ce que le bouton **chiffre** (et ce que le lancement a émis) : duels, cibles, archers.

    `nb_archers` = deux par duel (les tireurs directement concernés qui vont devoir se placer) — le
    décompte **défendable** aujourd'hui. Le « 118 personnes prévenues » du CA (l'audience entière
    via l'écran de salle et le public) suppose les canaux récepteurs d'E07US004/E07US008,
    séquencés : on ne fabrique pas un chiffre de spectateurs qu'on ne sait pas mesurer.
    """

    phase_id: int
    numeros: tuple[int, ...]
    cibles: tuple[int, ...]
    nb_duels: int
    nb_archers: int


class ServicePilotageTour:
    """Cas d'usage du pilotage d'un tour : feu vert, chiffrage, lancement des duels prêts."""

    def __init__(
        self,
        saisie_duels: ServiceSaisieDuels,
        placement_duels: ServicePlacementDuels,
        audit: ServiceAudit,
    ) -> None:
        self._saisie_duels = saisie_duels
        self._placement_duels = placement_duels
        self._audit = audit

    # --- Lecture -------------------------------------------------------------------------------

    def feu_vert(self, tournoi_id: TournoiId, phase_id: PhaseId) -> FeuVert:
        """L'état de préparation du prochain tour, duel par duel (lecture pure, `P-3`).

        Gardes de `reconstruire` (`TournoiIntrouvable` / `PhaseIntrouvable` / `PhasePasUnTableau`).
        Un tableau à moins de 2 archers en lice **n'existe pas** (`EffectifTableauInvalide`) :
        plutôt qu'échouer, l'écran rend un feu vert **vide** — « aucun duel à venir » — comme le
        plan de duels tolère un effectif insuffisant (plan vide).
        """
        try:
            tableau, lignes = self._saisie_duels.reconstruire(tournoi_id, phase_id)
        except EffectifTableauInvalide:
            return FeuVert(phase_id=phase_id, est_termine=False, duels=(), nb_prets=0)
        cibles = self._cibles_par_archer(tournoi_id, phase_id)
        a_venir = tuple(
            self._duel_a_venir(match, lignes, cibles)
            for match in tableau.matchs
            if not match.est_bye and match.vainqueur is None
        )
        return FeuVert(
            phase_id=phase_id,
            est_termine=tableau.est_termine,
            duels=a_venir,
            nb_prets=sum(1 for duel in a_venir if duel.pret_a_lancer),
        )

    def impact_lancement(
        self, tournoi_id: TournoiId, phase_id: PhaseId, numeros: tuple[int, ...] | None = None
    ) -> ResumeLancement:
        """Chiffre ce qu'un lancement déclencherait, **sans rien émettre** (prévisualisation).

        `numeros=None` = le **lancement global** (tous les duels prêts) ; sinon, l'intersection avec
        les prêts (le front peut proposer un sous-ensemble). Miroir exact de ce que `lancer` fera.
        """
        feu = self.feu_vert(tournoi_id, phase_id)
        return self._resume(phase_id, self._a_lancer(feu, numeros))

    # --- Écriture (via la file) ----------------------------------------------------------------

    def lancer(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numeros: tuple[int, ...] | None = None,
        auteur: str = _AUTEUR_ADMIN,
    ) -> ResumeLancement:
        """Fait **partir** les duels prêts (tous, ou le sous-ensemble `numeros`), et **trace**.

        Le feu vert est **recalculé ici** (dans la file) et jamais cru sur parole (E12US007) : un
        duel demandé qui n'est plus prêt (source dé-validée, cible retirée) est **écarté**. S'il ne
        reste, net, aucun duel à lancer, l'acte est un conflit d'état (`AucunDuelALancer`, 409) —
        rien à émettre, aucune trace. Sinon, une **entrée d'audit** `LANCEMENT` est consignée
        (datée/attribuée) : à la frontière API, sa présence dans la file **déclenche la diffusion**
        du `LiveEvent("tour_lance", …)` post-commit. Aucun statut n'est posé sur le tableau.
        """
        feu = self.feu_vert(tournoi_id, phase_id)
        a_lancer = self._a_lancer(feu, numeros)
        if not a_lancer:
            raise AucunDuelALancer(
                "Aucun duel n'est prêt à être lancé : rien à faire partir pour l'instant."
            )
        resume = self._resume(phase_id, a_lancer)
        self._audit.consigner(
            tournoi_id,
            ActionAuditee.LANCEMENT,
            auteur,
            objet=f"Lancement d'un tour — phase {phase_id}",
            apres=self._trace(resume),
        )
        return resume

    # --- Interne -------------------------------------------------------------------------------

    @staticmethod
    def _a_lancer(feu: FeuVert, numeros: tuple[int, ...] | None) -> tuple[DuelAVenir, ...]:
        """Les duels effectivement lançables : les prêts, filtrés par `numeros` si fourni."""
        prets = tuple(duel for duel in feu.duels if duel.pret_a_lancer)
        if numeros is None:
            return prets  # lancement global (`D-23`)
        demandes = set(numeros)
        return tuple(duel for duel in prets if duel.numero in demandes)

    @staticmethod
    def _resume(phase_id: PhaseId, duels: tuple[DuelAVenir, ...]) -> ResumeLancement:
        """Assemble le décompte chiffré : numéros, cibles distinctes triées, nombres."""
        numeros = tuple(sorted(duel.numero for duel in duels))
        cibles = tuple(
            sorted(
                {
                    cible
                    for duel in duels
                    for cible in (duel.cible_haut, duel.cible_bas)
                    if cible is not None
                }
            )
        )
        return ResumeLancement(
            phase_id=phase_id,
            numeros=numeros,
            cibles=cibles,
            nb_duels=len(numeros),
            nb_archers=2 * len(numeros),
        )

    @staticmethod
    def _trace(resume: ResumeLancement) -> str:
        """Le texte `apres` de la trace d'audit : ce que le lancement a fait partir."""
        cibles = ", ".join(str(cible) for cible in resume.cibles) or "—"
        return f"{resume.nb_duels} duel(s) lancé(s), cible(s) {cibles}"

    # DETTE-019 : jumelle de `ServiceRoutage._poses_par_archer` (E04US018).
    def _cibles_par_archer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> dict[int, int]:
        """`archer_id → cible_index` depuis le plan de duels **persisté** (`placement_tableau`).

        Best-effort en lecture : si le plan est indisponible — aucun gabarit appliqué, ou le
        placement des tours ≥ 2 (E05US010) n'existe pas encore — on renvoie une carte **vide**, d'où
        « cible non attribuée » sur les duels concernés, jamais un échec du feu vert. Même tolérance
        que `_zones_best_effort` de la saisie.
        """
        try:
            plan = self._placement_duels.plan_de_duels(tournoi_id, phase_id)
        except GabaritDuTournoiAbsent:
            return {}
        return {pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements}

    # DETTE-019 : garde tour-1, jumelle de `ServiceRoutage._pose_a_annoncer` (E04US018).
    # DETTE-021 : `cible_attribuee` n'exige pas que les deux camps soient sur la **même**
    # cible ni côte à côte — « prêt · cibles 4 et 7 » est donc affiché, et lancé. Le routage
    # porte l'alerte correspondante depuis E04US018 ; ici elle manque encore.
    def _duel_a_venir(
        self, match: Match, lignes: dict[int, LigneClassement], cibles: dict[int, int]
    ) -> DuelAVenir:
        """Assemble l'état d'un duel à venir : les trois questions du CA + le blocage nommé."""
        participants_connus = match.haut is not None and match.bas is not None
        # Le placement des cibles n'existe **qu'au tour 1** (E03US009, MVP tour-1 uniquement) ; le
        # placement intégral 1→N est E05US010, non livré. On **n'attribue donc aucune cible** aux
        # duels de tour ≥ 2 : leurs occupants (vainqueurs propagés) gardent leur ligne de placement
        # de tour 1 dans `placement_tableau`, mais cette cible serait **périmée** pour le tour
        # suivant (elle enverrait les finalistes, venus de deux cibles distinctes, sur l'ancienne).
        # Sans ce garde, le feu vert afficherait « prêt · cibles X et Y » et lancerait la finale à
        # tort — l'inverse de ce que promet l'ADR-0056. S'ouvrira aux tours ≥ 2 avec E05US010.
        place = match.tour == 1
        cible_haut = self._cible_de(match.haut, cibles) if place else None
        cible_bas = self._cible_de(match.bas, cibles) if place else None
        cible_attribuee = cible_haut is not None and cible_bas is not None
        sources = self._sources_en_attente(match)
        return DuelAVenir(
            numero=match.numero,
            tour=match.tour,
            haut=self._saisie_duels.duelliste(match.haut, lignes),
            bas=self._saisie_duels.duelliste(match.bas, lignes),
            participants_connus=participants_connus,
            cible_haut=cible_haut,
            cible_bas=cible_bas,
            cible_attribuee=cible_attribuee,
            sources_en_attente=sources,
            pret_a_lancer=participants_connus and cible_attribuee,
            blocage=self._blocage(participants_connus, cible_attribuee, sources),
        )

    @staticmethod
    def _cible_de(participant: Participant | None, cibles: dict[int, int]) -> int | None:
        """La cible attribuée à l'occupant d'un camp (individuel), ou `None` (vide / équipe / pas
        placé). Les équipes sont hors périmètre (E13US002), sans cible ici."""
        if participant is None or participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        return cibles.get(participant.ref_id)

    # DETTE-019 : corps identique à `ServiceRoutage._sources_en_attente` (E04US018).
    @staticmethod
    def _sources_en_attente(match: Match) -> tuple[int, ...]:
        """Numéros des duels **amont** dont ce match attend encore l'issue — pour nommer le blocage.

        Un camp `VainqueurDe(n)` / `PerdantDe(n)` **sans occupant** signale que le duel `n` n'est
        pas encore tranché (« le n°3 non validé » du CA). Un camp `TeteDeSerie` / `Exempt` (tour 1)
        vient du classement : il n'attend aucune source.
        """
        pending: list[int] = []
        for source, occupant in (
            (match.source_haut, match.haut),
            (match.source_bas, match.bas),
        ):
            if occupant is None and isinstance(source, VainqueurDe | PerdantDe):
                pending.append(source.numero)
        return tuple(pending)

    @staticmethod
    def _blocage(
        participants_connus: bool, cible_attribuee: bool, sources: tuple[int, ...]
    ) -> str | None:
        """Le motif de blocage **nommé** (CA), ou `None` si le duel est prêt à lancer.

        Priorité au blocage amont : sans les deux occupants, la cible n'a de toute façon aucun sens.
        """
        if not participants_connus:
            if sources:
                numeros = ", ".join(f"n°{numero}" for numero in sources)
                return f"en attente du duel {numeros}"
            return "adversaire non déterminé"
        if not cible_attribuee:
            return "cible non attribuée"
        return None
