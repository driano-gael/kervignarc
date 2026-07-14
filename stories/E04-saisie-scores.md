# E04 — Saisie des scores en temps réel — User Stories

> EPIC : [EPIC-04](../epics/EPIC-04-saisie-scores.md) · Réfs : CDC fonctionnel M5, ADR-0005, **CDC UX §4 et §7.2**.

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
- **Notes** : ~~« saisie d'un code de cible → session **scoreur** rattachée », v0.1~~ → **réécrite le 14/07/2026** (`D-06`, `D-07`). **Ni IP, ni empreinte** : les baux DHCP expirent (une tablette en veille perd sa cible) et une IP réattribuée ferait **partir les scores sur la mauvaise cible, silencieusement** — *un score faux et silencieux est pire qu'une erreur visible* ; l'empreinte ne distingue pas **30 tablettes identiques**. Réutilise le patron de `sessionAdminStore` (Zustand + `persist`, jeton `Bearer`, purge sur 401) → **`sessionPosteStore`** : ni concept nouveau, ni configuration réseau. **Piège traité par les CA** : *le jeton survit trop bien* — au tournoi suivant, la tablette de la cible 12 posée sur la cible 5 croirait toujours être la 12. **Le jeton porte les préférences, pas seulement le rattachement** (`D-26`, [CDC UX §4.5](../cahier-des-charges-ux.md)) : *dans un gymnase, la lumière varie d'une cible à l'autre* — la tablette sous la baie vitrée passe en thème clair, les 29 autres ne bougent pas. Sans ça, `D-05` (pas de kiosque, l'onglet se ferme) obligerait le bénévole à rebasculer son thème **à chaque réouverture**.
- **Dépend de** : E03US008, E01US001 · **Jalon** : J1

### E04US002 — Afficher la grille de saisie (4 archers)
*En tant que* **marqueur**, *je veux* voir les archers de ma cible, *afin de* saisir leurs scores.
- **CA** : liste des archers/positions de la cible **(déduite du jeton de poste, E04US001 — rien à choisir)** ; volée courante mise en évidence ; **le grain de validation actif est indiqué** (« validation à la fin de la série ») — sans ça le marqueur ne sait pas quand le scoreur viendra (`D-11`) ; adapté au tactile (**cibles ≥ 48 px**, plancher **768 px**, `D-02`).
- **Dépend de** : E04US001 · **Jalon** : J1

### E04US003 — Saisir les flèches d'une volée (pavé tactile)
*En tant que* scoreur, *je veux* saisir chaque flèche via un pavé, *afin de* renseigner rapidement.
- **CA** : pavé de valeurs **déduit du blason tiré** (`Blason.zones`, E01US014) et non du barème de la phase — sur un triple 40 les touches 5→1 n'existent pas (FFTA §4.4) ; gros boutons ; correction avant validation.
- **Dépend de** : E01US014
- **Dépend de** : E04US002 · **Jalon** : J1

### E04US004 — Valider les valeurs autorisées
*En tant que* système, *je veux* n'accepter que des valeurs légales, *afin d'*éviter les erreurs.
- **CA** : refus d'une valeur hors barème ; nb de flèches par volée conforme au barème (E01US009).
- **Dépend de** : E04US003 · **Jalon** : J1

### E04US005 — Enregistrer une volée via la file d'écriture
*En tant que* scoreur, *je veux* que ma volée soit enregistrée, *afin de* ne pas la perdre.
- **CA** : volée persistée par la **file d'écriture** (writer unique) ; accusé de réception au client.
- **Notes** : idempotence par identifiant de saisie (ADR-0005).
- **Dépend de** : E00US007, E04US004 · **Jalon** : J1

### E04US006 — Éditer une volée non validée
*En tant que* scoreur, *je veux* corriger une volée pas encore validée, *afin de* rectifier une saisie.
- **CA** : modification possible tant que la série n'est pas validée ; historique non requis à ce stade.
- **Dépend de** : E04US005 · **Jalon** : J1

### E04US007 — Verrouiller une série validée
*En tant que* scoreur, *je veux* valider une série, *afin de* la figer.
- **CA** : après validation, la série est **verrouillée** (non éditable sans correction habilitée) ; diffusée ; **la validation porte le nom du scoreur** (E10US003, alimente E10US005) ; **le grain de validation est lu dans la phase** (`config.validation`, E01US015) : fin de série, fin de duel, ou toutes les N volées.
- **Notes** : **la validation est un acte *de fin*** — FFTA : les feuilles de marque sont signées « à la fin de la distance, ou de la compétition, **ou du duel** ». L'art. B.6.1.2 (« établissement des scores toutes les 2 volées ») porte sur le **cumul** (E04US008, calculé par l'appli), **pas** sur la validation par un tiers : valider toutes les 2 volées ferait **~180 passages par départ** (intenable à 3 scoreurs). La validation du scoreur **tient lieu de seconde marque** (`D-03`, FFTA B.6.1.1 : « quand les compétiteurs sont marqueurs, la double marque est obligatoire ») — **`Q-UX3` : à confirmer par un arbitre du club.**
- **Dépend de** : E04US005, E01US015 · **Jalon** : J1

### E04US008 — Cumuler le score sur les volées
*En tant que* système, *je veux* cumuler les volées, *afin de* produire le score de qualif.
- **CA** : total mis à jour à chaque validation ; conforme au barème.
- **Dépend de** : E04US007 · **Jalon** : J1

### E04US009 — Diffuser la mise à jour en live
*En tant que* public/organisateur, *je veux* voir les scores en direct, *afin de* suivre l'épreuve.
- **CA** : après validation, diffusion WebSocket ; les abonnés (écran, mobile) se mettent à jour < 1-2 s.
- **Dépend de** : E00US008, E04US007 · **Jalon** : J1

### E04US010 — Mettre en file hors-ligne + rejouer
*En tant que* scoreur, *je veux* continuer à saisir malgré une coupure brève, *afin de* ne rien perdre.
- **CA** : saisies mises en file côté front hors-ligne ; rejeu à la reconnexion ; pas de doublon (idempotence).
- **Dépend de** : E04US005 · **Jalon** : J1

### E04US011 — Indicateur d'état de connexion
*En tant que* scoreur, *je veux* voir si je suis connecté, *afin de* savoir si mes saisies partent.
- **CA** : indicateur visible (connecté / hors-ligne / synchronisation en cours).
- **Dépend de** : E04US010 · **Jalon** : J1

### E04US012 — Corriger une volée validée (tracé)
*En tant qu'*administrateur/scoreur habilité, *je veux* corriger un score verrouillé, *afin de* réparer une erreur.
- **CA** : correction réservée aux rôles habilités ; entrée d'**AuditLog** (qui/quand/avant-après) ; recalcul du cumul.
- **Dépend de** : E04US007, E10US005 · **Jalon** : J1

### E04US013 — Saisie en sets (duels)
*En tant que* scoreur, *je veux* saisir un match au système de sets, *afin de* gérer les duels.
- **CA** : points de set attribués selon le barème (FFTA : premier à **6 pts** sur 5 sets ; format club : 4 pts) ; cumul des points de set du match ; **les arcs à poulies ne tirent pas en sets** mais au cumul (FFTA A.7.5.2) — le barème se résout par (phase, arme), cf. EF-3.4.
- **Dépend de** : E01US011, E05US007 · **Jalon** : J2

### E04US014 — Désigner le vainqueur d'un match
*En tant que* système, *je veux* déterminer le vainqueur, *afin de* faire progresser le tableau.
- **CA** : vainqueur calculé selon le barème de sets ; transmis au moteur (E05US008).
- **Dépend de** : E04US013 · **Jalon** : J2

### E04US015 — Gérer abandon / disqualification
*En tant que* scoreur, *je veux* enregistrer un abandon/DSQ, *afin de* refléter la réalité.
- **CA** : statut spécial sur un archer/match ; impact correct sur la progression et le classement.
- **Dépend de** : E04US014 · **Jalon** : J2

### E04US016 — Déclencher un barrage/shoot-off (égalité)
*En tant que* scoreur, *je veux* résoudre une égalité par barrage, *afin de* départager.
- **CA** : à égalité, saisie d'un shoot-off (1 flèche) ; plus près du centre départage ; vainqueur enregistré.
- **Notes** : politique `tiebreak` (ADR-0004) ; presets FFTA.
- **Dépend de** : E04US014, E06US003 · **Jalon** : J2

### E04US017 — Désigner et tracer le marqueur
*En tant que* **marqueur**, *je veux* que l'appli sache **qui saisit**, *afin de* remplacer la signature de la feuille de marque et de pouvoir passer le relais.
- **CA** : au début du départ, on **désigne le ou les marqueurs** parmi les archers de la cible (**plusieurs possibles**) ; le **marqueur actif** est **affiché discrètement et se change en un geste** ; **chaque volée enregistre qui l'a saisie**, consultable (« volée 7 saisie par DURAND, 10h42 ») ; alimente **E10US005** ; **déclaratif, pas authentifié** (E10US007 : le poste reste ouvert).
- **Notes** : `D-04`. **Contrainte d'ergonomie ferme** : *le marqueur change rarement, donc l'interface ne s'organise pas autour de ce changement* — **pas de sélecteur permanent** qui trône au-dessus de la grille et vole de l'espace au pavé (**discret par défaut, disponible au besoin**). Fondement : FFTA B.6.1.1 (« un marqueur doit être désigné à chaque cible », plusieurs possibles) et l'exigence de **signature de la feuille de marque par l'archer et le marqueur** — **la trace est l'équivalent numérique de cette signature**, seul argument sérieux face à un arbitre qui contesterait la dématérialisation.
- **Dépend de** : E04US002, E10US007 · **Jalon** : J1

### E04US018 — Afficher la prochaine cible après validation
*En tant qu'*archer, *je veux* voir **où je tire ensuite** dès que le scoreur a validé, *afin de* ne pas avoir à chercher ni à demander.
- **CA** : dès la validation (E04US007), la tablette **bascule en panneau de routage** : pour **chaque** archer de la cible, sa **prochaine affectation** (cible, position, heure, tour), son **repêchage**, ou son **rang final** s'il est éliminé ; l'affichage est **instantané** — rien n'est calculé à cet instant (`D-08`) ; retour à la grille pour la suite.
- **Notes** : `D-09` — **canal n°1 des 4 canaux de routage**, et **besoin absent des 117 US d'origine**. Ne couvre **que celui qui est encore là** : l'archer valide, range ses flèches et part — **l'info doit le suivre** sur son téléphone (**E07US008**). Fonctionne parce que **les cibles sont attribuées aux *matchs*** (positions de tableau), pas aux archers : « le match n°3 des 1/8ᵉ se tire sur la cible 4, quel que soit son vainqueur » → l'info existe **avant même le duel** (E03US009).
- **Dépend de** : E04US007, E03US009 · **Jalon** : J2
