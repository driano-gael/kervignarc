# ADR-0039 — Exposition publique du déroulé du tour, scores **provisoires** inclus

- **Statut** : Accepté
- **Date** : 2026-07-21
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E07-affichage-public.md`](../../stories/E07-affichage-public.md) (E07US009 : CA
  aligné au **grain volée**, cf. décision §4). N'amende ni le glossaire (« volée », « validée » y sont
  définis) ni la dette (aucun raccourci assumé).
- **Introduit par** : E07US009 (suivre le déroulé du tour en direct).
- **S'appuie sur** : [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) et la saisie E04US002
  (l'agrégat `Serie`/`Volee` porte déjà `validee_par`), le grain de validation E01US015
  ([`grain_validation.py`](../../backend/domain/grain_validation.py)), et le contrat d'accès public
  E10US001 (`backend/tests/test_acces_public.py`).

## Contexte et problème

E07US006 a livré la **liste de suivi** (front, `localStorage`) : pour un archer suivi, sa
cible/position/départ. E07US009 veut aller plus loin — afficher sa **feuille de marque en direct** :
les volées déjà tirées, la volée en cours, chacune avec un **statut** « en attente de validation »
puis « validé ».

Deux obstacles se posent, tous deux relevant d'un **arbitrage** (pas d'un choix technique) :

1. **Confidentialité / frontière de rôle.** Jusqu'ici, côté scores, seuls **deux** faits sont
   publics : le **validé** (le classement, E06US001) et le **placement**. L'**en-cours de saisie** —
   une volée saisie par le scoreur mais **pas encore validée** (`Volee.validee_par is None`) — n'est
   exposé sur **aucun canal public**. L'afficher au public, c'est montrer des chiffres **avant**
   confirmation du scoreur, donc parfois des **corrections en direct**. C'est un choix de
   transparence, à assumer explicitement plutôt qu'à glisser dans le code.

2. **Granularité.** Le CA d'origine (20/07/2026) demandait « la volée en cours **flèche par
   flèche** ». Or le modèle de saisie (E04US002) est **volée par volée** : une `Volee` porte le tuple
   **complet** de ses N valeurs, exige exactement N flèches (une volée incomplète est *rejetée*), et
   il n'existe **aucune entité `Fleche`** ni endpoint de saisie unitaire. Le serveur ne voit donc
   **jamais** une volée à moitié remplie : un « flèche par flèche » temps réel n'est pas réalisable
   sans refondre la saisie — une autre US, hors de cette tranche.

## Décision

**1. Un endpoint public dédié expose le déroulé par archer.**
`GET /api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule`, **sans authentification** (comme
toute lecture publique, E10US001), lecture seule exécutée **hors boucle** (`run_in_threadpool`). Il
réutilise le service de lecture existant `ServiceSaisie.etat_serie` — pas de nouveau modèle ni de
nouveau chemin de lecture. Un archer sans rien de saisi (ou un couple `(tournoi, archer)` inconnu)
renvoie un **déroulé vide en 200**, jamais un 404 : corollaire de la frontière de confidentialité —
l'endpoint public ne **révèle pas** l'existence d'un couple, l'énumération ne distingue rien.

**2. Le déroulé inclut les volées NON validées.** Chaque volée porte un **statut explicite**
`en_attente` (= `not Volee.verrouillee`) ou `valide`. Le public voit donc des scores **provisoires**,
susceptibles de correction avant verrouillage. **Choix demandé et assumé par l'organisateur**
(20/07/2026) : c'est un outil de suivi (« où en est mon archer »), pas un résultat officiel — le
classement (validé seul) reste la source de vérité des scores.

**3. DTO public restreint (règle 6).** Le DTO n'expose que : `numero`, `valeurs`, `points`, `statut`,
`horodatage` (par volée) et le `cumul` (validé) de la série. Il **n'expose jamais** l'**identité du
scoreur** (`saisie_par` / `validee_par`), ni le **code de cible**, ni l'IP. La frontière de
confidentialité passe par l'**omission de champ** dans un DTO **distinct** de la projection
poste/admin (`SerieReponse`, qui porte les marqueurs de scoreur). Le garde-fou `test_acces_public`
vérifie que ce GET répond sans 401.

**4. Grain volée, pas flèche.** Une volée apparaît **d'un bloc** dès qu'elle est consignée ; on
affiche ses valeurs une à une (10, 9, M…), mais pas leur apparition progressive. Le CA d'E07US009 est
**aligné** en ce sens dans `stories/` (même livraison — sans quoi l'US suivante en dériverait un test
faux, règle 9). Le vrai flèche-par-flèche reste une évolution possible du modèle de saisie, en US
dédiée.

**5. Diffusion live par l'événement générique existant.** La mise à jour temps réel réutilise la
diffusion post-commit déjà en place (`_diffuser_apres_ecriture` → `LiveEvent("donnees_modifiees")`),
qui invalide le cache React Query côté front → refetch du déroulé. Un **événement WebSocket typé
ciblé** (faire retourner un `LiveEvent` propre par la commande `saisir_volee`/`valider`) est un
**raffinement différé** : il n'est **pas requis** fonctionnellement (le live marche déjà) et
introduirait le premier événement typé du projet — hors périmètre de cette tranche.

## Conséquences

- **+** Un accompagnateur ou un coach suit le tour d'un archer **sans être à la cible**, avec la
  distinction claire attente/validé.
- **+** Réemploi intégral de l'existant : l'agrégat `Serie`/`Volee` porte déjà `validee_par`, le
  service `etat_serie` lit déjà volées + horodatages. Cette US ajoute **une frontière** (un endpoint
  + un DTO restreint), pas un modèle.
- **+** Le contrat `test_acces_public` verrouille l'ouverture publique en lecture **et** continue de
  bloquer toute écriture non authentifiée : la nouvelle route est couverte par ce garde-fou.
- **−** Le public voit des scores **non validés**, parfois corrigés en direct : c'est une transparence
  **assumée**, pas une garantie d'exactitude. L'UI doit l'afficher sans ambiguïté (badge « en attente
  de validation ») pour ne pas induire en erreur — responsabilité du front, portée par le `statut`.
- **−** Deux DTO projettent une volée (`SerieReponse` poste/admin **avec** marqueurs de scoreur ;
  `DerouleReponse` public **sans**) : c'est **voulu** — deux frontières de confidentialité, deux
  contrats (règle 6, « DTO distincts »), pas une duplication à factoriser.
- **−** Diffusion à **gros grain** (invalidation globale du cache front à chaque écriture) : acceptable
  en contexte mono-club, ~30 tablettes, réseau local (règle 12) ; un événement typé viendra **si** un
  besoin de finesse émerge, pas par anticipation.
