"""Fusion des rangs décernés par les phases — **ne rejoue aucun tableau** (ADR-0067, ADR-0085).

Rang **exact** (match terminal), **fourchette** (la plage du match perdu, ADR-0065) et **départage**
(politique `aggregation`) sont trois notions distinctes : la fourchette n'est pas une approximation.

⚠️ **Un type entre au palmarès sans qu'une ligne d'ici ne change** : `classement_lisible=True` le
fait entrer dans `TYPES_CLASSANTS_LUS`, donc au palmarès et au PDF. Bascule à distance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum

from domain.archer import ArcherId
from domain.categorie import CategorieId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.club import ClubId
from domain.podium import PorteePodium, ReglagePodiums
from domain.politiques import Aggregation, AggregationParQualification

LIBELLE_SCRATCH = "Toutes catégories"
"""Le nom du podium sans regroupement. ⚠️ **Surtout pas « Scratch »** : le glossaire réserve ce mot
à un **libellé de catégorie** (regroupement de classement arc nu, U21+S1+S2+S3).

Un club qui nomme sa catégorie arc nu « Scratch » — le cas nominal FFTA — et coche les deux portées
imprimait alors **deux blocs « Podium — Scratch »** sur la même page, contenus différents (relevé en
revue). Le code de la portée, lui, reste `scratch` : il est cohérent avec `rang_scratch`, qui porte
ce second sens partout dans le moteur.
"""


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
    tournoi : c'est la fusion qui les renumérote. `en_lice` dit si la fourchette peut encore se
    refermer **au tir** — le palmarès ne départage **que** ce qui est joué.
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

    ⚠️ **Ce champ garde les médailles.** `LignePalmares.decerne` se déduisait de « position acquise
    fermée », or le rang d'une qualification est *toujours* fermé : sans distinction d'origine, un
    tournoi de deux qualifications d'affilée remettrait or, argent et bronze **avant le moindre
    duel**. Vaut `DUELS` par défaut — les producteurs existants ne passent rien et doivent
    continuer de décerner ; l'inverse aurait retiré le podium à tous les tournois d'aujourd'hui.
    """

    rang_premier: int = 1
    """Le **premier rang du tournoi** que cette phase dispute (E05US020, ADR-0068 §5).

    Une phase qui prélève « les rangs 5 et suivants » ne joue pas pour la victoire : son vainqueur
    est 5ᵉ. Les positions arrivent dans l'espace de rangs **du tableau** ; ce décalage les ramène
    dans celui **du tournoi**. ⚠️ C'est ce qui résorbe `DETTE-034` : sans lui, l'ordre entre phases
    se lisait sur `ordre` et couronnait le vainqueur d'une **consolante** devant le finaliste du
    tableau principal. Vaut **1** par défaut.
    """


@dataclass(frozen=True)
class LignePalmares:
    """Une ligne du palmarès : le rang final d'un archer, scratch et dans sa catégorie.

    Les rangs sont des **fourchettes** (`min`/`max`), qui se referment dès qu'un rang exact est
    acquis. Deux champs plutôt qu'un « rang + ex æquo booléen » : la borne haute porte
    l'information (« 5ᵉ-8ᵉ » dit *combien* partagent), et un booléen obligerait chaque surface à
    recompter le groupe. `None` partout : l'archer est **hors classement** (disqualifié), pas «
    rang inconnu ».
    """

    rang_min: int | None
    rang_max: int | None
    rang_categorie_min: int | None
    rang_categorie_max: int | None
    rang_club_min: int | None
    rang_club_max: int | None
    """Le rang de l'archer **parmi ceux de son club** (E16US014), `None` s'il n'a pas de club.

    Troisième couple de bornes, et pas un rang de plus dans un champ générique : chacun se lit dans
    **son** espace de rangs et les trois cohabitent sur la même ligne. `None` sur `club_id is None`
    — l'anomalie « club inconnu » d'ADR-0014 n'est pas un club de rattachement.
    """

    decerne: bool
    """Un **match** a décerné ce rang — la seule forme qui vaut une médaille.

    ⚠️ **Ne se déduit PAS de `rang_min == rang_max`** : la renumérotation rend un rang « exact »
    dès qu'un archer est **seul dans son paquet**, ce qui arrive au finaliste dont la finale n'est
    pas tirée — l'écran lui remettait l'**or avant le tir**. Faux pour un rang de qualification,
    une position encore ouverte, et un ex æquo tranché par `aggregation` : celle-ci **décide** un
    ordre, elle ne le fait pas **gagner**.
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
    club_libelle: str | None
    """Le nom du club, ou `None`. ⚠️ **`None` a deux sens**, et le second n'est pas une anomalie :
    club inconnu (ADR-0014), **ou** **aucune** portée réglée — le référentiel n'est alors pas lu
    (`ServicePalmares._libelles_club`, garde élargie par E16US017/ADR-0104 : la lecture a désormais
    lieu dès qu'**une** portée l'est, défaut compris). Ne pas en déduire « club inconnu » sans
    regarder `club_id`.
    """

    origine: OriginePalmares
    statut: StatutClassement


@dataclass(frozen=True)
class PlacePodium:
    """Une place d'un podium : le rang **dans la portée du bloc**, et l'archer qui l'occupe.

    ⚠️ Le rang est porté ici et non lu sur la ligne : sans lui, chaque surface devrait aiguiller sur
    `bloc.portee` pour choisir entre trois couples de bornes — trois occasions de se tromper, dont
    une sur le papier où personne ne verrait l'erreur.
    """

    rang: int
    ligne: LignePalmares


@dataclass(frozen=True)
class BlocPodium:
    """Un podium affichable : ce qu'il récompense, ses places, et de quoi dire son état.

    ⚠️ **L'état est PORTÉ, jamais recalculé par l'appelant.** Trois fois de suite, cette US a
    produit un bloc dont l'énoncé portait sur une autre population que son contenu — blocs composés
    sur un palmarès filtré, puis effectif compté à l'écran sur les lignes affichées, puis garde de
    vacuité lue sur la vue. Les champs ci-dessous rendent la faute **non représentable** : ils sont
    remplis dans `_bloc`, là où le groupe est déjà filtré (ADR-0103 §6).
    """

    portee: PorteePodium
    cle: CategorieId | ClubId | None
    """L'identifiant de ce qui est regroupé — `None` pour le scratch, qui ne regroupe rien."""

    libelle: str
    places: tuple[PlacePodium, ...]
    effectif: int
    """Les archers du groupe qui peuvent **occuper une place** — pas tous ceux du groupe.

    Donc : rang issu des duels — `DETTE-028`, ceux restés en qualification n'entrent sur aucun
    podium — **et** classé. ⚠️ Le second terme est **défensif et non exercé** : `_situer` force
    `origine=QUALIFICATION` sur un disqualifié, donc le premier l'écarte déjà. Il garde les
    `Palmares` construits à la main et les producteurs à venir (relevé en revue).
    """

    en_attente: bool
    """Un archer du groupe a-t-il encore un match ? Sépare « pas encore » de « plus jamais »."""


@dataclass(frozen=True)
class Palmares:
    """Le classement final d'un tournoi, ordonné du 1ᵉʳ au dernier (hors classement en fin)."""

    lignes: tuple[LignePalmares, ...]
    duels_non_commences: bool = False
    """Une phase à duels **encore ouverte** n'a-t-elle rien livré ? (arbitrage du 01/09/2026)

    ⚠️ **Le nom dit ce qui est calculé, et pas plus** : ce n'est PAS « il reste des duels » — le
    champ est faux au milieu d'un tableau où il en reste des dizaines, l'attente s'y lisant alors
    archer par archer (`en_lice`). Sans ce fait, personne n'étant en lice tant qu'aucun résultat
    n'est lisible, chaque bloc annonçait le **définitif** toute la matinée.
    """

    def podiums(self, reglage: ReglagePodiums) -> tuple[BlocPodium, ...]:
        """Les podiums que ce tournoi décerne, dans l'ordre d'affichage (E16US014).

        Un bloc par groupe — un seul pour le scratch. ⚠️ **Un bloc sans place est rendu quand
        même** : à l'écran, un groupe qui disparaît se lit comme un groupe sans archers alors
        qu'il est en cours (`P-3`) ; c'est au **document** de sauter les vides. ⚠️ Un palmarès
        vide, lui, ne décerne rien — le scratch ne regroupant rien, il existerait toujours, et
        l'écran écrirait une phrase d'état au-dessus de personne.
        """
        if not self.lignes:
            return ()
        return tuple(
            self._bloc(portee, cle, libelle, reglage.profondeur)
            for portee in reglage.portees_actives()
            for cle, libelle in self._groupes(portee)
        )

    def _groupes(self, portee: PorteePodium) -> tuple[tuple[CategorieId | ClubId | None, str], ...]:
        """Ce que cette portée regroupe, dans l'ordre du palmarès — donc du meilleur au moins bon.

        Le scratch ne regroupe rien : un groupe unique, sans clé.
        """
        if portee is PorteePodium.SCRATCH:
            return ((None, LIBELLE_SCRATCH),)
        vus: dict[CategorieId | ClubId, str] = {}
        for ligne in self.lignes:
            if portee is PorteePodium.CATEGORIE:
                vus.setdefault(ligne.categorie_id, ligne.categorie_libelle)
            elif ligne.club_id is not None:
                # Garde-fou pour un `club_id` absent du référentiel, et pour tout appelant qui
                # désaccorderait réglage et calcul — cf. `libelle_de_club`, partagé avec le
                # classement des clubs pour que les deux vues nomment un club à l'identique.
                vus.setdefault(ligne.club_id, libelle_de_club(ligne))
        return tuple(vus.items())

    def _bloc(
        self,
        portee: PorteePodium,
        cle: CategorieId | ClubId | None,
        libelle: str,
        profondeur: int,
    ) -> BlocPodium:
        """Les places décernées d'un groupe — le tuple est vide tant qu'il n'y en a aucune.

        Trois conditions, les mêmes pour les trois portées (E06US004, élargi par E16US014) : le
        rang vient des **duels** et n'est plus ouvert ; il est **exact** ; il tient dans la
        profondeur. ⚠️ Un rang définitif suffit, il n'a pas à être **décerné par un match**
        (arbitrage du 03/08/2026) : le moteur ne monte qu'un seul tableau scratch (`DETTE-028`),
        donc l'exiger priverait de podium toutes les catégories, et tous les clubs.
        """
        groupe = tuple(ligne for ligne in self.lignes if self._cle_de(portee, ligne) == cle)
        places = tuple(
            PlacePodium(rang=rang, ligne=ligne)
            for ligne in groupe
            if ligne.origine is OriginePalmares.DUELS and not ligne.en_lice
            if (rang := _rang_exact(portee, ligne)) is not None and rang <= profondeur
        )
        return BlocPodium(
            portee=portee,
            cle=cle,
            libelle=libelle,
            places=places,
            effectif=sum(
                1
                for ligne in groupe
                if ligne.origine is OriginePalmares.DUELS and ligne.rang_min is not None
            ),
            # ⚠️ **Le créneau prime sur le groupe** : tant que des duels restent à tirer, rien
            # n'est définitif nulle part. On ne dit jamais « plus jamais » pendant que le
            # tournoi peut encore changer — l'erreur, si erreur il y a, va vers l'attente.
            en_attente=self.duels_non_commences or any(ligne.en_lice for ligne in groupe),
        )

    @staticmethod
    def _cle_de(portee: PorteePodium, ligne: LignePalmares) -> CategorieId | ClubId | None:
        """Le groupe auquel cette ligne appartient pour la portée donnée.

        ⚠️ Un archer **sans club** rend `None`, qui n'est la clé d'aucun bloc de club — il n'entre
        donc dans aucun. C'est `None` qui vaut « scratch », et le scratch retient tout le monde.
        """
        if portee is PorteePodium.SCRATCH:
            return None
        return ligne.categorie_id if portee is PorteePodium.CATEGORIE else ligne.club_id

    def pour_categorie(self, categorie_id: CategorieId) -> Palmares:
        """Restreint l'**affichage** à une catégorie, **sans renuméroter** le rang scratch.

        Même parti qu'E06US001 : on voit une catégorie sans perdre la position d'ensemble. Un
        recalcul ferait du 1ᵉʳ de sa catégorie un « 1ᵉʳ » tout court, ce qu'il n'est pas.
        """
        # `replace` et non une reconstruction champ par champ : la prochaine dérivation (une
        # `pour_depart` le jour où `DETTE-045` se résorbe) hériterait sinon d'un défaut silencieux.
        return replace(
            self,
            lignes=tuple(ligne for ligne in self.lignes if ligne.categorie_id == categorie_id),
        )


def libelle_de_club(ligne: LignePalmares) -> str:
    """Le nom du club d'une ligne, avec son repli **visible**.

    ⚠️ Un titre vide imprimerait « Podium — » au mur sans que personne sache pourquoi. Partagée
    avec `domain.classement_clubs` : le même club doit porter le même nom selon qu'on lit son
    podium ou le classement des clubs, et un commentaire ne suffisait pas à le tenir.
    """
    return ligne.club_libelle or f"Club {ligne.club_id}"


def _rang_exact(portee: PorteePodium, ligne: LignePalmares) -> int | None:
    """Le rang de la ligne **dans la portée**, s'il est fermé — `None` s'il reste une fourchette.

    Un *ex æquo* n'a pas de place de podium : personne ne saurait quelle médaille lui remettre.
    """
    if portee is PorteePodium.SCRATCH:
        minimum, maximum = ligne.rang_min, ligne.rang_max
    elif portee is PorteePodium.CATEGORIE:
        minimum, maximum = ligne.rang_categorie_min, ligne.rang_categorie_max
    else:
        minimum, maximum = ligne.rang_club_min, ligne.rang_club_max
    return minimum if minimum is not None and minimum == maximum else None


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
    libelles_club: Mapping[ClubId, str] | None = None,
    duels_non_commences: bool = False,
) -> Palmares:
    """Fusionne les rangs des phases en un palmarès (CA « podium » + CA « agrégation »).

    Trois temps : le **bloc** — chaque archer est situé par la phase la plus tardive qui l'a classé
    ; l'**ordre** — blocs décroissants puis position acquise croissante, si bien qu'un battu du 1ᵉʳ
    tour passe devant tout non-qualifié ; la **renumérotation** — 1→N sans trou. ⚠️ L'ordre entre
    archers se lit sur le **rang absolu** (`rang_premier`, qui résorbe DETTE-034), et un paquet
    **en lice** rend sa fourchette acquise — deux lignes peuvent donc se chevaucher.
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
        rangs_categorie.update(_numeroter(paquets, retenir=_du_groupe(par_categorie, categorie_id)))

    # E16US014 : le rang **dans son club**, calculé par la même passe que le rang de catégorie.
    # ⚠️ Un archer sans club n'est d'aucun groupe (ADR-0014) : il reste au classement, sans rang de
    # club — ce n'est pas un club à part, c'est une absence de club.
    par_club = {
        entree.ligne.archer_id: entree.ligne.club_id
        for entree in classables
        if entree.ligne.club_id is not None
    }
    rangs_club: dict[ArcherId, tuple[int, int]] = {}
    for club_id in dict.fromkeys(par_club.values()):
        rangs_club.update(_numeroter(paquets, retenir=_du_groupe(par_club, club_id)))

    libelles = libelles_club if libelles_club is not None else {}
    entree_par_archer = {entree.ligne.archer_id: entree for entree in classables}
    lignes = [
        _ligne(
            entree_par_archer[archer_id],
            rangs.get(archer_id),
            rangs_categorie.get(archer_id),
            rangs_club.get(archer_id),
            libelles,
            decerne=paquet.decerne,
            en_lice=paquet.en_lice,
        )
        for paquet in paquets
        for archer_id in paquet.archers
    ]
    lignes += [
        _ligne(entree, None, None, None, libelles, decerne=False, en_lice=False)
        for entree in hors_classement
    ]
    return Palmares(lignes=tuple(lignes), duels_non_commences=duels_non_commences)


def _du_groupe(
    par_archer: Mapping[ArcherId, CategorieId | ClubId], groupe: CategorieId | ClubId
) -> Callable[[ArcherId], bool]:
    """Le filtre « cet archer est-il de ce groupe ? », fermé sur le groupe voulu.

    Une catégorie ou un club (E16US014) : `_numeroter` ne demande qu'un prédicat, et les deux
    portées renumérotent à l'identique. Fonction nommée plutôt que `lambda` à paramètre par défaut :
    la seconde capture la variable de boucle *par effet de bord* d'une astuce de portée, que ni mypy
    ni un relecteur ne lisent volontiers.
    """
    return lambda archer: par_archer.get(archer) == groupe


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
    groupe, **sauf** s'il est encore en lice : ce que le tir doit trancher ne se départage pas
    d'avance.
    """

    # ⚠️ **Le tri se fait sur le rang absolu, pas sur l'ordre de phase** (E05US020, ADR-0068 §5).
    # Trier d'abord sur `-bloc` plaçait le vainqueur d'une consolante devant le finaliste du tableau
    # principal. Les tranches d'un déroulé valide ne se recoupent pas, donc les rangs absolus
    # suffisent ; `bloc` ne sert plus que de départage à rang égal.
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

    `retenir` restreint la numérotation à un sous-ensemble : l'**ordre** reste celui du palmarès,
    seule la numérotation repart de 1. ⚠️ **Un paquet encore en lice rend sa fourchette acquise,
    pas celle du curseur** : la numérotation par curseur donnait « 1ᵉʳ » — médaille comprise — au
    vainqueur d'une demi-finale dont l'autre demie n'était pas validée. ⚠️ Un paquet filtré peut se
    réduire à un membre : deux 5ᵉ-8ᵉ de catégories différentes sont chacun seul de la sienne.
    """

    # DETTE-029 — 4ᵉ site de l'arithmétique « un paquet d'ex æquo occupe autant de rangs qu'il
    # compte de membres » (avec `classement._ranger`, `poule`, `suisse`). Nuance : la **détection**
    # de l'égalité n'est pas dupliquée ici, seule la numérotation l'est, et sous une autre forme
    # (`(min, max)` plutôt que rang + drapeau).
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
    rang_club: tuple[int, int] | None,
    libelles_club: Mapping[ClubId, str],
    *,
    decerne: bool,
    en_lice: bool,
) -> LignePalmares:
    club_id = entree.ligne.club_id
    return LignePalmares(
        decerne=decerne,
        en_lice=en_lice,
        rang_min=rang[0] if rang is not None else None,
        rang_max=rang[1] if rang is not None else None,
        rang_categorie_min=rang_categorie[0] if rang_categorie is not None else None,
        rang_categorie_max=rang_categorie[1] if rang_categorie is not None else None,
        rang_club_min=rang_club[0] if rang_club is not None else None,
        rang_club_max=rang_club[1] if rang_club is not None else None,
        archer_id=entree.ligne.archer_id,
        nom=entree.ligne.nom,
        prenom=entree.ligne.prenom,
        categorie_id=entree.ligne.categorie_id,
        categorie_libelle=entree.ligne.categorie_libelle,
        club_id=club_id,
        # `None` et non "" : l'écran distingue « club inconnu » (ADR-0014) d'un nom vide, et le
        # référentiel peut manquer au lot passé sans que la ligne mente sur l'absence de club.
        club_libelle=libelles_club.get(club_id) if club_id is not None else None,
        origine=entree.origine,
        statut=entree.ligne.statut,
    )
