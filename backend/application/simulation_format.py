"""Simule un format sur le moteur **réel**, sur un tournoi qui n'existe nulle part (ADR-0063).
L'isolation tient au passage par `ouvrir_sur_harnais`, pas à l'absence de repository.

⚠️ **La simulation RÉVÈLE un écart qu'elle ne corrige pas** : le moteur de duels ensemence avec tous
les archers en lice sans lire le prélèvement déclaré (`DETTE-028`). D'où l'effectif **projeté** à
côté du **constaté** sur chaque `ToursPhase`.
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

_TYPES_DEROULABLES = TYPES_JOUES - {
    TypePhase.POULES,
    TypePhase.BIG_SHOOT_OFF,
    # DETTE-066 — ⚠️ **3ᵉ retrait à la main, et il a été oublié une fois** : `SUISSE` entre dans
    # `TYPES_JOUES` dès que le service le déroule, alors que `fabriquer_harnais_simulation` ne
    # construit **aucun** `ServiceSuisse`. Sans ce terme, l'atelier annonçait `joue=True, 0 tour,
    # 0 duel` — des zéros lus comme un constat — et le bandeau « le moteur ne sait pas encore
    # dérouler ce type » **disparaissait**. La capacité manquante au registre est « le **bot**
    # sait-il simuler ce type ? », distincte de « un service de production le déroule-t-il ? ».
    TypePhase.SUISSE,
    # DETTE-066 — ⚠️ **4ᵉ retrait, annoncé nommément par le commentaire ci-dessus.** E05US027
    # rend la colline jouable en production, et `fabriquer_harnais_simulation` ne construit
    # toujours aucun `ServiceColline`.
    #
    # ⚠️ **Cette fois l'oubli n'était pas possible** : le garde-fou posé en E05US035 est **tombé**
    # dès la bascule du registre, avant qu'une ligne de simulation soit touchée. Le test rend le
    # retrait manuel **visible et daté**, ce qui était tout ce qui manquait au remède.
    TypePhase.COLLINE,
}
"""Les types que **le bot de simulation** sait réellement jouer aujourd'hui.

⚠️ **Deux questions distinctes, et les confondre a fait mentir cet écran.** `TYPES_JOUES` répond «
un service de **production** sait jouer ce type » ; ce site demande « le **bot** sait-il le jouer ?
». Une phase de poules tombait donc dans la branche « pas d'état » et sortait `joue=True, tours=0`
— l'atelier affichait « 0 tour » comme un **constat**, et le bandeau d'avertissement disparaissait.
Le retrait est explicite faute d'une capacité « le bot sait simuler » au registre (`# DETTE-028`).
"""

GRAINE_DEFAUT = 20260801
"""Graine par défaut : un même format simulé deux fois rend le **même** déroulé (règle 9)."""

EFFECTIF_MAX = 200
"""Plafond d'effectif simulable.

Un format se joue intégralement — volées puis duels — sur le thread de la requête, et le coût croît
linéairement avec l'effectif et le barème. Ce n'est pas une règle métier mais une **borne de
service** : un `effectif` vient du client et rien d'autre ne le borne (même raison que le refus
d'un `frozenset(range(…))` dans `SourcePhase.intervalle`). 200 couvre très largement un tournoi de
club.
"""

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

    `effectif_projete` est ce que le **schéma** annonçait ; `effectif` ce que la simulation a
    **constaté**. Les deux doivent coïncider — quand ils divergent, c'est que le moteur n'honore
    pas certains prélèvements (`# DETTE-028` : `le_reste` et `par_issue_de_tour` n'ont aucun
    consommateur côté duels). L'écart est rendu au client plutôt que tu, parce qu'un chiffre faux
    et silencieux est pire qu'un chiffre discuté.
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

        Compare l'**effectif** et le **nombre de tours**, et signale une phase que le moteur ne
        sait pas jouer du tout. ⚠️ **Les duels sont hors du prédicat**, alors qu'ils sont affichés
        : le schéma compte les duels de l'**arbre** quand le moteur y ajoute ce que la profondeur
        impose (`# DETTE-035`). Les inclure rendait `ecart` vrai sur 100 % des simulations — le
        test de non-régression en devenait tautologique.
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

    Ce n'est pas une incohérence du format : `ServiceFormats.appliquer` l'accepte. C'est une limite
    du **bot** — il tire ses volées d'un barème, et sans phase de qualification il n'en a aucun. Le
    contrôle est remonté **avant** l'ouverture de session pour deux raisons : le 404 de
    `PhaseQualificationAbsente` est un contresens ici, et son message parle d'un tournoi que
    l'organisateur ne verrait nulle part.
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

    Le compte vient de l'état des tableaux, pas de la projection. L'appariement se fait par
    **`phase_id`** — consommer une liste ordonnée subissait le même décalage qu'un `zip` naïf,
    `_tableaux` sautant une phase non jouable sans dire laquelle. `joue` distingue « joué à 0 duel
    » de « le moteur ne sait pas dérouler ce type », et ⚠️ il se déduit du **type**, pas de
    l'absence de tableau — une élimination directe peut n'avoir rien eu à jouer.
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
