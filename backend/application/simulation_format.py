"""Service applicatif Simulation de format — « le format tient-il à N archers ? » (E01US024).

Le CA : *« je veux être sûr de pouvoir lancer une simulation du format du tournoi une fois les
phases et le nombre d'inscrits donnés »*. La simulation révèle ce qu'aucune relecture ne donne — le
format **tient-il** à cet effectif, **combien de duels au total** (donc quelle charge pour les
scoreurs et les cibles), combien de tours, et le **classement 1→N effectivement produit**.

**Aucun moteur n'est écrit ici.** Tout existe déjà : `fabriquer_harnais_simulation` (E15US002,
ADR-0054) fournit le substrat in-memory, `ServicePilotageSimulation` (E15US003, ADR-0055) fournit le
bot qui joue les volées et tranche les duels. Ce service **compose** les deux sur un tournoi qui
n'existe nulle part.

⚠️ **Ce que la simulation mesure vraiment — et sa limite d'aujourd'hui.** Elle joue le format sur le
moteur **réel**, celui du jour J. Or ce moteur **n'a pas encore de consommateur de `Phase.sources`**
côté duels : `ServiceSaisieDuels._decor` ensemence chaque tableau avec **tous** les archers en lice,
sans regarder le prélèvement déclaré. Un format qui dit « les rangs 1 à 8 au tableau » se joue donc
aujourd'hui à 12 si 12 archers sont classés. C'est `# DETTE-028` — le catalogue de types et le
routing sont livrés sans consommateur —, et cette US ne la résorbe pas : elle la **rend visible**.
Chaque `ToursPhase` porte donc l'effectif **projeté** à côté de l'effectif **constaté**, et l'écran
signale l'écart. Taire la divergence donnerait un chiffre de duels faux à qui dimensionne ses
scoreurs ; l'afficher dit exactement ce que l'outil sait et ce qu'il ne sait pas encore.

**Pourquoi le garde-fou d'ADR-0054 §4 ne s'applique pas ici.** Il interdit de simuler un tournoi
déjà démarré, pour ne pas interférer avec une compétition. Il n'y a ici **aucun tournoi réel** : le
tournoi simulé naît dans le harnais et meurt avec lui. La non-persistance reste structurelle — ce
service ne reçoit aucun repository SQL, seulement la bibliothèque de formats, en **lecture**.

**Pourquoi `ServiceJeuEssai` n'est pas réutilisé pour les archers fictifs.** La note de l'US le
prévoyait (« il n'y a qu'à composer les deux ») ; le code ne s'y prête pas. `ServiceJeuEssai` pilote
des **services** (`ServiceTournois`, `ServiceDeparts`, `ServiceClubs`, `ServiceInscriptions`…), pas
des repositories : le brancher sur le harnais supposerait d'élargir `HarnaisSimulation` de trois
magasins (clubs, départs, inscriptions) et d'instancier six services — pour obtenir des noms. Or un
format ne connaît ni départs ni clubs ni quotas : ces règles n'ont rien à valider ici. La génération
locale (`_peupler`) tient en une vingtaine de lignes, reste déterministe (`random.Random(graine)`,
règle 9) et n'emprunte aucune règle métier à qui que ce soit. Arbitrage tranché en cours d'US et
consigné à l'ADR-0063 §5.
"""

from __future__ import annotations

import datetime
import random
from dataclasses import dataclass

from application.erreurs import EffectifSimulationInvalide, FormatIntrouvable
from application.pilotage_simulation import EtatSession, ServicePilotageSimulation
from application.simulation import HarnaisSimulation, UsineHarnais
from domain.anomalie import Gravite
from domain.archer import Archer
from domain.blason import Blason
from domain.categorie import Categorie, CategorieId
from domain.classement import Classement
from domain.deroule import ProjectionDeroule
from domain.format_tournoi import FormatTournoi, FormatTournoiId
from domain.phase import TypePhase
from domain.ports import FormatTournoiRepository
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

GRAINE_DEFAUT = 20260801
"""Graine par défaut : un même format simulé deux fois rend le **même** déroulé (règle 9)."""

EFFECTIF_MAX = 200
"""Plafond d'effectif simulable.

Un format se joue intégralement — volées puis duels — sur le thread de la requête ; le coût croît
linéairement avec l'effectif et le barème (120 archers pour 20 volées : 2 400 volées, plus les
duels).
Le plafond n'est pas une règle métier mais une **borne de service** : un `effectif` vient du client
et rien d'autre ne le borne (même raison que le refus d'un `frozenset(range(…))` dans
`SourcePhase.intervalle`). 200 couvre très largement un tournoi de club (le plus gros oracle du
projet en compte 120)."""

_NOMS = (
    "Durand",
    "Lefèvre",
    "Moreau",
    "Petit",
    "Roux",
    "Girard",
    "Bonnet",
    "Dupuis",
    "Lambert",
    "Fontaine",
    "Rousseau",
    "Blanc",
    "Garnier",
    "Chevalier",
    "Robin",
)
_PRENOMS = (
    "Camille",
    "Alex",
    "Manon",
    "Théo",
    "Léa",
    "Noah",
    "Jade",
    "Lucas",
    "Chloé",
    "Hugo",
    "Anaïs",
    "Nathan",
    "Sarah",
    "Yanis",
    "Inès",
)


@dataclass(frozen=True)
class ToursPhase:
    """Combien de tours une phase a **réellement** joués, et combien de duels y ont été tranchés.

    `effectif_projete` est ce que le **schéma** annonçait pour cette phase ; `effectif` ce que la
    simulation a **constaté**. Les deux doivent coïncider — quand ils divergent, c'est que le moteur
    d'exécution n'honore pas encore le prélèvement déclaré (`# DETTE-028` : aucun consommateur de
    `Phase.sources` côté duels ; `ServiceSaisieDuels._decor` ensemence le tableau avec **tous** les
    archers en lice, quelle que soit la source). L'écart est rendu au client plutôt que tu, parce
    qu'un chiffre faux et silencieux est pire qu'un chiffre discuté (`ecart` ci-dessous).
    """

    ordre: int
    type: TypePhase
    effectif: int
    effectif_projete: int | None
    tours: int
    duels: int

    @property
    def ecart(self) -> bool:
        """Vrai si la simulation n'a pas joué l'effectif que le schéma annonçait."""
        return self.effectif_projete is not None and self.effectif_projete != self.effectif


@dataclass(frozen=True)
class ResultatSimulationFormat:
    """Ce que le format produit à cet effectif — la réponse aux quatre questions du CA.

    `projection` est jointe pour que l'écran affiche le **même** schéma que le diagnostic, sans
    second appel : la simulation confirme ou contredit ce que le dessin annonçait.
    """

    format_id: FormatTournoiId
    nom: str
    effectif: int
    graine: int
    duels_total: int
    volees_total: int
    phases: tuple[ToursPhase, ...]
    classement: Classement
    projection: ProjectionDeroule


class ServiceSimulationFormat:
    """Cas d'usage : jouer un format de bibliothèque sur N archers fictifs, sans rien persister."""

    def __init__(
        self,
        formats: FormatTournoiRepository,
        usine_harnais: UsineHarnais,
        pilotage: ServicePilotageSimulation,
    ) -> None:
        # Le repository des formats est le **seul** accès au réel, en lecture. Rien n'écrit.
        self._formats = formats
        self._usine_harnais = usine_harnais
        self._pilotage = pilotage

    def simuler(
        self,
        format_id: FormatTournoiId,
        effectif: int,
        graine: int = GRAINE_DEFAUT,
    ) -> ResultatSimulationFormat:
        """Joue le format sur `effectif` archers fictifs et rend ce qu'il a produit.

        Lève `FormatIntrouvable` (404), `EffectifSimulationInvalide` (422) hors de [2, 200], et la
        première anomalie **bloquante** du format (`DomainError` → 422) : on ne simule pas un
        déroulé qu'aucun tournoi ne pourrait recevoir — le diagnostic est là pour ça, et il dit
        pourquoi.
        """
        format_tournoi = self._formats.par_id(format_id)
        if format_tournoi is None:
            raise FormatIntrouvable(f"Aucun format de tournoi d'identifiant {format_id}.")
        _exiger_effectif(effectif)
        projection = format_tournoi.projeter(effectif)
        for anomalie in projection.anomalies:
            if anomalie.gravite is Gravite.BLOQUANTE:
                raise anomalie.erreur

        harnais = self._usine_harnais()
        tournoi = _fonder(harnais, format_tournoi, effectif, graine)
        session = self._pilotage.ouvrir_sur_harnais(harnais, tournoi, graine)
        try:
            final = self._pilotage.terminer(session.session_id)
            return ResultatSimulationFormat(
                format_id=format_id,
                nom=format_tournoi.nom,
                effectif=effectif,
                graine=graine,
                duels_total=final.progression.duels_faits,
                volees_total=final.progression.volees_faites,
                phases=_phases_jouees(final, harnais, tournoi, projection),
                classement=final.classement,
                projection=projection,
            )
        finally:
            # La session vit le temps de l'appel : la retirer libère le harnais, et empêche qu'une
            # simulation de format encombre le registre du cockpit (E15US003), qui n'en sait rien.
            self._pilotage.arreter(session.session_id)


def _exiger_effectif(effectif: int) -> None:
    if effectif < 2 or effectif > EFFECTIF_MAX:
        raise EffectifSimulationInvalide(
            f"Simuler un format demande entre 2 et {EFFECTIF_MAX} archers (reçu {effectif}) : "
            "en dessous il n'y a pas de tournoi, au-dessus le rejeu ne tiendrait pas dans une "
            "requête."
        )


def _fonder(
    harnais: HarnaisSimulation, format_tournoi: FormatTournoi, effectif: int, graine: int
) -> Tournoi:
    """Fonde de toutes pièces, **dans le harnais**, le tournoi éphémère sur lequel le format tourne.

    Le minimum vital pour que le bot tourne : un tournoi, une catégorie reliée à un blason (le bot y
    lit les zones légales), les archers, et les phases du format. Ni salle, ni départs, ni
    inscriptions — le bot n'en consomme aucun (il tire les volées et tranche les duels depuis le
    classement), et en fabriquer serait décrire un tournoi qu'on ne simule pas.
    """
    tournoi = harnais.tournois.ajouter(
        Tournoi(
            nom=f"Simulation — {format_tournoi.nom}",
            date=datetime.date(2000, 1, 1),
            statut=StatutTournoi.BROUILLON,
        )
    )
    assert tournoi.id is not None, "Le magasin in-memory attribue un identifiant."
    blason = harnais.blasons.ajouter(
        Blason.creer(tournoi_id=tournoi.id, nom="Blason de simulation", taille=0.25, capacite=1)
    )
    categorie = harnais.categories.ajouter(
        Categorie.creer(tournoi_id=tournoi.id, libelle="Simulation", blason_id=blason.id)
    )
    assert categorie.id is not None, "Le magasin in-memory attribue un identifiant."
    _peupler(harnais, tournoi.id, categorie.id, effectif, graine)
    for phase in format_tournoi.appliquer(tournoi.id):
        harnais.phases.ajouter(phase)
    return tournoi


def _peupler(
    harnais: HarnaisSimulation,
    tournoi_id: TournoiId,
    categorie_id: CategorieId,
    effectif: int,
    graine: int,
) -> None:
    """Crée `effectif` archers fictifs, **déterministes** à graine égale (règle 9).

    Les noms viennent de deux listes fermées et d'un compteur : deux archers homonymes ne gênent
    personne dans une simulation, et l'unicité de licence n'est pas une règle du domaine `Archer`.
    """
    alea = random.Random(graine)
    for numero in range(1, effectif + 1):
        harnais.archers.ajouter(
            Archer.creer(
                nom=alea.choice(_NOMS),
                prenom=f"{alea.choice(_PRENOMS)} {numero}",
                tournoi_id=tournoi_id,
                categorie_id=categorie_id,
            )
        )


def _phases_jouees(
    final: EtatSession,
    harnais: HarnaisSimulation,
    tournoi: Tournoi,
    projection: ProjectionDeroule,
) -> tuple[ToursPhase, ...]:
    """Compte, par phase, les tours et les duels **réellement** joués par le bot.

    Le compte vient de l'état des tableaux — pas de la projection : c'est tout l'intérêt de la
    simulation, confirmer (ou démentir) ce que le schéma annonçait.

    ⚠️ `EtatTableau` ne porte **pas** son `phase_id` : les tableaux sont rendus dans l'ordre des
    phases de duels jouables, une phase non jouable étant **sautée** (`_tableaux`). L'appariement se
    fait donc par consommation ordonnée, jamais par index dans la liste des phases — un `zip` naïf
    décalerait tout dès la première phase sautée.
    """
    assert tournoi.id is not None
    restants = list(final.tableaux)
    projetes = {bloc.ordre: bloc.effectif for bloc in projection.blocs}
    phases: list[ToursPhase] = []
    for phase in sorted(harnais.phases.par_tournoi(tournoi.id), key=lambda p: p.ordre):
        projete = projetes.get(phase.ordre)
        if phase.type is not TypePhase.ELIMINATION_DIRECTE or not restants:
            phases.append(
                ToursPhase(phase.ordre, phase.type, len(final.classement.lignes), projete, 0, 0)
            )
            continue
        etat = restants.pop(0)
        # Les duels **réellement tirés** (`duel is not None`) : ni les byes, ni les matchs dont les
        # occupants ne sont pas connus. Compter `effectif - 1` serait plus simple et **faux** — la
        # profondeur de podium (`ProfondeurPodium`) ajoute une petite finale, que la simulation est
        # précisément là pour révéler avant que les scoreurs ne la découvrent le jour J.
        joues = sum(1 for match in etat.duels if match.duel is not None)
        phases.append(
            ToursPhase(phase.ordre, phase.type, etat.effectif, projete, etat.nb_tours, joues)
        )
    return tuple(phases)
