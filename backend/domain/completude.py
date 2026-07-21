"""Complétude d'un tournoi (E12US005) — « qu'est-ce qui manque pour qu'il soit fini ? ».

Politique **pure** (aucune I/O, aucun framework — règle 1) : à partir de décomptes déjà agrégés par
le service (cibles de qualification terminées, archers réglés), elle assemble la réponse affichable,
**le sportif et le tiers comptés séparément** (`D-17`) — ce qui « fige » à *terminé* (le sportif)
n'est pas ce qui reste ouvert (les paiements). Ce n'est **pas** une barre de progression : c'est une
liste d'états, section par section.

Périmètre **séquencé** (arbitrage E12US005, cf. `stories/E12-pilotage-jour-j.md`) : les **phases
éliminatoires** (1/8, 1/4…) n'ont pas encore de moteur (EPIC-05, `TypePhase` ne porte que la
qualification), donc leur ligne est un jalon `À_VENIR` — présente pour dire « pas encore géré »,
sans jamais rendre le sportif éternellement incomplet. Le `sportif_complet` (qui pilote
l'avertissement avant *terminé*) ne dépend donc que de la **qualification** aujourd'hui ; il
s'enrichira quand EPIC-05 livrera les duels. Aucun comportement perdu (règle 9), seulement séquencé
— comme E12US001 pour les écrans de salle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Clés **stables** des lignes (contrat avec le front, qui mappe l'unité d'affichage et le rendu).
# Le libellé lisible voyage aussi dans la ligne, mais la clé est ce sur quoi le front s'appuie.
CLE_QUALIFICATION = "qualification"
CLE_PHASES_ELIMINATOIRES = "phases_eliminatoires"
CLE_CLASSEMENT = "classement"
CLE_PAIEMENTS = "paiements"


class EtatSection(str, Enum):
    """État d'une ligne de complétude — les quatre cas du tableau (`D-18`, CDC UX §8.3).

    - `OK` : terminé (« 30/30 cibles »).
    - `ALERTE` : commencé mais incomplet — le « ! » du tableau (« 144/156 »).
    - `EN_ATTENTE` : rien encore d'exploitable (aucune cible placée ; classement pas prêt).
    - `A_VENIR` : pas encore géré par l'appli (phases éliminatoires, EPIC-05 non livré) — séquencé.
    """

    OK = "ok"
    ALERTE = "alerte"
    EN_ATTENTE = "en_attente"
    A_VENIR = "a_venir"


@dataclass(frozen=True)
class LigneCompletude:
    """Une ligne du tableau : un jalon, son `etat`, et son décompte `fait/total` s'il en a un.

    `fait`/`total` sont `None` pour les lignes **sans décompte** (phases à venir, classement prêt/en
    attente) : leur information est dans `etat`. Le front rend « fait/total <unité> » selon la `cle`
    (« cibles » pour la qualification, rien pour les paiements) — le domaine ne porte pas l'unité
    d'affichage.
    """

    cle: str
    libelle: str
    etat: EtatSection
    fait: int | None = None
    total: int | None = None


@dataclass(frozen=True)
class Completude:
    """Réponse à « qu'est-ce qui manque ? » : les deux sections séparées + le verrou du sportif.

    `sportif_complet` pilote l'**avertissement en amont** du passage à *terminé* (la seule action
    irréversible, E01US002) : à `True`, terminer est un geste net ; à `False`, l'écran chiffre
    ce qui reste avant de laisser confirmer (« Terminer quand même ? »). Il ne couvre **que le
    sportif** :
    les paiements peuvent rester ouverts après *terminé* (`D-17`), ils ne bloquent donc jamais.
    """

    sportif: tuple[LigneCompletude, ...]
    hors_sportif: tuple[LigneCompletude, ...]
    sportif_complet: bool


def evaluer_completude(
    *,
    qualif: tuple[int, int],
    paiements: tuple[int, int],
) -> Completude:
    """Assemble la complétude depuis les décomptes agrégés (politique pure, testée depuis le CA).

    - `qualif` = `(cibles_terminees, cibles_total)` : une cible est *terminée* quand toutes ses
      séries sont complètes (`Serie.est_complete`). Qualification `OK` si toutes le sont (et qu'il y
      en a) ; `EN_ATTENTE` si aucune cible n'est encore placée (`total == 0`) ; `ALERTE` sinon.
    - `paiements` = `(archers_regles, archers_total)` : `OK` si tous réglés (`reste == 0`), `ALERTE`
      sinon. Aucun archer → `OK` **vacant** (rien à encaisser).
    - **classement** : *prêt* (`OK`) dès que la qualification est complète, `EN_ATTENTE` sinon — il
      se recalcule toujours (E06US001), mais n'est *définitif* qu'une fois toutes les séries closes.
    - **phases éliminatoires** : `A_VENIR` (séquencé EPIC-05, cf. module).

    `sportif_complet = qualification OK` (les phases à venir ne bloquent pas — cf. module).
    """
    cibles_terminees, cibles_total = qualif
    regles, total_arch = paiements

    qualif_ok = cibles_total > 0 and cibles_terminees == cibles_total
    if qualif_ok:
        etat_qualif = EtatSection.OK
    elif cibles_total == 0:
        etat_qualif = EtatSection.EN_ATTENTE
    else:
        etat_qualif = EtatSection.ALERTE

    sportif = (
        LigneCompletude(
            cle=CLE_QUALIFICATION,
            libelle="Qualification",
            etat=etat_qualif,
            fait=cibles_terminees,
            total=cibles_total,
        ),
        LigneCompletude(
            cle=CLE_PHASES_ELIMINATOIRES,
            libelle="Phases éliminatoires",
            etat=EtatSection.A_VENIR,
        ),
        LigneCompletude(
            cle=CLE_CLASSEMENT,
            libelle="Classement",
            etat=EtatSection.OK if qualif_ok else EtatSection.EN_ATTENTE,
        ),
    )
    hors_sportif = (
        LigneCompletude(
            cle=CLE_PAIEMENTS,
            libelle="Paiements",
            etat=EtatSection.OK if regles == total_arch else EtatSection.ALERTE,
            fait=regles,
            total=total_arch,
        ),
    )
    return Completude(sportif=sportif, hors_sportif=hors_sportif, sportif_complet=qualif_ok)
