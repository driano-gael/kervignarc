"""Service applicatif du **système suisse** (E05US026) — habiter le contrat de phase jouable.

Le moteur (`domain/suisse.py`) est livré depuis E05US015 et n'avait **aucun appelant de
production** : c'est le volet suisse de `DETTE-028`. Ce service est cet appelant.

## Ce qui est partagé, et ce qui ne l'est pas

Comme pour les poules ([ADR-0083](../../docs/adr/0083-le-contrat-de-phase-jouable.md) §7), ce qui
est partagé avec `ServiceSaisieDuels` l'est **réellement** : l'agrégat `Duel`, le pavé de saisie
(`bareme_de` / `zones_de`) et la table `duel`. Une rencontre de ronde **est** un duel ordinaire, et
la faire écrire autrement créerait deux façons de saisir un tir — l'exacte duplication qu'ADR-0083
se donne pour objet de fermer.

Ce qui diffère est la **navigation**, c'est-à-dire le `decor` du contrat (2ᵉ question) : là-bas on
retrouve un match dans un arbre, en poules une rencontre dans un groupe, ici une rencontre dans une
**ronde**. C'est tout ce que ce module réimplémente.

## Le rejeu, et la seule règle qui le contraint

Une phase de suisse ne persiste **ni ses appariements ni ses rondes** : elle les rejoue des duels
validés, exactement comme un tableau rejoue son arbre. `apparier_ronde` est déterministe à donnée
constante (règle 9), donc le rejeu est reproductible.

⚠️ **Mais le moteur refuse d'apparier par-dessus une ronde en cours de saisie**, et ce refus est le
cœur de ce service. `_rondes_closes` compte les résultats et **lève** si le compte ne tombe pas
juste, parce qu'apparier la ronde suivante perdrait les rencontres non encore saisies et donnerait
le bye à quelqu'un qui vient de tirer. Une ronde se saisit cible par cible : l'état « partiellement
saisie » est le régime **normal** du jour J, pas un cas limite.

Le rejeu s'arrête donc à la première ronde incomplète, et l'état rendu le **dit** (`close`). C'est
ce qui permet à l'écran de nommer l'attente au lieu d'afficher un bouton inerte.

## Les byes n'accompagnent que les rondes closes

`apparier_ronde` prend les byes **explicitement** et les vérifie (cardinal, appartenance, unicité).
Le service ne lui passe donc que les byes des rondes **closes** — un bye déclaré pour une ronde en
cours ferait mentir le compte et serait refusé, à juste titre.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from application.classements import ServiceClassement
from application.erreurs import (
    DuelDesynchronise,
    PhaseIntrouvable,
    PhasePasReglee,
    PhasePasUnSuisse,
    RencontreIntrouvable,
    TournoiIntrouvable,
)
from application.portee import phase_du_tournoi
from application.prelevement import ResolveurClassement, preleves, tranche
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.blason import ZoneScore
from domain.classement import LigneClassement
from domain.classement_de_suisse import classement_de_suisse
from domain.classement_de_tableau import ClassementSource
from domain.duel import BaremeDuel, Cote, Duel
from domain.participant import Participant
from domain.phase import Phase, PhaseId, TypePhase
from domain.ports import DuelRepository, PhaseRepository, TournoiRepository
from domain.suisse import (
    POINTS_DEFAITE,
    POINTS_NUL,
    POINTS_VICTOIRE,
    Appariement,
    ConfigurationSuisse,
    RangSuisse,
    ResultatRonde,
    apparier_ronde,
    classement_suisse,
    rondes_maximales,
)
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class RencontreDeRonde:
    """Une rencontre d'une ronde, prête à l'affichage et à la saisie.

    `numero` est le `match_numero` de la table `duel` : un **compteur continu sur toute la phase**,
    ronde après ronde. C'est ce qui permet de porter les rencontres de toutes les rondes sans table
    neuve — aucune migration, même parti que les poules.

    ⚠️ **Un compteur, donc pas une position stable.** La même remarque que `DETTE-057` vaut ici : si
    la population de la phase change après des tirs, les numéros glissent et les rencontres déjà
    tirées ne décrivent plus les mêmes duellistes. C'est `desynchronisee` qui le dit, et le tir est
    alors **masqué** plutôt que ré-attribué (ADR-0049 §4).
    """

    numero: int
    ronde: int
    haut: Duelliste | None
    bas: Duelliste | None
    duel: Duel | None
    desynchronisee: bool
    bareme: BaremeDuel
    zones: tuple[ZoneScore, ...]


@dataclass(frozen=True)
class RondeAffichee:
    """Une ronde : ses rencontres, son porteur de bye, et si elle est close.

    `close` est la seule information dont l'écran a besoin pour savoir s'il peut annoncer la ronde
    suivante — et c'est aussi ce qui empêche le service de l'apparier.
    """

    numero: int
    rencontres: tuple[RencontreDeRonde, ...]
    bye: Duelliste | None
    close: bool


@dataclass(frozen=True)
class EtatSuisse:
    """La photo complète d'une phase de suisse : ses rondes jouées ou en cours, son classement.

    `rondes_maximales` est la **borne** que l'effectif du jour autorise — ce que l'atelier affiche
    en clair sous le champ de réglage (CA « avec le maximum que l'effectif autorise »). Elle est
    rendue ici plutôt que calculée à l'écran : deux arithmétiques pour une même règle sont une
    divergence en attente, la leçon des dix filtres d'ADR-0083.
    """

    phase_id: PhaseId
    nb_rondes: int
    rondes_maximales: int
    effectif: int
    rondes: tuple[RondeAffichee, ...]
    classement: tuple[RangSuisse, ...]


class ServiceSuisse:
    """Cas d'usage du système suisse : consulter une phase, saisir ses rencontres, la classer."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        duels: DuelRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._duels = duels
        self._classements = classements
        # ⚠️ **Pas pour saisir** — uniquement pour emprunter sa résolution de classement amont et sa
        # résolution de pavé (barème par arme, zones du blason). Même parti que `ServicePoules`, et
        # le sens de dépendance est sûr : `saisie_duels` ne connaît pas le suisse.
        self._saisie_duels = saisie_duels

    # --- Lecture ---------------------------------------------------------------------------------

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatSuisse:
        """La photo complète : rondes rejouées, ronde en cours, classement.

        `# DETTE-031` — recomposée **intégralement** à chaque lecture, chaîne de sources amont
        comprise, sans mémoïsation transverse aux requêtes. Même régime que les poules.

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasUnSuisse` ou
        `PhasePasReglee` (409).
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._photo(phase, participants)

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement que cette phase **produit** — le port `LecteurClassementDePhase`.

        C'est ce qui rend une phase avale alimentable par un système suisse : jusqu'ici
        `ServiceSaisieDuels._classement_de_l_ordre` rendait `None` sur ce type, donc un prélèvement
        le visant restait **inerte** — la phase aval recevait tous les archers en lice, ce qui est
        plausible et faux.

        `rang_premier` est posé ici avec le **même** résolveur que celui qui a servi à prélever :
        deux bases différentes situeraient la population et le décalage dans deux espaces de rangs
        distincts, ce qui est exactement `DETTE-034`.
        """
        phase, participants = self._population(tournoi_id, phase_id, resolveur)
        photo = self._photo(phase, participants)
        return replace(
            classement_de_suisse(
                photo.classement, {ligne.archer_id: ligne for ligne in participants}
            ),
            rang_premier=tranche(phase, resolveur),
        )

    def _photo(self, phase: Phase, participants: list[LigneClassement]) -> EtatSuisse:
        """Le cœur d'`etat`, séparé des gardes : rejouer les rondes, puis classer.

        Extrait pour que `classement_de_phase` réutilise exactement le même calcul sans repayer la
        résolution de population — et surtout sans la refaire avec un **autre** résolveur, ce qui
        rejouerait deux appariements différents pour la même phase.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        configuration = self._configuration(phase)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        # Une phase encore vide est une photo **vide**, pas une erreur : elle se compose et se règle
        # avant que sa population existe. Sans cette porte, l'écran de saisie et toute phase avale
        # qui y prélève sortaient en 500 (le correctif que les poules ont dû faire en revue).
        if len(participants) < 2:
            return EtatSuisse(
                phase_id=phase_id,
                nb_rondes=configuration.nb_rondes,
                rondes_maximales=rondes_maximales(max(len(participants), 1)),
                effectif=len(participants),
                rondes=(),
                classement=(),
            )
        tireurs = [Participant.individuel(ligne.archer_id) for ligne in participants]
        rondes, resultats, byes = self._rejouer(phase_id, tireurs, configuration, lignes)
        return EtatSuisse(
            phase_id=phase_id,
            nb_rondes=configuration.nb_rondes,
            rondes_maximales=rondes_maximales(len(tireurs)),
            effectif=len(tireurs),
            rondes=rondes,
            classement=classement_suisse(tireurs, resultats, byes),
        )

    def _rejouer(
        self,
        phase_id: PhaseId,
        tireurs: list[Participant],
        configuration: ConfigurationSuisse,
        lignes: dict[int, LigneClassement],
    ) -> tuple[tuple[RondeAffichee, ...], list[ResultatRonde], list[Participant]]:
        """Rejoue les rondes des duels validés, et **s'arrête à la première ronde incomplète**.

        L'arrêt n'est pas une précaution : `apparier_ronde` **refuse** d'apparier par-dessus une
        ronde en cours (`_rondes_closes` lève), parce que la ronde suivante perdrait les rencontres
        non encore saisies et donnerait le bye à quelqu'un qui vient de tirer. On ne tente donc même
        pas l'appel — l'état rendu dit `close=False` et l'écran nomme l'attente.

        ⚠️ **Les byes n'accompagnent que les rondes closes**, pour la même raison : le moteur les
        vérifie contre le nombre de rondes disputées, et déclarer celui d'une ronde en cours ferait
        mentir le compte.

        ⚠️ **Le compteur de numéros court sur toute la phase**, ronde après ronde, et il ne se
        recale jamais : c'est ce qui permet à `(phase_id, match_numero)` de porter les rencontres de
        toutes les rondes sans table neuve.
        """
        rondes: list[RondeAffichee] = []
        resultats: list[ResultatRonde] = []
        byes: list[Participant] = []
        numero = 0
        for index in range(configuration.nb_rondes):
            appariements = apparier_ronde(tireurs, resultats, configuration, byes)
            rencontres: list[RencontreDeRonde] = []
            acquis: list[ResultatRonde] = []
            bye: Participant | None = None
            close = True
            for appariement in appariements:
                if appariement.est_bye:
                    bye = appariement.a
                    continue
                numero += 1
                rencontre = self._rencontre(numero, index + 1, appariement, phase_id, lignes)
                rencontres.append(rencontre)
                resultat = _resultat_de(rencontre)
                if resultat is None:
                    close = False
                else:
                    acquis.append(resultat)
            rondes.append(
                RondeAffichee(
                    numero=index + 1,
                    rencontres=tuple(rencontres),
                    bye=None if bye is None else self._duelliste(bye, lignes),
                    close=close,
                )
            )
            if not close:
                break
            resultats.extend(acquis)
            if bye is not None:
                byes.append(bye)
        return tuple(rondes), resultats, byes

    def _rencontre(
        self,
        numero: int,
        ronde: int,
        appariement: Appariement,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
    ) -> RencontreDeRonde:
        """Assemble une rencontre : ses adversaires résolus, son pavé, son tir.

        Le pavé est résolu par **le même code** que celui d'un duel de tableau
        (`ServiceSaisieDuels.bareme_de` / `zones_de`) : une rencontre de ronde *est* un duel
        ordinaire, et le même archer ne peut pas tirer en sets d'un côté et en cumul de l'autre.
        """
        a = appariement.a
        b = appariement.b
        assert b is not None, "`_rejouer` écarte les byes avant d'appeler cette méthode."
        bareme = self._saisie_duels.bareme_de(a, lignes)
        charge = self._duels.charger(phase_id, numero, bareme=bareme)
        # ⚠️ **L'ancrage d'ADR-0049 §4.** Un tir dont les duellistes enregistrés divergent des
        # adversaires recalculés est **masqué**, jamais ré-attribué : la rencontre s'affiche non
        # tirée plutôt que de prêter un score au mauvais couple.
        attendus = (a, b)
        concorde = (
            charge is not None
            and (
                charge.participant_haut,
                charge.participant_bas,
            )
            == attendus
        )
        return RencontreDeRonde(
            numero=numero,
            ronde=ronde,
            haut=self._duelliste(a, lignes),
            bas=self._duelliste(b, lignes),
            duel=charge if concorde else None,
            # Masquer ne suffit pas : sans ce drapeau la rencontre s'afficherait « à tirer »,
            # indiscernable d'une rencontre jamais commencée, et le scoreur se prendrait un 409 sur
            # un écran qui l'invitait à saisir (leçon de la revue d'E05US023).
            desynchronisee=charge is not None and not concorde,
            bareme=bareme,
            zones=self._saisie_duels.zones_de(a, lignes),
        )

    def _duelliste(self, participant: Participant, lignes: dict[int, LigneClassement]) -> Duelliste:
        """Le duelliste résolu — nom et prénom depuis le classement."""
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return Duelliste(archer_id=participant.ref_id, nom="?", prenom="")
        return Duelliste(archer_id=ligne.archer_id, nom=ligne.nom, prenom=ligne.prenom)

    # --- Gardes ----------------------------------------------------------------------------------

    def _population(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        resolveur: ResolveurClassement | None = None,
    ) -> tuple[Phase, list[LigneClassement]]:
        """Les gardes, puis **qui entre dans la phase** — la 1ʳᵉ question du contrat (ADR-0083 §1).

        Générique depuis ADR-0068/E05US024 : `preleves` lit chaque source dans le classement de
        **sa** phase, en remontant la chaîne. Une phase de suisse sans source déclarée est donc
        alimentée par le classement du départ, comme un tableau de tête.

        `resolveur` est fourni quand l'appel vient **d'en haut** (une phase aval qui remonte la
        chaîne par `LecteurClassementDePhase`) : on réutilise alors son cache et sa chaîne de phases
        visitées plutôt que d'en ouvrir un second (`DETTE-031`, et la détection de cycle avec).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.SUISSE:
            raise PhasePasUnSuisse(f"La phase {phase_id} n'est pas un système suisse.")
        classement = self._classements.pour_depart(phase.depart_id)
        participants = preleves(
            phase,
            classement,
            resolveur
            if resolveur is not None
            else self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return phase, participants

    def _configuration(self, phase: Phase) -> ConfigurationSuisse:
        """Le réglage de la phase, ou `PhasePasReglee` (409).

        ⚠️ **Aucune vérification de la borne ici.** Elle est portée par `EtapeDeroule`, à la
        composition, là où l'effectif **déclaré** est connu. La refaire sur l'effectif *réel* du
        jour ferait tomber la lecture d'une phase que l'atelier a acceptée — un écran qui refuse de
        s'ouvrir vaut moins qu'un écran qui montre la borne. C'est `apparier_ronde` qui reste le
        dernier rempart, et il lève une `DomainError` que la frontière traduit.
        """
        if phase.suisse is None:
            raise PhasePasReglee(
                f"La phase {phase.id} n'a pas encore de nombre de rondes : réglez-la à l'atelier "
                "avant de la faire jouer."
            )
        return phase.suisse

    # --- Saisie d'une rencontre (via la file) ----------------------------------------------------
    #
    # ⚠️ Mêmes trois méthodes que `ServicePoules`, et le même écart avec `ServiceSaisieDuels` :
    # l'agrégat, le pavé et la table sont partagés, seule la **navigation** diffère (ADR-0083 §7).

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        manche: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> RencontreDeRonde:
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
    ) -> RencontreDeRonde:
        """Saisit le tir de barrage **interne** à une rencontre nulle (§8.2, E04US013).

        ⚠️ **Offert, mais pas exigé — et c'est propre au suisse.** Un nul est ici un résultat
        **légitime** : le barème du format le prévoit (`POINTS_NUL`, un demi-point doublé), là où
        une poule ou un tableau doivent toujours désigner un vainqueur. Ne pas tirer le barrage
        laisse donc la rencontre à 1-1, ce qui est une réponse et non une absence de réponse.

        Le geste reste offert parce que le pavé est le même et que l'organisateur peut vouloir
        trancher : le refuser serait une asymétrie gratuite entre deux décors qui saisissent le
        même duel.
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
    ) -> RencontreDeRonde:
        """Valide le tir d'une rencontre — c'est ce qui la fait entrer au classement.

        ⚠️ **La validation est le geste qui clôt une ronde**, donc celui qui autorise l'appariement
        de la suivante. Un tir non validé laisse la ronde ouverte, et le moteur **refuse**
        d'apparier par-dessus : c'est voulu, et c'est la règle de la reconstruction d'un tableau,
        qui ne rejoue lui aussi que les duels validés.
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
    ) -> RencontreDeRonde:
        """Le tronc commun des trois écritures : retrouver la rencontre, appliquer, persister.

        `# DETTE-031` — appelle `etat()` à **chaque** manche, barrage et validation, donc rejoue la
        reconstruction complète sur le thread du writer unique. Même régime que `ServicePoules`, et
        la dette est élargie d'autant.

        La rencontre est retrouvée **par recomposition**, jamais par une lecture de la table
        `duel` : c'est ce qui garantit que le tir écrit porte les deux adversaires que l'appariement
        du moment désigne. Écrire depuis la ligne persistée se fierait à un `match_numero` qui a pu
        changer de sens — précisément ce que l'ancrage d'ADR-0049 §4 sert à détecter.

        ⚠️ **Une rencontre désynchronisée refuse l'écriture** au lieu de reconstruire un duel vierge.
        C'est le correctif que les poules ont dû faire en revue : le `or Duel.vide(...)` remplaçait
        la ligne, un tir validé disparaissait sans trace, et le verrou de validation sautait avec.
        """
        rencontre = self._trouver(tournoi_id, phase_id, numero)
        if rencontre.desynchronisee:
            raise DuelDesynchronise(
                f"Le tir de la rencontre {numero} oppose d'autres duellistes : la population de la "
                "phase a changé depuis. Rétablissez-la avant de saisir."
            )
        assert (
            rencontre.haut is not None and rencontre.bas is not None
        ), "`_rejouer` n'appareille que des rencontres à deux adversaires résolus."
        haut = Participant.individuel(rencontre.haut.archer_id)
        bas = Participant.individuel(rencontre.bas.archer_id)
        # Les zones sont relues en **strict** sur ce chemin d'écriture : un blason indéterminable
        # doit lever plutôt que produire un pavé vide, sinon on enregistrerait un score dont on ne
        # sait pas s'il est légal (même exigence qu'E04US002 et que les poules).
        zones = self._saisie_duels.zones_strictes(haut, self._lignes(phase_id))
        courant = rencontre.duel or Duel.vide(rencontre.bareme, haut, bas)
        duel = appliquer(courant, rencontre.bareme, zones)
        self._duels.enregistrer(phase_id, numero, duel)
        return replace(rencontre, duel=duel)

    def _trouver(self, tournoi_id: TournoiId, phase_id: PhaseId, numero: int) -> RencontreDeRonde:
        """La rencontre de ce numéro dans l'état rejoué, ou `RencontreIntrouvable` (404).

        Une rencontre d'une ronde **pas encore appariée** est introuvable, et c'est exact : elle
        n'existe pas tant que la ronde précédente n'est pas close.
        """
        etat = self.etat(tournoi_id, phase_id)
        for ronde in etat.rondes:
            for rencontre in ronde.rencontres:
                if rencontre.numero == numero:
                    return rencontre
        raise RencontreIntrouvable(
            f"Aucune rencontre {numero} dans la phase {phase_id} : soit elle n'existe pas, soit sa "
            "ronde n'est pas encore appariée — la précédente doit être close d'abord."
        )

    def _lignes(self, phase_id: PhaseId) -> dict[int, LigneClassement]:
        """Le classement du départ de cette phase, indexé par archer — pour résoudre le blason."""
        phase = self._phases.par_id(phase_id)
        assert phase is not None, "`etat` a déjà refusé une phase inconnue."
        return {
            ligne.archer_id: ligne
            for ligne in self._classements.pour_depart(phase.depart_id).lignes
        }


def _resultat_de(rencontre: RencontreDeRonde) -> ResultatRonde | None:
    """Traduit un tir **validé** en résultat consommable par le moteur d'appariement.

    ⚠️ **Seuls les duels validés comptent.** Un tir en cours de saisie ferait bouger le classement à
    chaque flèche, et surtout l'appariement de la ronde suivante changerait sous les yeux du juge.
    Même parti que la reconstruction d'un tableau et que les poules.

    Les points sont ceux du barème classique **doublé** (2 / 1 / 0) que `domain/suisse.py` emploie
    pour rester en entiers : une victoire vaut 1 point et un nul 0,5, et le domaine évite le
    flottant, dont les comparaisons d'égalité sont exactement ce sur quoi un départage ne doit pas
    reposer.
    """
    duel = rencontre.duel
    if duel is None or not duel.verrouille:
        return None
    vainqueur = duel.resultat.vainqueur
    points_a, points_b = (
        (POINTS_VICTOIRE, POINTS_DEFAITE)
        if vainqueur is Cote.HAUT
        else (POINTS_DEFAITE, POINTS_VICTOIRE)
        if vainqueur is Cote.BAS
        else (POINTS_NUL, POINTS_NUL)
    )
    haut = _volees_de(duel, cote_haut=True)
    bas = _volees_de(duel, cote_haut=False)
    return ResultatRonde(
        a=duel.participant_haut,
        b=duel.participant_bas,
        points_a=points_a,
        points_b=points_b,
        nb_dix_a=_compter(haut, "10"),
        nb_neuf_a=_compter(haut, "9"),
        nb_dix_b=_compter(bas, "10"),
        nb_neuf_b=_compter(bas, "9"),
    )


def _volees_de(duel: Duel, *, cote_haut: bool) -> tuple[str, ...]:
    """Les zones tirées par un camp, toutes manches confondues — pour le décompte FFTA."""
    return tuple(
        valeur
        for manche in duel.manches
        for volee in ((manche.volee_haut,) if cote_haut else (manche.volee_bas,))
        if volee is not None
        for valeur in volee.valeurs
    )


def _compter(valeurs: tuple[str, ...], zone: str) -> int:
    """Combien de flèches dans cette zone — le décompte de départage du §8.1."""
    return sum(1 for valeur in valeurs if valeur == zone)


__all__ = [
    "EtatSuisse",
    "RencontreDeRonde",
    "RondeAffichee",
    "ServiceSuisse",
]
