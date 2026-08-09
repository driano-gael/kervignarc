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
moteur **réel**, celui du jour J. ⚠️ **Depuis E05US020 il honore les prélèvements par rangs**
(ADR-0068) ; ce qui suit ne vaut donc plus que pour `le_reste`, `par_issue_de_tour` et les types
qu'aucun service ne déroule. Le moteur **n'a pas de consommateur** de ces sources-là
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
service ne reçoit aucun repository SQL en propre, seulement la bibliothèque de formats, en
**lecture**. Nuance à ne pas surestimer : `ServicePilotageSimulation`, qu'il compose, **détient**
des repositories SQL — ils ne sont lus que par `demarrer`, que ce chemin n'emprunte pas. L'isolation
tient donc parce qu'on appelle `ouvrir_sur_harnais`, pas parce que le chemin SQL serait absent.

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

from application.erreurs import (
    EffectifSimulationInvalide,
    FormatIntrouvable,
    FormatNonSimulable,
)
from application.pilotage_simulation import EtatSession, ServicePilotageSimulation
from application.simulation import HarnaisSimulation, UsineHarnais
from domain.anomalie import Gravite
from domain.archer import Archer
from domain.blason import Blason
from domain.categorie import Categorie, CategorieId
from domain.classement import Classement
from domain.contrat_phase import TYPES_JOUES
from domain.depart import Depart, DepartId
from domain.deroule import ProjectionDeroule
from domain.format_tournoi import FormatTournoi, FormatTournoiId
from domain.inscription import Inscription
from domain.phase import TypePhase
from domain.ports import FormatTournoiRepository
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

_TYPES_DEROULABLES = TYPES_JOUES
"""Les types que le bot sait réellement jouer aujourd'hui.

Dérivé du registre de contrat (`domain/contrat_phase.py`, ADR-0083) : montés, ou lus, ou les deux.
Tout le reste du catalogue d'E05US015 se **compose** mais ne se **déroule** pas (`# DETTE-028`) :
c'est ce que `ToursPhase.joue` rend au client, plutôt que des zéros qui passeraient pour des
constats. La table s'élargit **d'elle-même** au fur et à mesure que les moteurs trouvent leur
consommateur — elle n'est plus à tenir à jour à la main, ce qui était la 5ᵉ occasion de diverger."""

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
    d'exécution n'honore pas **certains** prélèvements (`# DETTE-028` — depuis E05US020 les rangs
    le sont ; restent `le_reste` et `par_issue_de_tour` : aucun consommateur de
    `Phase.sources` côté duels ; `ServiceSaisieDuels._decor` ensemence le tableau avec **tous** les
    archers en lice, quelle que soit la source). L'écart est rendu au client plutôt que tu, parce
    qu'un chiffre faux et silencieux est pire qu'un chiffre discuté (`ecart` ci-dessous).
    """

    ordre: int
    type: TypePhase
    effectif: int
    effectif_projete: int | None
    tours: int
    tours_projetes: int | None
    duels: int
    duels_projetes: int | None
    joue: bool

    @property
    def ecart(self) -> bool:
        """Vrai si la simulation n'a pas déroulé ce que le schéma annonçait.

        Compare l'**effectif** et le **nombre de tours** — et signale une phase que le moteur ne
        sait pas jouer du tout (`joue`).

        ⚠️ **Les duels sont délibérément hors du prédicat**, alors qu'ils sont affichés. Le schéma
        compte les duels de l'**arbre** (`effectif - 1`) ; le moteur y ajoute ce que la politique de
        profondeur impose — une petite finale au preset `podium`, **toute la cascade de placement**
        si la phase déclare un classement intégral (E06US006 : la profondeur se lit désormais sur la
        phase, elle n'est plus câblée). L'écart n'est donc plus « d'une unité » dans tous les cas,
        mais il reste **structurel et attendu** sur toute phase de tableau — `# DETTE-035`.

        Un premier jet l'incluait : `ecart` devenait vrai sur 100 % des simulations, y compris pour
        un format parfaitement composé, et l'avertissement — dont l'objet est de signaler la
        divergence `# DETTE-028` — se noyait dans son propre bruit. Pire, il rendait le test de
        non-régression de cette dette **tautologique**, alors qu'on attend précisément qu'il échoue
        le jour où le moteur honorera les sources.

        Les deux comptes restent rendus côte à côte : c'est à l'organisateur de lire « 15 annoncés,
        16 joués » et d'en tirer sa charge réelle.
        """
        return not self.joue or any(
            projete is not None and projete != constate
            for projete, constate in (
                (self.effectif_projete, self.effectif),
                (self.tours_projetes, self.tours),
            )
        )


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

        Lève `FormatIntrouvable` (404), `EffectifSimulationInvalide` (400) hors de [2, 200],
        `FormatNonSimulable` (400) si aucune qualification n'est décrite, et la
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

        _exiger_qualification(format_tournoi)

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


def _exiger_qualification(format_tournoi: FormatTournoi) -> None:
    """Un format sans qualification est **applicable**, mais pas **simulable**.

    Ce n'est pas une incohérence du format : `ServiceFormats.appliquer` l'accepte (il ne refuse que
    de *retirer* une qualification à un tournoi qui en a une). C'est une limite du **bot** — il tire
    ses volées d'un barème, et sans phase de qualification il n'en a aucun (`ouvrir_sur_harnais` →
    `PhaseQualificationAbsente`).

    Le contrôle est remonté **avant** l'ouverture de session pour deux raisons : le 404 de
    `PhaseQualificationAbsente` est un contresens ici (rien n'est « introuvable », et il n'y a même
    pas de tournoi), et son message parle d'un tournoi que l'organisateur ne verrait nulle part.
    """
    if not any(etape.type is TypePhase.QUALIFICATION for etape in format_tournoi.etapes):
        raise FormatNonSimulable(
            "Ce format ne décrit aucune qualification : la simulation n'a alors aucun barème d'où "
            "tirer des scores. Le format reste applicable à un tournoi — c'est le rejeu qui ne "
            "sait pas le dérouler."
        )


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
    # **Un créneau** pour la simulation (E01US025, ADR-0075) : le format s'applique à des départs,
    # pas à un tournoi. Un seul suffit ici — on simule un déroulé, pas une logistique de journée.
    # Créé **avant** le peuplement : c'est sur lui que les archers s'inscrivent.
    depart = harnais.departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=0, horaire="09:00")
    )
    assert depart.id is not None, "Le magasin in-memory attribue un identifiant."
    _peupler(harnais, tournoi.id, categorie.id, depart.id, effectif, graine)
    # **Un déroulé, puis son avancement** (ADR-0076) : le format définit les étapes du tournoi
    # simulé, et le créneau unique reçoit une instance par étape. La simulation n'a qu'un départ —
    # on simule un déroulé, pas une logistique de journée.
    for etape in format_tournoi.appliquer(tournoi.id):
        posee = harnais.deroules.ajouter(etape)
        harnais.phases.ajouter(posee.instancier(depart.id))
    return tournoi


def _peupler(
    harnais: HarnaisSimulation,
    tournoi_id: TournoiId,
    categorie_id: CategorieId,
    depart_id: DepartId,
    effectif: int,
    graine: int,
) -> None:
    """Crée `effectif` archers fictifs, **déterministes** à graine égale (règle 9).

    Les noms viennent de deux listes fermées et d'un compteur : deux archers homonymes ne gênent
    personne dans une simulation, et l'unicité de licence n'est pas une règle du domaine `Archer`.
    """
    alea = random.Random(graine)
    for numero in range(1, effectif + 1):
        archer = harnais.archers.ajouter(
            Archer.creer(
                nom=alea.choice(_NOMS),
                prenom=f"{alea.choice(_PRENOMS)} {numero}",
                tournoi_id=tournoi_id,
                categorie_id=categorie_id,
            )
        )
        assert archer.id is not None, "Le magasin in-memory attribue un identifiant."
        # ⚠️ **L'inscrire sur le créneau** : depuis ADR-0075 c'est l'inscription qui fait entrer un
        # archer au classement d'un départ, pas son rattachement au tournoi. Sans elle, la
        # simulation tournerait sur un classement vide — sans erreur, ce qui est le pire cas.
        harnais.inscriptions.ajouter(Inscription.creer(archer.id, depart_id))


def _phases_jouees(
    final: EtatSession,
    harnais: HarnaisSimulation,
    tournoi: Tournoi,
    projection: ProjectionDeroule,
) -> tuple[ToursPhase, ...]:
    """Compte, par phase, les tours et les duels **réellement** joués par le bot.

    Le compte vient de l'état des tableaux — pas de la projection : c'est tout l'intérêt de la
    simulation, confirmer (ou démentir) ce que le schéma annonçait.

    L'appariement se fait par **`phase_id`**, que `EtatTableau` porte depuis E01US024. Un premier
    jet consommait une liste ordonnée (`restants.pop(0)`) en croyant échapper au décalage d'un `zip`
    naïf — c'est **le même** décalage : `_tableaux` saute une phase non jouable sans dire laquelle,
    et tout ce qui suit glisse d'un cran. Relevé par trois axes de la revue.

    `joue` distingue « joué à 0 duel » de « le moteur ne sait pas dérouler ce type ». Les six types
    d'E05US015 (poules, suisse, colline, big shoot off, barrage, échauffement) n'ont **aucun**
    moteur d'exécution (`# DETTE-028`) : sans ce drapeau, ils s'affichaient « — tours, — duels »
    comme des **faits**, et l'écart restait muet puisque leur effectif « constaté » était l'effectif
    entier recopié. C'est précisément le cas où l'organisateur a le plus besoin d'être averti.

    ⚠️ Il se déduit du **type**, pas de l'absence de tableau. Une élimination directe peut être
    sautée par `_tableaux` faute de duellistes classés (`EffectifTableauInvalide`) : la conclure
    « type non déroulable » serait une cause fausse — le moteur sait la jouer, il n'a simplement
    rien eu à jouer.
    """
    assert tournoi.id is not None
    par_phase = {etat.phase_id: etat for etat in final.tableaux}
    blocs = {bloc.ordre: bloc for bloc in projection.blocs}
    phases: list[ToursPhase] = []
    for phase in sorted(harnais.phases.par_tournoi(tournoi.id), key=lambda p: p.ordre):
        bloc = blocs.get(phase.ordre)
        projete = None if bloc is None else bloc.effectif
        tours_projetes = None if bloc is None else len(bloc.tours) or None
        duels_projetes = (
            None if bloc is None or not bloc.tours else sum(t.duels for t in bloc.tours)
        )
        etat = par_phase.get(phase.id) if phase.id is not None else None
        if etat is None:
            phases.append(
                ToursPhase(
                    ordre=phase.ordre,
                    type=phase.type,
                    effectif=len(final.classement.lignes),
                    effectif_projete=projete,
                    tours=0,
                    tours_projetes=tours_projetes,
                    duels=0,
                    duels_projetes=duels_projetes,
                    joue=phase.type in _TYPES_DEROULABLES,
                )
            )
            continue
        # Les duels **réellement tirés** (`duel is not None`) : ni les byes, ni les matchs dont les
        # occupants ne sont pas connus. Compter `effectif - 1` serait plus simple et **faux** — la
        # profondeur de podium (`ProfondeurPodium`) ajoute une petite finale, que la simulation est
        # précisément là pour révéler avant que les scoreurs ne la découvrent le jour J.
        joues = sum(1 for match in etat.duels if match.duel is not None)
        phases.append(
            ToursPhase(
                ordre=phase.ordre,
                type=phase.type,
                effectif=etat.effectif,
                effectif_projete=projete,
                tours=etat.nb_tours,
                tours_projetes=tours_projetes,
                duels=joues,
                duels_projetes=duels_projetes,
                joue=True,
            )
        )
    return tuple(phases)
