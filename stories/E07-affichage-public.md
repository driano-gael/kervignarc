# E07 — Affichage public & écran projeté — User Stories

> EPIC : [EPIC-07](../epics/EPIC-07-affichage-public.md) · Réfs : CDC fonctionnel M6, **CDC UX §7.4–7.5**.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (8 → 5). Les anciennes
> US découpées par étape technique (classements / live / plans / déroulé auto / pilotage admin) sont
> devenues des **critères d'acceptation** de l'US de capacité qui les porte. **Aucun comportement n'est
> perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). `E07US002` (live) est absorbée dans
> `E07US001` ; les dépendances **internes** à E07 qui la visaient sont redirigées vers `E07US001`.
> Correspondance ancien → nouveau en fin de fichier.

> ⚠️ **Révisé le 14/07/2026** ([`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §6, `D-09`/`D-21`).
> **L'appli publique n'est pas un tableau de résultats : c'est le fil de la journée de l'archer** — un GPS.
> Son besoin n°1 (**« où je tire ensuite »**) était **absent des 117 US**. Deux conséquences : l'archer
> **n'a pas à chercher** (« c'est moi » mémorisé, E07US006 ; affectations poussées, E07US008), et **l'écran
> de salle est un *poste* de cette appli** (E07US004 réécrite), supervisé et pilotable — pas une 4ᵉ
> application.

---

### E07US001 — Vues publiques : classements, plans de cibles et live
*En tant que* spectateur/archer, *je veux* consulter les classements et le plan de cibles, mis à jour
seuls en direct, *afin de* suivre le tournoi et m'orienter dans la salle sans authentification.
- **CA — classements (ex-001)** : accès sans authentification ; lecture seule ; par catégorie ; responsive mobile.
- **CA — plans de cibles (ex-003)** : plan de cibles consultable (cible/position/départ) ; responsive.
- **CA — live (ex-002)** : abonnement WebSocket ; mise à jour automatique après chaque validation.
- **Absorbe** : ex-E07US002, E07US003. **Dépend de** : E06US001, E10US001, E04US009, E03US001 · **Jalon** : J1

### E07US004 — Écran de salle : déroulé automatique et pilotage admin
*En tant qu'*organisateur, *je veux* rattacher un écran à la salle avec un déroulé automatique, et pouvoir
le piloter à distance depuis mon poste, *afin qu'*il informe tout seul — et que je puisse imposer une vue
sans traverser le gymnase.
- **CA — poste rattaché & déroulé (ex-004)** : l'écran est un **poste de l'appli publique** rattaché par
  **jeton** (même mécanisme que la tablette de cible, E04US001) → il **apparaît dans la console de
  supervision** (E12US001) : *un écran figé ne se plaint pas*, seule la supervision le révèle ;
  **déroulé de vues par défaut** paramétré à la préparation du tournoi (classement, **affectations**
  E07US008, tableaux, plans) avec **cadence réglable** ; rendu **plein écran, lisible à distance**
  (échelle typographique dédiée, thème sombre par défaut) ; **aucune interaction** ; **plusieurs écrans
  possibles**, chacun son déroulé (ex. affectations près du pas de tir, classements côté public).
- **CA — pilotage admin (ex-007)** : depuis la console de supervision (E12US001), l'admin voit chaque
  écran de salle et **impose** soit une **vue figée** (ex. podium), soit une **autre séquence** ; l'écran
  bascule **en direct** (WebSocket) ; **une prise de contrôle sait se terminer** — **durée** (« podium
  10 min puis reprise du déroulé ») **ou** retour explicite très visible ; **jamais un état forcé qu'on
  oublie**.
- **Notes** : ~~« Écran projeté plein écran », v0.1~~ → **réécrite le 14/07/2026** (`D-21`, CDC UX §7.5).
  Ce n'est **ni une 4ᵉ appli, ni une vue autonome** : c'est un **poste**, comme une tablette de cible —
  donc rien de neuf à inventer (réemploi du jeton, du QR, de la supervision). `Q-UX2` **ouverte** : tri
  des affectations **par nom** (l'archer se cherche) ou **par cible** (l'organisation vérifie) — ce
  n'est pas le même écran. `Q-UX7` **ouverte** : durée ou geste pour terminer une prise de contrôle —
  à trancher. Motif du pilotage : basculer sur le podium à 17 h et partir serrer des mains, c'est un
  écran figé sur le podium à 18 h pendant que les gens cherchent leur classement.
- **Absorbe** : ex-E07US007. **Dépend de** : E07US001, E04US001, E12US001 · **Jalon** : J3

### E07US005 — Vue tableaux/arbres live
*En tant que* spectateur, *je veux* voir les arbres de duels en direct, *afin de* suivre la progression.
- **CA** : rendu de l'arbre (principal + placement) mis à jour en live.
- **Dépend de** : E05US005, E07US001 · **Jalon** : J3

### E07US006 — Suivre des archers : ma journée
*En tant qu'*archer/accompagnateur, *je veux* désigner un ou plusieurs archers à **suivre**, *afin de*
retrouver leur cible **sans rien chercher**, à chaque ouverture.
- **CA** : recherche par nom → l'utilisateur coche **« suivre »** ; les archers suivis forment une
  **liste mémorisée localement** (même principe que le jeton de poste : `localStorage`, **aucun compte,
  aucun mot de passe**) ; aux ouvertures suivantes, l'appli affiche **directement sa journée** — une
  **carte par archer suivi** avec **cible, position, départ** (le **départ n'apparaît qu'une fois
  l'archer placé** — avant, « pas encore placé » : la journée se lit sur le **plan de cibles**, pas sur
  les inscriptions, dont le DTO porte des données de paiement à ne pas exposer au public, règle 6 —
  arbitrage de revue reversé ici) ; **retirer un suivi** est possible
  (« ne plus suivre ») ; la **recherche reste accessible** mais **n'est plus la porte d'entrée** ;
  **live** (E07US001). *Hors de cette tranche : le **déroulé du tour en direct** (scores, statut
  attente/validé) est **E07US009** ; l'**à-venir** (prochaine phase/cible) est **E07US008**.*
- **Notes** : `D-09` (CDC UX §6.3). Sans risque : l'appareil est **personnel** — c'est précisément
  pourquoi il **n'y a pas de borne partagée** à la table de l'organisation (`D-10`), « retour auto à
  l'accueil » et « mémoriser mes suivis » se contrediraient. **La recherche devient l'exception, pas la
  règle.**
  > **CA élargi le 20/07/2026** (arbitrage métier, § Cadrage d'intention du workflow). Le v0.1 disait
  > « **c'est moi** » — **un** archer, sa propre journée, **front-only**. L'organisateur a demandé la
  > capacité **« suivre »**, généralisable à **plusieurs** archers (accompagnateur, coach), et le
  > **déroulé du tour en direct** (chaque score saisi, badge « en attente de validation » puis
  > « validé »). Cette dernière partie **n'est pas réalisable en front seul** : l'en-cours de saisie
  > (scores non validés, statut par volée) n'est exposé sur **aucun canal public** — seuls le validé
  > (classement) et le placement le sont. D'où le **redécoupage** : E07US006 = la **liste de suivis +
  > cible/position/départ** (front, ici) ; **E07US009** (nouvelle) = le **déroulé live** (backend +
  > ADR). L'à-venir reste **E07US008** (dépend de J2, phases/duels). « ce n'est pas moi » du v0.1
  > devient **« ne plus suivre »** par archer.
- **Dépend de** : E07US001, E03US001, E02US009 · **Jalon** : J1

### E07US009 — Suivre le déroulé du tour en direct
*En tant que* personne qui suit un archer, *je veux* voir sa feuille de marque se remplir **en direct**,
*afin de* suivre son tour sans être à côté de la cible.
- **CA** : pour un archer suivi (E07US006), l'appli publique affiche son **déroulé du tour** — la
  **volée en cours flèche par flèche** et l'**historique du jour** (volées déjà tirées) — mis à jour en
  temps réel ; chaque volée porte un **statut explicite** : **« en attente de validation »** (saisie
  par un scoreur, pas encore verrouillée) puis **« validé »** (grain de validation passé, E01US015) ;
  la donnée passe par un **endpoint public de suivi** dédié, avec un **DTO restreint** (règle 6 : ne
  fuiter ni le code de cible, ni l'IP, ni l'identité du scoreur) ; mise à jour poussée (WebSocket,
  E07US001/E04US009).
- **Notes** : **décision structurante ⇒ ADR** — cette US **expose au public des scores provisoires
  non validés** (le spectateur voit des chiffres avant confirmation du scoreur, donc parfois des
  corrections en direct). Choix **demandé et assumé** par l'organisateur (20/07/2026), mais à écrire
  en ADR (frontière de rôle/confidentialité) plutôt qu'à glisser dans le code. Terrain déjà en place :
  statut porté par `Volee.validee_par` (`None` = en attente), avancement incluant le non-validé dans
  `ServiceSaisie.avancement_cible` ; il « manque » un **endpoint public de projection** et un
  **événement WebSocket typé** (le point de diffusion post-commit existe déjà,
  `composition._diffuser_apres_ecriture`).
- **Dépend de** : E07US006, E04US002, E01US015 · **Jalon** : J1

### E07US008 — Vue publique des affectations du prochain tour
*En tant qu'*archer, *je veux* savoir **où je tire ensuite** dès que c'est décidé, *afin de* ne pas
rater mon tour ni aller demander à l'organisation.
- **CA** : après le lancement d'un tour (E12US002), chaque archer concerné voit **sa** prochaine
  affectation (**cible, position, heure, tour**) sur son téléphone (E07US006) ; l'archer **éliminé**
  voit son **rang final** ; l'archer **repêché** voit sa destination ; mise à jour **sans action de sa
  part** (WebSocket, E07US001) ; une **vue « toutes les affectations »** alimente l'écran de salle
  (E07US004) et la table de l'organisation.
- **Notes** : `D-08`/`D-09` (CDC UX §6). **L'info existe *avant* le duel** : les cibles sont attribuées
  **aux matchs** (positions de tableau), pas aux archers — donc rien à calculer au moment du
  lancement. **L'archer part après avoir validé : l'info doit le suivre** — la tablette de cible
  (E04US018) ne couvre que celui qui est encore là. C'est le canal n°2 des **4 canaux de routage**.
- **Dépend de** : E07US006, E03US009, E12US002 · **Jalon** : J2

---

## Correspondance ancien → nouveau (maille du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E07US001 | Vue publique des classements | **E07US001** — CA « classements » |
| E07US002 | Live des vues publiques | **E07US001** — CA « live » |
| E07US003 | Vue publique des plans de cibles | **E07US001** — CA « plans de cibles » |
| E07US004 | Écran de salle : poste rattaché à déroulé automatique | **E07US004** — CA « poste rattaché & déroulé » |
| E07US005 | Vue tableaux/arbres live | **E07US005** (inchangée) |
| E07US006 | « C'est moi » : ouvrir l'appli sur ma journée | **E07US006** « Suivre des archers » (élargie 20/07 : liste de suivis) + **E07US009** (déroulé live, scindée) |
| E07US007 | Piloter l'écran de salle depuis l'admin | **E07US004** — CA « pilotage admin » |
| E07US008 | Vue publique des affectations du prochain tour | **E07US008** (inchangée) |
