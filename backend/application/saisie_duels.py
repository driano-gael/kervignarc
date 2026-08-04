"""Service applicatif Saisie en duels — scorer un match du tableau (E04US013, ADR-0049).

Assemble ce que le domaine tient séparé : le **classement** (source d'ensemencement), l'**arbre**
d'élimination (`construire_tableau`, qui donne l'appariement), le **résolveur de barème** (par arme)
et l'agrégat **`Duel`** (le scoring). Le tableau n'est **pas** persisté (ADR-0023/0048) : il est
**reconstruit** du classement et **rejoué** des duels validés (`Tableau.jouer`) ; seul le **tir**
est persisté (`DuelRepository`). Le vainqueur d'un duel validé fait donc **avancer** le tableau à la
reconstruction suivante — c'est le sens de « transmis au moteur E05US005 ».

MVP (ADR-0049) : **ensemencement scratch**, tableau **tournoi-large** (les tableaux par catégorie
sont downstream). Le barème (et les zones du pavé) est résolu **par duel** depuis l'arme du **camp
haut** — en tableau par division les deux duellistes partagent la catégorie, donc la même arme ;
le bracket mixte-armes du MVP prend celle du haut (hypothèse d'homogénéité assumée). Résolveur FFTA
par défaut (cumul en poulies, sets sinon) ; E01US011 branchera les catalogues configurables au même
point d'injection. Les `Participant` de genre **équipe** sont ignorés (pas d'entité avant E13US002).
Le pont `Participant → archer` (nom, catégorie, blason) vit ici (couche haute, ADR-0028).
"""

from __future__ import annotations

from dataclasses import dataclass

from application.classements import ServiceClassement
from application.erreurs import (
    BlasonIntrouvable,
    DuelDesynchronise,
    PhaseIntrouvable,
    PhasePasUnTableau,
    TournoiIntrouvable,
)
from application.prelevement import preleves, profondeur_de
from domain.blason import ZoneScore
from domain.classement import LigneClassement
from domain.duel import BaremeDuel, Cote, Duel, ResolveurBaremeDuel
from domain.erreurs import MatchNonJouable
from domain.participant import GenreParticipant, Participant
from domain.phase import PhaseId, TypePhase
from domain.politiques import Byes, RegistrePolitiques, Routing, Seeding
from domain.ports import (
    BlasonRepository,
    CategorieRepository,
    DuelRepository,
    ForfaitRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tableau import Match, Tableau, construire_tableau, libelle_tour
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class Duelliste:
    """Un duelliste **résolu** pour l'affichage : son archer et son nom (depuis le classement)."""

    archer_id: int
    nom: str
    prenom: str


@dataclass(frozen=True)
class EtatDuel:
    """L'état d'un match du tableau : son câblage, ses occupants résolus et son tir (`duel`).

    `duel` est `None` tant qu'aucun tir n'y est saisi ; sinon il porte manches, barrage et résultat
    (`duel.resultat`). `est_bye` marque un match gagné d'office (pas de duel à saisir).

    `bareme` et `zones` dimensionnent le **pavé de saisie** du front (nombre de manches, de flèches,
    zones légales du blason tiré — E04US002 les expose déjà pour la qualif) : disponibles dès qu'un
    match est **jouable** (deux occupants connus, pas un bye), **avant** tout tir, pour que la
    grille sache d'emblée sets ou cumul. `bareme` est `None` et `zones` vide pour un bye ou un
    match dont les occupants ne sont pas encore connus.
    """

    numero: int
    tour: int
    place_en_jeu: tuple[int, int] | None
    haut: Duelliste | None
    bas: Duelliste | None
    est_bye: bool
    duel: Duel | None
    bareme: BaremeDuel | None = None
    zones: tuple[ZoneScore, ...] = ()
    plage: tuple[int, int] | None = None
    """La **branche** du match — `[1..8]` pour le tableau principal, `[5..8]` pour le sous-tableau
    de placement qui en descend (E07US005).

    Distincte de `place_en_jeu`, et c'est **tout l'intérêt** : `place_en_jeu` n'existe que sur les
    matchs **terminaux**, si bien qu'un match des places 5-8 disputé au tour d'une demi-finale
    n'avait, avant cette US, aucun champ qui le distinguât d'une demi-finale. Tout consommateur
    qui nommait ce match par son seul numéro de tour l'appelait « Demi-finale ». C'est ce que
    `libelle` ci-dessous corrige — et pourquoi la plage doit remonter jusqu'ici."""
    libelle: str = ""
    """Le nom que la salle donne au match, calculé par `domain.tableau.libelle_tour`.

    Porté par l'application plutôt que recalculé par chaque surface : c'est du **vocabulaire
    métier** (règle 3), il n'a qu'un domicile légitime, le domaine (`DETTE-020`)."""


@dataclass(frozen=True)
class EtatTableau:
    """La photo du tableau reconstruit : ses matchs (avec tir), son podium acquis, sa complétude.

    `phase_id` a été ajouté par E01US024 : sans lui, tout appelant qui reçoit **plusieurs** tableaux
    devait les rapparier à leurs phases **par position** — or `_tableaux` (pilotage de simulation)
    **saute** une phase non encore jouable, ce qui décalait silencieusement toute la suite. Un
    identifiant porté par la donnée supprime la classe entière de ces bugs d'appariement.
    """

    phase_id: PhaseId
    effectif: int
    taille: int
    nb_tours: int
    est_termine: bool
    duels: tuple[EtatDuel, ...]
    podium: tuple[tuple[int, Duelliste], ...]


class ServiceSaisieDuels:
    """Cas d'usage de la saisie en duels : consulter le tableau, saisir un duel, le valider."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        duels: DuelRepository,
        forfaits: ForfaitRepository,
        classements: ServiceClassement,
        resolveur: ResolveurBaremeDuel,
        seeding: Seeding,
        byes: Byes,
        routing: Routing,
        registre: RegistrePolitiques,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._categories = categories
        self._blasons = blasons
        self._duels = duels
        self._forfaits = forfaits
        self._classements = classements
        self._resolveur = resolveur
        # Politiques du tableau (E05US003) : le format est de la configuration (règle 2). MVP =
        # défauts (serpent / byes aux mieux classés / élimination sèche), comme le plan de duels.
        self._seeding = seeding
        self._byes = byes
        self._routing = routing
        # Profondeur lue **sur la phase** depuis E06US006 (`profondeur_de`), comme le plan de
        # duels : les deux montent le même arbre, ils ne peuvent pas le tronquer différemment.
        self._registre = registre

    # --- Lecture -------------------------------------------------------------------------------

    def etat_tableau(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatTableau:
        """Reconstruit le tableau (duels validés rejoués) et renvoie ses matchs + podium."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        duels = tuple(
            self._etat_du_match(m, phase_id, lignes, tableau.nb_tours) for m in tableau.matchs
        )
        podium = tuple(
            (place.rang, duelliste)
            for place in tableau.podium()
            if (duelliste := self._duelliste(place.participant, lignes)) is not None
        )
        return EtatTableau(
            phase_id=phase_id,
            effectif=tableau.effectif,
            taille=tableau.taille,
            nb_tours=tableau.nb_tours,
            est_termine=tableau.est_termine,
            duels=duels,
            podium=podium,
        )

    def etat_duel(self, tournoi_id: TournoiId, phase_id: PhaseId, match_numero: int) -> EtatDuel:
        """L'état d'un match précis (câblage, occupants, tir). `MatchIntrouvable` si rang absent."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        return self._etat_du_match(tableau.match(match_numero), phase_id, lignes, tableau.nb_tours)

    def reconstruire(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> tuple[Tableau, dict[int, LigneClassement]]:
        """Reconstruit le tableau (duels validés **rejoués**, forfaits **appliqués**) pour un
        lecteur externe — le **pilotage du tour** (E12US002, feu vert) — avec le classement (noms).

        Même décor que la saisie (`_decor`), simplement **exposé en lecture** : le pilotage a besoin
        du `Tableau` brut (occupants connus, vainqueurs propagés, câblage des sources) pour dire,
        par duel à venir, ce qui manque avant de lancer. On ne duplique donc pas la reconstruction —
        une
        seule source de vérité de la progression, comme la saisie et le placement partagent l'arbre.
        Mêmes gardes que `_decor` (`TournoiIntrouvable` / `PhaseIntrouvable` / `PhasePasUnTableau`).
        """
        return self._decor(tournoi_id, phase_id)

    def duelliste(
        self, participant: Participant | None, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom du classement), pour un lecteur externe.

        Expose la même résolution que la saisie applique à ses propres occupants (le pilotage
        affiche les mêmes noms) — `None` pour un camp vide ou une équipe (hors périmètre, E13US002).
        """
        return self._duelliste(participant, lignes)

    # --- Écritures (via la file) ---------------------------------------------------------------

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        match_numero: int,
        numero: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> EtatDuel:
        """Saisit (ou réédite) une manche d'un match : les deux volées opposées."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        zones = self._zones_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.saisir_manche(
            numero,
            valeurs_haut,
            valeurs_bas,
            zones_admises=zones,
            nb_fleches_par_volee=bareme.nb_fleches_par_volee,
        )
        self._duels.enregistrer(phase_id, match_numero, duel)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    def saisir_barrage(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        match_numero: int,
        fleche_haut: ZoneScore,
        fleche_bas: ZoneScore,
        gagnant_designe: Cote | None = None,
    ) -> EtatDuel:
        """Saisit le tir de barrage d'un match à égalité (§8.2)."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        zones = self._zones_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.saisir_barrage(
            fleche_haut, fleche_bas, zones_admises=zones, gagnant_designe=gagnant_designe
        )
        self._duels.enregistrer(phase_id, match_numero, duel)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    def valider(
        self, tournoi_id: TournoiId, phase_id: PhaseId, match_numero: int, scoreur: str
    ) -> EtatDuel:
        """Valide un match **tranché** au nom du scoreur : son vainqueur avancera le tableau."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.valider(scoreur)
        self._duels.enregistrer(phase_id, match_numero, duel)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    # --- Interne : reconstruction du décor (classement → arbre → rejeu des duels validés) -------

    def _decor(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> tuple[Tableau, dict[int, LigneClassement]]:
        """Valide les gardes puis reconstruit l'arbre, duels validés **rejoués** (progression)."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.tournoi_id != tournoi_id:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.ELIMINATION_DIRECTE:
            raise PhasePasUnTableau(
                f"La phase {phase_id} n'est pas une élimination directe : pas de duels."
            )
        classement = self._classements.pour_tournoi(tournoi_id)
        lignes = {ligne.archer_id: ligne for ligne in classement.lignes}
        # Ensemencement : **seuls les archers en lice** entrent dans le tableau. Un forfait déclaré
        # en **qualification** (abandon relégué / DSQ exclu, `statut != EN_LICE`) n'accède pas aux
        # duels ; son rang scratch peut d'ailleurs être `None` (DSQ). Le classement complet reste
        # dans `lignes` pour résoudre les noms.
        participants = [
            Participant.individuel(ligne.archer_id)
            for ligne in preleves(phase, classement, self._ordre_de_la_qualification(tournoi_id))
        ]
        tableau = construire_tableau(
            participants,
            self._seeding,
            self._byes,
            self._routing,
            profondeur_de(phase, self._registre),
        )
        tableau = self._rejouer(tableau, phase_id, lignes)
        return self._appliquer_forfaits(tableau, phase_id), lignes

    def _ordre_de_la_qualification(self, tournoi_id: TournoiId) -> int | None:
        """L'`ordre` de la phase de qualification — le seul classement que ce service lit.

        `None` si le tournoi n'en a pas : aucune source n'est alors honorée, et le tableau
        retombe sur tous les archers en lice. C'est le cas des décors de test montés sans
        qualification, et celui d'un tournoi dont la séquence commence autrement.
        """
        qualification = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        return qualification.ordre if qualification is not None else None

    def _appliquer_forfaits(self, tableau: Tableau, phase_id: PhaseId) -> Tableau:
        """Fait **passer l'adversaire** de tout duelliste déclaré forfait **dans cette phase de
        tableau** (E04US015 / ADR-0050, ex-E12US004).

        Un forfait en duels est un **walkover** : l'archer garde ses duels déjà validés (rejoués
        avant), mais tout match **jouable et non encore tranché** où il figure est gagné d'office
        par son adversaire — analogue à la résolution d'un bye. On traite par **tour croissant**
        (un tour ≥ 2 n'a ses occupants qu'après propagation amont). L'annulation du forfait fait
        **disparaître** le walkover à la reconstruction suivante (réversibilité, `D-15`). Deux
        forfaits face à face (rare) : le camp **haut** avance par convention — lui-même walkover
        en aval s'il reste forfait. Les forfaits de **qualification** ne passent pas ici : leurs
        archers ne sont pas dans le tableau (exclus à l'ensemencement).
        """
        forfaits = {f.archer_id for f in self._forfaits.par_phase(phase_id)}
        if not forfaits:
            return tableau
        for numero in sorted(
            (m.numero for m in tableau.matchs), key=lambda n: tableau.match(n).tour
        ):
            match = tableau.match(numero)
            if (
                match.est_bye
                or match.haut is None
                or match.bas is None
                or match.vainqueur is not None
            ):
                continue
            haut_forfait = match.haut.ref_id in forfaits
            bas_forfait = match.bas.ref_id in forfaits
            if haut_forfait and not bas_forfait:
                tableau = tableau.jouer(numero, match.bas)
            elif (bas_forfait and not haut_forfait) or (haut_forfait and bas_forfait):
                tableau = tableau.jouer(numero, match.haut)
        return tableau

    def _rejouer(
        self, tableau: Tableau, phase_id: PhaseId, lignes: dict[int, LigneClassement]
    ) -> Tableau:
        """Rejoue les duels **validés** dans l'ordre des tours pour peupler les tours ≥ 2.

        Un tour ≥ 2 ne connaît ses occupants qu'une fois les vainqueurs amont propagés : on traite
        donc les matchs **par tour croissant**. On ne rejoue qu'un duel **validé** (officiel) et
        tranché — un tir non validé n'avance pas le tableau (comme le cumul de qualif ne compte que
        le validé). Un tir dont les **duellistes enregistrés divergent** des occupants (le
        classement a changé depuis) est **ignoré**, jamais rejoué pour d'autres archers (ADR-0049
        §4) ; un `match_numero` **hors tableau** (effectif rétréci) est écarté avant tout accès.
        """
        numeros = self._duels.numeros_enregistres(phase_id)
        valides = {m.numero for m in tableau.matchs}
        for numero in sorted(numeros & valides, key=lambda n: tableau.match(n).tour):
            match = tableau.match(numero)
            if match.est_bye or match.haut is None or match.bas is None:
                continue
            bareme = self._bareme_du(match.haut, lignes)
            duel = self._duels.charger(phase_id, numero, bareme=bareme)
            if duel is None or duel.validee_par is None:
                continue
            if (duel.participant_haut, duel.participant_bas) != (match.haut, match.bas):
                continue  # divergence : le tir oppose d'autres duellistes, on ne le rejoue pas
            vainqueur = duel.vainqueur
            if vainqueur is not None:
                tableau = tableau.jouer(numero, vainqueur)
        return tableau

    # --- Interne : accès à un match / au duel courant ------------------------------------------

    @staticmethod
    def _match_saisissable(
        tableau: Tableau, match_numero: int
    ) -> tuple[Match, Participant, Participant]:
        """Le match et ses deux occupants connus, ou `MatchNonJouable` (bye / adversaires inconnus).

        On **n'exige pas** l'absence de vainqueur : un match déjà validé garde ses occupants et
        c'est l'agrégat `Duel` qui refuse la réécriture (`DuelVerrouille`)."""
        match = tableau.match(match_numero)  # MatchIntrouvable si le rang n'existe pas
        if match.est_bye:
            raise MatchNonJouable(f"Le match {match_numero} est un bye : pas de duel à saisir.")
        if match.haut is None or match.bas is None:
            raise MatchNonJouable(
                f"Les adversaires du match {match_numero} ne sont pas encore connus."
            )
        return match, match.haut, match.bas

    def _duel_courant(
        self,
        phase_id: PhaseId,
        match_numero: int,
        bareme: BaremeDuel,
        haut: Participant,
        bas: Participant,
    ) -> Duel:
        """Le duel persisté du match, ou un duel vierge (première saisie).

        **Refuse** (`DuelDesynchronise`, 409) un tir qui oppose d'**autres** duellistes que
        `(haut, bas)` recalculés : le classement a changé depuis, on n'écrit pas un score sur le
        mauvais couple (ADR-0049 §4). À première saisie (aucun tir), le duel vierge porte les
        occupants courants, qui seront enregistrés.
        """
        duel = self._duels.charger(phase_id, match_numero, bareme=bareme)
        if duel is None:
            return Duel.vide(bareme, haut, bas)
        if (duel.participant_haut, duel.participant_bas) != (haut, bas):
            raise DuelDesynchronise(
                f"Le tir du match {match_numero} oppose d'autres duellistes : le classement a "
                "changé depuis. Régénérez ou rétablissez le classement avant de saisir."
            )
        return duel

    # --- Interne : résolution barème / zones / duelliste ---------------------------------------

    def _bareme_du(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> BaremeDuel:
        """Le barème du duel, résolu par l'**arme** du participant (défaut FFTA, ADR-0049)."""
        return self._resolveur.bareme_pour(self._arme_du(participant, lignes))

    def _arme_du(self, participant: Participant, lignes: dict[int, LigneClassement]) -> str | None:
        """L'arme (texte libre de la catégorie) d'un participant individuel, ou `None`."""
        if participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        categorie = self._categories.par_id(ligne.categorie_id)
        return None if categorie is None else categorie.arme

    def _zones_du(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones admises du blason tiré (le pavé). **Strict** sur le chemin d'écriture : blason
        indéterminable → `BlasonIntrouvable` (404, erreur **visible**, jamais de score faux
        silencieux — même exigence que la grille de qualification, E04US002)."""
        individuel = participant.genre is GenreParticipant.INDIVIDUEL
        ligne = lignes.get(participant.ref_id) if individuel else None
        categorie = None if ligne is None else self._categories.par_id(ligne.categorie_id)
        blason_id = None if categorie is None else categorie.blason_id
        blason = None if blason_id is None else self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable("Blason du duelliste indéterminable : pavé indisponible.")
        return tuple(blason.zones)

    def _zones_best_effort(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones du pavé pour la **lecture** — tolérant, jumeau de `_zones_du`.

        Sur le chemin d'**écriture**, un blason indéterminable lève `BlasonIntrouvable` (404, jamais
        de score faux silencieux). En **lecture**, il ne doit pas faire échouer tout le tableau : on
        renvoie un pavé **vide** (le front affiche « pavé indisponible » sur ce match), exactement
        comme la grille de qualification renvoie des zones vides plutôt qu'un 404 (E04US002).
        """
        try:
            return self._zones_du(participant, lignes)
        except BlasonIntrouvable:
            return ()

    def _duelliste(
        self, participant: Participant | None, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom du classement), ou `None` (vide / équipe)."""
        if participant is None or participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        return Duelliste(archer_id=participant.ref_id, nom=ligne.nom, prenom=ligne.prenom)

    def _etat_du_match(
        self,
        match: Match,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
        nb_tours: int,
        *,
        duel: Duel | None = None,
    ) -> EtatDuel:
        """Assemble l'`EtatDuel` d'un match ; charge son tir au besoin (si le match a un duel).

        Un tir dont les duellistes enregistrés **divergent** des occupants recalculés (classement
        changé) est **masqué** (`duel=None`) : le match s'affiche non joué plutôt que de prêter un
        score au mauvais couple (ADR-0049 §4).
        """
        haut, bas = match.haut, match.bas
        bareme: BaremeDuel | None = None
        zones: tuple[ZoneScore, ...] = ()
        if haut is not None and bas is not None and not match.est_bye:
            # Match jouable : le pavé est déterminé (barème par arme + zones du blason), même avant
            # tout tir — la grille front sait d'emblée sets/cumul, nb de manches et zones légales.
            bareme = self._bareme_du(haut, lignes)
            zones = self._zones_best_effort(haut, lignes)
            if duel is None:
                charge = self._duels.charger(phase_id, match.numero, bareme=bareme)
                if (charge is not None) and (
                    (charge.participant_haut, charge.participant_bas) == (haut, bas)
                ):
                    duel = charge
        return EtatDuel(
            numero=match.numero,
            tour=match.tour,
            place_en_jeu=match.place_en_jeu,
            haut=self._duelliste(match.haut, lignes),
            bas=self._duelliste(match.bas, lignes),
            est_bye=match.est_bye,
            duel=duel,
            bareme=bareme,
            zones=zones,
            plage=None if match.plage is None else (match.plage.debut, match.plage.fin),
            libelle=libelle_tour(match.tour, nb_tours, match.place_en_jeu, match.plage),
        )
