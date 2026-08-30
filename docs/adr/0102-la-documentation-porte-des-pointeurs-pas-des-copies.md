# ADR-0102 — La documentation porte des pointeurs, pas des copies

- **Statut** : Accepté *(la **décision** est prise ; **rien ne l'implémente encore** — cf. § « Porté dans le code par », qui le dit au lieu de le laisser croire)*
- **Date** : 2026-08-30
- **US** : `E00US028`, `E00US029`, `E00US030`
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0099](0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md) — la **même** décision, prise
    pour le code. Cet ADR l'étend à la documentation, qui en avait été exemptée sans que personne
    ne l'ait décidé
  - [ADR-0086](0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md) — l'atlas : l'outil
    qui rend la vérification possible existe déjà, et il lit déjà les ADR
  - [ADR-0075](0075-le-depart-est-la-portee-sportive.md) — la section « Porté dans le code par »,
    et les quatre fois où elle a nommé un module qui ne portait rien

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'ADR-0075 § « Portée de la règle »**, et c'est
> volontaire : c'est une **convention documentaire**, au même titre qu'`0099` qui y est déjà inscrit
> pour cette raison. Aucun moteur sportif ne lit une règle d'écriture, aucune portée ne change.
> **Il est en revanche à inscrire à la liste « hors critère »** — c'est cette liste, et non un
> plaidoyer chez soi, qui borne ce qu'une revue a le droit de relever.

## Contexte

La règle 13 (ADR-0099) interdit au **code** de recopier un raisonnement, au motif qu'« un
commentaire est le seul artefact que **rien ne vérifie** : une phrase fausse y survit indéfiniment
et se lit comme une preuve ». Le raisonnement a été chassé du code — et déversé dans une
documentation qui, elle, n'est vérifiée par rien non plus.

### Ce qui a été mesuré, sur `E16US007` (30/08/2026)

| Mesure | Valeur |
|---|---|
| Lignes de documentation du lot | 527 |
| Lignes de code et de tests | 1 812 |
| **Documents touchés** | **13** |
| **Documents devant énoncer le même fait** *(« le forfait de qualification s'ouvre à l'admin »)* | **11** |

Le volume n'est pas le problème : 527 lignes de doc pour 1 812 de code est un ratio sain. **Le
problème est l'éparpillement d'un fait unique sur onze fichiers.** Quatre des dix majeurs de la
revue de cette US sont exactement cela — non pas des erreurs d'écriture, mais des **copies qui ont
divergé** :

- `stories/` (deux puces) affirmait que le geste n'était pas livré, pendant que le code le livrait ;
- `docs/fonctionnel/E16US008.md` et `E16US010.md` affirmaient la même chose, chacune de son côté ;
- `ADR-0050`, qui **porte** la frontière de rôles, nommait `autoriser_forfait_duel` — un symbole
  que le diff venait de supprimer.

C'est le mode de panne que le dépôt nomme déjà trois fois dans son propre registre de dette
(`DETTE-091`, `DETTE-094`, `DETTE-095`) : *une liste tenue à la main éteint la détection sur ce
qu'elle omet*. Il n'avait jamais été appliqué à la documentation.

### Ce que le dépôt savait déjà, et n'a pas su lire

Deux constats rendent cet ADR moins ambitieux qu'il n'en a l'air — l'outillage est **déjà là** :

1. **`E00US027` avait écrit le trou**, en dernière ligne de ses Notes : *« Limite connue et non
   fermée : rien ne vérifie qu'un renvoi `cf. ADR-00xx` pointe un ADR qui existe et dit bien
   cela. »*
2. **L'atlas vérifie déjà les symboles des ADR.** Le contrôle `portage-symbole-absent` existe
   (`backend/atlas/controles.py`), il fonctionne, et il rend **22 constats aujourd'hui** — dont
   `ADR-0004` qui annonce `Protocol` dans `backend/domain/tableau.py`, `ADR-0062` qui annonce
   `elimination_directe` dans `backend/domain/politiques.py`. Il est en sévérité **`SIGNAL`**, noyé
   dans un lot de 45 que **personne ne lit**, et il n'arrête rien.

⚠️ **Le défaut d'`ADR-0050` relevé en revue était donc détectable mécaniquement, et détecté.** Ce
qui a manqué n'est pas l'outil : c'est qu'un signal sans conséquence n'est pas un garde-fou.

## Décision

### §1 — Un fait, un lieu ; les autres pointent

Chaque type de document a **une** responsabilité et n'énonce en propre que ce qui relève d'elle. Ce
qui vient d'ailleurs se cite en **une ligne, avec un lien**, jamais recopié.

| Document | Ce qu'il énonce **en propre** | Ce qu'il ne fait que **pointer** |
|---|---|---|
| `stories/` | le **CA** et les **arbitrages** — c'est l'oracle des tests (règle 9) | le raisonnement (ADR), le geste (fiche fonctionnelle) |
| `docs/adr/` | le **pourquoi** — seul lieu du raisonnement long | le CA, l'état d'avancement |
| `docs/fonctionnel/` | le **geste utilisateur d'aujourd'hui**, en français non technique | le pourquoi, l'absence (cf. §2) |
| `docs/dette.md` | le **raccourci assumé** et son critère de fin | la décision qui l'a causé |
| `journal-d-avancement/<daté>` | le **récit** de l'US au commanditaire — seul lieu du récit | tout le reste |
| `journal-d-avancement/SUIVI-US.md` | l'**état** de chaque US et la prochaine à prendre | le récit (fichier daté), le pourquoi (ADR) |

C'est la règle 13 appliquée à la documentation, avec la même justification : un document qui recopie
est un document qui divergera.

### §2 — Une fiche fonctionnelle décrit le présent, jamais une absence durable

Une fiche de `docs/fonctionnel/` est un **scénario de recette** : elle dit ce qu'on teste
aujourd'hui. Une phrase du type « ce n'est pas livré », « réservé au scoreur », « en attente d'un
arbitrage » est de l'information de **backlog** : elle appartient à `stories/`.

⚠️ **C'est la source de pourrissement n° 1 mesurée sur `E16US007`** : deux fiches sur trois
disaient le faux, et un testeur les déroulant aurait remonté un défaut sur une fonctionnalité qui
marche. Une phrase à date de péremption, posée dans un document que personne ne relit, se périmera
toujours.

Une fiche peut **borner** son périmètre (« ce que ce scénario ne couvre pas ») : ce qu'elle ne peut
pas faire, c'est décrire l'état du **produit** ailleurs qu'elle.

### §3 — Ce qui se vérifie mécaniquement n'est pas laissé à la vigilance

La doctrine du projet — *ce qu'une machine prouve ne se relit pas* — vaut aussi pour sa
documentation. Concrètement, et par ordre de coût croissant :

1. **`portage-symbole-absent` passe de `SIGNAL` à `BLOQUANT`** une fois les 22 constats existants
   soldés. Un ADR qui nomme un symbole disparu fait alors **rougir la CI**, au lieu d'attendre
   qu'un relecteur le remarque — ce qui a échoué quatre fois (`0017`, `0028`, `0049`, `0050`).
2. **Une US ✅ qui a touché `frontend/src/` doit avoir sa fiche** `docs/fonctionnel/<US>.md` : le
   garde-fou de la règle 9-doc cesse d'être un réflexe de revue.
3. **Les chiffres repères ne sont plus saisis à la main** : l'atlas compte déjà les US livrées — il
   l'a prouvé ce 30/08 en attrapant un compteur d'épic périmé.

⚠️ **Un contrôle en `SIGNAL` n'est pas un garde-fou.** C'est le constat central de cet ADR : le
dépôt avait l'outil, la mesure et le constat, et le défaut est passé quand même.

### §4 — Le doublon `00-resume-projet.md` ↔ `SUIVI-US.md` est soldé, pas discipliné

`CLAUDE.md` reconnaît lui-même ce doublon — *« le doublon est lui-même une source de dérive : les
deux fichiers se réconcilient dans le même commit »* — et lui oppose une **discipline**. Une
discipline n'est pas un mécanisme : elle a tenu jusqu'ici parce qu'un humain y pense, et elle
cédera. Les chiffres du résumé sont **dérivés** (§3.3) ou retirés au profit d'un lien.

## Conséquences

- **Rien n'est supprimé de ce qui porte.** Les documents qui ont *tenu* dans la revue d'`E16US007`
  sont ceux à responsabilité unique : l'ADR (section vérifiée ligne à ligne, aucune sur-promesse),
  le registre de dette, le CA. La cible est la **duplication**, pas la documentation.
- **Le coût est concentré sur une dette de rattrapage** : 22 ADR annoncent aujourd'hui des symboles
  absents. Tant qu'ils ne sont pas soldés, `portage-symbole-absent` ne peut pas passer bloquant —
  c'est le patron du **cliquet** déjà employé par `E00US027` (on ne relève pas le seuil, on fait
  descendre le chiffre).
- ⚠️ **Un risque de cet ADR, à ne pas se cacher** : « un fait, un lieu » rend chaque document plus
  court mais **moins autonome**. Un lecteur qui arrive par la fiche fonctionnelle devra suivre un
  lien pour comprendre le pourquoi. C'est le prix, et c'est le même que celui d'ADR-0099 pour le
  code — accepté là, il l'est ici.
- ⚠️ **Cet ADR ne réduira pas le nombre de documents touchés par une US** : `E16US007` en toucherait
  toujours une dizaine. Il réduit le nombre de documents qui **répètent la même chose**, donc le
  nombre de copies capables de diverger. C'est la bonne cible, mais ce n'est pas la même que celle
  qu'on croit viser en disant « il y a trop de documentation ».

## Porté dans le code par

⚠️ **Rien à ce jour, et c'est écrit exprès.**

La décision est **acceptée** ; sa réalisation ne l'est pas encore. Nommer ici un module « qui
portera » la décision serait reproduire exactement le défaut d'`ADR-0017` — un ADR qui déclare porté
ce que personne ne porte —, et ce serait le reproduire dans l'ADR **dont c'est le sujet**.

⚠️ **Le dépôt n'a pas de statut « Proposé »** : l'atlas n'accepte que *Accepté* ou *Remplacé par*
(constaté à l'écriture de cet ADR, qui a été refusé sous ce statut). La distinction « décidé » vs
« réalisé » se porte donc **ici**, dans cette section — c'est précisément ce à quoi elle sert.

Cette section se remplira, module par module, à la livraison de :

| US | Ce qu'elle portera |
|---|---|
| `E00US028` | §3.1 — le contrôle d'atlas passé bloquant, et les 22 constats soldés |
| `E00US029` | §2 — la règle des fiches fonctionnelles et son garde-fou |
| `E00US030` | §1 et §4 — la charte des documents, et le doublon résorbé |

Cette section se remplit à mesure ; si l'une des trois US est abandonnée, l'ADR est **amendé pour
dire ce qui n'est pas tenu**, plutôt que de le laisser croire. C'est la seule discipline qui
distingue un ADR d'une intention.
