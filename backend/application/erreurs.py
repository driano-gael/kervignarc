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
    """Ajustement demandé alors qu'aucun gabarit n'est appliqué au tournoi (E01US008) → 404.

    Il faut d'abord **appliquer** un gabarit modèle au tournoi.
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
