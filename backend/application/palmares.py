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
from domain.politiques import Aggregation, AggregationParQualification
from domain.ports import (
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

Aujourd'hui : les **poules** et le **système suisse**. Ni l'un ni l'autre n'a d'arbre à rejouer, et
tous deux rendent un `ClassementSource` complet — c'est précisément ce que `classement_lisible`
promet. Les lire par leur classement, et non par une reconstruction, est donc la voie **directe**.

**Dérivée, pas énumérée** : un format qui devient `classement_lisible` sans être reconstructible
entre ici automatiquement. Les trois soustraits sont ceux qui ont déjà leur chemin — les tableaux
(rejeu d'arbre), la qualification (elle *est* la base du palmarès) et le Big Shoot Off (ses rangs
viennent des éliminations, pas d'un ordre de classement).
"""

_TYPES_RECONSTRUCTIBLES = TYPES_RECONSTRUCTIBLES
"""Les types de phase dont ce service sait **rejouer l'arbre** aujourd'hui.

Dérivé du registre de contrat (`domain/contrat_phase.py`, ADR-0083) : conjonction d'un décor en
arbre de duels **et** d'un service qui le monte. Le parti reste celui d'une **liste blanche**, à
rebours de `produit_un_classement` qui est écrit en négatif : là-bas l'oubli probable est
d'ajouter un vrai format (donc classant par défaut), ici c'est de croire lire une phase dont aucun
moteur ne déroule le résultat. Un type absent ne casse pas le palmarès — il n'y apporte
simplement rien, ce qui est le cas des **poules** dans cette tranche (leur classement est lisible,
mais il n'y a pas d'arbre à rejouer et le CA d'E05US023 ne demande pas leur palmarès).
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
        aggregation: Aggregation | None = None,
        big_shoot_off: LecteurEtatBigShootOff | None = None,
        rencontres: Mapping[TypePhase, LecteurRencontresARouter] | None = None,
    ) -> None:
        self._tournois = tournois
        # Le classement — donc le palmarès — vit par départ depuis ADR-0075.
        self._departs = departs
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
        palmares = calculer_palmares(qualification, resultats, self._aggregation)
        return palmares if categorie_id is None else palmares.pour_categorie(categorie_id)

    def imprimer(self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None) -> bytes:
        """Rend le palmarès en **PDF** (CA « affiché et exportable »).

        Même calcul que `pour_tournoi` — un document qui divergerait de l'écran serait pire que
        pas de document du tout : c'est celui-là qu'on affiche au mur et qu'on remet aux archers.
        Le rendu part au port `GenerateurPalmares` ; le service ne connaît ni ReportLab ni HTTP.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._generateur.palmares(tournoi.nom, self.pour_tournoi(tournoi_id, categorie_id))

    def _premier_depart(self, tournoi_id: TournoiId) -> DepartId:
        """Le premier créneau du tournoi — référence tant que la route reste au niveau tournoi.

        ⚠️ **Raccourci tracé (`DETTE-045`).** Le palmarès est rendu « du tournoi » alors que le
        classement dont il dérive est celui d'un **départ** : sur un tournoi multi-créneaux, il
        n'affiche donc que le podium du premier. La question métier qui bloquait la résorption —
        additionne-t-on les podiums de chaque créneau, ou les juxtapose-t-on ? — a été **tranchée
        par le commanditaire le 07/08/2026** : *juxtaposé*, quatre départs font quatre podiums. Il
        n'y a donc aucune agrégation à écrire, et le remède se réduit à une route par départ,
        planifiée en **E06US009**.
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

        ⚠️ **Un `_resultat` propre au format, et non une entrée de plus dans
        `TYPES_RECONSTRUCTIBLES`.** ADR-0083 l'annonçait pour les poules : cette table est l'alias
        de `TYPES_EN_TABLEAU_JOUE`, donc « rejouer l'arbre » — et un Big Shoot Off n'a pas d'arbre.
        Y ajouter le type aurait envoyé `ServiceSaisieDuels.reconstruire` sur une phase sans
        tableau. Ce qu'il faut lui demander est autre chose, et c'est plus simple : ses rangs sont
        **exacts** par construction, donc `rang_min == rang_max`.

        Trois écartements, et chacun a sa raison :

        1. **une phase que le lecteur ne sait pas résoudre** (`None`) — même parti que `_resultat` :
           une phase n'éteint pas un écran public, elle n'y ajoute rien ;
        2. **une phase où personne n'est encore sorti** : tous les finalistes partagent le rang 1
           tant que la première manche n'est pas jouée, ce qui leur donnerait à tous la première
           place du tournoi pendant qu'ils tirent. Même défaut que celui qu'`_resultat` corrige
           pour les tableaux (« 1ᵉʳ-120ᵉ · à départager » affiché toute la qualification), et même
           remède : on n'entre au palmarès qu'une fois qu'il y a quelque chose à dire ;
        3. **les rescapés d'une phase encore en cours**, marqués `en_lice` : leur rang 1 partagé
           n'est pas un titre, c'est une absence de verdict, et `LignePalmares.decerne` doit
           pouvoir les distinguer d'un vainqueur — sinon cinq archers reçoivent l'or.

        ⚠️ **`en_lice` se ferme quand la phase est terminée**, et l'oubli coûtait le podium. Le
        moteur garde les rescapés dans `en_lice` même une fois `est_termine` — c'est sa lice, pas
        un pronostic. Mais `LignePalmares.en_lice` répond à une autre question : « cet archer a-t-il
        encore un match devant lui ? ». Reporter le champ tel quel laissait le **vainqueur** en
        lice, donc `decerne=False`, donc **pas d'or** sur un BSO pourtant fini. Trouvé par le
        test de palmarès, pas par relecture : les deux champs portent le même nom et disent deux
        choses différentes.

        Aucune étiquette `origine=QUALIFICATION` ici, à la différence d'`_resultat_qualification` :
        les rangs d'un Big Shoot Off sont **gagnés au tir**, manche après manche. Le podium qu'ils
        décernent est légitime, et c'est précisément ce que ce format sert à produire.
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
            # palmarès est public et projeté en salle, donc une phase de la séquence ne doit pas
            # éteindre l'écran — mais une phase absente du palmarès le jour J serait indébogable.
            #
            # ⚠️ **La liste est nominative, et ce n'est pas un détail de style** (revue d'E05US028).
            # Un premier jet écrivait `(PhaseIntrouvable, PrelevementEnAttente, ApplicationError)` :
            # les deux premiers termes étant filles du troisième, la clause attrapait **toute**
            # erreur applicative, présente et future. Elle ré-avalait notamment `DerouleCyclique`,
            # que `_resultat` exclut **délibérément** (« une base incohérente doit rester visible »)
            # et que cette US venait justement de faire lever sur ce chemin — la garde était donc
            # écrite d'un côté du diff et neutralisée de l'autre. `ruff B014` ne voit pas ce
            # doublon : il ne résout pas les relations de sous-classe.
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

        `# DETTE-031` — une résolution de classement **par phase classante**, plus une lecture
        d'avancement (`_est_epuisee`), sur les deux routes publiques du palmarès dont le PDF.

        On lit son **classement de phase**, celui-là même qu'un prélèvement consomme
        (`ClassementSource`) : rangs et plages encore indécises. C'est la voie directe, et surtout
        la seule qui ne puisse pas **diverger** de ce que la phase avale reçoit — deux calculs pour
        un même ordre finiraient par se contredire.

        ⚠️ **`origine` porte la règle « décerne si rien ne prélève dedans »** (arbitrage du
        15/08/2026). Une phase consommée contribue ses rangs sans médaille ; une phase terminale
        décerne. Le critère est **structurel** — le graphe des sources du déroulé — et non « par
        type » : dans une cascade « poules → poules de niveau », la dernière phase *est* une phase
        de poules et rend le classement final exact, elle doit donc titrer.

        ⚠️ **Les plages indécises deviennent des fourchettes**, et c'est exactement leur sens : les
        quatre vainqueurs de quatre poules sont 1ᵉʳˢ-4ᵉˢ, et rien ne les départage tant que
        l'organisateur n'a pas demandé le départage inter-poules. C'est la politique `aggregation`
        qui tranchera, comme pour les battus d'un quart de finale — pas nous, ici, au hasard.

        Rend `None` quand la phase n'a **rien** classé : une phase qui n'a pas commencé n'ajoute
        rien au palmarès, elle n'y met pas tout le monde au rang 1.
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
            # Absorptions nominatives, **plus `DomainError`** — et ce dernier terme est un correctif
            # de revue, pas une précaution. Les moteurs de format lèvent des erreurs de **domaine**
            # (`ConfigurationSuisseInvalide`, `AppariementImpossible`,
            # `ConfigurationPouleInvalide`), qui ne sont pas des `ApplicationError` : la liste
            # d'origine les laissait passer, et une seule phase mal dimensionnée rendait **422 le
            # palmarès du tournoi entier, écran public et PDF compris** (reproduit par deux axes).
            #
            # ⚠️ `DomainError` est volontairement **le dernier terme** et non un remplacement des
            # quatre autres : ceux-ci restent nominatifs pour que la liste dise ce qu'elle attend,
            # et `DerouleCyclique` — une `ApplicationError` — continue de **traverser**, comme
            # `_resultat` l'exige (« une base incohérente doit rester visible »).
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
        neuf** : c'est un second rejeu de la chaîne amont par phase classante, pas une simple
        lecture d'avancement (précision apportée en revue).

        Prudent par défaut : sans lecteur branché, on répond « non », donc les archers restent
        `en_lice` et **aucune médaille n'est décernée**. Un montage incomplet retire un podium, il
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

        E05US025 (ADR-0082) : un déroulé peut enchaîner les qualifications. Sur l'exemple de
        référence — 120 archers en 3x20, puis une *haute* (rangs 1..60) et une *basse* (61..120) en
        3x15 —, c'est **ici** que le classement final devient un 1..120 au lieu de rester celui du
        premier tour.

        Trois écartements, chacun pour une raison différente :

        1. **La qualification de tête** (`sources` vide) n'est pas un résultat : elle *est* la base
           du palmarès, passée à `calculer_palmares` comme classement de référence. L'ajouter en
           plus lui ferait écraser… elle-même, en bloc `ordre` au lieu de bloc 0.
        2. **Une phase que le résolveur ne sait pas lire** (`None`) — même parti que `_resultat` :
           une phase n'éteint pas un écran public, elle n'y ajoute rien.
        3. **Une phase où personne n'a encore marqué** : tous les totaux à zéro rendent un
        classement
           d'ex æquo au rang 1, qui donnerait à ses 60 archers la première place du tournoi pendant
           tout le temps où ils tirent. Même défaut que celui qu'`_resultat` corrige pour les
           tableaux (« 1ᵉʳ-120ᵉ · à départager » affiché toute la qualification), et même remède :
           on n'entre au palmarès qu'une fois qu'il y a quelque chose à dire.

           ⚠️ Le critère est `total > 0`, donc une phase où **tout le monde aurait tout manqué**
           resterait dehors. C'est la limite que `_Decompte.a_tire` documente déjà côté classement
           (« a tiré » n'est pas « a marqué ») ; ici elle ne fait que **retarder** l'entrée au
           palmarès, elle ne fausse rien — et le cas ne se produit pas sur un tournoi réel.
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

        ⚠️ **Une phase qui n'a tranché aucun duel est écartée**, et c'est un correctif de revue
        relevé par trois axes. Le déroulé se compose à l'avance (E01US024), donc la phase de
        tableau existe **dès le matin** ; `_decor` l'ensemence alors avec tous les archers en lice
        (`# DETTE-028`), et chacun n'a acquis que la plage de son premier match — c'est-à-dire le
        tableau **entier**. Le palmarès affichait donc « 1ᵉʳ-120ᵉ · à départager » sur 120 lignes,
        pendant toute la qualification, sur l'onglet public et l'écran de salle.

        Le critère est **ce que le tableau a décidé**, pas `phase.statut` : le passage à `en_cours`
        est une action **manuelle** de l'organisateur (`ServicePhases.demarrer`), et faire dépendre
        un écran public de sa discipline le laisserait muet tout l'après-midi s'il l'oublie. Un
        tableau dont un duel est tranché a forcément commencé ; la lecture est auto-corrective.

        Deux choses ne comptent pas, et les distinguer a demandé une contre-revue : un **bye**
        avance un archer sans que rien ne se soit joué, et un **walkover de forfait**
        (`_appliquer_forfaits`, ADR-0050) fait de même sur un match qui n'est pourtant **pas**
        un bye. `est_bye` seul laissait donc revenir la régression dès qu'un organisateur
        enregistrait un forfait le matin — geste que le produit encourage. D'où le second
        critère : **un tir enregistré**. Aucun tir, aucun duel, quelle que soit la façon dont
        l'arbre s'est avancé tout seul.

        ⚠️ Le correctif symétrique proposé en revue — écarter côté domaine toute position couvrant
        le tableau entier — a été **écarté** : il casserait le milieu de tour. Après le premier
        duel d'un tableau de 8, six archers n'ont encore rien acquis (`[1..8]`) ; les faire retomber
        sur la qualification les classerait **derrière le battu** qu'ils n'ont pas rencontré.

        Les échecs absorbés sont ceux d'un tableau pas encore montable : effectif insuffisant
        (`EffectifTableauInvalide`, comme le routage) et phase disparue entre deux lectures. Le
        palmarès est **public et projeté en salle** : une phase de la séquence ne doit pas éteindre
        l'écran, elle doit simplement n'y rien ajouter — même parti que le filet d'E06US003. Ils
        sont **journalisés** : une phase absente du palmarès le jour J serait sinon indébogable.
        `PhasePasUnTableau` n'y figure plus — `pour_tournoi` filtre déjà sur le type, la garde était
        morte et une garde morte finit par masquer autre chose.
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
        # prélevant « les rangs 5 et suivants » joue pour la 5ᵉ place, pas pour la victoire. Sans
        # ce décalage, son vainqueur passait devant le finaliste du tableau principal — c'était
        # `DETTE-034`, inatteignable tant qu'aucun moteur ne consommait les prélèvements.
        # E05US024 : la tranche se lit sur **chaque** phase source, plus seulement sur la
        # qualification. Le même résolveur que l'ensemencement — un décalage calculé sur une autre
        # base que celle qui a peuplé le tableau situerait ses positions dans le mauvais espace de
        # rangs, ce qui est exactement `DETTE-034`.
        # ⚠️ Le paramètre `classement` a disparu de `tranche` (correctif de revue) : elle ne le
        # lisait plus depuis E05US024 — l'effectif se lit sur le classement **source**. L'appelant
        # payait donc ici une reconstruction complète du classement du départ (`DETTE-031`) pour
        # alimenter un paramètre mort, **une fois par phase à tableau**, sur deux routes publiques.
        rang_premier = tranche(
            phase,
            self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return ResultatPhase(ordre=phase.ordre, positions=positions, rang_premier=rang_premier)


def _est_terminale(phase: Phase, phases: list[Phase]) -> bool:
    """Aucune autre phase du créneau ne **prélève** dans celle-ci (E05US026).

    C'est le critère qui décide si une phase décerne des médailles ou se contente de classer. Il est
    **structurel** — lu sur le graphe des sources — et non « par type de phase » : la même phase de
    poules titre dans un format qui s'arrête là, et ne titre pas dans un format qui enchaîne.

    ⚠️ **Se lit sur `ordre`, pas sur l'identité**, parce que c'est ainsi qu'une source désigne sa
    phase (`SourcePhase.ordre_source`). C'est l'ancrage par ordre de `DETTE-026` ; le suivre ici est
    juste, s'en écarter créerait une seconde convention.
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
