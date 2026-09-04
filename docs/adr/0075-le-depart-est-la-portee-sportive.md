# ADR-0075 — Le départ est la portée sportive, pas seulement un créneau logistique

- **Statut** : Accepté
- **Date** : 2026-08-06
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) (dont la décision n'avait été
  portée que par la **logistique** — cf. « Contexte » ci-dessous) ;
  [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (la séquence 1..N est
  désormais celle **d'un départ**) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (`PHASE` change de parent : `DEPART` et non plus `TOURNOI`) ;
  [`docs/glossaire.md`](../glossaire.md) (*Départ*, *Phase*, *Classement*) ;
  [`docs/referentiel-ffta.md`](../referentiel-ffta.md) (§ « portée d'un classement », qui était muet)
- **Complété et partiellement révisé par** : [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
  — le §1 ci-dessous (« la séquence 1..N est celle d'un départ ») est **remplacé** : elle est celle du
  **déroulé du tournoi**, chaque départ n'en portant que l'avancement
- **Introduit par** : E01US025 (le format de tournoi porte un effectif **par départ** et un déroulé
  rejoué **par départ**) — la décision la précède logiquement et a donc été appliquée d'abord

## Contexte et problème

[ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) a tranché, le 16/07/2026, le sens du mot
« départ », en citant l'arbitrage de l'organisateur mot pour mot :

> « un départ est un créneau horaire sur un tournoi, **comme si le tournoi pouvait se jouer plusieurs
> fois dans la même journée** »

**Seule la moitié logistique de cette phrase a été portée dans le code.** Un an de développement plus
tard, `Depart` porte un horaire, un tarif, un quota, des inscriptions, un placement et une feuille de
marque — tout ce qui remplit la salle. Mais rien de ce qui **compte les points** ne le connaît :

| Ce que « le tournoi se joue plusieurs fois » impliquait | État constaté le 06/08/2026 |
|---|---|
| Une séquence de phases par départ | `Phase.tournoi_id` — aucune notion de départ dans `domain/phase.py` |
| Des ordres 1..N par départ | `SequencePhases` valide 1..N **par tournoi** (ADR-0045 §3) |
| Un classement par départ | `ServiceClassements.pour_tournoi()` classe **tous** les archers du tournoi |
| Des tableaux et duels par départ | `domain/tableau.py`, `domain/duel.py` — zéro occurrence de « départ » |
| Un prélèvement « rangs 1 à 16 **de mon départ** » | `SourcePhase` prélève dans la phase amont, toutes vagues confondues |
| Le modèle de données | `TOURNOI ||--o{ PHASE : "séquence"` |

Concrètement : sur un tournoi de 4 départs de 100 archers, l'application produit **un** classement de
400, où l'archer du matin est rangé contre celui du soir qu'il n'a jamais affronté.

**Pourquoi personne ne l'a vu.** L'oracle 120 — le rejeu de `Tableaux.xlsx`, garde-fou le plus solide
du projet (règle 9) — ne contient **aucun départ** (zéro occurrence dans le test). Il valide un
tournoi **mono-départ**, cas où portée tournoi et portée départ se **confondent**. Le modèle était
donc juste par accident, et le seul test capable de révéler l'écart ne l'exerçait pas.

**C'est le vrai enseignement de cet ADR, et il dépasse le sujet du départ** : une décision d'ADR
n'était reliée à **aucun** module chargé de la porter, et aucun test ne couvrait le cas qui les
distingue. Une décision écrite mais non rattachée au code n'est pas une décision, c'est une
intention — et elle diverge en silence, d'autant plus vite que le projet grossit.

## Décision

**Le départ est la portée sportive du tournoi.** Un départ est une *exécution complète* de la
compétition : il a sa séquence de phases, ses classements, ses tableaux, ses duels et son podium. Les
archers de deux départs ne sont jamais comparés.

1. **`Phase` appartient au départ** (`depart_id`), plus au tournoi. `SequencePhases` valide la suite
   contiguë 1..N **d'un départ** ; ses invariants sont inchangés, seule leur portée l'est.
2. **Le classement se calcule par départ.** `calculer_classement` reste une fonction pure sur un lot
   d'archers — c'est l'**appelant** qui ne lui passe plus que les archers d'un départ. Le rang
   scratch et le rang de catégorie sont donc des rangs *dans le départ*.
3. **Tableaux, duels, barrages et suivi de déroulé suivent la phase**, donc le départ, sans autre
   changement que leur rattachement.
4. **Les prélèvements (`SourcePhase`) restent intra-départ.** « Les rangs 1 à 16 de la phase 1 »
   désigne les rangs 1 à 16 *de la phase 1 de ce départ*. Aucune source ne traverse un départ.
5. **Le tournoi reste le contenant** : identité, dates, club organisateur, inscriptions, copies du
   patrimoine, format appliqué. Il n'a plus de phases en propre — les siennes sont l'union de celles
   de ses départs.
6. **Appliquer un format crée une séquence par départ.** Les N départs partent de **copies
   identiques** du déroulé du format, puis vivent leur vie : ajuster la phase 2 du départ 1 ne touche
   pas le départ 2. C'est le même patron de copie que partout ailleurs dans le patrimoine
   (ADR-0060) — un cran plus bas.

### Composer n'est pas piloter — deux mailles, deux écrans

*(Précision apportée par l'organisateur le 06/08/2026, en cours d'US.)*

Le départ est la portée **d'exécution**, pas la portée d'**édition**. La distinction se lit sur les
axes de l'application :

| | Maille | Où |
|---|---|---|
| **Composer** le déroulé (ajouter, éditer, réordonner, supprimer une phase) | **tournoi** | atelier |
| **Placer** une phase sur un créneau et la **faire vivre** (démarrer, mettre en pause, terminer) | **départ** | pilotage |

**Pourquoi la composition reste au tournoi.** Le déroulé n'est pas plus « par créneau » que le
barème : c'est le **même** déroulé rejoué, et c'est exactement ce que fait `FormatTournoi.appliquer`
en distribuant des copies identiques. Régler la séquence « pour le tournoi » l'écrit donc sur la
séquence de chaque départ — **écriture en éventail**, comme le barème et le grain. L'atelier ignore
les créneaux, et le format aussi : *seul le tournoi concret sait sur combien de départs il se joue.*

**Pourquoi le cycle de vie descend au départ.** Il ne peut pas s'appliquer en éventail : le créneau
du matin peut être **en duels** pendant que celui de l'après-midi **qualifie encore**. C'est même
l'un des bénéfices annoncés plus haut. Démarrer une phase « pour tout le tournoi » forcerait les
deux vagues à avancer du même pas, ce que la journée réelle ne permet pas.

⚠️ **`ServicePhases` porte donc deux mailles**, et c'est délibéré, non un oubli : ses opérations de
composition prennent un `tournoi_id`, celles de cycle de vie un `depart_id`. Un service qui n'en
aurait qu'une serait faux dans un sens ou dans l'autre.

### Ce qui a été écarté

- **Garder `Phase.tournoi_id` et ajouter `depart_id`.** Deux portées coexistantes obligeraient chaque
  lecture à choisir laquelle honorer, et la première qui se tromperait rétablirait le bug en silence.
  Une phase a **une** portée.
- **Scoper seulement le classement, en laissant les phases au tournoi.** C'est le correctif qui
  répare le symptôme visible et laisse la maladie : le `statut` d'une phase serait partagé, donc un
  départ en duels forcerait l'autre à l'être aussi alors qu'il qualifie encore.

## Conséquences

**Positives**

- Le code dit enfin ce qu'ADR-0017 avait décidé ; le mot « départ » a le même sens partout.
- Le format de tournoi (E01US025) peut porter un effectif **par départ** — sa notion naturelle,
  déjà présente sous le nom `Depart.quota`.
- Chaque départ étant étanche, plusieurs départs peuvent avancer **indépendamment** le jour J : le
  départ du matin peut être en duels pendant que celui de l'après-midi qualifie.

**Coûteuses / à surveiller**

- **Migration destructrice de portée** : les phases existantes doivent être rattachées à un départ.
  Les tournois **mono-départ** se migrent sans perte (leur unique départ reçoit la séquence) ; un
  tournoi **sans départ** ne peut pas conserver ses phases — cas traité explicitement par la
  migration, pas laissé au hasard.
- **Rupture d'API** : les routes de phases et de classement changent de parent
  (`/tournois/{id}/phases` → `/departs/{id}/phases`). Acceptable, l'application n'ayant aucun client
  tiers (mono-club, réseau local).
- **L'oracle 120 doit gagner un cas multi-départ.** Sans lui, cet ADR pourrait diverger comme
  ADR-0017 l'a fait.

### Remèdes contre la récidive (le point que l'organisateur a demandé)

Cette divergence a coûté cher parce que rien ne la rendait **visible**. Trois mesures, toutes
appliquées dans l'US qui porte cet ADR :

1. **Un ADR nomme les modules qui le portent.** Un champ « **Porté dans le code par** » listant les
   fichiers responsables. Un ADR qui n'en nomme aucun est une intention, pas une décision — et ça se
   voit en revue. ADR-0017 est amendé rétroactivement pour porter ce champ.
2. **Un test de conformité de portée** (`tests/test_portee_sportive.py`), sur le modèle du garde-fou
   d'isolation du domaine : il échoue si une phase, un classement ou un tableau redevient rattaché au
   tournoi. Mécanique, donc insensible à l'oubli.
3. **L'oracle gagne un scénario multi-départ**, parce que le cas qui distingue les deux portées doit
   être exercé par le test qui fait autorité — c'est son absence qui a permis douze ADR de silence.

## Porté dans le code par

- `backend/domain/phase.py` (`Phase.depart_id`, `SequencePhases`)
- `backend/application/classements.py` (`pour_depart`, et **plus** de `pour_tournoi`)
  ⚠️ *Corrigé le 07/08/2026 en revue : cette liste nommait aussi `domain/classement.py`,
  `domain/tableau.py` et `domain/duel.py`, qui ne portent **rien** de la portée — aucun n'a de champ
  de rattachement, ils suivent la phase par `phase_id`. Une section « Porté dans le code par » qui
  nomme des modules vides reproduit exactement le défaut d'ADR-0017 qu'elle existe pour empêcher.*
- `backend/domain/format_tournoi.py` (`appliquer` produit **le déroulé** du tournoi — une séquence
  unique, ADR-0076 ayant révisé cette ligne : elle annonçait « une séquence par départ », ce que le
  code n'a jamais fait dans sa forme livrée)
- `backend/infrastructure/db/repositories/moteur.py` + migration `0042`
- `backend/tests/test_portee_sportive.py` (garde-fou mécanique)

## Portée de la règle « Porté dans le code par » — tranchée le 08/08/2026

*(Cette section **borne** la règle que le présent ADR a fait naître le 06/08/2026 et que
`CLAUDE.md` § Workflow énonce. Elle vit ici, et non seulement dans `CLAUDE.md`, pour qu'un lecteur
qui arrive par `docs/adr/` ne lise jamais la règle sans sa borne.)*

### Le problème

La règle est née d'un cas réel — la décision d'[ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md)
n'a été portée qu'à moitié pendant treize mois — mais elle n'a pas été appliquée rétroactivement :
au 08/08/2026, **8 ADR sur 81** portaient la section. Les 73 autres étaient donc, à la lettre de
`CLAUDE.md`, des « intentions ». Rétro-équiper les 73 aurait produit une soixantaine de sections
cosmétiques pour en sauver une utile.

### Décision

La règle vaut :

1. **Pour tout ADR neuf**, sans exception.
2. **Pour tout ADR modifié** dont le diff touche sa section *Décision* ou *Conséquences* — c'est la
   définition opératoire de « **une US le rouvre** ». Un ADR qui gagne une coquille corrigée ou un
   lien réparé ne se « rouvre » pas.
3. **Pour les ADR structurants encore actifs**, au sens du critère ci-dessous.

**Critère (reproductible par un tiers).** Un ADR est *structurant encore actif* si **les deux**
conditions tiennent :
- son statut est **Accepté** et il n'a pas été *remplacé* par un ADR postérieur ; **et**
- sa décision est appliquée par le **moteur sportif** (déroulé, séquence de phases, placement,
  classement, duels, palmarès), par la **portée** (tournoi / départ / phase), ou par une
  **politique injectable** au sens de la règle 2 (`routing`, `scoring`, `seeding`, `byes`,
  `tiebreak`, `depth`, `aggregation`).

Un ADR d'**outillage**, d'**UI**, de **procédure** ou de **convention documentaire** n'entre pas
dans le critère : c'est un ADR de moteur non porté qui a coûté treize mois, pas un ADR de
gestionnaire de paquets. **Leur absence de section n'est pas un défaut à relever en revue.**

**Les seize ADR retenus**, rétro-équipés les 08/08/2026 :
`0004`, `0011`, `0017`, `0026`, `0028`, `0045`, `0046`, `0049`, `0060`, `0061`, `0062`, `0066`,
`0067`, `0068`, `0069`, `0070`.

⚠️ **`0050` manquait aux deux listes**, relevé en revue d'E16US008 (axe C2) — et il faut être
précis sur le mode de panne, parce que ce n'est **pas** celui que la section mesure plus bas. Les cas
`0087`/`0089`/`0090`/`0091` étaient des ADR **neufs** qui portaient leur section sans être inscrits
ici : la liste n'était pas tenue. `0050`, lui, ne portait **aucune** section : c'est le
**rétro-équipement du 08/08 qui a manqué un ADR de moteur** — et pas le seul. Un balayage des ADR
sans section, croisé au critère ci-dessus, rend au moins cinq autres candidats (`0023` placement
glouton, `0027` vocabulaire de score **injectable** au sens de la règle 2, `0047` et `0048`
placement/réordonnancement des duellistes, `0065` rang acquis sur la plage). ⚠️ Ne pas conclure de
`0050` que le trou est refermé : **la liste des seize retenus n'a jamais été auditée**, et le
présent paragraphe ne l'audite pas non plus — il le constate. C'est inscrit à `DETTE-091`, faute de
quoi ce balayage sera redemandé une troisième fois sans porteur. Il entre au
critère sans discussion — le forfait commande le **classement de qualification**
(relégation/exclusion) *et* la reconstruction du **tableau** (walkover) — et il est ajouté ici parce
que la même US le **rouvre** (sa *Décision* change d'acteur en duels) ; sa section « Porté dans le
code par » a donc été écrite dans le même commit. Leçon distincte, donc : la liste des **seize
retenus** mérite le même balayage que celle des ajouts.

**Ajoutés depuis** (ADR neufs, donc soumis à la règle sans rétro-équipement) : `0080`, `0081`,
`0082`, `0083`, `0084`, `0085`, **`0087`**, `0090`, `0091`, `0092`, `0093`, `0094`, **`0103`**
(E16US014, 31/08/2026 — la portée d'un podium devient un réglage de tournoi : le moteur publie
un **troisième espace de rangs** et la notion de podium change de définition), **`0104`**
(E16US017, 04/09/2026 — le classement des **clubs entre eux**, au décompte de médailles
inter-clubs : un classement neuf, dont l'entité classée n'est pas un archer), **`0105`**
(E16US015, 04/09/2026 — le QR d'un scoreur porte son code : le **canal de distribution** d'un
secret personnel change, ce qui amende ADR-0025 § Décision 2, dont la phrase « distribué sur
papier et retapé » devenait fausse en silence). Et, par
**réouverture**, **`0025`** (E16US015, 05/09/2026 — ADR-0105 amende sa *Décision 2* : le code
cesse d'être « distribué sur papier et **retapé** » pour devenir scannable ; section « Porté dans le
code par » écrite à cette occasion), **`0103`** une seconde fois (E16US017, 04/09/2026 — sa *Décision 3* affirmait
« `DETTE-029` n'a pas gagné de 5ᵉ site », ce que `0104` rend faux, et sa mention de la lecture
conditionnelle du référentiel des clubs était périmée par la levée du bornage ; sa section
« Porté dans le code par » a été re-vérifiée symbole par symbole à cette occasion — front compris,
`etatPodium` n'étant pas un symbole Python). Et, par
réouverture plutôt que par création : **`0067`** (E16US014, 31/08/2026 — sa Décision 5 figeait
le podium « par catégorie, rangs 1-4 » ; elle est révisée par `0103`, et sa section « Porté dans
le code par » a été re-vérifiée symbole par symbole à cette occasion), **`0050`** (E16US008, 28/08/2026 ; **rouvert une 2ᵉ fois** par E16US007 le 30/08/2026 — la qualification rejoint le régime « admin ou scoreur », et sa section « Porté dans le code par » nommait `autoriser_forfait_duel`, symbole que le diff avait supprimé). La liste dérive à
chaque US qui crée ou rouvre un ADR structurant — c'est pourquoi elle vit ici et non dans
`CLAUDE.md`.

⚠️ **`0087` et `0089` manquaient aux DEUX listes, et l'intervalle `0086`-`0089` sautait sans un mot**
— relevé en 3ᵉ passe de revue d'E16US009 (axe adversarial), dans le paragraphe même qui dénonce ce
mode de panne : la 2ᵉ passe avait réparé le cas signalé (`0097`) **sans auditer l'intervalle**.
Tranchés à l'occasion, tous deux portant déjà leur section « Porté dans le code par » :
- **`0087` entre au critère** (ci-dessus) — *« une attente n'est pas une indisponibilité »* décide
  d'une valeur d'`IssueRoutage`, que le **moteur de routage** produit et que l'écran ne fait que
  rendre ;
- **`0089` en est hors** (liste ci-dessous) — le catalogue `VueEcran` est de l'**IHM** : il dit ce
  qu'un écran de salle sait dessiner, aucun classement n'en dépend.

*Le geste d'audit correct n'est pas de recopier la liste : c'est de balayer `ls docs/adr/` sur
l'intervalle et de rapprocher des deux listes. Une liste tenue à la main ne se répare pas au cas par
cas.*

⚠️ **`0090` y a été oublié à son tour**, et rattrapé en revue d'E05US032 (axe C2) — soit la
**troisième** omission consécutive sur cette liste. Le constat ci-dessous n'a donc rien perdu de son
actualité, et il faut le lire comme une mesure : le réflexe n'est pas acquis, seule la revue le tient.

⚠️ **`0091` a été oublié à son tour** — **quatrième** omission consécutive, constatée en écrivant
`0092` (E05US034, 20/08/2026), donc cette fois *hors revue*. Les deux sont ajoutés ci-dessus. Le
point mérite d'être dit sans détour : quatre fois sur quatre, l'ADR neuf **portait** sa section
« Porté dans le code par » — c'est bien cette **liste** qui n'est pas tenue, pas la règle qu'elle
borne. Le geste manquant est de deux mots dans un fichier qu'on n'ouvre pas en créant un ADR
ailleurs, et rien dans le dépôt ne le réclame : ni le hook, ni la CI, ni l'atlas (qui vérifie les
sections **existantes**, pas leur inscription ici). Tant qu'aucun contrôle ne l'exige, l'inscription
restera un oubli par défaut plutôt qu'un réflexe — **le rendre vérifiable est une US, pas une note**
(candidat naturel pour la tranche d'atlas `E00US021` ou un contrôle voisin).

✅ **`0093` (E05US035, 20/08/2026) est inscrit du premier coup**, sans passer par la revue — la
série de quatre omissions s'arrête là. Ce n'est pas une réfutation du constat ci-dessus mais sa
confirmation par l'autre bout : l'inscription a tenu parce que l'US **précédente** venait de la
manquer et l'avait écrit ici. Autrement dit, le rappel a fonctionné une fois, sur la seule US qui
suivait immédiatement le constat — ce qu'aucun contrôle automatique n'a encore remplacé. La
conclusion reste entière : **le rendre vérifiable est une US.**

⚠️ **`0095` (E16US002, 22/08/2026) n'y figure PAS, et c'est volontaire.** Il est de **vocabulaire et
d'IHM** — un titre de phase est un libellé que le moteur ne lit jamais (ADR-0095 §3), et le reste de
la décision porte sur des libellés de menu et une bascule d'écran. Le critère de `CLAUDE.md` exclut
nommément les ADR d'outillage, d'UI, de procédure et de convention documentaire ; les précédents
existent (`0086`, `0088`). Il porte en revanche sa section « Porté dans le code par », exigée de
**tout** ADR neuf sans condition. *C'est noté ici parce que cette section documente quatre omissions
consécutives, chacune rationalisée après coup : un trou non commenté dans cette liste est
précisément ce qui produit la cinquième — un lecteur qui audite verrait « …0093, 0094 » puis rien.*

⚠️ **`0098` (E16US009, 2026-08-26) n'y figure PAS non plus, et c'est volontaire.** Même motif que
`0095` : il est d'**IHM** — un écran de salle *montre* un classement, il n'en produit aucun ; le
moteur sportif ne lit rien du réglage de pages, aucune portée ne change, aucune politique injectable
n'est en jeu. Il porte sa section « Porté dans le code par », exigée sans condition. *La liste des
ADR **hors critère** est donc, à ce jour : `0086`, `0088`, **`0089`**, `0095`, `0096`, **`0097`**,
`0098`, **`0099`** (E00US027 — convention documentaire : une règle d'écriture des commentaires ne
change ni portée, ni moteur, ni politique injectable ; inscrit ici en revue plutôt que laissé
expliqué chez lui, le mode de panne que ce paragraphe décrit), **`0100`** (E16US010 — **navigation
et IHM** : l'adresse d'admin gagne un 4ᵉ segment, l'élément ouvert ; aucun moteur ne lit une
adresse, aucune portée ne change. Inscrit **en 2ᵉ passe de revue** : l'ADR argumentait son
exclusion **chez lui** et l'intervalle sautait de `0099` à rien — la 5ᵉ occurrence du mode de panne
que ce paragraphe décrit, et la 2ᵉ fois qu'il se produit dans la même US), **`0101`** (E16US007 —
**outillage documentaire** : un catalogue de formats de fichier ne touche ni portée, ni moteur, ni
politique injectable au sens de la règle 2. ✅ **Inscrit du premier coup, hors revue** — 3ᵉ US
d'affilée), **`0102`** (E00US028 à E00US030 — **convention documentaire**, exactement au même titre
que `0099` : une règle d'écriture ne touche ni portée, ni moteur, ni politique injectable.
✅ Inscrit du premier coup, à l'écriture de l'ADR — 4ᵉ US d'affilée) —
⚠️ `0097` (le logo de tournoi) y manquait : la liste avait été recopiée depuis ADR-0098, qui
l'omettait déjà, et c'est le paragraphe même qui dénonce ce mode de panne qui l'a reproduit
(rattrapé en 2ᵉ passe, axe adversarial). Écrite ici et
pas seulement dans chaque ADR concerné, pour la raison même que cette section documente : un trou
non commenté dans l'énumération se lit comme un oubli, et c'est ainsi qu'on en produit un vrai.*
*(Inscription réclamée en revue d'E16US009, axe C2 : l'ADR expliquait son exclusion chez lui, pas ici.)*

✅ **`0094` (E05US029, 21/08/2026) est inscrit du premier coup**, lui aussi hors revue — deux US
d'affilée, cette fois sans que la précédente ait eu à manquer quoi que ce soit. C'est le premier
signe que le réflexe tient de lui-même ; deux points ne font pas une tendance, et le constat
ci-dessus reste debout tant qu'aucun contrôle ne le mécanise.

⚠️ **`0084` y avait été oublié à sa création, et `0085` a failli l'être** (relevé en revue
d'E05US026, deux fois). Deux omissions de suite sur le registre qui existe pour empêcher
exactement ça : la liste ne se met pas à jour toute seule, et l'auteur d'un ADR neuf est le
moins bien placé pour se souvenir de l'y inscrire. C'est à la revue de le vérifier — l'axe qui
juge les ADR a le log de branche en périmètre, il voit donc les ADR créés.

> *`0049`, `0066` et `0067` ont été ajoutés en revue le 08/08/2026 : le premier jet appliquait le
> critère « politiques » tout en excluant deux ADR **de politique** (`0066` porte le seuil de
> barrage dans `tiebreak`, `0067` ajoute la 7ᵉ famille `aggregation`) et l'ADR de **scoring** des
> duels. La liste ne découlait donc pas de son propre critère — défaut relevé par l'axe adversarial.*

### Le garde-fou

Une règle qui borne ce qu'une revue a le droit de relever doit dire **qui la vérifie**, sinon elle
ne retire que de la détection. La grille de revue (`.claude/agents/revue-axe-c2.md`, règle `12-ADR`, orchestrée par
`.claude/commands/revue-us.md`)
porte donc la contrepartie : elle exige la section sur tout ADR **créé**, et sur tout ADR
**rouvert** au sens du point 2. Sans cette contrepartie, le bornage serait un pur affaiblissement.

### Conséquence assumée

L'énumération ci-dessus **dérivera** : un ADR hors liste qui devient structurant la rejoindra le
jour où une US le rouvre. C'est pourquoi elle vit **ici** — dans le registre que les US touchent —
et non dans `CLAUDE.md`, qui ne porte que le critère.

⚠️ **Écrire la section, c'est vérifier dans le code du jour, pas déduire de l'ADR.** Le
rétro-équipement l'a prouvé deux fois : `ADR-0028` (équipes) n'est porté **qu'au quart** — la classe
`Equipe` n'existe pas — et `ADR-0049` promet dans son titre un barème résolu par « (phase, arme) »
que le code résout par l'**arme seule**. Ni l'un ni l'autre ne se voyait sans ouvrir les modules.
