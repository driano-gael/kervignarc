# E12 — Pilotage du jour J — User Stories

> EPIC : [EPIC-12](../epics/EPIC-12-pilotage-jour-j.md) · Réfs : [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §1, §7.1, §8, §9 (`D-15`→`D-25`) ; CDC fonctionnel M3/M5.

> 🎯 **C'est ici que se trouve la valeur du produit.** Le coût réel d'un tournoi n'est pas la lenteur de la
> saisie : c'est le **temps mort entre deux tours** — quelqu'un ramasse les feuilles, recopie, calcule,
> constitue le tableau suivant, l'imprime, l'affiche, **pendant que 150 archers attendent**.
>
> **Métrique de l'EPIC** (`D-25`) : **« dernier duel validé » → « les archers savent où aller » en < 2 min.**
>
> **EPIC créé le 14/07/2026** : les 12 EPICs existants couvraient la configuration, les inscriptions, le
> placement, la saisie, le moteur, les classements, l'affichage, les paiements, les exports, les rôles et
> l'exploitation — **aucun ne couvrait le pilotage du jour J**, alors que c'est là que se joue la valeur.

> ⚠️ **Ce que cet EPIC ne fait pas.** Il porte **le geste et l'affichage**, jamais le calcul : le tour suivant
> est calculé par **EPIC-05** (routage, seeding, byes) et affiché aux archers par **EPIC-07** (E07US008) et
> **EPIC-04** (E04US018). **Ici on lance ; là-bas on calcule et on affiche.**

> ⚠️ **Maille révisée le 17/07/2026** — E12 était déjà largement au grain « capacité » : un **seul
> regroupement** est fait ici (8 → 7 US), celui du feu vert et du lancement (ex-`E12US002` + ex-`E12US003`),
> **indissociables** — les deux partagent le même invariant (`D-23` : l'unité lançable est l'événement, pas
> le tour) et le geste de lancement ne se comprend pas sans l'affichage continu qui le précède. Les **6
> autres capacités restent séparées** : chacune porte un **arbitrage distinct**, ancré à un ADR ou une
> entrée propre du registre `D`/`Q` (`D-06`/`D-21` pour la supervision des postes, `D-17`/`D-18` pour la
> complétude, `D-10`/`D-19` pour la recherche, `P-4`/`D-15`/`D-16` pour l'alerte transverse,
> [ADR-0016](../docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)/`D-24`/`Q-UX5` pour le
> forfait, [ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md) pour le cycle de
> vie d'un départ) — les fondre les enterrerait sous un intitulé générique. **Aucun comportement n'est
> perdu** (règle 9) : chaque ancien titre reste identifiable. Correspondance ancien → nouveau en fin de
> fichier.

---

### E12US001 — Superviser les postes de saisie
*En tant qu'*organisateur, *je veux* voir l'état de mes ~30 postes en direct, *afin de* distinguer **« ils tirent lentement »** de **« leur tablette est morte »** — et d'agir avant que ça bloque.
- **CA** : liste de tous les postes du tournoi avec, pour chacun, son **état** (*en ligne* · *hors ligne* · *non rattaché*), sa **dernière activité** (« il y a 14 mn ») et son **avancement** (« volée 8/12 ») ; compteur global (« 28/30 en ligne ») ; **les écrans de salle y figurent** au même titre que les cibles (E07US004) ; mise à jour **live** (WebSocket, E04US009) sans action de l'admin ; l'admin peut **réinitialiser / révoquer** un poste (E04US001, `D-07`) ; l'**IP est affichée en diagnostic** — pour aider à retrouver physiquement un poste — **jamais comme identité** (`D-06`).
- **Notes** : `D-06`, `D-21` · [CDC UX §7.1](../cahier-des-charges-ux.md). **Ce n'est pas un graphique de progression : c'est une console de supervision.** *Un écran figé ne se plaint pas* — sans elle, l'admin confond « lent » et « mort », et envoie quelqu'un courir pour rien. **Forme de l'alerte** : un poste hors ligne est un **aplat ambre `#FFB000`** (9,22:1 sur le fond sombre), **jamais une pastille rouge** — sur l'anthracite de la charte, le rouge ne fait que 2,55:1 et **ne signale rien** ([CDC design §3.3](../cahier-des-charges-design.md), `DV-03`). Couleur **+ icône + texte**, jamais la couleur seule.
- **Arbitrages (tranchés le 20/07/2026 à la réalisation)** :
  - **Détection en ligne / hors ligne = heartbeat**, pas connexion WebSocket ([ADR-0038](../docs/adr/0038-presence-des-postes-par-heartbeat.md)). Rien ne suivait l'état de connexion côté serveur (le `Broadcaster` est anonyme) ; le poste pingue (~10 s), hors ligne si silence > **30 s**. Horloge injectée (déterminisme, règle 9). **« Dernière activité » ≠ heartbeat** : c'est la dernière **saisie** sur la cible (sinon un poste en ligne afficherait toujours « il y a 3 s » et la **lenteur serait invisible** — le cœur du CA). Le heartbeat dit *vivant/mort*, la saisie dit *avance/stagne*.
  - **Écran de salle reporté à E07US004** : le modèle `Poste` n'a pas de notion de *type* et l'écran de salle n'existe pas encore comme poste rattaché. On supervise les postes de **cible** ici ; la ligne « les écrans de salle y figurent » se réalisera **avec E07US004** (J3). Aucun comportement perdu (règle 9), seulement séquencé.
  - **Couleur hors ligne = token sémantique `--warn`**, pas la charte club en dur : `#FFB000`/anthracite est une décision des **US design** et reskinnera automatiquement. L'invariant réellement porté ici est celui du CA : **couleur + icône + texte**, jamais la couleur seule (`DV-03`).
  - **« Réinitialiser » ≡ « révoquer »** ([ADR-0038](../docs/adr/0038-presence-des-postes-par-heartbeat.md) §5) : les deux mots du CA désignent le **même geste** — fermer la session du poste pour forcer le re-rattachement. **Régénérer** le *code* de cible est un autre sujet (E09US008, réimpression des QR), pas cette US. Aucun comportement perdu.
- **Dépend de** : E04US001, E10US002 · **Jalon** : J1

### E12US002 — Lancer un tour (feu vert + lancement)
*En tant qu'*organisateur, *je veux* voir **en permanence** ce qui manque pour lancer la suite puis lancer le tour suivant **d'un geste**, *afin de* ne jamais découvrir un blocage en appuyant sur le bouton et que 150 archers sachent où aller **en moins de deux minutes**.
- **CA — feu vert (ex-002)** : l'état de préparation est **affiché en continu**, pas calculé au moment du clic ; pour chaque événement (duel) à venir : **duel source validé ?** · **cible attribuée ?** · **participants connus ?** ; ce qui bloque est **nommé** (« en attente : 1/4 n°3 non validé »), pas seulement signalé ; **l'appli n'empêche rien** — elle montre (`P-3`).
- **CA — lancement (ex-003)** : **le bouton ne calcule rien** — au moment où le dernier duel est validé, le tour suivant est **déjà prêt, affiché, contrôlé** ; **le bouton chiffre ce qu'il déclenche** (`P-4`) : pas « Tour suivant » mais « **2 duels, cibles 4 et 7, 14h20 — 118 personnes vont être prévenues** » ; **l'unité lançable est l'événement (le duel), pas le tour** — deux duels prêts et un qui attend sa source ? **on fait partir les deux** (`D-23`) ; le **lancement global** reste disponible ; à l'appui, les **4 canaux** sont servis ensemble (`D-09`) : tablettes (E04US018), téléphones (E07US008), écran de salle (E07US004), table de l'organisation (E12US006).
- **Notes** : `D-22`, `D-23`, `D-25` · [CDC UX §8.1](../cahier-des-charges-ux.md), [§8.2](../cahier-des-charges-ux.md). **Ouverte — `Q-UX6`** : la **liste exacte des métriques** du feu vert reste à arrêter (poste en ligne ? scoreur disponible ? conflit de placement ?). Les CA « feu vert » ci-dessus sont le **socle minimal** ; l'US ne sera close qu'une fois `Q-UX6` tranchée. **La journée a un maître de cérémonie, et ce n'est pas le logiciel** : l'appli prépare, contrôle, affiche — et **attend**. L'admin appuie quand l'arbitre est prêt. **Pourquoi tout doit être prêt avant** : sinon on a remplacé 20 minutes de recopie par 20 secondes de sablier, **et le doute revient**. Le **calcul** du tour suivant est **EPIC-05**, pas cette US.
- **Absorbe** : ex-E12US003. **Dépend de** : E05US005, E03US009 · **Jalon** : J2

### E12US004 — Tracer un forfait
*En tant qu'*organisateur, *je veux* déclarer un archer absent **sans bloquer le tour**, *afin que* la compétition continue et que l'absence reste documentée.
- **CA** : l'archer absent **n'est pas un trou dans le tableau** : c'est une **donnée** — forfait **daté**, **attribué**, motif optionnel ; **les flèches déjà tirées sont préservées** (le forfait ne les efface jamais) ; **l'adversaire passe** et le tableau reste cohérent (E05US005) ; **rien n'est jamais bloqué** (`P-3`) ; **trace d'audit** (E10US005) ; réversible tant que le tournoi n'est pas terminé (`D-15`).
- **Notes** : `D-24` · [CDC UX §8.2](../cahier-des-charges-ux.md). **Élargit E04US015** (abandon / DSQ, qui porte le cas **qualification**) : même famille — *rien ne bloque, tout se documente*. La **préservation des flèches** est la propriété sur laquelle repose [ADR-0016](../docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) : c'est **ce qui distingue** le forfait de la **suppression** d'archer (E02US003), laquelle les détruit. Un forfait qui effacerait les résultats rendrait cet ADR faux. **Ouverte — `Q-UX5`** : **qui déclare le forfait** (l'admin, le marqueur sur la tablette, le scoreur) ? Les CA supposent **l'admin** par défaut ; à confirmer avant réalisation.
- **Dépend de** : E04US015, E05US005 · **Jalon** : J2

### E12US005 — Afficher la complétude du tournoi
*En tant qu'*organisateur, *je veux* savoir **ce qui manque pour que ce tournoi soit fini**, *afin de* ne pas le terminer en laissant des trous.
- **CA** : répond à la question « **qu'est-ce qui manque ?** » — **pas** une barre de progression ; **le sportif et le hors sportif sont comptés séparément** (`D-17`) : *Sportif* (qualification 30/30 cibles, 1/8 8/8 duels, 1/4 **3/4 duels** ⚠️, classement en attente) et *Hors sportif* (**paiements 144/156**) ; l'écran **dit ce que « terminer » implique** : « **figera le sportif ; les paiements resteront modifiables** » ; **contrôle en amont** du passage à *terminé* : « 2 duels ne sont pas validés, 12 archers n'ont pas payé. Terminer quand même ? » ; live.
- **Notes** : `D-17`, `D-18` · [CDC UX §8.3](../cahier-des-charges-ux.md). **C'est le vrai visage de « afficher l'avancement du tournoi »** (demande client). **Pourquoi séparer sportif et tiers** : « terminé = tout figé » **empêcherait d'encaisser un chèque en retard** — un archer règle la semaine suivante, le tournoi terminé n'a rien à y redire. Passer à *terminé* est **la seule action irréversible de l'appli** (E01US002).
- **Dépend de** : E01US002, E08US002 · **Jalon** : J1

### E12US006 — Rechercher un archer depuis n'importe où
*En tant que* bénévole de la table d'organisation, *je veux* retrouver un archer **depuis n'importe quel écran**, *afin de* répondre à celui qui vient demander « je tire où ? ».
- **CA** : champ de recherche **dans la sidebar, en haut, présent en permanence** (`D-19`) — quel que soit l'écran affiché ; recherche **par nom** (tolérante à la casse et aux accents) ; le résultat donne **immédiatement** ce qu'on vient demander : **cible, position, départ**, et **la prochaine affectation** si elle existe (`D-09`) ; accessible au **clavier**.
- **Notes** : `D-10`, `D-19` · [CDC UX §7.1](../cahier-des-charges-ux.md). **La table de l'organisation est un humain, pas une borne** (`D-10`) : c'est pourquoi cette recherche est **dans l'appli admin** et qu'il n'y a **pas de borne partagée** en libre-service — « retour automatique à l'accueil » et « mémoriser c'est moi » (E07US006) se contrediraient. **C'est le 4ᵉ canal de routage.**
- **Dépend de** : E02US002, E03US001 · **Jalon** : J1

### E12US007 — Alerter par calcul d'impact
*En tant qu'*organisateur, *je veux* que l'appli ne me demande confirmation **que quand ça compte**, *afin de* ne pas apprendre à cliquer « oui » sans lire.
- **CA** : **règle transverse** à toutes les écritures ; l'appli **calcule l'impact réel au moment où on agit** — elle **ne classe pas les actions d'avance** ; **pas d'impact → aucune alerte** (changer le gabarit avant tout placement ; modifier une phase non jouée **même tournoi en cours** ; inscrire un retardataire pendant la qualification) ; **impact → alerte chiffrée** : « **156 archers perdront leur place ; 4 cibles ont déjà des scores, ils seront conservés** » ; les **actions massives** exigent un **geste délibéré** (taper un mot, ex. `REPLACER`) — impossible par réflexe ; **trace d'audit** (E10US005) ; **aucune action n'est refusée** tant que le tournoi n'est pas *terminé* (`D-15`).
- **Notes** : `P-4`, `D-15`, `D-16` · [CDC UX §9.1](../cahier-des-charges-ux.md). **Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection.** Si l'appli demande confirmation pour tout, l'admin apprend à cliquer « oui » sans lire — **et le jour où ça compte, il clique « oui » sans lire**. **La ligne de partage n'est ni *brouillon / en cours*, ni *sportif / tiers*, mais : *est-ce que ça a déjà produit des données réelles ?*** S'applique aussi au **contrôle de contraste** d'E01US016 (`DV-05` : avertir en chiffrant, ne pas refuser).
- **Dépend de** : E10US005 · **Jalon** : J1

### E12US008 — Cycle de vie d'un départ (créneau)
*En tant qu'*organisateur, *je veux* qu'un départ **déjà lancé ou clos** ne se modifie ni ne se supprime comme un créneau encore ouvert, *afin de* ne pas détruire une session en cours de tir.
- **CA** : un départ porte un **état** (*ouvert* · *lancé* · *clos*) ; supprimer ou modifier un créneau **lancé/clos** est **contrôlé** (au moins signalé, cf. E12US007 « alerter par calcul d'impact ») là où un créneau *ouvert* reste librement éditable ; l'état est **dérivé** d'un fait réel (heure atteinte, premier score du créneau) et non saisi à la main.
- **Notes** : **déportée d'E02US009** ([ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)). E02US009 n'a **rien** pour distinguer un créneau lancé : `Depart` n'a pas d'état de cycle de vie, `horaire` est un libellé libre, et le lien départ → scores (placement) n'existe pas avant EPIC-03. Poser ce garde-fou plus tôt aurait été un contrôle qu'aucun chemin réel ne déclenche. Rejoint la logique d'**E12US007** (alerter selon l'impact réel, pas selon un statut saisi d'avance). **Dépend** de la modélisation du placement/déroulé.
- **Dépend de** : E02US009, E03US001, E12US007 · **Jalon** : J2

---

## Correspondance ancien → nouveau

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E12US001 | Superviser les postes de saisie | **E12US001** (inchangée) |
| E12US002 | Feu vert : voir ce qui manque avant de lancer | **E12US002** — CA « feu vert » |
| E12US003 | Lancer un tour ou un événement | **E12US002** — CA « lancement » |
| E12US004 | Tracer un forfait | **E12US004** (inchangée) |
| E12US005 | Afficher la complétude du tournoi | **E12US005** (inchangée) |
| E12US006 | Rechercher un archer depuis n'importe où | **E12US006** (inchangée) |
| E12US007 | Alerter par calcul d'impact | **E12US007** (inchangée) |
| E12US008 | Cycle de vie d'un départ (créneau) | **E12US008** (inchangée) |
