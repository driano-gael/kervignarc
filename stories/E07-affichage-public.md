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
  > **Catalogue livré le 01/08/2026 : trois vues, pas quatre.** `classement`, `plan_cibles` et
  > `suivi_deroule`. Les **affectations** (E07US008) et les **tableaux** (E07US005) ne sont pas
  > livrées : les offrir au réglage ferait programmer un déroulé qui afficherait une page vide. Elles
  > s'ajouteront avec leur US **sans migration** — la valeur persistée est la chaîne, pas un rang.
  > *(Le CA n'est donc pas satisfait en totalité aujourd'hui, et c'est une conséquence de l'ordre des
  > US, pas un raccourci : voir la même note dans [ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) §Conséquences.)*
  >
  > ✅ **`affectations` ajoutée le 02/08/2026 par E07US008 — sans migration, comme annoncé.** La
  > prévision de conception s'est vérifiée au mot près : persister la **chaîne** plutôt qu'un rang a
  > rendu l'élargissement gratuit. *(Le test `test_une_vue_inconnue_est_refusee_sans_500` prenait
  > `affectations` comme exemple de vue inconnue : il a échoué au bon endroit, exactement comme sa
  > docstring l'annonçait, et a été mis à jour.)*
  >
  > ✅ **`tableaux` ajoutée le 04/08/2026 par E07US005 — le catalogue couvre désormais ce CA en
  > entier** (`classement`, `affectations`, `tableaux`, `plans`, plus `suivi_deroule` et
  > `palmares`). **Trois élargissements, zéro migration** : c'est la validation complète du choix
  > d'origine. Comme `affectations`, `tableaux` n'entre **pas** au déroulé par défaut — elle n'a de
  > contenu qu'après la qualification. *(Le même test a donc échoué une seconde fois, et son vivier
  > d'exemples — les vues nommées par ce CA mais non livrées — s'est **tari** : il prend désormais
  > une valeur franchement inventée, qu'aucune US future ne pourra rattraper.)*
- **CA — pilotage admin (ex-007)** : depuis la console de supervision (E12US001), l'admin voit chaque
  écran de salle et **impose** soit une **vue figée** (ex. podium), soit une **autre séquence** ; l'écran
  bascule **en direct** ; **une prise de contrôle sait se terminer** — **durée** (« podium
  10 min puis reprise du déroulé ») **et** retour explicite très visible ; **jamais un état forcé qu'on
  oublie**.
  > **`Q-UX7` fermée le 01/08/2026** (arbitrage du commanditaire, cadrage d'intention). Réponse :
  > **les deux**. L'admin choisit une durée bornée **ou** « jusqu'à ce que je rende la main », et
  > « rendre la main » reste disponible dans les deux cas. Une prise **sans échéance** porte un
  > drapeau `exige_rappel` — nommé **dans le domaine**, pas seulement dessiné — que la console
  > transforme en rappel très visible. Sans ce point d'ancrage, « jamais un état forcé qu'on oublie »
  > serait resté une intention de rédaction. Cf. [ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) §4.
  >
  > ⚠️ **Report déclaré le 02/08/2026 : « imposer une **autre séquence** » n'est pas offert à l'UI.**
  > Le domaine, le service et l'API le portent (et sont testés) ; la console de supervision, elle,
  > n'offre que la **vue figée**. Ce n'est donc **pas** livré côté utilisateur, et c'est déclaré ici
  > plutôt que laissé à deviner (remarque de revue : contrairement au catalogue de vues raccourci,
  > ce report n'était consigné nulle part, et un relecteur ou une US suivante l'aurait cru livré).
  > Le backend étant prêt, l'ajouter est un formulaire, pas une tranche.
  >
  > ⚠️ **« En direct » n'est pas WebSocket** (rectification du 01/08/2026, portée par le code livré).
  > Le v0.1 écrivait « (WebSocket) ». C'est **infaisable en l'état et, surtout, insuffisant** : le hub
  > temps réel est mono-canal (aucun ciblage par destinataire), et surtout la **fin** d'une prise de
  > contrôle naît du *temps qui passe* — qu'aucun événement serveur ne peut pousser (même
  > raisonnement qu'ADR-0038 §4 pour le passage hors-ligne d'un poste). L'écran **lit** donc sa
  > consigne (~15 s) et décompte en local ; en échange, une coupure réseau ne peut pas le laisser
  > bloqué sur un podium expiré.
- **Notes** : ~~« Écran projeté plein écran », v0.1~~ → **réécrite le 14/07/2026** (`D-21`, CDC UX §7.5).
  Ce n'est **ni une 4ᵉ appli, ni une vue autonome** : c'est un **poste**, comme une tablette de cible —
  donc rien de neuf à inventer (réemploi du jeton, du QR, de la supervision). ~~`Q-UX2` **ouverte**~~ :
  tri des affectations **par nom** (l'archer se cherche) ou **par cible** (l'organisation vérifie) — ce
  n'est pas le même écran.
  > **`Q-UX2` fermée le 02/08/2026 par E07US008 — sur son seul volet « tri » : les deux** ([ADR-0065](../docs/adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)).
  > Le constat « ce n'est pas le même écran » était juste, et c'est **exactement** pourquoi trancher
  > pour tout le monde était le mauvais réflexe. L'**écran projeté** garde l'ordre du **pas de tir**
  > (cible croissante, position A→D) — il n'a aucune interaction, l'ordre du serveur est le seul
  > qu'il aura, et c'est le seul qui se lise de loin. La **table de l'organisation**, interactive,
  > bascule d'un bouton. Même forme d'arbitrage que `Q-UX7` : « les deux », quand offrir les deux
  > coûte un bouton.
  >
  > ⚠️ **Son volet « scannabilité » reste OUVERT** (rectification de revue, 2ᵉ passe) : la question
  > enregistrée au CDC UX porte d'abord sur le fait que « 200 archers ne tiennent pas à l'écran,
  > donc ça défile, et un archer qui rate son nom attend un cycle entier ». E07US008 ne livre ni
  > pagination ni cycle — même régime que la vue `classement` depuis E07US004. Ne pas lire cette US
  > comme ayant clos la question entière : le CA périmé aurait fait dériver E07US005 d'un arbitrage
  > qui n'a pas eu lieu. Motif du pilotage : basculer sur le podium à 17 h
  et partir serrer des mains, c'est un écran figé sur le podium à 18 h pendant que les gens cherchent
  leur classement.
- **CA — le plan de tournoi, en suivi (ajouté le 31/07/2026)** : l'écran affiche le **même schéma à
  braquets** que l'atelier (E01US024), mais **rempli par la réalité** : phase terminée / en cours / à
  venir, **tour en cours**, duels joués sur duels attendus, braquets qui **se remplissent** au fur et
  à mesure. Demande du commanditaire : « *on doit bien voir l'avancement des tours aussi dans une
  phase* ». On voit d'un coup d'œil où en est le tournoi, quel tour tourne, et combien de duels
  restent.
- **CA — la même vue au pilotage** : ce plan de suivi est aussi une **destination de l'axe pilotage**
  (écran PC, interactif) — l'organisateur le consulte à son poste sans dépendre d'un écran projeté.
  Partage habituel : le **modèle** à l'atelier, l'**édition en cours** au pilotage
  ([ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §6).

> **Un seul composant de dessin, trois surfaces — c'est la décision de conception centrale.** Le
> dessiner pour un seul écran condamnerait les deux autres : les contraintes sont **opposées**.
>
> | Surface | Écran | Interaction | Habillage |
> |---|---|---|---|
> | Atelier — composer *(E01US024)* | PC | on compose | **outil** (jamais d'identité, `D-27`) |
> | Pilotage — suivre | PC | oui | **outil** |
> | Salle — projeter | ≥ 1920 px, **vu de loin** | **aucune** | **identité du tournoi** (`D-27`, `DV-08`) |
>
> Le composant est donc paramétré par **densité** (compact / large), **interactivité** (oui / non) et
> **habillage** (outil / identité). Distance de lecture, taille de texte, contraste et rotation
> automatique ne se rattrapent pas après coup.

> **Les données du suivi existent déjà** pour l'élimination directe : `domain/tableau.py` (arbre,
> progression, podium — E05US005 ✅), les duels (E04US013 ✅) et le classement. Ce qui manque viendra
> avec le **placement** (E05US010). Ne pas recoder l'arbre.

> **Ce que cette US ne fait pas** : dessiner l'**arbre de matchs duel par duel** (les 32 duels
> individuels d'un tableau). Le suivi montre l'avancement **par tour**. Un vrai bracket dessiné est
> un autre chantier, à ouvrir s'il se révèle nécessaire à l'usage.

- **Absorbe** : ex-E07US007, **et le suivi visuel du déroulé** (cadré le 31/07/2026 comme US
  distincte, regroupé ici à la demande du commanditaire — « des US les plus grosses possible »).
- **Dépend de** : E07US001, E04US001, E12US001, **E01US024** (le composant de dessin y naît) ·
  **Jalon** : J3 · **Origine du CA « suivi »** : cadrage du 31/07/2026

### E07US005 — Vue tableaux/arbres live
*En tant que* spectateur, *je veux* voir les arbres de duels en direct, *afin de* suivre la progression.
- **CA** : rendu de l'arbre (principal + placement) mis à jour en live ; **deux lectures** dans
  l'appli publique — **« Mon chemin »** (le parcours de chaque **archer suivi**, E07US006 : tour,
  adversaire, score vu de son côté, état) et **« Tableau complet »** (tous les duels **groupés par
  branche**, une branche et un tour ne se confondant pas) — ; la lecture **« Mon chemin » est celle
  par défaut dès qu'on suit quelqu'un** ; **aucun match n'est nommé par sa seule distance à la
  finale** : un match de placement disputé au tour d'une demi-finale s'annonce par ses **rangs** ;
  **rien n'est promis qui ne soit acquis** (ni vainqueur avant validation, ni tour à venir à qui
  n'a plus de match ou dont la défaite n'est pas scellée) ; la vue **`tableaux` entre au catalogue
  de l'écran de salle** (E07US004), où elle montre le **tableau qui se joue**, sans interaction.
- **Notes de conception** *(sorties du CA à la revue : ce sont des contraintes de mise en œuvre, pas
  du besoin — les y laisser aurait fait dériver les tests d'une US future de la forme du DTO plutôt
  que du besoin)* : DTO **public restreint** (règle 6, contrainte générale à toute surface
  publique) ; filtre du service sur `TYPES_EN_TABLEAU` ; libellé de match **servi par le domaine**
  (`libelle_tour`), jamais recalculé côté client.
- **Notes** : maquette **P05** (`maquettes/p05-tableau-duels.html`), dont les **deux partis pris
  sont livrés** dans l'ordre qu'elle recommande — A « Mon chemin » (*recommandé*, « l'archer est le
  sujet, la compétition est le contexte », `D-09`), B « Arbre complet » (*nécessaire en second*).
  **Pas de dessin d'arbre en branches** : il ne tient pas sur 360 px, la **liste par tour** est la
  concession assumée par la maquette.
  > **Trois arbitrages du 04/08/2026 (cadrage d'intention), reversés ici** — le CA d'origine tenait
  > en une ligne et datait d'avant tout le moteur J2 :
  >
  > 1. **Périmètre = A + B + la vue d'écran de salle.** Le questionnaire P05 était resté vide ; sa
  >    1ʳᵉ question (« le tableau complet est-il attendu du public, ou est-ce l'affaire de
  >    l'organisation ? ») est tranchée **« des deux »**, comme `Q-UX2` et `Q-UX7` avant elle : la
  >    lecture par archer et la lecture d'ensemble ne servent pas le même geste, et offrir les deux
  >    coûte un bouton.
  > 2. **« Mon chemin » s'appuie sur les archers suivis (E07US006)**, pas sur un sélecteur propre à
  >    l'onglet : `D-09` a précisément supprimé la recherche comme porte d'entrée, en réintroduire
  >    une ici la rétablirait par la bande.
  > 3. **Pas d'horaires prévisionnels** — 2ᵉ question de la maquette, tranchée **non**. Le domaine
  >    ne porte **aucun** horaire au grain de la phase ou du duel (seul le départ en a un,
  >    E02US010) : les afficher supposerait un moteur d'ordonnancement qui n'existe pas, et les
  >    inventer réaliserait exactement le risque que la maquette pointait. **La question reste
  >    ouverte** au questionnaire P05 — elle n'est pas close, elle est hors de cette US.
  >
  > **⚠️ « principal + placement » : la lecture du CA a dû être corrigée en cours d'US, et c'est le
  > test qui l'a trouvée.** Première lecture (naturelle) : les **deux types de phase**
  > `elimination_directe` et `placement`, les deux membres de `TYPES_EN_TABLEAU`. Le test écrit sur
  > cette lecture a **échoué** : `ServiceSaisieDuels._decor` refuse tout type autre que
  > l'élimination directe — le type `placement` est **composable mais pas exécutable**
  > ([DETTE-028](../docs/dette.md#dette-028--le-catalogue-de-types-de-phase-est-livré-sans-consommateur)).
  > Lecture retenue, et c'est celle du vocabulaire des tableaux : **les deux branches d'un même
  > arbre** — celle des gagnants et les **sous-tableaux de placement** que `PlacementEnCascade`
  > alimente sous profondeur intégrale (E06US006). Le service filtre sur `TYPES_EN_TABLEAU`, donc
  > une phase de type `placement` **entrera dans la vue sans rien toucher** le jour où le moteur
  > saura la monter ; d'ici là elle est **omise**, et un test le caractérise plutôt que de le taire.
  > *Conséquence à ne pas relire à l'envers : cette US ne résorbe pas `DETTE-028`, elle en montre le
  > coût sur une surface publique.*
  >
  > **⚠️ Ce que la revue a trouvé, et qui vaut d'être lu avant la prochaine US de cette épic.**
  > Trois défauts sérieux, une seule racine : **la règle de nommage d'un match a été réécrite de
  > mémoire au lieu d'être lue**. Le domaine possède `libelle_tour`, qui porte déjà un marqueur
  > `DETTE-020` avertissant qu'une copie front existe ; l'US en a d'abord écrit une troisième, avec
  > un modèle **faux** de `place_en_jeu` (renseigné seulement sur les matchs **terminaux**). Ce
  > modèle faux s'est propagé à l'identique dans le code, dans deux tests et dans la fiche de
  > recette — les trois se **confirmaient mutuellement**, ce qui est exactement pourquoi la suite
  > verte n'a rien arrêté. Résultat à l'écran : « Demi-finale » annoncée à un archer disputant les
  > places 5-8. Corrigé en servant le libellé du **domaine** au DTO, ce qui a **aussi** réparé le
  > panneau de routage (E07US008), porteur silencieux du même défaut. *Leçon reportable : quand une
  > règle métier existe côté serveur, la consommer coûte moins cher que la réécrire — et la copie
  > n'est pas seulement redondante, elle est souvent fausse.*
  >
  > Deux autres, de même famille (« affirmer plus que ce que le serveur sait ») : un archer battu
  > **dont la défaite n'était pas encore validée** se voyait promettre les tours restants ; et le
  > groupement par **numéro de tour** rangeait la petite finale sous l'en-tête « Finale » — le
  > piège que la fonction jumelle de la saisie documente pourtant avoir corrigé.
  >
  > **Et un bloquant sans rapport avec le métier** : le sélecteur Zustand dérivait un tableau neuf à
  > chaque appel → **boucle de rendu** (v5 / React 19), vue inutilisable. Le correctif existait déjà
  > dans la feature voisine, sur le même store. Ce qui manquait n'était pas la connaissance mais un
  > test qui **monte le composant** : `VueTableaux.test.tsx` a été ajouté pour cela.

  > **Robustesse jour J.** Un tableau **illisible** (phase déclarée dont la source ne prélève encore
  > personne — cas du matin) est **omis** de la liste au lieu de faire échouer la lecture : sur une
  > surface publique et projetée, une phase à venir ne doit pas produire une page blanche pour tout
  > le monde. Contrepartie assumée : un tableau **cassé** y est indiscernable d'un tableau **à
  > venir**. Même posture que `ServiceSuiviDeroule` (E07US004) et `ServicePalmares` (E06US004).
- **Dépend de** : E05US005, E07US001, **E07US006** (les archers suivis) · **Jalon** : J3
- **Élargit** : `DETTE-031` (3ᵉ endpoint public au régime « reconstruction à chaque lecture »)

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
- **CA** : pour un archer suivi (E07US006), l'appli publique affiche son **déroulé du tour** — les
  **volées du jour** (déjà tirées) et la **volée en cours**, chacune avec ses valeurs — mise à jour en
  temps réel ; chaque volée porte un **statut explicite** : **« en attente de validation »** (saisie
  par un scoreur, pas encore verrouillée) puis **« validé »** (grain de validation passé, E01US015) ;
  la donnée passe par un **endpoint public de suivi** dédié, avec un **DTO restreint** (règle 6 : ne
  fuiter ni le code de cible, ni l'IP, ni l'identité du scoreur) ; mise à jour poussée (WebSocket,
  E07US001/E04US009).
  > **CA aligné au grain volée le 21/07/2026** (arbitrage tranché, [ADR-0039](../docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md)).
  > Le v0.1 disait « la **volée en cours flèche par flèche** ». Or la saisie (E04US002) est
  > **volée par volée** : une `Volee` porte le tuple complet de ses N valeurs, il n'existe **aucune
  > entité `Fleche`** ni saisie unitaire — le serveur ne voit jamais une volée à moitié remplie. Le
  > « flèche par flèche » temps réel n'est donc **pas réalisable** sans refondre la saisie (autre US).
  > Grain retenu : **la volée** — elle apparaît d'un bloc dès qu'elle est consignée, valeurs affichées
  > une à une. Choix confirmé par l'organisateur (grain volée suffisant), cf. § Cadrage d'intention.
- **Notes** : **décision structurante ⇒ ADR** ([ADR-0039](../docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md)) —
  cette US **expose au public des scores provisoires non validés** (le spectateur voit des chiffres
  avant confirmation du scoreur, donc parfois des corrections en direct). Choix **demandé et assumé**
  par l'organisateur (20/07/2026). Terrain déjà en place : statut porté par `Volee.validee_par`
  (`None` = en attente), lecture par `ServiceSaisie.etat_serie` ; l'US ajoute un **endpoint public de
  projection** + un **DTO restreint**. La diffusion réutilise l'événement générique post-commit
  (`donnees_modifiees`, `composition._diffuser_apres_ecriture`) ; un **événement WebSocket typé**
  ciblé est un raffinement **différé** (le live marche déjà via l'invalidation de cache).
- **Dépend de** : E07US006, E04US002, E01US015 · **Jalon** : J1

### E07US008 — Vue publique des affectations du prochain tour
*En tant qu'*archer, *je veux* savoir **où je tire ensuite** dès que c'est décidé, *afin de* ne pas
rater mon tour ni aller demander à l'organisation.
- **CA** : après le lancement d'un tour (E12US002), chaque archer concerné voit **sa** prochaine
  affectation (**cible, position, tour**) sur son téléphone (E07US006) ; l'archer **éliminé**
  voit le **rang qu'il a acquis** ; l'archer **repêché** voit sa destination ; mise à jour **sans
  action de sa part** (WebSocket, E07US001) ; une **vue « toutes les affectations »** alimente
  l'écran de salle (E07US004) et la table de l'organisation.
  > **Trois arbitrages tranchés au cadrage du 02\08\2026** ([ADR-0065](../docs/adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)) :
  >
  > 1. **Périmètre : le CA complet** — le téléphone de l'archer **et** la vue collective, donc la
  >    dernière vue manquante du déroulé de l'écran de salle (E07US004) au passage.
  > 2. **Le rang de l'éliminé est calculé ici**, et non renvoyé à E06US004. Il se lit sur la
  >    **plage du match perdu** (*Règle R*, `Plage.moitie_basse`), **écrêtée à l'effectif réel** —
  >    donc une **fourchette** : « 5ᵉ-8ᵉ ». Ce n'est pas un pis-aller — dans un tableau tronqué au
  >    podium, **aucun match n'a départagé** les quatre battus des quarts, ils sont *ex æquo*. Sous
  >    placement intégral (E05US010), la fourchette se referme d'elle-même sur le rang exact.
  >    E06US004 (agrégation inter-phases, départage FFTA) reste due. *(L'écrêtage à l'effectif est un
  >    correctif de revue : une plage est bornée par la **taille** du tableau, une puissance de 2, et
  >    non par le nombre d'archers — sans lui, un battu du 1ᵉʳ tour de l'oracle 120 lisait
  >    « 65ᵉ-128ᵉ ».)*
  > 3. **Le repêché est traité**, avec une **issue distincte** de « éliminé » : `VersRepechage` ne
  >    consomme aucun rang, l'archer peut encore remonter. Sa destination se lit dans les
  >    **sources** de la phase avale.
  >    > ⚠️ **Portée exacte, rectifiée en 2ᵉ passe de revue (`DETTE-033`)** : seul le repêchage
  >    > décidé par le **routing** est annoncé — il se tranche **match par match**, donc sans
  >    > ambiguïté. Le battu qu'une phase avale **prélève** par `issue_de_tour/perdants` (composable
  >    > dès aujourd'hui dans l'atelier E01US024) lit son rang **sans savoir qu'il rejoue**. Ce n'est
  >    > pas un oubli : la sémantique de `par_issue_de_tour` **n'est pas tranchée** — un tour couvre
  >    > plusieurs plages, et « le tour perdu » n'est pas « le dernier match joué ». Elle appartient
  >    > à l'US qui implémentera le prélèvement (`DETTE-028`), pas à un canal d'affichage.
  >
  > ⚠️ **Pas d'« heure »**, malgré le v0.1 : aucun horaire n'existe par tour de tableau (les
  > horaires vivent sur les `Depart`, côté qualification). Arbitrage déjà pris en E04US018,
  > reconduit — c'est le **lancement du tour** (E12US002) qui fait partir les duels. On ne fabrique
  > pas une heure qu'on ne sait pas tenir.
  >
  > ⚠️ **Report déclaré** : un participant **équipe** (E13US002) est écarté de la vue collective —
  > le routage résout un `Participant` en **archer**, et une équipe n'a pas de nom d'archer ; ses
  > lignes seraient anonymes. La résolution viendra avec les équipes.
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
