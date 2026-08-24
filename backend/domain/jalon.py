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

**`bloquant` porte l'asymétrie de la famille.** *Démarrer* a des gardes de **contenu** (créneaux,
effectif) ; *terminer* n'en a aucune — `sportif_complet` choisit le libellé de la confirmation, il
ne garde rien (E12US005). Sans ce drapeau, la forme unique dirait la même chose des deux, donc
serait fausse sur l'un des deux.

⚠️ **La garde de statut, elle, est commune aux trois membres qui gardent une transition** — et elle
manquait à la première version de ce module, relevée en revue (axe D). `ServiceTournois` la lève
avant toute autre (`TransitionStatutInvalide`) : *démarrer* n'est atteignable que depuis *brouillon*
ou *prêt*, *terminer* que depuis *en cours*. Un jalon qui l'ignorait répondait « prêt, et l'action
passera » sur un tournoi déjà lancé — le 200 rassurant et faux que l'ADR interdit ailleurs, et le
piège tendu à `ARCHIVER`, dont le **statut est la seule garde**.

Les lignes réutilisent `LigneCompletude` / `EtatSection` de `domain.completude` : c'est déjà le
vocabulaire de `D-17` / `D-18` (liste d'états, jamais une barre de progression), et le jalon
*terminer* **est** la complétude sportive — la relire plutôt que la réécrire est le CA « sans
doublonner ce qui existe ».
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
# `DEMARRER` en garde deux : « prêt à démarrer ? » répond de l'**étape** (arriver à *en cours*), pas
# du prochain clic, et deux transitions y mènent.
# `None` — et **surtout pas** un tuple vide — pour `EXPORTER` : il garde un **geste répétable**, pas
# une transition (ADR-0096 §4). Un tuple vide se lit `any(nom in ())` → `False` **sur les sept
# statuts**, c'est-à-dire « la question ne se pose jamais » : l'export serait annoncé impossible y
# compris sur un tournoi *archivé*, l'état qu'ADR-0026 définit précisément comme « verrou total,
# après export ». C'était un piège armé pour `E16US007`, à qui cet ADR promet qu'elle « n'a plus de
# forme à inventer » : elle aurait recopié le patron des deux membres livrés et obtenu un écran
# bloqué partout (4ᵉ passe de revue, axe D). `None` dit « rien à garder », donc « toujours posée ».
_TRANSITIONS_DU_JALON: dict[Jalon, tuple[str, ...] | None] = {
    Jalon.DEMARRER: ("vers-pret", "demarrer"),
    Jalon.TERMINER: ("terminer",),
    Jalon.ARCHIVER: ("archiver",),
    Jalon.EXPORTER: None,
}


def transition_offerte(statut: StatutTournoi, jalon: Jalon) -> bool:
    """Le statut offre-t-il encore une transition de ce jalon ?

    ⚠️ **Dérivé, jamais recopié.** La première version portait `(BROUILLON, PRET)` et `EN_COURS` en
    dur — un **second encodage** de la table que ce module importe déjà, dans le commit même qui
    érigeait le transport du verdict en doctrine (relevé en 2ᵉ passe par les axes A et C2). Le jour
    où `terminer` sera accepté depuis *en pause*, la table bouge et le jalon suit — sans quoi il
    annoncerait un refus que le serveur ne prononce plus.

    ⚠️ `_TRANSITIONS_DU_JALON` doit rester **totale** sur `Jalon` : un membre ajouté à la famille
    sans sa ligne ici lève un `KeyError` (donc un 500), et non un refus typé. Un test paramétré sur
    `list(Jalon)` le garde — la règle ne vit plus seulement dans ce commentaire.

    Un membre à `None` ne garde **aucune** transition : la question se pose alors toujours (`True`),
    quel que soit le statut. Ne pas confondre avec « aucune transition offerte » (`False`).
    """
    noms = _TRANSITIONS_DU_JALON[jalon]
    if noms is None:
        return True
    return any(transition.nom in noms for transition in transitions_possibles(statut))


@dataclass(frozen=True)
class PreparationJalon:
    """La réponse d'un jalon : ce qui manque, et si l'action passera.

    - `lignes` : *ce qui manque*, en états (`D-17`) — jamais un pourcentage ;
    - `pret` : la réponse **binaire** à « puis-je passer à l'étape suivante ? » ;
    - `question_posee` : la question a-t-elle encore un objet ? À `False`, l'étape n'est plus
      atteignable depuis le statut courant, et l'écran ne rend **pas** de verdict — seulement la
      raison (`detail`). ⚠️ **Ce champ existe parce que la liste ne peut plus le dire.** Tant que
      les deux membres vidaient leurs lignes hors transition offerte, `lignes == ()` **était** le
      signal ; il a cessé de l'être quand *terminer* a gardé les siennes, et n'a d'abord été
      remplacé que par un commentaire. Un écran neuf recopiant le patron aurait alors annoncé « ce
      qui manque ci-dessous sera refusé » au-dessus de trois lignes vertes — le défaut qu'une passe
      entière avait servi à fermer (6ᵉ passe de revue, axes C1 et D). ⚠️ **Sans valeur par
      défaut** : la prop TS jumelle est obligatoire pour la même raison, et l'oublier ici serait
      pire — `ARCHIVER` a le **statut pour seule garde**, donc un membre neuf qui ne renseigne pas
      ce champ répondrait « la question se pose » sur un tournoi archivé, en silence (7ᵉ passe).

    - `bloquant` : à `False`, l'action passe **quand même** malgré `pret is False` (`D-15`) ;
    - `detail` : la **cause chiffrée** du blocage, quand elle existe — « 8 archer(s) inscrit(s) sur
      le départ 2 pour 34 requis… ». Une ligne dit *quoi* (« Inscrits · 8/34 ») ; `detail` dit
      *pourquoi ce chiffre-là* (`D-16` / `P-4` : « une alerte qui ne chiffre pas son impact est un
      clic de plus, pas une protection »). Sur un tournoi à deux créneaux de 40 et 8, « 8/34 » seul
      contredit le total affiché ailleurs — c'est le défaut qu'ADR-0075 a coûté cher à trouver. La
      phrase n'est **pas rédigée ici** : elle vient de `ExigenceEffectifTournoi.message_de_refus`,
      celle-là même que la garde met dans son refus, pour que l'avertissement et le refus ne
      puissent pas diverger ;
    - `moment` : **quand** le refus tombera — « au démarrage », « dès le passage en « prêt » ».
      Dérivé de la garde qui bloque en **premier**, jamais du jalon : les deux gardes de *démarrer*
      ne tombent pas au même clic (les créneaux au passage en *prêt*, l'effectif au démarrage). Le
      front l'écrivait en dur, donc juste pour l'effectif et **faux** pour les créneaux — sur
      l'état initial de tout tournoi neuf (relevé en 2ᵉ passe de revue, axe C1).

    ⚠️ **Aucun bouton n'est jamais désactivé sur la foi de ces champs.** E05US021 avait déjà tranché
    ce point pour le démarrage : l'avertissement se lit avant le clic, le refus remonte du serveur.
    Un front qui grise le bouton se met à décider d'une garde — et devient la seconde source que le
    CA interdit.
    """

    jalon: Jalon
    lignes: tuple[LigneCompletude, ...]
    pret: bool
    bloquant: bool
    question_posee: bool
    detail: str | None = None
    moment: str | None = None


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

    - **Statut** (`statut`) : garde de `vers_pret` **et** de `demarrer` — la question ne se pose
      qu'avant le départ (`brouillon`, `prêt`). Elle ne produit **pas de ligne** : « ce qui manque »
      n'a pas de sens pour un tournoi déjà lancé, il n'y a simplement plus rien à préparer.
    - **Créneaux** (`nb_creneaux`) : garde de `vers_pret` (E02US010) — sans départ, pas de feu
      vert. `EN_ATTENTE` plutôt qu'`ALERTE` : rien n'est commencé, il n'y a pas d'écart à chiffrer.
    - **Inscrits** (`effectif_suffisant`) : garde de `demarrer` (E05US021), chiffrée « 28/34 ».
      ⚠️ Le **verdict est reçu, pas recalculé** : c'est `ExigenceEffectifTournoi.suffisant`, le
      champ exact que `_exiger_un_effectif_suffisant` lit pour refuser. La première version
      comparait `inscrits >= minimum` ici — vrai aujourd'hui, faux au premier assouplissement de
      `exigence_effectif`, et **aucun test ne l'aurait vu** puisque les deux formules coïncidaient
      (relevé par quatre axes de revue). `inscrits`/`minimum` ne servent donc plus qu'à **chiffrer**
      la ligne. `minimum == 0` (rien n'est prélevé, rien n'est exigé) ne porte alors aucun décompte.
    - **Déroulé composé** (`nb_etapes_deroule`) : **avertissement seul**. Le service laisse démarrer
      un tournoi sans déroulé ; le dire bloquant ferait mentir l'écran. Que ce soit *souhaitable*
      est une autre question — elle est ouverte à l'ADR, pas tranchée ici.

    `pret` ne retient donc que les gardes dures. `bloquant` est `True` : le serveur refuse
    réellement, et l'écran doit annoncer un refus, pas une simple gêne.

    ⚠️ **`pret` répond de l'étape, pas du prochain clic.** Depuis *brouillon*, l'action offerte est
    `vers-pret`, qui n'exige que les créneaux : un tournoi à 28 inscrits sur 34 y passera « prêt »
    alors que ce jalon dit déjà `pret is False`. Ce n'est pas une contradiction, c'est **tout
    l'objet de l'US** — annoncer l'effectif *avant* le premier clic plutôt qu'au second. C'est en
    revanche ce qui oblige l'écran à dire *quand* le refus tombe (« sera refusé **au démarrage** »)
    et non « sera refusé », qui se lirait comme un refus immédiat (relevé en revue, axe D).
    """
    if not transition_offerte(statut, Jalon.DEMARRER):
        # **Aucune ligne** : « ce qui manque » n'a pas de sens pour un tournoi qui ne partira plus.
        # Les rendre quand même — ce que faisait la 1ʳᵉ correction, contre sa propre docstring —
        # obligeait le front à les masquer lui-même, donc à recopier la garde (axes B et D).
        return PreparationJalon(
            jalon=Jalon.DEMARRER,
            lignes=(),
            pret=False,
            bloquant=True,
            question_posee=False,
            detail=_pourquoi_plus_a_lancer(statut),
        )

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


def _etat_effectif(suffisant: bool, minimum: int) -> EtatSection:
    """L'état de la ligne « Inscrits » — trois cas, et pas deux.

    ⚠️ **Zéro inscrit n'est pas « terminé »**, même quand rien n'est exigé (aucun déroulé composé,
    donc aucun prélèvement à honorer). La première version rendait alors `OK`, que le front affiche
    « Inscrits · **Terminé** » sur un tournoi tout juste créé — lisible comme « les inscriptions
    sont closes » (relevé en revue, axe C1). `EN_ATTENTE` est la définition même du cas : « rien
    encore d'exploitable » (`domain.completude.EtatSection`). Cela ne change **pas** `pret` : un
    tournoi sans exigence démarre, c'est `D-15`.
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

    Aucun calcul propre : les lignes *sont* `completude.sportif` et `pret` *est*
    `completude.sportif_complet`. C'est le CA « sans doublonner ce qui existe » pris au pied de la
    lettre — un second calcul finirait par contredire le premier, et l'écran des paiements
    (`CompletudeAdministrative`, E16US003) lit déjà la même réponse serveur.

    `bloquant` est `False` **pendant le tournoi** : terminer n'a aucune garde de *contenu*.
    L'incomplétude change le libellé de la confirmation (« Terminer quand même ? »), jamais le droit
    de terminer — une garde ici empêcherait de clore un tournoi pour une cible abandonnée, le
    contraire de `D-15`.

    ⚠️ **Hors *en cours*, il en a une** — et la première version disait « aucune », ce qui était
    faux (relevé en revue). `ServiceTournois.terminer` n'accepte que `{EN_COURS}` : sur un tournoi
    **en pause** (la pause déjeuner du jour J), terminer est refusé tant qu'on n'a pas repris.
    Répondre `bloquant=False` y aurait fait dire à l'écran « l'application ne vous en empêchera
    pas » juste avant un 409.

    L'administratif reste **hors** de ce jalon (retour A14, E16US003) : les paiements ne bloquent
    pas la clôture sportive et se suivent sur l'axe Gestion.
    """
    offert = transition_offerte(statut, Jalon.TERMINER)
    return PreparationJalon(
        jalon=Jalon.TERMINER,
        # ⚠️ **Toujours rendues, quel que soit le statut** — asymétrie **assumée** avec
        # `evaluer_demarrer`, pas un oubli. Chez *démarrer*, la liste **est** la préparation : un
        # tournoi déjà lancé n'a plus rien à préparer, donc rien à lister. Chez *terminer*, elle
        # **est l'état sportif** : « où en est la qualification » a du sens à tout statut, et c'est
        # ce que l'organisateur vient voir pendant la pause déjeuner.
        #
        # La vider ici fut une **sur-correction** : elle visait un verdict qui accusait des lignes
        # vertes (3ᵉ passe), alors que c'était le **verdict** qu'il fallait couper. La 4ᵉ passe l'a
        # corrigé à l'écran et pas ici — les deux versants du même membre répondaient donc
        # différemment au même cas, et la résorption inscrite à `DETTE-084` (« migrer l'écran sur
        # `/jalons/terminer` ») aurait **rétabli** la régression (5ᵉ passe, quatre axes).
        #
        # Ce qui porte la garde de statut, c'est `question_posee` — plus `pret`, `bloquant` et
        # `detail`. Jamais la liste.
        lignes=completude.sportif,
        pret=offert and completude.sportif_complet,
        bloquant=not offert,
        question_posee=offert,
        # La phrase du refus lui-même (`domain.tournoi`), pas une seconde rédaction : la 1ʳᵉ
        # correction la recopiait mot pour mot depuis `ServiceTournois.terminer` — la duplication
        # que ce même travail dénonçait pour l'effectif (2ᵉ passe, axes A, C2 et D).
        detail=None if offert else MESSAGE_TERMINER_HORS_EN_COURS,
    )
