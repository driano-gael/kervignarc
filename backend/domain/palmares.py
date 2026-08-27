"""Fusion des rangs décernés par les phases — **ne rejoue aucun tableau** (ADR-0067, ADR-0085).

Rang **exact** (match terminal), **fourchette** (la plage du match perdu, ADR-0065) et **départage**
(politique `aggregation`) sont trois notions distinctes : la fourchette n'est pas une approximation.

⚠️ **Un type entre au palmarès sans qu'une ligne d'ici ne change** : `classement_lisible=True` le
fait entrer dans `TYPES_CLASSANTS_LUS`, donc au palmarès et au PDF. Bascule à distance.
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
    origine: OriginePalmares = OriginePalmares.DUELS
    """Ce qui a décidé ces positions — **un tir de duel, ou un classement** (E05US025).

    Jusqu'ici la question ne se posait pas : seules les phases à tableau produisaient un
    `ResultatPhase`, donc `_situer` étiquetait `DUELS` en dur. Un déroulé peut désormais enchaîner
    **plusieurs qualifications** (ADR-0082), et la seconde décerne bien des rangs — sans qu'aucun
    duel ait eu lieu.

    ⚠️ **Ce champ garde les médailles.** `LignePalmares.decerne` — la seule forme qui vaut un podium
    — se déduisait de « position acquise fermée » (`rang_min == rang_max`). Or le rang d'une
    qualification est *toujours* fermé : sans distinction d'origine, un tournoi de deux
    qualifications d'affilée remettrait or, argent et bronze **avant le moindre duel**. C'est
    exactement le défaut que la docstring de `decerne` dit avoir corrigé en revue d'E06US004, sous
    une autre forme.

    Vaut `DUELS` par défaut : les producteurs existants (phases à tableau) ne passent rien et
    doivent continuer de décerner. Un défaut inverse aurait retiré le podium à tous les tournois
    d'aujourd'hui — une régression bien plus grave que le trou comblé."""

    rang_premier: int = 1
    """Le **premier rang du tournoi** que cette phase dispute (E05US020, ADR-0068 §5).

    Une phase qui prélève « les rangs 5 et suivants » ne joue pas pour la victoire : son vainqueur
    est 5ᵉ, pas 1ᵉʳ. Les positions arrivent dans l'espace de rangs **du tableau** (1..effectif) ;
    ce décalage les ramène dans celui **du tournoi**.

    ⚠️ C'est ce qui résorbe `DETTE-034`. Sans lui, l'ordre entre phases se lisait sur `ordre` — « la
    plus tardive l'emporte » — et couronnait le vainqueur d'une **consolante** devant le finaliste
    du tableau principal. Défaut inatteignable tant qu'aucun moteur ne consommait les prélèvements,
    rendu atteignable par E05US020 et mesuré en revue adversariale.

    Vaut **1** par défaut : une phase qui ne prélève rien dispute le tournoi entier."""


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


@dataclass(frozen=True)
class Palmares:
    """Le classement final d'un tournoi, ordonné du 1ᵉʳ au dernier (hors classement en fin)."""

    lignes: tuple[LignePalmares, ...]

    def podium(self, categorie_id: CategorieId) -> tuple[LignePalmares, ...]:
        """Les quatre premiers **d'une catégorie** (CA « podium »).

        Trois conditions, et chacune ferme un trou trouvé en revue :

        1. **le rang vient des duels et n'est plus ouvert** (`origine is DUELS`, `not en_lice`).
           Sans la première moitié, le podium se remplissait sur les seuls scores du matin : un
           rang de qualification étant exact par construction, l'écran décernait « Or / Argent /
           Bronze » **avant le moindre duel**. Sans la seconde, le vainqueur d'une demi-finale
           recevait l'or **avant la finale** — sa position `[1..2]`, seule de son paquet, sortait
           « 1ᵉʳ » de la renumérotation ;
        2. **rang de catégorie exact** — on ne remet pas une médaille à quatre archers *ex æquo* ;
        3. **≤ 4** — finale (1-2) et petite finale (3-4).

        ⚠️ **Un rang définitif suffit ; il n'a pas à être décerné par un match** (arbitrage du
        commanditaire, 03/08/2026). La condition « décerné » avait été essayée et **amputait le
        livrable** : le moteur ne monte qu'un **seul tableau scratch** (`# DETTE-028`), donc quatre
        archers du tournoi entier seulement ont un rang décerné par un match terminal — toutes les
        autres catégories perdaient leur podium, **tournoi terminé**, et le PDF affiché au mur
        omettait leurs blocs. Le CA (« rangs 1-4 issus de la finale/petite finale ») présuppose un
        tableau **par catégorie**, que le moteur ne réalise pas encore.

        La provenance n'est pas perdue pour autant : `LignePalmares.decerne` la porte, et l'écran
        comme le PDF **disent** quand une place a été rangée au classement plutôt que gagnée au
        tir. C'est ce qui garde la distinction demandée entre *classement* et *podium* sans faire
        disparaître les médailles.

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
            and ligne.origine is OriginePalmares.DUELS
            and not ligne.en_lice
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
       ⚠️ **L'ordre entre archers se lit sur le rang absolu**, pas sur l'ordre de
       phase : une phase qui prélève « les rangs 5 et suivants » dispute les places 5+, et
       son vainqueur est 5ᵉ. `ResultatPhase.rang_premier` porte ce décalage (E05US020,
       ADR-0068 §5, qui résorbe DETTE-034) ;
    2. **l'ordre** — blocs décroissants, puis position acquise croissante. Un battu du 1ᵉʳ tour du
       tableau passe donc devant tout non-qualifié, quel qu'ait été son rang de qualification :
       il a franchi une porte que l'autre n'a pas franchie ;
    3. **la renumérotation** — les rangs repartent de 1 et se suivent **sans trou**, chaque paquet
       d'ex æquo occupant autant de rangs qu'il compte d'archers. Le palmarès est un classement du
       tournoi, pas la juxtaposition des numérotations de ses phases. ⚠️ **Une exception** :
       un paquet encore **en lice** rend sa fourchette acquise (`_numeroter`), si bien que deux
       lignes peuvent se **chevaucher** tant que le tir n'a pas tranché — c'est ce qu'un
       tournoi en cours a de vrai à dire.

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
    decalage = resultat.rang_premier - 1
    return _Entree(
        ligne=ligne,
        bloc=resultat.ordre,
        rang_min=position.rang_min + decalage,
        rang_max=position.rang_max + decalage,
        # E05US025 : l'origine vient de la **phase**, elle n'est plus `DUELS` en dur. Une seconde
        # qualification décerne des rangs sans qu'aucun duel ait eu lieu, et l'écran doit pouvoir le
        # dire — « 9ᵉ » ne veut pas dire la même chose selon qu'un duel perdu l'a décidé ou qu'un
        # second tour de qualification l'a classé.
        origine=resultat.origine,
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
    # ⚠️ **Le tri se fait sur le rang absolu, pas sur l'ordre de phase** (E05US020, ADR-0068 §5).
    # Trier d'abord sur `-bloc` — « la phase la plus tardive l'emporte » — plaçait le vainqueur
    # d'une consolante devant le finaliste du tableau principal. Les tranches d'un déroulé valide ne
    # se recoupent pas (`verifier_sequence`), donc les rangs absolus suffisent à ordonner ; `bloc`
    # ne sert plus que de départage, pour qu'à rang égal une position **jouée** précède un rang de
    # qualification.
    ordonnees = sorted(
        classables,
        key=lambda entree: (entree.rang_min or 0, entree.rang_max or 0, -entree.bloc),
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
        # ⚠️ **`decerne` exige un duel, pas seulement un rang exact** (E05US025). Le rang d'une
        # qualification est fermé par construction (`rang_min == rang_max`) : sans la condition
        # d'origine, le vainqueur d'une seconde qualification recevait l'or, et un déroulé fait de
        # trois qualifications remettait un podium complet sans qu'une flèche ait été tirée en duel.
        decerne = (
            acquis is not None and acquis[0] == acquis[1] and tete.origine is OriginePalmares.DUELS
        )
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
        # ⚠️ `retenir is None` : la fourchette acquise est exprimée dans l'espace de
        # rangs **du tournoi**, pas dans celui d'une catégorie. L'honorer aussi dans la
        # passe par catégorie rendait « 1ᵉʳ-8ᵉ » à une catégorie de deux archers, et
        # faisait chevaucher un rang de catégorie ouvert avec un rang décerné — défaut
        # relevé par trois axes en contre-revue, et régression par rapport à l'état
        # d'avant le correctif. La passe par catégorie retombe donc sur le curseur,
        # borné par l'effectif de la catégorie ; la médaille reste gardée par `decerne`.
        fourchette = (
            paquet.acquis
            if retenir is None and paquet.en_lice and paquet.acquis is not None
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
