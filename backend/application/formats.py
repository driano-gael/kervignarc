"""Service applicatif Formats de tournoi — la brique « déroulé » du club (E01US023, ADR-0060 §5).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur d'infrastructure.

**Ce qui distingue ce service de `ServicePatrimoine`** : un format n'a pas de forme « copie de
tournoi ». Sa copie, ce sont les **phases** du tournoi — d'un autre type, dans un autre dépôt. Le
service traverse donc deux ports (`FormatTournoiRepository` et `PhaseRepository`) là où l'assemblage
des catégories et des blasons reste dans le sien.

Trois cas d'usage au-delà du CRUD :

- **appliquer** — instancie le format en phases du tournoi. **Remplace** la séquence existante, et
  refuse net si une phase est engagée (`PhasesEngagees`) : à ce stade, deviner ce que
  l'organisateur veut garder serait plus dangereux que de lui rendre la main ;
- **promouvoir** — capture les phases d'un tournoi en format de bibliothèque, idempotent par nom ;
- **dupliquer** — l'issue « en faire une copie pour garder les deux modèles » du CA, face à
  `modifier`, qui est l'issue « modifier l'officiel sur place ».
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from application.erreurs import (
    FormatIntrouvable,
    NomFormatDejaPris,
    PhasesEngagees,
    TournoiIntrouvable,
    TournoiSansPhase,
)
from domain.deroule import ProjectionDeroule
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import FormatSansDepart
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    FormatTournoiRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import Tournoi, TournoiId


class LecteurDonneesDePhase(Protocol):
    """Port **étroit** : tout ce dont la garde de remplacement a besoin d'un dépôt qui pend.

    Le service n'a pas à connaître un `ForfaitRepository` entier (déclarer, lister par tournoi, par
    archer…) pour répondre à une seule question : « cette phase porte-t-elle des données ? ». Même
    patron que `LecteurAvancementDepart` (`application/departs.py`), et même bénéfice : le faux de
    test se réduit à une méthode, et le couplage dit exactement ce qu'il est.

    **Deux** adapters le satisfont structurellement, sans rien déclarer : `ForfaitRepositorySQL` et
    `PlacementTableauRepositorySQL`. C'est ce qui permet à la garde de couvrir les deux cascades
    sans les distinguer.

    Déclaré ici plutôt que dans `domain/ports.py` parce que c'est un besoin **de ce service**, pas
    du domaine.
    """

    def par_phase(self, phase_id: PhaseId) -> Sequence[object]:
        """Renvoie ce qui pend à une phase (éventuellement rien).

        Typé `Sequence[object]` parce que la garde n'en compte que la **taille** : les deux dépôts
        qui satisfont ce port rendent des types différents (`Forfait`, `Affectation`), et le port
        n'a aucune raison de les connaître pour répondre « y a-t-il quelque chose ? ».
        """
        ...


class ServiceFormats:
    """Cas d'usage des formats : bibliothèque, application à un tournoi, promotion."""

    def __init__(
        self,
        tournois: TournoiRepository,
        formats: FormatTournoiRepository,
        phases: PhaseRepository,
        forfaits: LecteurDonneesDePhase,
        placements_tableau: LecteurDonneesDePhase,
        departs: DepartRepository,
        deroules: DerouleRepository,
    ) -> None:
        self._tournois = tournois
        # Le **déroulé** du tournoi : la définition, écrite une fois (ADR-0076). Les phases,
        # elles, ne sont plus que des avancements — une par créneau et par étape.
        self._deroules = deroules
        # Appliquer un format crée une séquence **par départ** (ADR-0075) : sans les créneaux,
        # le service ne saurait pas combien de séquences instancier.
        self._departs = departs
        self._formats = formats
        self._phases = phases
        self._forfaits = forfaits
        self._placements_tableau = placements_tableau

    # --- Bibliothèque ---------------------------------------------------------------------

    def lister(self) -> list[FormatTournoi]:
        """Renvoie toute la bibliothèque de formats (liste éventuellement vide)."""
        return self._formats.lister()

    def creer(
        self,
        nom: str,
        etapes: Iterable[ModelePhase],
        effectif_minimum_exige: int | None = None,
    ) -> FormatTournoi:
        """Crée un format de bibliothèque.

        **Accepte un brouillon** depuis E01US024 (ADR-0063) : un format sans étape ou à la séquence
        incohérente s'enregistre — c'est `appliquer` qui protège le tournoi, et `diagnostiquer` qui
        dit ce qui manque. Un minimum d'inscrits **incohérent** avec le déroulé (E05US021) suit la
        même règle : il s'enregistre et se diagnostique. Lève `NomFormatDejaPris` si le nom est déjà
        porté, `DomainError` si le **nom** est vide ou si l'exigence n'est pas positive.
        """
        format_tournoi = FormatTournoi.creer(
            nom, etapes, effectif_minimum_exige=effectif_minimum_exige
        )
        self._verifier_nom_libre(format_tournoi.nom)
        return self._formats.ajouter(format_tournoi)

    def modifier(
        self,
        format_id: FormatTournoiId,
        nom: str,
        etapes: Iterable[ModelePhase],
        effectif_minimum_exige: int | None = None,
    ) -> FormatTournoi:
        """Édite un format **sur place** — l'origine est préservée (ADR-0060 §4).

        C'est l'issue « intégrer au FFTA officiel » du CA : modifier un officiel le laisse
        officiel, parce que le règlement évolue. Pour garder les deux modèles, voir `dupliquer`.

        Lève `FormatIntrouvable`, `NomFormatDejaPris` si le nouveau nom est pris par un **autre**
        format, `DomainError` si le résultat est invalide.
        """
        existant = self._format_existant(format_id)
        modifie = existant.modifier(nom, etapes, effectif_minimum_exige)
        self._verifier_nom_libre(modifie.nom, sauf=format_id)
        return self._formats.enregistrer(modifie)

    def dupliquer(self, format_id: FormatTournoiId, nom: str) -> FormatTournoi:
        """Détache une **copie** d'un format sous un nouveau nom, marquée « création utilisateur ».

        L'issue « en faire une copie pour garder les deux modèles » du CA : l'original est intact.
        Lève `FormatIntrouvable`, `NomFormatDejaPris` si le nom est déjà porté.
        """
        existant = self._format_existant(format_id)
        copie = existant.en_creation_utilisateur(nom)
        self._verifier_nom_libre(copie.nom)
        return self._formats.ajouter(copie)

    def supprimer(self, format_id: FormatTournoiId) -> None:
        """Supprime un format. Les tournois qui l'avaient appliqué gardent leurs **phases**.

        Lève `FormatIntrouvable` si l'identifiant est inconnu.
        """
        self._format_existant(format_id)
        self._formats.supprimer(format_id)

    def precharger_presets(self) -> list[FormatTournoi]:
        """Pré-charge les formats presets dans la bibliothèque (E01US009 : FFTA officiel / club).

        Rejouable sans doublonner (dédup sur le nom exact, comme la contrainte en base). Renvoie
        les formats effectivement **créés**, liste vide si tout était déjà présent.
        """
        crees: list[FormatTournoi] = []
        for preset in (FormatTournoi.preset_ffta_18m(), FormatTournoi.preset_club()):
            if self._formats.par_nom(preset.nom) is not None:
                continue
            crees.append(self._formats.ajouter(preset))
        return crees

    # --- Diagnostic -----------------------------------------------------------------------

    def diagnostiquer(
        self, format_id: FormatTournoiId, effectif: int | None = None
    ) -> ProjectionDeroule:
        """Projette le format sur `effectif` archers : le schéma à braquets et tout ce qui cloche.

        Lecture pure — aucun refus, c'est justement le point (E01US024) : un brouillon incohérent
        doit pouvoir être **regardé** pour être corrigé. Le verdict est dans
        `ProjectionDeroule.est_applicable`. Lève `FormatIntrouvable` (404).
        """
        return self._format_existant(format_id).projeter(effectif)

    # --- Application à un tournoi ---------------------------------------------------------

    def appliquer(self, tournoi_id: TournoiId, format_id: FormatTournoiId) -> list[EtapeDeroule]:
        """Instancie le format en **déroulé** du tournoi et renvoie la séquence créée.

        **Rend des étapes, plus des phases** (ADR-0076) : le déroulé se définit une fois, et
        les phases créées dans la foulée ne sont que des **avancements** (une par créneau et
        par étape), sans réglage propre.

        **Remplace** la séquence existante : les phases déjà posées sont supprimées d'abord, sans
        quoi les ordres du format entreraient en collision avec elles et `SequencePhases`
        refuserait toute composition ultérieure.

        Refuse (`PhasesEngagees`) dès qu'une phase du tournoi n'est plus `à venir` : le
        remplacement jetterait un déroulé en cours, avec les séries et les duels qui y pendent.

        **Recopie le minimum d'inscrits exigé** par le format sur le tournoi (E05US021) : le tournoi
        ne garde aucun lien vers son format — sa copie, ce sont ses phases (ADR-0060) —, donc
        sans ce transport la garde de démarrage n'aurait rien à lire. Même patron que le
        gabarit de salle : modèle → copie → ajustement sans altérer le modèle. Le plancher
        **technique**, lui, ne se recopie pas : il se déduit des phases, qui viennent d'être
        posées.

        Lève `TournoiIntrouvable`, `FormatIntrouvable`.
        """
        tournoi = self._tournoi_existant(tournoi_id)
        format_tournoi = self._format_existant(format_id)
        existantes = self._phases.par_tournoi(tournoi_id)
        self._exiger_sequence_remplacable(tournoi_id, existantes, format_tournoi)

        # ⚠️ **Instancier AVANT de détruire** (E01US024). `format_tournoi.appliquer` peut lever :
        # depuis ADR-0063 un format incohérent s'enregistre, et c'est ici que l'invariant est tenu.
        # Les suppressions sont **committées** (une session par appel de repository, DETTE-025),
        # donc une exception levée après elles laisserait le tournoi **sans aucun déroulé** — et
        # sans son barème de qualification, que le troisième garde existe pour protéger.
        etapes = format_tournoi.appliquer(tournoi_id)

        # Le domaine ignore les créneaux (ADR-0076) : c'est ici qu'on refuse un tournoi qui n'en a
        # aucun. Sans départ, le déroulé serait défini mais **personne ne le jouerait** — et le
        # silence ferait croire à un succès.
        departs = [d.id for d in self._departs.par_tournoi(tournoi_id) if d.id is not None]
        if not departs:
            raise FormatSansDepart(
                "Ce tournoi n'a aucun départ : appliquer un format ne créerait aucune phase. "
                "Créez au moins un créneau avant d'appliquer un déroulé."
            )

        # DETTE-025 — destruction puis recréation en **transactions séparées** : une panne entre
        # les deux laisse le tournoi sans déroulé. Le remède est un `remplacer_sequence` atomique
        # sur l'adapter concret, qui touche le **port** — hors périmètre. Les gardes ci-dessus
        # bornent la perte à une séquence `à venir` sans données attachées.
        for phase in existantes:
            assert phase.id is not None, "une phase relue du dépôt porte toujours un identifiant."
            self._phases.supprimer(phase.id)
        for ancienne in self._deroules.par_tournoi(tournoi_id):
            assert ancienne.id is not None, "une étape relue du dépôt porte un identifiant."
            self._deroules.supprimer(ancienne.id)

        posees = [self._deroules.ajouter(etape) for etape in etapes]
        # **Un avancement par créneau et par étape** : c'est le seul éventail qui subsiste, et il
        # ne porte aucun réglage — juste « où en est ce départ de cette étape ».
        for depart_id in departs:
            for etape in posees:
                self._phases.ajouter(etape.instancier(depart_id))

        # DETTE-025 (élargie par E05US021) — écriture supplémentaire, dans sa propre transaction :
        # une panne ici laisse un tournoi au déroulé du nouveau format et à l'exigence de l'ancien.
        # Placée après le déroulé à dessein : le tournoi ne porte l'exigence que si les étapes qui
        # la justifient sont en place.
        self._tournois.enregistrer(
            tournoi.exiger_effectif_minimum(format_tournoi.effectif_minimum_exige)
        )
        return posees

    def _exiger_sequence_remplacable(
        self,
        tournoi_id: TournoiId,
        existantes: list[Phase],
        format_tournoi: FormatTournoi,
    ) -> None:
        """Trois refus avant de détruire une séquence — statut, **contenu**, et qualification.

        Le premier jet ne regardait que le `statut`, et c'était insuffisant : une phase `à venir`
        peut déjà porter des données. `forfait.phase_id` et `placement_tableau.phase_id` sont en
        `ON DELETE CASCADE` (cf. `infrastructure/db/models.py`), et **ni** `ServiceForfait` **ni**
        `ServicePlacementDuels` n'exigent qu'une phase soit démarrée : un forfait déclaré au
        pointage pend sur une phase `à venir`, et un plan de duels ajusté à la main la veille aussi
        (E03US009 — l'ajustement manuel *est* la fonctionnalité). Le remplacement les effaçait en
        silence, alors que le message de `PhasesEngagees` promet de protéger « les séries et les
        duels qui y pendent ».

        ⚠️ Le deuxième jet ne comptait que les **forfaits**, tout en **nommant** `placement_tableau`
        dans cette docstring même — la revue l'a démontré à l'exécution (une pose avant, zéro
        après). Les deux cascades sont désormais comptées.

        Le troisième refus ferme une **route parallèle** : `ServicePhases.supprimer` interdit de
        retirer la phase de qualification (`PhaseQualificationNonSupprimable`) parce qu'elle porte
        le barème ; passer par le repository contournait ce contrôle. Appliquer un format sans
        qualification à un tournoi qui en a une lui retirait donc son barème, sans qu'aucun écran ne
        permette de le recréer autrement qu'en le redéfinissant.
        """
        engagees = [p for p in existantes if p.statut is not StatutPhase.A_VENIR]
        if engagees:
            raise PhasesEngagees(
                f"Le tournoi {tournoi_id} a {len(engagees)} phase(s) déjà engagée(s) : appliquer "
                "un format remplacerait un déroulé en cours."
            )
        ids = [p.id for p in existantes if p.id is not None]
        forfaits = sum(len(self._forfaits.par_phase(phase_id)) for phase_id in ids)
        if forfaits:
            raise PhasesEngagees(
                f"{forfaits} forfait(s) sont déclarés sur les phases de ce tournoi : appliquer un "
                "format les effacerait avec elles."
            )
        poses = sum(len(self._placements_tableau.par_phase(phase_id)) for phase_id in ids)
        if poses:
            raise PhasesEngagees(
                f"{poses} duelliste(s) sont posés sur le plan de duels de ce tournoi : appliquer "
                "un format les effacerait avec les phases."
            )
        avait_qualification = any(p.type is TypePhase.QUALIFICATION for p in existantes)
        aura_qualification = any(e.type is TypePhase.QUALIFICATION for e in format_tournoi.etapes)
        if avait_qualification and not aura_qualification:
            raise PhasesEngagees(
                "Ce format ne décrit aucune qualification : l'appliquer retirerait au tournoi son "
                "barème, que rien ne permettrait de recréer ensuite."
            )

    # --- Promotion ------------------------------------------------------------------------

    def promouvoir(self, tournoi_id: TournoiId, nom: str) -> FormatTournoi:
        """Capture le déroulé d'un tournoi en format de bibliothèque (« c'est permanent »).

        Idempotent par nom : promouvoir deux fois sous le même nom **met à jour** le format au lieu
        d'accumuler des homonymes. La mise à jour conserve l'identifiant **et l'origine** du format
        existant (même règle que `modifier`).

        Ne rétroagit sur aucun tournoi : les éditions déjà assemblées gardent leurs phases
        (ADR-0060 §3). Lève `TournoiIntrouvable`, `TournoiSansPhase` si le tournoi n'a aucune phase
        à capturer.

        **L'exigence d'effectif du tournoi remonte avec le déroulé** (E05US021) : elle y a été
        recopiée à l'application d'un format, et c'est une propriété du déroulé qu'on promeut — pas
        un accident de l'édition. En son absence, l'exigence du format existant
        est **conservée** : la promotion capture des *phases*, elle n'a aucune raison d'effacer une
        règle de club qu'elle ne sait pas exprimer.
        """
        tournoi = self._tournoi_existant(tournoi_id)
        # **Le déroulé, tout simplement** (ADR-0076). Tant que la définition était recopiée par
        # créneau, promouvoir obligeait à choisir *laquelle* des N copies faisait foi — et à
        # refuser les lots mêlés. Le déroulé étant unique, la question ne se pose plus.
        etapes = self._deroules.par_tournoi(tournoi_id)
        if not etapes:
            raise TournoiSansPhase(f"Le tournoi {tournoi_id} n'a aucun déroulé à promouvoir.")
        capture = FormatTournoi.de_deroule(nom, etapes, tournoi.effectif_minimum_exige)
        existant = self._formats.par_nom(capture.nom)
        if existant is None:
            return self._formats.ajouter(capture)
        return self._formats.enregistrer(
            existant.modifier(
                capture.nom,
                capture.etapes,
                capture.effectif_minimum_exige or existant.effectif_minimum_exige,
            )
        )

    # --- Rouages internes -----------------------------------------------------------------

    def _format_existant(self, format_id: FormatTournoiId) -> FormatTournoi:
        format_tournoi = self._formats.par_id(format_id)
        if format_tournoi is None:
            raise FormatIntrouvable(f"Aucun format de tournoi d'identifiant {format_id}.")
        return format_tournoi

    def _verifier_nom_libre(self, nom: str, sauf: FormatTournoiId | None = None) -> None:
        """Refuse un homonyme ; `sauf` laisse un format garder son propre nom à l'édition."""
        existant = self._formats.par_nom(nom)
        if existant is not None and existant.id != sauf:
            raise NomFormatDejaPris(f"Un format de tournoi porte déjà le nom « {nom} ».")

    def _tournoi_existant(self, tournoi_id: TournoiId) -> Tournoi:
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi
