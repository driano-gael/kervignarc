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

    **Un signalement, pas un refus** — même protocole qu'`HomonymeArcher` (ADR-0015) : l'admin
    tranche via `autoriser_suppression_engage`, et la suppression confirmée **efface scores et
    placement**. ⚠️ **Ce n'est pas la façon d'enregistrer un abandon** : celui-ci est un **forfait
    tracé** qui **préserve** les flèches (E04US015, ADR-0050). Le refus définitif d'abord retenu a
    été renversé le 16/07/2026 : il tenait la place du forfait sans en être un.
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

    Le tableau est reconstruit du classement à chaque opération (ADR-0048) ; le tir est **ancré**
    sur l'identité des duellistes qui l'ont produit (ADR-0049 §4). Si le classement bouge, on
    **refuse** d'écrire plutôt que d'attribuer le score en silence à d'autres archers. Conflit
    d'état et non 404 : le tir existe, il ne correspond plus à ce match.
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
    """Un poste saisit pour un archer qui n'est pas sur **sa** cible (E10US007) → 403.

    **Refus, pas signalement, et surtout pas 401** : le jeton de poste est valide (identité par le
    *lieu*, `D-13`, ADR-0030) mais n'autorise que sa cible. ⚠️ Les numéros de cible se répètent
    d'un tournoi à l'autre, donc un poste d'un **autre tournoi** est éconduit aussi. Premier 403 du
    projet. L'admin n'a aucune contrainte de cible (E10US001) : ce refus ne vise que l'identité
    *poste*.
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


class PhaseEnPause(ApplicationError):
    """La phase est **en pause** : on n'y saisit ni ne valide de résultat neuf (E05US033) → 409.

    ⚠️ **Cette garde n'existait pas avant E05US033** : `StatutPhase.EN_PAUSE` ne gelait **rien**,
    et les archers continuaient de tirer (cf. `DETTE-073` pour le volet tournoi). ⚠️ **Ce refus ne
    couvre pas la correction**, CA explicite du commanditaire : la pause gèle un résultat **neuf**,
    jamais la rectification — `corriger_volee` n'a donc pas cette garde. 409 et non 403 : c'est un
    **état**, le même geste redevient licite à la reprise.
    """

    code = "phase_en_pause"
