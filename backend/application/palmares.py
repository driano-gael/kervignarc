"""Service **Palmarès** — reconstruit ce que chaque phase a décerné, ne rejoue rien du domaine.

⚠️ **Une phase ne décerne ses rangs que si RIEN ne prélève dedans** (ADR-0085) : tant qu'une phase
avale puise dans celle-ci, ses rangs sont provisoires et n'ont pas leur place au palmarès. C'est ce
qui distingue « la phase est finie » de « la phase a décerné », et les confondre publierait au mur
un classement que la compétition va encore modifier.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from application.big_shoot_off import LecteurEtatBigShootOff
from application.classements import ServiceClassement
from application.erreurs import (
    PhaseIntrouvable,
    PhasePasReglee,
    PhasePasUnBigShootOff,
    PrelevementEnAttente,
    TournoiIntrouvable,
    TournoiSansDepart,
)
from application.prelevement import tranche
from application.routage import LecteurRencontresARouter
from application.saisie_duels import ServiceSaisieDuels
from domain.categorie import CategorieId
from domain.club import ClubId
from domain.contrat_phase import TYPES_CLASSANTS_LUS, TYPES_RECONSTRUCTIBLES
from domain.depart import DepartId
from domain.erreurs import DomainError, EffectifTableauInvalide
from domain.palmares import (
    OriginePalmares,
    Palmares,
    PositionPhase,
    ResultatPhase,
    calculer_palmares,
)
from domain.participant import GenreParticipant
from domain.phase import Phase, TypePhase
from domain.podium import ReglagePodiums
from domain.politiques import Aggregation, AggregationParQualification
from domain.ports import (
    ClubRepository,
    DepartRepository,
    DuelRepository,
    GenerateurPalmares,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)

_TYPES_CLASSANTS_AU_PALMARES: frozenset[TypePhase] = TYPES_CLASSANTS_LUS - (
    TYPES_RECONSTRUCTIBLES | {TypePhase.QUALIFICATION, TypePhase.BIG_SHOOT_OFF}
)
"""Les types dont le palmarès lit le **classement de phase** plutôt qu'un arbre (E05US026).

Aujourd'hui les **poules** et le **système suisse** : ni l'un ni l'autre n'a d'arbre à rejouer, et
tous deux rendent un `ClassementSource` complet. **Dérivée, pas énumérée** — un format qui devient
`classement_lisible` sans être reconstructible entre ici automatiquement. Les trois soustraits ont
déjà leur chemin : les tableaux (rejeu d'arbre), la qualification (base du palmarès) et le Big
Shoot Off (ses rangs viennent des éliminations).
"""

_TYPES_RECONSTRUCTIBLES = TYPES_RECONSTRUCTIBLES
"""Les types de phase dont ce service sait **rejouer l'arbre** aujourd'hui.

Dérivé du registre de contrat (ADR-0083) : conjonction d'un décor en arbre **et** d'un service qui
le monte. **Liste blanche**, à rebours de `produit_un_classement` écrit en négatif : là-bas l'oubli
probable est d'ajouter un vrai format, ici c'est de croire lire une phase dont aucun moteur ne
déroule le résultat. Un type absent ne casse pas le palmarès — il n'y apporte rien.
"""


class ServicePalmares:
    """Cas d'usage du palmarès : consulter le classement final d'un tournoi."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
        duels: DuelRepository,
        generateur: GenerateurPalmares,
        departs: DepartRepository,
        clubs: ClubRepository,
        aggregation: Aggregation | None = None,
        big_shoot_off: LecteurEtatBigShootOff | None = None,
        rencontres: Mapping[TypePhase, LecteurRencontresARouter] | None = None,
    ) -> None:
        self._tournois = tournois
        # Le classement — donc le palmarès — vit par départ depuis ADR-0075.
        self._departs = departs
        # E16US014 : de quoi **nommer** les podiums de club. Référentiel global (E02US001),
        # relu à chaque palmarès — une liste de clubs, sans commune mesure avec DETTE-031.
        self._clubs = clubs
        self._phases = phases
        self._classements = classements
        self._saisie_duels = saisie_duels
        # Lu pour une seule question : **un tir a-t-il été enregistré** dans cette phase ? Le
        # tableau reconstruit ne sait pas le dire — un match peut y porter un vainqueur sans
        # qu'une flèche ait été tirée (bye, walkover de forfait).
        self._duels = duels
        self._generateur = generateur
        # Politique de **départage des sortis au même tour** (ADR-0067), injectée par la
        # composition root — un format de tournoi est de la configuration (règle 2). Elle n'est pas
        # encore *réglable* par l'organisateur : `Phase` ne persiste aucune `config.policies`
        # générique (seul `barrage_jusqu_au` l'est, E06US003), donc il n'existe aucun champ où
        # écrire le choix. Injectable aujourd'hui, réglable le jour où les phases porteront leur
        # config — c'est un manque de **surface**, pas de conception.
        self._aggregation = (
            aggregation if aggregation is not None else AggregationParQualification()
        )
        # E05US028 : le Big Shoot Off entre au palmarès par son **propre** résultat, pas par la
        # reconstruction d'un arbre qu'il n'a pas.
        #
        # ⚠️ **Au constructeur, et non par un `brancher_…` tardif.** Le branchement tardif de
        # `ServiceSaisieDuels.brancher_lecteur` existe pour casser un **cycle** ; il n'y en a pas
        # ici. L'imiter sans sa raison aurait échangé un contrôle du compilateur contre un test de
        # câblage, pour rien. `None` reste licite : c'est le régime de tout montage sans Big Shoot
        # Off (harnais de simulation, tests de tableau), et il se lit dans la signature.
        self._big_shoot_off = big_shoot_off
        # E05US026 : de quoi savoir si une phase **à rencontres** est allée à son terme. C'est le
        # **même port** que celui du routage (`LecteurRencontresARouter`), réutilisé plutôt que
        # dupliqué : la question « reste-t-il quelque chose à tirer ? » est la même des deux côtés,
        # et deux calculs concurrents finiraient par se contredire sur qui a fini.
        #
        # ⚠️ **Absent ⇒ prudent, pas optimiste** : sans lecteur, `_est_epuisee` rend `False`, donc
        # `en_lice=True`, donc **aucune médaille**. Un montage incomplet retire un podium ; il n'en
        # invente pas.
        self._rencontres: dict[TypePhase, LecteurRencontresARouter] = dict(rencontres or {})

    def pour_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None
    ) -> Palmares:
        """Renvoie le palmarès d'un tournoi, éventuellement **filtré** à une catégorie.

        Lève `TournoiIntrouvable` si le tournoi manque. Le calcul se fait **toujours en entier**
        (les rangs scratch et de catégorie sont ceux du tournoi complet) ; `categorie_id` ne fait
        que restreindre l'affichage — même parti qu'E06US001, pour ne pas transformer le 1ᵉʳ de sa
        catégorie en 1ᵉʳ tout court.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        # Le palmarès d'un **départ** (ADR-0075) : il s'appuie sur le classement de qualification,
        # qui n'existe plus qu'à cette maille. Le premier départ qui en porte un fait référence
        # tant que la route reste au niveau tournoi — cf. DETTE-045.
        premier = self._premier_depart(tournoi_id)
        qualification = self._classements.pour_depart(premier)
        # ⚠️ **Les phases du même créneau que la qualification**, pas celles du tournoi. Le résultat
        # affiché ne changeait pas — `calculer_palmares` écarte les archers absents du classement de
        # référence —, mais on reconstruisait le tableau de **tous** les créneaux pour les jeter
        # ensuite : sur quatre départs, quatre fois le travail de `ServiceSaisieDuels.reconstruire`
        # (DETTE-031) sur deux routes **publiques**, l'écran et le PDF. Et le résultat n'était juste
        # que par ricochet : un archer engagé sur deux créneaux (cas soutenu, DETTE-046) pouvait se
        # voir attribuer la position acquise dans le tableau de l'autre créneau, les rangs se
        # répétant d'un départ à l'autre.
        phases = self._phases.par_depart(premier)
        resultats = (
            tuple(
                resultat
                for phase in phases
                if phase.type in _TYPES_RECONSTRUCTIBLES
                if (resultat := self._resultat(tournoi_id, phase)) is not None
            )
            + tuple(
                resultat
                for phase in phases
                if phase.type is TypePhase.QUALIFICATION
                if (resultat := self._resultat_qualification(tournoi_id, phase)) is not None
            )
            + tuple(
                resultat
                for phase in phases
                if phase.type is TypePhase.BIG_SHOOT_OFF
                if (resultat := self._resultat_big_shoot_off(tournoi_id, phase)) is not None
            )
            + tuple(
                resultat
                for phase in phases
                if phase.type in _TYPES_CLASSANTS_AU_PALMARES
                if (resultat := self._resultat_classant(tournoi_id, phase, phases)) is not None
            )
        )
        palmares = calculer_palmares(
            qualification, resultats, self._aggregation, self._libelles_club()
        )
        return palmares if categorie_id is None else palmares.pour_categorie(categorie_id)

    def _libelles_club(self) -> Mapping[ClubId, str]:
        """Le nom de chaque club, pour que les podiums de club se **nomment** (E16US014).

        Résolu ici et non à l'écran : le PDF doit nommer ses blocs et n'a pas de front pour le
        faire à sa place. Le référentiel est global et de la taille d'une liste de clubs — la
        lecture est sans commune mesure avec la reconstruction des tableaux (`DETTE-031`).
        """
        return {club.id: club.nom for club in self._clubs.lister() if club.id is not None}

    def reglage_podiums(self, tournoi_id: TournoiId) -> ReglagePodiums:
        """Ce que ce tournoi récompense (E16US014) — lecture d'une seule ligne.

        Servie à part du palmarès plutôt que fondue dedans : `Palmares` est le **résultat sportif**,
        le réglage est de la configuration, et l'écran de réglage doit pouvoir le lire sans payer
        la reconstruction de tous les tableaux (`DETTE-031`).
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi.reglage_podiums

    def definir_reglage_podiums(
        self, tournoi_id: TournoiId, reglage: ReglagePodiums
    ) -> ReglagePodiums:
        """Règle ce que le tournoi récompense et renvoie la valeur retenue (E16US014).

        Aucune garde de statut : le palmarès se recalcule à chaque lecture, changer le réglage ne
        réécrit donc aucun résultat — et ce que le club récompense se décide jusqu'à la remise.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        enregistre = self._tournois.enregistrer(tournoi.definir_reglage_podiums(reglage))
        return enregistre.reglage_podiums

    def imprimer(self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None) -> bytes:
        """Rend le palmarès en **PDF** (CA « affiché et exportable »).

        Même calcul que `pour_tournoi` — un document qui divergerait de l'écran serait pire que
        pas de document du tout : c'est celui-là qu'on affiche au mur et qu'on remet aux archers.
        Le rendu part au port `GenerateurPalmares` ; le service ne connaît ni ReportLab ni HTTP.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._generateur.palmares(
            tournoi.nom,
            self.pour_tournoi(tournoi_id, categorie_id),
            tournoi.reglage_podiums,
        )

    def _premier_depart(self, tournoi_id: TournoiId) -> DepartId:
        """Le premier créneau du tournoi — référence tant que la route reste au niveau tournoi.

        ⚠️ **Raccourci tracé (`DETTE-045`)** : le palmarès est rendu « du tournoi » alors que le
        classement dont il dérive est celui d'un **départ**, donc un tournoi multi-créneaux
        n'affiche que le podium du premier. La question métier a été tranchée le 07/08/2026 —
        *juxtaposé*, quatre départs font quatre podiums —, et le remède se réduit à une route par
        départ (E06US009).
        """
        departs = self._departs.par_tournoi(tournoi_id)
        if not departs:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : il n'y a pas de classement dont tirer un palmarès."
            )
        premier = departs[0]
        assert premier.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
        return premier.id

    def _resultat_big_shoot_off(self, tournoi_id: TournoiId, phase: Phase) -> ResultatPhase | None:
        """Ce qu'un Big Shoot Off a décidé — `None` s'il n'a **rien** décidé (encore) (E05US028).

        ⚠️ **Un `_resultat` propre au format, et non une entrée de `TYPES_RECONSTRUCTIBLES`** :
        cette table est l'alias de « rejouer l'arbre », qu'un Big Shoot Off n'a pas. Ses rangs sont
        **exacts** par construction. Trois écartements : phase illisible, phase où personne n'est
        sorti, et **rescapés** d'une phase en cours. ⚠️ `en_lice` se ferme quand la phase est
        terminée — le reporter tel quel laissait le **vainqueur** en lice, donc sans or.
        """
        if phase.id is None or self._big_shoot_off is None:
            return None
        try:
            etat = self._big_shoot_off.etat(tournoi_id, phase.id)
        except (
            PhaseIntrouvable,
            PrelevementEnAttente,
            PhasePasReglee,
            PhasePasUnBigShootOff,
        ) as exc:
            # Mêmes absorptions que `_resultat`, et **journalisées** pour la même raison : le
            # palmarès est public et projeté en salle, donc une phase ne doit pas éteindre l'écran —
            # mais une phase absente le jour J serait indébogable.
            #
            # ⚠️ **La liste est nominative, et ce n'est pas un détail de style** : écrire
            # `(PhaseIntrouvable, PrelevementEnAttente, ApplicationError)` attrapait **toute**
            # erreur applicative, y compris `DerouleCyclique` que `_resultat` exclut délibérément.
            # `ruff B014` ne le voit pas : il ne résout pas les relations de sous-classe.
            _logger.info("Big Shoot Off %s écarté du palmarès : %s", phase.id, exc)
            return None
        if not any(tireur.rang is not None for tireur in etat.tireurs):
            return None
        positions = tuple(
            PositionPhase(
                archer_id=tireur.archer_id,
                rang_min=tireur.rang if tireur.rang is not None else 1,
                rang_max=tireur.rang if tireur.rang is not None else 1,
                en_lice=tireur.en_lice and not etat.termine,
            )
            for tireur in etat.tireurs
        )
        return ResultatPhase(
            ordre=phase.ordre,
            positions=positions,
            rang_premier=tranche(
                phase, self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id)
            ),
        )

    def _resultat_classant(
        self, tournoi_id: TournoiId, phase: Phase, phases: list[Phase]
    ) -> ResultatPhase | None:
        """Ce qu'une phase **classante sans arbre** a décidé — poules, système suisse (E05US026).

        `# DETTE-031` — une résolution de classement par phase classante, plus une lecture
        d'avancement, sur les deux routes publiques. On lit son **classement de phase**, celui-là
        même qu'un prélèvement consomme : deux calculs pour un même ordre se contrediraient. ⚠️
        `origine` porte la règle « décerne si rien ne prélève dedans », critère **structurel** et
        non par type. Les plages indécises deviennent des **fourchettes**.
        """
        if phase.id is None:
            return None
        resolveur = self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id)
        try:
            source = resolveur(phase.ordre)
        except (
            PhaseIntrouvable,
            PrelevementEnAttente,
            PhasePasReglee,
            EffectifTableauInvalide,
            DomainError,
        ) as exc:
            # Absorptions nominatives, **plus `DomainError`** — un correctif de revue, pas une
            # précaution : les moteurs de format lèvent des erreurs de **domaine**
            # (`ConfigurationSuisseInvalide`, `AppariementImpossible`), qui ne sont pas des
            # `ApplicationError`. La liste d'origine les laissait passer, et une seule phase mal
            # dimensionnée rendait **422 le palmarès du tournoi entier**, PDF compris.
            #
            # ⚠️ `DomainError` est volontairement **le dernier terme** : les autres restent
            # nominatifs, et `DerouleCyclique` continue de **traverser**, comme `_resultat` l'exige.
            _logger.info("Phase classante %s écartée du palmarès : %s", phase.id, exc)
            return None
        if source is None or not source.classement.lignes:
            return None
        # ⚠️ **Une phase qui n'a rien joué ne décerne rien**, et l'oubli de cette garde était un
        # bloquant de revue. `classement_de_suisse` / `classement_de_poules` rendent un ordre
        # **complet** dès la composition — dérivé du classement amont, pas d'un tir. Sans ce
        # contrôle, une phase terminale non commencée posait `origine=DUELS` et `en_lice=False` sur
        # tout le monde, et `Palmares.podium` décernait or, argent et bronze **avant la première
        # flèche**, sur des rangs venus de la qualification du matin. C'est mot pour mot le défaut
        # qu'`OriginePalmares` a été créé pour fermer (E05US025), rouvert par un autre chemin.
        if not self._a_commence(phase):
            return None
        indecises = source.plages_indecises
        # `en_lice` tant que la phase n'est pas allée à son terme : `LignePalmares.decerne` répond à
        # « cet archer a-t-il encore quelque chose devant lui ? », et un rang annoncé avant la fin
        # serait un faux départ. Même parti que `_resultat` pour les tableaux.
        en_cours = not self._est_epuisee(tournoi_id, phase)
        positions = tuple(
            PositionPhase(
                archer_id=ligne.archer_id,
                rang_min=_borne(ligne.rang_scratch, indecises, haute=False),
                rang_max=_borne(ligne.rang_scratch, indecises, haute=True),
                en_lice=en_cours,
            )
            for ligne in source.classement.lignes
            if ligne.rang_scratch is not None
        )
        if not positions:
            return None
        return ResultatPhase(
            ordre=phase.ordre,
            positions=positions,
            origine=OriginePalmares.DUELS
            if _est_terminale(phase, phases)
            else OriginePalmares.QUALIFICATION,
            rang_premier=source.rang_premier,
        )

    def _a_commence(self, phase: Phase) -> bool:
        """Au moins un tir a-t-il été enregistré dans cette phase ?

        Même signal que `_resultat` pour les tableaux, et même dépôt (`numeros_enregistres`) : le
        classement d'une phase à rencontres, lui, est **complet dès la composition** — il dérive du
        classement amont, pas d'un tir. Sans cette question, une phase jamais commencée décernerait
        des rangs venus de la qualification du matin.
        """
        return phase.id is not None and bool(self._duels.numeros_enregistres(phase.id))

    def _est_epuisee(self, tournoi_id: TournoiId, phase: Phase) -> bool:
        """La phase est-elle allée à son terme ? — par le port partagé avec le routage.

        `# DETTE-031` — `rencontres_a_tirer` rejoue l'état complet de la phase, **avec un résolveur
        neuf** : c'est un second rejeu de la chaîne amont, pas une simple lecture d'avancement.
        Prudent par défaut : sans lecteur branché on répond « non », donc les archers restent
        `en_lice` et **aucune médaille n'est décernée** — un montage incomplet retire un podium, il
        n'en invente pas.
        """
        lecteur = self._rencontres.get(phase.type)
        if lecteur is None or phase.id is None:
            return False
        try:
            return lecteur.rencontres_a_tirer(tournoi_id, phase.id).epuisee
        except (
            PhaseIntrouvable,
            PrelevementEnAttente,
            PhasePasReglee,
            EffectifTableauInvalide,
            DomainError,
        ) as exc:
            # ⚠️ **Nominative comme partout ailleurs dans ce fichier**, et le premier jet ne l'était
            # pas : `except ApplicationError` avalait `DerouleCyclique`, à trois lignes du
            # commentaire qui explique que cette erreur doit **traverser** (« une base incohérente
            # doit rester visible »). Sans effet observable — `classement_de_phase` la lève plus
            # tôt — mais c'est la convention du fichier, et une convention qui souffre une
            # exception non écrite ne tient pas longtemps. Relevé en revue.
            _logger.info("Avancement de la phase %s illisible : %s", phase.id, exc)
            return False

    def _resultat_qualification(self, tournoi_id: TournoiId, phase: Phase) -> ResultatPhase | None:
        """Ce qu'une **seconde** qualification a classé — `None` si elle n'a rien à dire encore.

        E05US025 (ADR-0082) : c'est ici que le classement final devient un 1..120. Trois
        écartements : la **qualification de tête** (elle *est* la base du palmarès) ; une phase que
        le résolveur ne sait pas lire ; une phase où **personne n'a marqué**, dont les ex æquo au
        rang 1 donneraient à 60 archers la première place pendant qu'ils tirent. ⚠️ Le critère est
        `total > 0` : une phase où tout le monde aurait manqué resterait dehors — cela retarde.
        """
        if not phase.sources:
            return None
        source = self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id)(
            phase.ordre
        )
        if source is None:
            return None
        lignes = source.classement.lignes
        if not any(ligne.total > 0 for ligne in lignes):
            return None
        positions = tuple(
            PositionPhase(
                archer_id=ligne.archer_id,
                rang_min=ligne.rang_scratch,
                rang_max=ligne.rang_scratch,
            )
            for ligne in lignes
            if ligne.rang_scratch is not None
        )
        if not positions:
            return None
        # `origine=QUALIFICATION` : ces rangs sont **exacts** mais n'ont été gagnés par aucun match.
        # Sans cette étiquette, `LignePalmares.decerne` les prendrait pour des rangs de duel et le
        # podium remettrait or, argent et bronze sans qu'une flèche ait été tirée en duel.
        return ResultatPhase(
            ordre=phase.ordre,
            positions=positions,
            rang_premier=source.rang_premier,
            origine=OriginePalmares.QUALIFICATION,
        )

    def _resultat(self, tournoi_id: TournoiId, phase: Phase) -> ResultatPhase | None:
        """Ce qu'une phase à tableau a décidé — `None` si elle n'a **rien** décidé (encore).

        ⚠️ **Une phase qui n'a tranché aucun duel est écartée** : elle existe dès le matin et
        `_decor` l'ensemence avec tous les archers en lice (`# DETTE-028`) — le palmarès affichait
        « 1ᵉʳ-120ᵉ · à départager » sur 120 lignes toute la qualification. Le critère est **ce que
        le tableau a décidé**, pas `phase.statut`. ⚠️ Ni un **bye** ni un **walkover de forfait**
        ne comptent : d'où le second critère, **un tir enregistré**.
        """
        if phase.id is None:
            return None
        # DETTE-031 : cette lecture appelle `ServiceSaisieDuels.reconstruire` — tout le classement
        # du tournoi, l'arbre rebâti, les duels rejoués — **une fois par phase à tableau**, sans
        # cache et sans plafond, sur deux routes publiques non authentifiées (dont le PDF).
        try:
            tableau, _lignes = self._saisie_duels.reconstruire(tournoi_id, phase.id)
        # `PrelevementEnAttente` rejoint la liste (E05US024, ADR-0081) : une phase dont la source
        # n'a pas encore départagé les places qu'elle prélève n'a **rien** à ajouter au palmarès —
        # l'écarter est la bonne réponse, pas un pis-aller. `DerouleCyclique`, lui, n'y est
        # **délibérément pas** : une base incohérente doit rester visible, et c'est précisément
        # parce qu'un premier jet levait `PhaseIntrouvable` pour ce cas qu'il était avalé ici.
        except (EffectifTableauInvalide, PhaseIntrouvable, PrelevementEnAttente) as exc:
            _logger.info("Phase %s écartée du palmarès : %s", phase.id, exc)
            return None
        if not self._duels.numeros_enregistres(phase.id):
            return None
        if not any(match.vainqueur is not None and not match.est_bye for match in tableau.matchs):
            return None
        positions = tuple(
            PositionPhase(
                archer_id=participant.ref_id,
                rang_min=acquise.rang_min,
                rang_max=acquise.rang_max,
                en_lice=acquise.en_lice,
            )
            for participant, acquise in tableau.positions_acquises().items()
            # Les participants **équipe** (E13US002) sont écartés : leur `ref_id` n'est pas un
            # archer, et le palmarès classe des archers. La résolution équipe → ligne viendra avec
            # les équipes elles-mêmes, comme pour le routage.
            if participant.genre is GenreParticipant.INDIVIDUEL
        )
        # ⚠️ La **tranche** que cette phase dispute (E05US020, ADR-0068 §5) : une consolante
        # prélevant « les rangs 5 et suivants » joue pour la 5ᵉ place, pas pour la victoire. Sans ce
        # décalage, son vainqueur passait devant le finaliste du tableau principal (`DETTE-034`).
        # E05US024 : la tranche se lit sur **chaque** phase source, avec le même résolveur que
        # l'ensemencement — une autre base situerait les positions dans le mauvais espace de rangs.
        #
        # ⚠️ Le paramètre `classement` a disparu de `tranche` : l'appelant payait une reconstruction
        # complète du classement du départ pour alimenter un paramètre mort, une fois par phase.
        rang_premier = tranche(
            phase,
            self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return ResultatPhase(ordre=phase.ordre, positions=positions, rang_premier=rang_premier)


def _est_terminale(phase: Phase, phases: list[Phase]) -> bool:
    """Aucune autre phase du créneau ne **prélève** dans celle-ci (E05US026).

    Le critère qui décide si une phase décerne des médailles ou se contente de classer. Il est
    **structurel** — lu sur le graphe des sources — et non « par type » : la même phase de poules
    titre dans un format qui s'arrête là, et ne titre pas dans un format qui enchaîne. ⚠️ Se lit
    sur `ordre`, pas sur l'identité, parce que c'est ainsi qu'une source désigne sa phase
    (`DETTE-026`).
    """
    return not any(
        source.ordre_source == phase.ordre
        for autre in phases
        if autre.id != phase.id
        for source in autre.sources
    )


def _borne(rang: int, indecises: tuple[tuple[int, int], ...], *, haute: bool) -> int:
    """La borne de la fourchette d'un rang : la plage indécise qui le contient, ou lui-même.

    Une plage indécise **est** une fourchette au sens du palmarès : les quatre vainqueurs de quatre
    poules occupent les positions 1 à 4 sans que rien ne les sépare. Les y écraser sur leur position
    exacte donnerait un ordre que la compétition n'a pas produit — c'est la faute qu'ADR-0081 nomme,
    transposée du prélèvement à l'affichage.
    """
    for debut, fin in indecises:
        if debut <= rang <= fin:
            return fin if haute else debut
    return rang
