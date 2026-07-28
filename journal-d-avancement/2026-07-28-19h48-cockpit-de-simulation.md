# 28 juillet 2026, 19 h 48 — Un cockpit pour rejouer un tournoi en accéléré

**Pour qui :** l'organisateur (démo au client, mise au point avant le jour J).

## Ce qui est nouveau

Un nouvel écran d'administration, **« Simulation »**, permet de **rejouer un tournoi de bout en bout,
en accéléré, sans rien enregistrer**. On choisit un tournoi (pas encore lancé), on clique
**« Démarrer »**, et un **robot** se met à jouer tout seul : il génère des scores plausibles, remplit
les qualifications, puis déroule les duels jusqu'au classement et au podium — le tout en quelques
secondes.

C'est un **pilote automatique qu'on peut mettre en pause** à tout moment. En pause, on peut **prendre
la main à la place d'un rôle** : saisir soi-même la volée qu'allait jouer une cible, ou désigner le
vainqueur d'un duel comme le ferait un scoreur. Puis on **rend la main** au robot, qui reprend là où
on l'a laissé.

Un **jeu d'onglets** en haut de l'écran fait basculer entre **quatre points de vue** du tournoi
simulé :

- **Public** : le classement en direct et les tableaux de duels (avec le podium) ;
- **Cible** : la volée en cours de saisie (et le formulaire de saisie quand on prend la main) ;
- **Archer** : la « journée » d'un archer au choix — ses volées, son cumul ;
- **Scoreur** : les duels du moment, avec les boutons pour désigner un vainqueur en pause.

Un réglage de **vitesse** (Lent / Normal / Rapide) accélère ou ralentit le robot pour la démo.

## Ce que ça change

- **Pour démontrer le produit** : plus besoin de saisir des scores à la main devant le client — on
  lance la simulation et on **raconte le déroulé** en direct, en changeant de point de vue.
- **Pour vérifier** : on peut s'assurer d'un coup d'œil que tout **s'enchaîne** (qualif → duels →
  podium) sur un tournoi de test, avant le jour J.

## Les garde-fous

- **Rien n'est jamais enregistré** : la simulation joue sur des copies **en mémoire**, la vraie base
  n'est pas touchée. On ne peut d'ailleurs simuler qu'un tournoi **avant son démarrage** (un tournoi
  en cours ou terminé est refusé) — impossible de polluer une compétition réelle par mégarde.
- Avec la même **graine**, la simulation rejoue **exactement le même déroulé** — utile pour retomber
  sur un cas précis.

> **À vérifier à l'écran.** Cet écran n'a pas de tests automatiques d'affichage : son rendu et son
> ergonomie restent à éprouver sur un vrai appareil.

Cette US **clôt le chantier « Jeu d'essai & simulation »** (EPIC-15) : générer des inscrits, rejouer
le moteur, et maintenant piloter et observer le tout.
