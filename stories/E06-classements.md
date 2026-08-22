# E06 — Classements & résultats — User Stories

> EPIC : [EPIC-06](../epics/EPIC-06-classements.md) · Réfs : CDC fonctionnel M7, `moteur-placement-lucky-loser.md` §3-4.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (8 → 4). Les anciennes
> US découpées par sous-aspect (départage, catégorie, agrégation de rangs, profondeur) sont devenues des
> **critères d'acceptation** de l'US de capacité qui les porte. **Aucun comportement n'est perdu** (règle 9
> — chaque ancien titre = une puce CA identifiée). Les dépendances entrantes internes ont été redirigées
> vers l'US survivante. Correspondance ancien → nouveau en fin de fichier.

---

### E06US001 — Classement de qualification (cumul, départage, par catégorie)
*En tant que* public/organisateur, *je veux* le classement de qualification trié, départagé et disponible par catégorie, *afin de* connaître les positions sans ambiguïté.
- **CA — cumul (ex-001)** : archers triés par score cumulé (somme des volées **validées**, cf.
  `Serie.cumul`) ; mis à jour en live ; par tournoi.
- **CA — départage (ex-002)** : à score égal, tri par nombre de 10 puis de 9 ; départage déterministe
  et **traçable** — le nombre de 10 et de 9 est **restitué** dans chaque ligne, vérifiable à l'œil.
  Les deux critères sont séquentiels (`referentiel-ffta` §8.1) ; si l'égalité subsiste, le **défaut**
  est l'**ex æquo** (rangs partagés). Départager les places à enjeu par un **barrage** de tir (§8.2)
  reste une **option configurable** (US dédiée E06US003 ; politique `tiebreak` d'ADR-0004) : les deux
  résolutions doivent rester **ouvertes** — seul le défaut (ex æquo) est fixé ici.
- **CA — catégorie (ex-008)** : **deux rangs** coexistent (arbitrage produit du 20/07/2026) — un rang
  **scratch** (global, toutes catégories) et un rang **par catégorie** (repartant de 1 par catégorie,
  ex æquo partagés **avec sauts** — même règle que le scratch, **pas** un rang « dense » sans trou :
  deux ex æquo en 2ᵉ place sont suivis d'un 4ᵉ) ; un **filtre** d'affichage restreint à une catégorie
  sans changer les rangs. Applicable qualif et duels.
- **Notes** : politique `tiebreak` (ADR-0004) pour le départage, preset FFTA modifiable. En E06US001
  la règle FFTA est implémentée comme **clé de tri isolée et nommée** dans le domaine (couture
  d'injection future) ; la machinerie `Phase.config.tiebreak` **n'est pas** introduite ici — son
  moteur relève d'EPIC-05, qu'ADR-0004 scope lui-même là-bas (règle 12). Le classement dérive des
  **séries** de saisie (E04US002), pas de l'agrégat `Score` du walking skeleton (repointé en E06US001).
- **Absorbe** : ex-E06US002, E06US008. **Dépend de** : E04US002 · **Jalon** : J1

### E06US003 — Barrage de tir pour places décisives
*En tant que* système, *je veux* un barrage quand le comptage ne suffit pas, *afin de* trancher les places décisives.
- **CA** : déclenchement d'un barrage (shoot-off) pour les positions à enjeu ; résultat intégré au
  classement **de qualification**. *(Précisé le 02/08/2026 : en poule et en Big Shoot Off le barrage
  est conduit mais son verdict n'est reversé nulle part — voir la puce « poule & Big Shoot Off ».)*
- **CA — seuil configurable (cadrage du 02/08/2026)** : ce qui fait qu'une place est « à enjeu » est un
  **réglage de format**, pas une règle en dur : la politique `tiebreak` de la phase porte un seuil
  `jusqu_au`, et **toute égalité dont le rang du groupe est ≤ seuil** est signalée « barrage requis ».
  Le **défaut reste l'ex æquo** (aucun barrage) — E06US001 est inchangée tant que rien n'est réglé.
  ⚠️ Le seuil désigne le **rang du groupe**, pas chacune de ses places : deux ex æquo au rang 8 avec
  `jusqu_au = 8` se départagent, et le barrage tranche donc aussi la 9ᵉ place. Sans cela on ne
  pourrait jamais départager la **dernière place qualificative**, qui est le cas d'usage même.
- **CA — trois consommateurs** : le barrage sert (a) le **classement de qualification** quand §8.1 est
  épuisé, (b) le **classement de poule** (« barrage si nécessaire », §10.1), (c) l'égalité **au plus
  faible** d'un **Big Shoot Off**. Les trois appliquent le même moteur (`resoudre_barrage`) ; aucun ne
  le réimplémente. Le BSO n'est **pas** soumis au seuil : son égalité bloque la manche par
  construction, elle n'a pas de « place à enjeu » à comparer.
  ⚠️ **Seul (a) ferme la boucle** (précisé le 02/08/2026) : pour (b) et (c), les tireurs sont
  **désignés** et le verdict n'est reversé nulle part, faute de classement calculé — puce suivante.
- **CA — poule & Big Shoot Off : tireurs désignés, verdict non reversé** : hors qualification,
  l'organisateur **désigne** les archers à départager, et le résultat du barrage **se lit à
  l'écran sans être reversé dans aucun classement**. Le barrage y est conduit entièrement (annonce,
  manches, absents, distance au centre, correction, annulation) avec le même moteur.
  *Pourquoi* : il n'existe aucun classement de poule ni aucun état de Big Shoot Off **calculé** où
  lire les ex æquo ni où reverser le verdict — ni `poule.py` ni `big_shoot_off.py` n'ont de
  consommateur de production ([DETTE-028](../docs/dette.md)). **L'US qui livrera l'exécution de ces
  phases devra reprendre ce CA** ; une US qui en dériverait ses tests d'ici là écrirait un test faux.
  - 👉 **Cette US est nommée : c'est [`E05US023`](E05-moteur-phases.md)** *(« rendre jouables poules,
    suisse, colline, Big Shoot Off »)*, placée au **rang 2** de la file d'exécution le 08/08/2026.
    Reprendre ce CA n'y est **pas optionnel** : le jour où un classement de poule existe, « verdict
    non reversé » cesse d'être une constatation et devient un **bug spécifié**. Renvoi posé ici pour
    que l'obligation soit trouvable depuis les deux côtés — sans lui, elle ne vivait que dans une
    phrase sans destinataire.
- **CA — un verdict périmé ne s'applique pas**. Les tireurs sont **figés à l'annonce** ; le
  classement, lui, continue de vivre. Si une volée validée en retard, une correction ou un forfait
  **change le groupe** d'ex æquo, le verdict ne décrit plus cette égalité : il est **écarté** et
  l'égalité **re-signalée** (le juge refait tirer). Annoncer un second barrage sur une place où un
  barrage **périmé** reste ouvert est **refusé** : il faut l'annuler d'abord.
  Le barrage périmé est aussi **signalé à l'écran** : sur un barrage en cours, son formulaire de
  saisie et son bouton « acter » disparaissent ; sur un barrage **acté**, c'est son verdict — le
  « Départagé » — qui cède la place à l'avertissement. Dans les deux cas il ne reste qu'à l'annuler — sans quoi on ferait tirer un groupe qui
  n'oppose plus les bonnes personnes, et le classement ne bougerait pas sans un mot d'explication.
  ⚠️ Cela vaut **aussi pour un barrage déjà acté** : la clôture ne protège de rien, le verdict
  n'étant jamais stocké mais recalculé et écarté dès que le groupe change.
- **CA — rien n'est signalé avant le premier tir**. Seuls les archers **en lice ayant validé au
  moins une volée** sont candidats à un barrage. Sans cela, au démarrage tout le plateau est à zéro,
  donc ex æquo au rang 1 — et l'écran proposerait de faire tirer les 120 archers au moment même où
  l'organisateur règle sa phase. « Avoir tiré » n'est pas « avoir marqué » : une volée entièrement
  manquée compte.
- **CA — un verdict acté reste corrigible**. Clore un barrage signifie « le juge a acté », pas « le
  résultat est gravé » : le verdict n'est jamais stocké, il se recalcule. Corriger une manche d'un
  barrage clos le **rouvre**. Sans quoi un verdict inversé sur la dernière place qualificative
  enverrait le mauvais archer au tableau, définitivement.
- **CA — persistance flèche par flèche** : chaque tir est enregistré (score, distance au centre,
  **absence** distinguée d'une saisie en attente), les **manches successives** sont conservées, et le
  verdict est **rejouable** depuis les tirs — on ne stocke pas un ordre saisi à la main.
- **CA — intégration au classement** : les rangs partagés que le barrage a tranchés deviennent
  **consécutifs** dans l'ordre du barrage ; un barrage **non résolu** ne change rien (le rang reste
  partagé) plutôt que de publier un ordre à moitié vrai.
- **CA — câblage de la politique** : `domain/classement.py` cesse de réimplémenter §8.1 à la main et
  passe par `PolitiquesPhase.tiebreak` — c'est la couture qu'E06US001 avait laissée en attente, et
  une part de **DETTE-028**.
- **Notes** : dépendances redirigées au regroupement du 17/07/2026 — l'ex-`E06US002` (dont dépendait cette
  US) a rejoint `E06US001` ; l'ex-`E04US016` a rejoint `E04US013` (redirection déjà actée dans
  `E04-saisie-scores.md`).
- **Notes — ce que l'US ne refait pas** : le **moteur** du barrage est déjà livré et pur
  (`domain/barrage.py`, E05US015 : absents relégués → plus haut score → distance au centre → groupes à
  rejouer). E06US003 lui donne ses **consommateurs**, sa **persistance** et son **déclenchement** ;
  elle ne retouche sa règle nulle part. Le **shoot-off interne à un duel nul** (égalité de sets) reste
  hors périmètre : il vit dans l'agrégat `Duel` depuis E04US013 ([ADR-0049](../docs/adr/0049-saisie-et-scoring-des-duels.md) §3),
  et cet arbitrage n'est pas rouvert.
- **Dépend de** : E06US001, E04US013 · **Jalon** : J2

### E06US004 — Podium des duels & agrégation des rangs
*En tant que* public, *je veux* voir le podium et un classement de duels cohérent, *afin de* connaître les vainqueurs et le rang de chacun.
- **CA — podium (ex-004)** : rangs 1-4 issus de la finale/petite finale (E05US005) ; affiché et exportable.
  Un podium se lit **par catégorie** (c'est là que se remettent les médailles) et n'affiche que des
  rangs **décernés** — il peut donc être partiel (le bronze se tire couramment avant l'or) ou vide,
  et le **dit** plutôt que de laisser un blanc.
- **CA — agrégation (ex-005)** : rangs des différentes phases fusionnés en un classement cohérent par catégorie.
  Avoir disputé le tableau passe avant tout : le battu du 1ᵉʳ tour devance tout non-qualifié, quel
  qu'ait été son rang de qualification. Les rangs sont renumérotés **1→N sans trou**.
- **CA — départage des sortis au même tour** *(arbitrage du 03/08/2026, reversé ici)* : deux archers
  sortis au même tour n'ont été départagés par **aucun match** (les quatre battus des quarts d'un
  tableau tronqué au podium sont 5ᵉ-8ᵉ). C'est une **politique injectable** (famille `aggregation`,
  7ᵉ du catalogue ADR-0004) qui décide, au **défaut** `par_qualification` — l'usage World Archery,
  qui donne un classement sans ex æquo. `ex_aequo` publie la fourchette telle quelle.
  ⚠️ Le départage ne s'applique **qu'à ce qui est joué** : deux finalistes partagent « 1ᵉʳ-2ᵉ »
  jusqu'à ce que la finale tranche — aucune politique ne décerne l'or à la place du tir.
- **Notes** : périmètre arbitré au cadrage du 03/08/2026 — **moteur + API + vue publique + export
  PDF**. Portée réelle : qualification + phases à **tableau** ; les moteurs `poule`, `suisse`,
  `colline`, `big_shoot_off` existent mais aucun service ne les déroule (`DETTE-028`), ils entreront
  sans toucher au domaine. Une phase de **consolation** serait mal classée (`DETTE-034`), impact nul
  tant qu'aucun repêchage n'est câblé. Voir [ADR-0067](../docs/adr/0067-palmares-agregation-des-rangs-de-phases.md).
- **Absorbe** : ex-E06US005. **Dépend de** : E05US005 · **Jalon** : J2

### E06US006 — Classement intégral 1→N & profondeur configurable
*En tant que* public/organisateur, *je veux* un classement complet dont je choisis la profondeur, *afin de* connaître le rang de chaque archer, adapté au tournoi.
- **CA — rang unique (ex-006)** : chaque archer a un rang unique 1→N, alimenté par les matchs terminaux (E05US010).
- **CA — profondeur configurable (ex-007)** : mode 1→N OU top N + regroupement du reliquat ;
  politique `depth`, réglée **phase par phase** (cadrage du 04/08/2026 : le déroulé se compose déjà
  à cette maille, et un tournoi peut jouer un tableau principal intégral avec une consolante
  tronquée). Réglable depuis « Composer un format » (renommé par E16US002) **et** depuis les phases d'un tournoi.
- **CA — le preset d'une phase non réglée est le podium** *(arbitrage du 04/08/2026, reversé ici)*.
  Le CA d'origine disait « mode 1→N (**défaut**) », repris d'[ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md).
  C'est vrai du **catalogue**, faux du **preset d'une phase déjà en base** : jusqu'à cette US, toutes
  les phases se jouaient en `ProfondeurPodium` figée au câblage, et faire de 1→N le preset aurait
  converti **tous les tournois existants** au placement intégral — un tableau de 120 passant de
  128 duels à 436 (mesuré), sans que personne ne l'ait demandé. 1→N est donc ce que
  l'organisateur **choisit**, jamais ce qu'il subit ([ADR-0070](../docs/adr/0070-profondeur-de-classement-reglee-par-phase.md) §3).
  ⚠️ **Une exception, voulue** : le type `placement` a pour preset le classement **intégral**. Lui
  seul n'a aucun existant à préserver (aucun service ne monte encore son tableau, `DETTE-028`) et
  son intitulé promet de « classer tout le monde, du 1ᵉʳ au dernier » — lui donner le podium aurait
  affiché « Podium (défaut) » sur le type dont le nom dit l'inverse.
- **Notes** : cohérent avec l'oracle 120. Le « regroupement du reliquat » **existe déjà** : c'est le
  mécanisme de **fourchette** livré par E06US004 (`rang_min`/`rang_max` + `decerne`), qui dit ce
  qu'aucun match n'a départagé. L'US n'ajoute donc rien au palmarès — sous placement intégral, les
  fourchettes disparaissent d'elles-mêmes et chaque rang devient exact **et** décerné. Une
  profondeur sur un type qui ne monte aucun tableau (qualification, poule, échauffement) est
  **refusée** sur une phase ; sur une **étape de format** elle s'enregistre (régime brouillon,
  ADR-0063) et n'est refusée qu'à l'application. Les deux modes offerts se nomment `un_vers_n` et
  `top_n` — **pas** `podium`, réservé par le glossaire aux rangs 1-4 décernés par un match. ⚠️ Reste non livré, inscrit en `DETTE-035` : le
  schéma à braquets ne **chiffre** pas les duels qu'une profondeur ajoute, alors que la maquette A07
  en fait son exigence `P-4` — la simulation, elle, donne le compte exact.
- **Absorbe** : ex-E06US007. **Dépend de** : E05US010 · **Jalon** : J3

---

### E06US009 — Un palmarès par départ, juxtaposés
*En tant qu'*organisateur, *je veux* un palmarès **par créneau**, présentés côte à côte, *afin de*
remettre les récompenses de chaque départ sans que l'application invente un classement d'ensemble
que le règlement ne prévoit pas.

Origine : `DETTE-045`, ouverte par E01US025 en portant le classement au départ
([ADR-0075](../docs/adr/0075-le-depart-est-la-portee-sportive.md)). Le palmarès et le rejeu de
simulation étaient restés à la maille tournoi : ils lisent le **premier** créneau et ignorent les
autres, silencieusement — rien à l'écran ne dit que la vue est partielle.

**Arbitrage du commanditaire (07/08/2026)** : « **juxtaposé — 4 départs = 4 podiums** ». La question
posée était « additionne-t-on les podiums ou les juxtapose-t-on ? » ; elle est tranchée, et il n'y a
donc **aucune** agrégation inter-départs à écrire.

- **CA — un palmarès par créneau** : le palmarès rend **N podiums**, un par départ du tournoi, chacun
  calculé sur le classement de **son** créneau. Un tournoi mono-départ rend un seul podium — le
  rendu d'aujourd'hui, inchangé.
- **CA — juxtaposition, pas addition** : l'application ne produit **aucun** classement « du
  tournoi » toutes catégories et tous départs confondus. Deux archers de créneaux différents ne sont
  jamais comparés. *(C'est l'arbitrage : le tournoi est un contenant, le départ la portée sportive.)*
- **CA — chaque podium est nommé** : le créneau est identifié par son libellé usuel (« Départ 2 —
  14:00 »), le **même** partout dans le produit. Un podium anonyme dans une pile de quatre ne se
  distribue pas.
- **CA — la simulation suit** : le rejeu de simulation cesse de ne voir que le premier départ.
- **Notes — ce n'est pas qu'un changement d'affichage.** `_premier_depart` disparaît de
  `application/palmares.py` : tant qu'il existe, la vue reste juste par accident sur les tournois
  mono-créneau et fausse partout ailleurs. Les marqueurs `# DETTE-045` posés dans `palmares.py`,
  `simulation.py` et `simulation_format.py` désignent les sites exacts.
- **Notes — exports** : tout export du palmarès (EPIC-09) hérite de la juxtaposition. Un fichier par
  départ ou un fichier à N sections est un choix de **format d'export**, pas de classement — à
  trancher dans l'US d'export, pas ici.
- **Résorbe** : `DETTE-045`. **Dépend de** : E01US025 · **Jalon** : J3

---

## Correspondance ancien → nouveau (maille du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E06US001 | Classement de qualification (cumul) | **E06US001** — CA « cumul » |
| E06US002 | Départage qualif (nb de 10 puis 9) | **E06US001** — CA « départage » |
| E06US003 | Barrage de tir pour places décisives | **E06US003** (inchangée) |
| E06US004 | Podium issu des duels | **E06US004** — CA « podium » |
| E06US005 | Agréger les rangs de tableau | **E06US004** — CA « agrégation » |
| E06US006 | Classement intégral 1→N | **E06US006** — CA « rang unique » |
| E06US007 | Profondeur de classement configurable | **E06US006** — CA « profondeur configurable » |
| E06US008 | Classement par catégorie | **E06US001** — CA « catégorie » |
