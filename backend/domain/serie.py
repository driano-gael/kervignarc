"""Agrégat **Serie** — l'état (les volées) ; la configuration lui est **passée** par le service.

Zones du blason, flèches par volée, grain de validation ne sont pas dupliqués dans l'agrégat : ses
invariants sont vérifiés à chaque opération contre la config fournie.

⚠️ **Le reliquat de volées est VALIDÉ en fin de barème** (moins de N pour un grain « toutes les
N ») — sinon les dernières volées ne se verrouilleraient jamais.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.archer import ArcherId
from domain.blason import ZoneScore
from domain.erreurs import (
    NombreFlechesVoleeInvalide,
    NomIntervenantInvalide,
    NumeroVoleeInvalide,
    RienAValider,
    SerieIncomplete,
    ValeurHorsBlason,
    VoleeIntrouvable,
    VoleeNonVerrouillee,
    VoleeVerrouillee,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import PhaseId
from domain.tournoi import TournoiId

SerieId = int
"""Identifiant technique d'une série, attribué par la persistance."""


def _points_zone(zone: ZoneScore) -> int:
    """Points d'une zone : sa valeur numérique, le manqué (`M`) valant 0."""
    return 0 if zone is ZoneScore.MANQUE else int(zone.value)


@dataclass(frozen=True)
class Volee:
    """Une volée saisie : ses `valeurs`, qui l'a saisie (`saisie_par`, déclaratif) et, une fois
    validée, qui l'a validée (`validee_par` = nom du scoreur ; `None` tant qu'elle ne l'est pas).

    Le verrou n'est pas un champ à part : une volée est **verrouillée** dès qu'elle porte un
    validateur. `points` somme les zones (le manqué vaut 0)."""

    numero: int
    valeurs: tuple[ZoneScore, ...]
    saisie_par: str | None = None
    validee_par: str | None = None

    @property
    def verrouillee(self) -> bool:
        """Une volée validée est verrouillée : seule la correction tracée peut encore l'écrire."""
        return self.validee_par is not None

    @property
    def points(self) -> int:
        """Total des points de la volée (somme des zones ; `M` = 0)."""
        return sum(_points_zone(z) for z in self.valeurs)


def valider_valeurs_volee(
    valeurs: tuple[ZoneScore, ...],
    zones_admises: tuple[ZoneScore, ...],
    nb_fleches_par_volee: int,
) -> None:
    """Vérifie qu'une volée compte le bon nombre de flèches, toutes dans les zones du blason tiré.

    Lève `NombreFlechesVoleeInvalide` ou `ValeurHorsBlason`. **Publique** à dessein : « qu'est-ce
    qu'une volée valide » est **une** règle du domaine, et d'autres cas d'usage que la saisie
    l'appliquent — la simulation (E15US003) valide sans repasser par le workflow de grain (ADR-0055
    §3) ni dupliquer la règle. Même geste que `blason.valider_zones`.
    """
    if len(valeurs) != nb_fleches_par_volee:
        raise NombreFlechesVoleeInvalide(
            f"Une volée doit compter {nb_fleches_par_volee} flèche(s), pas {len(valeurs)}."
        )
    hors = [v for v in valeurs if v not in zones_admises]
    if hors:
        raise ValeurHorsBlason("Une valeur saisie n'est pas une zone admise du blason tiré.")


def _intervenant_valide(nom: str) -> str:
    """Normalise le nom de qui valide/corrige ; refuse le vide (`NomIntervenantInvalide`)."""
    normalise = nom.strip()
    if not normalise:
        raise NomIntervenantInvalide("Le nom de qui valide ou corrige une volée ne peut être vide.")
    return normalise


def _avec_volee(volees: tuple[Volee, ...], volee: Volee) -> tuple[Volee, ...]:
    """Remplace la volée de même numéro si elle existe, sinon l'ajoute ; trie par numéro."""
    autres = tuple(v for v in volees if v.numero != volee.numero)
    return tuple(sorted((*autres, volee), key=lambda v: v.numero))


@dataclass(frozen=True)
class Serie:
    """La feuille de marque d'un archer **dans une phase** : l'ensemble ordonné de ses volées.

    Racine d'agrégat : toute mutation renvoie une **nouvelle** instance, et le cumul ne compte que
    les volées **validées**. ⚠️ **La clé est `(phase_id, archer_id)`, pas `(tournoi_id,
    archer_id)`** (E05US025, ADR-0082) : un déroulé peut enchaîner plusieurs qualifications, où
    l'archer tient **deux feuilles distinctes**. Cela résorbe `DETTE-046` au passage. `tournoi_id`
    **reste**, comme cadre lu par les vues d'ensemble — plus comme clé.
    """

    tournoi_id: TournoiId
    archer_id: ArcherId
    phase_id: PhaseId
    volees: tuple[Volee, ...] = ()
    id: SerieId | None = None

    @staticmethod
    def vide(tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId) -> Serie:
        """Une série sans volée, prête à recevoir la saisie **dans cette phase**.

        `phase_id` est **obligatoire** et sans valeur par défaut : un défaut aurait laissé les
        appelants d'avant l'US continuer de compiler en écrivant tous dans la même feuille, ce qui
        est exactement le défaut que l'US corrige. Le compilateur doit les faire tomber un par un.
        """
        return Serie(tournoi_id=tournoi_id, archer_id=archer_id, phase_id=phase_id)

    def volee(self, numero: int) -> Volee | None:
        """La volée de ce numéro, ou `None`."""
        return next((v for v in self.volees if v.numero == numero), None)

    @property
    def cumul(self) -> int:
        """Total des points des volées **validées** (mis à jour à chaque validation, ex-008)."""
        return sum(v.points for v in self.volees if v.verrouillee)

    def compter(self, zone: ZoneScore) -> int:
        """Nombre de flèches d'une zone donnée, sur les volées **validées** seulement.

        Sert au **départage** du classement de qualification (E06US001) : à total égal, on compte
        les 10 puis les 9 (`docs/referentiel-ffta.md` §8.1). On ne compte que les volées validées,
        pour rester cohérent avec `cumul` — le score qu'on départage — : une flèche non validée ne
        pèse ni sur le total ni sur son départage.
        """
        return sum(v.valeurs.count(zone) for v in self.volees if v.verrouillee)

    @property
    def nb_fleches_validees(self) -> int:
        """Nombre de flèches des volées **validées** — la mesure de « l'archer a déjà tiré ».

        « A tiré » = **au moins une volée validée** (arbitrage du 20/07/2026, reversé dans
        `stories/E02-inscriptions.md`), cohérent avec `cumul` et le classement : une volée saisie
        non validée est un état intermédiaire. On compte les **flèches** et non les volées car le
        message énumère « N flèches déjà tirées » — le manqué (`M`) en fait partie.
        """
        return sum(len(v.valeurs) for v in self.volees if v.verrouillee)

    def est_complete(self, nb_volees_bareme: int) -> bool:
        """La série a-t-elle **toutes** les volées du barème, **validées** (E12US005) ?

        « Complète » au sens de la qualification *terminée* : les volées 1..N sont présentes **et
        verrouillées**, aligné sur `cumul` / `nb_fleches_validees` / le classement. Sert à la
        complétude du tournoi. ⚠️ `nb_volees_bareme <= 0` (barème non configuré) → **jamais
        complète** : on ne déclare pas « terminé » ce dont on ignore l'attendu.
        """
        if nb_volees_bareme <= 0:
            return False
        valides = {v.numero for v in self.volees if v.verrouillee}
        return valides == set(range(1, nb_volees_bareme + 1))

    def saisir_volee(
        self,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        *,
        zones_admises: tuple[ZoneScore, ...],
        nb_fleches_par_volee: int,
        nb_volees_bareme: int,
        saisie_par: str | None = None,
    ) -> Serie:
        """Saisit ou réédite (avant validation) la volée `numero`.

        Valide le **rang** (`1 <= numero <= nb_volees_bareme`), le nombre de flèches et les zones :
        le serveur est autoritaire, une volée hors barème gonflerait le cumul. Une volée déjà
        **verrouillée** ne se réécrit pas ici — passer par `corriger_volee`. En réédition, le
        marqueur précédent est gardé si aucun n'est fourni ; vide = « non déclaré » (`None`).
        """
        if not 1 <= numero <= nb_volees_bareme:
            raise NumeroVoleeInvalide(
                f"Le numéro d'une volée est un rang entre 1 et {nb_volees_bareme} (barème)."
            )
        valider_valeurs_volee(valeurs, zones_admises, nb_fleches_par_volee)
        existante = self.volee(numero)
        if existante is not None and existante.verrouillee:
            raise VoleeVerrouillee(
                "Cette volée est validée : seule une correction habilitée peut la modifier."
            )
        marqueur = (
            saisie_par
            if saisie_par is not None
            else (existante.saisie_par if existante is not None else None)
        )
        if marqueur is not None:
            marqueur = marqueur.strip() or None
        volee = Volee(numero=numero, valeurs=valeurs, saisie_par=marqueur)
        return replace(self, volees=_avec_volee(self.volees, volee))

    def valider(
        self,
        par: str,
        *,
        grain: GrainValidation,
        nb_volees_bareme: int,
    ) -> Serie:
        """Verrouille les volées à valider selon le `grain`, au nom de `par` (le scoreur).

        **Fin de série** (et fin de duel) : verrouille tout un bloc, mais seulement quand la série
        est **complète** — sinon `SerieIncomplete`. **Toutes les N volées** : verrouille le
        prochain lot de N non validées ; en fin de barème un **reliquat** de moins de N est validé
        plutôt que laissé ouvert. `RienAValider` si aucun lot complet ni reliquat n'est disponible.
        """
        par = _intervenant_valide(par)
        a_valider = tuple(v for v in self.volees if not v.verrouillee)
        # Complétude **explicite** : les volées 1..N sont toutes présentes. Ne pas se fier au seul
        # `len` : même borné à la saisie, l'ensemble exact est un contrat plus clair.
        serie_complete = {v.numero for v in self.volees} == set(range(1, nb_volees_bareme + 1))
        if grain.type is TypeGrain.TOUTES_LES_N_VOLEES:
            n = grain.n_volees
            assert n is not None  # garanti par GrainValidation.creer
            if len(a_valider) >= n:
                lot = a_valider[:n]
            elif a_valider and serie_complete:
                lot = a_valider  # reliquat de fin de barème
            else:
                raise RienAValider("Aucun lot complet ni reliquat de fin de barème à valider.")
        else:  # FIN_DE_SERIE / FIN_DE_DUEL : validation d'un bloc en fin d'unité
            if not serie_complete:
                raise SerieIncomplete(
                    "La validation de fin de série suppose toutes les volées du barème saisies."
                )
            if not a_valider:
                raise RienAValider("Toutes les volées sont déjà validées.")
            lot = a_valider
        verrouillees = self.volees
        for volee in lot:
            verrouillees = _avec_volee(verrouillees, replace(volee, validee_par=par))
        return replace(self, volees=verrouillees)

    def corriger_volee(
        self,
        numero: int,
        nouvelles_valeurs: tuple[ZoneScore, ...],
        *,
        par: str,
        zones_admises: tuple[ZoneScore, ...],
        nb_fleches_par_volee: int,
    ) -> Serie:
        """Corrige une volée **verrouillée** (chemin habilité, tracé par le service, ex-012).

        La volée reste verrouillée, au nom du correcteur `par` ; le cumul se recalcule mécaniquement
        (il dérive des valeurs). `VoleeIntrouvable` si le numéro n'existe pas, `VoleeNonVerrouillee`
        si la volée n'est pas validée (une volée en cours se modifie par `saisir_volee`).
        """
        par = _intervenant_valide(par)
        existante = self.volee(numero)
        if existante is None:
            raise VoleeIntrouvable(f"Aucune volée numéro {numero} dans cette série.")
        if not existante.verrouillee:
            raise VoleeNonVerrouillee(
                "Seule une volée validée se corrige ; une volée en cours se modifie par saisie."
            )
        valider_valeurs_volee(nouvelles_valeurs, zones_admises, nb_fleches_par_volee)
        corrigee = replace(existante, valeurs=nouvelles_valeurs, validee_par=par)
        return replace(self, volees=_avec_volee(self.volees, corrigee))
