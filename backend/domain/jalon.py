"""Les **jalons « prêt à… »** (E16US012) — « puis-je passer à l'étape suivante, et sinon quoi ? ».

Politique **pure** (aucune I/O, aucun framework — règle 1). Elle donne à quatre écrans une **forme
unique paramétrée** par le jalon, plutôt que quatre écrans jumeaux qui divergeraient : c'est
l'arbitrage du commanditaire du 23/08/2026, et la raison pour laquelle cette US devait être
instruite **avant** `E16US007` (exports) et `E16US008` (feu vert), qui allaient chacune figer sa
propre variante (ADR-0096).

**Ce que l'US corrige.** Les gardes du cycle de vie existent déjà, mais elles ne sont lisibles
**qu'en échouant** : `ServiceTournois.vers_pret` lève `TournoiSansDepart`, `demarrer` lève
`EffectifInsuffisantPourDemarrer`. Une exception ne rend que le **premier** manquement rencontré —
l'organisateur règle les créneaux, reclique, et découvre alors l'effectif. Un jalon **énumère** ce
que les gardes vérifient, sans les exécuter.

**Ce que la forme unique paramètre, et ce qu'elle ne fusionne pas.** Elle unifie la *réponse*
(`PreparationJalon`) et la *question* (`question`), pas les *règles* : chaque membre a ses propres
entrées, donc sa propre politique. Fusionner les règles dans une fonction unique aurait demandé
l'union de toutes leurs entrées — et aurait reconstruit, à l'intérieur, les quatre variantes qu'on
cherche à éviter.

**`pret` n'est pas « toutes les lignes vertes ».** Une ligne dit *ce qui manque* ; `pret` dit *si
l'action passera*. Les deux se séparent parce que `D-15` (« l'appli n'empêche pas, elle avertit »)
autorise des manquements qui ne bloquent pas — un tournoi sans déroulé composé démarre. Les
confondre ferait dire à l'écran « vous ne pouvez pas » là où le serveur accepte.

**`bloquant` porte l'asymétrie de la famille.** *Démarrer* a des gardes dures ; *terminer* n'en a
aucune (`sportif_complet` choisit le libellé de la confirmation, il ne garde rien — E12US005). Sans
ce drapeau, la forme unique dirait la même chose des deux, donc serait fausse sur l'un des deux.

Les lignes réutilisent `LigneCompletude` / `EtatSection` de `domain.completude` : c'est déjà le
vocabulaire de `D-17` / `D-18` (liste d'états, jamais une barre de progression), et le jalon
*terminer* **est** la complétude sportive — la relire plutôt que la réécrire est le CA « sans
doublonner ce qui existe ».
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.completude import Completude, EtatSection, LigneCompletude

# Clés **stables** des lignes de « prêt à démarrer » (contrat avec le front, comme celles de la
# complétude). Le libellé lisible voyage dans la ligne ; la clé est ce sur quoi le front s'appuie.
CLE_CRENEAUX = "creneaux"
CLE_EFFECTIF = "effectif"
CLE_DEROULE = "deroule"


class Jalon(str, Enum):
    """Les quatre membres de la famille (CA E16US012).

    Ils ne sont **pas** tous de même nature, et l'ADR le tranche : `DEMARRER`, `TERMINER` et
    `ARCHIVER` gardent une **transition** du cycle de vie ([ADR-0026] §2) ; `EXPORTER` garde un
    **geste répétable**, qui ne fait franchir aucun statut. Ce qu'ils partagent n'est donc pas la
    machine à états — c'est la question posée à l'organisateur.
    """

    DEMARRER = "demarrer"
    TERMINER = "terminer"
    ARCHIVER = "archiver"
    EXPORTER = "exporter"


# Le verbe de chaque jalon, seule part variable de la question. La phrase, elle, est commune : c'est
# ce qui fait une **famille** plutôt que quatre écrans qui se ressemblent.
_VERBE: dict[Jalon, str] = {
    Jalon.DEMARRER: "démarrer",
    Jalon.TERMINER: "terminer",
    Jalon.ARCHIVER: "archiver",
    Jalon.EXPORTER: "exporter",
}


def question(jalon: Jalon) -> str:
    """La question posée par l'écran — « Prêt à démarrer ? ».

    Dérivée du jalon, jamais rédigée écran par écran : c'est ce qui garantit qu'un membre ajouté
    plus tard (`ARCHIVER`, `EXPORTER`) parle exactement comme les deux premiers. Le libellé
    « Prêt à terminer ? » d'E16US003 est repris **à l'identique** — l'écran existant ne change pas
    de nom en migrant sur la famille.
    """
    return f"Prêt à {_VERBE[jalon]} ?"


@dataclass(frozen=True)
class PreparationJalon:
    """La réponse d'un jalon : ce qui manque, et si l'action passera.

    - `lignes` : *ce qui manque*, en états (`D-17`) — jamais un pourcentage ;
    - `pret` : la réponse **binaire** à « puis-je passer à l'étape suivante ? » ;
    - `bloquant` : à `False`, l'action passe **quand même** malgré `pret is False` (`D-15`).

    ⚠️ **Aucun bouton n'est jamais désactivé sur la foi de ces champs.** E05US021 avait déjà tranché
    ce point pour le démarrage : l'avertissement se lit avant le clic, le refus remonte du serveur.
    Un front qui grise le bouton se met à décider d'une garde — et devient la seconde source que le
    CA interdit.
    """

    jalon: Jalon
    lignes: tuple[LigneCompletude, ...]
    pret: bool
    bloquant: bool


def evaluer_demarrer(
    *,
    nb_creneaux: int,
    nb_etapes_deroule: int,
    inscrits: int,
    minimum: int,
) -> PreparationJalon:
    """« Prêt à démarrer ? » — les deux gardes du feu vert, plus un avertissement qui ne bloque pas.

    - **Créneaux** (`nb_creneaux`) : garde de `vers_pret` (E02US010) — sans départ, pas de feu
      vert. `EN_ATTENTE` plutôt qu'`ALERTE` : rien n'est commencé, il n'y a pas d'écart à chiffrer.
    - **Inscrits** (`inscrits` / `minimum`) : garde de `demarrer` (E05US021), chiffrée « 28/34 ».
      `minimum == 0` signifie *rien n'est prélevé, donc rien n'est exigé* — la ligne est alors `OK`
      et ne s'alarme pas sur un plancher qui n'existe pas.
    - **Déroulé composé** (`nb_etapes_deroule`) : **avertissement seul**. Le service laisse démarrer
      un tournoi sans déroulé ; le dire bloquant ferait mentir l'écran. Que ce soit *souhaitable*
      est une autre question — elle est ouverte à l'ADR, pas tranchée ici.

    `pret` ne retient donc que les deux gardes dures. `bloquant` est `True` : le serveur refuse
    réellement, et l'écran doit annoncer un refus, pas une simple gêne.
    """
    etat_creneaux = EtatSection.OK if nb_creneaux > 0 else EtatSection.EN_ATTENTE
    effectif_ok = minimum == 0 or inscrits >= minimum
    etat_effectif = EtatSection.OK if effectif_ok else EtatSection.ALERTE
    etat_deroule = EtatSection.OK if nb_etapes_deroule > 0 else EtatSection.EN_ATTENTE

    lignes = (
        LigneCompletude(cle=CLE_CRENEAUX, libelle="Créneaux", etat=etat_creneaux),
        LigneCompletude(
            cle=CLE_EFFECTIF,
            libelle="Inscrits",
            etat=etat_effectif,
            # Sans exigence, le décompte n'a rien à comparer : on ne rend pas « 12/0 ».
            fait=None if minimum == 0 else inscrits,
            total=None if minimum == 0 else minimum,
        ),
        LigneCompletude(cle=CLE_DEROULE, libelle="Déroulé composé", etat=etat_deroule),
    )
    return PreparationJalon(
        jalon=Jalon.DEMARRER,
        lignes=lignes,
        pret=etat_creneaux is EtatSection.OK and effectif_ok,
        bloquant=True,
    )


def evaluer_terminer(completude: Completude) -> PreparationJalon:
    """« Prêt à terminer ? » — la complétude **sportive**, relue telle quelle.

    Aucun calcul propre : les lignes *sont* `completude.sportif` et `pret` *est*
    `completude.sportif_complet`. C'est le CA « sans doublonner ce qui existe » pris au pied de la
    lettre — un second calcul finirait par contredire le premier, et l'écran des paiements
    (`CompletudeAdministrative`, E16US003) lit déjà la même réponse serveur.

    `bloquant` est `False` : terminer n'a **aucune** garde dure. L'incomplétude change le libellé de
    la confirmation (« Terminer quand même ? »), jamais le droit de terminer — une garde ici
    empêcherait de clore un tournoi pour une cible abandonnée, le contraire de `D-15`.

    L'administratif reste **hors** de ce jalon (retour A14, E16US003) : les paiements ne bloquent
    pas la clôture sportive et se suivent sur l'axe Gestion.
    """
    return PreparationJalon(
        jalon=Jalon.TERMINER,
        lignes=completude.sportif,
        pret=completude.sportif_complet,
        bloquant=False,
    )
