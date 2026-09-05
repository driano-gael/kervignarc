"""Erreurs du **moteur de phases** — comment le tournoi se déroule : l'enchaînement des
phases, ce que chacune prélève à la précédente, la construction de l'arbre de duels et
les politiques injectées.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 77 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from application.erreurs.base import ApplicationError


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


class DepartIntrouvable(ApplicationError):
    """Aucun départ (créneau) ne correspond à l'identifiant dans ce tournoi (E02US004) → 404.

    Couvre l'identifiant inconnu **et** le départ d'un **autre** tournoi : du point de vue du
    tournoi de l'URL, un créneau qui ne lui appartient pas n'existe pas davantage qu'un identifiant
    inventé — même parti que `CategorieHorsTournoi`, distinguer les deux apprendrait au client ce
    qui vit dans les tournois voisins.
    """

    code = "depart_introuvable"


class InscriptionIntrouvable(ApplicationError):
    """Aucune inscription ne correspond à l'identifiant demandé (E02US009) → 404."""

    code = "inscription_introuvable"


class DeplacementInvalide(ApplicationError):
    """Ajustement de placement refusé : le déplacement/échange violerait une contrainte (E03US004).

    **Un refus, pas un signalement** → 409. Couvre le déplacement qui déborde un budget de cible
    (capacité, espace, partage de carton, hauteur — ADR-0022/0024), l'échange dont l'un des deux ne
    tient pas à la place de l'autre (refus **en bloc**, état inchangé), le dépôt sur une case
    occupée, une cible inexistante, ou un archer **sans blason**. Le message dit **quelle**
    contrainte bloque, sans détail interne (règle 5).
    """

    code = "deplacement_invalide"


class ReplacementNonConfirme(ApplicationError):
    """Régénération **massive** du plan non confirmée (E12US007, ADR-0040) → 409.

    **Un signalement chiffré, pas un refus** : régénérer écrase le placement de tous les archers,
    et des scores existent déjà. Côté UI il faut **taper un mot** (`REPLACER`) ; à la frontière API
    le serveur n'exige que le booléen — il ne connaît pas la copie d'UI (ADR-0040 §4). ⚠️ À la
    différence des confirmations aveugles (DETTE-007), le décompte est **recalculé au commit**,
    jamais cru sur parole : `details` porte les chiffres frais.
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


class FormatIntrouvable(ApplicationError):
    """Aucun format de tournoi ne correspond à l'identifiant demandé (E01US023) → 404."""

    code = "format_introuvable"


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


class PhasePasUneQualification(ApplicationError):
    """L'étape désignée existe mais n'est **pas** une qualification (E05US025) → 409.

    Pendant symétrique de `PhasePasUnTableau`. Régler un barème ou un grain de validation sur une
    étape de tableau n'a pas de sens : ce sont les réglages d'un tir en séries. L'étape existant
    bien, c'est un conflit d'état et non un 404. Cette erreur naît avec la **désignation** de
    l'étape : tant que le barème se réglait « du tournoi », il n'y avait rien à désigner de
    travers.
    """

    code = "phase_pas_une_qualification"


class PhasePasUnTableau(ApplicationError):
    """La phase existe mais n'est **pas** une élimination directe (E03US009) → 409.

    Le plan de duels (placer les duellistes côte à côte) n'a de sens que pour une phase de
    **tableau** (`TypePhase.ELIMINATION_DIRECTE`) : la demander sur une qualification ou un barrage
    est un conflit d'état, pas un 404 (la phase existe bien) — même famille que
    `TransitionStatutInvalide`.
    """

    code = "phase_pas_un_tableau"


class RegenerationSurTourEnTir(ApplicationError):
    """Régénérer le plan d'un tour dont un duel porte **déjà un tir** (E03US012) → 409.

    ⚠️ **La justification d'origine est tombée.** Tant que le plan ne posait que le tour 1,
    « régénérer » ne pouvait rien perturber : aucun duel n'avait encore tiré, d'où l'absence
    d'alerte d'impact (E12US007, ADR-0048). Depuis que le plan suit le tour **qui se joue**,
    régénérer redistribuerait des archers **sur la butte**, et effacerait les poses des duels déjà
    tirés du tour. Un tir enregistré — validé ou non — est donc un conflit d'état.
    """

    code = "regeneration_sur_tour_en_tir"


class PhasePasDesPoules(ApplicationError):
    """La phase existe mais n'est **pas** une phase de poules (E05US023) → 409.

    Jumeau de `PhasePasUnTableau`, et le fait qu'il en faille un second est le symptôme même
    qu'ADR-0083 traite : chaque décor de saisie refuse ce qui n'est pas le sien. La différence est
    qu'ici le refus est **dérivé du contrat de phase** au lieu d'être écrit à la main.
    """

    code = "phase_pas_des_poules"


class PhasePasUnBigShootOff(ApplicationError):
    """La phase existe mais n'est **pas** un Big Shoot Off (E05US028) → 409.

    Troisième jumeau de `PhasePasUnTableau`, et le troisième n'est **pas** le signal d'un remède
    structurel : ce qui serait dupliqué, ce serait la **table** des types admis — or elle est
    dérivée du registre depuis E05US023, donc il ne reste ici qu'un nom d'erreur par décor. Trois
    noms distincts valent mieux qu'un « type de phase incorrect » qui n'aide personne.
    """

    code = "phase_pas_un_big_shoot_off"


class PhasePasUnSuisse(ApplicationError):
    """La phase existe mais n'est **pas** un système suisse (E05US026) → 409.

    Quatrième jumeau de `PhasePasUnTableau`. Même justification qu'à `PhasePasUnBigShootOff` : ce
    qui serait fâcheux à dupliquer est la **table** des types admis, dérivée du registre de
    contrat. Il ne reste ici qu'un nom d'erreur par décor, et c'est ce qui permet de lire « cette
    phase n'est pas un système suisse » plutôt qu'un message générique.
    """

    code = "phase_pas_un_suisse"


class PhasePasUneColline(ApplicationError):
    """La phase existe mais n'est **pas** une colline (E05US027) → 409.

    Cinquième et **dernier** jumeau de `PhasePasUnTableau` : la colline est le dernier format
    d'E05US015 à recevoir son service. ⚠️ **Cinq jumeaux ne déclenchent pas le seuil du remède
    structurel**, et il faut le dire puisque le § *Dette* le fixe à la 3ᵉ occurrence : le critère y
    est « invariant déjà dupliqué », or aucun ne l'est ici. Chaque classe ne porte qu'un `code` et
    un texte — les fondre rendrait le message générique sans supprimer une ligne de règle.
    """

    code = "phase_pas_une_colline"


class MancheIntrouvable(ApplicationError):
    """Aucune manche de ce numéro dans ce Big Shoot Off (E05US028) → 404.

    Cousin de `RencontreIntrouvable`, même cause : l'écran est resté ouvert pendant que l'effectif
    bougeait, et la manche cliquée n'existe plus — la liste de sortants s'écourte quand la lice se
    vide (« on joue tant que la manche est possible »). Un 404 est la bonne réponse : la tablette
    recharge et retrouve un état cohérent.
    """

    code = "manche_introuvable"


class ArcherHorsBigShootOff(ApplicationError):
    """Cet archer ne fait pas partie de ce Big Shoot Off (E05US028) → 404.

    ⚠️ **Erreur ajoutée à la revue d'E05US028**, où ce refus empruntait le code de
    `MancheIntrouvable`. Aucune manche n'est pourtant en cause : c'est la **population** de la phase
    qui ne contient pas cet archer. Un client qui aiguille sur le `code` — et c'est la raison d'être
    du champ (règle 5) — affichait donc « cette manche n'existe pas » à un archer qui n'était
    simplement pas finaliste.
    """

    code = "archer_hors_big_shoot_off"


class ArcherDejaSorti(ApplicationError):
    """Cet archer est sorti du Big Shoot Off : il ne tire plus (E05US028) → 409.

    ⚠️ Ce refus empruntait `PhasePasReglee`, dont le code signifie « l'organisateur doit régler la
    phase à l'atelier » : le même code sortait du même endpoint pour deux situations aux
    corrections **opposées** — aller régler la phase, ou recharger parce que cet archer est
    éliminé. 409 et non 404 : l'archer **existe** dans cette phase, il y a même un rang — c'est son
    état qui interdit l'écriture, pas son absence.
    """

    code = "archer_deja_sorti"


class RencontreIntrouvable(ApplicationError):
    """Aucune rencontre de ce numéro dans cette phase de poules (E05US023) → 404.

    Distinct de `MatchNonJouable` : ici le numéro ne désigne rien du tout. Le cas se produit quand
    la composition a changé sous un écran resté ouvert — l'effectif a baissé, la phase compte moins
    de rencontres, et le numéro cliqué n'existe plus. Un 404 est alors la bonne réponse : la
    tablette rechargera et retrouvera un état cohérent.
    """

    code = "rencontre_introuvable"


class PhasePasReglee(ApplicationError):
    """La phase de poules existe mais sa **taille de poule** n'est pas réglée (E05US023) → 409.

    Distinct de `PhasePasDesPoules` parce que la correction l'est aussi : ici le type est bon, il
    manque un paramètre que l'organisateur fixe à l'atelier — confondre les deux enverrait chercher
    la faute au mauvais endroit. C'est la contrepartie assumée du brouillon d'ADR-0063 : le type se
    choisit avant ses paramètres, donc le refus arrive au moment d'en jouer une.
    """

    code = "phase_pas_reglee"


class PrelevementEnAttente(ApplicationError):
    """La phase prélève des places que sa source n'a **pas encore décidées** (E05US024) → 409.

    Un tableau de 8 non commencé porte ses huit archers sur la plage `[1..8]` : aucune des huit
    places n'est attribuée. Une consolante qui déclare « les rangs 5 à 8 » demande donc quatre
    places qui n'existent pas — et le moteur y répondait en départageant sur le rang de
    qualification (ADR-0081). ⚠️ **Distinct d'un prélèvement inerte** (`DETTE-033`) et d'une phase
    **sans source** : les trois se ressemblaient, et les confondre rendait le défaut silencieux.
    """

    code = "prelevement_en_attente"

    def __init__(self, message: str, ordre_source: int) -> None:
        super().__init__(message)
        # L'ordre de la phase attendue voyage avec l'erreur : c'est ce que la vue publique affiche
        # (« en attente de la phase 2 »), et le reconstituer en parsant le message serait le genre
        # de couplage au texte que la règle 5 proscrit.
        self.ordre_source = ordre_source
        # …et il passe aussi par le canal **déjà existant** `details`, que la frontière API publie
        # dans `{code, message, details?}` (règle 5, inauguré par `ReplacementNonConfirme`). Sans
        # lui, un client recevant le 409 côté saisie ou plan de cibles devait parser le message
        # pour savoir quoi attendre — exactement ce que le commentaire ci-dessus dit vouloir
        # éviter, l'attribut nu n'étant lu que par `ServiceTableauxPublics` (relevé en revue).
        self.details = {"ordre_source": ordre_source}


class DerouleCyclique(ApplicationError):
    """Une chaîne de sources **boucle** : une phase se prélève elle-même (E05US024) → 409.

    Inatteignable par la composition (`verifier_sequence` exige une source antérieure) mais
    atteignable par une base incohérente. ⚠️ **Type dédié, et non `PhaseIntrouvable`** :
    `ServicePalmares._resultat` attrape déjà celui-ci pour écarter une phase disparue, si bien que
    le refus devenait une **omission muette** sur l'écran de salle. Elle reste avalée par deux
    filets larges — sur l'onglet public, un déroulé cyclique reste un tableau absent.
    """

    code = "deroule_cyclique"


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


class EffectifSimulationInvalide(ApplicationError):
    """L'effectif demandé pour simuler un format sort des bornes de service (E01US024) → 400.

    Ni règle métier (le domaine ne connaît pas de nombre maximal d'archers) ni conflit d'état : une
    **borne de service**. Simuler joue le tournoi entier sur le thread de la requête, et l'effectif
    vient du client — sans plafond, une valeur absurde immobiliserait le serveur. Seule erreur
    applicative en **400** : les autres sont 401/403/404/409 (`api/erreurs.py`).
    """

    code = "effectif_simulation_invalide"


class FormatNonSimulable(ApplicationError):
    """Le format s'applique à un tournoi, mais le rejeu ne sait pas le dérouler (E01US024) → 400.

    Un seul motif aujourd'hui : **aucune phase de qualification**, donc aucun barème d'où le bot
    tirerait des volées. Ce n'est pas une incohérence du format — `ServiceFormats.appliquer`
    l'accepte —, c'est une limite du substrat de simulation. Distincte de
    `PhaseQualificationAbsente` (404), qui parle d'un **tournoi** réel : ici il n'y en a aucun.
    """

    code = "format_non_simulable"


class ArretIntrouvable(ApplicationError):
    """Aucun arrêt **relançable** ne correspond à cet identifiant dans ce créneau (E05US033) → 404.

    Trois cas réunis parce qu'ils appellent le même geste — recharger l'écran : identifiant
    inconnu, arrêt d'un **autre** créneau, ou arrêt **déjà levé** (le cas courant en salle : deux
    tablettes, ou un double-clic). ⚠️ Un arrêt encore `ARME` est également introuvable au sens de
    ce refus : la coupe est décidée mais pas faite, il n'y a rien à relancer.
    """

    code = "arret_introuvable"
