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
    """Transition de cycle de vie impossible depuis l'état courant (E01US002, E01US017) → 409.

    Le graphe des sept statuts ([ADR-0026] §2) n'autorise qu'un sous-ensemble d'arêtes : passer
    `prêt` un tournoi déjà démarré, reprendre un tournoi qui n'est pas en pause, archiver un
    tournoi non terminé, annuler un tournoi terminé… — tout le reste est refusé ici. L'agrégat ne
    porte que la valeur ; c'est le service qui arbitre l'enchaînement (ADR-0007/0026 §4).
    """

    code = "transition_statut_invalide"


class TournoiSansDepart(ApplicationError):
    """Passage à `prêt` refusé : le tournoi n'a **aucun départ** (créneau) (E02US010) → 409.

    **Un refus, pas un signalement** (famille de `TransitionStatutInvalide`) : un tournoi se joue
    sur des créneaux ; sans au moins un départ, il n'y a **rien à lancer** ni personne à placer. La
    garde vit sur `vers_pret` (l'entrée de la zone « préparé ») ; l'invariant tient ensuite parce
    qu'on ne peut plus retirer le **dernier** départ d'un tournoi non-brouillon
    (`DernierDepartNonSupprimable`). C'est une **première brique** de la garde de complétude de
    préparation ([ADR-0026] §2) — catégories, blasons, gabarit, barème restent à ajouter par une
    tranche ultérieure. Conflit d'**état**, d'où 409.
    """

    code = "tournoi_sans_depart"


class TournoiEnCoursNonSupprimable(ApplicationError):
    """Suppression refusée : le tournoi est `en_cours` ou `en_pause` (E01US002, E01US017) → 409.

    Il faut d'abord le **terminer** (ou l'**annuler** s'il est abandonné) ; un tournoi `brouillon`,
    `prêt`, `terminé` ou `annulé` reste supprimable. La suppression d'un `archivé` relève, elle, du
    verrou de lecture seule (`TournoiArchiveNonModifiable`) — [ADR-0026] §1.
    """

    code = "tournoi_en_cours_non_supprimable"


class TournoiArchiveNonModifiable(ApplicationError):
    """Écriture refusée sur un tournoi `archivé` — lecture seule définitive (E01US017) → 409.

    `archivé` est le **verrou total** ([ADR-0026] §1) : ni édition des métadonnées, ni suppression,
    ni transition (c'est un état terminal atteint depuis `terminé`). On ne dé-archive pas — la
    réouverture reste différée. Conflit d'**état**, d'où 409.
    """

    code = "tournoi_archive_non_modifiable"


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


class DernierDepartNonSupprimable(ApplicationError):
    """Suppression refusée : c'est le **dernier** départ d'un tournoi **non-brouillon** (E02US010)
    → 409.

    **Un refus, pas un signalement** : un tournoi `prêt`, `en_cours`, `en_pause` ou `terminé` a été
    validé comme ayant au moins un créneau (garde `TournoiSansDepart` sur `vers_pret`). Lui retirer
    son dernier départ le laisserait sans rien à jouer tout en restant hors brouillon — un état
    incohérent que l'invariant « ≥ 1 départ dès qu'on quitte le brouillon » interdit. Pour repartir
    de zéro depuis `prêt`, l'admin **revient en brouillon** (`revenir_brouillon`), où les créneaux
    redeviennent librement supprimables ; depuis un statut terminal (`terminé`/`annulé`/`archivé`)
    la configuration est figée, le dernier départ y reste définitivement en place. Sur un
    `brouillon`, supprimer le dernier départ reste permis (le tournoi n'est pas encore engagé).
    Conflit d'**état**, d'où 409.
    """

    code = "dernier_depart_non_supprimable"


class DepartEnCoursNonConfirme(ApplicationError):
    """Édition/suppression d'un départ **lancé ou clos** non confirmée (E12US008) → 409.

    **Un signalement chiffré, pas un refus** — même famille que `ReplacementNonConfirme`
    (ADR-0040) : un créneau *ouvert* (aucun score consigné) se modifie et se supprime librement,
    mais dès qu'une **flèche y a été tirée** (état *lancé*), et *a fortiori* quand toutes ses séries
    sont closes (*clos*), le toucher risque de détruire une **session de tir en cours ou finie**.
    Le geste demande donc une confirmation explicite (`modifier(..., confirme_cycle=True)` /
    `supprimer(..., confirme_cycle=True)`).

    À la différence des confirmations aveugles de la famille `DepartAvecInscriptions` (DETTE-007),
    l'état est **dérivé au moment d'agir** d'un fait réel (scores présents, séries closes), jamais
    saisi ni cru sur parole : `details` porte l'**état** et le **nombre d'archers ayant tiré** —
    canal `details` du format `{code, message, details?}` (règle 5), comme `ReplacementNonConfirme`.

    Sur **suppression**, la confirmation de cycle **subsume** `DepartAvecInscriptions`
    (un créneau lancé porte forcément des inscriptions) : confirmer qu'on détruit une session de tir
    couvre *a fortiori* les inscriptions. Un créneau *ouvert* garde exactement le comportement
    E02US009 (seul `DepartAvecInscriptions` s'y applique) — non-régression.
    """

    code = "depart_en_cours_non_confirme"

    def __init__(self, message: str, *, etat: str, archers_ayant_tire: int) -> None:
        super().__init__(message)
        # `details` est lu tel quel par `_sur_erreur_application` (frontière API) et sérialisé dans
        # la réponse — le front y retrouve l'état chiffré (lancé/clos, combien ont tiré) sans le
        # reconstituer.
        self.details = {"etat": etat, "archers_ayant_tire": archers_ayant_tire}


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


class FusionImpossible(ApplicationError):
    """Fusion de doublons **structurellement** impossible (E02US005) → 409.

    **Un refus, pas un signalement** (famille de `DejaInscrit`) : aucun drapeau ne le lève, la
    demande n'a pas de sens. Deux causes, toutes deux constatées avant d'écrire :

    - fusionner une fiche **avec elle-même** (gagnant = perdant) — il n'y a rien à fusionner ;
    - fusionner deux fiches de **tournois différents** — ce sont deux inscriptions distinctes,
      pas un doublon (l'homonymie se juge dans le tournoi, comme à l'inscription, E02US002).
      Réassigner inscriptions et séries d'un tournoi à l'autre romprait leur cloisonnement.
    """

    code = "fusion_impossible"


class FusionArchersEngages(ApplicationError):
    """Fusion refusée : les **deux** fiches ont déjà une saisie (série) au tournoi (E02US005) → 409.

    **Un signalement, pas un début d'exécution** (esprit ADR-0015) : fusionner mêlerait deux séries
    de volées sur le même `(tournoi, archer)` — la contrainte `UNIQUE(tournoi_id, archer_id)` d'une
    part, l'ambiguïté « quelles volées garder ? » d'autre part. Le doublon se règle **à
    l'inscription, avant que le tournoi tire** (arbitrage du 22/07/2026) ; ce cas n'est donc pas
    nominal. Aucun drapeau ne le lève : mêler des scores en silence détruirait des flèches. Si une
    seule des deux fiches a tiré, la fusion passe (la série est réassignée sans collision).
    """

    code = "fusion_archers_engages"


class InscriptionIntrouvable(ApplicationError):
    """Aucune inscription ne correspond à l'identifiant demandé (E02US009) → 404."""

    code = "inscription_introuvable"


class InscriptionPayeeARembourser(ApplicationError):
    """Désinscription suspendue : l'inscription est **payée**, sa suppression ouvrira un
    remboursement (E08US005, ADR-0057) → 409.

    **Un signalement chiffré, pas un refus** — même famille que `DepartEnCoursNonConfirme` : la
    désinscription est **confirmable**, pas interdite. Une inscription non payée (ou d'un créneau
    gratuit) se désinscrit **librement** (comportement E02US009 inchangé) ; mais désinscrire une
    inscription **payée** efface une somme encaissée, qui deviendra un **remboursement à traiter**.
    L'admin doit le voir avant de trancher — d'où ce signalement, levé par
    `ServiceInscriptions.desinscrire(confirme=True)`, qui supprime **et** ouvre le remboursement
    dans
    la même transaction (atomicité, ADR-0057).

    `details` porte le **montant** à rembourser (centimes) et le **nom** de l'archer, calculés au
    moment d'agir — canal `details` du format `{code, message, details?}` (règle 5), comme
    `DepartEnCoursNonConfirme`. Symétrique de `DepartAvecInscriptions`, qui joue le même rôle côté
    suppression d'un **départ** entier.
    """

    code = "inscription_payee_a_rembourser"

    def __init__(self, message: str, *, montant_centimes: int, archer: str) -> None:
        super().__init__(message)
        # Lu tel quel par `_sur_erreur_application` (frontière API) : le front y retrouve le montant
        # et l'archer pour composer sa demande de confirmation, sans les reconstituer.
        self.details = {"montant_centimes": montant_centimes, "archer": archer}


class RemboursementIntrouvable(ApplicationError):
    """Aucun remboursement ne correspond à l'identifiant demandé (E08US005) → 404."""

    code = "remboursement_introuvable"


class RemboursementDejaTraite(ApplicationError):
    """Traitement refusé : le remboursement est **déjà** remboursé ou reporté (E08US005) → 409.

    **Un refus, pas un signalement** : un remboursement traité est **terminal** (marquer «
    remboursé »
    ou « reporté » clôt le poste). Le re-marquer réécrirait sa date de traitement, brouillant la
    trace d'un mouvement d'argent — conflit d'**état**, comme les transitions de statut de tournoi
    (`TransitionStatutInvalide`), d'où le 409 porté par le **service** (l'entité, pure, ne connaît
    pas l'intention de l'appelant). Le front n'offre le geste que sur les postes `à_rembourser` ;
    cette garde est le filet serveur (autorité, règle 6).
    """

    code = "remboursement_deja_traite"


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


class ReplacementNonConfirme(ApplicationError):
    """Régénération **massive** du plan non confirmée (E12US007, [ADR-0040]) → 409.

    **Un signalement chiffré, pas un refus** — famille d'`ArcherEngage`/`DepartAvecInscriptions`
    (ADR-0016/0018) : régénérer le plan écrase le placement de tous les archers, et **des scores
    existent déjà** (niveau `MASSIF`). Le geste demande donc une confirmation explicite
    (`regenerer(..., confirme=True)`) ; côté UI, il faut **taper un mot** (`REPLACER`) — friction
    humaine impossible par réflexe. Ici, à la frontière API, le serveur n'exige que le booléen : il
    ne connaît pas la copie d'UI (couplage évité, ADR-0040 §4).

    À la **différence** des confirmations aveugles de la famille (DETTE-007), le décompte est
    **recalculé au commit**, jamais cru sur parole : `details` porte les chiffres frais
    (`archers_deplaces`, `cibles_avec_scores`) — première utilisation du canal `details` du format
    `{code, message, details?}` (règle 5). L'action ne rejoint donc pas DETTE-007.
    """

    code = "replacement_non_confirme"

    def __init__(self, message: str, *, archers_deplaces: int, cibles_avec_scores: int) -> None:
        super().__init__(message)
        # `details` est lu tel quel par le gestionnaire `_sur_erreur_application` (frontière API) et
        # sérialisé dans la réponse — le client y retrouve l'impact chiffré sans le reconstituer.
        self.details = {
            "archers_deplaces": archers_deplaces,
            "cibles_avec_scores": cibles_avec_scores,
        }


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


class FormatIntrouvable(ApplicationError):
    """Aucun format de tournoi ne correspond à l'identifiant demandé (E01US023) → 404."""

    code = "format_introuvable"


class NomFormatDejaPris(ApplicationError):
    """Un format porte déjà ce nom dans la bibliothèque (E01US023) → 409.

    Le refus est **fonctionnel** : la contrainte `UNIQUE` de `format_tournoi.nom` n'est qu'un
    garde-fou d'intégrité en aval (même patron que `NomClubDejaPris`). Un homonyme n'est pas
    interdit par principe — il l'est parce qu'une bibliothèque où deux formats portent le même nom
    est une bibliothèque où l'organisateur ne sait plus lequel il applique.
    """

    code = "nom_format_deja_pris"


class BriqueHorsBibliotheque(ApplicationError):
    """Application demandée sur une brique qui n'est **pas** un modèle de bibliothèque → 409.

    Assembler un tournoi copie des **modèles** (`tournoi_id is None`, ADR-0060 §1). Viser la copie
    d'un autre tournoi recopierait le matériau d'une autre édition — ce qui n'est pas la promesse
    de l'atelier, et brouillerait la provenance sans que rien ne le signale.
    """

    code = "brique_hors_bibliotheque"


class NomBriqueDejaPris(ApplicationError):
    """Une brique de bibliothèque porte déjà ce nom (E01US023) → 409.

    Même patron que `NomClubDejaPris` et `NomFormatDejaPris`, et pour la même raison : l'assemblage
    et la promotion **dédoublonnent par le nom** (`_cle`). Deux modèles homonymes rendraient donc
    ces deux gestes non déterministes — un seul serait copié, et lequel des deux la promotion met à
    jour dépendrait de l'ordre du dépôt. Le refus à la création est ce qui rend la déduplication
    aval honnête.
    """

    code = "nom_brique_deja_pris"


class BriqueDejaEnBibliotheque(ApplicationError):
    """Promotion demandée sur une brique qui est **déjà** un modèle de bibliothèque → 409.

    La promotion fait remonter la **copie d'un tournoi** vers l'atelier (« cette modification est
    permanente », ADR-0060 §3). Promouvoir un modèle serait un geste sans objet : il n'a pas de
    modèle au-dessus de lui. Erreur distincte de `BriqueHorsBibliotheque` pour que le message dise
    laquelle des deux confusions a eu lieu.
    """

    code = "brique_deja_en_bibliotheque"


class PhasesEngagees(ApplicationError):
    """Application d'un format demandée alors qu'une phase du tournoi est déjà engagée → 409.

    Appliquer un format **remplace** la séquence de phases du tournoi. Tant que tout est `à venir`,
    c'est une reconfiguration anodine ; dès qu'une phase est démarrée, en pause ou terminée, ce
    serait jeter un déroulé **en cours** — avec les séries et les duels qui y pendent. Le refus est
    délibérément grossier (une seule phase engagée suffit à bloquer) : à ce stade, deviner ce que
    l'organisateur veut garder est plus dangereux que de lui rendre la main.
    """

    code = "phases_engagees"


class TournoiSansPhase(ApplicationError):
    """Promotion d'un format demandée sur un tournoi qui n'a aucune phase (E01US023) → 409.

    Il n'y a pas de déroulé à capturer : le format promu serait vide, et un format vide n'a rien à
    appliquer (`FormatSansEtape`).
    """

    code = "tournoi_sans_phase"


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


class PhaseIntrouvable(ApplicationError):
    """Aucune phase ne correspond à l'identifiant dans ce tournoi (E05US001) → 404.

    Couvre l'identifiant inconnu **et** la phase d'un **autre** tournoi : du point de vue du tournoi
    de l'URL, une phase qui ne lui appartient pas n'existe pas davantage qu'un identifiant inventé —
    même parti que `DepartIntrouvable` / `ScoreurIntrouvable`.
    """

    code = "phase_introuvable"


class PhasePasUnTableau(ApplicationError):
    """La phase existe mais n'est **pas** une élimination directe (E03US009) → 409.

    Le plan de duels (placer les duellistes côte à côte) n'a de sens que pour une phase de
    **tableau** (`TypePhase.ELIMINATION_DIRECTE`) : la demander sur une qualification ou un barrage
    est un conflit d'état, pas un 404 (la phase existe bien) — même famille que
    `TransitionStatutInvalide`.
    """

    code = "phase_pas_un_tableau"


class AucunDuelALancer(ApplicationError):
    """Le lancement d'un tour ne trouve **aucun duel prêt** à faire partir (E12US002) → 409.

    Le feu vert est **recalculé dans la file** au moment du lancement (jamais cru sur parole — même
    principe que `ReplacementNonConfirme`/E12US007) : un duel demandé par le front qui n'est plus
    **jouable** (source non validée, occupant inconnu) ou **sans cible attribuée** est écarté. Si,
    net, il ne reste rien à lancer, l'acte est un **conflit d'état** (rien à diffuser, aucune trace)
    — l'organisateur relance quand un duel le sera. Ce n'est pas un refus de principe (`P-3` :
    l'appli n'empêche rien), c'est l'absence de matière : aucun événement à émettre.
    """

    code = "aucun_duel_a_lancer"


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


class PhaseSourceReferencee(ApplicationError):
    """Suppression refusée : la phase est la **source** d'une autre phase (E05US001) → 409.

    **Un refus, pas un signalement** (famille de `ClubReference`/`BlasonReference`) : retirer une
    phase dont une autre tire ses participants romprait le peuplement de cette dernière. Il faut
    d'abord réaffecter ou retirer la phase consommatrice. Se distingue de la cohérence de séquence
    (levée en 422 à la construction) : ici, c'est un **conflit d'état** entre phases existantes.
    """

    code = "phase_source_referencee"


class PhaseQualificationNonSupprimable(ApplicationError):
    """Suppression refusée : la phase de qualification se gère via le barème (E05US001) → 409.

    La qualification naît et vit avec le **barème** (ADR-0011) ; la retirer par l'écran des phases
    l'**orphelinerait** (le barème n'aurait plus de phase porteuse) et casserait la saisie. Garde en
    profondeur : le front masque déjà l'action (`gereeAilleurs`), mais l'API ne doit pas l'ouvrir
    par une route directe (revue E05US001, axe D).
    """

    code = "phase_qualification_non_supprimable"


class ReordonnancementPhasesInvalide(ApplicationError):
    """Réordonnancement refusé : la liste fournie ne recouvre pas exactement les phases du tournoi
    (E05US001) → 409.

    Réordonner, c'est **permuter l'ensemble** des phases : la liste d'identifiants doit contenir
    chaque phase du tournoi une et une seule fois. Un identifiant manquant, en trop, en double ou
    étranger au tournoi rend l'opération ambiguë — refus net plutôt qu'un ordre partiel deviné.
    """

    code = "reordonnancement_phases_invalide"


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


class PosteIntrouvable(ApplicationError):
    """Aucun poste ne correspond à l'identifiant dans ce tournoi (E12US001) → 404.

    Couvre l'identifiant inconnu **et** le poste d'un **autre** tournoi : du point de vue du tournoi
    de l'URL, un poste qui ne lui appartient pas n'existe pas davantage qu'un identifiant inventé —
    même parti que `DepartIntrouvable` / `ScoreurIntrouvable`. Levée à la **révocation** admin d'un
    poste depuis la console de supervision.
    """

    code = "poste_introuvable"


class RattachementTournoiTermine(ApplicationError):
    """Rattachement (ou session) d'un poste dont le tournoi est **terminé** (E04US001). → 409.

    C'est l'ancrage de la révocation « nouveau tournoi force le re-rattachement » (ADR-0029) :
    terminer un tournoi rend caducs tous ses jetons de poste. Conflit d'**état** (le tournoi n'est
    plus en mesure d'accueillir un poste), d'où 409 — le statut par défaut d'`ApplicationError`.
    """

    code = "rattachement_tournoi_termine"


class ScoreurHorsTournoi(ApplicationError):
    """Un scoreur agit (valide/corrige) sur une série d'un **autre tournoi** que le sien. → 403.

    Le scoreur est **itinérant dans son tournoi** (`D-12`) : il valide n'importe quelle cible, mais
    de **son** tournoi seulement. Sa session est valide (identité établie), mais elle n'autorise pas
    à agir dans un tournoi voisin — la faille se rouvrirait en concurrence de tournois (intérieur +
    extérieur). **Refus, pas défaut d'authentification** : 403, comme `SaisieHorsCible` (le poste
    hors cible). L'admin, lui, n'a pas cette borne (E10US001).
    """

    code = "scoreur_hors_tournoi"


class DepartCourantNonDefini(ApplicationError):
    """Un poste tente de saisir (ou lister ses archers) sans avoir fixé son départ courant. → 409.

    ADR-0034 §1 : tant qu'aucun départ n'est fixé, le poste connaît son lieu mais **ne sait pas qui
    afficher** — refus **explicite**, jamais un affichage vide ambigu. Conflit d'**état** (le poste
    n'est pas en état de saisir), d'où 409 : le front doit d'abord fixer le départ (« mode départ »)
    avant d'afficher la grille. Distinct de `SaisieHorsCible` (403 : le départ *est* fixé, mais
    l'archer visé n'y est pas).
    """

    code = "depart_courant_non_defini"


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


class PeuplementTournoiDemarre(ApplicationError):
    """Peupler d'archers de test un tournoi **déjà démarré** est refusé (E15US001) → 409.

    Le jeu d'essai écrit de la **donnée réelle** : le peupler sur un tournoi `en_cours`, `en_pause`,
    `terminé` ou `archivé` injecterait des inscrits factices dans une compétition **vivante** (le
    sélecteur d'admin liste tous les tournois — un clic malencontreux suffit). On borne donc le
    peuplement aux tournois **avant démarrage** (`brouillon`/`prêt`), cohérent avec l'esprit
    d'EPIC-15 (« ne pollue jamais le réel ») et le garde-fou de la simulation éphémère à venir
    (E15US002). Instancier un scénario crée un tournoi `brouillon` neuf — ce chemin n'est pas borné.
    **Un refus, pas un signalement** (aucun drapeau ne le lève) : pour peupler, l'admin repart d'un
    tournoi de test. Conflit d'**état**, d'où 409.
    """

    code = "peuplement_tournoi_demarre"


class SimulationTournoiDemarre(ApplicationError):
    """Simuler (moteur éphémère) un tournoi **déjà démarré** est refusé (E15US002) → 409.

    La simulation rejoue le moteur (qualif → duels → classement) sur des adapters **in-memory**,
    sans rien persister (ADR-0054) : elle n'a de sens qu'**avant démarrage**, quand le déroulé n'a
    pas encore commencé pour de vrai. La lancer sur un tournoi `en_cours`, `en_pause`, `terminé`,
    `archivé` ou `annulé` mêlerait l'outil de démo/QA à une compétition **vivante ou figée** — même
    borne, même famille et même raison que `PeuplementTournoiDemarre` d'E15US001. Seuls
    `brouillon`/`prêt` sont simulables. L'arbitrage du CA (« terminé/archivé simulable ? ») est
    tranché **non** (ADR-0054 §4), cohérent avec l'invariant d'EPIC-15 « ne pollue jamais le réel ».

    **Un refus, pas un signalement** (aucun drapeau ne le lève) : conflit d'**état**, d'où 409.
    """

    code = "simulation_tournoi_demarre"


class SessionSimulationIntrouvable(ApplicationError):
    """Aucune session de simulation ne correspond à l'identifiant demandé (E15US003) → 404.

    Les sessions sont **éphémères, en mémoire** (ADR-0055 §1) : un identifiant inconnu (jamais créé,
    déjà arrêté, ou perdu au redémarrage du serveur) est un « introuvable », pas un conflit d'état.
    Le front repart alors d'un `démarrer`.
    """

    code = "session_simulation_introuvable"


class PilotageSimulationInvalide(ApplicationError):
    """Action de pilotage incompatible avec l'état du pilote (E15US003, ADR-0055 §2) → 409.

    Le pilote a trois états gardés : avancer (le bot) n'est permis qu'`en_cours`, saisir (l'humain)
    qu'`en_pause`, et rien n'est permis quand la session est `terminée`. Demander l'un hors de son
    état — reprendre une session déjà en cours, avancer une session en pause, saisir alors que le
    bot tient les commandes — est un **conflit d'état**, comme `TransitionStatutInvalide`.
    """

    code = "pilotage_simulation_invalide"


class UniteSimulationInvalide(ApplicationError):
    """La saisie manuelle ne désigne pas une unité jouable de la simulation (E15US003) → 409.

    En pause, l'humain saisit « à la place d'un rôle » : une volée pour un archer, un vainqueur pour
    un duel. Viser une unité qui n'a pas de sens — un archer hors tournoi, une volée hors barème ou
    déjà validée, un duel inexistant, tranché ou non encore jouable — est refusé (l'état reste
    inchangé). Distinct des erreurs de **valeurs** (nombre de flèches, zone hors blason), qui
    remontent du domaine en 422 : ici c'est le **ciblage** de l'unité qui est en cause.
    """

    code = "unite_simulation_invalide"


class ScenarioInconnu(ApplicationError):
    """Aucun scénario de jeu d'essai ne correspond à l'identifiant demandé (E15US001) → 404.

    Le catalogue des scénarios est **fermé** (`application.jeu_essai.CATALOGUE`) et le front puise
    ses choix dans `GET …/jeu-essai/scenarios` : un identifiant hors catalogue est un
    « introuvable », pas un conflit d'état. Même parti que `GabaritIntrouvable`.
    """

    code = "scenario_inconnu"


class ForfaitTournoiTermine(ApplicationError):
    """Déclarer ou annuler un forfait sur un tournoi **terminé** est refusé (`D-15`). → 409.

    Le forfait est réversible **tant que le tournoi n'est pas terminé** : une fois clos, les
    résultats sont figés — on ne rouvre pas un abandon ni une DSQ. Ce n'est pas un signalement (rien
    à confirmer) mais un **conflit d'état**, comme la suppression d'un tournoi en cours.
    """

    code = "forfait_tournoi_termine"


class EffectifSimulationInvalide(ApplicationError):
    """L'effectif demandé pour simuler un format sort des bornes de service (E01US024) → 400.

    Ce n'est **ni** une règle métier (le domaine ne connaît pas de nombre maximal d'archers) **ni**
    un conflit d'état : c'est une **borne de service**, comme le refus de matérialiser
    `frozenset(range(…))` dans `SourcePhase.intervalle`. Simuler joue le tournoi entier — volées
    puis duels — sur le thread de la requête, et l'effectif vient du client : sans plafond, une
    valeur absurde immobiliserait le serveur. En dessous de 2, il n'y a pas de tournoi à jouer.

    Seule erreur applicative en **400** : les autres sont 401/403/404/409 (cf. `api/erreurs.py`).
    """

    code = "effectif_simulation_invalide"


class FormatNonSimulable(ApplicationError):
    """Le format s'applique à un tournoi, mais le rejeu ne sait pas le dérouler (E01US024) → 400.

    Aujourd'hui, un seul motif : **aucune phase de qualification**, donc aucun barème d'où le bot
    tirerait des volées. Ce n'est **pas** une incohérence du format — `ServiceFormats.appliquer`
    l'accepte —, c'est une limite du substrat de simulation.

    Même famille que `EffectifSimulationInvalide` (**400**) : la requête est impossible *en soi*, et
    aucun changement d'état ne la rendrait acceptable. Distincte de `PhaseQualificationAbsente`
    (404), qui parle d'un **tournoi** réel : ici il n'y en a aucun, et ce 404 était un contresens.
    """

    code = "format_non_simulable"


class PosteNEstPasUnEcran(ApplicationError):
    """Une opération réservée aux écrans de salle vise un poste de cible (E07US004).

    Régler un déroulé de vues, imposer une vue, lire l'affichage courant : autant de gestes qui
    n'ont de sens que pour un écran. La garde n'est pas théorique — la console de supervision
    affiche cibles et écrans **côte à côte** (CA : « un écran figé ne se plaint pas »), donc
    l'identifiant d'une tablette est à portée de clic de celui d'un écran.

    Conflit d'**état** plutôt qu'absence : le poste existe bien, c'est sa nature qui ne convient pas
    — d'où un 409 à la frontière API, et non un 404 qui laisserait croire à un identifiant faux.
    """

    code = "poste_n_est_pas_un_ecran"
