# E07 — Affichage public & écran projeté — User Stories

> EPIC : [EPIC-07](../epics/EPIC-07-affichage-public.md) · Réfs : CDC fonctionnel M6, **CDC UX §7.4–7.5**.

> ⚠️ **Révisé le 14/07/2026** ([`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §6, `D-09`/`D-21`).
> **L'appli publique n'est pas un tableau de résultats : c'est le fil de la journée de l'archer** — un GPS.
> Son besoin n°1 (**« où je tire ensuite »**) était **absent des 117 US**. Deux conséquences : l'archer
> **n'a pas à chercher** (« c'est moi » mémorisé, E07US006 ; affectations poussées, E07US008), et **l'écran
> de salle est un *poste* de cette appli** (E07US004 réécrite), supervisé et pilotable — pas une 4ᵉ
> application.

---

### E07US001 — Vue publique des classements
*En tant que* spectateur, *je veux* consulter les classements en lecture seule, *afin de* suivre le tournoi.
- **CA** : accès sans authentification ; lecture seule ; par catégorie ; responsive mobile.
- **Dépend de** : E06US001, E10US001 · **Jalon** : J1

### E07US002 — Live des vues publiques
*En tant que* spectateur, *je veux* que les classements se mettent à jour seuls, *afin de* ne pas rafraîchir.
- **CA** : abonnement WebSocket ; mise à jour automatique après chaque validation.
- **Dépend de** : E07US001, E04US009 · **Jalon** : J1

### E07US003 — Vue publique des plans de cibles
*En tant que* archer/spectateur, *je veux* voir qui tire où, *afin de* m'orienter dans la salle.
- **CA** : plan de cibles consultable (cible/position/départ) ; responsive.
- **Dépend de** : E03US008 · **Jalon** : J1

### E07US004 — Écran de salle : poste rattaché à déroulé automatique
*En tant qu'*organisateur, *je veux* rattacher un écran à la salle et l'oublier, *afin qu'*il informe tout seul, et que je sache s'il tombe.
- **CA** : l'écran est un **poste de l'appli publique** rattaché par **jeton** (même mécanisme que la tablette de cible, E04US001) → il **apparaît dans la console de supervision** (E12US001) : *un écran figé ne se plaint pas*, seule la supervision le révèle ; **déroulé de vues par défaut** paramétré à la préparation du tournoi (classement, **affectations** E07US008, tableaux, plans) avec **cadence réglable** ; rendu **plein écran, lisible à distance** (échelle typographique dédiée, thème sombre par défaut) ; **aucune interaction** ; **plusieurs écrans possibles**, chacun son déroulé (ex. affectations près du pas de tir, classements côté public).
- **Notes** : ~~« Écran projeté plein écran », v0.1~~ → **réécrite le 14/07/2026** (`D-21`, CDC UX §7.5). Ce n'est **ni une 4ᵉ appli, ni une vue autonome** : c'est un **poste**, comme une tablette de cible — donc rien de neuf à inventer (réemploi du jeton, du QR, de la supervision). `Q-UX2` **ouverte** : tri des affectations **par nom** (l'archer se cherche) ou **par cible** (l'organisation vérifie) — ce n'est pas le même écran.
- **Dépend de** : E07US002, E04US001 · **Jalon** : J3

### E07US005 — Vue tableaux/arbres live
*En tant que* spectateur, *je veux* voir les arbres de duels en direct, *afin de* suivre la progression.
- **CA** : rendu de l'arbre (principal + placement) mis à jour en live.
- **Dépend de** : E05US007, E07US002 · **Jalon** : J3

### E07US006 — « C'est moi » : ouvrir l'appli sur ma journée
*En tant qu'*archer, *je veux* que l'appli me reconnaisse, *afin de* voir ma cible **sans rien chercher**, à chaque ouverture.
- **CA** : à la 1ʳᵉ ouverture, recherche par nom → l'archer coche **« c'est moi »** ; le choix est **mémorisé localement** (même principe que le jeton de poste : `localStorage`, **aucun compte, aucun mot de passe**) ; aux ouvertures suivantes, l'appli affiche **directement sa journée** : **maintenant** (cible, position, départ, volée en cours) et **ensuite** (prochaine affectation, E07US008) ; la **recherche reste accessible** (voir un autre archer) mais **n'est plus la porte d'entrée** ; « ce n'est pas moi » réinitialise ; **live** (E07US002).
- **Notes** : `D-09` (CDC UX §6.3). Sans risque : l'appareil est **personnel** — c'est précisément pourquoi il **n'y a pas de borne partagée** à la table de l'organisation (`D-10`), « retour auto à l'accueil » et « mémoriser c'est moi » se contrediraient. **La recherche devient l'exception, pas la règle.**
- **Dépend de** : E07US001, E03US008 · **Jalon** : J1

### E07US008 — Vue publique des affectations du prochain tour
*En tant qu'*archer, *je veux* savoir **où je tire ensuite** dès que c'est décidé, *afin de* ne pas rater mon tour ni aller demander à l'organisation.
- **CA** : après le lancement d'un tour (E12US003), chaque archer concerné voit **sa** prochaine affectation (**cible, position, heure, tour**) sur son téléphone (E07US006) ; l'archer **éliminé** voit son **rang final** ; l'archer **repêché** voit sa destination ; mise à jour **sans action de sa part** (WebSocket, E07US002) ; une **vue « toutes les affectations »** alimente l'écran de salle (E07US004) et la table de l'organisation.
- **Notes** : `D-08`/`D-09` (CDC UX §6). **L'info existe *avant* le duel** : les cibles sont attribuées **aux matchs** (positions de tableau), pas aux archers — donc rien à calculer au moment du lancement. **L'archer part après avoir validé : l'info doit le suivre** — la tablette de cible (E04US018) ne couvre que celui qui est encore là. C'est le canal n°2 des **4 canaux de routage**.
- **Dépend de** : E07US006, E03US009, E12US003 · **Jalon** : J2

### E07US007 — Piloter l'écran de salle depuis l'admin
*En tant qu'*organisateur, *je veux* changer ce qu'affiche l'écran **depuis mon poste**, *afin de* projeter le podium sans traverser le gymnase.
- **CA** : depuis la console de supervision (E12US001), l'admin voit chaque écran de salle et **impose** soit une **vue figée** (ex. podium), soit une **autre séquence** ; l'écran bascule **en direct** (WebSocket) ; **une prise de contrôle sait se terminer** — **durée** (« podium 10 min puis reprise du déroulé ») **ou** retour explicite très visible ; **jamais un état forcé qu'on oublie**.
- **Notes** : `D-21`, `Q-UX7` (**durée ou geste : à trancher**). Motif : basculer sur le podium à 17 h et partir serrer des mains, c'est un écran figé sur le podium à 18 h pendant que les gens cherchent leur classement.
- **Dépend de** : E07US004, E12US001 · **Jalon** : J3
