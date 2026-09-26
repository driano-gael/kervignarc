"""Import d'un fichier d'inscrits (E02US007) — la décision ligne à ligne, sans rien écrire.

Le fichier est **déjà lu** (adapters `infrastructure/import_inscrits/`) ; ce module décide, sur un
instantané du tournoi, ce que devient chaque ligne. Le même plan sert l'aperçu et la confirmation :
ce que l'admin a vu est ce qui s'écrit. Raisonnement : ADR-0115.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.archer import Archer, ArcherId, cle_identite, normaliser_licence, sont_homonymes
from domain.categorie import Categorie, CategorieId, SexeCategorie, TrancheAge
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.erreurs import DomainError
from domain.inscription import Inscription


class SourceImport(str, Enum):
    IANSEO = "ianseo"
    RESULTARC = "resultarc"


@dataclass(frozen=True)
class LigneFichier:
    """Une ligne lue. Résult'Arc ne porte ni nom, ni prénom, ni sexe, ni naissance, ni club.

    `anomalie` : la ligne n'a pas pu être lue (date illisible, colonnes manquantes) — elle sera
    rejetée avec ce motif plutôt que de faire échouer le fichier entier.
    """

    numero: int
    licence: str | None
    depart_numero: int | None
    nom: str | None = None
    prenom: str | None = None
    sexe: SexeCategorie | None = None
    date_naissance: datetime.date | None = None
    club: str | None = None
    arme: str | None = None
    anomalie: str | None = None


@dataclass(frozen=True)
class FichierInscrits:
    source: SourceImport
    lignes: tuple[LigneFichier, ...]
    colonnes_ignorees: tuple[str, ...] = ()
    """Colonnes lues mais non reprises (arbitrage 5 : paiement, cible, trispot de Résult'Arc)."""


@dataclass(frozen=True)
class InstantaneDuTournoi:
    """Ce que le plan doit voir du tournoi. `clubs` est le référentiel **global** (E02US001)."""

    date_tournoi: datetime.date
    categories: tuple[Categorie, ...]
    departs: tuple[Depart, ...]
    archers: tuple[Archer, ...]
    clubs: tuple[Club, ...]
    inscriptions: tuple[Inscription, ...]


class Decision(str, Enum):
    CREER = "creer"
    """Nouvelle fiche, inscrite sur le départ de la ligne."""
    INSCRIRE = "inscrire"
    """Fiche déjà désignée par la licence (en base, ou créée plus haut dans le fichier)."""
    HOMONYME = "homonyme"
    """Même identité qu'un inscrit, sans licence qui les départage : l'admin tranche (ADR-0015)."""
    REJETEE = "rejetee"


@dataclass(frozen=True)
class LignePlan:
    """La décision sur une ligne. Une INSCRIRE désigne sa fiche par `archer_id` (en base) **ou** par
    `fiche_de_la_ligne` (créée par cette ligne du même fichier) — jamais les deux."""

    ligne: LigneFichier
    decision: Decision
    motif: str | None = None
    depart_id: DepartId | None = None
    categorie_id: CategorieId | None = None
    club_id: ClubId | None = None
    club_a_creer: str | None = None
    archer_id: ArcherId | None = None
    fiche_de_la_ligne: int | None = None
    homonyme_de: str | None = None
    licence: str | None = None
    fiche: str | None = None
    """INSCRIRE : l'identité de la fiche que la licence désigne — le fichier peut dire autre chose,
    et Résult'Arc ne dit rien (revue d'E02US007, axe D)."""


@dataclass(frozen=True)
class PlanImport:
    source: SourceImport
    lignes: tuple[LignePlan, ...]
    colonnes_ignorees: tuple[str, ...] = ()

    @property
    def importables(self) -> tuple[LignePlan, ...]:
        return tuple(ligne for ligne in self.lignes if ligne.decision in _ECRITES)

    @property
    def rejetees(self) -> tuple[LignePlan, ...]:
        return tuple(ligne for ligne in self.lignes if ligne.decision is Decision.REJETEE)

    @property
    def homonymes(self) -> tuple[LignePlan, ...]:
        return tuple(ligne for ligne in self.lignes if ligne.decision is Decision.HOMONYME)


_ECRITES = (Decision.CREER, Decision.INSCRIRE)

_Identite = tuple[str, str, ClubId | str | None]
"""`CleIdentite`, étendue au club pas encore créé (désigné par son nom replié)."""

_BORNES_D_AGE: tuple[tuple[int, TrancheAge], ...] = (
    (10, TrancheAge.U11),
    (12, TrancheAge.U13),
    (14, TrancheAge.U15),
    (17, TrancheAge.U18),
    (20, TrancheAge.U21),
    (39, TrancheAge.S1),
    (59, TrancheAge.S2),
)
"""Âge maximal de chaque tranche — `docs/referentiel-ffta.md` §2 (art. C.3.1). Au-delà : S3."""

MOIS_DEBUT_DE_SAISON = 9


def tranche_age(date_naissance: datetime.date, date_tournoi: datetime.date) -> TrancheAge:
    """Tranche FFTA : âge atteint dans l'année civile de **fin** de saison (01/09 → 31/08).

    ⚠️ Lecture de « l'année civile de la licence » : la licence porte le millésime de fin de
    saison (ADR-0115 le trace comme une interprétation).
    """
    annee_de_licence = date_tournoi.year + (1 if date_tournoi.month >= MOIS_DEBUT_DE_SAISON else 0)
    age = annee_de_licence - date_naissance.year
    for age_maximal, tranche in _BORNES_D_AGE:
        if age <= age_maximal:
            return tranche
    return TrancheAge.S3


def planifier_import(
    fichier: FichierInscrits,
    etat: InstantaneDuTournoi,
    homonymes_acceptes: frozenset[int] = frozenset(),
) -> PlanImport:
    """Décide de chaque ligne, dans l'ordre du fichier. `homonymes_acceptes` : n° de lignes cochés.

    L'ordre compte : une ligne voit les fiches créées et les places prises par les précédentes.
    """
    planificateur = _Planificateur(fichier.source, etat, homonymes_acceptes)
    return PlanImport(
        source=fichier.source,
        lignes=tuple(planificateur.decider(ligne) for ligne in fichier.lignes),
        colonnes_ignorees=fichier.colonnes_ignorees,
    )


class _Planificateur:
    def __init__(
        self,
        source: SourceImport,
        etat: InstantaneDuTournoi,
        homonymes_acceptes: frozenset[int],
    ) -> None:
        self._source = source
        self._etat = etat
        self._homonymes_acceptes = homonymes_acceptes
        self._departs = {depart.numero: depart for depart in etat.departs}
        self._clubs = {cle_nom(club.nom): club for club in etat.clubs}
        self._archers_par_licence = {a.licence: a for a in etat.archers if a.licence is not None}
        self._inscrits_par_depart: dict[DepartId, int] = {}
        self._couples: set[tuple[ArcherId | str, DepartId]] = set()
        for inscription in etat.inscriptions:
            self._compter(inscription.archer_id, inscription.depart_id)
        # Fiches créées par le fichier : licence → (n° de la ligne créatrice, identité).
        self._fiches_du_fichier: dict[str, tuple[int, str]] = {}
        self._identites_du_fichier: list[tuple[_Identite, str | None]] = []

    def decider(self, ligne: LigneFichier) -> LignePlan:
        try:
            return self._decider(ligne)
        except _Rejet as rejet:
            return LignePlan(ligne=ligne, decision=Decision.REJETEE, motif=str(rejet))
        except DomainError as erreur:
            return LignePlan(ligne=ligne, decision=Decision.REJETEE, motif=str(erreur))

    def _decider(self, ligne: LigneFichier) -> LignePlan:
        if ligne.anomalie is not None:
            raise _Rejet(f"Ligne illisible : {ligne.anomalie}.")
        depart = self._depart(ligne)
        licence = normaliser_licence(ligne.licence)
        if licence is not None:
            existante = self._inscrire_fiche_connue(ligne, licence, depart)
            if existante is not None:
                return existante
        if self._source is SourceImport.RESULTARC:
            raise _Rejet(
                "Licence inconnue du tournoi. Un fichier Résult'Arc ne porte pas le nom de "
                "l'archer : importez d'abord l'export Ianseo, qui crée les fiches."
                if licence is not None
                else "Ligne sans n° de licence : impossible de désigner l'archer."
            )
        return self._creer(ligne, licence, depart)

    def _depart(self, ligne: LigneFichier) -> Depart:
        if ligne.depart_numero is None:
            raise _Rejet("Aucun n° de départ sur la ligne.")
        depart = self._departs.get(ligne.depart_numero)
        if depart is None:
            raise _Rejet(
                f"Le départ n° {ligne.depart_numero} n'existe pas dans ce tournoi : créez-le "
                "d'abord (un départ exige un horaire et un tarif, que le fichier ne porte pas)."
            )
        return depart

    def _inscrire_fiche_connue(
        self, ligne: LigneFichier, licence: str, depart: Depart
    ) -> LignePlan | None:
        """La licence désigne-t-elle déjà une fiche ? Alors on l'inscrit, on n'en crée pas."""
        archer = self._archers_par_licence.get(licence)
        creee = self._fiches_du_fichier.get(licence)
        if archer is None and creee is None:
            return None
        cle: ArcherId | str = archer.id if archer is not None and archer.id is not None else licence
        fiche = (
            f"{archer.prenom} {archer.nom}" if archer is not None else creee[1] if creee else None
        )
        assert depart.id is not None
        if (cle, depart.id) in self._couples:
            raise _Rejet(
                f"La licence {licence} est déjà inscrite sur le départ n° {depart.numero}."
            )
        self._reserver_une_place(depart)
        self._compter(cle, depart.id)
        return LignePlan(
            ligne=ligne,
            decision=Decision.INSCRIRE,
            depart_id=depart.id,
            archer_id=archer.id if archer is not None else None,
            fiche_de_la_ligne=creee[0] if archer is None and creee is not None else None,
            licence=licence,
            fiche=fiche,
        )

    def _creer(self, ligne: LigneFichier, licence: str | None, depart: Depart) -> LignePlan:
        nom, prenom = (ligne.nom or "").strip(), (ligne.prenom or "").strip()
        if not nom or not prenom:
            raise _Rejet("Nom ou prénom absent.")
        categorie = self._categorie(ligne)
        club_id, club_a_creer = self._club(ligne.club)
        homonyme_de = self._homonyme(nom, prenom, club_id, club_a_creer, licence)
        if homonyme_de is not None and ligne.numero not in self._homonymes_acceptes:
            return LignePlan(
                ligne=ligne,
                decision=Decision.HOMONYME,
                depart_id=depart.id,
                categorie_id=categorie.id,
                club_id=club_id,
                club_a_creer=club_a_creer,
                homonyme_de=homonyme_de,
                licence=licence,
            )
        assert depart.id is not None
        self._reserver_une_place(depart)
        cle: ArcherId | str = licence if licence is not None else f"ligne-{ligne.numero}"
        self._compter(cle, depart.id)
        if licence is not None:
            self._fiches_du_fichier[licence] = (ligne.numero, f"{prenom} {nom}")
        self._identites_du_fichier.append((_identite(nom, prenom, club_id, club_a_creer), licence))
        return LignePlan(
            ligne=ligne,
            decision=Decision.CREER,
            depart_id=depart.id,
            categorie_id=categorie.id,
            club_id=club_id,
            club_a_creer=club_a_creer,
            homonyme_de=homonyme_de,
            licence=licence,
        )

    def _categorie(self, ligne: LigneFichier) -> Categorie:
        if ligne.date_naissance is not None and ligne.date_naissance > self._etat.date_tournoi:
            raise _Rejet(f"Date de naissance postérieure au tournoi ({ligne.date_naissance}).")
        tranche = (
            tranche_age(ligne.date_naissance, self._etat.date_tournoi)
            if ligne.date_naissance is not None
            else None
        )
        candidates = [
            categorie
            for categorie in self._etat.categories
            if _accepte(categorie, ligne.sexe, tranche, ligne.arme)
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise _Rejet(
                "Aucune catégorie du tournoi ne correspond (sexe "
                f"{_ou_inconnu(ligne.sexe.value if ligne.sexe else None)}, âge "
                f"{_ou_inconnu(tranche.value if tranche else None)}, arme "
                f"{ligne.arme or 'tous arcs'})."
            )
        noms = ", ".join(sorted(categorie.libelle for categorie in candidates))
        raise _Rejet(f"Plusieurs catégories possibles ({noms}) : impossible de choisir.")

    def _club(self, nom: str | None) -> tuple[ClubId | None, str | None]:
        if nom is None or not nom.strip():
            return None, None
        club = self._clubs.get(cle_nom(nom))
        if club is not None:
            return club.id, None
        return None, nom.strip()

    def _homonyme(
        self,
        nom: str,
        prenom: str,
        club_id: ClubId | None,
        club_a_creer: str | None,
        licence: str | None,
    ) -> str | None:
        if club_a_creer is None:
            cle = cle_identite(nom, prenom, club_id)
            for archer in self._etat.archers:
                if sont_homonymes(archer.cle_identite(), archer.licence, cle, licence):
                    return f"{archer.prenom} {archer.nom}"
        identite = _identite(nom, prenom, club_id, club_a_creer)
        for autre, autre_licence in self._identites_du_fichier:
            if sont_homonymes(autre, autre_licence, identite, licence):
                return f"{prenom} {nom} (plus haut dans le fichier)"
        return None

    def _reserver_une_place(self, depart: Depart) -> None:
        assert depart.id is not None
        if depart.est_complet(self._inscrits_par_depart.get(depart.id, 0)):
            raise _Rejet(f"Le départ n° {depart.numero} est complet ({depart.quota} places).")

    def _compter(self, cle: ArcherId | str, depart_id: DepartId) -> None:
        self._couples.add((cle, depart_id))
        self._inscrits_par_depart[depart_id] = self._inscrits_par_depart.get(depart_id, 0) + 1


class _Rejet(Exception):
    """Motif de rejet d'une ligne : interne au plan, jamais levé hors de ce module."""


def _accepte(
    categorie: Categorie,
    sexe: SexeCategorie | None,
    tranche: TrancheAge | None,
    arme: str | None,
) -> bool:
    """Une contrainte absente de la catégorie accepte tout ; présente, elle exige la donnée — sauf
    l'arme : `None` y vaut « tous arcs » (arbitrage du 26/09/2026), qui ne contraint rien."""
    sexe_exige = categorie.sexe is not None and categorie.sexe is not SexeCategorie.MIXTE
    if sexe_exige and sexe is not categorie.sexe:
        return False
    if categorie.ages and (tranche is None or tranche not in categorie.ages):
        return False
    return categorie.arme is None or arme is None or cle_nom(arme) == cle_nom(categorie.arme)


def _identite(nom: str, prenom: str, club_id: ClubId | None, club_a_creer: str | None) -> _Identite:
    club: ClubId | str | None = cle_nom(club_a_creer) if club_a_creer is not None else club_id
    return (cle_nom(nom), cle_nom(prenom), club)


def _ou_inconnu(valeur: str | None) -> str:
    return valeur if valeur else "inconnu"
