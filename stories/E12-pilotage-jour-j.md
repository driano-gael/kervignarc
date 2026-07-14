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

---

### E12US001 — Superviser les postes de saisie
*En tant qu'*organisateur, *je veux* voir l'état de mes ~30 postes en direct, *afin de* distinguer **« ils tirent lentement »** de **« leur tablette est morte »** — et d'agir avant que ça bloque.
- **CA** : liste de tous les postes du tournoi avec, pour chacun, son **état** (*en ligne* · *hors ligne* · *non rattaché*), sa **dernière activité** (« il y a 14 mn ») et son **avancement** (« volée 8/12 ») ; compteur global (« 28/30 en ligne ») ; **les écrans de salle y figurent** au même titre que les cibles (E07US004) ; mise à jour **live** (WebSocket, E04US009) sans action de l'admin ; l'admin peut **réinitialiser / révoquer** un poste (E04US001, `D-07`) ; l'**IP est affichée en diagnostic** — pour aider à retrouver physiquement un poste — **jamais comme identité** (`D-06`).
- **Notes** : `D-06`, `D-21` · [CDC UX §7.1](../cahier-des-charges-ux.md). **Ce n'est pas un graphique de progression : c'est une console de supervision.** *Un écran figé ne se plaint pas* — sans elle, l'admin confond « lent » et « mort », et envoie quelqu'un courir pour rien. **Forme de l'alerte** : un poste hors ligne est un **aplat ambre `#FFB000`** (9,22:1 sur le fond sombre), **jamais une pastille rouge** — sur l'anthracite de la charte, le rouge ne fait que 2,55:1 et **ne signale rien** ([CDC design §3.3](../cahier-des-charges-design.md), `DV-03`). Couleur **+ icône + texte**, jamais la couleur seule.
- **Dépend de** : E04US001, E10US002 · **Jalon** : J1

### E12US002 — Feu vert : voir ce qui manque avant de lancer
*En tant qu'*organisateur, *je veux* voir **en permanence** ce qui manque pour lancer la suite, *afin de* ne pas le découvrir en appuyant sur le bouton.
- **CA** : l'état de préparation est **affiché en continu**, pas calculé au moment du clic ; pour chaque événement (duel) à venir : **duel source validé ?** · **cible attribuée ?** · **participants connus ?** ; ce qui bloque est **nommé** (« en attente : 1/4 n°3 non validé »), pas seulement signalé ; **l'appli n'empêche rien** — elle montre (`P-3`).
- **Notes** : `D-23` · [CDC UX §8.2](../cahier-des-charges-ux.md). **Ouverte — `Q-UX6`** : la **liste exacte des métriques** du feu vert reste à arrêter (poste en ligne ? scoreur disponible ? conflit de placement ?). Les CA ci-dessus sont le **socle minimal** ; l'US ne sera close qu'une fois `Q-UX6` tranchée.
- **Dépend de** : E05US008, E03US009 · **Jalon** : J2

### E12US003 — Lancer un tour ou un événement
*En tant qu'*organisateur, *je veux* lancer le tour suivant **d'un geste**, *afin que* 150 archers sachent où aller **en moins de deux minutes**.
- **CA** : **le bouton ne calcule rien** — au moment où le dernier duel est validé, le tour suivant est **déjà prêt, affiché, contrôlé** ; **le bouton chiffre ce qu'il déclenche** (`P-4`) : pas « Tour suivant » mais « **2 duels, cibles 4 et 7, 14h20 — 118 personnes vont être prévenues** » ; **l'unité lançable est l'événement (le duel), pas le tour** — deux duels prêts et un qui attend sa source ? **on fait partir les deux** (`D-23`) ; le **lancement global** reste disponible ; à l'appui, les **4 canaux** sont servis ensemble (`D-09`) : tablettes (E04US018), téléphones (E07US008), écran de salle (E07US004), table de l'organisation (E12US006).
- **Notes** : `D-22`, `D-23`, `D-25` · [CDC UX §8.1](../cahier-des-charges-ux.md). **La journée a un maître de cérémonie, et ce n'est pas le logiciel** : l'appli prépare, contrôle, affiche — et **attend**. L'admin appuie quand l'arbitre est prêt. **Pourquoi tout doit être prêt avant** : sinon on a remplacé 20 minutes de recopie par 20 secondes de sablier, **et le doute revient**. Le **calcul** du tour suivant est **EPIC-05**, pas cette US.
- **Dépend de** : E12US002, E05US008, E03US009 · **Jalon** : J2

### E12US004 — Tracer un forfait
*En tant qu'*organisateur, *je veux* déclarer un archer absent **sans bloquer le tour**, *afin que* la compétition continue et que l'absence reste documentée.
- **CA** : l'archer absent **n'est pas un trou dans le tableau** : c'est une **donnée** — forfait **daté**, **attribué**, motif optionnel ; **l'adversaire passe** et le tableau reste cohérent (E05US008) ; **rien n'est jamais bloqué** (`P-3`) ; **trace d'audit** (E10US005) ; réversible tant que le tournoi n'est pas terminé (`D-15`).
- **Notes** : `D-24` · [CDC UX §8.2](../cahier-des-charges-ux.md). **Élargit E04US015** (abandon / DSQ) : même famille — *rien ne bloque, tout se documente*. **Ouverte — `Q-UX5`** : **qui déclare le forfait** (l'admin, le marqueur sur la tablette, le scoreur) ? Les CA supposent **l'admin** par défaut ; à confirmer avant réalisation.
- **Dépend de** : E04US015, E05US008 · **Jalon** : J2

### E12US005 — Afficher la complétude du tournoi
*En tant qu'*organisateur, *je veux* savoir **ce qui manque pour que ce tournoi soit fini**, *afin de* ne pas le terminer en laissant des trous.
- **CA** : répond à la question « **qu'est-ce qui manque ?** » — **pas** une barre de progression ; **le sportif et le hors sportif sont comptés séparément** (`D-17`) : *Sportif* (qualification 30/30 cibles, 1/8 8/8 duels, 1/4 **3/4 duels** ⚠️, classement en attente) et *Hors sportif* (**paiements 144/156**) ; l'écran **dit ce que « terminer » implique** : « **figera le sportif ; les paiements resteront modifiables** » ; **contrôle en amont** du passage à *terminé* : « 2 duels ne sont pas validés, 12 archers n'ont pas payé. Terminer quand même ? » ; live.
- **Notes** : `D-17`, `D-18` · [CDC UX §8.3](../cahier-des-charges-ux.md). **C'est le vrai visage de « afficher l'avancement du tournoi »** (demande client). **Pourquoi séparer sportif et tiers** : « terminé = tout figé » **empêcherait d'encaisser un chèque en retard** — un archer règle la semaine suivante, le tournoi terminé n'a rien à y redire. Passer à *terminé* est **la seule action irréversible de l'appli** (E01US002).
- **Dépend de** : E01US002, E08US002 · **Jalon** : J1

### E12US006 — Rechercher un archer depuis n'importe où
*En tant que* bénévole de la table d'organisation, *je veux* retrouver un archer **depuis n'importe quel écran**, *afin de* répondre à celui qui vient demander « je tire où ? ».
- **CA** : champ de recherche **dans la sidebar, en haut, présent en permanence** (`D-19`) — quel que soit l'écran affiché ; recherche **par nom** (tolérante à la casse et aux accents) ; le résultat donne **immédiatement** ce qu'on vient demander : **cible, position, départ**, et **la prochaine affectation** si elle existe (`D-09`) ; accessible au **clavier**.
- **Notes** : `D-10`, `D-19` · [CDC UX §7.1](../cahier-des-charges-ux.md). **La table de l'organisation est un humain, pas une borne** (`D-10`) : c'est pourquoi cette recherche est **dans l'appli admin** et qu'il n'y a **pas de borne partagée** en libre-service — « retour automatique à l'accueil » et « mémoriser c'est moi » (E07US006) se contrediraient. **C'est le 4ᵉ canal de routage.**
- **Dépend de** : E02US002, E03US008 · **Jalon** : J1

### E12US007 — Alerter par calcul d'impact
*En tant qu'*organisateur, *je veux* que l'appli ne me demande confirmation **que quand ça compte**, *afin de* ne pas apprendre à cliquer « oui » sans lire.
- **CA** : **règle transverse** à toutes les écritures ; l'appli **calcule l'impact réel au moment où on agit** — elle **ne classe pas les actions d'avance** ; **pas d'impact → aucune alerte** (changer le gabarit avant tout placement ; modifier une phase non jouée **même tournoi en cours** ; inscrire un retardataire pendant la qualification) ; **impact → alerte chiffrée** : « **156 archers perdront leur place ; 4 cibles ont déjà des scores, ils seront conservés** » ; les **actions massives** exigent un **geste délibéré** (taper un mot, ex. `REPLACER`) — impossible par réflexe ; **trace d'audit** (E10US005) ; **aucune action n'est refusée** tant que le tournoi n'est pas *terminé* (`D-15`).
- **Notes** : `P-4`, `D-15`, `D-16` · [CDC UX §9.1](../cahier-des-charges-ux.md). **Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection.** Si l'appli demande confirmation pour tout, l'admin apprend à cliquer « oui » sans lire — **et le jour où ça compte, il clique « oui » sans lire**. **La ligne de partage n'est ni *brouillon / en cours*, ni *sportif / tiers*, mais : *est-ce que ça a déjà produit des données réelles ?*** S'applique aussi au **contrôle de contraste** d'E01US016 (`DV-05` : avertir en chiffrant, ne pas refuser).
- **Dépend de** : E10US005 · **Jalon** : J1
