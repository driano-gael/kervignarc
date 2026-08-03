"""Palmarès du tournoi (E06US004) — fusion des rangs décernés par les phases.

Le classement de qualification (E06US001) dit qui a le mieux tiré ; le tableau (E05US005) dit qui a
gagné. Le **palmarès** est le classement final du tournoi : un rang par archer, par catégorie, où
les archers passés par les duels prennent les premiers rangs — dans l'ordre que les duels ont
décidé — et où ceux qui n'y sont pas entrés suivent dans l'ordre de la qualification.

**Ce module ne rejoue aucun tableau.** Il reçoit ce que chaque phase a **décidé** (`ResultatPhase`,
une position acquise par archer) et applique la règle de fusion. Reconstruire l'arbre est le travail
du service (`application/palmares.py`), lire une position acquise celui du domaine `tableau.py`
(`Tableau.positions_acquises`). La séparation n'est pas cosmétique : elle est ce qui rend la règle
de fusion testable sans monter un tournoi.

**Trois notions à ne pas confondre** :

| Notion | Qui décide | Exemple |
|---|---|---|
| rang **exact** | un match terminal (*Règle T*) | le vainqueur de la petite finale est 3ᵉ |
| **fourchette** | la plage du match perdu (*Règle R*, ADR-0065) | le battu d'un quart est 5ᵉ-8ᵉ |
| **départage** | la politique `aggregation` ([ADR-0067]) | qui, des quatre, est 5ᵉ ? |

La fourchette n'est **pas** une approximation : dans un tableau tronqué au podium, aucun match n'a
été joué pour départager les quatre battus des quarts. La politique `aggregation` décide alors si
l'on emprunte un ordre à la qualification (défaut, usage World Archery) ou si l'on publie l'ex æquo.

⚠️ **Portée : qualification + phases à tableau.** Les moteurs `poule`, `big_shoot_off`, `suisse` et
`colline` existent (E05US015) mais **aucun service ne les déroule** (`# DETTE-028`) : ils ne
produisent donc aucun `ResultatPhase`. Le jour où ils en produiront, ce module n'aura pas à changer
— il ne connaît que des positions acquises, pas la structure qui les a produites.

[ADR-0067]: ../../docs/adr/0067-palmares-agregation-des-rangs-de-phases.md
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from domain.archer import ArcherId
from domain.categorie import CategorieId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.club import ClubId
from domain.politiques import Aggregation, AggregationParQualification

PODIUM_JUSQU_AU = 4
"""Les rangs qui font un podium : 1-2 (finale) et 3-4 (petite finale), CA « podium »."""


class OriginePalmares(str, Enum):
    """D'où vient le rang d'un archer — l'information manquerait sinon à l'écran.

    « 9ᵉ » ne veut pas dire la même chose selon qu'un duel perdu l'a décidé ou que l'archer n'a
    jamais quitté la qualification ; l'afficher sans le dire laisserait croire à une élimination.
    """

    DUELS = "duels"
    QUALIFICATION = "qualification"


@dataclass(frozen=True)
class PositionPhase:
    """La position qu'une phase a fait acquérir à un archer — exacte ou en fourchette.

    `rang_min == rang_max` quand un match terminal a décerné le rang ; sinon la fourchette *ex
    æquo* de la plage du match perdu (ADR-0065). Les rangs sont ceux **de la phase**, pas du
    tournoi : c'est la fusion qui les renumérote.

    `en_lice` dit si la fourchette peut encore se refermer **au tir** (`Tableau.PositionAcquise`).
    Le palmarès ne départage **que** ce qui est joué : deux finalistes partagent « 1ᵉʳ-2ᵉ » jusqu'à
    ce que la finale tranche, et aucune politique n'a le droit de décider à leur place.
    """

    archer_id: ArcherId
    rang_min: int
    rang_max: int
    en_lice: bool = False


@dataclass(frozen=True)
class ResultatPhase:
    """Ce qu'une phase a décidé : son `ordre` dans la séquence et ses positions acquises.

    Pas de politique `aggregation` **par phase**, et c'est délibéré : `Phase` ne persiste aucune
    `config.policies` générique (seul `barrage_jusqu_au` l'est, E06US003), donc rien ne pourrait la
    renseigner. Le champ existerait pour l'idée, pas pour un besoin — la politique se règle au
    tournoi, par la composition root, jusqu'à ce qu'une US donne aux phases leur config.
    """

    ordre: int
    positions: tuple[PositionPhase, ...]


@dataclass(frozen=True)
class LignePalmares:
    """Une ligne du palmarès : le rang final d'un archer, scratch et dans sa catégorie.

    Les rangs sont des **fourchettes** (`min`/`max`), qui se referment (`min == max`) dès qu'un
    rang exact est acquis. Deux champs plutôt qu'un « rang + ex æquo booléen » : la borne haute
    porte l'information (« 5ᵉ-8ᵉ » dit *combien* d'archers partagent), et un booléen obligerait
    chaque surface à recompter le groupe pour l'afficher.

    `None` partout : l'archer est **hors classement** (disqualifié, ADR-0050) — et non « rang
    inconnu ».
    """

    rang_min: int | None
    rang_max: int | None
    rang_categorie_min: int | None
    rang_categorie_max: int | None
    decerne: bool
    """Un **match** a décerné ce rang — la seule forme qui vaut une médaille.

    ⚠️ **Ne se déduit PAS de `rang_min == rang_max`**, et c'est tout l'objet de ce champ. La
    renumérotation rend un rang « exact » dès qu'un archer est **seul dans son paquet**, ce qui
    arrive à un finaliste dont la finale n'est pas tirée : sa position acquise vaut `[1..2]`, mais
    aucun autre archer ne la partage, donc le curseur lui donnait « 1ᵉʳ ». L'écran et le PDF lui
    remettaient l'**or avant le tir** (défaut trouvé en revue, axe adversarial — le drapeau
    `en_lice` protégeait le *groupement*, pas la *numérotation*).

    Faux, donc, pour : un rang de qualification (aucun duel ne l'a décerné), une position encore
    ouverte (`en_lice`), et un ex æquo tranché par la politique `aggregation` — celle-ci **décide**
    un ordre, elle ne le fait pas **gagner**.
    """

    en_lice: bool
    """L'archer a encore un match devant lui : ce qui reste ouvert le sera **au tir**.

    À distinguer d'un ex æquo **définitif** (`decerne=False`, `en_lice=False`), que plus aucun match
    ne départagera. Les deux se présentent comme une fourchette ; les confondre à l'écran ferait
    dire « à départager » à deux finalistes, ce qui annonce un barrage là où c'est la finale."""

    archer_id: ArcherId
    nom: str
    prenom: str
    categorie_id: CategorieId
    categorie_libelle: str
    club_id: ClubId | None
    origine: OriginePalmares
    statut: StatutClassement

    @property
    def est_exact(self) -> bool:
        """Le rang s'affiche en un seul nombre (« 3ᵉ ») plutôt qu'en fourchette (« 5ᵉ-8ᵉ »).

        ⚠️ Question d'**affichage**, pas de médaille : un rang peut être exact sans avoir été
        décerné par un match (rang de qualification, ex æquo tranché par la politique). C'est
        `decerne` que le podium regarde.
        """
        return self.rang_min is not None and self.rang_min == self.rang_max


@dataclass(frozen=True)
class Palmares:
    """Le classement final d'un tournoi, ordonné du 1ᵉʳ au dernier (hors classement en fin)."""

    lignes: tuple[LignePalmares, ...]

    def podium(self, categorie_id: CategorieId) -> tuple[LignePalmares, ...]:
        """Les quatre premiers **d'une catégorie** (CA « podium »).

        Trois conditions, et chacune ferme un trou trouvé en revue :

        1. **`decerne`** — le rang vient d'un **match** (finale / petite finale). Sans cette
           condition, le podium se remplissait sur les seuls scores du matin : chaque rang de
           qualification étant exact par construction, l'écran public décernait « Or / Argent /
           Bronze » **avant le moindre duel**. Elle écarte aussi le finaliste dont la finale n'est
           pas tirée, à qui la renumérotation donnait « 1ᵉʳ » ;
        2. **rang de catégorie exact** — on ne remet pas une médaille à quatre archers *ex æquo* ;
        3. **≤ 4** — finale (1-2) et petite finale (3-4).

        Le podium se lit **par catégorie**, jamais scratch : c'est là que se remettent les
        médailles, et la restriction du podium scratch serait vide pour toute catégorie n'ayant
        personne dans les quatre premiers. Le paramètre est **obligatoire** depuis la revue — une
        branche scratch que seuls ses tests tenaient aurait dérivé en silence.

        Un podium peut donc être **partiel** (rangs 3-4 publiés seuls : la petite finale se tire
        couramment avant la finale) ou **vide** — c'est la lecture au fil de l'eau de tout le
        projet, et l'écran le **dit** plutôt que de laisser un blanc.
        """
        return tuple(
            ligne
            for ligne in self.lignes
            if ligne.categorie_id == categorie_id
            and ligne.decerne
            and ligne.rang_categorie_min is not None
            and ligne.rang_categorie_min == ligne.rang_categorie_max
            and ligne.rang_categorie_min <= PODIUM_JUSQU_AU
        )

    def pour_categorie(self, categorie_id: CategorieId) -> Palmares:
        """Restreint l'**affichage** à une catégorie, **sans renuméroter** le rang scratch.

        Même parti qu'E06US001 : on voit une catégorie sans perdre la position d'ensemble. Un
        recalcul ferait du 1ᵉʳ de sa catégorie un « 1ᵉʳ » tout court, ce qu'il n'est pas.
        """
        return Palmares(
            lignes=tuple(ligne for ligne in self.lignes if ligne.categorie_id == categorie_id)
        )

    def categories(self) -> tuple[tuple[CategorieId, str], ...]:
        """Les catégories présentes, dans l'ordre du palmarès — de quoi composer les podiums."""
        vues: dict[CategorieId, str] = {}
        for ligne in self.lignes:
            vues.setdefault(ligne.categorie_id, ligne.categorie_libelle)
        return tuple(vues.items())


# --- calcul --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Entree:
    """Un archer et ce qui le situe : son bloc (la phase qui l'a classé) et sa position acquise."""

    ligne: LigneClassement
    bloc: int
    rang_min: int | None
    rang_max: int | None
    origine: OriginePalmares
    en_lice: bool = False
    """L'archer a encore un match devant lui : sa fourchette se refermera **au tir**, donc aucune
    politique de départage ne doit y toucher."""


def calculer_palmares(
    qualification: Classement,
    resultats: Sequence[ResultatPhase] = (),
    aggregation: Aggregation | None = None,
) -> Palmares:
    """Fusionne les rangs des phases en un palmarès (CA « podium » + CA « agrégation »).

    - `qualification` : le classement de qualification (E06US001). Il fournit **l'identité** de
      chaque archer, son statut (ADR-0050) et le rang de repli de qui n'a pas disputé de duel ;
    - `resultats` : ce que chaque phase classante a décidé, dans un ordre quelconque ;
    - `aggregation` : la politique de **départage des sortis au même tour** par défaut du tournoi.
      `None` retombe sur `AggregationParQualification` (usage World Archery).

    La règle de fusion tient en trois temps :

    1. **le bloc** — chaque archer est situé par la phase la plus **tardive** qui l'a classé (son
       `ordre`), la qualification faisant bloc 0. Un rang acquis plus tard **remplace** le
       précédent : celui qui gagne son tableau n'est plus 6ᵉ de qualif, il est 1ᵉʳ.
       # DETTE-034 (../../docs/dette.md) — cette règle suppose qu'une phase avale dispute les rangs
       # **du haut** que la précédente laissait ouverts, ce qui est vrai de la cascade réelle
       # (qualification → tableau) et **faux** d'une phase de **consolation** : son vainqueur
       # passerait devant le finaliste du tableau principal. Corriger demanderait de savoir quels
       # rangs une phase dispute — ce que `SourcePhase.par_issue_de_tour` ne dit pas encore
       # (DETTE-033) et qu'aucun moteur ne consomme (DETTE-028). Impact nul aujourd'hui : aucun
       # repêchage n'est câblé en production ;
    2. **l'ordre** — blocs décroissants, puis position acquise croissante. Un battu du 1ᵉʳ tour du
       tableau passe donc devant tout non-qualifié, quel qu'ait été son rang de qualification :
       il a franchi une porte que l'autre n'a pas franchie ;
    3. **la renumérotation** — les rangs repartent de 1 et se suivent **sans trou**, chaque paquet
       d'ex æquo occupant autant de rangs qu'il compte d'archers. Le palmarès est un classement du
       tournoi, pas la juxtaposition des numérotations de ses phases.

    Les **disqualifiés** (ADR-0050) restent hors classement (`rang_* is None`), listés en fin.
    """
    defaut = aggregation if aggregation is not None else AggregationParQualification()
    rang_qualification = {ligne.archer_id: ligne.rang_scratch for ligne in qualification.lignes}
    positions = _positions_par_archer(resultats, connus=set(rang_qualification))

    entrees = [_situer(ligne, positions) for ligne in qualification.lignes]
    classables = [entree for entree in entrees if entree.rang_min is not None]
    hors_classement = [entree for entree in entrees if entree.rang_min is None]

    paquets = _paquets(classables, rang_qualification, defaut)
    rangs = _numeroter(paquets)
    par_categorie = {entree.ligne.archer_id: entree.ligne.categorie_id for entree in classables}
    rangs_categorie: dict[ArcherId, tuple[int, int]] = {}
    for categorie_id in dict.fromkeys(par_categorie.values()):
        rangs_categorie.update(
            _numeroter(paquets, retenir=_de_categorie(par_categorie, categorie_id))
        )

    entree_par_archer = {entree.ligne.archer_id: entree for entree in classables}
    lignes = [
        _ligne(
            entree_par_archer[archer_id],
            rangs.get(archer_id),
            rangs_categorie.get(archer_id),
            decerne=paquet.decerne,
            en_lice=paquet.en_lice,
        )
        for paquet in paquets
        for archer_id in paquet.archers
    ]
    lignes += [
        _ligne(entree, None, None, decerne=False, en_lice=False) for entree in hors_classement
    ]
    return Palmares(lignes=tuple(lignes))


def _de_categorie(
    par_categorie: Mapping[ArcherId, CategorieId], categorie_id: CategorieId
) -> Callable[[ArcherId], bool]:
    """Le filtre « cet archer est-il de cette catégorie ? », fermé sur la catégorie voulue.

    Une fonction nommée plutôt qu'une `lambda` à paramètre par défaut : la seconde capture la
    variable de boucle par valeur *par effet de bord* d'une astuce de portée, ce que ni mypy ni un
    relecteur ne lisent volontiers.
    """
    return lambda archer: par_categorie.get(archer) == categorie_id


def _positions_par_archer(
    resultats: Sequence[ResultatPhase], connus: set[ArcherId]
) -> dict[ArcherId, tuple[ResultatPhase, PositionPhase]]:
    """La position **la plus tardive** de chaque archer (phases parcourues par `ordre` croissant).

    Les archers absents du classement de qualification sont ignorés : le palmarès liste les archers
    du **tournoi**, et faire naître une ligne depuis un tableau la rendrait anonyme (ni nom, ni
    catégorie). Le cas est une incohérence de données, pas un cas nominal — d'où le silence plutôt
    qu'une erreur, un palmarès public ne devant jamais tomber (même parti qu'E06US003).
    """
    retenues: dict[ArcherId, tuple[ResultatPhase, PositionPhase]] = {}
    for resultat in sorted(resultats, key=lambda phase: phase.ordre):
        for position in resultat.positions:
            if position.archer_id in connus:
                retenues[position.archer_id] = (resultat, position)
    return retenues


def _situer(
    ligne: LigneClassement,
    positions: Mapping[ArcherId, tuple[ResultatPhase, PositionPhase]],
) -> _Entree:
    """Situe un archer : la phase qui l'a classé, ou la qualification à défaut."""
    # Un **disqualifié** est sorti du classement (ADR-0050) et n'entre donc pas au tableau :
    # `ServiceSaisieDuels._decor` n'ensemence que les archers en lice. La garde est ici quand
    # même, parce que l'invariant vit **en amont** et qu'ADR-0067 promet de brancher d'autres
    # producteurs de `ResultatPhase` (poules, suisse) « sans toucher au domaine » — ceux-là
    # n'auront aucune raison de refaire le filtre. Sans elle, un DSQ prenait le rang 1 et l'or
    # (relevé en revue, axe adversarial).
    trouvee = (
        None if ligne.statut is StatutClassement.DISQUALIFIE else positions.get(ligne.archer_id)
    )
    if trouvee is None:
        return _Entree(
            ligne=ligne,
            bloc=0,
            rang_min=ligne.rang_scratch,
            rang_max=ligne.rang_scratch,
            origine=OriginePalmares.QUALIFICATION,
        )
    resultat, position = trouvee
    return _Entree(
        ligne=ligne,
        bloc=resultat.ordre,
        rang_min=position.rang_min,
        rang_max=position.rang_max,
        origine=OriginePalmares.DUELS,
        en_lice=position.en_lice,
    )


@dataclass(frozen=True)
class _Paquet:
    """Un groupe d'archers à numéroter d'un bloc, et ce que le tournoi en a décidé."""

    archers: tuple[ArcherId, ...]
    acquis: tuple[int, int] | None
    """La position **acquise** commune, quand elle vient d'une phase (`None` pour un rang de
    qualification). C'est elle qu'on rend telle quelle quand le paquet est encore en lice."""

    en_lice: bool
    decerne: bool
    """Un match a décerné ce rang : position acquise **fermée** (`min == max`) dans une
    phase."""


def _paquets(
    classables: Sequence[_Entree],
    rang_qualification: Mapping[ArcherId, int | None],
    defaut: Aggregation,
) -> tuple[_Paquet, ...]:
    """Ordonne les archers et regroupe en paquets ceux que rien ne départage.

    Deux archers forment un groupe quand ils sortent du **même bloc** sur la **même position** —
    c'est-à-dire quand aucun match ne les a séparés. La politique décide alors s'il faut éclater le
    groupe (par la qualification) ou le laisser tel quel… **sauf** si le groupe est encore en lice :
    ce que le tir doit trancher ne se départage pas d'avance.
    """
    ordonnees = sorted(
        classables,
        key=lambda entree: (-entree.bloc, entree.rang_min or 0, entree.rang_max or 0),
    )
    paquets: list[_Paquet] = []
    for _cle, groupe in _grouper(ordonnees):
        tete = groupe[0]
        identifiants = [entree.ligne.archer_id for entree in groupe]
        acquis = (
            (tete.rang_min, tete.rang_max)
            if tete.bloc > 0 and tete.rang_min is not None and tete.rang_max is not None
            else None
        )
        decerne = acquis is not None and acquis[0] == acquis[1]
        if any(entree.en_lice for entree in groupe):
            # Rien à départager : ces archers ont un match devant eux. Les deux finalistes
            # partagent « 1ᵉʳ-2ᵉ » jusqu'à ce que la finale tranche — leur appliquer la politique
            # reviendrait à décerner l'or au mieux qualifié **avant** le tir.
            paquets.append(_Paquet(tuple(identifiants), acquis, en_lice=True, decerne=False))
            continue
        paquets.extend(
            _Paquet(bucket, acquis, en_lice=False, decerne=decerne)
            for bucket in defaut.departager(identifiants, rang_qualification)
        )
    return tuple(paquets)


def _grouper(
    ordonnees: Sequence[_Entree],
) -> list[tuple[tuple[int, int | None, int | None], list[_Entree]]]:
    """Regroupe les entrées consécutives de même bloc et de même position acquise."""
    groupes: list[tuple[tuple[int, int | None, int | None], list[_Entree]]] = []
    for entree in ordonnees:
        cle = (entree.bloc, entree.rang_min, entree.rang_max)
        if groupes and groupes[-1][0] == cle:
            groupes[-1][1].append(entree)
        else:
            groupes.append((cle, [entree]))
    return groupes


def _numeroter(
    paquets: Sequence[_Paquet],
    retenir: Callable[[ArcherId], bool] | None = None,
) -> dict[ArcherId, tuple[int, int]]:
    """Numérote les paquets **1→N sans trou**, chacun occupant autant de rangs qu'il a de membres.

    `retenir` restreint la numérotation à un sous-ensemble (une catégorie) : l'**ordre** reste
    celui du palmarès, seule la numérotation repart de 1. C'est le même parti qu'E06US001 sur le
    rang de catégorie — même ordre, deux numérotations.

    ⚠️ **Un paquet encore en lice rend sa fourchette acquise, pas celle du curseur.** C'est le
    correctif du défaut le plus grave de cette US (revue, axe adversarial) : la numérotation par
    curseur donne un rang **exact** à qui est seul dans son paquet, ce qui arrive au vainqueur
    d'une demi-finale quand l'autre demie n'est pas encore validée — il sortait « 1ᵉʳ », médaille
    comprise, la finale non tirée. Sa position acquise dit `[1..2]` : c'est **elle** la vérité,
    et la rendre telle quelle est la seule façon de ne rien resserrer que le tir n'a pas resserré.
    La fourchette acquise vaut directement comme rang du tournoi parce qu'une phase dispute les
    rangs du haut de celui-ci — l'hypothèse qu'un repêchage romprait (`# DETTE-034`).

    ⚠️ Un paquet d'ex æquo filtré peut se réduire à un seul membre : deux archers 5ᵉ-8ᵉ scratch de
    catégories différentes sont chacun **seul** de sa catégorie à ce niveau, donc chacun reçoit un
    rang de catégorie **exact**. Ce n'est pas une contradiction : rien ne les départage entre eux,
    mais ils ne concourent pas l'un contre l'autre pour la médaille. Le podium ne s'y trompe pas —
    il exige `decerne`, pas l'exactitude d'affichage.
    """
    # DETTE-029 (../../docs/dette.md) — 4ᵉ site de l'arithmétique « un paquet d'ex æquo
    # occupe autant de rangs qu'il compte de membres, le suivant reprend après le saut »
    # (avec `classement._ranger`, `poule.classement_de_poule`, `suisse.classement_suisse`).
    # Nuance : la **détection** de l'égalité n'est pas dupliquée ici — `_grouper` et la
    # politique la portent —, seule la numérotation l'est, et sous une autre forme
    # (`(min, max)` plutôt que rang + drapeau). Le remède déjà proposé au registre
    # (`attribuer_rangs`) accommoderait ce site.
    rangs: dict[ArcherId, tuple[int, int]] = {}
    curseur = 1
    for paquet in paquets:
        membres = [archer for archer in paquet.archers if retenir is None or retenir(archer)]
        if not membres:
            continue
        fourchette = (
            paquet.acquis
            if paquet.en_lice and paquet.acquis is not None
            else (curseur, curseur + len(membres) - 1)
        )
        for archer in membres:
            rangs[archer] = fourchette
        curseur += len(membres)
    return rangs


def _ligne(
    entree: _Entree,
    rang: tuple[int, int] | None,
    rang_categorie: tuple[int, int] | None,
    *,
    decerne: bool,
    en_lice: bool,
) -> LignePalmares:
    return LignePalmares(
        decerne=decerne,
        en_lice=en_lice,
        rang_min=rang[0] if rang is not None else None,
        rang_max=rang[1] if rang is not None else None,
        rang_categorie_min=rang_categorie[0] if rang_categorie is not None else None,
        rang_categorie_max=rang_categorie[1] if rang_categorie is not None else None,
        archer_id=entree.ligne.archer_id,
        nom=entree.ligne.nom,
        prenom=entree.ligne.prenom,
        categorie_id=entree.ligne.categorie_id,
        categorie_libelle=entree.ligne.categorie_libelle,
        club_id=entree.ligne.club_id,
        origine=entree.origine,
        statut=entree.ligne.statut,
    )
