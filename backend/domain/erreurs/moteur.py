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


class ReglageDePoulesInvalide(DomainError):
    """Un réglage de poules porté par une phase qui n'est pas de type `poules` (E05US023).

    Symétrique de `ProfondeurInvalide` sur son troisième cas, et pour la même raison : retyper une
    phase sans nettoyer son réglage laisserait une élimination directe porter une taille de poule,
    que plus aucun lecteur n'irait chercher. Un réglage que rien ne lit est pire qu'absent — il se
    voit en base, il rassure, et il ne s'applique pas.

    Les réglages **incohérents en eux-mêmes** (taille < 2, qualifiés hors bornes) restent
    `ConfigurationPouleInvalide`, levée par `ReglageDePoules` : c'est la cohérence du réglage,
    celle-ci est sa compatibilité avec le type qui le porte.
    """

    code = "reglage_de_poules_invalide"


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


class ChocDePoulePossible(DomainError):
    """Deux archers d'une **même poule** peuvent se retrouver au premier tour du tableau (E05US023).

    Le serpent sépare les membres d'une poule quand leur nombre `P` est **pair** : le tableau
    apparie les rangs `r` et `M+1-r` (`M` = taille du tableau, une puissance de 2), donc l'écart
    entre deux adversaires est **impair** et n'est jamais divisible par un `P` pair. À `P` impair il
    existe des paires fautives : 3 poules x 4 qualifiés = 12 archers produit (rang 7, rang 10), tous
    deux de la poule 1 — l'exemple du CA.

    ⚠️ **Deux énoncés antérieurs de cette règle étaient faux, et l'un vivait ici.** « Puissance de 2
    ⇒ pas de choc » ne tient pas : à 3 poules et 16 places, la paire (1, 16) réunit le n° 1 et un
    membre de sa propre poule. Les sept mesures qui l'étayaient — 4x2, 8x2, 4x4, 8x4, 16x2, 2x4,
    5x2 — avaient toutes soit un `P` pair, soit un effectif non puissance de 2 : un échantillon
    biaisé dont on avait tiré une loi générale. Et « les byes décalent les paires » est un faux
    positif systématique à `P` pair. Le prédicat exact vit dans `domain/deroule.py`
    (`_motif_de_choc`), vérifié contre l'appariement réel sur 9945 configurations.

    **Avertissement, jamais bloquant** (arbitrage du 09/08/2026) : corriger demanderait une
    politique de croisement, donc une règle métier que personne n'a demandée. On le **signale** à
    l'atelier plutôt qu'en douce — l'organisateur ajuste son nombre de qualifiés s'il y tient.
    """

    code = "choc_de_poule_possible"


class SerpentApresDesPoules(DomainError):
    """Une phase de poules prélève dans une autre phase de poules et compose au **serpent**
    (E05US029).

    Le serpent **équilibre** les groupes, ce qui est juste tant que personne ne connaît les
    niveaux — c'est pourquoi il est le défaut depuis le 31/07/2026. Mais une phase nourrie par
    d'autres poules dispose déjà d'un classement de niveau : composer au serpent y éparpille les
    six têtes de série dans les six groupes, soit l'inverse exact de ce que l'organisateur croit
    régler en enchaînant deux phases de poules.

    **Bloquant, et c'est un arbitrage** (cadrage du 21/08/2026). Le défaut ne produit ni erreur ni
    incohérence : il monte un tournoi parfaitement jouable, simplement dépourvu de l'intérêt
    sportif visé — et cela ne se voit qu'en salle, une fois les groupes affichés. Un avertissement
    qu'on peut ignorer arriverait donc toujours trop tard.

    `ReglageDePoules.serpent_assume` lève le refus. Rebrasser volontairement les groupes reste
    légitime ; ce que la dérogation apporte est la **trace** que le choix a été posé, sans quoi
    « voulu » et « pas vu » sont indiscernables.

    ⚠️ **Le prédicat porte sur la SOURCE, pas sur le rang dans le déroulé.** Une phase de poules
    sans source déclarée est alimentée par le classement du départ (ADR-0068), donc par la
    qualification — les niveaux n'en viennent pas, et le serpent y reste légitime même si des
    poules la précèdent dans le déroulé.
    """

    code = "serpent_apres_des_poules"


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


class ArretProgrammeInvalide(DomainError):
    """Un **arrêt programmé** ne décrit pas une coupe applicable (E05US033, ADR-0091).

    Trois motifs, tous constatables à la composition :

    - `apres_tour` < 1 — un arrêt « après le tour 0 » couperait la phase avant son premier tir ;
      ce n'est pas une pause mais un refus de démarrer, qui a déjà son geste (ne pas la démarrer) ;
    - deux arrêts après le **même** tour — le second est inapplicable, la phase étant déjà en
      pause, et la portée ne les désambiguïse pas (le geste large contient le geste étroit) ;
    - `apres_tour` ≥ le nombre de tours **quand celui-ci est connu** — l'arrêt est inerte, la phase
      étant finie. Silencieux quand il ne l'est pas : un suisse réglé à 7 rondes n'en joue que 5 si
      l'effectif ne permet pas plus, et l'atelier ne connaît pas toujours l'effectif. Même doctrine
      qu'`EtapeDeroule._verifier_rondes_appariables` — on ne refuse pas ce qu'on ne peut pas juger.

    Sert aussi de refus au **franchissement** qui reculerait (`ARME → FRANCHI → LEVE` est monotone,
    comme le cycle de vie d'une phase, ADR-0045) : un franchissement réversible ferait de chaque
    évaluation du déclencheur un tirage au sort.
    """

    code = "arret_programme_invalide"
