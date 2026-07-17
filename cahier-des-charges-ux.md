# Cahier des charges — Architecture d'expérience & ergonomie — Kervignarc

**Solution logicielle de gestion de tournoi de tir à l'arc en salle (18 m)**

| | |
|---|---|
| **Version** | 0.2 (UX — architecture d'expérience, layouts, règles d'interaction) |
| **Date** | 14/07/2026 |
| **Statut** | Décisions arbitrées par le client le 14/07/2026 · questions ouvertes `Q-UXn` |
| **Documents liés** | `cahier-des-charges.md` (fonctionnel v0.3), `cahier-des-charges-technique.md` (technique v0.2), **`cahier-des-charges-design.md` (visuel & ergonomie v0.3 — charte instruite)**, `docs/referentiel-ffta.md` (v1.1), ADR-0011 |
| **Sources** | Entretien de conception du 14/07/2026 (24 arbitrages, registre §11), **éléments graphiques fournis le 14/07/2026 (`docs/elements_design/`) + arbitrages design du même jour (`D-26`→`D-28`)**, règlement sportif FFTA 2023 (B.3, B.6.1), état du code front au 14/07/2026 |
| **Périmètre** | **Structure** de l'expérience : combien d'applications, qui y entre et comment, comment on y navigue, quels écrans portent la valeur, quelles règles régissent les modifications. **Ne traite pas** l'identité visuelle (couleurs, typo, logo, tokens) : c'est `cahier-des-charges-design.md`. |

> **Document vivant et versionné.** Chaque arbitrage porte un identifiant `D-nn` (registre §11) avec sa
> version d'introduction. Les questions non tranchées portent `Q-UXn` (§12). L'historique des versions
> est en §13. **Un agent qui reprend ce projet doit pouvoir savoir non seulement *ce qui* a été décidé,
> mais *depuis quand* et *à la place de quoi*.**

---

## 1. La thèse — ce que ce produit vend réellement

> **Ce produit ne fait pas gagner du confort : il fait disparaître un temps mort.**

Le coût réel d'un tournoi aujourd'hui n'est pas la lenteur de la saisie. C'est le **temps mort entre deux
tours** : quelqu'un ramasse les feuilles, recopie, calcule, constitue le tableau suivant, l'imprime,
l'affiche — pendant que 150 archers attendent. S'y ajoutent les erreurs de remontée de score, les archers
qui ne savent pas où ils tirent, le traitement des inscrits et le suivi des paiements (arbitrage client,
14/07/2026).

**Tout ce qu'une automatisation et un contrôle peuvent prévenir doit l'être.** Le reste du document en
découle.

### 1.1 La métrique du produit

> **Temps entre « dernier duel validé » et « les archers savent où aller » : < 2 minutes.** — `D-25`

C'est la seule métrique qui compte, et elle **remplace** l'objectif de vitesse de saisie envisagé par le
CDC design v0.1 (`Q-D3` : « une volée de 3 flèches saisie et validée en < 10 s »). Raison : si un marqueur
met 12 s au lieu de 10, **personne ne le remarque** — il attend les autres archers de sa cible de toute
façon. Si la bascule entre deux tours prend 20 minutes, **150 personnes attendent**.

La vitesse de saisie reste une exigence de confort (§7.2), pas un objectif contractuel.

### 1.2 Ce que ça change dans la hiérarchie des écrans

Le CDC design v0.1 (§5.2) classe les pièces maîtresses ainsi : saisie tablette, plan de cibles, éditeur de
phases, écran projeté, mobile. **La bascule de tour n'y figure pas** — alors qu'elle porte toute la valeur.
Hiérarchie corrigée :

| # | Écran | Pourquoi |
|---|---|---|
| **1** | **Bascule de tour** (§8) | C'est le produit. Les autres écrans ne font que la rendre possible. |
| **2** | **Console de supervision** (§7.1) | Voir ce qui bloque avant que ça bloque. |
| **3** | **Saisie sur la tablette de cible** (§7.2) | Le poste le plus utilisé, le plus sensible à l'erreur. |
| **4** | **Plan de cibles / placement** (§7.1) | L'écran signature de l'admin — *non instruit à ce jour, cf. `Q-UX8`*. |
| **5** | **Consultation mobile « ma journée »** (§7.4) | Le plus grand nombre d'utilisateurs. |
| **6** | **Écran de salle** (§7.5) | La vitrine — et un canal de routage à part entière. |

---

## 2. Principes directeurs

- **P-1 — Le design se juge au temps mort supprimé**, pas à l'esthétique (§1).
- **P-2 — L'information « où je tire ensuite » est omniprésente.** L'archer ne doit jamais la chercher :
  elle vient à lui, sur le canal où il se trouve (§6). — `D-09`
- **P-3 — L'appli n'empêche jamais l'admin : elle l'avertit.** Le jour J, tout arrive. Un outil qui bloque
  l'organisateur est un outil qu'on contourne sur papier — et l'appli perd la vérité. Seul le statut
  *terminé* fige, et seulement le sportif (§9). — `D-15`
- **P-4 — Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection.** Si l'appli
  demande confirmation pour tout, l'admin apprend à cliquer « oui » sans lire — et le jour où ça compte, il
  clique « oui » sans lire (§9.1). — `D-16`
- **P-5 — L'identité est proportionnée au risque** — et n'est jamais un compte utilisateur. Le jour J,
  personne n'a le temps de créer des comptes (§5). — `D-13`
- **P-6 — Tout ce qui s'identifie se prépare à l'avance.** Le jour J, on distribue et on pilote ; on ne
  configure pas. — `D-14`
- **P-7 — Chaque application assume son terrain** au lieu de tout faire partout mal (§3.2). — `D-02`
- **P-8 — Accessibilité WCAG 2.1 AA** : exigence contractuelle inchangée, cf. `cahier-des-charges-design.md`
  §6.

---

## 3. Architecture d'expérience — trois applications

### 3.1 Le découpage — `D-01`

Décision client : **trois applications**, découpées par **geste** et non par statut d'utilisateur.

| Appli | URL | Qui | Geste |
|---|---|---|---|
| **Admin** | `/admin` | Organisateur | Configurer, superviser, piloter, corriger, exporter |
| **Saisie** | `/saisie` | Marqueurs (archers) et scoreurs | Saisir, valider |
| **Public** | `/` | Archers, public, **écran de salle** | Consulter |

**Pourquoi archer et scoreur dans la même appli :** ils font le même geste — taper des scores sur un écran
tactile, debout, près du pas de tir. La seule différence est que le scoreur valide. **Ça, c'est une
permission, pas une application.**

**L'archer est à cheval, et c'est assumé** : il *saisit* (appli saisie, sur la tablette de sa cible) et il
*consulte* (appli publique, sur son téléphone). Ce n'est pas une incohérence — ce sont deux moments
différents de sa journée, sur deux appareils différents.

**Il n'y a pas de quatrième application.** L'écran de salle est un **poste de l'appli publique** (§4, `D-21`).

> **Remplace** le découpage en 4 contextes d'usage C1–C4 du CDC design v0.1 §2.1. La correspondance est
> établie en §3.4.

### 3.2 Planchers responsive différenciés — `D-02`

Conséquence directe de `D-01` : **les trois applis n'ont pas le même socle responsive.**

| Appli | Plancher | Cible | Ne supporte pas |
|---|---|---|---|
| **Saisie** | **768 px — tablette** | Tablette de club, PC | **Le smartphone** (arbitrage client : taille tablette garantie) |
| **Public** | **360 px — mobile d'abord** | Tout, jusqu'à l'écran de salle (≥ 1920 px) | — |
| **Admin** | **1280 px — PC** | PC portable de l'organisateur | Mobile (tablette en secours dégradé) |

**Ce que le plancher tablette débloque :** la grille des 3–4 archers **et** le pavé de flèches tiennent sans
compromis, donc la contrainte de cibles tactiles ≥ 48 px (CDC design §2.3) est **tenable partout**, et non
plus au prix d'un repli « un archer à la fois ».

> **Remplace** l'hypothèse « ~30 tablettes BYOD » du CDC technique et du CDC design v0.1 §2.2 (cf. §4.1).

### 3.3 L'identité du tournoi s'arrête à la vitrine — `D-27`

Le matériau graphique fourni le 14/07/2026 a établi un fait que le découpage en 3 applis n'avait pas anticipé :
**il y a deux marques** — le **club** (permanent) et l'**événement** (par édition, ex. *Challenge des
Champions*). Chaque tournoi peut donc porter **son** identité (CDC design §3.6, `DV-06`).

**Décision : elle habille l'appli publique et l'écran de salle. Pas l'admin, pas la saisie.**

| Appli | Porte l'identité du tournoi ? | Pourquoi |
|---|---|---|
| **Public** (dont l'écran de salle) | ✅ **Oui** | C'est **la vitrine**. L'archer et le public viennent pour *le Challenge des Champions*, pas pour un logiciel. |
| **Saisie** | ❌ **Non** | **C'est l'outil.** |
| **Admin** | ❌ **Non** | **C'est l'outil.** |

> **Le jour J, un bénévole n'a pas le temps de réapprendre des repères visuels.** Le marqueur qui prend la
> tablette de la cible 12 a peut-être marqué au tournoi précédent : **il doit retrouver exactement la même
> interface**. Une appli de travail qui change d'apparence à chaque édition est une appli qu'on redécouvre à
> chaque édition — c'est du temps mort, et le temps mort est précisément ce que ce produit supprime (§1).

**Ce découpage tombe juste parce qu'il suit `D-01`** : les applis sont découpées par **geste**. *Consulter*
est un geste tourné vers l'événement ; *saisir* et *piloter* sont des gestes tournés vers l'outil.

**Ce qui ne se personnalise jamais** (CDC design §4.2, `DV-06`) : **les couleurs sémantiques**. Un tournoi
change *de quoi ça a l'air*, **jamais *ce que ça veut dire***. L'ambre d'une alerte appartient au produit.

### 3.4 Correspondance avec les contextes C1–C4 du CDC design v0.1

| CDC design v0.1 | Devient |
|---|---|
| **C1 — Pilotage** (admin, PC) | **Appli admin** — inchangé sur le fond |
| **C2 — Saisie** (scoreur, tablette) | **Appli saisie**, mais **deux postes distincts** : la tablette de cible (marqueurs) et l'appareil du scoreur (itinérant) — cf. §7.2 et §7.3 |
| **C3 — Consultation** (archer/public, mobile) | **Appli publique** — enrichie : ce n'est pas un tableau de résultats, c'est le **fil de la journée de l'archer** (§7.4) |
| **C4 — Projection** (écran de salle) | **Un poste de l'appli publique**, supervisé et pilotable (§7.5) — plus un contexte isolé |

---

## 4. Le modèle de poste

C'est le concept central de l'architecture d'expérience, et il n'existe dans aucune US à ce jour.

### 4.1 Le matériel réel — `D-05`

Arbitrage client :

- **Le club fournit un parc de tablettes**, avec **interdiction d'y installer quoi que ce soit** → navigateur
  uniquement.
- **Les tablettes personnelles font l'appoint** en cas de manque → **parc hétérogène par construction**, à
  concevoir défensivement.
- **Taille tablette (ou PC) garantie** → `D-02`.

**Conséquences fermes :**

| Contrainte | Conséquence de conception |
|---|---|
| Pas d'installation possible | **Pas de mode kiosque.** L'appli vit dans un onglet de navigateur, 8 h durant, manipulée par des gens qui ne la connaissent pas. |
| Onglet de navigateur | ~60 à 100 px de hauteur perdus (barre d'URL), et **un geste malheureux ferme l'onglet**. Sur 30 postes × 8 h, **ça arrivera plusieurs fois**. |
| Écran allumé 6 à 10 h | Aucune batterie ne tient. Recours : *Screen Wake Lock* (API navigateur, sans garantie sur tout le parc) ; alimentation à prévoir (`Q-UX4`). |
| Parc hétérogène (appoint perso) | Concevoir pour le pire cas : pas de plein écran garanti, notifications système possibles par-dessus la saisie. |

> **Exigence qui découle de tout ça :** puisque l'onglet peut être fermé ou perdu, **le rattachement d'un
> poste à sa cible doit se refaire en un geste, par quelqu'un qui ne sait rien** (§4.3).

### 4.2 L'identité d'un poste : le jeton, pas l'IP — `D-06`

Un poste est **rattaché une fois** et **nourri par le back** ensuite. Le rattachement est porté par un
**jeton persistant stocké dans le navigateur** (`localStorage`).

**Mécanismes écartés, et pourquoi :**

| Mécanisme | Pourquoi il est refusé |
|---|---|
| **Adresse IP** | Les baux DHCP expirent : une tablette en veille se réveille avec une autre IP et **perd sa cible**. Pire, une IP libérée **réattribuée à une autre tablette** lui fait hériter du rattachement — **les scores partent sur la mauvaise cible, silencieusement**. Un score faux et silencieux est bien pire qu'une erreur visible. Figer les baux par MAC exigerait de la configuration réseau : contraire à EPIC-11 (« exploitable par un non-technicien »). |
| **Empreinte d'appareil** | Le parc est constitué de tablettes **identiques** (même modèle, OS, navigateur, résolution) : elles sont **indiscernables**. Le *fingerprinting* distingue des appareils hétérogènes, pas une flotte uniforme. |

**Mécanisme retenu — et il existe déjà dans le code :** le pattern de `shared/stores/sessionAdminStore.ts`
(Zustand + `persist`, jeton en `localStorage`, envoi en `Authorization: Bearer`, purge sur 401). On ajoute
un `sessionPosteStore` sur le même moule. **Ni concept nouveau, ni configuration réseau** — l'IP peut
changer dix fois dans la journée, le jeton s'en moque.

```
   MONTAGE (une fois)          APRES UNE COUPURE
   scan QR cible 12            ouvrir kervignarc.local
        |                              |
        v                              v
   back -> jeton "poste C12"     jeton retrouve en local
        |                              |
        v                              v
   localStorage                  "Cible 12" directement
```

L'IP conserve un usage **de diagnostic** (aider l'admin à retrouver un poste), **jamais d'identité**.

### 4.3 Rattachement et révocation — `D-07`

- **Rattachement par QR** imprimé et posé sur la cible (produit par les exports, EPIC-09). Recours : **code
  saisi à la main** si le QR est abîmé ou l'appareil photo capricieux.
- **Le jeton est lié au tournoi et révocable.** Piège à traiter : *le jeton survit trop bien*. Au tournoi
  suivant, la tablette de la cible 12 posée sur la cible 5 **croirait toujours être la 12**. Nouveau
  tournoi → tous les postes redemandent un rattachement.
- L'admin voit et réinitialise les postes depuis la console de supervision (§7.1).

### 4.4 Types de postes

| Poste | Rattaché à | Identité | Alimenté par |
|---|---|---|---|
| **Poste de cible** | Une cible | Le **lieu** (§5) | Grille de sa cible, volée courante, routage après validation |
| **Écran de salle** | Le tournoi | Le **lieu** | Déroulé de vues, pilotable par l'admin (§7.5) |

L'appareil du scoreur **n'est pas un poste** : il est rattaché à une **personne**, pas à un lieu (§5).

### 4.5 Ce que le poste retient — le thème suit le jeton — `D-26`

**Le thème sombre est le défaut** — ce n'est pas un choix de confort, **c'est la charte** : le fond de la
banderole du club **est** l'anthracite `#1D1D1B` (CDC design §3.3, `DV-02`). Le thème clair reste disponible
partout, en déclinaison complète.

**Mais la bascule est *par poste*, et c'est une décision de structure, pas de design :**

> **Dans un gymnase, la lumière varie d'une cible à l'autre.** La cible 3 est sous la baie vitrée en plein
> soleil ; la cible 22 est au fond, à l'ombre. **Un thème global est faux pour l'une ou pour l'autre.**

Conséquence sur le modèle de poste : **le jeton ne porte pas que le rattachement, il porte les préférences du
poste.** Le `sessionPosteStore` (§4.2) retient le thème choisi **à côté** du rattachement à la cible — même
`localStorage`, même cycle de vie, **même révocation** (`D-07`).

```
   JETON DE POSTE
   +---------------------------+
   |  cible      : 12          |  <- le rattachement (D-06)
   |  tournoi    : 2026-10-12  |  <- la revocation   (D-07)
   |  theme      : clair       |  <- la preference   (D-26)
   +---------------------------+
        survit a la fermeture de l'onglet
```

**Pourquoi ça compte** : `D-05` établit qu'il n'y a **pas de mode kiosque** et qu'un geste malheureux ferme
l'onglet — *sur 30 postes × 8 h, ça arrivera plusieurs fois*. Si le thème n'était qu'un état d'écran, **le
bénévole de la cible 3 devrait le rebasculer à chaque réouverture**. Porté par le jeton, il revient tout seul.

**La préférence système n'est consultée qu'à la première ouverture** ; **un choix explicite prime toujours**
et n'est plus écrasé.

> ⚠️ **Exigence qui remonte au design :** une bascule de thème **ne doit jamais rendre une alerte invisible**.
> L'ambre d'alerte passe de 9,22:1 (sombre) à **1,83:1 sur blanc** : chaque token sémantique **a une valeur
> par thème** (CDC design §3.3.4). **Ce n'est pas un détail esthétique, c'est la supervision qui s'éteint.**

---

## 5. Les trois modes d'identité — `D-13`

Aucun n'est un compte utilisateur. Chacun est proportionné au risque.

| Qui | Identifié par | Mécanisme | Pourquoi ce niveau |
|---|---|---|---|
| **Poste de cible** | **Le lieu** | Jeton de poste (§4.2). **Aucune authentification.** | La tablette est fixée à la cible : **qui tape dessus est légitime par construction**. Aucun pouvoir : on saisit, rien n'est définitif. |
| **Scoreur** | **La personne** | Code individuel court → jeton en `localStorage` | Il **verrouille** des scores. On doit savoir qui. |
| **Admin** | **Un secret** | Login + mot de passe (E10US002, livré) | Il peut tout casser. |

**Le contrôle d'accès du poste de cible est physique.** Zéro friction, zéro code à distribuer, zéro bénévole
à former — et **30 postes ouverts au lieu de 30 codes à gérer**.

**Le scoreur, lui, doit être identifié** parce que la traçabilité de la validation l'exige (`D-12`).
Concrètement : **3 ou 4 codes à distribuer, pas 30.**

> **Ces décisions invalident deux US :** E10US003 (« session scoreur par **code de cible** ») — le scoreur
> n'est pas rattaché à une cible, il butine ; et E10US007 (« rôle archer : saisir ses scores ») — **il n'y a
> pas de rôle archer**, il y a une tablette ouverte. Réécriture cadrée en §14.

---

## 6. Le routage — le fil rouge de la journée — `D-09`

> **P-2 : l'information « où je tire ensuite » est omniprésente.**

C'est le besoin identifié par le client et absent de toutes les US à ce jour. C'est aussi le moment où
l'archer est perdu, où il va déranger l'organisateur, où il rate son tour.

### 6.1 Quatre canaux, une seule donnée

| Canal | Quand | Pour qui |
|---|---|---|
| **Tablette de la cible** | À la validation, immédiatement | Celui qui est encore là, à l'instant T |
| **Téléphone** (appli publique) | Tout le temps | Tous les autres — **l'archer part, l'info le suit** |
| **Écran de salle** | En rotation | Celui qui lève les yeux |
| **Table de l'organisation** | À la demande | Celui qui préfère demander (`D-10`) |

### 6.2 Le timing : la cible suivante est connue *d'avance* — `D-08`

**En qualification, le problème ne se pose pas** : un archer reste sur sa cible pour ses 20 volées.

**Aux duels, il est central** — et il bute sur un piège de timing : on ne lance pas un 1/8ᵉ dès qu'un duel se
termine, donc à la seconde où le scoreur valide, l'appli pourrait n'avoir rien à dire.

**Solution retenue :** les cibles sont attribuées **aux matchs** (positions du tableau), **pas aux archers**,
dès la génération du tableau. Le match n° 3 des 1/8ᵉ se tire sur la cible 4, **quel que soit son vainqueur**.
L'information existe donc **avant même le duel**, et la tablette l'affiche instantanément.

```
   VALIDATION DU DUEL              PUIS, IMMEDIATEMENT
   +-----------------------+       +-----------------------------+
   |  MARTIN 6 - 2 DURAND  |       |  MARTIN Paul                |
   |  [ Valider ]          |  -->  |  > CIBLE 4 - 14h20          |
   +-----------------------+       |    Quart de finale          |
                                   |                             |
                                   |  DURAND Jean                |
                                   |  > Termine - 12e place      |
                                   +-----------------------------+
```

C'est la façon dont ça se fait en compétition, **et c'est la seule qui tienne la promesse**. Impact sur
E03US009 (« duellistes côte à côte »), qui amorce déjà ce raisonnement.

### 6.3 « C'est moi » — l'appli publique sans compte

L'archer tape son nom **une fois** ; l'appli le retient en local (même principe que le jeton de poste, sans
compte ni mot de passe). Il rouvre l'appli, il tombe sur **sa** journée. **La recherche devient l'exception,
pas la porte d'entrée.**

```
   1re ouverture              Ensuite (memorise)
   +------------------+       +--------------------+
   | Rechercher...    |       | MARTIN Paul        |
   | [ mart|        ] |       | -------------------|
   | MARTIN Paul   >  |       | MAINTENANT         |
   | MARTIN Sophie >  |  -->  | Cible 12 - Pos. B  |
   +------------------+       | Volee 8/12         |
     [x] C'est moi            |                    |
                              | ENSUITE            |
                              | 1/4 - Cible 4      |
                              | 14h20              |
                              +--------------------+
```

Sans risque sur un appareil personnel — et c'est précisément pourquoi **il n'y a pas de borne partagée**
(`D-10`) : « retour automatique à l'accueil » et « mémoriser c'est moi » se contrediraient.

---

## 7. Les applications, écran par écran

### 7.1 Appli admin — ossature — `D-19`, `D-20`

**Destinations** (~16, réparties en trois temps) :

- **Préparation** — Tournoi · **Identité** · Catégories · Blasons · Gabarit · Phases · Barèmes · Tarifs ·
  **Scoreurs** · Clubs · Inscriptions · Placement
- **Jour J** — **Supervision** · **Complétude** · Validation · Classements
- **Après** — Classements · Podiums · Paiements · Exports · Archive · Audit

**Ossature retenue : sidebar groupée par temps, tout cliquable en permanence.** Les groupes suivent la vie
du tournoi ; le groupe du moment est ouvert, les autres repliés. **Replié ≠ interdit** — un clic sur
*Préparation* et on inscrit un retardataire (`P-3`).

```
+------------------+--------------------------------+
| Tournoi 12 oct v |  SUPERVISION                   |
| En cours  * LIVE |  ----------------------------- |
| [ Rechercher.. ] |  Qualification    Volee 8/12   |
|                  |  [##########------] 62%        |
| PREPARATION    > |                                |
| JOUR J         v |  POSTES            28/30       |
|  > Supervision   |  Cible 7   HORS LIGNE   14mn ! |
|    Completude  ! |  Cible 23  non rattachee     ! |
|    Validation  3!|                                |
|    Classements   |  A VALIDER              3      |
| APRES          > |  Cible 3   attend 4mn 20   [>] |
+------------------+--------------------------------+
     240px               le reste
```

**Deux éléments du wireframe qui ne sont pas des détails :**

- **La recherche est dans la sidebar, en haut, toujours présente** — c'est le bénévole de la table qui
  répond à un archer (`D-10`).
- **Le sélecteur de tournoi est au-dessus de tout** : tout ce qui est en dessous lui appartient. Évite la
  catastrophe classique — modifier le mauvais tournoi.

**L'identité est une destination de préparation — `D-28`.** L'organisateur y dépose **un logo et deux
couleurs d'accent** ; le système dérive tout le reste (CDC design §3.6). Elle est rangée dans *Préparation*
au titre de `P-6` — **tout ce qui s'identifie se prépare à l'avance** : le jour J, on distribue et on pilote,
**on ne choisit pas des couleurs**. Comme toute destination, elle **reste accessible en permanence** (`P-3`).
Deux exigences la distinguent d'un simple formulaire :

- **Un aperçu, pas un nuancier.** L'organisateur ne juge pas une couleur dans un sélecteur : il la juge **sur
  l'écran de salle et sur le téléphone** — les deux seules surfaces qu'elle habille (`D-27`).
- **Le contrôle de contraste est une alerte chiffrée** (`P-4`), pas un refus : « ce rouge donne 2,55:1 sur le
  fond sombre — il servira d'aplat, le texte utilisera une variante éclaircie ». C'est **exactement le cas du
  rouge du club** (CDC design §3.5, `DV-05`). *Rien n'est refusé, tout est expliqué.*

**Repli en icônes** réservé au **plan de salle** et à l'**arbre de duels**, qui réclament toute la largeur :

```
+---+----------------------------------------------+
| = |  PLACEMENT                                   |
| . |  +--------------------------------------+    |
| . |  | [1] [2] [3] [4] [5] [6] [7] [8]      |    |
| . |  | [9] [10][11][12][13][14][15][16]     |    |
| . |  +--------------------------------------+    |
+---+----------------------------------------------+
  56px          1224px pour le plan
```

**Accueil contextualisé — `D-20`.** *Accessible* et *au premier plan* sont deux choses différentes. La
sidebar est un **squelette stable** ; ce qui change avec le statut du tournoi, c'est **l'accueil** et les
**états portés par les entrées** (`3!`, `62%`, `HORS LIGNE`) :

| Statut (E01US002, livré) | Accueil | Registre |
|---|---|---|
| **Brouillon** | La préparation | Dense, formulaires, on a le temps |
| **En cours** | **La console de supervision** | Gros, alertes, **zéro formulaire au premier plan** |
| **Terminé** | Résultats & exports | Lecture, export |

**Ce n'est pas une restriction** (`P-3`) : les 15 destinations restent à un clic. C'est une priorité
d'affichage — **l'avancement décide de ce que l'admin voit en premier.**

**La console de supervision — l'écran que le besoin « voir l'avancement » réclamait réellement.** Ce n'est
pas un graphique de progression : c'est **une console de supervision de 30 postes**.

```
   POSTES DE SAISIE                     28/30 en ligne
   +---------------------------------------------+
   | Cible 1    en ligne     volee 8   il y a 2mn|
   | Cible 7    HORS LIGNE   volee 5   il y a 14mn| !
   | Cible 12   en ligne     volee 8   il y a 1mn|
   | Cible 23   non rattachee                    | !
   | Ecran salle en ligne    Affectations        |
   +---------------------------------------------+
```

Elle distingue **« ils tirent lentement »** de **« leur tablette est morte »**. Sans elle, l'admin confond
les deux et envoie quelqu'un courir pour rien. **Un écran figé ne se plaint pas** — seule la supervision le
révèle.

### 7.2 Appli saisie — le poste de cible

**La tablette appartient à la cible, pas à la personne.** Poste fixe, partagé par les 3–4 archers, sans
session nominative : la tablette **est** la cible 12, toute la journée.

**Qui tape — `D-03`.** Le règlement FFTA (B.6.1.1) impose « un marqueur désigné à chaque cible » qui
inscrit, **dans l'ordre décroissant**, selon les indications de l'archer ; les autres archers **vérifient
chaque flèche annoncée**. La tablette est donc **le poste du marqueur** : une grille des 3–4 archers, une
personne dessus, qui tape ce que chacun annonce à voix haute.

**La double marque.** B.6.1.1 note : « quand les compétiteurs sont marqueurs, **la double marque est
obligatoire** » — et en club, le marqueur est presque toujours un archer de la cible. La double marque
existe parce que le papier est faillible (additions, ratures, feuille perdue) ; l'appli fait les additions et
ne perd rien, **mais ne protège pas contre la faute de frappe** — ce contre quoi la double marque protège.

**Décision : la validation par le scoreur tient lieu de seconde marque** (`D-03`), ce qui donne au scoreur
un **sens réglementaire** au lieu d'un rôle de simple superviseur. *À faire confirmer par un arbitre —
`Q-UX3`.*

**Plusieurs marqueurs, tracés à la volée — `D-04`.** Plusieurs marqueurs peuvent être désignés sur une même
cible. Chaque volée enregistre **qui l'a saisie** : c'est **l'équivalent numérique de la signature** de la
feuille de marque (le règlement, art. cité §B, exige la signature de l'archer et du marqueur), et ça alimente
le journal d'audit (E10US005).

**Contrainte d'ergonomie ferme :** *le marqueur change rarement, donc l'interface ne s'organise pas autour de
ce changement.* Pas de sélecteur permanent qui trône au-dessus de la grille et vole de l'espace au pavé.
**Discret par défaut, disponible au besoin.**

```
   CIBLE 12                    Volee 8/12
   Marqueur : MARTIN >            <- discret, tapable
   +---------------------------------------+
   | A  MARTIN   [10][ 9][ 8] = 27         |
   | B  DURAND   [ 9][ 9][ 7] = 25         |
   | C  PETIT    [10][10][ 9] = 29         |
   +---------------------------------------+
   Validation a la fin de la serie     <- le grain actif, D-11
```

**La tablette dit quel grain de validation s'applique** (`D-11`) : sans ça, le marqueur ne sait pas quand le
scoreur viendra — « validation à la fin de la série » n'est pas la même journée que « validation toutes les
2 volées ».

**Après validation, la tablette devient un panneau de routage** (§6.2).

### 7.3 Appli saisie — le poste du scoreur

**Le scoreur est itinérant** : appareil personnel, rattaché à aucune cible, **il choisit** celle dont il veut
valider les scores. **3 à 4 scoreurs pour ~30 cibles**, **définis à la configuration du tournoi et
redéfinissables à tout moment** (`D-14` — un scoreur qui ne vient pas, ça arrive).

**Le grain de validation est une politique de phase — `D-11`.** Pas un réglage global : la qualification
valide en fin de série, l'élimination directe en fin de duel. Réglé **une fois à la configuration de la
phase**, jamais le jour J.

> **Assise technique :** l'ADR-0011 (14/07/2026) a introduit `Phase` avec une `config` JSON ne portant que
> `scoring`, en précisant que « les autres politiques y viendront **sans changement de schéma** ». Le grain
> devient **`config.validation`**, à côté de `config.scoring`. Zéro friction.

**Fondement réglementaire du grain « fin de série / fin de duel » :** les feuilles de marque sont signées
« à la fin de la distance, ou de la compétition, **ou du duel** ». La validation est un acte **de fin**.
L'article B.6.1.2 (« établissement des scores toutes les 2 volées ») porte sur le **cumul** — que l'appli
calcule seule — pas sur la validation par un tiers.

| Grain | Validations / départ (30 cibles) | Avec 3 scoreurs |
|---|---|---|
| Chaque volée | ~360 | une toutes les 20 s — ils ne font plus que ça |
| Toutes les 2 volées | ~180 | une toutes les 40 s — intenable |
| **Fin de série** | **~60** | **20 chacun — confortable** |
| **Fin de duel** | 8 en simultané | **pic court mais violent** |

**Pas de prise en charge, mais une trace — `D-12`.** Deux scoreurs peuvent ouvrir la même cible : le live
(WebSocket, déjà en place) la retire de la file dès qu'elle est validée. **Chaque validation porte le nom du
scoreur.**

**La file est triée par ancienneté d'attente** — parce que le pic des duels est **le goulot d'étranglement
de la journée**, pas la saisie : les 8 duels d'un tour finissent ensemble, attendent tous, et le tour suivant
ne peut pas partir.

```
   VUE SCOREUR (son appareil)
   +---------------------------------------+
   |  A VALIDER                        3   |
   |  Cible 7    attend 4mn 20        [>]  |  <- le plus ancien
   |  Cible 12   attend 1mn 05        [>]  |     toujours en haut
   |  Cible 3    attend 0mn 30        [>]  |
   |  ----------------------------------   |
   |  EN COURS                             |
   |  Cible 1    volee 8/12                |
   +---------------------------------------+
```

### 7.4 Appli publique — le fil de la journée

**Ce n'est pas un tableau de résultats, c'est un GPS** (§6). Entrée directe sur l'essentiel, « c'est moi »
mémorisé (`D-09`, §6.3), mobile d'abord, lecture seule, live.

Contenus : ma cible / ma position / mon départ · **ma prochaine affectation** · mon classement · classements
par catégorie · plans de cibles · tableaux.

### 7.5 Appli publique — le poste « écran de salle » — `D-21`

**L'écran de salle est un poste de l'appli publique**, rattaché par jeton comme une tablette de cible.

- **Déroulé de vues par défaut**, paramétré à la préparation du tournoi (`P-6`).
- **C'est la surface qui porte l'identité du tournoi** (`D-27`) : logo de l'événement au premier plan, **club
  en signature de pied** (« organisé par les Archers de Kervignac ») — co-branding hiérarchisé, `DV-08`. **Si
  le tournoi n'a pas d'identité propre, le club reprend la place** : aucune surface ne reste vide.
- **L'admin peut à tout moment imposer** une vue figée (le podium) **ou** une autre séquence, **depuis son
  poste** — sans traverser le gymnase.
- **Il apparaît dans la console de supervision** : un écran tombé se voit (§7.1).
- **Plusieurs écrans sont possibles** sans effort : chaque poste a son jeton, donc son déroulé (ex. un sur
  les affectations près du pas de tir, un sur les classements côté public).

```
   CONSOLE ADMIN                    ECRAN DE SALLE
   +------------------------+       +------------------------+
   | POSTES        29/31    |       |                        |
   | Cible 7   HORS LIGNE ! |       |   1/4 DE FINALE        |
   | Ecran salle  en ligne  |       |                        |
   |   Affiche : Affectations       |   MARTIN P.  -> C4     |
   |   [Classement    ]     |       |   DURAND J.  -> C4     |
   |   [Affectations *]     |  -->  |   PETIT L.   -> C7     |
   |   [x] Rotation 20s     |       |                        |
   +------------------------+       +------------------------+
```

**Recommandation ferme : une prise de contrôle doit savoir se terminer.** Basculer sur le podium à 17 h et
partir serrer des mains, c'est un écran figé sur le podium à 18 h pendant que les gens cherchent leur
classement. Donc **une durée** (« podium 10 min puis reprise du déroulé ») **ou** un retour explicite très
visible — **jamais un état forcé qu'on oublie** (`Q-UX7`).

**Une vue que le CDC design v0.1 n'avait pas : les affectations du prochain tour.** C'est probablement la
plus utile — un classement, on le regarde par curiosité ; une affectation, on en a **besoin**. Elle pose un
problème de scannabilité non tranché (`Q-UX2`) : 200 archers ne tiennent pas à l'écran, donc ça défile, et
**un archer qui rate son nom attend un cycle entier**. Le tri **par nom** (l'archer se cherche) et **par
cible** (l'organisation vérifie) ne servent pas les mêmes gens.

---

## 8. La bascule de tour — le cœur du produit

> C'est le moment où le produit gagne ou perd (§1).

### 8.1 Le geste : l'admin lance — `D-22`

**Tout est déjà en place** : le placement des duels est connu d'avance (`D-08`), les affectations sont
poussées sur 4 canaux (`D-09`), la complétude est calculable (§8.3), le WebSocket met tout le monde à jour
ensemble. **Il ne manque que le geste.**

**La journée a un maître de cérémonie, et ce n'est pas le logiciel.** L'appli prépare, contrôle, affiche —
et **attend**. L'admin appuie quand l'arbitre est prêt.

**Deux exigences fermes :**

1. **L'appli doit tout préparer *avant* qu'on appuie.** Le bouton ne calcule rien : sinon on a remplacé
   20 minutes de recopie par 20 secondes de sablier, **et le doute revient**. Au moment où le dernier duel
   est validé, le tour suivant est **déjà prêt, affiché, contrôlé**. On n'appuie que sur « go ».
2. **Le bouton dit ce qu'il déclenche, chiffré** (`P-4`). Pas « Tour suivant » mais « 2 duels, cibles 4 et 7,
   14h20 — 118 personnes vont être prévenues ».

```
   BASCULE DE TOUR                 Quart de finale
   +---------------------------------------------+
   | 4/4 duels valides                       OK  |
   | Vainqueurs : MARTIN, DURAND, PETIT, LEROY   |
   |                                             |
   | DEMI-FINALES  ->  2 duels, cibles 4 et 7    |
   |                   depart 14h20              |
   |                                             |
   | En lancant : 31 postes, 87 telephones et    |
   | l'ecran de salle affichent les affectations |
   |                                             |
   |            [ LANCER LES DEMI-FINALES ]      |
   +---------------------------------------------+
```

### 8.2 Feu vert et granularité — `D-23`, `D-24`

**Le feu vert est affiché en permanence**, pas découvert en appuyant : l'admin voit ce qui manque **avant**
de vouloir lancer (`P-3` — l'appli n'empêche pas, elle montre).

**L'unité lançable est l'événement (le duel), pas le tour.** Deux duels prêts et un qui attend son duel
source ? **On fait partir les deux** au lieu de bloquer 4 archers à cause d'un cinquième en retard. Le
lancement **global** reste disponible.

```
   DEMI-FINALES                      2 duels
   +---------------------------------------------+
   | (v) Duel 1  MARTIN vs DURAND      cible 4   |
   | (v) Duel 2  PETIT  vs LEROY       cible 7   |
   |  [ Lancer les 2 duels - 14h20 ]             |
   +---------------------------------------------+

   Si tout n'est pas mur :
   +---------------------------------------------+
   | (v) Duel 1  MARTIN vs DURAND      cible 4   |
   | ( ) Duel 2  PETIT  vs  ?          cible 7   |
   |     en attente : 1/4 n3 non valide          |
   |  [ Lancer le duel 1 ]   [ Tout lancer ]     |
   +---------------------------------------------+
```

**Le forfait est tracé — `D-24`.** L'archer absent n'est pas un trou dans le tableau : c'est une **donnée**
— forfait, daté, attribué ; l'adversaire passe. **Rien ne bloque jamais, tout se documente** (`P-3`).
Élargit la portée d'E04US015 (abandon/DSQ). *Qui déclare le forfait : `Q-UX5`. Liste exacte des métriques du
feu vert : `Q-UX6`.*

### 8.3 La complétude — `D-18`

> « Une information pour l'admin doit préciser si tout n'est pas complet pour le tournoi » — arbitrage
> client.

**C'est le vrai visage de « l'avancement du tournoi ».** Pas une barre de progression : **une réponse à
« qu'est-ce qui manque pour que ce tournoi soit fini ? »**, avec **le sportif et le tiers comptés
séparément** (`D-17`).

```
   TOURNOI DU 12 OCTOBRE - En cours
   +---------------------------------------------+
   | SPORTIF                          incomplet  |
   |   Qualification            OK  30/30 cibles |
   |   1/8 de finale            OK   8/8 duels   |
   |   1/4 de finale            !    3/4 duels   |
   |   Demi-finales                  a venir     |
   |   Classement 1->N               en attente  |
   +---------------------------------------------+
   | HORS SPORTIF                                |
   |   Paiements                !   144/156      |
   +---------------------------------------------+
   | Terminer le tournoi -> figera le sportif.   |
   | Les paiements resteront modifiables.        |
   +---------------------------------------------+
```

---

## 9. Règles de modification

### 9.1 L'alerte se calcule, elle ne se classe pas — `D-16`

> **`P-4` : une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection.**

**L'appli calcule l'impact réel au moment où on agit** — elle ne classe pas les actions d'avance. La même
action n'a pas le même impact selon le moment :

| Action | Contexte | Alerte |
|---|---|---|
| Changer le gabarit | **Avant tout placement** | **Aucune** — impact nul |
| Changer le gabarit | **156 archers placés** | Chiffrée : « 156 archers perdront leur place ; 4 cibles ont déjà des scores, ils seront conservés » |
| Modifier une phase | **Pas encore jouée**, tournoi en cours | **Aucune** — impact nul, *malgré* le tournoi « en cours » |
| Inscrire un retardataire | Pendant la qualification | **Aucune** |

**La ligne de partage n'est donc ni *brouillon / en cours*, ni *sportif / tiers* seule, mais : *est-ce que ça
a déjà produit des données réelles ?***

```
   MAUVAIS                          BON
   +----------------------+   +--------------------------------+
   | Etes-vous sur ?      |   | Changer le gabarit maintenant  |
   |                      |   |                                |
   | Le tournoi est en    |   | 156 archers perdront leur      |
   | cours.               |   | place. 4 cibles ont deja des   |
   |                      |   | scores : ils seront conserves. |
   | [Annuler] [OK]       |   |                                |
   +----------------------+   | Tapez REPLACER pour confirmer  |
                              | [__________]                   |
   on clique OK sans lire     +--------------------------------+
```

Les actions massives demandent un **geste délibéré** (taper un mot), impossible à faire par réflexe, et
laissent une **trace d'audit** (E10US005).

### 9.2 Blocage : « terminé » seulement — `D-15`

**En cours, tout passe** avec confirmation chiffrée et trace. **Aucune action n'est refusée.**

### 9.3 Le sportif et le tiers — `D-17`

> **Le tournoi sportif et ce qui l'entoure ne suivent pas le même régime.**

| Nature | Exemples | À « terminé » |
|---|---|---|
| **Sportif** | Configuration, placement, phases, scores, duels, classements | **Figé** |
| **Hors sportif** | **Paiements** | **Reste modifiable** |

**Sans cette distinction, « terminé = tout est figé » empêcherait d'encaisser un chèque en retard.** Un
archer règle la semaine suivante : le tournoi terminé n'a rien à y redire.

**Passer à « terminé » est la seule action irréversible de l'appli** (la réouverture est différée). Geste
délibéré + contrôle de complétude en amont : « 2 duels ne sont pas validés, 12 archers n'ont pas payé.
Terminer quand même ? » (§8.3).

---

## 10. État du front au 14/07/2026 — l'écart à combler

Factuel, pour cadrer les US de refonte (§14) :

| Existant | Cible |
|---|---|
| **Aucun routeur** (`react-router` absent) ; navigation = `useState` local | 3 applis, URL, deep-link, retour navigateur |
| **Un seul écran**, `TrancheVerticale.tsx` (423 lignes) empilant 6 sections admin dans une carte `max-width: 560px` | Layout admin (sidebar §7.1) + features par écran |
| `PlanDeSalle.tsx` : **un formulaire, pas un plan** | Plan de salle (`Q-UX8`) |
| Saisie : **1 flèche par `input`** dans `TableClassement.tsx` | Pavé tactile (E04US002) |
| Déconnexion **cachée dans le formulaire de création de tournoi** | Sortie du fourre-tout |
| `MessageErreur` **dupliqué dans 6 fichiers** ; CSS monolithique (`App.css`, 429 lignes) | Composants partagés |
| Thème sombre par `prefers-color-scheme` **sans bascule manuelle** | Bascule manuelle (CDC design §7.1) |

**Fondations saines à conserver** : découpage `features/*` (api/hooks/composant), erreurs normalisées
(ADR-0007), React Query + WebSocket live, Zustand persisté (**le patron du jeton de poste**, §4.2), TS strict,
souci d'a11y réel. Les commentaires du code assument le provisoire : « les vrais écrans d'administration
viendront comme features dédiées ».

---

## 11. Registre des décisions

> Chaque décision est arbitrée par le client sauf mention contraire. **Version** = version de ce document où
> elle apparaît. Une décision n'est jamais réécrite silencieusement : elle est **remplacée** par une nouvelle
> ligne, l'ancienne passant à *Remplacée par D-nn*.

| ID | Décision | Statut | Ver. | Remplace / impacte |
|---|---|---|---|---|
| **D-01** | Trois applications : admin / saisie / public. Découpage par **geste**, pas par statut | Actée | 0.1 | CDC design v0.1 §2.1 (contextes C1–C4) |
| **D-02** | Planchers responsive différenciés : saisie 768 px, public 360 px, admin 1280 px | Actée | 0.1 | — |
| **D-03** | Marqueur unique par cible ; la validation du scoreur tient lieu de **seconde marque** | Actée | 0.1 | FFTA B.6.1.1 · `Q-UX3` |
| **D-04** | Plusieurs marqueurs possibles, **tracés à la volée** (équivalent de la signature) | Actée | 0.1 | E10US005 (audit) |
| **D-05** | Parc club, **navigateur seul** (rien à installer) ; tablette/PC minimum ; perso en appoint | Actée | 0.1 | CDC technique (« ~30 tablettes BYOD ») |
| **D-06** | Identité de poste par **jeton persistant**. **Ni IP, ni empreinte** | Actée | 0.1 | Proposition client « IP » écartée, motifs §4.2 |
| **D-07** | Jeton **lié au tournoi et révocable** ; rattachement par **QR** + code de secours | Actée | 0.1 | E04US001, EPIC-09 |
| **D-08** | Cibles attribuées **aux matchs** (positions de tableau) → cible suivante connue d'avance | Actée | 0.1 | E03US009 |
| **D-09** | **Routage omniprésent** sur 4 canaux ; « c'est moi » mémorisé | Actée | 0.1 | **Besoin absent de toutes les US** |
| **D-10** | Table de l'organisation = **un humain**, pas de borne → **recherche globale permanente** | Actée | 0.1 | — |
| **D-11** | Grain de validation = **politique de phase** (`config.validation`) | Actée | 0.1 | ADR-0011 (`config` JSON extensible) |
| **D-12** | Pas de prise en charge de cible ; file **triée par ancienneté** ; validation **tracée** | Actée | 0.1 | — |
| **D-13** | Trois modes d'identité : **lieu** (poste) / **personne** (scoreur) / **secret** (admin) | Actée | 0.1 | **Invalide E10US003 et E10US007** |
| **D-14** | Scoreurs (3–4) définis au tournoi, **redéfinissables à tout moment** | Actée | 0.1 | — |
| **D-15** | **Accès complet en permanence** ; l'appli n'empêche pas, elle avertit. Blocage = « terminé » seul | Actée | 0.1 | — |
| **D-16** | Alerte par **calcul d'impact** : pas d'impact → pas d'alerte | Actée | 0.1 | — |
| **D-17** | **Sportif vs hors sportif** : « terminé » ne fige que le sportif ; les paiements restent ouverts | Actée | 0.1 | E01US002 (cycle de vie) |
| **D-18** | **Complétude** affichée, sportif et tiers comptés séparément | Actée | 0.1 | Réponse à « afficher l'avancement » |
| **D-19** | Ossature admin : **sidebar groupée par temps**, tout cliquable ; repli pour le plan de salle | Actée | 0.1 | — |
| **D-20** | **Accueil contextualisé** par le statut ; *accessible* ≠ *au premier plan* | Actée | 0.1 | — |
| **D-21** | Écran de salle = **poste de l'appli publique** ; déroulé par défaut + prise de contrôle admin | Actée | 0.1 | E07US004 |
| **D-22** | Bascule de tour : **l'admin lance** ; tout est prêt **avant** l'appui ; bouton chiffré | Actée | 0.1 | — |
| **D-23** | **Feu vert** affiché en permanence ; lancement **global ou par événement** | Actée | 0.1 | — |
| **D-24** | **Forfait tracé** : rien ne bloque, tout se documente | Actée | 0.1 | Élargit E04US015 |
| **D-25** | Métrique produit : **bascule de tour < 2 min** | Actée | 0.1 | **Remplace `Q-D3`** (volée < 10 s) |
| **D-26** | **Thème sombre par défaut** (c'est la charte) ; bascule vers le clair **mémorisée par poste, portée par le jeton** | Actée | 0.2 | Amende CDC design §7.1 v0.2 · `DV-02` · §4.5 |
| **D-27** | L'**identité du tournoi** habille **le public et l'écran de salle** ; **l'admin et la saisie restent l'outil** | Actée | 0.2 | `DV-06`, `DV-08` · Ferme la moitié de `Q-UX9` |
| **D-28** | L'**identité est une destination de préparation** : logo + 2 accents, aperçu réel, contrôle de contraste **chiffré et non bloquant** | Actée | 0.2 | `DV-05`, `DV-06` · **Crée E01US016** |

---

## 12. Questions ouvertes

| # | Sujet | À décider | Bloque |
|---|---|---|---|
| **Q-UX1** | « Interdiction d'installer » inclut-elle le **raccourci sur l'écran d'accueil** (PWA) ? Ce n'est pas une installation (pas de store, pas de fichier, pas de permission) et ça rend ~100 px + supprime la sortie accidentelle | À demander au **propriétaire des tablettes**. En attendant : **conçu pour l'onglet** (pire cas) | Rien — dégradation gracieuse |
| **Q-UX2** | **Tri des affectations** sur l'écran de salle : par **nom** (l'archer se cherche) ou par **cible** (l'organisation vérifie) ? | Client | E07US004 |
| **Q-UX3** | La **validation du scoreur vaut-elle double marque** (FFTA B.6.1.1) ? | **Un arbitre du club** — remonte jusqu'au nombre de tablettes à prévoir | `D-03` |
| **Q-UX4** | **Alimentation** des postes (6–10 h d'écran) : prises au pas de tir, batteries, ou veille tolérée ? Si veille : réveil instantané exigé, sinon 15 s perdues par volée | Client / terrain | §4.1 |
| **Q-UX5** | Qui **déclare le forfait** : l'admin, le marqueur sur la tablette, le scoreur ? | Client | `D-24` |
| **Q-UX6** | Liste exacte des **métriques du feu vert** (participants connus ? poste en ligne ? scoreur disponible ? conflit de placement ?) | Client / conception | `D-23` |
| **Q-UX7** | Fin d'une **prise de contrôle** de l'écran de salle : durée fixe ou retour explicite ? | Client | `D-21` |
| **Q-UX8** | **Plan de salle & glisser-déposer : non instruit à ce jour.** Densité, zoom, alternative clavier (a11y), visualisation des contraintes, impression | **Entretien dédié** — c'est l'écran signature de l'admin | E03US001, E03US004 |
| **Q-UX9** | ~~Multilingue et **personnalisation par tournoi**~~ → **la personnalisation est tranchée** (`D-27`, `D-28`, `DV-06`) : logo + 2 accents, sur le public et l'écran de salle. **Reste le multilingue** | Client — cf. `Q-D7` (CDC design) | — |
| **Q-UX10** | **Qui fournit l'identité d'un tournoi ?** L'organisateur dépose un logo — mais le club a-t-il un **graphiste** qui produit l'affiche (comme celle du Challenge des Champions), ou l'organisateur bricole-t-il le jour même ? **Ça change tout** : un SVG propre et calibré, ou un JPEG de 4 Mo sorti d'un téléphone qu'il faudra recadrer, détourer et voiler | Client | `D-28` · E01US016 |
| **Q-UX11** | **Que devient l'identité d'une édition passée ?** L'archive d'un tournoi terminé (`D-17`, E11US003) doit-elle **figer** son identité visuelle (le Challenge 2025 reste le Challenge 2025) ou reprendre celle du club ? Sans décision, rejouer une archive affichera **le mauvais logo** | Client / conception | `D-17`, `D-27` |

---

## 13. Historique des versions

| Version | Date | Auteur | Contenu |
|---|---|---|---|
| **0.2** | 14/07/2026 | Éléments graphiques fournis (`docs/elements_design/`) + arbitrages client | **3 décisions** (`D-26`→`D-28`) issues du versement de la charte réelle. **Le matériau a révélé qu'il y a *deux* marques** — le club (permanent) et l'événement (par édition) — ce que l'architecture en 3 applis n'avait pas anticipé. D'où : **portée de l'identité** limitée à la vitrine (§3.3, `D-27`), **identité = destination de préparation** (§7.1, `D-28`), **thème sombre par défaut avec bascule portée par le jeton de poste** (§4.5, `D-26` — la lumière varie d'une cible à l'autre). Amende `cahier-des-charges-design.md` en **v0.3** (charte versée et **mesurée** : `Q-D1`/`Q-D4`/`Q-D8` fermées). **Ferme la moitié de `Q-UX9`** ; ouvre `Q-UX10`, `Q-UX11`. Crée **E01US016**. |
| **0.1** | 14/07/2026 | Entretien de conception client | Création. 25 décisions (`D-01`→`D-25`) issues de l'entretien du 14/07/2026 : architecture en 3 applis, modèle de poste, 3 modes d'identité, routage omniprésent, bascule de tour, complétude, règles de modification, ossature admin. 9 questions ouvertes. Amende `cahier-des-charges-design.md` en v0.2 (5 contradictions). Invalide E10US003 / E10US007. |

---

## 14. Impacts sur le backlog

> Pour l'agent qui reprend : voici ce que ce document **change** dans les US existantes, et ce qu'il
> **crée**. Le détail est dans `stories/`.

### 14.1 US invalidées — à réécrire

| US | Ce qui casse | Décision |
|---|---|---|
| **E10US003** — « Session scoreur par **code de cible** » | Le scoreur **n'est pas rattaché** à une cible : il butine et choisit. Le code de cible sert au **poste**, pas à lui | `D-12`, `D-13` |
| **E10US007** — « **Rôle archer** : saisir ses scores » | **Il n'y a pas de rôle archer.** La tablette est ouverte : l'identité est le **lieu**. Le « mécanisme d'accès à préciser » de l'US est tranché : **aucun** | `D-13` |
| **E04US001** — « Rattacher un appareil à une cible » | Le rattachement est un **jeton de poste** (QR, lié au tournoi, révocable), pas une session scoreur | `D-06`, `D-07` |
| **E07US004** — « Écran projeté plein écran » | C'est un **poste** supervisé et pilotable, pas une vue autonome | `D-21` |

### 14.2 Besoins non couverts — US à créer

- **Routage** (`D-09`) : « ma prochaine cible » sur la tablette après validation, sur le téléphone, sur
  l'écran de salle. **Absent des 117 US.**
- **Pilotage du jour J** : console de supervision (`D-06`, `D-21`), complétude (`D-18`), bascule de tour
  (`D-22`→`D-24`), recherche globale (`D-10`). **Aucun EPIC ne le couvre** → **EPIC-12**.
- **Marqueur tracé à la volée** (`D-04`).
- **Grain de validation en `config.validation`** (`D-11`).
- **Codes scoreurs** à la configuration (`D-14`) ; **QR de cible** imprimable (`D-07`, EPIC-09).
- **Identité visuelle du tournoi** (`D-27`, `D-28`) : logo + 2 accents, dérivation des variantes accessibles,
  aperçu réel → **E01US016**. **Absent des 117 US** — le CDC design v0.1 la portait en question ouverte
  (`Q-D8`), aucune US ne la couvrait.
- **Thème sombre par défaut + bascule portée par le jeton de poste** (`D-26`) : impacte **E04US001**
  (le jeton porte les préférences, pas seulement le rattachement) et le front (§10 : le thème sombre est
  aujourd'hui piloté par `prefers-color-scheme` **sans bascule manuelle**).
- **Front** : routeur + 3 applis, layout admin, sortie du fourre-tout `TrancheVerticale.tsx` (§10).

---

*Produit à partir de l'entretien de conception du 14/07/2026, du règlement sportif FFTA 2023, des CDC
fonctionnel v0.3 / technique v0.2 / design v0.1, et de l'état du code au 14/07/2026. Document vivant : toute
décision nouvelle s'inscrit au registre §11 avec sa version.*
