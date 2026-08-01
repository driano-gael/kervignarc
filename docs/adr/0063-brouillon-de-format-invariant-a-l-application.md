# ADR-0063 — Un format se compose en brouillon ; l'invariant se vérifie à l'application

- **Statut** : Accepté
- **Date** : 2026-08-01
- **Décideurs** : Organisateur / Architecte
- **Portée** : E01US024 (composer, diagnostiquer et simuler un déroulé de tournoi)
- **Lie** : [ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) (le
  format comme brique du club, dont cet ADR relâche les invariants d'enregistrement),
  [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (§3 : les invariants collectifs
  d'une séquence, qui deviennent ici des anomalies énumérables),
  [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (sources multiples et **plages
  relatives**, sans lesquelles la question « à quel effectif ? » ne se poserait pas),
  [ADR-0062](0062-catalogue-de-types-de-phase.md) (les neuf types que cet écran compose enfin),
  [ADR-0054](0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md) et
  [ADR-0055](0055-cockpit-de-simulation-bot-pausable.md) (le substrat et le bot que la simulation
  de format **compose** au lieu de les réécrire),
  [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md) (le patron « on crée en brouillon, on ne
  passe `prêt` que si… », dont ceci est la transposition au format)
- **Source métier** : demandes du commanditaire du **31/07/2026**, citées verbatim dans le CA
  d'E01US024 (`stories/E01-configuration.md`).

## Contexte et problème

E01US023 a fait du **format** une brique du patrimoine du club. Mais l'écran livré ne savait
fabriquer qu'une **qualification** : ni élimination directe, ni effectif, ni source. La capacité de
composer un déroulé avait donc *disparu* de l'atelier, et le contournement documenté — « composez-le
sur un tournoi puis promouvez-le en format » — obligeait à passer par une édition pour fabriquer un
modèle du club, soit exactement le mélange que le découpage en axes d'E14US003 supprime.

Rendre l'écran capable de tout composer bute immédiatement sur un mur : **`FormatTournoi` valide
tout à la construction**. Une qualification sans barème, une séquence à laquelle il manque encore
sa deuxième phase, un prélèvement qui pointe vers une phase pas encore créée — autant d'états
parfaitement normaux *en cours de composition*, et tous refusés à l'enregistrement. On ne peut pas
composer un déroulé si chaque état intermédiaire est illégal.

Le commanditaire a tranché le besoin sans ambiguïté :

> « on doit pouvoir sauvegarder le brouillon tout le temps, mais on ne peut réellement l'utiliser
> pour un vrai tournoi que s'il est valide, avec un déroulé cohérent »

## Décision

**L'invariant quitte l'enregistrement pour l'usage.** Ce qui doit être cohérent, ce n'est pas la
ligne en base : ce sont les **phases produites**.

### 1. Un format s'enregistre presque toujours ; il ne s'applique que s'il tient

`ModelePhase.__post_init__` ne valide plus rien. `FormatTournoi.__post_init__` ne garde qu'**un**
invariant : le **nom** non vide. Il le garde parce que le nom est la **clé d'unicité** de la
bibliothèque — l'assemblage et la promotion dédoublonnent par lui (arbitrage d'E01US023, point 1) :
un format sans nom ne serait pas un brouillon, il serait introuvable.

Tout le reste — aucune étape, ordres non contigus, source postérieure, qualification sans barème,
grain inadmissible — se **diagnostique** (`FormatTournoi.anomalies`) et se **refuse à
l'application** (`FormatTournoi.appliquer`).

**Le garde-fou n'est pas désarmé : il a changé de porte.** `appliquer` lève la première anomalie
bloquante *telle quelle* — même classe d'exception, même `code`, même message d'organisateur,
donc même 422 à la frontière API.

⚠️ **Ce que `pour_tournoi` rattrape, et ce qu'il ne rattrape pas.** Une première rédaction de cet
ADR affirmait qu'« même en court-circuitant `appliquer`, `pour_tournoi` construit une `Phase` dont
le `__post_init__` valide : aucun modèle incohérent ne peut atteindre un tournoi réel ». C'est vrai
pour **la moitié** des invariants seulement. `Phase.__post_init__` n'appelle que
`verifier_coherence_etape` — les invariants **internes**. Les invariants **collectifs** (ordres
contigus, source postérieure ou introuvable, recoupements, somme des prélèvements) ne sont tenus
que par `SequencePhases.__post_init__`, que `appliquer` ne construit **pas** : il rend un
`tuple[Phase, ...]`. Il n'y a pas de trou aujourd'hui — `pour_tournoi` n'a qu'un seul appelant,
`appliquer` lui-même — mais la phrase invitait à en ouvrir un. **Règle à tenir : tout nouvel
appelant de `pour_tournoi` doit passer par `appliquer`.**

**Corollaire découvert en revue, et qui vaut d'être écrit : relâcher une validation ne suffit pas,
il faut la relâcher partout où l'ancienne hypothèse était encodée.** Trois couches la portaient
encore, et chacune a produit un défaut réel : l'adapter SQL **refusait d'écrire** l'état devenu
licite (500 sur toute la bibliothèque), `ServiceFormats.appliquer` **détruisait avant de valider**
(le tournoi perdait ses phases), et le formulaire front **ne savait pas produire** l'état que l'US
existe pour rendre possible. Aucun n'était visible depuis le domaine.

**Conséquence à assumer noir sur blanc : la base peut contenir des formats incohérents.** C'est le
prix, et il est payé volontairement. Ce qui protège le tournoi, ce n'est plus la contrainte
d'écriture, c'est `appliquer`.

### 2. Les règles restent à un seul endroit — elles changent de **mode**, pas de **domicile**

`verifier_coherence_etape` et `verifier_sequence` levaient la **première** erreur rencontrée. Elles
deviennent de minces enveloppes autour de générateurs — `anomalies_etape`, `anomalies_sequence` —
qui les **énumèrent**. Les anomalies portent les **instances d'erreurs typées existantes**
(`SourceApresPhase`, `PhaseQualificationIncomplete`, `EffectifIncompatible`…), qui portent déjà leur
code et leur message.

**Portée de ce mécanisme.** `Anomalie` est le mode de signalement de la **composition d'un
format** — diagnostiquer un brouillon —, pas un remplacement général de l'exception dans le domaine.
Partout ailleurs, une règle violée se lève : c'est ce qui garde les invariants tenus par
construction. Une US qui voudrait l'étendre devrait dire pourquoi son objet est, lui aussi,
« énumérer les défauts d'un état volontairement incomplet ».

**Aucune règle n'est recopiée.** C'est le point de conception qui compte : un diagnostic qui
réimplémenterait les contrôles serait une duplication d'invariant — précisément ce que le registre
de dette proscrit —, et il dériverait au premier changement de règle. Ici, `Phase.__post_init__`,
`SequencePhases.__post_init__`, `appliquer` et l'écran de composition consomment **le même**
générateur.

Une anomalie porte l'`ordre` de la phase qu'elle concerne (`None` = la séquence entière). C'est ce
qui permet de la coller au bon **bloc** du schéma, comme le CA l'exige — « un trou visible dans le
dessin, pas un message d'erreur abstrait ».

### 3. Deux gravités, et la ligne de partage est la contribution de l'US

> **Ce qui est faux quel que soit l'effectif *bloque* ; ce qui n'est faux qu'à *cet* effectif
> *avertit*.**

- **Bloquante** — une source postérieure, un ordre en doublon, une qualification sans barème. Vrai à
  12 archers comme à 120. Interdit d'appliquer le format.
- **Avertissement** — « les rangs 33 à 120 » alors qu'il n'y a que 82 inscrits, une phase que plus
  personne n'atteint. Le format **n'est pas faux** : il ne tient pas *ici*.

Sans cette distinction, la décision d'ADR-0061 s'effondrerait : les **plages relatives** existent
précisément pour qu'un déroulé composé pour 120 archers se joue à 82. Bloquer sur un débordement
d'effectif rendrait inutilisable ce que le CA d'E05US010 demande. Inversement, taire ces
avertissements rendrait le diagnostic muet là où il est le plus utile.

### 4. Le domaine **projette**, le front **dessine**

Le schéma à braquets est calculé par `domain/deroule.py` (`projeter(etapes, effectif)`), qui rend des
**faits structurés** : effectif par bloc, tranche de rangs, flux entrants et sortants, tours, et les
braquets tour par tour. Le front ne fait que la géométrie et l'habillage.

La tentation était de tout calculer en TypeScript — c'est du dessin, après tout. Elle a été écartée :
les braquets **sont** la *Règle R* de `moteur-placement-lucky-loser.md` (« les perdants du tour *t*
forment la tranche de rangs basse encore ouverte »), déjà portée par `domain.plage.Plage`. La
recalculer côté client dupliquerait un invariant du moteur, avec deux vérités qui divergeraient à la
première correction. Le prix payé est un aller-retour serveur par modification du brouillon — rendu
indolore par la décision §1, puisqu'un brouillon s'enregistre à tout moment.

### 5. La simulation **compose** l'existant ; elle n'écrit aucun moteur

`simuler_format(format, effectif)` fabrique un tournoi éphémère **dans le harnais in-memory**
(ADR-0054), y applique le format, y génère N archers fictifs et le fait jouer par le **bot** du
cockpit (ADR-0055). `demarrer` a été scindé pour exposer `ouvrir_sur_harnais` : un seul bot, donc
une seule dérive possible.

Le garde-fou d'ADR-0054 §4 (« on ne simule qu'un tournoi avant démarrage ») **ne s'applique pas** :
il protège une compétition réelle d'une interférence, et ici il n'y a aucun tournoi réel.

Sur la non-persistance, une nuance que la revue a eu raison d'exiger : `ServiceSimulationFormat` ne
reçoit en propre aucun repository SQL sinon la bibliothèque de formats, en lecture — mais
`ServicePilotageSimulation`, qu'il compose, en **détient**. Ils ne sont lus que par `demarrer`, que
ce chemin n'emprunte pas. L'isolation tient donc parce qu'on appelle `ouvrir_sur_harnais`, **pas**
parce que le chemin SQL serait absent : elle est vérifiée, pas structurelle. La dire structurelle
inviterait à ne plus la vérifier.

**Arbitrage : `ServiceJeuEssai` n'est pas réutilisé pour les archers fictifs.** La note de l'US le
prévoyait. Le code ne s'y prête pas : ce service pilote des **services** (tournois, départs, clubs,
inscriptions), pas des repositories ; le brancher sur le harnais supposerait de l'élargir de trois
magasins et d'instancier six services — pour obtenir des noms. Or un format ne connaît ni départs,
ni clubs, ni quotas. La génération locale tient en vingt lignes et reste déterministe
(`random.Random(graine)`, règle 9).

### 5 bis. Le schéma est un SVG **maison**, sans bibliothèque de layout

Règle 11 (parcimonie), avec le précédent du routeur maison (DETTE-024). La disposition est linéaire
— une colonne par phase, dans l'ordre — et les seules courbes sont les flèches qui sautent une
colonne : 157 lignes de géométrie pure (`schema.ts`), couvertes par 11 tests. L'inline permet en
outre aux couleurs de passer par les variables CSS, donc au thème clair/sombre de suivre sans code
conditionnel.

Ce que cette disposition **ne saura pas** faire, et qui justifierait de reconsidérer : des
branchements non linéaires (deux phases au même rang), des croisements de flèches à optimiser, des
nœuds de tailles très hétérogènes. Aucun n'est au programme du chantier moteur.

### 6. La simulation ne passe **pas** par la file d'écriture

Elle joue plusieurs milliers de volées. La router vers le writer unique bloquerait **toutes** les
écritures du tournoi pendant sa durée, pour un calcul qui ne touche pas la base (règle 7 : la file
protège SQLite, or rien ici n'y mène). Elle part donc au threadpool, comme une lecture. Son effectif
est borné par une **borne de service** (`EffectifSimulationInvalide` → **400**, seule erreur
applicative en 400 : la requête est impossible *en soi*, pas en conflit avec un état).

## Conséquences

**Positives.**

- L'atelier sait de nouveau composer un déroulé complet, sans passer par un tournoi.
- Les neuf types du catalogue (ADR-0062) et les trois natures de prélèvement (ADR-0061) sont enfin
  **atteignables depuis un écran** — la réserve de DETTE-015 (« l'écran n'édite qu'un prélèvement par
  rangs ») est levée.
- Le diagnostic est compréhensible par un non-technicien : un bloc, un compte, une tranche de rangs.
- La simulation révèle ce qu'aucune relecture ne donne. Elle a d'emblée corrigé une croyance : un
  tableau à N duellistes ne coûte pas `N-1` duels mais `N`, la profondeur de podium ajoutant la
  petite finale. Qui dimensionne ses scoreurs sur le compte théorique se trompe d'un duel par
  tableau.

**Négatives, assumées.**

- **La base peut contenir des formats incohérents** (§1). Un outil de reprise qui lirait la table
  sans passer par `appliquer` doit le savoir.
- **Cinq tests de domaine et un test d'API ont été inversés.** Ils vérifiaient que la *construction*
  refuse ; ils vérifient que le brouillon s'enregistre, que le diagnostic nomme le défaut avec le
  **même code**, et que `appliquer` refuse avec la **même exception**. C'est ce qui ressemble le plus
  à un garde-fou désarmé sans en être un — d'où le présent §1, et d'où le commentaire d'avertissement
  en tête du bloc de tests. Précédent au projet : le test HTTP inversé de DETTE-009.
- **La simulation d'un format multi-phases diverge de sa projection**, et cette US ne le corrige pas.
  Le moteur d'exécution n'a **aucun consommateur de `Phase.sources`** côté duels
  (`ServiceSaisieDuels._decor` ensemence chaque tableau avec **tous** les archers en lice) : un
  format qui dit « les rangs 1 à 8 au tableau » se joue aujourd'hui à 12 si 12 archers sont classés.
  C'est le cœur de **DETTE-028**, dont la résorption est une US à part entière. Le parti retenu est
  de **rendre l'écart visible** : chaque phase simulée porte l'effectif **projeté** à côté de
  l'effectif **constaté**, et l'écran le signale. Un chiffre faux et muet est pire qu'un chiffre
  discuté.
- Un aller-retour serveur par modification du brouillon (§4).

## Alternatives écartées

- **Garder la validation à l'enregistrement et composer entièrement côté client, en n'envoyant que
  le format fini.** C'était le chemin le plus court. Écarté : il faut alors réimplémenter tous les
  contrôles en TypeScript pour dire à l'organisateur ce qui manque — la duplication d'invariant, et
  deux vérités qui divergent. Et cela ne résout pas la reprise : on ne peut pas fermer l'onglet et
  revenir le lendemain sur un déroulé à moitié composé.
- **Un statut `brouillon` / `publié` sur le format** (transposition littérale d'ADR-0026). Écarté :
  un statut serait un **second** état à tenir cohérent avec le contenu, et rien n'empêcherait un
  format « publié » de devenir incohérent à l'édition suivante. La cohérence se **calcule** depuis
  les étapes — la dériver est plus sûr que la déclarer.
- **Bloquer aussi les anomalies conjoncturelles** (§3). Écarté : cela reviendrait à interdire les
  plages relatives, que le CA d'E05US010 demande explicitement.
- **Écrire un moteur de simulation dédié au format.** Écarté sans hésitation : ADR-0054 et ADR-0055
  livrent le substrat et le bot. Un second moteur aurait dérivé du premier, et c'est le premier qui
  tourne le jour J.
