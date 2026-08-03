# Audit de maintenabilité — 03/08/2026

> Commandé après E06US004, sur ce constat du commanditaire : *« le temps que tu passes à faire les
> US me fait penser que le code a perdu en maintenabilité et agilité »*.
>
> Le constat est **fondé**, mais la cause n'est pas celle qu'on suppose spontanément. Ce document
> donne les mesures, distingue ce qui coûte de ce qui ne coûte pas, et propose trois actions
> classées par coût mesuré.

## Méthode et limites

Toutes les mesures viennent de `git` et du code au commit `e0a766e` (92 US mergées). **Aucune mesure
de temps d'exécution n'a été faite** : quand ce document parle de « coût », il parle de lignes, de
fichiers touchés et de défauts constatés — jamais de millisecondes ni d'heures-homme. Les
volumétries de diff sont un **proxy** de l'effort, pas l'effort.

Biais à connaître : l'auteur de cet audit est l'auteur du code qu'il audite.

---

## 1. Le coût d'une US a triplé — mais pas là où on croit

Insertions et fichiers touchés par US fonctionnelle mergée, par tranche de 10 :

| US | insertions / US | fichiers / US |
|---|---|---|
| 1-10 | 823 | 18 |
| 21-30 | 1 145 | 20 |
| 41-50 | 1 241 | 19 |
| 61-70 | 1 670 | 24 |
| 71-80 | 1 437 | 19 |
| **81-90** | **4 925** | **55** |

La rupture est nette et **récente**. Répartition de ces insertions :

| | US 41-50 | US 81-90 |
|---|---|---|
| code backend | 267/US (21 %) | 1 546/US (31 %) |
| tests backend | 370/US (29 %) | 1 516/US (30 %) |
| code front | 323/US (26 %) | 917/US (18 %) |
| **documentation** | **193/US (15 %)** | **684/US (13 %)** |
| tests front | 86/US (7 %) | 203/US (4 %) |

**La part de documentation est stable, celle des tests aussi.** Le process n'explique pas la
rupture : c'est le **contenu** des US qui a changé. Les dix dernières sont le chantier moteur
(placement intégral 1→N, catalogue de types de phase, atelier de déroulé, écran de salle, barrage,
palmarès) — des fonctionnalités structurellement plus grosses que « ajouter un champ horaire ».

**Conclusion 1 : une partie du ralentissement est légitime.** Supprimer la doc ferait gagner 13 %
et perdre la traçabilité qui a rattrapé, en E06US004, une médaille décernée avant la finale.

---

## 2. Ce qui, en revanche, est une vraie perte d'agilité : le rayon d'impact

Nombre de fichiers de production **déjà existants** qu'une US doit modifier :

| US | fichiers existants modifiés / US |
|---|---|
| 1-10 | 6 |
| 41-50 | 7 |
| **81-90** | **18** |

Une US ne s'écrit plus dans son coin : elle doit **entrer dans 18 fichiers qu'elle ne possède pas**.
C'est la définition opérationnelle de « le code résiste au changement », et c'est là que l'agilité
s'est perdue.

### Les passages obligés

Fichiers existants modifiés par au moins 5 des 12 dernières US :

| US touchées | Taille | Fichier |
|---|---|---|
| 8/12 | 1 028 | `backend/bootstrap/composition.py` |
| 8/12 | 3 524 | `frontend/src/app/App.css` |
| 7/12 | 3 378 | `backend/infrastructure/db/repositories.py` |
| 7/12 | 941 | `backend/domain/erreurs.py` |
| 5/12 | 1 166 | `backend/domain/ports.py` |
| 5/12 | 962 | `backend/application/erreurs.py` |
| 5/12 | 714 | `backend/infrastructure/db/models.py` |
| 5/12 | 716 | `backend/domain/tableau.py` |
| 5/12 | 979 | `backend/domain/politiques.py` |
| 5/12 | 873 | `backend/domain/phase.py` |
| 5/12 | 591 | `frontend/src/features/admin/CoquilleAdmin.tsx` |

Ces onze fichiers se répartissent en **deux familles très différentes**, et les confondre mènerait
au mauvais remède.

**Famille A — les agrégateurs techniques** (`repositories.py`, `erreurs.py` ×2, `App.css`,
`models.py`, `composition.py`). Un seul fichier par *préoccupation technique*, où toutes les
features viennent écrire. `erreurs.py` porte à lui seul **171 classes d'exception** (94 domaine +
77 application) ; `repositories.py` porte **tous** les adapters SQL en 3 378 lignes ; `App.css`
**tout** le style en 3 524 lignes.

C'est exactement l'organisation que la règle 10 **interdit au front** (« par features, pas par type
technique ») — et qu'aucune règle n'interdit au backend. Le coût est mécanique : conflits, relecture
d'un fichier de 3 000 lignes pour ajouter 20 lignes, et un `git blame` illisible.

**Famille B — le cœur métier** (`tableau.py`, `politiques.py`, `phase.py`, `ports.py`). Ceux-là sont
touchés parce que le moteur de phases **est** le sujet des dernières US. C'est normal et sain : on
n'ajoute pas un format de tournoi sans toucher au moteur. **Ne rien y faire.**

---

## 3. La dette qui fabrique des défauts

23 dettes ouvertes (5 majeures), 9 résorbées. La plupart sont des raccourcis assumés qui coûtent de
la friction. **Une seule fabrique des défauts visibles par l'utilisateur** :

### `DETTE-028` — le moteur ignore `phase.sources`

`ServiceSaisieDuels._decor` ensemence le tableau avec **tous** les archers en lice, sans jamais lire
les prélèvements déclarés par la phase. Conséquence : il n'existe qu'**un seul tableau scratch**,
jamais un tableau par catégorie ni par tranche de rangs.

En E06US004 seule, cette dette a produit **trois des cinq bloquants** trouvés en revue :

1. le palmarès affichait « 1ᵉʳ-120ᵉ » sur toutes ses lignes pendant toute la matinée ;
2. un walkover de forfait rouvrait ce même défaut ;
3. **le podium par catégorie est impossible à décerner par des matchs** — arbitré le 03/08 en
   affichant la provenance (« Bronze · au classement »), faute de pouvoir faire mieux.

Le CA d'E06US004 (« rangs 1-4 issus de la finale/petite finale ») **présuppose un tableau par
catégorie**. Le produit ne sait pas le faire. Tant que c'est vrai, chaque US de classement paiera le
même écart entre ce que le métier décrit et ce que le moteur exécute.

### `DETTE-031` — la reconstruction d'arbre, quatre fois, sans cache

`ServiceSaisieDuels.reconstruire` (classement complet + arbre rebâti + duels rejoués) a désormais
**4 consommateurs** (`routage`, `pilotage_tour`, `suivi_deroule`, `palmares`), sur des routes
publiques pollées. C'est la seule façon de savoir quoi que ce soit d'un tableau : toute nouvelle
lecture devra y passer.

Coût aujourd'hui : perf (non mesurée, LAN fermé). Coût réel : **couplage** — quatre services
dépendent du service de saisie.

---

## 4. Ce qui ne coûte pas, et qu'il ne faut donc pas « optimiser »

Trois soupçons naturels, écartés par les mesures :

- **La documentation** : 13-15 % des insertions, stable depuis le début. 68 ADR pour 92 US. C'est ce
  qui permet à une session repartant d'un `/clear` de retrouver *pourquoi* une décision a été prise.
- **Les tests** : 30 % des insertions, stable. 48 561 lignes pour 21 836 lignes de code de
  production effectif (2,2×). L'oracle 120 est le filet qui autorise à toucher au moteur.
- **La revue à cinq axes** : elle a trouvé, sur la seule E06US004, cinq bloquants **visibles par le
  public** (médaille avant la finale, podium sur la qualification, classement plat toute la matinée).
  Son coût est du temps d'assistant, pas de la dette de code.

⚠️ **Un chiffre mérite quand même surveillance** : les docstrings représentent **28 %** des lignes du
backend de production (11 910 lignes sur 42 345). C'est un choix assumé du projet — mais chaque
modification d'une règle oblige à réécrire un paragraphe. À ne pas réduire par principe ; à
surveiller si le ratio dépasse le tiers.

---

## 5. Actions proposées, par coût mesuré décroissant

| # | Action | Ce que ça rend | Coût |
|---|---|---|---|
| **1** | **Résorber `DETTE-028`** — le moteur consomme `phase.sources` **par rangs** | Le tournoi se déroule comme le schéma composé ; supprime la cause des défauts « palmarès plat ». ⚠️ **Correction du 03/08** : ne rend **pas** possible le podium par catégorie — `SourcePhase` sélectionne par **rangs** et `Phase` ne porte aucune catégorie (vérifié au cadrage d'E05US020). Les tableaux par catégorie sont une **US distincte**, avec son ADR | ✅ livrée (E05US020, [ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md)) |
| **2** | **Découper les 4 agrégateurs techniques** (`repositories.py`, les deux `erreurs.py`, `App.css`) **par feature** | Retire ~4 des 18 fichiers existants qu'une US doit modifier. Mécanique, sans changement de comportement, testable par la suite existante | 1 US de refactor, risque faible |
| **3** | **Mémoïser `reconstruire`** par `(tournoi_id, version)`, invalidée sur `donnees_modifiees` | Résorbe `DETTE-031` | À ne faire **que** si une mesure le réclame — aucune mesure n'existe |
| — | Documentation, tests, procédure de revue | — | **Ne rien changer** : mesurés stables et rentables |

⚠️ **Correction apportée à ce document le 03/08/2026**, au cadrage d'E05US020 : l'action 1 était
présentée comme rendant possible « le vrai podium par catégorie ». C'est **faux** — consommer les
prélèvements donne « les rangs 1 à 32 du classement scratch », jamais « les Seniors Hommes ». Le
podium par catégorie demande un concept qui n'existe pas (une phase scopée à une catégorie), donc une
**troisième action** : *US « tableaux par catégorie » + ADR*. Vérifier avant de promettre aurait évité
de faire croire qu'une US en réglerait deux.

**Ordre recommandé : 1, puis 2.** L'action 1 traite ce qui casse des cas utilisateurs ; l'action 2
traite ce qui ralentit. L'action 3 attend une mesure.

---

## 6. Ce qui relève de l'assistant, pas du code

Une part du coût d'E06US004 m'est imputable et n'a rien à voir avec la maintenabilité :

- j'ai **ajusté un test au code** au lieu de questionner le comportement quand il a échoué —
  exactement le piège que la règle 9 décrit. Coût : un tour de revue entier ;
- j'ai perdu des cycles sur des scripts de patch fragiles au lieu d'éditer directement ;
- le même schéma d'erreur s'est répété quatre fois dans l'US (un prédicat juste dans l'espace du
  tableau, réutilisé tel quel dans l'espace de la catégorie). La question « où ailleurs ce
  raisonnement s'applique-t-il ? » n'a été posée qu'à la contre-revue.

Ces trois points se corrigent par de la discipline, pas par du refactor.
