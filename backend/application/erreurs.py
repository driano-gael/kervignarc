"""Erreurs applicatives (ADR-0007) — un cas d'usage est impossible.

Racine `ApplicationError`. Traduites à la frontière API en 404 (ressource introuvable)
ou 409 (conflit d'état) ; la couche application, elle, ignore HTTP.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Racine des erreurs de cas d'usage. Chaque sous-classe porte un `code` stable."""

    code = "erreur_application"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TournoiIntrouvable(ApplicationError):
    """Aucun tournoi ne correspond à l'identifiant demandé."""

    code = "tournoi_introuvable"


class TransitionStatutInvalide(ApplicationError):
    """Transition de cycle de vie impossible depuis l'état courant (E01US002) → 409.

    Ex. démarrer un tournoi déjà démarré ou terminé, terminer un tournoi non démarré.
    """

    code = "transition_statut_invalide"


class TournoiEnCoursNonSupprimable(ApplicationError):
    """Suppression refusée : le tournoi est en cours (E01US002) → 409.

    Il faut d'abord le **terminer** ; un tournoi `brouillon` ou `terminé` reste supprimable.
    """

    code = "tournoi_en_cours_non_supprimable"


class DepartIntrouvable(ApplicationError):
    """Aucun départ (créneau) ne correspond à l'identifiant dans ce tournoi (E02US004) → 404.

    Couvre l'identifiant inconnu **et** le départ d'un **autre** tournoi : du point de vue du
    tournoi de l'URL, un créneau qui ne lui appartient pas n'existe pas davantage qu'un identifiant
    inventé — même parti que `CategorieHorsTournoi`, distinguer les deux apprendrait au client ce
    qui vit dans les tournois voisins.
    """

    code = "depart_introuvable"


class DepartAvecInscriptions(ApplicationError):
    """Suppression suspendue : le départ porte des inscriptions (E02US009) → 409.

    **Un signalement, pas un refus** — même famille qu'`ArcherEngage` (ADR-0016), tranchée en
    [ADR-0018](../../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md). Un créneau
    est une **configuration locale du tournoi**, comme un archer : un créneau annulé doit pouvoir
    être retiré sans désinscrire à la main chaque archer. L'admin confirme via
    `ServiceDeparts.supprimer(autoriser_suppression_inscrits=True)`, et la suppression **efface les
    inscriptions** du créneau — définitivement.

    Le message **décompte les inscriptions détruites, dont les payées** : l'effet de bord monétaire
    (le remboursement, déporté en E08US005) est rendu visible au point de décision. Le refus dur
    `ClubReference` a été **écarté** (ADR-0018) — le club est un référentiel *global* partagé entre
    tournois, le départ non.
    """

    code = "depart_avec_inscriptions"


class ArcherIntrouvable(ApplicationError):
    """Aucun archer ne correspond à l'identifiant demandé."""

    code = "archer_introuvable"


class HomonymeArcher(ApplicationError):
    """Inscription suspendue : un archer de même nom, prénom et club existe déjà (E02US002) → 409.

    **Un signalement, pas un refus.** Deux archers réels peuvent porter les mêmes nom, prénom et
    club (un père et son fils, cas courant en compétition de club) : les rejeter interdirait une
    inscription légitime, le jour J, au guichet. C'est donc l'**admin qui tranche** : renoncer
    (il réinscrivait le même archer par mégarde) ou confirmer l'homonyme via
    `ServiceArchers.ajouter(autoriser_homonyme=True)`.

    D'où l'absence de contrainte `UNIQUE` correspondante en base : elle rejetterait le fils sans
    recours. Le contrôle vit ici, et il suffit — le **writer unique** (règle 7, ADR-0005) sérialise
    les écritures, et le contrôle **et** l'insertion tiennent dans la même commande en file, donc
    aucune création concurrente ne peut se glisser entre les deux. Comparaison au sens de
    `domain.archer.cle_identite` (casse et accents repliés). Voir ADR-0015 pour le protocole.
    """

    code = "homonyme_archer"


class ChangementCategorieArcherEngage(ApplicationError):
    """Édition suspendue : on change la catégorie d'un archer qui a déjà tiré (E02US003) → 409.

    **Un signalement, pas un refus** — même protocole qu'`HomonymeArcher` (ADR-0015), et pour la
    même raison : la machine constate un fait troublant, elle ne sait pas ce qu'il signifie. Changer
    de catégorie en cours d'épreuve déplace l'archer d'un classement à l'autre avec ses flèches
    déjà tirées ; c'est le plus souvent une erreur, mais c'est parfois exactement la correction
    attendue (catégorie mal saisie au guichet, découverte à la première volée). Figer la catégorie
    à la première flèche rendrait cette erreur-là inrattrapable ; l'admin tranche via
    `ServiceArchers.modifier(autoriser_changement_categorie=True)`.

    Ne se déclenche que sur un **changement** de catégorie : éditer le nom d'un archer engagé ne
    fausse aucun classement et n'a rien à confirmer.
    """

    code = "changement_categorie_archer_engage"


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


class InscriptionIntrouvable(ApplicationError):
    """Aucune inscription ne correspond à l'identifiant demandé (E02US009) → 404."""

    code = "inscription_introuvable"


class DejaInscrit(ApplicationError):
    """Inscription refusée : l'archer est **déjà inscrit** sur ce départ (E02US009) → 409.

    **Un refus, pas un signalement** — contrairement à l'homonyme (deux personnes distinctes peuvent
    partager une identité), un second lien `(archer, départ)` n'a **aucun sens** : l'archer est déjà
    sur ce créneau. Aucun drapeau ne le lève ; c'est aussi la contrainte `UNIQUE(archer_id,
    depart_id)` en base. Pour changer d'avis, l'admin désinscrit puis réinscrit.
    """

    code = "deja_inscrit"


class DepartComplet(ApplicationError):
    """Inscription refusée : le départ a **atteint son quota** de places (E02US006) → 409.

    **Un refus, pas un signalement** — famille de `DejaInscrit` : le créneau est plein, il n'y a
    aucun sens à passer outre (le quota *est* la capacité de la salle). Aucun drapeau ne le lève ;
    pour faire de la place, l'admin désinscrit quelqu'un ou relève le quota du départ. Contrairement
    à l'unicité, **aucune contrainte SQL** ne garantit le plafond : c'est la sérialisation par le
    writer unique (règle 7) qui empêche deux inscriptions concurrentes de franchir la dernière
    place.
    """

    code = "depart_complet"


class DeplacementInvalide(ApplicationError):
    """Ajustement de placement refusé : le déplacement/échange violerait une contrainte (E03US004).

    **Un refus, pas un signalement** (famille de `DejaInscrit`/`DepartComplet`) → 409. Couvre le
    déplacement qui déborde un budget de cible (capacité, espace, partage de carton, **hauteur** —
    ADR-0022/0024), l'échange dont l'un des deux tireurs ne tient pas à la place de l'autre (refus
    **en bloc**, état inchangé), le dépôt depuis la réserve sur une case **occupée** (rien à
    permuter en retour), une cible/position **inexistante**, ou un archer **sans blason** (fraction
    inconnue, non plaçable). Aucun drapeau ne le lève : l'admin corrige son geste. Le message dit
    **quelle** contrainte bloque, sans détail interne (règle 5).
    """

    code = "deplacement_invalide"


class ClubIntrouvable(ApplicationError):
    """Aucun club ne correspond à l'identifiant demandé."""

    code = "club_introuvable"


class ClubReference(ApplicationError):
    """Suppression refusée : au moins un archer est rattaché à ce club (E02US001) → 409.

    Il faut d'abord **réaffecter ou retirer** ces archers ; un club non référencé reste
    supprimable. Même parti que `BlasonReference` : on refuse plutôt que de cascader
    silencieusement sur des inscriptions.
    """

    code = "club_reference"


class NomClubDejaPris(ApplicationError):
    """Création/renommage refusé : un autre club porte déjà ce nom (E02US001) → 409.

    Règle d'ensemble (le domaine ne voit qu'un club à la fois) : le référentiel n'offre pas
    deux entrées pour un même club, sans quoi les archers se répartiraient entre les doublons.
    Comparaison au sens de `domain.club.cle_nom` : espaces de bord, casse **et accents** repliés
    (cf. `ClubRepository.par_nom`).
    """

    code = "nom_club_deja_pris"


class CategorieIntrouvable(ApplicationError):
    """Aucune catégorie ne correspond à l'identifiant demandé."""

    code = "categorie_introuvable"


class CategorieHorsTournoi(ApplicationError):
    """Catégorie d'un archer incohérente : inexistante ou rattachée à un autre tournoi → 409.

    Règle inter-agrégats (E02US002), calquée sur `BlasonHorsTournoi` : un archer ne peut tirer que
    dans une catégorie **du tournoi où il est inscrit**. Comme pour le blason, l'inexistant et le
    hors-tournoi rendent la **même** erreur : du point de vue de ce tournoi, une catégorie d'un
    autre tournoi n'existe pas davantage qu'un identifiant inventé, et distinguer les deux
    apprendrait au client ce qui vit dans les tournois voisins.
    """

    code = "categorie_hors_tournoi"


class BlasonIntrouvable(ApplicationError):
    """Aucun blason ne correspond à l'identifiant demandé."""

    code = "blason_introuvable"


class BlasonHorsTournoi(ApplicationError):
    """Blason par défaut incohérent : inexistant ou rattaché à un autre tournoi (E01US006) → 409.

    Règle inter-agrégats : une catégorie ne peut porter comme blason par défaut qu'un blason du
    **même** tournoi.
    """

    code = "blason_hors_tournoi"


class BlasonReference(ApplicationError):
    """Suppression refusée : le blason est le blason par défaut d'au moins une catégorie → 409.

    Il faut d'abord **réaffecter** ces catégories (autre blason ou aucun) ; un blason non
    référencé reste supprimable (E01US006).
    """

    code = "blason_reference"


class GabaritIntrouvable(ApplicationError):
    """Aucun gabarit de salle ne correspond à l'identifiant demandé.

    Couvre aussi l'application d'un identifiant qui n'est **pas un modèle** (une instance déjà
    rattachée à un tournoi) : seul un modèle de bibliothèque est applicable (E01US008).
    """

    code = "gabarit_introuvable"


class GabaritDuTournoiAbsent(ApplicationError):
    """Ajustement (E01US008) ou placement (E03US001) demandé alors qu'aucun gabarit n'est appliqué
    au tournoi → 404.

    Il faut d'abord **appliquer** un gabarit modèle au tournoi : sans cibles, il n'y a rien à
    ajuster ni où placer les archers.
    """

    code = "gabarit_du_tournoi_absent"


class PhaseQualificationAbsente(ApplicationError):
    """Grain de validation demandé alors que la qualification n'existe pas encore (E01US015) → 404.

    La phase de qualification naît avec son **barème** (E01US009) : il faut d'abord le définir.
    """

    code = "phase_qualification_absente"


class IdentifiantsInvalides(ApplicationError):
    """Login/mot de passe admin incorrects (E10US002). Traduite en 401 à la frontière."""

    code = "identifiants_invalides"


class NonAuthentifie(ApplicationError):
    """Action admin demandée sans session valide (E10US002). Traduite en 401."""

    code = "non_authentifie"


class AccesDejaConfigure(ApplicationError):
    """Tentative de (re)définir l'accès admin alors qu'il existe déjà (E10US002) → 409."""

    code = "acces_deja_configure"


class AccesNonConfigure(ApplicationError):
    """Connexion demandée alors qu'aucun accès admin n'est encore défini (E10US002) → 409."""

    code = "acces_non_configure"


class ScoreurIntrouvable(ApplicationError):
    """Aucun scoreur ne correspond à l'identifiant dans ce tournoi (E10US003) → 404.

    Couvre l'identifiant inconnu **et** le scoreur d'un **autre** tournoi : du point de vue du
    tournoi de l'URL, un scoreur qui ne lui appartient pas n'existe pas davantage qu'un identifiant
    inventé — même parti que `DepartIntrouvable`.
    """

    code = "scoreur_introuvable"


class CodeScoreurInconnu(ApplicationError):
    """Connexion scoreur refusée : aucun scoreur ne porte ce code (E10US003). Traduite en 401.

    Même statut que `IdentifiantsInvalides` (un secret présenté ne correspond à rien) : le scoreur
    est identifié par **la personne** (son code), l'échec est un défaut d'authentification, pas un
    conflit d'état.
    """

    code = "code_scoreur_inconnu"


class CodePosteInconnu(ApplicationError):
    """Rattachement refusé : aucun poste ne porte ce code de cible (E04US001). Traduite en 401.

    Même statut que `CodeScoreurInconnu` : le poste est identifié par **le lieu** (le code de sa
    cible) ; un code qui ne correspond à rien est un défaut de rattachement, pas un conflit d'état.
    Le front purge alors le jeton local et redemande un rattachement (re-scan).
    """

    code = "code_poste_inconnu"


class RattachementTournoiTermine(ApplicationError):
    """Rattachement (ou session) d'un poste dont le tournoi est **terminé** (E04US001). → 409.

    C'est l'ancrage de la révocation « nouveau tournoi force le re-rattachement » (ADR-0029) :
    terminer un tournoi rend caducs tous ses jetons de poste. Conflit d'**état** (le tournoi n'est
    plus en mesure d'accueillir un poste), d'où 409 — le statut par défaut d'`ApplicationError`.
    """

    code = "rattachement_tournoi_termine"


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
