"""Moteur du **système suisse** — classer sans éliminer (E05US015, [ADR-0062]).

Règle **fournie par le commanditaire le 31/07/2026**, reproduite au [référentiel §10.1] :

> **Objectif** — classer beaucoup de participants sans éliminer personne.
> **Fonctionnement** — manche 1, les rencontres sont aléatoires (ou par classement) ; manche 2, les
> vainqueurs rencontrent les vainqueurs et les perdants rencontrent les perdants ; même principe
> ensuite. Au fil des manches, les meilleurs jouent les meilleurs et les moins forts des adversaires
> de leur niveau. Après 5 à 7 rondes, on obtient un classement très fiable sans avoir éliminé
> personne.

**Quatre points que la règle laisse ouverts**, tranchés au cadrage du 31/07/2026 avec le
commanditaire et reversés dans `stories/E05-moteur-phases.md` :

1. **Nombre de rondes** : paramètre, **défaut 5** (la règle dit « 5 à 7 »).
2. **Appariement de la ronde 1** : **par classement source**, jamais aléatoire. La règle proposait
   les deux ; l'aléatoire est écarté parce que la **règle 9 du projet** interdit l'aléa non maîtrisé
   — un tournoi doit se rejouer à l'identique, et un appariement tiré au sort rendrait tout test de
   non-régression impossible. Ce n'est pas une préférence esthétique : c'est ce qui permet de
   reconstruire une phase après un incident le jour J.
3. **Pas de ré-affrontement** : deux participants ne se rencontrent **jamais deux fois**. La règle
   ne le dit pas, mais l'omettre dégrade le format — le système suisse tire sa précision du fait que
   chaque ronde apporte une *information nouvelle*.
4. **Départage final** : points, puis **Buchholz** (somme des points des adversaires rencontrés),
   puis les critères FFTA (10 puis 9, §8.1). Le Buchholz mesure la difficulté du parcours : deux
   archers à 3 victoires ne valent pas la même chose si l'un a battu les trois meilleurs.

**Effectif impair** : un participant reçoit un **bye** (victoire d'office), attribué au **moins bien
classé n'en ayant pas encore eu** — un bye est un cadeau, il ne doit pas revenir deux fois à la même
personne ni au mieux classé.

⚠️ **L'appariement est glouton, pas optimal.** On apparie par groupes de score décroissants, en
descendant chercher un adversaire compatible quand le groupe est impair ou déjà rencontré. C'est
l'algorithme des tournois d'échecs de club (pas le couplage de poids maximal de la FIDE). Il peut,
sur des configurations défavorables, ne pas trouver de solution alors qu'il en existait une :
`AppariementImpossible` est alors levée plutôt qu'un ré-affrontement silencieux —
une erreur **de déroulé**, distincte d'un refus de configuration. C'est un compromis
**assumé** — un couplage optimal est un algorithme de graphe entier pour un gain qui, à l'échelle
d'un club, ne se verra pas.

Domaine **pur** (règle 1).

[référentiel §10.1]: ../../docs/referentiel-ffta.md
[ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
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
    rondes_jouees = _verifier_rondes_closes(participants, resultats, byes)
    if rondes_jouees >= configuration.nb_rondes:
        raise ConfigurationSuisseInvalide(
            f"Les {configuration.nb_rondes} rondes de cette phase ont déjà été disputées."
        )
    maximum = _rondes_maximales(len(participants))
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


def _rondes_maximales(effectif: int) -> int:
    """Combien de rondes sont appariables sans qu'aucune paire ne se répète.

    À effectif **pair**, chacun a `n-1` adversaires et joue à chaque ronde : `n-1` rondes.
    À effectif **impair**, chacun a encore `n-1` adversaires mais **chôme une fois** (le bye), donc
    il faut `n` rondes pour les rencontrer tous — le bye tourne, et c'est un tour de plus.

    ⚠️ Le raccourci `n-1` dans les deux cas serait faux d'une ronde à effectif impair, et le refus
    tomberait sur une composition parfaitement jouable. La distinction paraît anodine ; c'est
    exactement le genre d'écart qui ne se voit qu'en refusant un format légitime le jour J.
    """
    return effectif - 1 if effectif % 2 == 0 else effectif


def _verifier_rondes_closes(
    participants: Sequence[Participant],
    resultats: Sequence[ResultatRonde],
    byes: Sequence[Participant],
) -> int:
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
    if len(participants) % 2 == 1 and len(byes) != rondes:
        raise ConfigurationSuisseInvalide(
            f"À effectif impair, chaque ronde close décerne un bye : {rondes} ronde(s) disputée(s) "
            f"mais {len(byes)} bye(s) déclaré(s)."
        )
    return rondes


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

    Le repli quand deux voisins se sont déjà rencontrés : on descend chercher le premier adversaire
    compatible. Glouton, donc faillible — d'où `AppariementImpossible` plutôt qu'un ré-affrontement
    muet.

    # DETTE-027 (docs/dette.md) : ce glouton n'est pas le couplage de poids maximal des fédérations
    # d'échecs ; il peut refuser une ronde pourtant appariable. Assumé — l'échec est explicite, et
    # le remède est un algorithme de graphe entier pour un gain invisible à l'échelle d'un club.
    """
    if coupe_en_deux:
        moitie = len(ordre) // 2
        return list(zip(ordre[:moitie], ordre[moitie:], strict=True))
    restants = list(ordre)
    paires: list[tuple[Participant, Participant]] = []
    while restants:
        premier = restants.pop(0)
        adversaire: Participant | None = None
        for candidat in restants:
            if frozenset((premier, candidat)) not in deja_rencontres:
                adversaire = candidat
                break
        if adversaire is None:
            raise AppariementImpossible(
                "Aucun appariement sans ré-affrontement n'a pu être trouvé pour cette ronde : "
                "réduisez le nombre de rondes ou acceptez de rejouer une rencontre."
            )
        restants.remove(adversaire)
        paires.append((premier, adversaire))
    return paires


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
