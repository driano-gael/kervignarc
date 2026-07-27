"""Agrégat de duel `Duel` / barème de duel `BaremeDuel` — la saisie d'un match (E04US013, ADR-0049).

Vocabulaire du glossaire : un **duel** oppose deux `Participant` sur un match du tableau ; une
**manche** (`MancheDuel`, un « set ») oppose deux **volées** ; un **point de set** récompense la
manche (2 au vainqueur, 1-1 à égalité, 0 au perdant, référentiel §7). Le vainqueur est le premier à
`points_pour_gagner` (6 FFTA, 4 club) ; à égalité de sets, un **barrage** (shoot-off, §8.2) tranche.

Modèle de domaine **pur** (immuable, sans dépendance framework — règle 1), jumeau de `Serie` :

- La **flèche est une valeur** (`ZoneScore`) et une manche **réutilise `Volee`** (`.points`) — on
  mutualise la volée, pas la racine : `Serie` somme les points d'**un** archer au cumul, un duel
  **oppose** deux volées manche par manche et s'arrête à 6. Structures distinctes (ADR-0049 §1).
- La **configuration** (barème, zones admises du blason tiré) n'est **pas** dupliquée dans
  l'agrégat : elle est **passée aux opérations** par le service (lues sur la phase et le blason).
- L'**arc à poulies** tire **au cumul** (A.7.5.2), sans sets : `ModeDuel.CUMUL` — le plus haut total
  des 5 volées gagne. Classique / arc nu tirent en `ModeDuel.SETS` (§6.2, §7).

Le **barème se résout par (phase, arme)** via un `ResolveurBaremeDuel` **injecté** (défaut FFTA,
`ResolveurBaremeDuelFfta`) : c'est le point d'injection d'ADR-0004 où E01US011 branchera les
catalogues configurables (FFTA / club) — l'agrégat n'en sait rien (règle 2).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

from domain.blason import ZoneScore
from domain.erreurs import (
    BaremeDuelInvalide,
    BarrageIndecis,
    BarrageNonRequis,
    DuelDejaTranche,
    DuelIncomplet,
    DuelVerrouille,
    NombreFlechesVoleeInvalide,
    NomIntervenantInvalide,
    NumeroMancheInvalide,
    ValeurHorsBlason,
)
from domain.participant import Participant
from domain.serie import Volee

# Points de set (référentiel §7) : le vainqueur de la manche marque 2, égalité 1-1, perdant 0.
POINTS_MANCHE_GAGNEE = 2
POINTS_MANCHE_NULLE = 1
POINTS_MANCHE_PERDUE = 0


class Cote(str, Enum):
    """Le camp d'un duelliste dans un match : `HAUT`/`BAS` (les occupants du `Match`, ADR-0028)."""

    HAUT = "haut"
    BAS = "bas"


class ModeDuel(str, Enum):
    """Comment se tranche un duel : au **système de sets** (classique/arc nu, §7) ou au **cumul**
    (arc à poulies, A.7.5.2 — 5 volées, plus haut total, sans points de set)."""

    SETS = "sets"
    CUMUL = "cumul"


def _points_zone(zone: ZoneScore) -> int:
    """Points d'une zone : sa valeur numérique, le manqué (`M`) valant 0 (jumeau de `serie`)."""
    return 0 if zone is ZoneScore.MANQUE else int(zone.value)


def _valider_volee(
    valeurs: tuple[ZoneScore, ...], zones_admises: tuple[ZoneScore, ...], nb_fleches_par_volee: int
) -> None:
    """Vérifie le nombre de flèches et l'appartenance aux zones (jumeau de `serie`).

    Duplication assumée du contrôle de volée (2ᵉ occurrence, règle 12) : les deux agrégats ont leur
    propre barème (nb flèches), un socle partagé les coupleraient. Lève `NombreFlechesVoleeInvalide`
    ou `ValeurHorsBlason`.
    """
    if len(valeurs) != nb_fleches_par_volee:
        raise NombreFlechesVoleeInvalide(
            f"Une volée doit compter {nb_fleches_par_volee} flèche(s), pas {len(valeurs)}."
        )
    if any(v not in zones_admises for v in valeurs):
        raise ValeurHorsBlason("Une valeur saisie n'est pas une zone admise du blason tiré.")


def _intervenant_valide(nom: str) -> str:
    """Normalise le nom de qui valide ; refuse le vide (`NomIntervenantInvalide`)."""
    normalise = nom.strip()
    if not normalise:
        raise NomIntervenantInvalide("Le nom de qui valide un duel ne peut être vide.")
    return normalise


@dataclass(frozen=True)
class BaremeDuel:
    """Le format d'un duel : mode (sets / cumul), nombre de manches, flèches par volée, seuil.

    Value object **pur** paramétré (jumeau de `BaremeQualification`) — une **structure**, pas un
    choix dans un catalogue fermé. `points_pour_gagner` ne sert qu'en `SETS` (ignoré en `CUMUL`).
    """

    mode: ModeDuel
    nb_manches: int
    nb_fleches_par_volee: int
    points_pour_gagner: int

    def __post_init__(self) -> None:
        if self.nb_manches < 1 or self.nb_fleches_par_volee < 1:
            raise BaremeDuelInvalide("Un duel demande au moins une manche d'au moins une flèche.")
        if self.mode is ModeDuel.SETS and not 1 <= self.points_pour_gagner <= 2 * self.nb_manches:
            raise BaremeDuelInvalide(
                "Le seuil de points de set doit être atteignable "
                f"(entre 1 et {2 * self.nb_manches})."
            )

    @staticmethod
    def preset_ffta_classique() -> BaremeDuel:
        """FFTA arc classique / arc nu (§6.2, §7) : sets, 5 manches de 3, premier à **6** points."""
        return BaremeDuel(ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=6)

    @staticmethod
    def preset_ffta_poulies() -> BaremeDuel:
        """FFTA arc à poulies (A.7.5.2) : **cumul** de 5 volées de 3, sans points de set."""
        return BaremeDuel(
            ModeDuel.CUMUL, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=0
        )

    @staticmethod
    def preset_club() -> BaremeDuel:
        """Format club (`Tableaux.xlsx`, §11) : sets, 5 manches de 3, premier à **4** points."""
        return BaremeDuel(ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=4)


@dataclass(frozen=True)
class MancheDuel:
    """Une manche (« set ») : son rang et les **deux volées** opposées (réutilise `Volee`)."""

    numero: int
    volee_haut: Volee
    volee_bas: Volee


@dataclass(frozen=True)
class Barrage:
    """Le tir de barrage (§8.2) : une flèche par camp ; `gagnant_designe` tranche à flèches égales
    (le plus près du centre, jugé par le scoreur — l'application ne mesure pas la distance)."""

    fleche_haut: ZoneScore
    fleche_bas: ZoneScore
    gagnant_designe: Cote | None = None


@dataclass(frozen=True)
class ResultatDuel:
    """L'issue calculée d'un duel : les points de chaque camp (points de set en `SETS`, cumul en
    `CUMUL`), le `vainqueur` (`None` si indécis), `termine` (vainqueur connu) et `barrage_requis`
    (égalité en attente d'un shoot-off)."""

    points_haut: int
    points_bas: int
    vainqueur: Cote | None
    termine: bool
    barrage_requis: bool


def _points_manche(manche: MancheDuel) -> tuple[int, int]:
    """Points de set d'une manche : 2-0 / 1-1 / 0-2 selon la comparaison des volées (§7)."""
    a, b = manche.volee_haut.points, manche.volee_bas.points
    if a > b:
        return POINTS_MANCHE_GAGNEE, POINTS_MANCHE_PERDUE
    if a < b:
        return POINTS_MANCHE_PERDUE, POINTS_MANCHE_GAGNEE
    return POINTS_MANCHE_NULLE, POINTS_MANCHE_NULLE


@dataclass(frozen=True)
class Duel:
    """Le scoring d'un match du tableau : deux participants, ses manches, son éventuel barrage.

    Racine d'agrégat **immuable** (comme `Serie`/`Tableau`) : toute saisie renvoie un **nouveau**
    `Duel`. Le résultat (points, vainqueur, barrage requis) est **dérivé** des manches et du barème.
    Une fois **validé** (au nom du scoreur), le duel est verrouillé et son vainqueur transmis au
    moteur `Tableau.jouer` (par le service).
    """

    bareme: BaremeDuel
    participant_haut: Participant
    participant_bas: Participant
    manches: tuple[MancheDuel, ...] = ()
    barrage: Barrage | None = None
    validee_par: str | None = None

    @staticmethod
    def vide(
        bareme: BaremeDuel, participant_haut: Participant, participant_bas: Participant
    ) -> Duel:
        """Un duel sans manche, prêt à recevoir la saisie."""
        return Duel(
            bareme=bareme, participant_haut=participant_haut, participant_bas=participant_bas
        )

    def manche(self, numero: int) -> MancheDuel | None:
        """La manche de ce rang, ou `None`."""
        return next((m for m in self.manches if m.numero == numero), None)

    @property
    def verrouille(self) -> bool:
        """Un duel validé est verrouillé : plus aucune saisie (pas de correction tracée ici)."""
        return self.validee_par is not None

    # --- résultat (dérivé) ---------------------------------------------------------------------

    @property
    def resultat(self) -> ResultatDuel:
        """L'issue du duel selon son mode (sets ou cumul)."""
        if self.bareme.mode is ModeDuel.SETS:
            return self._resultat_sets()
        return self._resultat_cumul()

    @property
    def vainqueur(self) -> Participant | None:
        """Le `Participant` vainqueur (ce que le service transmet à `Tableau.jouer`), ou `None`."""
        cote = self.resultat.vainqueur
        if cote is Cote.HAUT:
            return self.participant_haut
        if cote is Cote.BAS:
            return self.participant_bas
        return None

    def _manches_ordonnees(self) -> tuple[MancheDuel, ...]:
        return tuple(sorted(self.manches, key=lambda m: m.numero))

    def _vainqueur_barrage(self) -> Cote | None:
        """Le vainqueur du barrage : plus haute flèche, sinon la désignation (§8.2)."""
        if self.barrage is None:
            return None
        haut = _points_zone(self.barrage.fleche_haut)
        bas = _points_zone(self.barrage.fleche_bas)
        if haut > bas:
            return Cote.HAUT
        if bas > haut:
            return Cote.BAS
        return self.barrage.gagnant_designe

    def _resultat_sets(self) -> ResultatDuel:
        """Résultat au système de sets : accumule les points, s'arrête au seuil, barrage si 5-5."""
        seuil = self.bareme.points_pour_gagner
        points_haut = points_bas = 0
        for manche in self._manches_ordonnees():
            gain_haut, gain_bas = _points_manche(manche)
            points_haut += gain_haut
            points_bas += gain_bas
            if points_haut >= seuil:
                return ResultatDuel(points_haut, points_bas, Cote.HAUT, True, False)
            if points_bas >= seuil:
                return ResultatDuel(points_haut, points_bas, Cote.BAS, True, False)
        if len(self.manches) < self.bareme.nb_manches:
            return ResultatDuel(points_haut, points_bas, None, False, False)
        # Toutes les manches jouées, personne au seuil : égalité → barrage (§7).
        if points_haut != points_bas:  # défensif : ne survient pas aux barèmes FFTA/club
            avance = Cote.HAUT if points_haut > points_bas else Cote.BAS
            return ResultatDuel(points_haut, points_bas, avance, True, False)
        gagnant = self._vainqueur_barrage()
        if gagnant is None:
            return ResultatDuel(points_haut, points_bas, None, False, True)
        if gagnant is Cote.HAUT:
            points_haut += 1  # le vainqueur du barrage marque 1 point de set (6-5, §7)
        else:
            points_bas += 1
        return ResultatDuel(points_haut, points_bas, gagnant, True, False)

    def _resultat_cumul(self) -> ResultatDuel:
        """Résultat au cumul (poulies) : plus haut total ; barrage si égalité (A.7.5.2)."""
        total_haut = sum(m.volee_haut.points for m in self.manches)
        total_bas = sum(m.volee_bas.points for m in self.manches)
        if len(self.manches) < self.bareme.nb_manches:
            return ResultatDuel(total_haut, total_bas, None, False, False)
        if total_haut > total_bas:
            return ResultatDuel(total_haut, total_bas, Cote.HAUT, True, False)
        if total_bas > total_haut:
            return ResultatDuel(total_haut, total_bas, Cote.BAS, True, False)
        gagnant = self._vainqueur_barrage()
        if gagnant is None:
            return ResultatDuel(total_haut, total_bas, None, False, True)
        return ResultatDuel(total_haut, total_bas, gagnant, True, False)

    # --- saisie --------------------------------------------------------------------------------

    def saisir_manche(
        self,
        numero: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
        *,
        zones_admises: tuple[ZoneScore, ...],
        nb_fleches_par_volee: int,
    ) -> Duel:
        """Saisit ou réédite (avant validation) la manche `numero` : les deux volées opposées.

        Borne le rang par le barème (`NumeroMancheInvalide`), valide chaque volée (nombre de
        flèches, zones du blason). Refuse d'**ajouter** une manche à un duel tranché
        (`DuelDejaTranche`) ou d'écrire sur un duel validé (`DuelVerrouille`) ; la ré-édition d'une
        manche existante reste possible tant que le duel n'est pas validé.
        """
        if self.verrouille:
            raise DuelVerrouille("Ce duel est validé : plus aucune saisie n'est possible.")
        if not 1 <= numero <= self.bareme.nb_manches:
            raise NumeroMancheInvalide(
                f"Le rang d'une manche est entre 1 et {self.bareme.nb_manches} (barème)."
            )
        _valider_volee(valeurs_haut, zones_admises, nb_fleches_par_volee)
        _valider_volee(valeurs_bas, zones_admises, nb_fleches_par_volee)
        if self.manche(numero) is None and self.resultat.termine:
            raise DuelDejaTranche("Le duel est déjà gagné : pas de manche supplémentaire à saisir.")
        manche = MancheDuel(
            numero=numero,
            volee_haut=Volee(numero=numero, valeurs=valeurs_haut),
            volee_bas=Volee(numero=numero, valeurs=valeurs_bas),
        )
        autres = tuple(m for m in self.manches if m.numero != numero)
        manches = tuple(sorted((*autres, manche), key=lambda m: m.numero))
        return replace(self, manches=manches)

    def saisir_barrage(
        self,
        fleche_haut: ZoneScore,
        fleche_bas: ZoneScore,
        *,
        zones_admises: tuple[ZoneScore, ...],
        gagnant_designe: Cote | None = None,
    ) -> Duel:
        """Saisit le tir de barrage (§8.2) — une flèche par camp — quand l'égalité l'exige.

        Refuse si le barrage n'est pas requis (`BarrageNonRequis`), sur un duel validé
        (`DuelVerrouille`), une flèche hors blason (`ValeurHorsBlason`), ou une égalité de flèche
        sans désignation du plus près du centre (`BarrageIndecis`).
        """
        if self.verrouille:
            raise DuelVerrouille("Ce duel est validé : plus aucune saisie n'est possible.")
        if not self.resultat.barrage_requis:
            raise BarrageNonRequis("Le duel n'est pas à égalité : aucun barrage à tirer.")
        for fleche in (fleche_haut, fleche_bas):
            if fleche not in zones_admises:
                raise ValeurHorsBlason("Une flèche de barrage n'est pas une zone admise du blason.")
        if _points_zone(fleche_haut) == _points_zone(fleche_bas) and gagnant_designe is None:
            raise BarrageIndecis(
                "Flèches de barrage à égalité : désignez le plus près du centre (§8.2)."
            )
        return replace(self, barrage=Barrage(fleche_haut, fleche_bas, gagnant_designe))

    def valider(self, par: str) -> Duel:
        """Verrouille le duel **tranché** au nom du scoreur `par` (grain fin de duel).

        Refuse un duel non tranché (`DuelIncomplet`) ou un nom vide (`NomIntervenantInvalide`). Le
        vainqueur est ensuite transmis au moteur `Tableau.jouer` par le service (ADR-0049 §4).
        """
        par = _intervenant_valide(par)
        if not self.resultat.termine:
            raise DuelIncomplet(
                "On ne valide qu'un duel tranché (toutes manches / barrage résolus)."
            )
        return replace(self, validee_par=par)


class ResolveurBaremeDuel(Protocol):
    """Résout le barème d'un duel pour une **arme** (référentiel §10 : par (phase, division)).

    Point d'injection d'ADR-0004 (règle 2) : E01US011 y branchera les catalogues configurables
    (FFTA / club, surcharge par arme) sans toucher l'agrégat ni le service."""

    def bareme_pour(self, arme: str | None) -> BaremeDuel: ...


@dataclass(frozen=True)
class ResolveurBaremeDuelFfta:
    """Résolveur **par défaut** (FFTA) : cumul pour l'arc à poulies (A.7.5.2), sets sinon (§7).

    L'arme est un **champ texte libre** de `Categorie` (pas d'énuméré) : on reconnaît « poulies /
    compound » par normalisation. Fragile par nature — **centralisé ici** (point unique de
    correction quand E01US018/E01US011 formalisera l'arme). ADR-0049 §résolveur.
    """

    def bareme_pour(self, arme: str | None) -> BaremeDuel:
        if _est_poulies(arme):
            return BaremeDuel.preset_ffta_poulies()
        return BaremeDuel.preset_ffta_classique()


def _est_poulies(arme: str | None) -> bool:
    """Vrai si l'arme désigne l'arc à poulies (cumul, A.7.5.2), par normalisation du texte libre."""
    if arme is None:
        return False
    normalise = arme.strip().lower()
    return "poulie" in normalise or "compound" in normalise
