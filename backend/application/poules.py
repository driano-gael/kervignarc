"""Service applicatif **Poules** — composer, poser, faire tirer et classer (E05US023, [ADR-0083]).

C'est le consommateur de production qui manquait à `domain/poule.py` depuis E05US015 : le moteur
existait, testé, et **personne ne l'appelait** (`DETTE-028`). Ce service assemble ce que le domaine
tient séparé — le **classement source** (`application/prelevement.py`), la **composition** en
groupes (`composer_poules`), le **placement** en blocs de couloirs (`placer_les_poules`), les
**rencontres** (`rencontres_de_poule`), le **classement de poule** (`classement_de_poule`) et le
**barrage** (`domain/barrage.py`, déjà opérationnel en portée `poule` depuis E06US003).

## Ce qui est recalculé, ce qui est persisté

Le parti est celui du tableau (ADR-0023/0048), et pour la même raison : **la structure se recalcule,
le tir se persiste**.

- **Recalculé à chaque lecture** : la composition (qui est dans quelle poule), les rencontres et
  leur ordre, les couloirs de chaque rencontre tour par tour, le classement de poule. Tout cela est
  une fonction déterministe du classement source et du réglage — le persister créerait une seconde
  vérité, périmée dès qu'une volée en retard est validée.
- **Persisté** : le **bloc de couloirs** de chaque poule (`placement_poule`, migration 0045) et le
  **tir** de chaque rencontre (table `duel`, sans table ni migration neuve — ADR-0083 §7).

## La numérotation des rencontres, et son ancrage

Une rencontre est un **duel ordinaire** : elle se saisit avec le pavé d'E04US013 et se range dans
`duel`, keyée `(phase_id, match_numero)`. Le `match_numero` est attribué **déterministe** — poules
dans l'ordre, rencontres dans l'ordre que la méthode du cercle produit, numérotation continue depuis
1. Même hypothèse que l'arbre d'un tableau, et **le même garde-fou** : le tir enregistre l'identité
de ses deux duellistes, si bien qu'une composition changée (un forfait, une volée validée en retard)
fait **détecter** la divergence au lieu de ré-attribuer un score à d'autres (ADR-0049 §4).

⚠️ **Ce garde-fou masque, il ne répare pas.** Un score dont les duellistes ne correspondent plus
s'affiche « non tiré » — ce qui est le comportement voulu, mais qui reste une perte visible pour le
scoreur. En salle, recomposer une phase de poules déjà entamée n'est donc pas une opération
anodine ; le CA ne l'offre pas, et rien ici ne la facilite.

## Coût d'exécution

La composition relit le classement source, donc hérite de `DETTE-031` (reconstruction non
mémoïsée). La mémoïsation **à l'intérieur d'un appel** suit le parti d'E05US024 — le cache est créé
au sommet et descendu — ; le cache transverse aux requêtes n'est pas rouvert ici.

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from application.classements import ServiceClassement
from application.erreurs import (
    GabaritDuTournoiAbsent,
    PhaseIntrouvable,
    PhasePasDesPoules,
    PhasePasReglee,
    RencontreIntrouvable,
    TournoiIntrouvable,
)
from application.portee import phase_du_tournoi
from application.prelevement import preleves
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.barrage import PorteeBarrage
from domain.blason import ZoneScore
from domain.classement import LigneClassement
from domain.contrat_phase import TypePhase
from domain.duel import BaremeDuel, Cote, Duel, ModeDuel
from domain.erreurs import BarrageRequisAvantQualification, MatchNonJouable
from domain.participant import GenreParticipant, Participant
from domain.phase import Phase, PhaseId
from domain.placement_poules import (
    BlocDePoule,
    ConflitDePoule,
    RaisonConflitPoule,
    placer_les_poules,
)
from domain.ports import (
    BarrageRepository,
    DuelRepository,
    GabaritSalleRepository,
    PhaseRepository,
    PlacementPouleRepository,
    TournoiRepository,
)
from domain.poule import (
    ConfigurationPoules,
    Poule,
    RangPoule,
    RencontrePoule,
    ResultatRencontre,
    classement_de_poule,
    composer_poules,
    qualifies_de_poule,
    rencontres_de_poule,
)
from domain.serie import Volee
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class RepartitionPoules:
    """Ce que le réglage produit sur l'effectif réel — le CA « la répartition est montrée ».

    `tailles` porte l'effectif de chaque groupe, dans l'ordre. C'est ce qui rend l'arrondi
    **lisible** plutôt que surprenant : 30 archers en poules de 4 donnent 7 poules, cinq de 4 et
    deux de 5, et l'organisateur le voit avant de valider. C'est aussi ce qui rend inoffensif le cas
    extrême — 7 archers en poules de 4 donnent **une** poule de 7, que l'écran montre et qu'il
    corrige s'il n'en veut pas (`nb_poules_pour`).
    """

    effectif: int
    taille_visee: int
    tailles: tuple[int, ...]

    @property
    def nb_poules(self) -> int:
        return len(self.tailles)


@dataclass(frozen=True)
class RencontreAffichee:
    """Une rencontre de poule, prête pour le pavé de saisie d'E04US013.

    `numero` est le `match_numero` de la table `duel` : c'est par lui que la saisie écrit, et il est
    **dérivé** de la composition, jamais stocké. `couloirs` porte les deux couloirs que les
    adversaires occupent à ce tour — dérivés du bloc, comme l'appariement d'un tableau.

    `duel` vaut `None` tant qu'aucun tir n'est saisi **ou** si le tir enregistré ne correspond plus
    aux deux adversaires recalculés (ADR-0049 §4).
    """

    numero: int
    poule: int
    tour: int
    haut: Duelliste | None
    bas: Duelliste | None
    couloirs: tuple[tuple[int, str], tuple[int, str]] | None
    duel: Duel | None
    bareme: BaremeDuel | None
    zones: tuple[ZoneScore, ...]


@dataclass(frozen=True)
class PouleAffichee:
    """Une poule : ses membres, son bloc, ses rencontres par tour, son classement.

    `barrage_requis` porte le **régime d'ex æquo** d'ADR-0083 §5, et c'est le seul champ dont le
    sens dépende du réglage :

    - la poule **classe** (`nb_qualifies` non déclaré) — le classement *est* le livrable, donc
      **tout** ex æquo irréductible se départage ;
    - la poule **qualifie** — seul le franchissement de la barre compte : deux archers à égalité aux
      rangs 3-4 d'une poule qui en qualifie 2 restent à égalité, et l'outil ne les départage pas.
    """

    numero: int
    membres: tuple[Duelliste, ...]
    bloc: BlocDePoule | None
    rencontres: tuple[RencontreAffichee, ...]
    classement: tuple[RangPoule, ...]
    qualifies: tuple[Duelliste, ...]
    barrage_requis: bool


@dataclass(frozen=True)
class EtatPoules:
    """La photo d'une phase de poules : sa répartition, ses groupes, ce qui n'a pas pu être posé."""

    phase_id: PhaseId
    repartition: RepartitionPoules
    poules: tuple[PouleAffichee, ...]
    conflits: tuple[ConflitDePoule, ...]


class ServicePoules:
    """Cas d'usage des poules : consulter une phase, poser son plan, saisir ses rencontres.

    **Ce qui est partagé avec `ServiceSaisieDuels` l'est réellement** : l'agrégat `Duel`, le pavé
    (`bareme_de` / `zones_de` / `zones_strictes`) et la table `duel`. Une rencontre de poule *est*
    un duel ordinaire (ADR-0083 §7), et la faire écrire autrement créerait deux façons de saisir un
    tir — l'exacte duplication que cet ADR se donne pour objet de fermer.

    **Ce qui diffère est la navigation** : là-bas on retrouve un match dans un arbre, ici une
    rencontre dans un groupe. C'est le `decor` du contrat (la 2ᵉ question), et c'est tout ce que les
    trois méthodes de saisie ci-dessous réimplémentent.
    """

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        gabarits: GabaritSalleRepository,
        placements: PlacementPouleRepository,
        duels: DuelRepository,
        barrages: BarrageRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._gabarits = gabarits
        self._placements = placements
        self._duels = duels
        self._barrages = barrages
        self._classements = classements
        # ⚠️ **Pas pour saisir** — uniquement pour emprunter sa résolution de classement amont et
        # sa résolution de pavé (barème par arme, zones du blason). Même parti que
        # `ServicePlacementDuels`, et le sens de dépendance est sûr : `saisie_duels` ne connaît pas
        # les poules. L'alternative — recopier `resolveur_de_classement` ici — est exactement ce
        # qu'`application/prelevement.py` existe pour empêcher.
        self._saisie_duels = saisie_duels

    # --- Lecture ---------------------------------------------------------------------------------

    def repartition(self, tournoi_id: TournoiId, phase_id: PhaseId) -> RepartitionPoules:
        """Ce que le réglage produit sur l'effectif **réel**, sans rien poser ni écrire.

        C'est ce que l'atelier affiche en direct sous la fiche de réglages (« 30 archers → 7
        poules : cinq de 4, deux de 5 »). Volontairement séparé d'`etat` : montrer la répartition ne
        doit exiger ni gabarit de salle, ni plan posé, ni le moindre tir — sans quoi l'organisateur
        ne pourrait pas régler ses poules avant d'avoir fait sa salle.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._repartition(phase, len(participants))

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatPoules:
        """La photo complète : composition, plan posé, rencontres tirées, classements.

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasDesPoules` ou
        `PhasePasReglee` (409).
        """
        phase, participants = self._population(tournoi_id, phase_id)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        configuration = self._configuration(phase, len(participants))
        poules = composer_poules(
            [Participant.individuel(ligne.archer_id) for ligne in participants], configuration
        )
        blocs = {bloc.poule: bloc for bloc in self._placements.par_phase(phase_id)}
        conflits = self._conflits_du_plan(poules, blocs)
        # La numérotation est **continue sur toute la phase**, poule après poule : c'est ce qui
        # permet à la table `duel` de porter les rencontres de tous les groupes sans les distinguer,
        # donc de réutiliser `(phase_id, match_numero)` tel quel — aucune table, aucune migration.
        numero = 0
        affichees: list[PouleAffichee] = []
        verdicts = self._verdicts_de_barrage(phase)
        for poule in poules:
            rencontres: list[RencontreAffichee] = []
            # La **position dans le tour** décide des couloirs (la n-ième rencontre d'un tour prend
            # les couloirs 2n et 2n+1 du bloc). Elle se compte par tour, et non sur la poule
            # entière : au tour 2, la première rencontre doit retrouver les couloirs qu'occupait la
            # première rencontre du tour 1, sans quoi la poule glisserait d'un cran à chaque tour et
            # déborderait de son propre bloc.
            position = 0
            tour_courant = 0
            for rencontre in rencontres_de_poule(poule, configuration):
                if rencontre.tour != tour_courant:
                    tour_courant, position = rencontre.tour, 0
                numero += 1
                rencontres.append(
                    self._rencontre_affichee(
                        numero,
                        rencontre,
                        phase_id,
                        lignes,
                        blocs.get(poule.numero),
                        position,
                    )
                )
                position += 1
            affichees.append(
                self._poule_affichee(poule, rencontres, configuration, lignes, blocs, verdicts)
            )
        return EtatPoules(
            phase_id=phase_id,
            repartition=self._repartition(phase, len(participants)),
            poules=tuple(affichees),
            conflits=conflits,
        )

    # --- Saisie d'une rencontre (via la file) ----------------------------------------------------
    #
    # ⚠️ **Trois méthodes qui ressemblent à celles de `ServiceSaisieDuels`, et l'écart est
    # exactement le sujet d'ADR-0083.** Ce qui est partagé — l'agrégat `Duel`, le pavé
    # (`bareme_de` / `zones_de`), la table `duel` — l'est *réellement* : une rencontre de poule
    # **est** un duel ordinaire (§6). Ce qui diffère est la **navigation** : là-bas on retrouve un
    # match dans un arbre, ici une rencontre dans un groupe. C'est le `decor` du contrat, la 2ᵉ
    # question, et c'est la seule chose que ces trois méthodes réimplémentent.
    #
    # L'alternative — élargir `ServiceSaisieDuels` à un second décor — a été écartée : son `_decor`
    # rend un `Tableau`, type qu'une poule n'a pas, et l'y ouvrir demanderait de rendre le tableau
    # facultatif dans un service dont **toutes** les méthodes s'en servent. On aurait échangé une
    # duplication de trente lignes contre un service à deux modes, ce qui est le pire des deux.

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        manche: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> RencontreAffichee:
        """Saisit une manche d'une rencontre — même agrégat, même contrôle qu'un duel de tableau."""
        return self._ecrire(
            tournoi_id,
            phase_id,
            numero,
            lambda duel, bareme, zones: duel.saisir_manche(
                manche,
                valeurs_haut,
                valeurs_bas,
                zones_admises=zones,
                nb_fleches_par_volee=bareme.nb_fleches_par_volee,
            ),
        )

    def saisir_barrage(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        fleche_haut: ZoneScore,
        fleche_bas: ZoneScore,
        gagnant_designe: Cote | None = None,
    ) -> RencontreAffichee:
        """Saisit le tir de barrage **interne** à une rencontre nulle (§8.2).

        ⚠️ **À ne pas confondre avec le barrage de poule** (`domain/barrage.py`, portée `POULE`),
        qui départage des ex æquo *du classement*. Celui-ci tranche une **rencontre** nulle, et
        c'est le barrage d'E04US013 — la même distinction qu'entre le barrage d'un duel de tableau
        et le barrage de places d'E06US003.
        """
        return self._ecrire(
            tournoi_id,
            phase_id,
            numero,
            lambda duel, _bareme, zones: duel.saisir_barrage(
                fleche_haut, fleche_bas, zones_admises=zones, gagnant_designe=gagnant_designe
            ),
        )

    def valider(
        self, tournoi_id: TournoiId, phase_id: PhaseId, numero: int, scoreur: str
    ) -> RencontreAffichee:
        """Valide une rencontre tranchée : c'est elle qui entrera au classement de la poule.

        Seules les rencontres **validées** alimentent `classement_de_poule` — un tir en cours de
        saisie ferait bouger le classement à chaque flèche, et le barrage requis apparaîtrait puis
        disparaîtrait sous les yeux du juge.
        """
        return self._ecrire(
            tournoi_id, phase_id, numero, lambda duel, _bareme, _zones: duel.valider(scoreur)
        )

    def _ecrire(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        appliquer: Callable[[Duel, BaremeDuel, tuple[ZoneScore, ...]], Duel],
    ) -> RencontreAffichee:
        """Le tronc commun des trois écritures : retrouver la rencontre, appliquer, persister.

        La rencontre est retrouvée **par recomposition**, jamais par une lecture de la table
        `duel` : c'est ce qui garantit que le tir écrit porte les deux adversaires que la
        composition du moment désigne. Écrire depuis la ligne persistée reviendrait à se fier à un
        `match_numero` qui a pu changer de sens — précisément ce que l'ancrage d'ADR-0049 §4 sert
        à détecter.
        """
        etat = self.etat(tournoi_id, phase_id)
        rencontre = next(
            (r for poule in etat.poules for r in poule.rencontres if r.numero == numero), None
        )
        if rencontre is None:
            raise RencontreIntrouvable(
                f"Aucune rencontre {numero} dans la phase de poules {phase_id}."
            )
        if rencontre.haut is None or rencontre.bas is None or rencontre.bareme is None:
            raise MatchNonJouable(
                f"La rencontre {numero} n'a pas deux adversaires résolus : rien à y saisir."
            )
        haut = Participant.individuel(rencontre.haut.archer_id)
        bas = Participant.individuel(rencontre.bas.archer_id)
        # Les zones sont relues en **strict** ici (chemin d'écriture) : un blason indéterminable
        # doit lever plutôt que produire un pavé vide, sinon on enregistrerait un score dont on ne
        # sait pas s'il est légal (même exigence qu'E04US002).
        zones = self._saisie_duels.zones_strictes(haut, self._lignes(phase_id))
        courant = rencontre.duel or Duel.vide(rencontre.bareme, haut, bas)
        duel = appliquer(courant, rencontre.bareme, zones)
        self._duels.enregistrer(phase_id, numero, duel)
        return replace(rencontre, duel=duel)

    def _lignes(self, phase_id: PhaseId) -> dict[int, LigneClassement]:
        """Le classement du départ de cette phase, indexé par archer — pour résoudre le blason."""
        phase = self._phases.par_id(phase_id)
        assert phase is not None, "`etat` a déjà refusé une phase inconnue."
        return {
            ligne.archer_id: ligne
            for ligne in self._classements.pour_depart(phase.depart_id).lignes
        }

    # --- Écriture du plan (via la file) ----------------------------------------------------------

    def regenerer_plan(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatPoules:
        """Pose les poules sur la salle et **remplace** le plan existant.

        Le geste est volontairement grossier — on repose tout — parce que l'unité déplaçable est la
        **poule** et que la contiguïté de son bloc est l'invariant du format. Reposer après un
        changement d'effectif est donc sûr, à ceci près que les tirs déjà saisis se retrouvent
        éventuellement rattachés à d'autres adversaires : c'est précisément ce qu'ADR-0049 §4
        détecte, et ce que l'écran affiche « non tiré » plutôt que d'attribuer à tort.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )
        configuration = self._configuration(phase, len(participants))
        poules = composer_poules(
            [Participant.individuel(ligne.archer_id) for ligne in participants], configuration
        )
        plan = placer_les_poules(poules, gabarit)
        self._placements.definir_plan(phase_id, plan.blocs)
        return self.etat(tournoi_id, phase_id)

    # --- Rouages ---------------------------------------------------------------------------------

    def _population(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> tuple[Phase, list[LigneClassement]]:
        """Les gardes, puis **qui entre dans la phase** — la 1ʳᵉ question du contrat (ADR-0083 §1).

        Générique depuis ADR-0068/E05US024 : `preleves` lit chaque source dans le classement de
        **sa** phase, en remontant la chaîne. Une phase de poules sans source déclarée est donc
        alimentée par le classement du départ, comme un tableau de tête.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.POULES:
            raise PhasePasDesPoules(f"La phase {phase_id} n'est pas une phase de poules.")
        classement = self._classements.pour_depart(phase.depart_id)
        participants = preleves(
            phase,
            classement,
            self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return phase, participants

    def _repartition(self, phase: Phase, effectif: int) -> RepartitionPoules:
        """La répartition obtenue — les tailles réelles, pas seulement leur nombre."""
        configuration = self._configuration(phase, effectif)
        # On compte les tailles **par le serpent lui-même** plutôt que par une division : c'est le
        # même code qui répartira le jour J, donc l'écran ne peut pas annoncer autre chose que ce
        # qui sera joué. Refaire l'arithmétique ici serait une seconde vérité, et c'est exactement
        # ce genre de doublon qui a produit les dix filtres d'ADR-0083.
        poules = composer_poules(
            [Participant.individuel(rang) for rang in range(1, effectif + 1)], configuration
        )
        reglage = phase.poules
        assert reglage is not None, "`_configuration` a déjà refusé une phase non réglée."
        return RepartitionPoules(
            effectif=effectif,
            taille_visee=reglage.taille_visee,
            tailles=tuple(len(poule.membres) for poule in poules),
        )

    def _configuration(self, phase: Phase, effectif: int) -> ConfigurationPoules:
        """Le réglage de l'atelier, converti sur l'effectif du jour — **en un seul endroit**.

        `ReglageDePoules.pour_effectif` fait la conversion taille → nombre de groupes. Elle n'est
        appelée que d'ici : deux appels indépendants pourraient recevoir deux effectifs différents
        (l'un avant, l'autre après une validation de volée) et monter deux répartitions.
        """
        if phase.poules is None:
            raise PhasePasReglee(
                f"La phase {phase.id} est une phase de poules, mais sa taille de poule n'est pas "
                "réglée : l'organisateur doit la fixer à l'atelier avant de composer."
            )
        return phase.poules.pour_effectif(effectif)

    def _conflits_du_plan(
        self, poules: tuple[Poule, ...], blocs: dict[int, BlocDePoule]
    ) -> tuple[ConflitDePoule, ...]:
        """Les poules composées qu'aucun bloc ne porte — plan non posé, ou salle trop petite.

        ⚠️ **On rapporte le manque, on ne le comble pas.** Poser ici la poule oubliée reviendrait à
        écrire un plan à la lecture, donc à décider du placement dans une méthode dont l'appelant
        croit qu'elle ne fait que lire. `placer_les_poules` a déjà tranché la règle (à la première
        poule qui ne tient pas, on s'arrête et on rapporte le reste) ; on la relaie, on ne la
        rejoue pas.
        """
        return tuple(
            ConflitDePoule(poule.numero, RaisonConflitPoule.NON_POSEE)
            for poule in poules
            if poule.numero not in blocs
        )

    def _rencontre_affichee(
        self,
        numero: int,
        rencontre: RencontrePoule,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
        bloc: BlocDePoule | None,
        position_dans_le_tour: int,
    ) -> RencontreAffichee:
        """Assemble une rencontre : ses adversaires résolus, son pavé, ses couloirs, son tir.

        Le pavé est résolu par **le même code** que celui d'un duel de tableau
        (`ServiceSaisieDuels.bareme_de` / `zones_de`) : une rencontre de poule *est* un duel
        ordinaire, et le même archer ne peut pas tirer en sets d'un côté et en cumul de l'autre.
        """
        a, b = rencontre.a, rencontre.b
        bareme = self._saisie_duels.bareme_de(a, lignes)
        charge = self._duels.charger(phase_id, numero, bareme=bareme)
        # ⚠️ **L'ancrage d'ADR-0049 §4.** Un tir dont les duellistes enregistrés divergent des
        # adversaires recalculés est **masqué**, jamais ré-attribué : la rencontre s'affiche non
        # tirée plutôt que de prêter un score au mauvais couple. Le cas se produit dès qu'une
        # composition change sous un tir déjà saisi — un forfait, une volée validée en retard.
        duel = (
            charge
            if charge is not None and (charge.participant_haut, charge.participant_bas) == (a, b)
            else None
        )
        return RencontreAffichee(
            numero=numero,
            poule=rencontre.poule,
            tour=rencontre.tour,
            haut=self._duelliste(a, lignes),
            bas=self._duelliste(b, lignes),
            couloirs=_couloirs_de_la_rencontre(bloc, position_dans_le_tour),
            duel=duel,
            bareme=bareme,
            zones=self._saisie_duels.zones_de(a, lignes),
        )

    def _poule_affichee(
        self,
        poule: Poule,
        rencontres: list[RencontreAffichee],
        configuration: ConfigurationPoules,
        lignes: dict[int, LigneClassement],
        blocs: dict[int, BlocDePoule],
        verdicts: dict[Participant, int],
    ) -> PouleAffichee:
        """Classe la poule depuis les rencontres **tirées**, puis referme sur le barrage."""
        classement = classement_de_poule(
            poule,
            [
                resultat
                for rencontre in rencontres
                if (resultat := _resultat_de(rencontre)) is not None
            ],
            configuration,
        )
        classement = _appliquer_verdicts(classement, verdicts)
        return PouleAffichee(
            numero=poule.numero,
            membres=tuple(
                duelliste
                for membre in poule.membres
                if (duelliste := self._duelliste(membre, lignes)) is not None
            ),
            bloc=blocs.get(poule.numero),
            rencontres=tuple(rencontres),
            classement=classement,
            qualifies=tuple(
                duelliste
                for participant in _qualifies_sans_lever(classement, configuration)
                if (duelliste := self._duelliste(participant, lignes)) is not None
            ),
            barrage_requis=_barrage_requis(classement, configuration),
        )

    def _verdicts_de_barrage(self, phase: Phase) -> dict[Participant, int]:
        """Les rangs qu'un barrage de portée **poule** a tranchés dans cette phase.

        C'est ce qui « referme le classement » (CA) et ferme la boucle que `DETTE-028` laissait
        ouverte : le moteur de barrage était complet depuis E05US015 et son verdict ne retournait
        dans aucun classement.

        ⚠️ **Les barrages clos comptent**, comme en qualification : ce sont eux qui portent les
        verdicts déjà appliqués. Les filtrer ferait retomber en ex æquo, à la lecture suivante, des
        rangs qu'on a fait tirer.
        """
        rangs: dict[Participant, int] = {}
        for barrage in self._barrages.par_depart(phase.depart_id):
            if barrage.portee is not PorteeBarrage.POULE or barrage.phase_id != phase.id:
                continue
            rangs.update(barrage.verdict().rangs())
        return rangs

    def _duelliste(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom lu au classement), ou `None`."""
        if participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        return Duelliste(archer_id=participant.ref_id, nom=ligne.nom, prenom=ligne.prenom)


def _couloirs_de_la_rencontre(
    bloc: BlocDePoule | None, position_dans_le_tour: int
) -> tuple[tuple[int, str], tuple[int, str]] | None:
    """Les deux couloirs qu'une rencontre occupe — **dérivés** du bloc, jamais persistés.

    La *n*-ième rencontre d'un tour prend les couloirs `2n` et `2n+1` du bloc, donc les deux
    adversaires sont **côte à côte** : c'est la même intention qu'ADR-0048 pour un tableau, obtenue
    ici sans réordonnancement puisque le bloc est contigu par construction.

    Rend `None` si le bloc manque (plan non posé) ou est trop court pour cette position — un plan
    incomplet doit se voir comme incomplet, pas se compléter tout seul.
    """
    if bloc is None:
        return None
    debut = 2 * position_dans_le_tour
    if debut + 1 >= len(bloc.places):
        return None
    return bloc.places[debut], bloc.places[debut + 1]


def _resultat_de(rencontre: RencontreAffichee) -> ResultatRencontre | None:
    """Traduit un tir **validé** en résultat consommable par le moteur de classement.

    ⚠️ **Seuls les duels validés comptent.** Un tir en cours de saisie ferait bouger le classement
    de poule à chaque flèche, et le barrage requis apparaîtrait puis disparaîtrait sous les yeux du
    juge. Même parti que la reconstruction d'un tableau, qui ne rejoue que les duels validés.

    ⚠️ **Le cumul est reporté dans les sets** (limite documentée par `ResultatRencontre`) : un duel
    à l'arc à poulies ne joue pas en manches, et le laisser à 0-0 en ferait un **nul** au sens des
    points de match. C'est ici, où l'on sait qui a gagné, que la conversion est légitime — le
    résultat, lui, ne sait pas qu'il est au cumul.
    """
    duel = rencontre.duel
    if duel is None or not duel.verrouille:
        return None
    resultat = duel.resultat
    haut = _volees(duel, cote_haut=True)
    bas = _volees(duel, cote_haut=False)
    sets_a, sets_b = resultat.points_haut, resultat.points_bas
    if duel.bareme.mode is ModeDuel.CUMUL:
        # ⚠️ Au cumul, `points_*` **est** le total de flèches, pas un nombre de sets : les laisser
        # tels quels ferait compter un écart de 12 points comme 12 sets d'avance, ce que la
        # différence de sets du §10.1 propagerait dans tout le classement. On reporte donc la
        # victoire en 1-0 — la conversion que `ResultatRencontre` documente comme étant à la charge
        # du service, et qui n'est légitime qu'ici, où l'on sait qui a gagné.
        gagnant = resultat.vainqueur
        sets_a, sets_b = (
            (1, 0) if gagnant is Cote.HAUT else (0, 1) if gagnant is Cote.BAS else (0, 0)
        )
    return ResultatRencontre(
        a=duel.participant_haut,
        b=duel.participant_bas,
        sets_a=sets_a,
        sets_b=sets_b,
        # La **différence de score** du §10.1 est un écart de flèches, jamais de points de set :
        # elle se recompte donc sur les volées, dans les deux modes.
        score_a=sum(volee.points for volee in haut),
        score_b=sum(volee.points for volee in bas),
        nb_dix_a=_compter(haut, "10"),
        nb_neuf_a=_compter(haut, "9"),
        nb_dix_b=_compter(bas, "10"),
        nb_neuf_b=_compter(bas, "9"),
    )


def _volees(duel: Duel, *, cote_haut: bool) -> tuple[Volee, ...]:
    """Les volées d'un camp, toutes manches confondues."""
    return tuple(manche.volee_haut if cote_haut else manche.volee_bas for manche in duel.manches)


def _compter(volees: tuple[Volee, ...], zone: str) -> int:
    """Combien de flèches d'une valeur donnée — les 4ᵉ et 5ᵉ critères de départage (§10.1).

    ⚠️ **Le X n'est pas compté comme un 10 ici**, et c'est une limite à connaître : le référentiel
    §10.1 dit « nombre de 10 », sans trancher le sort du X. La qualification, elle, les distingue
    (`domain/classement.py`). Aligner les deux demanderait de savoir laquelle des deux lectures le
    club applique en poule — une question de règle, pas de code, et le CA d'E05US023 ne la pose pas.
    On compte donc littéralement ce que la règle nomme, et l'écart est signalé plutôt que tranché
    ici.
    """
    return sum(1 for volee in volees for valeur in volee.valeurs if valeur == zone)


def _appliquer_verdicts(
    classement: tuple[RangPoule, ...], verdicts: dict[Participant, int]
) -> tuple[RangPoule, ...]:
    """Referme les ex æquo qu'un barrage a tranchés, et **eux seuls**.

    Un participant absent des verdicts garde son rang et son `ex_aequo` : le barrage ne réordonne
    que ce qu'il a fait tirer. Le tri final se refait sur le rang obtenu, pour que l'affichage suive
    le verdict plutôt que l'ordre de composition.
    """
    if not verdicts:
        return classement
    refermes = [
        RangPoule(
            rang=verdicts.get(ligne.participant, ligne.rang),
            participant=ligne.participant,
            decompte=ligne.decompte,
            ex_aequo=ligne.ex_aequo and ligne.participant not in verdicts,
        )
        for ligne in classement
    ]
    return tuple(sorted(refermes, key=lambda ligne: ligne.rang))


def _qualifies_sans_lever(
    classement: tuple[RangPoule, ...], configuration: ConfigurationPoules
) -> tuple[Participant, ...]:
    """Les qualifiés, ou `()` si un barrage doit d'abord trancher la barre.

    `qualifies_de_poule` **lève** dans ce cas (`BarrageRequisAvantQualification`), et c'est le bon
    contrat pour un moteur : il refuse de qualifier sur l'ordre d'affichage. Mais une **lecture
    d'écran** ne peut pas se solder par un 409 — l'organisateur doit voir la poule, son classement
    et le barrage à faire tirer. On rattrape donc ici, et l'information n'est pas perdue :
    `barrage_requis` la porte, sur la même poule.
    """
    try:
        return qualifies_de_poule(classement, configuration)
    except BarrageRequisAvantQualification:
        return ()


def _barrage_requis(classement: tuple[RangPoule, ...], configuration: ConfigurationPoules) -> bool:
    """Les **deux régimes d'ex æquo** d'ADR-0083 §5, et toute la différence est ici.

    - La poule **classe** (`nb_qualifies` non déclaré) : le classement *est* le livrable, donc tout
      ex æquo irréductible se départage.
    - La poule **qualifie** : seul le franchissement de la barre compte. Deux archers à égalité aux
      rangs 3-4 d'une poule qui en qualifie 2 **restent** à égalité — les départager reviendrait à
      faire tirer des flèches pour une distinction que personne n'utilise.

    ⚠️ **Un classement vide ou incomplet ne réclame rien.** Avant le premier tir, tous les membres
    sont à 0 partout, donc tous ex æquo : signaler un barrage là annoncerait un départage à faire
    avant même que la poule ait commencé. On exige donc qu'au moins une rencontre ait été comptée —
    ce que trahit un décompte non nul quelque part.
    """
    if not any(ligne.decompte.points_match for ligne in classement):
        return False
    if configuration.nb_qualifies is None:
        return any(ligne.ex_aequo for ligne in classement)
    barre = configuration.nb_qualifies
    if barre >= len(classement):
        return False
    return classement[barre - 1].rang == classement[barre].rang
