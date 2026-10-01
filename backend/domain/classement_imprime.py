"""Contenu imprimable du classement de qualification — une page par catégorie (E09US005).

Le classement lui-même vient de `calculer_classement` : ce module ne range personne, il découpe
et juge l'état. Voir `stories/E09-exports.md` pour le CA.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from domain.categorie import Categorie, CategorieId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.club import ClubId
from domain.serie import Serie


@dataclass(frozen=True)
class BlocCategorie:
    """Les archers d'une catégorie, dans l'ordre du classement — la page affichée au mur."""

    libelle: str
    lignes: tuple[LigneClassement, ...]


@dataclass(frozen=True)
class SectionClassementQualification:
    """Le classement de qualification d'**un** créneau (ADR-0075), découpé par catégorie."""

    libelle: str
    provisoire: bool
    categories: tuple[BlocCategorie, ...]


@dataclass(frozen=True)
class ClassementQualificationImprime:
    """Le document : une section par créneau, et de quoi nommer les clubs des lignes."""

    tournoi: str
    sections: tuple[SectionClassementQualification, ...]
    clubs: Mapping[ClubId, str]


def blocs_par_categorie(
    classement: Classement, categories: Sequence[Categorie]
) -> tuple[BlocCategorie, ...]:
    """Un bloc par catégorie engagée, dans l'ordre des catégories du tournoi.

    ⚠️ Une ligne dont la catégorie manque à `categories` n'est **pas** perdue : elle forme un bloc
    en fin de document, sous le libellé qu'elle porte. Un archer absent d'une feuille affichée au
    mur se découvre trop tard.
    """
    par_categorie: dict[CategorieId, list[LigneClassement]] = {}
    for ligne in classement.lignes:
        par_categorie.setdefault(ligne.categorie_id, []).append(ligne)
    ordre = [c.id for c in categories if c.id is not None and c.id in par_categorie]
    ordre += [cid for cid in par_categorie if cid not in ordre]
    return tuple(
        BlocCategorie(
            libelle=par_categorie[cid][0].categorie_libelle, lignes=tuple(par_categorie[cid])
        )
        for cid in ordre
    )


def qualification_provisoire(
    classement: Classement, series: Iterable[Serie], nb_volees: int
) -> bool:
    """Un archer **en lice** n'a-t-il pas encore validé toutes les volées du barème ?

    Même notion de série close que la complétude (`ServiceCompletude._serie_close`), où le
    forfait clôt la série : ici, il se lit sur le statut de la ligne. Barème non réglé
    (`nb_volees <= 0`) → provisoire, par `Serie.est_complete`, qui ne déclare rien terminé sans
    attendu. Un créneau sans archer n'attend rien : il n'est pas provisoire.
    """
    par_archer = {serie.archer_id: serie for serie in series}
    return any(
        (serie := par_archer.get(ligne.archer_id)) is None or not serie.est_complete(nb_volees)
        for ligne in classement.lignes
        if ligne.statut is StatutClassement.EN_LICE
    )
