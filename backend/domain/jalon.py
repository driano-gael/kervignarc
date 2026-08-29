"""Les **jalons « prêt à… »** — « puis-je passer à l'étape suivante, et sinon quoi ? » (ADR-0096).

Politique pure : aucune I/O, aucun framework (règle 1).

⚠️ **Ne pas fusionner les règles des quatre membres** : chacun a ses propres entrées, et une
fonction unique reconstruirait à l'intérieur les quatre variantes que la forme unique évite. Les
lignes réutilisent `LigneCompletude` — le jalon *terminer* **est** la complétude sportive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.completude import Completude, EtatSection, LigneCompletude
from domain.tournoi import (
    MESSAGE_SANS_DEPART,
    MESSAGE_TERMINER_HORS_EN_COURS,
    StatutTournoi,
    transitions_possibles,
)

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


# Les transitions que chaque jalon garde, **par leur nom** — ceux de `domain.tournoi._TRANSITIONS`.
# `DEMARRER` en garde deux : « prêt à démarrer ? » répond de l'**étape**, pas du prochain clic.
# ⚠️ `None` — et **surtout pas** un tuple vide — pour `EXPORTER`, qui garde un **geste répétable**
# (ADR-0096 §4) : `any(nom in ())` est `False` sur les **sept** statuts, donc l'export serait
# annoncé impossible jusque sur un tournoi *archivé*, l'état qu'ADR-0026 définit comme « après
# export ». `None` dit « rien à garder », donc « toujours posée ».
_TRANSITIONS_DU_JALON: dict[Jalon, tuple[str, ...] | None] = {
    Jalon.DEMARRER: ("vers-pret", "demarrer"),
    Jalon.TERMINER: ("terminer",),
    Jalon.ARCHIVER: ("archiver",),
    Jalon.EXPORTER: None,
}


def transition_offerte(statut: StatutTournoi, jalon: Jalon) -> bool:
    """Le statut offre-t-il encore une transition de ce jalon ?

    ⚠️ **Dérivé, jamais recopié.** La première version portait `(BROUILLON, PRET)` et `EN_COURS` en
    dur — un second encodage de la table que ce module importe déjà. ⚠️ `_TRANSITIONS_DU_JALON`
    doit rester **totale** sur `Jalon` : un membre sans sa ligne lève un `KeyError` (donc un 500)
    au lieu d'un refus typé — un test paramétré sur `list(Jalon)` le garde. `None` = aucune garde
    (`True`).
    """
    noms = _TRANSITIONS_DU_JALON[jalon]
    if noms is None:
        return True
    return any(transition.nom in noms for transition in transitions_possibles(statut))


@dataclass(frozen=True)
class PreparationJalon:
    """La réponse d'un jalon : ce qui manque, et si l'action passera.

    `lignes` = ce qui manque, en états (`D-17`). `pret` = « puis-je passer à l'étape suivante ? ».
    `question_posee` = la question a-t-elle un objet — ⚠️ **sans valeur par défaut**, `ARCHIVER`
    n'ayant que le statut pour garde. `bloquant=False` = l'action passe quand même (`D-15`).
    `detail` = la cause chiffrée, **reprise de** `ExigenceEffectifTournoi.message_de_refus`. ⚠️
    Aucun bouton n'est grisé sur la foi de ces champs.
    """

    jalon: Jalon
    lignes: tuple[LigneCompletude, ...]
    pret: bool
    bloquant: bool
    question_posee: bool
    detail: str | None = None
    moment: str | None = None


class NiveauPreparation(str, Enum):
    """Les deux niveaux de pastille du CA d'E16US010, plus l'absence de pastille.

    `AVERTISSEMENT` = « tout n'est pas complet » ; `ALERTE` = « impossible de lancer en l'état »
    (questionnaire A02). ⚠️ Deux niveaux **et pas trois** : `EtatSection` en a quatre, mais c'est
    l'état d'une *ligne* — ici on résume une préparation entière pour une ligne de liste.
    """

    AUCUN = "aucun"
    AVERTISSEMENT = "avertissement"
    ALERTE = "alerte"


# Les états de ligne qui comptent comme un **manque**. ⚠️ `A_VENIR` n'en est pas un : il marque un
# séquencement de l'appli (`domain.completude`), et le compter rendrait la pastille inextinguible.
_ETATS_EN_MANQUE = frozenset({EtatSection.ALERTE, EtatSection.EN_ATTENTE})


def niveau_de_preparation(preparation: PreparationJalon) -> NiveauPreparation:
    """Résume une préparation en un niveau d'alerte, pour une **ligne de liste** (E16US010).

    ⚠️ **Dérivé, jamais recalculé** : aucune garde n'est relue ici, sinon la liste et l'écran du
    jalon finiraient par se contredire — c'est ce que le CA d'E16US012 interdit. ⚠️ `pret` seul ne
    suffit pas : il vaut `False` sur un tournoi déjà lancé, qui ne doit porter **aucune** pastille.
    C'est `question_posee` qui dit si la question a encore un objet.
    """
    if not preparation.question_posee:
        return NiveauPreparation.AUCUN
    if not preparation.pret:
        return NiveauPreparation.ALERTE if preparation.bloquant else NiveauPreparation.AVERTISSEMENT
    if any(ligne.etat in _ETATS_EN_MANQUE for ligne in preparation.lignes):
        return NiveauPreparation.AVERTISSEMENT
    return NiveauPreparation.AUCUN


def resume_du_manque(preparation: PreparationJalon) -> str | None:
    """Ce que la pastille dit quand on la survole — `None` si elle ne s'allume pas.

    `D-16` : « une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection ».
    ⚠️ **Rédigé ici, jamais au front** — même raison que la question du jalon : une seconde table
    de libellés finirait par contredire celle du refus. La phrase du refus prime quand elle existe,
    parce qu'elle est déjà **celle que le serveur opposera** au clic.
    """
    if niveau_de_preparation(preparation) is NiveauPreparation.AUCUN:
        return None
    if preparation.detail is not None:
        return preparation.detail
    restants = [ligne.libelle for ligne in preparation.lignes if ligne.etat in _ETATS_EN_MANQUE]
    return f"Il reste à préparer : {', '.join(restants)}." if restants else None


def evaluer_demarrer(
    *,
    statut: StatutTournoi,
    nb_creneaux: int,
    nb_etapes_deroule: int,
    effectif_suffisant: bool,
    inscrits: int,
    minimum: int,
    cause_effectif: str | None,
) -> PreparationJalon:
    """« Prêt à démarrer ? » — les trois gardes du feu vert, plus un avertissement sans effet.

    Statut (garde de `vers_pret` **et** de `demarrer`, sans ligne : rien à préparer sur un tournoi
    lancé), créneaux (E02US010), inscrits (E05US021). ⚠️ Le **verdict est reçu, pas recalculé** :
    `ExigenceEffectifTournoi.suffisant`, le champ que `_exiger_un_effectif_suffisant` lit. Le
    déroulé composé n'est qu'un **avertissement**. ⚠️ `pret` répond de l'**étape**, pas du prochain
    clic — d'où `moment`.
    """
    if not transition_offerte(statut, Jalon.DEMARRER):
        return demarrer_sans_objet(statut)

    etat_creneaux = EtatSection.OK if nb_creneaux > 0 else EtatSection.EN_ATTENTE
    etat_effectif = _etat_effectif(effectif_suffisant, minimum)
    etat_deroule = EtatSection.OK if nb_etapes_deroule > 0 else EtatSection.EN_ATTENTE
    creneaux_ok = etat_creneaux is EtatSection.OK

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
        pret=creneaux_ok and effectif_suffisant,
        bloquant=True,
        question_posee=True,
        detail=_cause_demarrer(creneaux_ok, effectif_suffisant, cause_effectif),
        moment=_moment_du_refus(creneaux_ok, effectif_suffisant),
    )


def demarrer_sans_objet(statut: StatutTournoi) -> PreparationJalon:
    """La réponse de « prêt à démarrer ? » pour un tournoi qui ne partira plus.

    **Aucune ligne** : « ce qui manque » n'a pas de sens ici. Les rendre quand même obligeait le
    front à les masquer lui-même, donc à recopier la garde (E16US012, axes B et D).
    ⚠️ **Publique depuis E16US010** : l'agrégat de liste s'en sert pour trancher un tournoi *sans
    lire ses créneaux ni son effectif* — il n'y a rien à préparer, donc rien à aller chercher.
    C'est la **même** réponse que par le chemin complet ; ne pas en écrire une seconde ici.
    """
    return PreparationJalon(
        jalon=Jalon.DEMARRER,
        lignes=(),
        pret=False,
        bloquant=True,
        question_posee=False,
        detail=_pourquoi_plus_a_lancer(statut),
    )


def _etat_effectif(suffisant: bool, minimum: int) -> EtatSection:
    """L'état de la ligne « Inscrits » — trois cas, et pas deux.

    ⚠️ **Zéro inscrit n'est pas « terminé »**, même quand rien n'est exigé : le front afficherait «
    Inscrits · **Terminé** » sur un tournoi tout juste créé, lisible comme « les inscriptions sont
    closes ». `EN_ATTENTE` est la définition même du cas (`domain.completude.EtatSection`). Cela ne
    change **pas** `pret` : un tournoi sans exigence démarre, c'est `D-15`.
    """
    if not suffisant:
        return EtatSection.ALERTE
    return EtatSection.OK if minimum > 0 else EtatSection.EN_ATTENTE


def _pourquoi_plus_a_lancer(statut: StatutTournoi) -> str:
    """Pourquoi la question ne se pose plus — et **pas** « déjà lancé » pour tout le monde.

    Un tournoi **annulé** depuis le brouillon n'a jamais démarré (`brouillon → annule` existe). La
    1ʳᵉ correction l'avait corrigé côté écran et laissé faux au **contrat** — celui-là même dont
    l'argument était que `E16US007` et `E16US008` le liront sans le garde-fou du front (relevé en
    2ᵉ passe de revue par quatre axes).
    """
    if statut is StatutTournoi.ANNULE:
        return "Ce tournoi est annulé : il ne sera pas lancé."
    if statut is StatutTournoi.ARCHIVE:
        return "Ce tournoi est archivé : il est en lecture seule."
    return "Ce tournoi est déjà lancé : il n'y a plus rien à préparer avant son démarrage."


def _cause_demarrer(
    creneaux_ok: bool, effectif_suffisant: bool, cause_effectif: str | None
) -> str | None:
    """La phrase qui explique le blocage — celle du refus, jamais une seconde rédaction.

    L'ordre suit celui des gardes : sans créneau, c'est `vers_pret` qui refusera d'abord, et c'est
    donc **son** message qu'il faut afficher.
    """
    if not creneaux_ok:
        return MESSAGE_SANS_DEPART
    return None if effectif_suffisant else cause_effectif


def _moment_du_refus(creneaux_ok: bool, effectif_suffisant: bool) -> str | None:
    """Au clic de quelle action le refus tombera — les deux gardes ne tombent pas au même.

    Sans créneau, c'est `vers_pret` qui refuse (`TournoiSansDepart`), donc **dès** « Marquer
    prêt » ; l'effectif, lui, n'est vérifié qu'au démarrage. Annoncer « au démarrage » dans les
    deux cas rendait la phrase fausse sur l'état initial de tout tournoi neuf.
    """
    if not creneaux_ok:
        return "dès le passage en « prêt »"
    return None if effectif_suffisant else "au démarrage"


def evaluer_terminer(*, completude: Completude, statut: StatutTournoi) -> PreparationJalon:
    """« Prêt à terminer ? » — la complétude **sportive**, relue telle quelle.

    Aucun calcul propre : les lignes *sont* `completude.sportif`, `pret` *est*
    `completude.sportif_complet` — un second calcul finirait par contredire le premier. `bloquant`
    est `False` **pendant le tournoi** (terminer n'a aucune garde de contenu, `D-15`), ⚠️ mais
    `True` ailleurs : `ServiceTournois.terminer` n'accepte que `{EN_COURS}`, donc terminer un
    tournoi *en pause* part en 409. L'administratif reste **hors** de ce jalon (E16US003).
    """
    offert = transition_offerte(statut, Jalon.TERMINER)
    return PreparationJalon(
        jalon=Jalon.TERMINER,
        # ⚠️ **Toujours rendues, quel que soit le statut** — asymétrie **assumée** avec
        # `evaluer_demarrer` : là-bas la liste **est** la préparation (rien à lister sur un tournoi
        # lancé), ici elle **est l'état sportif**, que l'organisateur vient voir pendant la pause.
        # La vider fut une sur-correction, corrigée à l'écran seulement — les deux versants du même
        # membre répondaient donc différemment, et la résorption de `DETTE-084` (« migrer l'écran
        # sur `/jalons/terminer` ») aurait **rétabli** la régression.
        #
        # Ce qui porte la garde de statut, c'est `question_posee` — jamais la liste.
        lignes=completude.sportif,
        pret=offert and completude.sportif_complet,
        bloquant=not offert,
        question_posee=offert,
        # La phrase du refus lui-même (`domain.tournoi`), pas une seconde rédaction : la 1ʳᵉ
        # correction la recopiait mot pour mot depuis `ServiceTournois.terminer` — la duplication
        # que ce même travail dénonçait pour l'effectif (2ᵉ passe, axes A, C2 et D).
        detail=None if offert else MESSAGE_TERMINER_HORS_EN_COURS,
    )
