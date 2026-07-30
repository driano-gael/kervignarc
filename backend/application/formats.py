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

from collections.abc import Iterable

from application.erreurs import (
    FormatIntrouvable,
    NomFormatDejaPris,
    PhasesEngagees,
    TournoiIntrouvable,
    TournoiSansPhase,
)
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.phase import Phase, StatutPhase
from domain.ports import FormatTournoiRepository, PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceFormats:
    """Cas d'usage des formats : bibliothèque, application à un tournoi, promotion."""

    def __init__(
        self,
        tournois: TournoiRepository,
        formats: FormatTournoiRepository,
        phases: PhaseRepository,
    ) -> None:
        self._tournois = tournois
        self._formats = formats
        self._phases = phases

    # --- Bibliothèque ---------------------------------------------------------------------

    def lister(self) -> list[FormatTournoi]:
        """Renvoie toute la bibliothèque de formats (liste éventuellement vide)."""
        return self._formats.lister()

    def creer(self, nom: str, etapes: Iterable[ModelePhase]) -> FormatTournoi:
        """Crée un format de bibliothèque.

        Lève `NomFormatDejaPris` si le nom est déjà porté, `DomainError` si le format est
        invalide (nom vide, aucune étape, séquence incohérente).
        """
        format_tournoi = FormatTournoi.creer(nom, etapes)
        self._verifier_nom_libre(format_tournoi.nom)
        return self._formats.ajouter(format_tournoi)

    def modifier(
        self, format_id: FormatTournoiId, nom: str, etapes: Iterable[ModelePhase]
    ) -> FormatTournoi:
        """Édite un format **sur place** — l'origine est préservée (ADR-0060 §4).

        C'est l'issue « intégrer au FFTA officiel » du CA : modifier un officiel le laisse
        officiel, parce que le règlement évolue. Pour garder les deux modèles, voir `dupliquer`.

        Lève `FormatIntrouvable`, `NomFormatDejaPris` si le nouveau nom est pris par un **autre**
        format, `DomainError` si le résultat est invalide.
        """
        existant = self._format_existant(format_id)
        modifie = existant.modifier(nom, etapes)
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

    # --- Application à un tournoi ---------------------------------------------------------

    def appliquer(self, tournoi_id: TournoiId, format_id: FormatTournoiId) -> list[Phase]:
        """Instancie le format en **phases** du tournoi et renvoie la séquence créée.

        **Remplace** la séquence existante : les phases déjà posées sont supprimées d'abord, sans
        quoi les ordres du format entreraient en collision avec elles et `SequencePhases`
        refuserait toute composition ultérieure.

        Refuse (`PhasesEngagees`) dès qu'une phase du tournoi n'est plus `à venir` : le
        remplacement jetterait un déroulé en cours, avec les séries et les duels qui y pendent.

        Lève `TournoiIntrouvable`, `FormatIntrouvable`.
        """
        self._tournoi_existant(tournoi_id)
        format_tournoi = self._format_existant(format_id)
        existantes = self._phases.par_tournoi(tournoi_id)
        engagees = [p for p in existantes if p.statut is not StatutPhase.A_VENIR]
        if engagees:
            raise PhasesEngagees(
                f"Le tournoi {tournoi_id} a {len(engagees)} phase(s) déjà engagée(s) : appliquer "
                "un format remplacerait un déroulé en cours."
            )
        for phase in existantes:
            assert phase.id is not None, "une phase relue du dépôt porte toujours un identifiant."
            self._phases.supprimer(phase.id)
        return [self._phases.ajouter(phase) for phase in format_tournoi.appliquer(tournoi_id)]

    # --- Promotion ------------------------------------------------------------------------

    def promouvoir(self, tournoi_id: TournoiId, nom: str) -> FormatTournoi:
        """Capture le déroulé d'un tournoi en format de bibliothèque (« c'est permanent »).

        Idempotent par nom : promouvoir deux fois sous le même nom **met à jour** le format au lieu
        d'accumuler des homonymes. La mise à jour conserve l'identifiant **et l'origine** du format
        existant (même règle que `modifier`).

        Ne rétroagit sur aucun tournoi : les éditions déjà assemblées gardent leurs phases
        (ADR-0060 §3). Lève `TournoiIntrouvable`, `TournoiSansPhase` si le tournoi n'a aucune phase
        à capturer.
        """
        self._tournoi_existant(tournoi_id)
        phases = self._phases.par_tournoi(tournoi_id)
        if not phases:
            raise TournoiSansPhase(
                f"Le tournoi {tournoi_id} n'a aucune phase : il n'y a pas de déroulé à promouvoir."
            )
        capture = FormatTournoi.de_phases(nom, phases)
        existant = self._formats.par_nom(capture.nom)
        if existant is None:
            return self._formats.ajouter(capture)
        return self._formats.enregistrer(existant.modifier(capture.nom, capture.etapes))

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

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
