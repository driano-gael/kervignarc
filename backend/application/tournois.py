"""Service des **tournois** — arbitre l'existence et les **conflits d'état** du cycle de vie.

L'agrégat, lui, ne valide que les valeurs (ADR-0007, ADR-0026 §4). Le service ignore HTTP, SQL et
la file : il reste synchrone et pur d'infrastructure.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from application.erreurs import (
    EffectifInsuffisantPourDemarrer,
    TournoiArchiveNonModifiable,
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TournoiPeuple,
    TournoiSansDepart,
    TransitionStatutInvalide,
)
from application.suivi_deroule import CompteurEngages
from domain.deroule import exigence_minimale
from domain.deroule_etape import EtapeDeroule, vues_du_deroule
from domain.gabarit_salle import GabaritSalle
from domain.ports import ArcherRepository, DepartRepository, TournoiRepository
from domain.tournoi import (
    MESSAGE_SANS_DEPART,
    MESSAGE_TERMINER_HORS_EN_COURS,
    DescendanceTournoi,
    StatutTournoi,
    Tournoi,
    TournoiId,
    TransitionTournoi,
    TypeTournoi,
)
from domain.tournoi import (
    transitions_possibles as topologie_transitions,
)


class LecteurPlanDeSalle(Protocol):
    """Port **étroit** : le plan de salle d'un tournoi, pour compter ses cibles (A04, E17US012).

    Même patron que `LecteurDerouleDuTournoi` : `GabaritSalleRepositorySQL` le satisfait
    structurellement, sans rien déclarer.
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit du tournoi, ou `None` s'il n'y en a pas."""
        ...


class LecteurDerouleDuTournoi(Protocol):
    """Port **étroit** : le déroulé composé d'un tournoi, et rien d'autre (E05US021).

    La garde de démarrage n'a besoin que de « quel déroulé ce tournoi a-t-il ? », pas d'un
    `DerouleRepository` entier — même patron que `CompteurEngages`. ⚠️ **Il lit des `EtapeDeroule`,
    plus des `Phase`** (E01US025, ADR-0076) : il lisait `PhaseRepository.par_tournoi`, qui n'est
    pas une séquence, et sur quatre créneaux `exigence_minimale` recevait quatre copies concaténées
    du déroulé. `DerouleRepositorySQL` le satisfait structurellement, sans rien déclarer.
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        """Renvoie les étapes du déroulé du tournoi (liste éventuellement vide)."""
        ...


class OrigineExigence(str, Enum):
    """D'où vient le minimum d'inscrits d'un tournoi (E05US021).

    Trois origines qui appellent trois phrases différentes — les confondre fait dire au produit des
    choses fausses (cf. `ExigenceEffectifTournoi`).
    """

    AUCUNE = "aucune"
    """Aucun déroulé composé : rien n'est exigé."""

    DEROULE = "deroule"
    """Le plancher **déduit** du déroulé — un prélèvement par rangs, ou la structure d'une phase."""

    CLUB = "club"
    """Une règle sportive **saisie** sur le format (« pas de tournoi de ce type sous 40 »)."""


@dataclass(frozen=True)
class ExigenceEffectifTournoi:
    """Ce qu'un tournoi exige d'inscrits, ce qu'il en a, et pourquoi (E05US021).

    Lecture d'écran **et** matière du refus — les deux disent la même chose, d'où un seul objet.
    `minimum` vaut `0` sans déroulé composé. ⚠️ `origine` dit **d'où vient le chiffre** et n'est
    pas décoratif : le déduire de `ordre_phase is None` faisait annoncer « le minimum exigé pour ce
    format » — une règle de club — sur un simple plancher structurel. `ordre_phase`/`rang_debut`
    restent `None` quand le manque ne vient d'aucun prélèvement.
    """

    inscrits: int
    minimum: int
    suffisant: bool
    origine: OrigineExigence = OrigineExigence.AUCUNE
    ordre_phase: int | None = None
    rang_debut: int | None = None
    ordre_source: int | None = None
    """La phase **dans laquelle** `rang_debut` se lit (E05US024) — cf. `ExigenceEffectif`."""
    depart_numero: int | None = None
    """Le **numéro du créneau** dont `inscrits` est le compte — le moins garni (E01US025).

    `None` quand le tournoi n'a aucun départ. Le porter explicitement plutôt que de laisser
    l'organisateur deviner : « 8 inscrits pour 34 requis » sur un tournoi qui en affiche 48 au
    total est incompréhensible tant qu'on ne dit pas *dans quel créneau* le compte manque.
    """

    def message_de_refus(self) -> str:
        """Le message rendu à l'organisateur — **chiffré et actionnable** (`D-16` / `P-4`).

        « Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection » : on
        nomme le manque *et* sa cause. Le **créneau** est nommé dès qu'on le connaît — le compte
        est celui du départ le moins garni, et sans cette précision le chiffre semble contredire le
        total affiché ailleurs.
        """
        ou = "" if self.depart_numero is None else f" sur le départ {self.depart_numero}"
        manque = f"{self.inscrits} archer(s) inscrit(s){ou} pour {self.minimum} requis"
        if self.origine is OrigineExigence.CLUB:
            return (
                f"Ce tournoi ne peut pas démarrer : {manque}. Ce format exige au moins "
                f"{self.minimum} inscrits. Complétez les inscriptions ou changez de format."
            )
        if self.ordre_phase is None:
            return (
                f"Ce tournoi ne peut pas démarrer : {manque}. Son déroulé ne peut pas se jouer à "
                "moins que cela."
            )
        # ⚠️ **Le rang et le nombre d'inscrits ne vivent pas dans le même espace** depuis que la
        # chaîne se remonte (E05US024) : « le rang 5 » se lit dans la phase **source**, tandis que
        # « 22 inscrits » compte des inscrits au tournoi. Les énoncer sans nommer la source rendait
        # le message indéchiffrable — deux chiffres qui ne se déduisent plus l'un de l'autre
        # (relevé en revue, axe C1).
        ou = (
            f" de la phase {self.ordre_source}"
            if self.ordre_source is not None and self.ordre_source != self.ordre_phase
            else ""
        )
        return (
            f"Ce tournoi ne peut pas démarrer : {manque}. La phase {self.ordre_phase} prélève à "
            f"partir du rang {self.rang_debut}{ou} : il faut au moins {self.minimum} inscrits pour "
            "qu'elle ait des tireurs. Changez de format ou complétez les inscriptions."
        )


@dataclass(frozen=True)
class TournoiEnListe:
    """Un tournoi et les effectifs de la liste d'administration (planche A04, E17US012).

    `nb_inscrits` compte les **archers du tournoi** — le même compte que « Voir les N inscrits »
    d'A09. `nb_cibles is None` : aucun plan de salle posé, à ne pas confondre avec une salle vide.
    """

    tournoi: Tournoi
    nb_inscrits: int
    nb_cibles: int | None


class ServiceTournois:
    """Cas d'usage des tournois : créer, consulter, lister, éditer, cycle de vie, supprimer."""

    def __init__(
        self,
        repository: TournoiRepository,
        depart_repository: DepartRepository,
        deroule_repository: LecteurDerouleDuTournoi,
        engages: CompteurEngages,
        archer_repository: ArcherRepository,
        plan_de_salle: LecteurPlanDeSalle,
    ) -> None:
        self._repository = repository
        # E02US010 : le passage à `prêt` exige **au moins un départ**. `ServiceTournois` lit donc
        # les créneaux (port `DepartRepository`, un port de domaine — pas l'autre service, pas
        # d'infra), comme il lit les tournois. Depuis E01US025 il en lit aussi l'**effectif**, un
        # créneau à la fois : le déroulé doit se jouer dans chacun (cf. `exigence_effectif`).
        self._departs = depart_repository
        # E05US021 : le **démarrage** confronte les inscrits au minimum que le déroulé réclame. Même
        # parti que ci-dessus — deux lectures de plus, par des ports (le déroulé du tournoi, et le
        # port étroit `CompteurEngages` déjà réalisé pour le suivi), pas par d'autres services.
        self._deroules = deroule_repository
        self._engages = engages
        # E17US012 : les effectifs de la liste (A04) — archers et plan de salle, par leurs ports.
        self._archers = archer_repository
        self._gabarits = plan_de_salle

    def creer(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée et persiste un tournoi. Lève `DomainError` si les champs sont invalides.

        Le tarif ne se fixe plus ici : il vit sur chaque départ (créneau), configuré par
        `ServiceDeparts` (E02US004, ADR-0017).
        """
        tournoi = Tournoi.creer(nom, date, lieu, type_tournoi)
        return self._repository.ajouter(tournoi)

    def consulter(self, tournoi_id: TournoiId) -> Tournoi:
        """Relit un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        tournoi = self._repository.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi

    def lister_en_liste(self) -> list[TournoiEnListe]:
        """Tous les tournois avec leurs inscrits et leurs cibles (liste d'administration, A04).

        Deux lectures par tournoi : tenable pour la douzaine de tournois d'un club (règle 12).
        """
        return [self._en_liste(tournoi) for tournoi in self._repository.lister()]

    def _en_liste(self, tournoi: Tournoi) -> TournoiEnListe:
        assert tournoi.id is not None, "Un tournoi relu est persisté."
        gabarit = self._gabarits.par_tournoi(tournoi.id)
        return TournoiEnListe(
            tournoi=tournoi,
            nb_inscrits=len(self._archers.par_tournoi(tournoi.id)),
            nb_cibles=None if gabarit is None else gabarit.nb_cibles,
        )

    def modifier(
        self,
        tournoi_id: TournoiId,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Édite les métadonnées d'un tournoi (nom, date, lieu, type), statut préservé.

        Lève `TournoiIntrouvable` si l'identifiant est inconnu, `DomainError` si le nom est
        vide. L'édition est autorisée quel que soit le statut. Le tarif ne fait plus partie des
        métadonnées du tournoi (il vit sur chaque départ — E02US004).
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is StatutTournoi.ARCHIVE:
            raise TournoiArchiveNonModifiable(
                "Un tournoi archivé est en lecture seule ; il ne peut plus être édité."
            )
        modifie = tournoi.modifier(nom, date, lieu, type_tournoi)
        return self._repository.enregistrer(modifie)

    # --- Cycle de vie enrichi (E01US017, ADR-0026) ---
    # L'agrégat ne porte que la valeur ; le service arbitre l'**enchaînement** légal (ADR-0007/0026
    # §4). `_transition` factorise le patron « relire → vérifier le statut de départ → produire la
    # copie → persister » pour les arêtes à garde de simple légalité. `vers_pret` fait bande à part
    # (garde de complétude en plus, E12US005 à froid) ; `supprimer` n'est pas une transition.

    def vers_pret(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `brouillon` à `prêt` (feu vert au démarrage).

        Lève `TournoiIntrouvable` si inconnu, `TransitionStatutInvalide` (→ 409) s'il n'est pas
        `brouillon`, `TournoiSansDepart` (→ 409) s'il n'a **aucun départ** (E02US010). Cette garde
        « ≥ 1 départ » est la **première brique** de la garde de complétude de préparation
        (catégories, blasons associés, gabarit, barème — [ADR-0026] §2) : le reste est ajouté par
        une tranche ultérieure.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is not StatutTournoi.BROUILLON:
            raise TransitionStatutInvalide("Seul un tournoi en brouillon peut passer prêt.")
        if not self._departs.par_tournoi(tournoi_id):
            raise TournoiSansDepart(MESSAGE_SANS_DEPART)
        return self._repository.enregistrer(tournoi.vers_pret())

    def revenir_brouillon(self, tournoi_id: TournoiId) -> Tournoi:
        """Repasse un tournoi `prêt` en `brouillon` (renoncer au feu vert pour rééditer)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.PRET},
            Tournoi.revenir_brouillon,
            "Seul un tournoi prêt peut revenir en brouillon.",
        )

    def demarrer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `prêt` à `en_cours`, **si l'effectif suit** (E05US021).

        Lève `TransitionStatutInvalide` (→ 409) s'il n'est pas `prêt`, et
        `EffectifInsuffisantPourDemarrer` (→ 409) s'il compte moins d'inscrits que son déroulé n'en
        réclame. Cette seconde garde ne s'exprime que si un déroulé est **composé** : sans phase, il
        n'y a aucun prélèvement à honorer, donc rien à exiger.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is not StatutTournoi.PRET:
            raise TransitionStatutInvalide("Seul un tournoi prêt peut être démarré.")
        self._exiger_un_effectif_suffisant(tournoi_id)
        return self._repository.enregistrer(tournoi.demarrer())

    def exigence_effectif(self, tournoi_id: TournoiId) -> ExigenceEffectifTournoi:
        """Ce que ce tournoi exige d'inscrits, et ce qu'il en a — « visible avant le clic ».

        Aucune écriture : un **état à afficher**, le refus au clic relevant de `demarrer`. Lève
        `TournoiIntrouvable` (→ 404) sur l'**existence** — sinon un tournoi inconnu rendrait «
        aucune exigence ». ⚠️ **Le minimum vient du déroulé (unique, au tournoi) ; les inscrits, du
        créneau le moins garni** (ADR-0075/0076) : le confronter à la **somme** laissait démarrer
        un tournoi de deux créneaux à 40 et 8 archers.
        """
        tournoi = self.consulter(tournoi_id)
        etapes = self._deroules.par_tournoi(tournoi_id)
        creneau = self._creneau_le_moins_garni(tournoi_id)
        inscrits = 0 if creneau is None else creneau[1]
        numero = None if creneau is None else creneau[0]
        if not etapes:
            # Aucun déroulé composé : rien n'est prélevé, donc rien n'est exigé. Le dire
            # « satisfait » plutôt que « minimum 1 » évite d'afficher une exigence là où
            # l'organisateur n'a encore rien décidé.
            return ExigenceEffectifTournoi(
                inscrits=inscrits,
                minimum=0,
                suffisant=True,
                origine=OrigineExigence.AUCUNE,
                depart_numero=numero,
            )

        exige = tournoi.effectif_minimum_exige
        deduite = exigence_minimale(vues_du_deroule(etapes))
        if exige is not None and exige > deduite.minimum:
            # L'exigence du club dépasse le plancher technique : c'est elle qui commande, et aucune
            # phase n'est en cause — le manque vient d'une règle sportive, pas d'un prélèvement.
            return ExigenceEffectifTournoi(
                inscrits=inscrits,
                minimum=exige,
                suffisant=inscrits >= exige,
                origine=OrigineExigence.CLUB,
                depart_numero=numero,
            )
        return ExigenceEffectifTournoi(
            inscrits=inscrits,
            minimum=deduite.minimum,
            suffisant=inscrits >= deduite.minimum,
            origine=OrigineExigence.DEROULE,
            ordre_phase=deduite.ordre,
            rang_debut=deduite.rang_debut,
            ordre_source=deduite.ordre_source,
            depart_numero=numero,
        )

    def _creneau_le_moins_garni(self, tournoi_id: TournoiId) -> tuple[int, int] | None:
        """`(numéro, inscrits)` du créneau le plus faible — `None` si le tournoi n'a aucun départ.

        C'est **lui** que le déroulé doit pouvoir se jouer : chaque départ rejoue le tournoi en
        entier (ADR-0075), donc l'exigence se juge sur le maillon faible, jamais sur la somme. En
        cas d'égalité, le **plus petit numéro** l'emporte — un choix stable, pour que l'écran
        n'alterne pas entre deux créneaux d'un rafraîchissement à l'autre.
        """
        comptes = [
            (depart.numero, self._engages.nb_engages_du_depart(depart.id))
            for depart in self._departs.par_tournoi(tournoi_id)
            if depart.id is not None
        ]
        return min(comptes, key=lambda couple: (couple[1], couple[0])) if comptes else None

    def _exiger_un_effectif_suffisant(self, tournoi_id: TournoiId) -> None:
        """Refuse le démarrage si les inscrits ne couvrent pas ce que le déroulé réclame."""
        exigence = self.exigence_effectif(tournoi_id)
        if exigence.suffisant:
            return
        raise EffectifInsuffisantPourDemarrer(exigence.message_de_refus())

    def mettre_en_pause(self, tournoi_id: TournoiId) -> Tournoi:
        """Fait passer un tournoi `en_cours` à `en_pause`. **N'arrête rien d'autre** (`DETTE-073`).

        ⚠️ Cette docstring promettait « la saisie s'arrête jusqu'à `reprendre` ». C'était **faux**
        depuis toujours : aucun chemin d'écriture ne lit `StatutTournoi`. Le volet **phase** a été
        corrigé en E05US033 (`PhaseEnPause`, ADR-0091 §6) ; le volet **tournoi** est à une autre
        maille (ADR-0026 §3) et sa capacité **reste absente** — le bouton de l'écran d'admin laisse
        toujours croire le contraire. Cf. docs/dette.md.
        """
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_COURS},
            Tournoi.mettre_en_pause,
            "Seul un tournoi en cours peut être mis en pause.",
        )

    def reprendre(self, tournoi_id: TournoiId) -> Tournoi:
        """Reprend un tournoi `en_pause` en `en_cours`."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_PAUSE},
            Tournoi.reprendre,
            "Seul un tournoi en pause peut être repris.",
        )

    def terminer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `en_cours` à `terminé` (fige les résultats sportifs)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_COURS},
            Tournoi.terminer,
            MESSAGE_TERMINER_HORS_EN_COURS,
        )

    def archiver(self, tournoi_id: TournoiId) -> Tournoi:
        """Archive un tournoi `terminé` (verrou total, lecture seule définitive)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.TERMINE},
            Tournoi.archiver,
            "Seul un tournoi terminé peut être archivé.",
        )

    def annuler(self, tournoi_id: TournoiId) -> Tournoi:
        """Annule un tournoi abandonné (terminal, conserve la trace ≠ suppression).

        Accessible depuis `brouillon`, `prêt`, `en_cours`, `en_pause` — **pas** depuis `terminé`
        (un tournoi joué jusqu'au bout n'est pas « annulé ») ni `archivé` ([ADR-0026] §2).
        """
        return self._transition(
            tournoi_id,
            {
                StatutTournoi.BROUILLON,
                StatutTournoi.PRET,
                StatutTournoi.EN_COURS,
                StatutTournoi.EN_PAUSE,
            },
            Tournoi.annuler,
            "Un tournoi terminé ou archivé ne peut pas être annulé.",
        )

    def transitions_possibles(self, tournoi_id: TournoiId) -> tuple[TransitionTournoi, ...]:
        """Renvoie les transitions de cycle de vie **offertes** par le statut courant du tournoi.

        Relit le tournoi (`TournoiIntrouvable` si inconnu) et délègue la **topologie** au domaine
        (`domain.tournoi.transitions_possibles`) — pas de second encodage du graphe ici (règle 1).
        ⚠️ Aucune garde n'est ré-évaluée : une arête offerte peut échouer à l'exécution
        (`vers-pret` sans départ). `test_service_tournois` vérifie que la topologie ne diverge pas
        des gardes.
        """
        return topologie_transitions(self.consulter(tournoi_id).statut)

    def _transition(
        self,
        tournoi_id: TournoiId,
        depuis: Iterable[StatutTournoi],
        produire: Callable[[Tournoi], Tournoi],
        message: str,
    ) -> Tournoi:
        """Applique une transition de cycle de vie gardée par le seul statut de départ.

        Relit le tournoi (`TournoiIntrouvable` si inconnu), refuse si son statut n'est pas dans
        `depuis` (`TransitionStatutInvalide` → 409), sinon persiste la copie produite.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut not in set(depuis):
            raise TransitionStatutInvalide(message)
        return self._repository.enregistrer(produire(tournoi))

    def supprimer(self, tournoi_id: TournoiId, autoriser_suppression_peuplee: bool = False) -> None:
        """Supprime un tournoi **et toute sa descendance** (E01US026, ADR-0077).

        Lève `TournoiIntrouvable` si inconnu ; `TournoiEnCoursNonSupprimable` (→ 409) s'il est
        `en_cours`/`en_pause` ; `TournoiArchiveNonModifiable` (→ 409) s'il est `archivé`
        ([ADR-0026] §1). S'il porte des données, lève `TournoiPeuple` (→ 409) avec un décompte
        chiffré, sauf `autoriser_suppression_peuplee=True` — un **signalement**, pas un refus.
        """
        tournoi = self.consulter(tournoi_id)
        # ⚠️ Les gardes d'état passent **avant** le signalement, et l'ordre est le CA lui-même : un
        # tournoi en cours peuplé doit rendre le refus définitif, jamais un signalement que la
        # confirmation lèverait — sinon l'admin apprend qu'un tournoi en cours se supprime « en
        # confirmant ». Vérifié par `test_le_signalement_precede_la_garde_d_etat_jamais_l_inverse`.
        if tournoi.statut in {StatutTournoi.EN_COURS, StatutTournoi.EN_PAUSE}:
            raise TournoiEnCoursNonSupprimable(
                "Un tournoi en cours ou en pause ne peut pas être supprimé ; terminez-le ou "
                "annulez-le d'abord."
            )
        if tournoi.statut is StatutTournoi.ARCHIVE:
            raise TournoiArchiveNonModifiable(
                "Un tournoi archivé est en lecture seule ; il ne peut pas être supprimé."
            )
        assert tournoi.id is not None, "Un tournoi consulté est persisté."
        # DETTE-007 : la confirmation est **aveugle**, comme pour l'archer engagé et le départ. Le
        # décompte annoncé n'est pas revérifié au rejeu — entre le 409 et la confirmation, d'autres
        # tablettes peuvent saisir, et l'on détruirait plus que le message n'a annoncé.
        if not autoriser_suppression_peuplee:
            self._signaler_descendance(tournoi)
        self._repository.supprimer(tournoi.id)

    def _signaler_descendance(self, tournoi: Tournoi) -> None:
        """Lève `TournoiPeuple` si le tournoi porte des données, en **chiffrant** chaque nature.

        « Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection »
        (`D-16`) : le message énumère les natures **présentes** et leurs nombres — une nature à zéro
        n'est pas un impact et ne figure pas. Même patron que `ServiceArchers._signaler_engagement`.
        """
        assert tournoi.id is not None, "Un tournoi consulté est persisté."
        descendance = self._repository.compter_descendance(tournoi.id)
        if descendance.est_vide():
            return
        motifs = [
            _accorde(nombre, singulier, pluriel)
            for nombre, singulier, pluriel in (
                (descendance.archers, "archer", "archers"),
                (descendance.inscriptions, "inscription", "inscriptions"),
                (descendance.fleches, "flèche tirée", "flèches tirées"),
                (descendance.series, "série de saisie", "séries de saisie"),
                (descendance.duels, "duel", "duels"),
                (descendance.forfaits, "forfait", "forfaits"),
                (descendance.barrages, "barrage", "barrages"),
                (descendance.postes, "poste enrôlé", "postes enrôlés"),
                (descendance.scoreurs, "scoreur", "scoreurs"),
                (descendance.entrees_audit, "acte au journal", "actes au journal"),
            )
            if nombre
        ]
        motifs.extend(_motifs_d_argent(descendance))
        raise TournoiPeuple(
            f"« {tournoi.nom} » porte {_enumere(motifs)}. Tout sera détruit et rien ne pourra "
            "être récupéré ; confirmez pour supprimer quand même."
        )


def _accorde(nombre: int, singulier: str, pluriel: str) -> str:
    """« 1 archer » / « 42 archers » — un message lu par un bénévole qui s'apprête à détruire.

    Accord réel plutôt qu'un « archer(s) » : il doit se lire, pas se décoder (même parti que
    `ServiceArchers._signaler_engagement`).
    """
    return f"{nombre} {singulier if nombre == 1 else pluriel}"


def _motifs_d_argent(descendance: DescendanceTournoi) -> list[str]:
    """Les deux natures **monétaires**, chiffrées en euros et jamais confondues (E01US026).

    ⚠️ `encaisse` est l'argent **reçu** (inscriptions payées), `remboursements` ce qui était déjà
    déclaré à rendre : les additionner compterait deux fois la même pièce. Aucune contrepartie n'est
    possible — le registre a `tournoi_id` pour unique FK, donc il part avec le tournoi (à la
    différence de DETTE-018, où il survit). Chiffrer est tout ce qui reste.
    """
    motifs = []
    if descendance.inscriptions_payees:
        payees = _accorde(
            descendance.inscriptions_payees, "inscription payée", "inscriptions payées"
        )
        motifs.append(f"{payees} ({_euros(descendance.encaisse_centimes)} encaissés)")
    if descendance.remboursements:
        nombre = _accorde(descendance.remboursements, "remboursement", "remboursements")
        motifs.append(f"{nombre} ({_euros(descendance.remboursements_centimes)} restant à rendre)")
    return motifs


def _euros(centimes: int) -> str:
    """« 4550 » → « 45,50 € » — le séparateur décimal est la virgule, le lecteur est un bénévole."""
    return f"{centimes / 100:.2f}".replace(".", ",") + " €"


def _enumere(motifs: list[str]) -> str:
    """Joint les natures en français : « a, b et c » — jamais une liste à virgules jusqu'au bout."""
    if len(motifs) == 1:
        return motifs[0]
    return f"{', '.join(motifs[:-1])} et {motifs[-1]}"
