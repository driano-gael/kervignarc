# E04 — Saisie des scores en temps réel — User Stories

> EPIC : [EPIC-04](../epics/EPIC-04-saisie-scores.md) · Réfs : CDC fonctionnel M5, ADR-0005, **CDC UX §4 et §7.2**.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (÷3 : 18 → 6). Les
> anciennes US découpées par étape technique (saisir / valider / enregistrer / verrouiller / cumuler /
> diffuser / corriger…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte.
> **Aucun comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). Les liens
> entrants ont été redirigés vers l'US survivante. Correspondance ancien → nouveau en fin de fichier.

> ⚠️ **Révisé le 14/07/2026** ([`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §4, §7.2–7.3).
> **La tablette appartient à la cible, pas à la personne** : c'est un **poste fixe et ouvert** (`D-13`), et
> **ce n'est pas le scoreur qui saisit** — c'est un **marqueur** (un archer de la cible, désigné selon FFTA
> B.6.1.1) qui tape pour les 3–4 archers. Le scoreur, lui, est **itinérant** et **valide** (E10US003).
> **Deux postes distincts, pas un.** Le parc est **fourni par le club, navigateur seul, plancher tablette**
> (`D-05`, `D-02`) : **pas de mode kiosque**, donc la **fermeture accidentelle de l'onglet arrivera** — d'où
> E04US001.

---

### E04US001 — Rattacher une tablette à sa cible (QR + jeton de poste)
*En tant qu'*organisateur (au montage), *je veux* rattacher une tablette à une cible **en un scan**, *afin que* le poste sache qui il sert toute la journée — **et le retrouve tout seul après une coupure**.
- **CA** : **scan du QR de la cible** (E09US008) → le back émet un **jeton de poste** rangé dans le navigateur (`localStorage`) ; **code de secours saisi à la main** si le QR est abîmé ou l'appareil photo capricieux ; à **toute réouverture** (onglet fermé, navigateur planté, tablette redémarrée, veille de 3 h), le poste **retrouve sa cible sans rien demander à personne** ; le jeton est **lié au tournoi** et **révocable** → un **nouveau tournoi force le re-rattachement** ; le poste ne peut saisir que pour **sa** cible (E10US007) ; l'IP **n'est jamais l'identité** (diagnostic uniquement) ; **le jeton porte aussi les préférences du poste** — dont le **thème** choisi (`D-26`), qui **revient tout seul** à la réouverture.
- **Notes** : ~~« saisie d'un code de cible → session **scoreur** rattachée », v0.1~~ → **réécrite le 14/07/2026** (`D-06`, `D-07`). **Ni IP, ni empreinte** : les baux DHCP expirent (une tablette en veille perd sa cible) et une IP réattribuée ferait **partir les scores sur la mauvaise cible, silencieusement** — *un score faux et silencieux est pire qu'une erreur visible* ; l'empreinte ne distingue pas **30 tablettes identiques**. Réutilise le patron de `sessionAdminStore` (Zustand + `persist`, jeton `Bearer`, purge sur 401) → **`sessionPosteStore`** : ni concept nouveau, ni configuration réseau. **Piège traité par les CA** : *le jeton survit trop bien* — au tournoi suivant, la tablette de la cible 12 posée sur la cible 5 croirait toujours être la 12. **Le jeton porte les préférences, pas seulement le rattachement** (`D-26`, [CDC UX §4.5](../cahier-des-charges-ux.md)) : *dans un gymnase, la lumière varie d'une cible à l'autre* — la tablette sous la baie vitrée passe en thème clair, les 29 autres ne bougent pas. Sans ça, `D-05` (pas de kiosque, l'onglet se ferme) obligerait le bénévole à rebasculer son thème **à chaque réouverture**. **Arbitrage tranché le 18/07/2026 (multi-tournoi)** : « lié au tournoi » supporte **plusieurs tournois non terminés en même temps** (ex. intérieur + extérieur) — la révocation s'ancre sur le **statut** du tournoi (terminer un tournoi invalide ses jetons de poste ; régénérer les codes = E09US008), **jamais** sur un « tournoi courant » global. Le contrat d'identité du poste (code de cible généré/stocké, jeton opaque en mémoire, en-tête `X-Jeton-Poste`) est fixé par [ADR-0029](../docs/adr/0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) — **3ᵉ mode de `D-13`, après le scoreur (ADR-0025)**. La garde s'appuie sur le `terminé` du cycle **actuel à 3 statuts** ; à réaligner quand E01US017 livrera les **7 statuts**.
- **Recette (ENF-7, 18/07/2026)** : une **seule tablette** disponible en test. Le jeton étant en `localStorage` **par origine**, un navigateur ne porte **qu'un** poste — exercer le multi-poste (plusieurs rattachements, diffusion, supervision E12US001) demande des **contextes séparés** (profils / navigation privée) ou le PC de dev comme postes additionnels ; la tablette valide le *device-specific* (tactile, QR, Wake Lock). Cf. [`guide-architecture.md`](../guide-architecture.md) §9.
- **Dépend de** : E03US001, E01US001 · **Jalon** : J1

### E04US002 — Saisie de qualification en temps réel
*En tant que* **marqueur**, *je veux* saisir, valider, cumuler et corriger les flèches de qualification sur ma cible, *afin de* produire le score en temps réel — sans rien perdre ni laisser d'incorrigible.
- **CA — grille (ex-002)** : archers/positions de la cible **déduits du jeton de poste** (E04US001 — rien à choisir) ; volée courante mise en évidence ; **grain de validation actif indiqué** (« validation à la fin de la série », `D-11`, E01US015) ; adapté au tactile — **cibles ≥ 48 px**, plancher **768 px** (`D-02`).
- **CA — marqueur (ex-017)** : au début du départ, **désignation du ou des marqueurs** parmi les archers de la cible (**plusieurs possibles**) ; **marqueur actif affiché discrètement et changé en un geste** (pas de sélecteur permanent qui vole l'espace du pavé) ; **chaque volée enregistre qui l'a saisie**, consultable (« volée 7 saisie par DURAND, 10h42 ») ; **déclaratif, pas authentifié** (E10US007 : le poste reste ouvert) ; alimente **E10US005** (`D-04`).
- **CA — pavé (ex-003)** : pavé de valeurs **déduit du blason tiré** (`Blason.zones`, E01US014) et **non** du barème de la phase — sur un triple 40 les touches 5→1 n'existent pas (FFTA §4.4) ; gros boutons ; correction possible avant validation.
- **CA — valeurs légales (ex-004)** : refus d'une valeur hors barème ; nombre de flèches par volée conforme au barème (E01US009).
- **CA — enregistrement (ex-005)** : volée persistée par la **file d'écriture** (writer unique) ; accusé de réception au client ; **idempotence par identifiant de saisie** (ADR-0005).
- **CA — édition avant validation (ex-006)** : volée modifiable tant que la série n'est pas validée ; historique non requis à ce stade.
- **CA — validation & verrou (ex-007)** : après validation, la série est **verrouillée** (non éditable hors correction habilitée, cf. CA suivant) ; **la validation porte le nom du scoreur** (E10US003, alimente E10US005) ; **grain de validation lu dans la phase** (`config.validation`, E01US015 : fin de série / fin de duel / toutes les N volées).
- **CA — cumul (ex-008)** : total mis à jour à chaque validation, conforme au barème.
- **CA — correction tracée (ex-012)** : un score **verrouillé** n'est corrigeable que par un **rôle habilité** ; toute correction écrit une entrée d'**AuditLog** (qui / quand / avant-après, E10US005) et **recalcule le cumul**.
- **Notes** : **la validation est un acte *de fin*** — FFTA : les feuilles de marque sont signées « à la fin de la distance, de la compétition **ou du duel** ». L'art. B.6.1.2 (« établissement des scores toutes les 2 volées ») porte sur le **cumul** (calculé par l'appli), **pas** sur la validation par un tiers : valider toutes les 2 volées ferait **~180 passages par départ** (intenable à 3 scoreurs). La validation du scoreur **tient lieu de seconde marque** (`D-03`, FFTA B.6.1.1) — **`Q-UX3` : à confirmer par un arbitre du club**. Le **marqueur** (`D-04`) : *il change rarement, donc l'interface ne s'organise pas autour de ce changement* (**pas de sélecteur permanent** au-dessus de la grille) ; la trace est l'**équivalent numérique de la signature** de la feuille de marque (FFTA B.6.1.1), seul argument sérieux face à un arbitre contestant la dématérialisation. La **correction tracée** (ex-012) est le seul chemin d'écriture sur une série verrouillée.
- **Arbitrages tranchés le 19/07/2026** (reversés ici — règle 9 ; pour que l'implémentation d'E04US002
  n'en dérive pas des tests faux) :
  - **Dépendance E10US005 satisfaite en amont** : elle était insatisfiable (l'US 005, seq 47, vient
    *après* cette US, seq 41, et n'existait pas). Son **socle** (agrégat `EntreeAudit`, port
    `AuditRepository`, `ServiceAudit.consigner`, port `Horloge`) a été **livré d'abord** — cf. entrée
    E10US005 « Livré (socle backend) ». La **correction tracée** (ex-012) appellera
    `ServiceAudit.consigner(action=CORRECTION_SCORE, avant, apres, auteur=nom du rôle habilité)` **dans
    la même commande de file** que la ré-écriture (règle 7) ; la validation appellera de même
    (`action=VALIDATION`, auteur = nom du scoreur — `exiger_scoreur` devra **résoudre le `Scoreur`**,
    aujourd'hui il ne fait que valider).
  - **Source des archers-par-cible = modèle `Affectation` (E03US004, ADR-0024)**, *pas* le champ
    walking-skeleton `Archer.cible` (qu'utilise encore la démo `saisir_score`). Le poste connaît
    `(tournoi_id, cible_index)` ; on reconstitue cible → départ → inscriptions → archers avec leur
    **position A–D** via `PlacementRepository`. **Un ADR actera l'abandon d'`Archer.cible` comme source
    de saisie** (à écrire dans la branche E04US002, pas ici).
  - **Atomicité acte↔trace à trancher (remontée de la revue adversariale d'E10US005)** : le socle
    d'audit expose `ServiceAudit.consigner`, qui commit dans **sa propre session** ; être « dans la
    même commande de file » (règle 7) n'est **pas** être dans la même **transaction**. Une écriture
    déchirée (le score validé commit, la trace échoue — ou l'inverse) laisserait une validation **non
    tracée** ou une **trace fantôme**. E04US002 doit **choisir consciemment** : ordonner consign
    avant/après le commit du score, assumer et documenter la fenêtre, ou introduire une couture de
    **session partagée** (co-localiser les deux écritures dans une seule méthode de repository, cf.
    `ArcherRepositorySQL.supprimer`) — cette couture **n'existe pas** dans le socle.
  - **`avant`/`apres` : passer `None`, jamais `""`** — le socle les conserve **verbatim** (pas de
    normalisation) : `""` est distinct de `NULL` en base et à la relecture. Une `CORRECTION_SCORE`
    **porte** avant/après ; une validation les laisse à `None` (un `""` afficherait un « avant » vide).
- **Absorbe** : ex-E04US002 à 008, E04US012, E04US017. **Dépend de** : E04US001, E01US009, E01US014, E01US015, E00US007, E10US003, E10US005, E10US007 · **Jalon** : J1

### E04US009 — Diffusion live & résilience réseau
*En tant que* public/organisateur (le live) et scoreur (les coupures), *je veux* que les scores validés se diffusent en direct et survivent à une coupure brève, *afin de* suivre l'épreuve et de **ne rien perdre**.
- **CA — diffusion live (ex-009)** : après validation (E04US002), **diffusion WebSocket** ; les abonnés (écran de salle, mobile) se mettent à jour en **< 1–2 s**.
- **CA — file hors-ligne (ex-010)** : hors-ligne, les saisies sont **mises en file côté front** et **rejouées à la reconnexion** ; **pas de doublon** (idempotence, ADR-0005).
- **CA — indicateur (ex-011)** : **état de connexion visible** en permanence — connecté / hors-ligne / synchronisation en cours.
- **Absorbe** : ex-E04US009 à 011. **Dépend de** : E00US008, E04US002 · **Jalon** : J1

### E04US013 — Saisie en duels
*En tant que* scoreur, *je veux* saisir un duel au système de sets, en désigner le vainqueur et résoudre les égalités, *afin de* faire progresser le tableau.
- **CA — sets (ex-013)** : points de set attribués selon le barème (FFTA : premier à **6 pts** sur 5 sets ; format club : 4 pts) ; cumul des points de set du match ; **les arcs à poulies ne tirent pas en sets** mais au cumul (FFTA A.7.5.2) — le barème se résout par (phase, arme), cf. EF-3.4.
- **CA — vainqueur (ex-014)** : vainqueur calculé selon le barème de sets ; transmis au moteur (E05US005).
- **CA — barrage/shoot-off (ex-016)** : à égalité, saisie d'un **shoot-off** (1 flèche) ; plus près du centre départage ; vainqueur enregistré — politique `tiebreak` (ADR-0004), presets FFTA.
- **Notes** : **incohérence corrigée le 17/07/2026** — l'ex-`E04US016` déclarait « Dépend de E06US003 » alors que `E06US003` (barrage de places au classement) dépend elle-même de l'ex-`E04US016` : cycle. La saisie du shoot-off est le **mécanisme**, le classement de barrage en est un **consommateur** ; la dépendance ne va que dans un sens (`E06US003` → cette US). La dépendance inverse est retirée.
- **Absorbe** : ex-E04US013, E04US014, E04US016. **Dépend de** : E01US011, E05US005 · **Jalon** : J2

### E04US015 — Gérer abandon / disqualification
*En tant que* scoreur, *je veux* enregistrer un abandon/DSQ, *afin de* refléter la réalité.
- **CA** : statut spécial sur un archer/match ; impact correct sur la progression et le classement ; **les flèches déjà tirées sont préservées** — un archer qui abandonne reste dans les résultats avec son statut, il n'en disparaît pas.
- **Notes** : c'est l'**alternative désignée à la suppression d'archer** (E02US003) pour l'abandon en **qualification** — le seul cas exerçable avant les duels ([ADR-0016](../docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md), arbitrage métier du 16/07/2026). La préservation des flèches n'est pas un détail d'implémentation : c'est **ce qui distingue** l'abandon de la suppression, laquelle les détruit. Un abandon qui effacerait les résultats rendrait ADR-0016 faux. **E12US004 élargit** cette US aux duels (forfait daté, attribué, réversible, audité). Tant que cette US n'est pas livrée, un archer qui abandonne n'a **aucun** moyen propre d'être enregistré, et la suppression est à portée de clic pour faire exactement la mauvaise chose — d'où sa priorité.
  > **Restée séparée au regroupement ÷3 du 17/07/2026** (elle n'a pas rejoint « Saisie en duels ») : elle est **ancrée par [ADR-0016]** (qui lui fait porter l'abandon en qualification *et*, via E12US004, aux duels) — un ancrage ADR ne se fond pas dans une US de capacité. *Incohérence latente à signaler, non tranchée ici : le jalon (J2) et la dépendance (duels) contredisent le « abandon en qualification » de la note ; à arbitrer hors refactor de maille.*
- **Dépend de** : E04US013 · **Jalon** : J2

### E04US018 — Afficher la prochaine cible après validation
*En tant qu'*archer, *je veux* voir **où je tire ensuite** dès que le scoreur a validé, *afin de* ne pas avoir à chercher ni à demander.
- **CA** : dès la validation (E04US002), la tablette **bascule en panneau de routage** : pour **chaque** archer de la cible, sa **prochaine affectation** (cible, position, heure, tour), son **repêchage**, ou son **rang final** s'il est éliminé ; l'affichage est **instantané** — rien n'est calculé à cet instant (`D-08`) ; retour à la grille pour la suite.
- **Notes** : `D-09` — **canal n°1 des 4 canaux de routage**, et **besoin absent des 117 US d'origine**. Ne couvre **que celui qui est encore là** : l'archer valide, range ses flèches et part — **l'info doit le suivre** sur son téléphone (**E07US008**). Fonctionne parce que **les cibles sont attribuées aux *matchs*** (positions de tableau), pas aux archers : « le match n°3 des 1/8ᵉ se tire sur la cible 4, quel que soit son vainqueur » → l'info existe **avant même le duel** (E03US009).
- **Dépend de** : E04US002, E03US009 · **Jalon** : J2

---

## Correspondance ancien → nouveau (maille ÷3 du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E04US001 | Rattacher une tablette à sa cible | **E04US001** (inchangée) |
| E04US002 | Afficher la grille de saisie | **E04US002** — CA « grille » |
| E04US003 | Saisir les flèches (pavé) | **E04US002** — CA « pavé » |
| E04US004 | Valider les valeurs autorisées | **E04US002** — CA « valeurs légales » |
| E04US005 | Enregistrer une volée via la file | **E04US002** — CA « enregistrement » |
| E04US006 | Éditer une volée non validée | **E04US002** — CA « édition avant validation » |
| E04US007 | Verrouiller une série validée | **E04US002** — CA « validation & verrou » |
| E04US008 | Cumuler le score sur les volées | **E04US002** — CA « cumul » |
| E04US009 | Diffuser la mise à jour en live | **E04US009** — CA « diffusion live » |
| E04US010 | Mettre en file hors-ligne + rejouer | **E04US009** — CA « file hors-ligne » |
| E04US011 | Indicateur d'état de connexion | **E04US009** — CA « indicateur » |
| E04US012 | Corriger une volée validée (tracé) | **E04US002** — CA « correction tracée » |
| E04US013 | Saisie en sets (duels) | **E04US013** — CA « sets » |
| E04US014 | Désigner le vainqueur d'un match | **E04US013** — CA « vainqueur » |
| E04US015 | Gérer abandon / disqualification | **E04US015** (inchangée) |
| E04US016 | Déclencher un barrage/shoot-off | **E04US013** — CA « barrage/shoot-off » |
| E04US017 | Désigner et tracer le marqueur | **E04US002** — CA « marqueur » |
| E04US018 | Afficher la prochaine cible après validation | **E04US018** (inchangée) |
