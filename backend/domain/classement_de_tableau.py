"""Le **classement** que produit un tableau — pour qu'une phase aval puisse y prélever (E05US024).

Jusqu'ici, prélever « les rangs 1 à 8 » n'était possible que dans la **qualification** : c'était le
seul classement que le moteur savait lire. Une source visant un tableau amont était **ignorée en
silence**, et la phase recevait *tous* les archers en lice — un tableau bien formé, plausible, et
faux (reste ouvert de `DETTE-028`).

Ce module fournit la pièce qui manquait : lire un `Tableau` **comme un classement**, dans la même
forme que celui d'une qualification, pour que `application/prelevement.py` n'ait pas à savoir de
quel type de phase vient l'ordre qu'il consomme.

**Pourquoi le domaine et non l'application.** La fonction croise un `Tableau`, un `Classement`
et une politique `Aggregation` — trois notions du domaine, aucune infrastructure, aucun
repository. C'est l'argument exact que `application/prelevement.py` retourne pour `profondeur_de` :
ce qui ne
touche que des objets du domaine et n'exprime aucun cas d'usage y descend.

⚠️ **Un tableau ne décerne pas que des rangs exacts.** Les quatre battus des quarts d'un tableau de 8
sortent tous sur la plage `[5..8]` (*Règle R*, ADR-0065) : la compétition ne dit pas lequel est 5ᵉ.
Fermer ces fourchettes est précisément ce que la politique `aggregation` sait faire (ADR-0067), et
c'est elle qu'on appelle — on ne réinvente pas un départage local, qui divergerait du palmarès
affiché au mur le même jour.

⚠️ **Toutes les fourchettes ne se valent pas, et c'est ce que ce module rend explicite** (ADR-0081,
correctif de revue adversariale). Une fourchette portée par des archers **encore en lice** n'est pas
*ex æquo* : elle est **indécise** — des matchs restent à tirer qui la trancheront. Le classement
rendu leur donne des rangs *provisoires*, et c'est légitime tant que l'aval les prend **en bloc** ;
ça ne l'est plus dès qu'une fenêtre **coupe** le bloc. `ClassementSource.plages_indecises` porte
donc
l'information dont l'appelant a besoin pour refuser une fenêtre à laquelle la compétition n'a pas
encore répondu, au lieu de rendre une population plausible et fausse.
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

    `plages_indecises` énumère les blocs de rangs — bornes **incluses**, dans l'espace de rangs de
    ce classement — que la compétition n'a pas encore tranchés. Un classement de qualification n'en
    a aucun ; un tableau en cours en a autant que de fourchettes portées par des archers en lice.

    L'appelant s'en sert pour décider s'il peut honorer une fenêtre de prélèvement : voir `coupe`.

    `rang_premier` est le **rang de tournoi** qu'occupe le rang 1 de ce classement. Il vaut 1 pour
    une qualification ; il vaut 33 pour un tableau qui disputait les places 33 et suivantes. C'est
    lui qui permet à `application/prelevement.py:tranche` de **cumuler** le décalage le long d'une
    chaîne, au lieu de croire que les rangs locaux le portent déjà (ADR-0081).

    ⚠️ **Il est posé par l'appelant, pas par `classement_de_tableau`** (correctif de revue, axe C2) :
    un tableau ne sait pas quelle tranche du tournoi il dispute — c'est une propriété de sa place
    dans le déroulé, que seul le service qui remonte la chaîne connaît. Le faire traverser la
    fonction du domaine en paramètre lui donnait une valeur qu'elle ne pouvait pas vérifier, avec un
    défaut à `1` qu'un appelant distrait aurait réintroduit en silence — c'est-à-dire `DETTE-034`
    rouverte, le défaut même que ce champ ferme.
    """

    classement: Classement
    plages_indecises: tuple[tuple[int, int], ...] = ()
    rang_premier: int = 1

    def coupe(self, debut: int, fin: int) -> tuple[int, int] | None:
        """La première plage indécise que la fenêtre `[debut..fin]` **coupe**, ou `None`.

        « Couper », c'est chevaucher **sans contenir**. La distinction est tout l'objet d'ADR-0081,
        et elle sauve le raisonnement d'ADR-0080 §2 au lieu de le jeter :

        - fenêtre `[1..2]` sur les deux finalistes `[1..2]` → **contient** : on les prend tous les
          deux, ce qui est la bonne réponse (elle veut les deux finalistes, pas le champion) ;
        - fenêtre `[5..8]` sur un tableau de 8 **non commencé**, où les huit archers partagent
          la plage `[1..8]` de leur quart en cours → **coupe** : désigner « les rangs 5 à 8 » y
          reviendrait à trancher sur le rang de qualification quatre places que les quarts n'ont
          pas encore attribuées. La consolante recevrait les 4 derniers qualifiés, pas les battus.
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

    ⚠️ **Mais ces rangs provisoires ne valent qu'en bloc** (ADR-0081). Ils sont rendus tels quels —
    le palmarès en a besoin pour situer tout le monde à chaque instant —, et les blocs concernés
    sont
    **signalés** dans `ClassementSource.plages_indecises` pour que `preleves` puisse refuser une
    fenêtre qui les couperait. Sans ce signalement, un tableau de 8 non commencé livrait ses
    « rangs 5 à 8 » comme étant les 4 derniers **qualifiés** : bien formé, plausible, et faux.

    Les participants **équipe** sont écartés (leur `ref_id` n'est pas un archer, ADR-0028), comme le
    palmarès le fait déjà — la résolution viendra avec les équipes elles-mêmes (E13US002).
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

    `statut` est remis à `EN_LICE` : un archer présent dans la phase y a sa place, quel que soit
    ce que la qualification disait de lui. Le filtre des sortis a déjà eu lieu — à l'ensemencement
    de cette phase-ci —, et le rejouer ici retirerait deux fois le même archer.

    ⚠️ **Publique et non plus privée depuis E05US023** : `domain/classement_de_poules.py` situe ses
    lignes par la **même** règle. La recopier là-bas aurait dupliqué un invariant — et la note
    `DETTE-051` ci-dessous avec lui, qui aurait alors décrit deux codes au lieu d'un.
    """
    # DETTE-051 : un forfait déclaré **dans ce tableau-ci** (walkover, ADR-0050) garde sa position
    # acquise et ressort donc `EN_LICE` ici, donc prélevable par une phase aval. Un archer qui a
    # abandonné en 1/8 peut ainsi être ensemencé dans la consolante. Relevé en revue (axe B) ;
    # c'est une **règle métier** à trancher avec le club, pas un correctif de revue — cf.
    # docs/dette.md.
    return replace(ligne, rang_scratch=rang, statut=StatutClassement.EN_LICE)
