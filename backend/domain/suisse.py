"""**Système suisse** — personne n'est éliminé ; les quatre points ouverts de la règle (rondes,
ronde 1, ré-affrontement, Buchholz) sont tranchés dans `stories/E05-moteur-phases.md`.

⚠️ **L'appariement procède par ESSAIS AVEC RETOUR ARRIÈRE, jamais en glouton.** Mesuré en revue sur
500 tournois au réglage par défaut (16 archers, 5 rondes) : le glouton se bloquait **53 %** du
temps. `AppariementImpossible` ne se lève donc que si aucune solution n'existe (`DETTE-027`).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from domain.erreurs import AppariementImpossible, ConfigurationSuisseInvalide
from domain.participant import Participant
from domain.politiques import DecompteDepartage

# Barème du suisse en **demi-points doublés**, pour rester en arithmétique entière : une victoire
# vaut classiquement 1 point et un nul 0,5, donc on double tout. Le domaine évite ainsi le flottant,
# dont les comparaisons d'égalité sont exactement ce sur quoi un départage ne doit pas reposer.
POINTS_VICTOIRE = 2
POINTS_NUL = 1
POINTS_DEFAITE = 0


@dataclass(frozen=True)
class ConfigurationSuisse:
    """Le réglage d'une phase au système suisse.

    `nb_rondes` est validé contre l'effectif au démarrage et non ici : à N participants chacun n'a
    que N-1 adversaires, donc au-delà de N-1 rondes l'appariement sans ré-affrontement est
    **impossible par construction**. Le dire à la composition évite de bloquer à la ronde 6 le jour
    J — mais l'effectif n'est pas connu quand un format de bibliothèque s'écrit.
    """

    nb_rondes: int = 5

    def __post_init__(self) -> None:
        if self.nb_rondes < 1:
            raise ConfigurationSuisseInvalide(
                f"Un système suisse compte au moins une ronde (reçu {self.nb_rondes})."
            )


@dataclass(frozen=True)
class ResultatRonde:
    """L'issue d'une rencontre, en **demi-points doublés** pour rester en entiers.

    Une victoire vaut 2, un nul 1, une défaite 0 — soit le barème classique 1 / 0,5 / 0 multiplié
    par deux. Le domaine évite ainsi le flottant, dont les comparaisons d'égalité sont exactement ce
    qu'un départage ne doit pas reposer dessus.
    """

    a: Participant
    b: Participant
    points_a: int
    points_b: int
    nb_dix_a: int = 0
    nb_neuf_a: int = 0
    nb_dix_b: int = 0
    nb_neuf_b: int = 0

    @staticmethod
    def victoire_de(gagnant: Participant, perdant: Participant) -> ResultatRonde:
        return ResultatRonde(
            a=gagnant, b=perdant, points_a=POINTS_VICTOIRE, points_b=POINTS_DEFAITE
        )

    @staticmethod
    def nul(a: Participant, b: Participant) -> ResultatRonde:
        return ResultatRonde(a=a, b=b, points_a=POINTS_NUL, points_b=POINTS_NUL)


@dataclass(frozen=True)
class Appariement:
    """Une rencontre à disputer. `b` est `None` pour un **bye** (victoire d'office)."""

    a: Participant
    b: Participant | None = None

    @property
    def est_bye(self) -> bool:
        return self.b is None


@dataclass(frozen=True)
class RangSuisse:
    """Une ligne du classement final : rang, participant, points, Buchholz, décompte FFTA."""

    rang: int
    participant: Participant
    points: int
    buchholz: int
    decompte: DecompteDepartage
    ex_aequo: bool = False


def apparier_ronde(
    participants: Sequence[Participant],
    resultats: Sequence[ResultatRonde],
    configuration: ConfigurationSuisse,
    byes: Sequence[Participant] = (),
) -> tuple[Appariement, ...]:
    """Compose les rencontres de la ronde suivante.

    `participants` est l'ordre du **classement source** (indice 0 = premier), qui sert d'appariement
    de la ronde 1 *et* de départage stable ensuite. `resultats` porte **toutes** les rencontres déjà
    disputées ; `byes` porte, dans l'ordre des rondes, **qui a reçu un bye**.

    ⚠️ **Les byes sont passés explicitement, ils ne se devinent plus.** Un premier jet de cette US
    les déduisait des « rencontres manquantes » (celui qui a joué une rencontre de moins que les
    autres a chômé). Deux défauts, tous deux constatés : un bye ne rapportait alors **aucun point**
    — le bénéficiaire finissait derrière un perdant, puis se faisait apparier avec les perdants à la
    ronde suivante, l'exact contraire de la règle ; et une ronde **partiellement saisie** faisait
    passer pour porteurs de bye tous ceux dont le résultat n'était pas encore entré. Une donnée
    qu'on déduit d'une absence est fausse dès que l'absence a deux causes possibles.

    Ronde 1 : appariement **par classement**, fort contre faible (1 vs N/2+1, 2 vs N/2+2, …), qui
    est la façon habituelle d'ouvrir un suisse : elle évite qu'un favori sorte dès la première
    ronde, sans introduire d'aléa.

    Rondes suivantes : les participants sont regroupés par **score identique** (« les vainqueurs
    rencontrent les vainqueurs »), les groupes parcourus du meilleur au moins bon, et l'on apparie
    au sein du groupe en descendant chercher un adversaire dès qu'une paire s'est déjà rencontrée.
    """
    if len(participants) < 2:
        raise ConfigurationSuisseInvalide("Un système suisse apparie au moins deux participants.")
    rondes_jouees = _rondes_closes(participants, resultats)
    _verifier_byes(participants, byes, rondes_jouees)
    if rondes_jouees >= configuration.nb_rondes:
        raise ConfigurationSuisseInvalide(
            f"Les {configuration.nb_rondes} rondes de cette phase ont déjà été disputées."
        )
    maximum = rondes_maximales(len(participants))
    if configuration.nb_rondes > maximum:
        raise ConfigurationSuisseInvalide(
            f"À {len(participants)} participants, {maximum} rondes au plus sont appariables sans "
            f"ré-affrontement ; {configuration.nb_rondes} en sont demandées."
        )
    deja_rencontres = _deja_rencontres(resultats)
    if rondes_jouees == 0:
        ordre = list(participants)
    else:
        points = _points(participants, resultats, byes)
        # Tri par score décroissant, puis par rang source — le rang source est ce qui rend l'ordre
        # **déterministe** à score égal, donc l'appariement reproductible (règle 9).
        rangs = {participant: index for index, participant in enumerate(participants)}
        ordre = sorted(participants, key=lambda p: (-points[p], rangs[p]))
    porteur_de_bye = _attribuer_le_bye(ordre, byes) if len(ordre) % 2 == 1 else None
    a_apparier = [p for p in ordre if p != porteur_de_bye]
    paires = _apparier(a_apparier, deja_rencontres, coupe_en_deux=rondes_jouees == 0)
    appariements = [Appariement(a=a, b=b) for a, b in paires]
    if porteur_de_bye is not None:
        appariements.append(Appariement(a=porteur_de_bye, b=None))
    return tuple(appariements)


def classement_suisse(
    participants: Sequence[Participant],
    resultats: Sequence[ResultatRonde],
    byes: Sequence[Participant] = (),
) -> tuple[RangSuisse, ...]:
    """Classe les participants : points, puis **Buchholz**, puis les critères FFTA (§8.1).

    Le Buchholz est la somme des points des adversaires **effectivement rencontrés** : il mesure la
    difficulté du parcours. Deux archers à trois victoires ne valent pas la même chose si l'un a
    battu les trois meilleurs et l'autre les trois derniers — et le système suisse, qui n'oppose
    jamais tout le monde à tout le monde, a besoin de ce correctif.

    ⚠️ Un **bye vaut une victoire** (`POINTS_VICTOIRE`) mais **aucun adversaire**, donc il ne
    gonfle pas le Buchholz. Les deux moitiés comptent : sans les points, le bénéficiaire finissait
    derrière un perdant, et l'appariement de la ronde suivante — qui trie par points — l'envoyait
    chez les perdants, l'exact contraire de la règle. Et compter le bye comme un adversaire à 0
    point pénaliserait celui qui l'a reçu, tandis que le compter comme un adversaire fort le
    favoriserait : ne rien compter au Buchholz est le seul choix neutre.
    """
    # ⚠️ Le classement **vérifie** ses byes, il ne les prend pas sur parole. `apparier_ronde` le
    # faisait déjà, pas lui : un appelant qui oubliait l'argument à effectif impair obtenait un
    # classement **silencieusement faux** — le porteur de bye relégué dernier à zéro point. Une
    # fonction qui rend un classement ne doit pas avoir de mode « à peu près juste ».
    _verifier_byes(participants, byes, _rondes_closes(participants, resultats))
    points = _points(participants, resultats, byes)
    adversaires = _adversaires(resultats)
    buchholz = {
        participant: sum(points.get(autre, 0) for autre in adversaires.get(participant, ()))
        for participant in participants
    }
    decomptes = _decomptes(participants, resultats)
    rangs_source = {participant: index for index, participant in enumerate(participants)}
    ordonnes = sorted(
        participants,
        key=lambda p: (
            -points[p],
            -buchholz[p],
            -decomptes[p].nb_dix,
            -decomptes[p].nb_neuf,
            rangs_source[p],
        ),
    )

    def cle_de_departage(participant: Participant) -> tuple[int, int, int, int]:
        decompte = decomptes[participant]
        return (
            points[participant],
            buchholz[participant],
            decompte.nb_dix,
            decompte.nb_neuf,
        )

    # DETTE-029 (docs/dette.md) : 3ᵉ écriture de « rang partagé à clé égale, avec sauts » dans le
    # domaine (`classement._ranger`, `poule.classement_de_poule`, `suisse.classement_suisse`), et
    # les trois divergent déjà. Remède proposé (fonction pure `attribuer_rangs`) en US dédiée.
    lignes: list[RangSuisse] = []
    rang = 0
    precedente: tuple[int, int, int, int] | None = None
    for index, participant in enumerate(ordonnes):
        cle = cle_de_departage(participant)
        partage = cle == precedente
        if not partage:
            rang = index + 1
        lignes.append(
            RangSuisse(
                rang=rang,
                participant=participant,
                points=points[participant],
                buchholz=buchholz[participant],
                decompte=decomptes[participant],
                ex_aequo=partage,
            )
        )
        precedente = cle
    return tuple(_propager_ex_aequo(lignes))


# --- rouages internes ----------------------------------------------------------------------------


def rondes_maximales(effectif: int) -> int:
    """Combien de rondes sont appariables sans qu'aucune paire ne se répète.

    À effectif **pair**, chacun a `n-1` adversaires et joue à chaque ronde : `n-1` rondes.
    À effectif **impair**, chacun a encore `n-1` adversaires mais **chôme une fois** (le bye), donc
    il faut `n` rondes pour les rencontrer tous — le bye tourne, et c'est un tour de plus.

    ⚠️ Le raccourci `n-1` dans les deux cas serait faux d'une ronde à effectif impair, et le refus
    tomberait sur une composition parfaitement jouable. La distinction paraît anodine ; c'est
    exactement le genre d'écart qui ne se voit qu'en refusant un format légitime le jour J.
    """
    return effectif - 1 if effectif % 2 == 0 else effectif


def _rondes_closes(participants: Sequence[Participant], resultats: Sequence[ResultatRonde]) -> int:
    """Combien de rondes sont **closes** — et **refuse** si la dernière ne l'est pas.

    Une ronde produit exactement `len(participants) // 2` rencontres, plus un bye si l'effectif est
    impair. Un compte qui ne tombe pas juste signifie qu'une ronde est **en cours de saisie**.

    ⚠️ **On refuse au lieu d'arrondir.** Un premier jet de cette US arrondissait au supérieur en
    commentant que « apparier une ronde par-dessus une ronde en cours serait bien pire que de
    refuser » — mais ne refusait rien, il incrémentait le compteur et continuait. Conséquence
    constatée : les rencontres non encore saisies étaient **perdues** (jamais rejouées), et le bye
    échoyait à quelqu'un qui venait de tirer. C'est un cas normal du jour J, pas un cas limite : une
    ronde se saisit cible par cible.
    """
    par_ronde = max(1, len(participants) // 2)
    rondes, reste = divmod(len(resultats), par_ronde)
    if reste:
        raise ConfigurationSuisseInvalide(
            f"La ronde en cours n'est pas entièrement saisie : {reste} rencontre(s) sur "
            f"{par_ronde} manquent encore. Apparier la ronde suivante les perdrait."
        )
    return rondes


def _verifier_byes(
    participants: Sequence[Participant], byes: Sequence[Participant], rondes: int
) -> None:
    """Vérifie que les byes déclarés décrivent un déroulé possible.

    ⚠️ **Trois contrôles, et le cardinal seul n'en est qu'un.** Un premier jet ne comparait que
    `len(byes)` au nombre de rondes, et **seulement à effectif impair**. Trois trous en résultaient,
    tous constatés :

    - à effectif **pair**, `byes` n'était jamais examiné alors que `_points` le créditait quand même
      — un perdant déclaré porteur de bye finissait à égalité de tête avec les vainqueurs ;
    - un bénéficiaire **hors liste** passait le compte : le vrai bye ne rapportait rien et la
      rotation était corrompue ;
    - **deux byes pour la même personne** passaient aussi : elle terminait première avec six points
      en n'ayant tiré qu'une rencontre.

    C'est la leçon du correctif précédent, une marche plus haut : passer une donnée explicitement au
    lieu de la déduire ne suffit pas — encore faut-il la **vérifier**.
    """
    if len(participants) % 2 == 0:
        if byes:
            raise ConfigurationSuisseInvalide(
                "À effectif pair, aucune ronde ne décerne de bye : tout le monde est apparié."
            )
        return
    if len(byes) != rondes:
        raise ConfigurationSuisseInvalide(
            f"À effectif impair, chaque ronde close décerne un bye : {rondes} ronde(s) disputée(s) "
            f"mais {len(byes)} bye(s) déclaré(s)."
        )
    inscrits = set(participants)
    etrangers = [beneficiaire for beneficiaire in byes if beneficiaire not in inscrits]
    if etrangers:
        raise ConfigurationSuisseInvalide(
            f"{len(etrangers)} bye(s) sont déclarés pour des participants absents de la phase."
        )
    if len(set(byes)) != len(byes):
        raise ConfigurationSuisseInvalide(
            "Un même participant ne peut pas recevoir deux byes tant que quelqu'un n'en a pas eu."
        )


def _deja_rencontres(resultats: Iterable[ResultatRonde]) -> set[frozenset[Participant]]:
    return {frozenset((resultat.a, resultat.b)) for resultat in resultats}


def _points(
    participants: Sequence[Participant],
    resultats: Sequence[ResultatRonde],
    byes: Sequence[Participant] = (),
) -> dict[Participant, int]:
    """Points de chacun — rencontres **et** byes, un bye valant une victoire (`POINTS_VICTOIRE`)."""
    points = dict.fromkeys(participants, 0)
    for resultat in resultats:
        if resultat.a in points:
            points[resultat.a] += resultat.points_a
        if resultat.b in points:
            points[resultat.b] += resultat.points_b
    for beneficiaire in byes:
        if beneficiaire in points:
            points[beneficiaire] += POINTS_VICTOIRE
    return points


def _adversaires(
    resultats: Iterable[ResultatRonde],
) -> dict[Participant, list[Participant]]:
    adversaires: dict[Participant, list[Participant]] = {}
    for resultat in resultats:
        adversaires.setdefault(resultat.a, []).append(resultat.b)
        adversaires.setdefault(resultat.b, []).append(resultat.a)
    return adversaires


def _decomptes(
    participants: Sequence[Participant], resultats: Sequence[ResultatRonde]
) -> dict[Participant, DecompteDepartage]:
    dix = dict.fromkeys(participants, 0)
    neuf = dict.fromkeys(participants, 0)
    for resultat in resultats:
        if resultat.a in dix:
            dix[resultat.a] += resultat.nb_dix_a
            neuf[resultat.a] += resultat.nb_neuf_a
        if resultat.b in dix:
            dix[resultat.b] += resultat.nb_dix_b
            neuf[resultat.b] += resultat.nb_neuf_b
    return {
        participant: DecompteDepartage(nb_dix=dix[participant], nb_neuf=neuf[participant])
        for participant in participants
    }


def _attribuer_le_bye(ordre: Sequence[Participant], byes: Sequence[Participant]) -> Participant:
    """Le bye va au **moins bien classé n'en ayant pas encore eu** (arbitrage du 31/07).

    Deux principes s'y croisent : un bye est un cadeau (une victoire sans tirer), donc il ne revient
    pas au mieux classé ; et il ne se donne pas deux fois à la même personne tant que quelqu'un n'en
    a pas eu. Si **tout le monde** en a déjà eu un — possible sur beaucoup de rondes à petit
    effectif —, on repart du moins bien classé : mieux vaut un second bye qu'un blocage.

    `byes` est la **liste déclarée** des bénéficiaires passés, et non plus une déduction faite sur
    les rencontres manquantes : cette déduction confondait « il a chômé » et « son résultat n'est
    pas encore saisi ».
    """
    deja_servis = set(byes)
    for participant in reversed(ordre):
        if participant not in deja_servis:
            return participant
    return ordre[-1]


def _apparier(
    ordre: Sequence[Participant],
    deja_rencontres: set[frozenset[Participant]],
    coupe_en_deux: bool,
) -> list[tuple[Participant, Participant]]:
    """Apparie une liste **déjà ordonnée** (par score, puis rang source).

    `coupe_en_deux` sert la **ronde 1** : on oppose la moitié haute à la moitié basse (1 vs N/2+1),
    ce qui évite d'éliminer un favori d'entrée. Aux rondes suivantes, on apparie de proche en proche
    dans l'ordre — c'est ce qui réalise « les vainqueurs rencontrent les vainqueurs », puisque
    l'ordre est trié par score.

    Quand deux voisins se sont déjà rencontrés, l'appariement est délégué à
    `_apparier_en_reculant` : **essais successifs avec retour arrière**, et non un repli glouton.
    `AppariementImpossible` n'est donc levée que si **aucun** appariement sans ré-affrontement
    n'existe — l'échec est exact, pas un abandon en chemin (DETTE-027, résorbée le 01/08/2026).
    """
    if coupe_en_deux:
        moitie = len(ordre) // 2
        return list(zip(ordre[:moitie], ordre[moitie:], strict=True))
    paires = _apparier_en_reculant(list(ordre), deja_rencontres)
    if paires is None:
        raise AppariementImpossible(
            "Aucun appariement sans ré-affrontement n'existe pour cette ronde : réduisez le nombre "
            "de rondes ou acceptez de rejouer une rencontre."
        )
    return paires


def _apparier_en_reculant(
    restants: list[Participant], deja_rencontres: set[frozenset[Participant]]
) -> list[tuple[Participant, Participant]] | None:
    """Apparie par **essais successifs avec retour arrière** ; `None` si aucun appariement n'existe.

    On prend toujours le **premier** restant (le mieux placé), on lui essaie chaque adversaire
    possible dans l'ordre — donc le plus proche de lui d'abord, ce qui conserve « les vainqueurs
    rencontrent les vainqueurs » —, et l'on **revient sur ses pas** si la suite mène à une impasse.

    ⚠️ **Pourquoi ce n'est pas un luxe.** Le premier jet appariait en **glouton** sans retour
    arrière, et la dette qui l'assumait affirmait un impact faible « sur un effectif restreint et
    beaucoup de rondes ». C'était faux, et mesurable : sur 500 tournois simulés à **16 archers en
    5 rondes** — le réglage par **défaut**, sur un effectif de club ordinaire —, le glouton se
    bloquait **53 % du temps**, le plus souvent à la **dernière** ronde, quand chacun avait déjà
    tiré quatre fois. Pas un cas limite : le cas nominal, et le format en était inutilisable.

    Le retour arrière **rend l'échec exact** : il n'échoue que si aucun appariement n'existe
    réellement, ce qui rend `AppariementImpossible` enfin honnête. Le coût est celui d'une recherche
    en profondeur sur un graphe de quelques dizaines de sommets, calculée une fois par ronde entre
    deux volées — sans commune mesure avec le temps de tir qu'elle sépare.
    """
    if not restants:
        return []
    premier = restants[0]
    for index in range(1, len(restants)):
        candidat = restants[index]
        if frozenset((premier, candidat)) in deja_rencontres:
            continue
        suite = _apparier_en_reculant([p for p in restants[1:] if p != candidat], deja_rencontres)
        if suite is not None:
            return [(premier, candidat), *suite]
    return None


def _propager_ex_aequo(lignes: Sequence[RangSuisse]) -> list[RangSuisse]:
    """Marque aussi le **premier** d'un groupe d'ex æquo (voir `poule._marquer_ex_aequo`)."""
    marquees = list(lignes)
    for index, ligne in enumerate(marquees):
        if ligne.ex_aequo and index > 0 and not marquees[index - 1].ex_aequo:
            precedente = marquees[index - 1]
            marquees[index - 1] = RangSuisse(
                rang=precedente.rang,
                participant=precedente.participant,
                points=precedente.points,
                buchholz=precedente.buchholz,
                decompte=precedente.decompte,
                ex_aequo=True,
            )
    return marquees
