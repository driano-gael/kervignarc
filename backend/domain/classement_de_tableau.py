"""Le **classement** que produit un tableau — pour qu'une phase aval puisse y prélever (E05US024).

Jusqu'ici, prélever « les rangs 1 à 8 » n'était possible que dans la **qualification** : c'était le
seul classement que le moteur savait lire. Une source visant un tableau amont était **ignorée en
silence**, et la phase recevait *tous* les archers en lice — un tableau bien formé, plausible, et
faux (reste ouvert de `DETTE-028`).

Ce module fournit la pièce qui manquait : lire un `Tableau` **comme un classement**, dans la même
forme que celui d'une qualification, pour que `application/prelevement.py` n'ait pas à savoir de
quel type de phase vient l'ordre qu'il consomme.

**Pourquoi le domaine et non l'application.** La fonction croise un `Tableau`, un `Classement` et
une
politique `Aggregation` — trois notions du domaine, aucune infrastructure, aucun repository. C'est
l'argument exact que `application/prelevement.py` retourne pour `profondeur_de` : ce qui ne touche
que des objets du domaine et n'exprime aucun cas d'usage y descend.

⚠️ **Un tableau ne décerne pas que des rangs exacts.** Les quatre battus des quarts d'un tableau de 8
sortent tous sur la plage `[5..8]` (*Règle R*, ADR-0065) : la compétition ne dit pas lequel est 5ᵉ.
Fermer ces fourchettes est précisément ce que la politique `aggregation` sait faire (ADR-0067), et
c'est elle qu'on appelle — on ne réinvente pas un départage local, qui divergerait du palmarès
affiché au mur le même jour.
"""

from __future__ import annotations

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.participant import GenreParticipant
from domain.politiques import Aggregation
from domain.tableau import Tableau


def classement_de_tableau(
    tableau: Tableau,
    lignes: dict[ArcherId, LigneClassement],
    aggregation: Aggregation,
) -> Classement:
    """Le classement des participants d'un tableau, rangs **fermes** de 1 à N.

    `lignes` porte les lignes de qualification, dont on reprend l'identité (nom, catégorie, club) :
    un classement de tableau n'est pas un objet d'une autre nature, c'est le **même** archer situé
    autrement. Seul `rang_scratch` est réécrit — c'est ce que `preleves` lit.

    **L'ordre.** D'abord la fourchette acquise (`rang_min`, puis `rang_max`) : un finaliste `[1..2]`
    précède un battu des quarts `[5..8]`. Puis, à fourchette égale, la politique `aggregation`
    tranche — sur le rang de qualification par défaut, l'usage World Archery.

    ⚠️ **`en_lice` n'entre pas dans l'ordre, et c'est délibéré.** Deux archers qui vont tirer la
    finale sont `[1..2]` tous les deux : les départager ici sur leur rang de qualification
    décernerait l'or **avant** que la finale ne soit tirée — le défaut exact qu'ADR-0067 a corrigé
    au
    palmarès. On leur donne donc des rangs consécutifs *provisoires*, qui se referment match après
    match ; une phase aval qui prélève « les rangs 1 à 2 » les prend **tous les deux**, ce qui est
    la
    bonne réponse : elle veut les deux finalistes.

    Les participants **équipe** sont écartés (leur `ref_id` n'est pas un archer, ADR-0028), comme le
    palmarès le fait déjà — la résolution viendra avec les équipes elles-mêmes (E13US002).
    """
    acquises = {
        participant.ref_id: position
        for participant, position in tableau.positions_acquises().items()
        if participant.genre is GenreParticipant.INDIVIDUEL
    }
    if not acquises:
        return Classement(lignes=())

    rang_qualification = {
        archer_id: lignes[archer_id].rang_scratch for archer_id in acquises if archer_id in lignes
    }

    # Regrouper par fourchette identique : c'est là — et seulement là — qu'un départage est requis.
    paquets: dict[tuple[int, int], list[ArcherId]] = {}
    for archer_id, position in acquises.items():
        paquets.setdefault((position.rang_min, position.rang_max), []).append(archer_id)

    ordonnes: list[ArcherId] = []
    for fourchette in sorted(paquets):
        groupe = paquets[fourchette]
        if len(groupe) == 1:
            ordonnes.extend(groupe)
            continue
        for sous_groupe in aggregation.departager(groupe, rang_qualification):
            ordonnes.extend(sous_groupe)

    return Classement(
        lignes=tuple(
            _situee(lignes[archer_id], rang)
            for rang, archer_id in enumerate(ordonnes, start=1)
            if archer_id in lignes
        )
    )


def _situee(ligne: LigneClassement, rang: int) -> LigneClassement:
    """La même ligne, resituée au rang que le **tableau** lui a donné.

    `statut` est remis à `EN_LICE` : un archer présent dans le tableau y a sa place, quel que soit
    ce que la qualification disait de lui. Le filtre des sortis a déjà eu lieu — à l'ensemencement
    de ce tableau-ci —, et le rejouer ici retirerait deux fois le même archer.
    """
    from dataclasses import replace

    return replace(ligne, rang_scratch=rang, statut=StatutClassement.EN_LICE)
