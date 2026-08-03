"""Erreurs du **tir** — ce qui se passe sur le pas de tir et ce qu'on en note : séries et
volées de qualification, duels et manches, barrages, formats de départage (poules, Big
Shoot Off, système suisse, colline), forfaits.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 94 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from domain.erreurs.base import DomainError

# --- duels : saisie et scoring (E04US013, ADR-0049) --------------------------------------------


class BaremeDuelInvalide(DomainError):
    """Le barème d'un duel est incohérent (E04US013) : nombre de manches / flèches < 1, ou un
    seuil de points de set inatteignable (`> 2 x nb_manches`). Un barème est une **structure**
    paramétrée (ADR-0049) — on refuse une structure impossible à disputer."""

    code = "bareme_duel_invalide"


class NumeroMancheInvalide(DomainError):
    """Le rang d'une manche de duel sort du barème (`1 <= numero <= nb_manches`, E04US013).

    Symétrique de `NumeroVoleeInvalide` pour la qualification : le serveur est autoritaire, une
    manche hors barème fausserait le décompte des points de set (§7)."""

    code = "numero_manche_invalide"


class DuelDejaTranche(DomainError):
    """On ajoute une manche à un duel **déjà gagné** (E04US013).

    Le système de sets s'arrête dès qu'un camp atteint le seuil (6 pts FFTA) : tirer une manche de
    plus n'a pas de sens (§6.2). La ré-édition d'une manche **déjà saisie** reste permise tant que
    le duel n'est pas validé — c'est l'**ajout** d'une manche superflue qui est refusé."""

    code = "duel_deja_tranche"


class BarrageNonRequis(DomainError):
    """Un barrage est saisi alors que le duel n'est **pas** à égalité de sets (E04US013, §8.2).

    Le tir de barrage ne se dispute qu'à égalité (5-5 en individuel) ; le proposer autrement
    court-circuiterait le résultat des manches."""

    code = "barrage_non_requis"


class BarrageIndecis(DomainError):
    """Le barrage reste à égalité de flèche **sans** désignation du plus près du centre (E04US013).

    §8.2 : à score de flèche égal, on départage « au plus près du centre » — un jugement que
    l'application **ne mesure pas**. Le scoreur doit **désigner** le vainqueur ; sans quoi le duel
    resterait indécidable."""

    code = "barrage_indecis"


class DuelIncomplet(DomainError):
    """On valide un duel dont le vainqueur n'est **pas encore** connu (E04US013).

    La validation (grain fin de duel) suppose le duel **tranché** : toutes les manches nécessaires
    saisies, et l'éventuel barrage résolu. Un duel en cours ne se valide pas."""

    code = "duel_incomplet"


class DuelVerrouille(DomainError):
    """Tentative d'écrire sur un duel **validé** (E04US013).

    Après validation (au nom du scoreur), le duel est verrouillé — son vainqueur est transmis au
    tableau. Toute nouvelle saisie de manche ou de barrage est refusée (pas de correction tracée à
    ce stade, hors périmètre de cette US)."""

    code = "duel_verrouille"


class ScoreInvalide(DomainError):
    """La valeur d'un score sort de la plage autorisée pour une flèche (0 à 10)."""

    code = "score_invalide"


class NumeroVoleeInvalide(DomainError):
    """Le numéro (rang) d'une volée n'est pas un entier `>= 1` (E04US002)."""

    code = "numero_volee_invalide"


class NombreFlechesVoleeInvalide(DomainError):
    """Le nombre de flèches d'une volée ne correspond pas au barème de la phase (E04US002).

    Le barème (E01US009) fixe combien de flèches compte une volée ; une volée d'un autre compte est
    refusée à la saisie — distinct de `NombreFlechesParVoleeInvalide`, qui protège le **barème**,
    quand celle-ci protège une **volée saisie** contre ce barème.
    """

    code = "nombre_fleches_volee_invalide"


class ValeurHorsBlason(DomainError):
    """Une valeur saisie n'est pas une zone admise du blason tiré (E04US002, `Blason.zones`).

    Le pavé de saisie se déduit du **blason** et non du barème : sur un triple 40 les valeurs 5 → 1
    n'existent pas (référentiel §4.4). Une valeur hors des `zones_admises` est donc refusée.
    """

    code = "valeur_hors_blason"


class VoleeVerrouillee(DomainError):
    """Tentative de modifier par simple saisie une volée déjà validée (E04US002).

    Après validation, une volée est verrouillée : le seul chemin d'écriture est la **correction
    tracée** (rôle habilité, `Serie.corriger_volee`), pas la ré-saisie.
    """

    code = "volee_verrouillee"


class VoleeNonVerrouillee(DomainError):
    """Tentative de corriger une volée qui n'est pas verrouillée (E04US002).

    La correction tracée ne vise que le **verrouillé** ; une volée en cours se modifie par saisie
    ordinaire (`Serie.saisir_volee`), sans trace d'audit.
    """

    code = "volee_non_verrouillee"


class VoleeIntrouvable(DomainError):
    """Aucune volée de ce numéro dans la série (E04US002) — corriger n'est pas créer."""

    code = "volee_introuvable"


class SerieIncomplete(DomainError):
    """Validation « fin de série » demandée avant que toutes les volées du barème soient saisies."""

    code = "serie_incomplete"


class RienAValider(DomainError):
    """Aucune volée à valider : ni lot complet du grain, ni reliquat de fin de barème (E04US002)."""

    code = "rien_a_valider"


class NomIntervenantInvalide(DomainError):
    """Le nom de qui valide ou corrige une volée est vide (après normalisation, E04US002).

    Une volée verrouillée **nomme** son validateur (l'équivalent numérique de la signature, FFTA
    B.6.1.1) : un verrou sans nom serait une signature blanche. Le domaine défend cet invariant
    lui-même, sans l'emprunter à la couche audit.
    """

    code = "nom_intervenant_invalide"


class DeclarantForfaitInvalide(DomainError):
    """Le déclarant d'un forfait est vide (après normalisation, E04US015).

    Le forfait est **attribué** (comme l'audit a un auteur) : le nom de qui l'a prononcé — scoreur
    ou admin — fige *qui* décide qu'un archer ne concourt plus. Sans lui, la déclaration ne se
    rattache à personne et l'annulation, réversible, perd sa trace.
    """

    code = "declarant_forfait_invalide"


class HorodatageForfaitInvalide(DomainError):
    """L'horodatage d'un forfait n'est pas un instant **UTC** *aware* (E04US015).

    Même invariant que l'audit (`HorodatageAuditInvalide`) : un `datetime` **naïf** ou **aware
    non-UTC** serait stocké sans fuseau puis relu comme de l'UTC, faisant **mentir** la date du
    forfait. On ferme ce chemin **à la construction** plutôt que laisser une horloge fautive
    corrompre le « quand » d'un acte réversible.
    """

    code = "horodatage_forfait_invalide"


class ConfigurationPouleInvalide(DomainError):
    """Les paramètres d'une phase de **poules** ne décrivent pas un tournoi jouable (E05US015).

    Nombre de poules < 1, plus de poules que de participants, barème de points incohérent (une
    victoire ne peut pas rapporter moins qu'un nul), nombre de qualifiés par poule supérieur à
    d'adversaires disponibles, rencontre fournie deux fois. Les contrôles qui ne dépendent que du
    réglage sont faits à la **composition** ; ceux qui exigent l'effectif réel (nombre de qualifiés,
    rencontres par archer) le sont à l'appel, faute de connaître les participants plus tôt. Dans les
    deux cas on refuse plutôt que de produire un classement de poule indéfendable.
    """

    code = "configuration_poule_invalide"


class ConfigurationBigShootOffInvalide(DomainError):
    """Les paramètres d'un **Big Shoot Off** ne décrivent pas une finale jouable (E05US015).

    `restants` (le K de la règle du club, référentiel §10.1) doit être ≥ 1 et **strictement
    inférieur** au nombre d'entrants — à `K = N` personne n'est jamais éliminé et la phase ne se
    termine pas. Volées et flèches par volée sont ≥ 1.
    """

    code = "configuration_big_shoot_off_invalide"


class ConfigurationSuisseInvalide(DomainError):
    """Les paramètres d'un **système suisse** ne décrivent pas un tournoi appariable (E05US015).

    Nombre de rondes < 1, ou supérieur à ce que l'effectif permet sans ré-affrontement : à N
    participants, chacun a N-1 adversaires possibles, donc au-delà de N-1 rondes l'appariement sans
    rematch est **impossible par construction**. On le dit à la composition plutôt que de bloquer
    à la ronde 6 le jour J.
    """

    code = "configuration_suisse_invalide"


class ConfigurationCollineInvalide(DomainError):
    """Les paramètres d'une phase de **colline** (King of the Hill / Ladder) sont incohérents
    (E05US015).

    Nombre de manches < 1, ou portée de défi < 1 ou ≥ à l'effectif : une portée qui couvre toute la
    colline transforme le format en « n'importe qui défie n'importe qui », ce qui n'est plus ni un
    King of the Hill ni un Ladder.
    """

    code = "configuration_colline_invalide"


class ConfigurationBarrageInvalide(DomainError):
    """Les paramètres d'un **barrage de tir** contredisent le règlement (E05US015, §8.2).

    Le barrage individuel se tire à **1 flèche** et le barrage par équipe à **3** (une par archer,
    art. B.6.5.2.2) : un nombre de flèches différent n'est pas un réglage mais une autre épreuve.
    Un barrage oppose par ailleurs **au moins deux** tireurs — départager un ex æquo d'une seule
    personne n'a pas d'objet.
    """

    code = "configuration_barrage_invalide"


class AppariementImpossible(DomainError):
    """Aucun appariement sans ré-affrontement n'a pu être composé pour cette ronde (E05US015).

    **Incident de déroulé, pas défaut de configuration** — et c'est pourquoi ce code est distinct de
    `ConfigurationSuisseInvalide` : la réaction attendue n'est pas « recompose ta phase » mais
    « accepte de rejouer une rencontre, ou arrête-toi à cette ronde ». Les confondre obligerait le
    client à lire le message pour savoir quoi proposer à l'organisateur.

    L'appariement du système suisse est **glouton** (ADR-0062, DETTE-027) : il peut échouer là où
    une solution existait. On le dit franchement plutôt que de rejouer une rencontre en silence.
    """

    code = "appariement_impossible"


class ScoreDeMancheManquant(DomainError):
    """Un participant encore en lice n'a pas de score pour la manche à conclure (E05US015).

    **Saisie incomplète**, pas configuration fautive. La distinction compte : un score absent n'est
    **pas** un score nul, et traiter l'absence comme un zéro éliminerait un archer sur une donnée
    non saisie — l'erreur qu'on ne voit qu'après coup, le jour J.
    """

    code = "score_de_manche_manquant"


class BarrageRequisAvantQualification(DomainError):
    """Un rang partagé tombe sur la barre de qualification d'une poule (E05US015, §10.1).

    **Ce n'est pas une erreur mais une action à proposer** : « barrage si nécessaire », dernier
    terme de la règle de départage. Qualifier « les deux premiers » quand les rangs 2 et 3 sont à
    égalité reviendrait à qualifier sur l'ordre d'affichage — donc sur le rang de qualification
    d'origine, qui n'a plus cours en poule. Le code est distinct de `ConfigurationPouleInvalide`
    pour que le client sache faire tirer au lieu d'inviter à recomposer la phase.
    """

    code = "barrage_requis_avant_qualification"
