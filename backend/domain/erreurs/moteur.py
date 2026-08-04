"""Erreurs du **moteur de phases** — comment le tournoi se déroule : l'enchaînement des
phases, ce que chacune prélève à la précédente, la construction de l'arbre de duels et
les politiques injectées.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 94 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from domain.erreurs.base import DomainError


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


class ProfondeurInvalide(DomainError):
    """La profondeur de classement réglée sur une phase est incohérente (E06US006, ADR-0070).

    Trois cas : un top N sans rang d'arrêt (ou à un rang `< 1`), un classement intégral assorti
    d'un rang d'arrêt — les deux décrivent des profondeurs contradictoires —, et une profondeur
    réglée sur un type qui ne monte **aucun tableau** (une qualification classe toujours tout le
    monde, un échauffement ne classe rien : le réglage n'y agit sur rien).

    La profondeur est **facultative** (`None` = non réglée) : elle retombe alors sur le preset du
    type, le podium pour un tableau (mécanisme « politique sans migration », ADR-0011).
    """

    code = "profondeur_invalide"


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


class PlusieursQualifications(DomainError):
    """Une séquence déclare **plus d'une** phase de qualification (E05US021).

    L'unicité était supposée partout et vérifiée nulle part : `PhaseRepository.par_tournoi_et_type`
    en rend « la plus récente » avec un commentaire « ne devrait pas survenir », et **neuf** sites
    (classements, palmarès, complétude, placement, feuille de marque, saisie en duels…) lisent
    « la » qualification comme s'il n'y en avait qu'une. Rien ne l'interdisait pourtant : l'écran de
    composition offre tous les types à chaque étape.

    Le coût de l'ambiguïté a été démontré en revue : « la qualification » se résolvait au plus
    petit `ordre` dans le domaine et au plus grand `id` dans le repository — deux phases
    différentes. Le minimum d'inscrits se calculait donc sur une phase et le moteur prélevait dans
    l'autre : un tournoi annoncé « minimum 2 » cassait en salle. Aligner les deux résolutions
    n'aurait fait que reporter le problème (un réordonnancement les redésaccorde) ; on rend
    l'ambiguïté **impossible**.

    Bloquante : c'est faux à tout effectif. Une qualification en deux manches se modélise par un
    barème, pas par deux phases.
    """

    code = "plusieurs_qualifications"


class EffectifMinimumIncoherent(DomainError):
    """Un format exige **moins** d'inscrits que son déroulé n'en réclame (E05US021).

    Le minimum d'un format se **déduit** de ses prélèvements : « les rangs 33 et suivants » ne monte
    un tableau de deux qu'à partir du 34ᵉ classé. Un club peut exiger davantage (« pas de tournoi de
    ce type sous 40 archers ») — c'est une règle sportive, elle se pose au-dessus du plancher
    technique.

    ⚠️ **Une exigence trop basse ne laisse rien passer** : le minimum retenu est le `max` des deux,
    donc une valeur sous le plancher est simplement **inerte**. Ce n'est pas un risque pour le
    tournoi, c'est un **écran qui ment** — l'organisateur croit avoir réglé un seuil qui ne
    s'appliquera jamais, et le corrigera d'autant moins qu'il le croit posé. C'est ce mensonge que
    l'anomalie interdit, pas un danger d'exécution. *(La docstring affirmait initialement l'inverse
    — « il laisserait démarrer un tournoi que le moteur refuserait » — ce que le `max` contredit ;
    relevé en revue.)*

    Bloquante, donc, et non conjoncturelle : la contradiction est vraie à tout effectif. Le prix
    assumé est qu'ajouter une consolante « rangs 41 et suivants » à un format qui exigeait 40 le
    rend inapplicable jusqu'à ce que le chiffre soit relevé — le déroulé a changé, l'exigence doit
    être revue.
    """

    code = "effectif_minimum_incoherent"


class ExigenceEffectifInvalide(DomainError):
    """Le minimum exigé d'un format n'est pas un entier positif (E05US021).

    « Aucune exigence » se dit en ne réglant **rien** (`None`), pas en réglant zéro — même parti que
    `Phase.barrage_jusqu_au`. Un zéro accepté se lirait « exige 0 archer », un nombre qui n'a aucun
    sens et qu'aucun écran ne saurait présenter.
    """

    code = "exigence_effectif_invalide"


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
