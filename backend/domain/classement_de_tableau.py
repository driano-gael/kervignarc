"""Lire un `Tableau` **comme un classement**, pour que l'aval ignore d'où vient l'ordre (ADR-0065).
Fermer les fourchettes est le travail de la politique `aggregation` (ADR-0067) — on ne réinvente pas
un départage local, qui divergerait du palmarès affiché le même jour.

⚠️ **Une fourchette portée par des archers ENCORE EN LICE n'est pas *ex æquo*, elle est indécise** :
des matchs la trancheront. D'où `plages_indecises`, qui permet de refuser une fenêtre qui la
**coupe** au lieu de rendre une population plausible et fausse (ADR-0081).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.participant import GenreParticipant
from domain.politiques import Aggregation
from domain.tableau import Tableau


@dataclass(frozen=True)
class ClassementSource:
    """Le classement d'une phase source, **et ce qu'il a d'encore indécis** (E05US024, ADR-0081).

    `plages_indecises` énumère les blocs de rangs — bornes **incluses** — que la compétition n'a
    pas tranchés ; l'appelant s'en sert pour décider s'il peut honorer une fenêtre (cf. `coupe`).
    `rang_premier` est le **rang de tournoi** du rang 1 de ce classement, qui permet à
    `prelevement.tranche` de **cumuler** le décalage le long d'une chaîne. ⚠️ **Il est posé par
    l'appelant** : un tableau ne sait pas quelle tranche du tournoi il dispute (`DETTE-034`).
    """

    classement: Classement
    plages_indecises: tuple[tuple[int, int], ...] = ()
    rang_premier: int = 1

    def coupe(self, debut: int, fin: int) -> tuple[int, int] | None:
        """La première plage indécise que la fenêtre `[debut..fin]` **coupe**, ou `None`.

        « Couper », c'est chevaucher **sans contenir** — toute la distinction d'ADR-0081. Fenêtre
        `[1..2]` sur les deux finalistes `[1..2]` : elle **contient**, on les prend tous les deux.
        Fenêtre `[5..8]` sur un tableau de 8 non commencé, où les huit partagent `[1..8]` : elle
        **coupe**, et la consolante recevrait les 4 derniers qualifiés au lieu des battus.
        """
        for debut_plage, fin_plage in self.plages_indecises:
            chevauche = debut <= fin_plage and debut_plage <= fin
            contient = debut <= debut_plage and fin_plage <= fin
            if chevauche and not contient:
                return (debut_plage, fin_plage)
        return None


def classement_de_tableau(
    tableau: Tableau,
    lignes: Mapping[ArcherId, LigneClassement],
    aggregation: Aggregation,
) -> ClassementSource:
    """Le classement des participants d'un tableau, rangs **fermes** de 1 à N.

    On reprend l'identité des lignes de qualification — c'est le **même** archer situé autrement —
    et seul `rang_scratch` est réécrit. L'ordre : fourchette acquise (`rang_min`, `rang_max`), puis
    la politique `aggregation`. ⚠️ **`en_lice` n'entre pas dans l'ordre** : départager deux
    finalistes sur leur rang de qualification décernerait l'or **avant** la finale (ADR-0067) —
    leurs rangs provisoires ne valent qu'**en bloc**, d'où `plages_indecises`. Équipes écartées.
    """
    acquises = {
        participant.ref_id: position
        for participant, position in tableau.positions_acquises().items()
        if participant.genre is GenreParticipant.INDIVIDUEL
    }
    if not acquises:
        return ClassementSource(classement=Classement(lignes=()))

    rang_qualification = {
        archer_id: lignes[archer_id].rang_scratch for archer_id in acquises if archer_id in lignes
    }

    # Regrouper par fourchette identique : c'est là — et seulement là — qu'un départage est requis.
    paquets: dict[tuple[int, int], list[ArcherId]] = {}
    for archer_id, position in acquises.items():
        paquets.setdefault((position.rang_min, position.rang_max), []).append(archer_id)
    # Une fourchette est **indécise** dès qu'**un** de ses porteurs est encore en lice : ce sont
    # les matchs à venir qui la trancheront, pas une politique. On ne suppose **pas** que `en_lice`
    # soit homogène au sein d'un paquet — il ne l'est pas toujours (un battu déjà routé vers un
    # match de placement et un battu qui ne l'est pas peuvent partager la même fourchette). Le sens
    # retenu est le **conservateur** : marquer indécis au moindre doute produit au pire un refus,
    # jamais une population fausse. Un premier commentaire annonçait « on lit le premier venu »,
    # ce que le code ne fait pas — et s'y fier aurait invité à « simplifier » vers un vrai premier.
    en_lice = {
        (position.rang_min, position.rang_max) for position in acquises.values() if position.en_lice
    }

    ordonnes: list[ArcherId] = []
    indecises: list[tuple[int, int]] = []
    for fourchette in sorted(paquets):
        groupe = paquets[fourchette]
        # Le rang qu'occupera ce paquet dans le classement rendu — **après** le filtre des archers
        # sans ligne, sans quoi les bornes désigneraient des rangs qui n'existent pas.
        retenus = [archer_id for archer_id in groupe if archer_id in lignes]
        if retenus and fourchette in en_lice:
            indecises.append((len(ordonnes) + 1, len(ordonnes) + len(retenus)))
        if len(groupe) == 1:
            ordonnes.extend(retenus)
            continue
        departages = [
            archer_id
            for sous_groupe in aggregation.departager(groupe, rang_qualification)
            for archer_id in sous_groupe
        ]
        ordonnes.extend(archer_id for archer_id in departages if archer_id in lignes)

    return ClassementSource(
        classement=Classement(
            lignes=tuple(
                situee_au_rang(lignes[archer_id], rang)
                for rang, archer_id in enumerate(ordonnes, start=1)
            )
        ),
        plages_indecises=tuple(indecises),
    )


def situee_au_rang(ligne: LigneClassement, rang: int) -> LigneClassement:
    """La même ligne, resituée au rang que la **phase** lui a donné.

    `statut` est remis à `EN_LICE` : un archer présent dans la phase y a sa place, le filtre des
    sortis ayant déjà eu lieu à l'ensemencement — le rejouer retirerait deux fois le même archer.
    ⚠️ **Publique depuis E05US023** : `domain/classement_de_poules.py` situe ses lignes par la
    **même** règle, et la recopier aurait dupliqué un invariant.
    """

    # DETTE-051 : un forfait déclaré **dans ce tableau-ci** (walkover, ADR-0050) garde sa position
    # acquise et ressort donc `EN_LICE` ici, donc prélevable par une phase aval. C'est une **règle
    # métier** à trancher avec le club, pas un correctif de revue — cf. docs/dette.md.
    return replace(ligne, rang_scratch=rang, statut=StatutClassement.EN_LICE)
