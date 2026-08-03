"""Erreurs du **tir** — ce qui se passe sur le pas de tir et ce qu'on en note : séries et
volées de qualification, duels et manches, barrages, formats de départage (poules, Big
Shoot Off, système suisse, colline), forfaits.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 77 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from application.erreurs.base import ApplicationError


class BarrageIntrouvable(ApplicationError):
    """Aucun barrage de cet identifiant dans ce tournoi (E06US003)."""

    code = "barrage_introuvable"


class EgaliteNonDepartageable(ApplicationError):
    """L'égalité annoncée n'en est plus une, ou la politique ne réclame pas de barrage (E06US003).

    Le cas n'est pas théorique : entre le moment où l'écran affiche « barrage requis au rang 8 » et
    celui où l'organisateur clique, une volée validée en retard peut avoir défait l'égalité. Ouvrir
    quand même ferait tirer des archers que plus rien n'oppose. Sert aussi au refus de **clore** un
    barrage encore indécis — sa clôture dirait « c'est tranché » alors qu'il reste à retirer.
    """

    code = "egalite_non_departageable"


class BarragePerime(ApplicationError):
    """Un barrage est ouvert à cette place, mais sur d'autres tireurs (E06US003).

    Le classement a bougé depuis son annonce — une volée validée en retard, un score corrigé, un
    forfait. L'ancien barrage ne départage plus le bon groupe, et son verdict sera écarté. On refuse
    d'en ouvrir un second plutôt que de laisser l'organisateur faire tirer un groupe incomplet
    devant un écran qui ne lui dirait rien.
    """

    code = "barrage_perime"


class TireursDesignesInvalides(ApplicationError):
    """Les archers désignés pour un barrage de poule / Big Shoot Off ne conviennent pas (E06US003).

    Régime **désigné** : aucun classement ne valide les tireurs, donc le service vérifie ce que la
    qualification obtenait gratuitement — au moins deux archers distincts, du **bon** tournoi, et
    une phase du bon tournoi. Erreur distincte d'`EgaliteNonDepartageable` : aucun de ces cas n'est
    une égalité indépartageable, et le `code` est ce sur quoi le front et les journaux s'appuient.
    """

    code = "tireurs_designes_invalides"


class ArcherIntrouvable(ApplicationError):
    """Aucun archer ne correspond à l'identifiant demandé."""

    code = "archer_introuvable"


class ArcherEngage(ApplicationError):
    """Suppression suspendue : l'archer est placé ou a déjà tiré (E02US003) → 409.

    **Un signalement, pas un refus** — 3ᵉ de la famille, même protocole qu'`HomonymeArcher`
    (ADR-0015) : la machine constate un fait lourd, elle ne sait pas ce qu'il signifie. L'admin
    tranche via `ServiceArchers.supprimer(autoriser_suppression_engage=True)`, et la suppression
    confirmée **efface les scores et le placement** — définitivement, sans journal (l'audit est
    E10US005).

    **Ce signalement n'est pas la façon d'enregistrer un abandon.** Un archer qui arrête en cours
    d'épreuve n'est pas une donnée à effacer : c'est un **forfait tracé** (daté, attribué, motif,
    réversible, audité) — E12US004, qui **préserve** ses flèches. La suppression, elle, ne sert
    que l'**erreur de saisie** (cet archer n'aurait jamais dû être inscrit) et le **cas majeur**.
    D'où le message, qui dit ce qui sera détruit plutôt que d'inviter à cliquer.

    **Refus définitif d'abord retenu, renversé le 16/07/2026** (arbitrage métier). Il tenait la
    place du forfait sans en être un : l'archer devenait indéboulonnable à vie et le message
    prescrivait un geste — « retirez-le de son placement » — qu'aucun écran n'offrait. Le vrai
    besoin était de **séparer** forfait et suppression, pas de refuser la seconde.
    """

    code = "archer_engage"


class CategorieIntrouvable(ApplicationError):
    """Aucune catégorie ne correspond à l'identifiant demandé."""

    code = "categorie_introuvable"


class BlasonIntrouvable(ApplicationError):
    """Aucun blason ne correspond à l'identifiant demandé."""

    code = "blason_introuvable"


class DuelDesynchronise(ApplicationError):
    """Le tir enregistré oppose d'**autres** duellistes que ceux recalculés (E04US013) → 409.

    Le tableau est reconstruit du classement à chaque opération (ADR-0048) ; le tir, lui, est
    **ancré** sur l'identité des duellistes qui l'ont produit (ADR-0049 §4). Si le classement bouge
    depuis le tir (correction de qualification…), les occupants recalculés du match divergent des
    enregistrés : on **refuse** d'écrire dessus plutôt que d'attribuer le score en silence
    à d'autres archers (« un score faux et silencieux est pire qu'une erreur visible »). Conflit
    d'état, pas un 404 : le tir existe, mais il ne correspond plus à ce match. Le gel du classement
    pendant la phase de tableau relève du cycle de vie (E01US017/E12US002).
    """

    code = "duel_desynchronise"


class ScoreurHorsTournoi(ApplicationError):
    """Un scoreur agit (valide/corrige) sur une série d'un **autre tournoi** que le sien. → 403.

    Le scoreur est **itinérant dans son tournoi** (`D-12`) : il valide n'importe quelle cible, mais
    de **son** tournoi seulement. Sa session est valide (identité établie), mais elle n'autorise pas
    à agir dans un tournoi voisin — la faille se rouvrirait en concurrence de tournois (intérieur +
    extérieur). **Refus, pas défaut d'authentification** : 403, comme `SaisieHorsCible` (le poste
    hors cible). L'admin, lui, n'a pas cette borne (E10US001).
    """

    code = "scoreur_hors_tournoi"


class SaisieHorsCible(ApplicationError):
    """Un poste tente de saisir pour un archer qui n'est pas sur **sa** cible (E10US007). → 403.

    **Refus, pas signalement, et surtout pas 401** : le jeton de poste est valide (l'identité par
    le *lieu* est établie, `D-13`, ADR-0030), mais il n'autorise la saisie que pour la cible qu'il
    sert. Un poste sur une **autre** cible — ou d'un **autre tournoi**, les numéros de cible se
    répètent d'un tournoi à l'autre — ou visant un archer **non placé** (sur aucune cible) est
    éconduit. C'est le **premier 403** du projet : « authentifié mais interdit pour cette
    ressource » n'est ni un défaut d'authentification (401) ni un conflit d'état (409). L'admin,
    lui, n'a aucune contrainte de cible (E10US001) : ce refus ne vise que l'identité *poste*.
    """

    code = "saisie_hors_cible"


class ForfaitDejaDeclare(ApplicationError):
    """L'archer est **déjà** déclaré forfait dans cette phase (E04US015, ADR-0050). → 409.

    **Un refus, pas un signalement** : un forfait par `(tournoi, archer, phase)` (unicité en base).
    Re-déclarer n'a pas de sens tant que le premier tient — pour **changer** la nature (abandon ↔
    DSQ), on **annule** puis on re-déclare (chemin réversible, `D-15`), ce qui laisse deux traces
    d'audit distinctes plutôt qu'une mutation silencieuse.
    """

    code = "forfait_deja_declare"


class ForfaitIntrouvable(ApplicationError):
    """Aucun forfait de cet archer dans cette phase à annuler (E04US015, ADR-0050). → 404.

    L'annulation (réversibilité, `D-15`) suppose une déclaration existante ; sans elle, il n'y a
    rien à défaire.
    """

    code = "forfait_introuvable"


class ForfaitTournoiTermine(ApplicationError):
    """Déclarer ou annuler un forfait sur un tournoi **terminé** est refusé (`D-15`). → 409.

    Le forfait est réversible **tant que le tournoi n'est pas terminé** : une fois clos, les
    résultats sont figés — on ne rouvre pas un abandon ni une DSQ. Ce n'est pas un signalement (rien
    à confirmer) mais un **conflit d'état**, comme la suppression d'un tournoi en cours.
    """

    code = "forfait_tournoi_termine"
