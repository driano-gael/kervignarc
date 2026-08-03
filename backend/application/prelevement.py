"""Qui entre dans une phase — la règle d'ensemencement, **partagée** (E05US020, ADR-0068).

Deux services montent le même tableau à partir du même classement : `ServiceSaisieDuels` (l'arbre
que l'on joue) et `ServicePlacementDuels` (le plan de cibles qui pose les duellistes côte à côte).
Ils doivent ensemencer **exactement** la même population : le premier dit qui affronte qui, le
second où ils tirent. Un écart entre les deux, c'est un archer posté sur une butte sans duel, et
un autre en face du mauvais adversaire — invisible jusqu'au jour J.

Cette règle vivait **recopiée** aux deux endroits, avec un commentaire affirmant leur parité. La
recopie a tenu tant que la règle était « tous les archers en lice » ; elle a lâché à la première
évolution — E05US020 a fait consommer les prélèvements d'un seul côté, et la revue adversariale a
mesuré le résultat : plan de 8 placements pour un tableau de 4. D'où cette extraction, qui n'ajoute
aucune abstraction : une fonction pure, appelée deux fois.

**Pourquoi en couche application et non dans le domaine** : la règle croise un `Classement`
(domaine) et une `Phase` (domaine), mais son *besoin* est celui de deux cas d'usage. La poser dans
`domain/phase.py` obligerait ce module à importer `domain/classement.py`, qui importe déjà
`domain/politiques.py` — on paierait un couplage de modules pour une fonction de quinze lignes.
"""

from __future__ import annotations

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.phase import Phase


def preleves(
    phase: Phase, classement: Classement, ordre_qualification: int | None
) -> list[LigneClassement]:
    """Les archers que **cette phase déclare prélever**, dans l'ordre du classement source.

    C'est ici que le moteur cesse d'ignorer `phase.sources` (cœur de `DETTE-028`). Jusqu'à
    E05US020, le tableau était ensemencé avec **tous** les archers en lice : un format déclarant
    « les rangs 1 à 32 » se jouait à 120 si 120 archers étaient classés, et l'organisateur repartait
    avec un tournoi qui ne suivait pas le schéma qu'il avait composé et validé (E01US024).

    La règle tient en une phrase : **un prélèvement par rangs garde les archers dont le rang scratch
    tombe dans son intervalle**. Les bornes viennent du domaine (`SourcePhase.intervalle`), qui sait
    déjà résoudre une fin ouverte — « les rangs 33 et suivants ». On consomme cette sémantique, on
    ne la réécrit pas.

    ⚠️ **Seules les sources visant la QUALIFICATION sont honorées** (`ordre_qualification`). C'est
    le seul classement lisible ici ; appliquer « les rangs 1 à 8 de la phase 2 » à ce classement
    prendrait les 8 premiers de la **qualification** en croyant prendre ceux du tableau principal —
    un tableau bien formé, plausible, et faux, que rien ne signalerait. Lire le classement d'un
    tableau amont demande la lecture d'E06US004 et créerait un cycle service → service.

    ⚠️ **Deux natures restent inertes** : `le_reste` et `par_issue_de_tour`. Vérifié au cadrage —
    ni l'une ni l'autre n'est résolue nulle part (`effectif_selectionne`, `resoudre` et `intervalle`
    rendent `None`). Leur donner un sens dans un service d'exécution serait décider une règle métier
    au mauvais endroit — l'erreur qu'ADR-0065 §3 a refusé de commettre, que `DETTE-033` acte.

    Une phase **sans source** (ou qui n'en déclare que d'inertes) est alimentée par les
    inscriptions : c'est la première de sa séquence, et c'est le comportement d'avant l'US.
    """
    en_lice = sorted(
        (ligne for ligne in classement.lignes if ligne.statut is StatutClassement.EN_LICE),
        key=lambda ligne: ligne.rang_scratch or 0,
    )
    # L'effectif de la phase source : les archers **classés**. Un disqualifié n'a pas de rang
    # (ADR-0050). ⚠️ Cette borne est aujourd'hui **redondante** avec le classement lui-même — le
    # rang d'une ligne classée ne dépasse jamais le nombre de lignes classées, donc la borne haute
    # d'une fin ouverte ne filtre rien. On la passe quand même parce que c'est l'appel
    # sémantiquement juste : le jour où `intervalle` changera d'écrêtage, le site sera correct sans
    # retouche. *(Un premier jet de l'ADR en faisait un argument central ; la revue adversariale a
    # montré, mutation à l'appui, qu'aucun test ne pouvait le distinguer — parce qu'il n'y a rien à
    # distinguer. L'argument a été retiré plutôt que d'être illustré par un test décoratif.)*
    effectif_source = sum(1 for ligne in classement.lignes if ligne.rang_scratch is not None)
    intervalles = [
        borne
        for source in phase.sources
        if source.ordre_source == ordre_qualification
        if (borne := source.intervalle(effectif_source)) is not None
    ]
    if not intervalles:
        return en_lice
    return [
        ligne
        for ligne in en_lice
        if ligne.rang_scratch is not None
        and any(debut <= ligne.rang_scratch <= fin for debut, fin in intervalles)
    ]
