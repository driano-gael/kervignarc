"""Erreurs du domaine (ADR-0007) — une règle métier est violée.

Racine `DomainError` : le domaine **ignore HTTP**. La traduction en réponse (HTTP 422,
code métier) se fait uniquement à la frontière API (`api/erreurs.py`).
"""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier. Chaque sous-classe porte un `code` stable."""

    code = "erreur_domaine"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NomTournoiInvalide(DomainError):
    """Le nom d'un tournoi est vide (après normalisation)."""

    code = "nom_tournoi_invalide"


class NomArcherInvalide(DomainError):
    """Le nom d'un archer est vide (après normalisation)."""

    code = "nom_archer_invalide"


class PrenomArcherInvalide(DomainError):
    """Le prénom d'un archer est vide (après normalisation, E02US002)."""

    code = "prenom_archer_invalide"


class NomClubInvalide(DomainError):
    """Le nom d'un club est vide (après normalisation)."""

    code = "nom_club_invalide"


class LibelleCategorieInvalide(DomainError):
    """Le libellé d'une catégorie est vide (après normalisation)."""

    code = "libelle_categorie_invalide"


class HauteurCentreInvalide(DomainError):
    """La hauteur du centre de l'or d'une catégorie n'est pas un entier strictement positif.

    Hauteur du sol au centre de l'or, en cm (E03US001, ADR-0022). Pilote la contrainte de
    placement « une butte, une hauteur » : 130 cm par défaut, 110 cm pour les U11 (référentiel §5).
    """

    code = "hauteur_centre_invalide"


class NomFormatInvalide(DomainError):
    """Le nom d'un format de tournoi est vide (après normalisation) — E01US023."""

    code = "nom_format_invalide"


class FormatSansEtape(DomainError):
    """Un format de tournoi ne décrit aucune phase (E01US023, ADR-0060 §5).

    Distinct d'une `SequencePhases` **vide**, qui est licite (un tournoi peut n'avoir aucune phase
    composée). Un *format*, lui, n'existe que pour être appliqué : appliquer un format vide ne
    créerait rien, et l'organisateur croirait avoir assemblé son tournoi.
    """

    code = "format_sans_etape"


class NomBlasonInvalide(DomainError):
    """Le nom d'un blason est vide (après normalisation)."""

    code = "nom_blason_invalide"


class TailleBlasonInvalide(DomainError):
    """La taille d'un blason sort de la plage autorisée (fraction de place `]0, 1]`)."""

    code = "taille_blason_invalide"


class CapaciteBlasonInvalide(DomainError):
    """La capacité d'un blason est inférieure à 1."""

    code = "capacite_blason_invalide"


class ZonesBlasonInvalides(DomainError):
    """Les valeurs de score admises d'un blason sont invalides (E01US014).

    Hors vocabulaire du référentiel (§4.2), doublon, absence de `M`, ou aucune zone marquante.
    """

    code = "zones_blason_invalides"


class NomGabaritInvalide(DomainError):
    """Le nom d'un gabarit de salle est vide (après normalisation)."""

    code = "nom_gabarit_invalide"


class NombreCiblesInvalide(DomainError):
    """Le nombre de cibles d'un gabarit de salle est inférieur à 1."""

    code = "nombre_cibles_invalide"


class CapaciteCibleInvalide(DomainError):
    """Le plafond d'archers d'une cible sort de la plage autorisée (`[1, 4]`)."""

    code = "capacite_cible_invalide"


class CibleInvalide(DomainError):
    """Le numéro de cible d'un placement n'est pas un entier strictement positif."""

    code = "cible_invalide"


class NombreVoleesInvalide(DomainError):
    """Le nombre de volées d'un barème de qualification est inférieur à 1."""

    code = "nombre_volees_invalide"


class NombreFlechesParVoleeInvalide(DomainError):
    """Le nombre de flèches par volée d'un barème de qualification est inférieur à 1."""

    code = "nombre_fleches_par_volee_invalide"


class NumeroDepartInvalide(DomainError):
    """Le numéro d'un départ (créneau) n'est pas un entier strictement positif (E02US004)."""

    code = "numero_depart_invalide"


class HoraireDepartInvalide(DomainError):
    """L'horaire d'un départ n'est pas un horaire du jour `HH:MM` valide (E02US010).

    Depuis E02US010, l'horaire d'un créneau est une **vraie donnée temporelle obligatoire**
    (24 h, `00:00`-`23:59`), et non plus le libellé libre d'E02US004 : « 9hzc », « matin » ou un
    horaire absent sont refusés **au domaine** (422). Le front pose un masque `HH:MM` en
    prévention, mais l'autorité reste ici — le serveur ne fait pas confiance à la saisie cliente.
    """

    code = "horaire_depart_invalide"


class TarifDepartInvalide(DomainError):
    """Le tarif d'un départ sort de la plage autorisée (`[0, 1 000 €]`, E02US004 / ADR-0017).

    Un tarif **nul** est licite (créneau gratuit). Contrairement à l'ancien tarif du tournoi, le
    tarif d'un créneau est **obligatoire** — il n'y a plus d'état « non défini » : voir
    `Depart.tarif_centimes`.
    """

    code = "tarif_depart_invalide"


class QuotaDepartInvalide(DomainError):
    """Le quota d'un départ (créneau) est défini mais n'est pas un entier ≥ 1 (E02US006).

    Le quota est **facultatif** : `None` = illimité, un état licite et distinct. Défini, il compte
    des **places** — au moins une, sinon le créneau serait fermé à toute inscription (on le
    supprimerait plutôt). Un plafond `QUOTA_DEPART_MAX` borne le haut, même raison que le tarif :
    une valeur absurde est une faute de frappe, et on la refuse ici (422) plutôt que de la laisser
    déborder la capacité d'un entier SQLite en erreur non typée (500).
    """

    code = "quota_depart_invalide"


class NombreVoleesParValidationInvalide(DomainError):
    """La cadence d'un grain « toutes les N volées » est inférieure à 1 (E01US015)."""

    code = "nombre_volees_par_validation_invalide"


class NombreVoleesParValidationManquant(DomainError):
    """Un grain « toutes les N volées » a été demandé sans préciser N (E01US015)."""

    code = "nombre_volees_par_validation_manquant"


class CadenceValidationSuperieureAuBareme(DomainError):
    """La cadence de validation dépasse le nombre de volées du barème de la phase (E01US015).

    Valider « toutes les 30 volées » une qualification qui n'en compte que 20, c'est ne **jamais**
    valider : le grain et le barème vivent sur la même phase, leur cohérence est une règle métier.
    """

    code = "cadence_validation_superieure_au_bareme"


class GrainIncompatibleAvecTypePhase(DomainError):
    """Le grain de validation n'a pas de sens pour ce type de phase (E01US015).

    Ex. « fin de duel » sur une phase de `qualification`, qui ne comporte pas de duels.
    """

    code = "grain_incompatible_avec_type_phase"


class EffectifPhaseInvalide(DomainError):
    """L'effectif déclaré d'une phase n'est pas un entier `>= 1` (E05US001).

    L'effectif est **facultatif** (`None` = non déclaré, licite) ; défini, il compte des
    **participants** — au moins un. Il borne les rangs qu'une source peut prélever et sert au
    contrôle de cohérence « effectif incompatible » (ADR-0045 §3).
    """

    code = "effectif_phase_invalide"


class SeuilDeBarrageInvalide(DomainError):
    """Le rang jusqu'auquel une phase départage **au tir** n'est pas un entier `>= 1` (E06US003).

    Le seuil est **facultatif** (`None` = aucun barrage, le défaut d'E06US001 : les ex æquo
    partagent leur rang). Réglé, il désigne le dernier rang « à enjeu », donc au moins le premier.
    Un `0` ne veut pas dire « aucun barrage » — cela se dit en ne réglant rien —, et l'accepter
    laisserait croire à l'organisateur qu'il a désactivé une option qu'il vient en fait de régler.
    """

    code = "seuil_de_barrage_invalide"


class PhaseQualificationIncomplete(DomainError):
    """Une phase de `qualification` a été construite sans barème ou sans grain (E05US001).

    Depuis E05US001, `bareme`/`validation` sont **facultatifs** sur `Phase` (une phase
    d'élimination n'a pas de barème de qualification) — mais une phase de **qualification** les
    exige toujours (ADR-0045 §2). Cette erreur protège l'invariant à la construction ; les fabriques
    (`Phase.qualification`, relecture du dépôt) le garantissent, ce n'est pas un cas d'entrée
    utilisateur.
    """

    code = "phase_qualification_incomplete"


class RangSourceInvalide(DomainError):
    """Le rang de début d'une source de phase est inférieur à 1 (E05US001).

    Une source prélève « les rangs `[début..fin]` » d'un classement : le premier rang est 1. Un
    `rang_debut < 1` vise des rangs **inexistants** — la moitié « rangs inexistants » du contrôle de
    cohérence détectable sans connaître la phase source (ADR-0045 §3).
    """

    code = "rang_source_invalide"


class PlageSourceVide(DomainError):
    """La plage de rangs d'une source de phase est vide : `rang_fin < rang_debut` (E05US001).

    C'est le contrôle « **source vide** » du CA : sélectionner « des rangs 8 à 4 » ne prélève
    personne. Vérifié sur le value object `SourcePhase` lui-même (indépendant de la séquence).
    """

    code = "plage_source_vide"


class SequenceOrdreInvalide(DomainError):
    """Les ordres d'une séquence de phases ne forment pas la suite contiguë 1..N (E05US001).

    Trou (1, 2, 4), doublon (1, 2, 2) ou départ hors de 1 : une séquence est une suite **ordonnée
    sans trou**. Le service réattribue les ordres à chaque édition ; cette erreur garde l'invariant
    à la construction de `SequencePhases` (ADR-0045 §3).
    """

    code = "sequence_ordre_invalide"


class SourceIntrouvable(DomainError):
    """Une phase est alimentée par une phase d'ordre inexistant dans la séquence (E05US001).

    La source désigne « la phase d'ordre *k* » ; si aucune phase de la séquence ne porte cet ordre,
    le peuplement n'a pas de source réelle (ADR-0045 §3).
    """

    code = "source_phase_introuvable"


class SourceApresPhase(DomainError):
    """Une phase est alimentée par une phase de rang **égal ou postérieur** (E05US001).

    Une phase ne peut prélever que dans le classement d'une phase **antérieure** (ordre strictement
    inférieur) : se nourrir de soi-même ou d'une phase à venir n'a pas de sens (ADR-0045 §3).
    """

    code = "source_apres_phase"


class RangsSourceInexistants(DomainError):
    """Une source prélève au-delà de l'effectif déclaré de sa phase source (E05US001).

    Prendre « les rangs 1 à 40 » d'une phase qui n'en classe que 32 vise des **rangs inexistants** —
    seconde moitié du contrôle de cohérence, celle qui met en jeu l'effectif de la source
    (ADR-0045 §3). Silencieux si la phase source ne déclare pas d'effectif (rien à quoi comparer).
    """

    code = "rangs_source_inexistants"


class EffectifIncompatible(DomainError):
    """Le nombre de participants prélevés par une source ne correspond pas à l'effectif de la phase
    consommatrice (E05US001).

    Contrôle « **effectif incompatible** » du CA : une phase déclarée pour 16 archers doit recevoir
    exactement 16 rangs de sa source. Silencieux si la phase consommatrice ne déclare pas d'effectif
    (ADR-0045 §3).
    """

    code = "effectif_incompatible"


class PhaseSansParticipant(DomainError):
    """À l'effectif projeté, cette phase n'accueille personne (E01US024).

    C'est le « **trou** » du CA d'E01US024 rendu nommable : un bloc du schéma où aucun archer
    n'arrive — parce que ses prélèvements visent des rangs que l'effectif simulé n'atteint pas, ou
    parce qu'une source amont s'est vidée. **Jamais bloquant** : le défaut ne vaut qu'à *cet*
    effectif, et un format composé pour 120 archers a le droit de se vider à 12 sans être faux
    (ADR-0063 §3). Contrairement aux autres erreurs de ce module, celle-ci n'est jamais **levée** —
    elle ne naît que portée par une `Anomalie`.
    """

    code = "phase_sans_participant"


class PrelevementVide(DomainError):
    """À l'effectif projeté, ce prélèvement ne prend aucun participant (E01US024).

    Distincte de `PlageSourceVide`, qui refuse une plage vide **par construction** ([12..8]) : ici
    la plage est bien formée, c'est l'effectif réel qui la laisse hors d'atteinte (« les rangs 33 et
    suivants » sur 30 inscrits). Avertissement, jamais bloquante — même raison que
    `PhaseSansParticipant`.
    """

    code = "prelevement_vide"


class PolitiqueInconnue(DomainError):
    """Une politique de phase désigne une implémentation non enregistrée (E05US003, ADR-0004).

    La `config.policies` d'une phase nomme une implémentation par famille
    (`{"scoring": {"nom": "cumul", …}}`) ; le registre — peuplé par la composition root — la
    résout. Un `nom` absent du catalogue de sa famille remonte ici, **explicitement**, plutôt qu'en
    `KeyError` que la relecture diagnostiquerait « configuration illisible ». Signale une config
    écrite pour un moteur qui ne connaît pas (encore) ce format.
    """

    code = "politique_inconnue"


class PolitiqueMalFormee(DomainError):
    """La `config.policies` d'une phase n'a pas la forme attendue (E05US003, ADR-0004).

    Chaque politique est un objet `{"nom": <implémentation>, …paramètres}` sous une **famille du
    catalogue ADR-0004** (`routing/scoring/seeding/byes/tiebreak/depth`). Une clé hors catalogue
    (le grain de `validation` n'en est **pas** une : il vit hors `policies`, ADR-0046) ou un objet
    sans `nom` est une config mal formée — l'assemblage refuse de deviner l'implémentation.
    """

    code = "politique_malformee"


class EffectifTableauInvalide(DomainError):
    """L'effectif d'un tableau d'élimination directe est inférieur à 2 (E05US005).

    Un tableau **oppose** des tireurs : il en faut au moins deux pour disputer un match. À un seul
    participant il n'y a pas d'arbre à construire (champion d'office) — cas traité hors moteur.
    """

    code = "effectif_tableau_invalide"


class FormatTableauIncoherent(DomainError):
    """Les politiques `seeding` et `byes` injectées se contredisent sur les exempts (E05US005).

    Un format de tableau est un **assemblage** de stratégies (règle 2) : le `seeding` place les
    seeds dans les slots, le `byes` désigne les dispensés du premier tour. Ces deux choix doivent
    **concorder** — les seeds que `byes` dispense doivent être exactement ceux que la structure du
    seeding laisse sans adversaire réel. Une paire incohérente (ex. seeding serpent + byes « aux
    plus mauvais classés ») produirait un arbre où un seed dispensé aurait pourtant un adversaire,
    ou l'inverse : le moteur la **refuse** à la construction plutôt que de trancher en douce.
    """

    code = "format_tableau_incoherent"


class MatchIntrouvable(DomainError):
    """Aucun match de ce numéro dans le tableau (E05US005) — progression d'un match inexistant."""

    code = "match_introuvable"


class MatchNonJouable(DomainError):
    """Le match visé ne peut pas recevoir de vainqueur en l'état (E05US005).

    Trois cas : c'est un **bye** (déjà gagné d'office par le seed exempté), ses deux occupants ne
    sont **pas encore connus** (un match amont n'a pas livré son vainqueur), ou il est déjà joué.
    La progression n'écrit que sur un match aux deux places remplies et sans vainqueur.
    """

    code = "match_non_jouable"


class VainqueurHorsMatch(DomainError):
    """Le vainqueur déclaré ne dispute pas ce match (E05US005).

    On ne peut désigner vainqueur que l'un des deux occupants effectifs du match — pas un tireur
    d'un autre match ni un seed déjà éliminé.
    """

    code = "vainqueur_hors_match"


class RoutingNonSupporte(DomainError):
    """Le moteur ne sait pas honorer la destination que le routing réclame pour le perdant.

    E05US005 ne connaissait qu'« élimination sèche » et refusait tout le reste ; E05US010 a livré la
    **cascade de placement** (`VersPlage`), qui n'est donc plus un cas d'erreur. L'erreur reste pour
    la destination encore à écrire — le **repêchage** WA (E05US015), qui réinjecte le perdant
    dans le tableau *amont* au lieu de le faire descendre, et suppose un câblage que ce moteur ne
    construit
    pas.
    """

    code = "routing_non_supporte"


class SourceMalFormee(DomainError):
    """Le prélèvement décrit ne correspond à aucune nature cohérente (E05US010).

    Une source porte les champs de **sa** nature et pas d'autres : un prélèvement « par issue
    de tour » sans tour ne désigne personne ; un tour sur un prélèvement « par rangs » est une
    configuration qui ment sur ce qu'elle fait. Refusé à la construction plutôt qu'ignoré en
    silence — un champ ignoré, c'est un réglage que l'organisateur croit avoir posé.
    """

    code = "source_malformee"


class SourcesQuiSeRecoupent(DomainError):
    """Deux sources d'une même phase prélèvent le même participant (E05US010).

    Un archer ne peut pas entrer deux fois dans la même phase : il occuperait deux places et
    fausserait l'effectif comme l'ensemencement. Le contrôle se fait **par phase source** — les
    rangs 1-4 de deux phases différentes désignent bien huit participants distincts.
    """

    code = "sources_qui_se_recoupent"


class PlageInvalide(DomainError):
    """La plage de rangs demandée n'a pas de sens (E05US010).

    Trois cas : elle est **inversée ou vide** (`fin < debut`), elle commence **avant le rang 1**, ou
    l'on tente de **subdiviser une plage terminale** (largeur 2 : ce n'est plus un sous-tableau à
    engendrer mais un match à jouer, *Règle T*). Le moteur refuse plutôt que de produire une
    récursion sans fin ou des rangs fantômes.
    """

    code = "plage_invalide"


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


class NomScoreurInvalide(DomainError):
    """Le nom d'un scoreur est vide (après normalisation, E10US003)."""

    code = "nom_scoreur_invalide"


class CodeScoreurInvalide(DomainError):
    """Le code individuel d'un scoreur est vide (après normalisation, E10US003).

    Le code est **attribué par le service** (généré, jamais saisi à la création) : cette erreur
    protège l'invariant à la construction de l'agrégat, elle n'est pas un cas d'entrée utilisateur.
    """

    code = "code_scoreur_invalide"


class CodePosteInvalide(DomainError):
    """Le code d'un poste de cible est vide (après normalisation, E04US001).

    Le code est **attribué par le service** (généré, jamais saisi à la création) : cette erreur
    protège l'invariant à la construction de l'agrégat, elle n'est pas un cas d'entrée utilisateur.
    Le numéro de cible invalide réutilise, lui, `CibleInvalide` (déjà défini pour le placement).
    """

    code = "code_poste_invalide"


class AuteurAuditInvalide(DomainError):
    """L'auteur d'une entrée du journal d'audit est vide (après normalisation, E10US005).

    L'auteur est le **nom** de qui a agi (scoreur, admin) — le premier des « qui / quand /
    avant-après ». Une entrée sans auteur ne dit pas *qui* : elle manque sa raison d'être en litige.
    """

    code = "auteur_audit_invalide"


class ObjetAuditInvalide(DomainError):
    """L'objet d'une entrée du journal d'audit est vide (après normalisation, E10US005).

    L'objet décrit *ce sur quoi* porte l'action (quelle série, quelle cible, quel archer). Sans lui,
    une **validation** — qui n'a ni avant ni après — ne serait plus rattachable à rien.
    """

    code = "objet_audit_invalide"


class HorodatageAuditInvalide(DomainError):
    """L'horodatage d'une entrée d'audit n'est pas un instant **UTC** *aware* (E10US005).

    Le « quand » d'une trace de litige doit être comparable **sans ambiguïté de fuseau**. La
    persistance stocke un `DateTime` **sans fuseau** et l'adapter réattache UTC à la relecture :
    cette réattache n'est fidèle **que si** l'instant écrit était déjà UTC. Un `datetime` **naïf**
    (aucun fuseau) ou **aware non-UTC** (ex. `Europe/Paris`) ferait donc **mentir le journal en
    silence** — la valeur murale serait stockée puis relue comme de l'UTC. On ferme ce chemin **à la
    construction**, comme les autres invariants de l'entrée, plutôt que laisser une horloge fautive
    corrompre la preuve.
    """

    code = "horodatage_audit_invalide"


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


class RemboursementMontantInvalide(DomainError):
    """Le montant d'un remboursement n'est pas strictement positif (E08US005, ADR-0057).

    Un remboursement matérialise une **somme encaissée à rendre** : à 0 € (ou négatif) il n'a pas de
    raison d'exister. Le site appelant ne construit un remboursement que pour une inscription
    **payée** d'un créneau **tarifé**, mais l'entité défend l'invariant elle-même à la construction
    —
    comme `TarifDepartInvalide` protège un tarif.
    """

    code = "remboursement_montant_invalide"


class PhaseSansClassementPrelevee(DomainError):
    """Une source prélève **par rangs** dans une phase qui ne produit aucun classement (E05US015).

    C'est la règle de cohérence de l'**échauffement** (référentiel §10.1) : une phase sans point et
    sans classement n'ordonne personne, donc « les rangs 1 à 32 de l'échauffement » ne désigne
    aucun ensemble. Ce n'est pas un détail d'ergonomie mais un invariant de séquence : la seule
    façon licite de succéder à une phase non classante est de reprendre **les mêmes participants,
    sans ordre** (`le reste`).

    Le contrôle est **collectif** (il faut connaître la phase amont), donc il vit dans
    `verifier_sequence` et non dans `SourcePhase.__post_init__`.
    """

    code = "phase_sans_classement_prelevee"


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


class HandicapInvalide(DomainError):
    """La valeur de handicap portée par un archer n'est pas exploitable (E05US015).

    Un handicap s'**ajoute** au score réalisé (règle donnée par le commanditaire le 31/07/2026) :
    il est donc positif ou nul. Une valeur négative retrancherait des points, ce qui n'est pas le
    système décrit — et passerait inaperçue au classement, où elle ressemblerait à une
    contre-performance.
    """

    code = "handicap_invalide"


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


class PhaseSansSource(DomainError):
    """Une phase autre que la première ne prélève dans aucune phase antérieure (E01US024).

    Le bloc ne dit pas d'où viennent ses archers : c'est le « trou » du CA d'E01US024 dans sa forme
    structurelle. **Avertissement, jamais bloquante** — la revue a montré que la bloquer casserait
    un déroulé livré (`docs/fonctionnel/E05US015.md` : « échauffement puis élimination directe sans
    source, c'est accepté ») et affirmerait quelque chose de faux, le peuplement ensemençant
    aujourd'hui avec *tous* les archers en lice (`# DETTE-028`). Comme les autres erreurs de
    diagnostic, elle n'est jamais **levée** : elle ne naît que portée par une `Anomalie`.

    La **première** phase, elle, se peuple des inscrits : son absence de source est normale.
    """

    code = "phase_sans_source"


class LibelleEcranInvalide(DomainError):
    """Un poste de type « écran de salle » est créé sans libellé exploitable (E07US004).

    Un écran n'est pas devant une cible : il est *quelque part* dans le gymnase, et c'est ce
    « quelque part » qui le désigne dans la console de supervision au moment de le piloter. Sans
    libellé, l'admin ne peut pas savoir lequel des trois écrans il fige sur le podium.
    """

    code = "libelle_ecran_invalide"


class PosteSansCible(DomainError):
    """La cible d'un poste est demandée alors que ce poste n'en a pas (E07US004).

    Depuis l'élargissement du `Poste` à l'écran de salle, `cible_index` est facultatif. Plutôt que
    de rendre `None` et de laisser chaque appelant décider quoi en faire — donc parfois l'oublier —,
    l'accesseur `Poste.cible()` exige l'invariant au point d'usage : un écran ne saisit pas de
    score, ne s'affecte pas un départ, et n'apparaît pas dans l'avancement d'une cible.
    """

    code = "poste_sans_cible"


class SequenceVuesVide(DomainError):
    """Un déroulé d'écran de salle ne programme aucune vue (E07US004).

    Un écran sans vue n'affiche rien, et un écran noir « ne se plaint pas » (CA) : c'est exactement
    la panne muette que la supervision est censée révéler. On refuse donc de la fabriquer.
    """

    code = "sequence_vues_vide"


class CadenceEcranInvalide(DomainError):
    """La cadence d'une vue du déroulé sort des bornes tenables (E07US004).

    « Cadence réglable » n'est pas « cadence quelconque » : sous le plancher, l'écran clignote et
    devient illisible à dix mètres ; au-delà du plafond, le déroulé n'en est plus un — c'est une vue
    figée qui s'ignore, et le CA a un geste dédié pour cela (la prise de contrôle).
    """

    code = "cadence_ecran_invalide"


class ConsigneEcranInvalide(DomainError):
    """Une prise de contrôle n'impose ni exactement une vue figée, ni exactement une séquence
    (E07US004).

    Les deux à la fois : l'écran ne saurait laquelle honorer. Ni l'une ni l'autre : ce n'est pas une
    prise de contrôle mais un retour à la main, qui est un **autre** geste (et le seul qui efface la
    consigne).
    """

    code = "consigne_ecran_invalide"


class DureePriseDeControleInvalide(DomainError):
    """La durée d'une prise de contrôle n'est pas strictement positive (E07US004).

    « Podium 0 minute » n'est pas une prise de contrôle. L'absence de durée, elle, est **licite**
    (« jusqu'à ce que je rende la main », arbitrage Q-UX7 du 01/08/2026) : c'est `None`, pas zéro.
    """

    code = "duree_prise_de_controle_invalide"


class PosteSansEcran(DomainError):
    """Un réglage d'écran de salle est demandé sur un poste qui n'en est pas un (E07US004).

    Symétrique de `PosteSansCible` : un poste de cible n'a ni libellé, ni déroulé de vues. Les deux
    gardes ensemble ferment le typage du `Poste` par ses **points d'usage** plutôt que par un
    `CHECK` en base — le domaine reste seul dépositaire de la règle (règle 2).
    """

    code = "poste_sans_ecran"
