# ADR-0073 — « Pas de tir » = groupement de cibles, « couloir de tir » = place d'un archer

- **Statut** : accepté
- **Date** : 05/08/2026
- **US** : E16US001 — Plan de salle : se mettre d'accord sur ce qu'est un pas de tir
- **Amende** : [ADR-0006](0006-ubiquitous-language.md) (langage ubiquitaire) — le terme métier de la
  place d'un archer n'est plus « position », et la **cohérence obligatoire** code ↔ API ↔ UI ↔ doc
  qu'il pose est **délibérément suspendue** le temps du renommage (DETTE-042)
- **Prolonge** : [ADR-0064](0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) (ce qu'est un
  **poste** : une tablette ou un écran), [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md)
  (plan de cibles matérialisé)

## Contexte

L'écran de plan de salle (maquette A10) a été **refusé** à la relecture du 04/08/2026. Le refus ne
portait ni sur l'ergonomie ni sur la fonction, mais sur **un mot**. Le commanditaire écrit :

> « Je ne comprends pas l'usage. Pour moi un **pas de tir**, c'est le **couloir de tir d'un archer**
> et, suivant le nombre de blasons et le nombre d'archers que je positionne sur la cible, exemple
> 4 archers 2 blasons → A, B, C, D. Explique-moi ce que toi tu vois avant de valider l'écran. »

Trois usages cohabitaient dans le dépôt, sans qu'aucun document ne tranche :

1. **« pas de tir »** = une rangée de cibles, dans les maquettes (A10, S01, S07, A13) et dans
   l'ordre de service des affectations (`api/v1/routage.py`) ;
2. **« pas de tir »** = le couloir d'un archer, dans la bouche du commanditaire ;
3. **« poste »** = *à la fois* la place d'un archer sur une cible (maquette A10 : « nombre de postes
   par cible ») **et** la tablette ou l'écran rattaché à un lieu (ADR-0064, code livré).

Le troisième point est la collision réelle : un mot pour deux choses, dans l'application livrée. Le
`docs/glossaire.md` ne portait **aucune** entrée « pas de tir » — c'est ce trou qui a laissé les
sens dériver jusqu'au refus.

Deux questions du même questionnaire étaient restées sans réponse et **conditionnaient le modèle** :
la salle a-t-elle une disposition particulière (cibles décalées, piliers, deux pas de tir) ; le
gabarit doit-il porter autre chose que les cibles (table d'organisation, échauffement, entrée du
public).

## Options

1. **« Pas de tir » = la place d'un archer** (lecture du commanditaire prise au pied de la lettre),
   la rangée devenant « rangée » ou « départ ». *Écartée* : « départ » est déjà pris (ADR-0017, un
   créneau du tournoi), et le mot « pas de tir » au sens rangée est déjà employé par cinq maquettes
   et par l'ordre de service — on déplacerait la collision au lieu de la fermer.
2. **On bannit le mot** des deux côtés (« rangée de cibles » / « position sur la cible »).
   *Écartée* : sûr contre la rechute, mais s'éloigne du vocabulaire parlé du club, alors que
   l'objectif est précisément que l'organisateur **reconnaisse sa salle** dans l'écran.
3. **Retenue** — voir ci-dessous.
4. **Renommer `position` → `couloir` immédiatement**, partout. *Écartée pour cette US* : traverse le
   domaine, l'ORM, une migration Alembic, cinq modules d'API et le front, pour un gain **nul** côté
   utilisateur (ce qu'il lit est corrigé par ailleurs) ; son diff mécanique noierait celui du
   vocabulaire d'écran et rendrait la revue inopérante. Différée en **DETTE-042**.

## Décision

**Trois termes, opposables partout — écrans, PDF, messages d'API, maquettes, glossaire :**

| Terme | Désigne | Ne désigne jamais |
|---|---|---|
| **pas de tir** | un **groupement de cibles** : la rangée tirée depuis la même ligne de tir | la place d'un archer |
| **couloir de tir** | la place d'**un archer** devant sa cible, repérée par une lettre (A, B, C, D…) | une rangée, une tablette |
| **poste** | une **tablette** ou un **écran** rattaché à un lieu (ADR-0064) | la place d'un archer |

« Pas de tir » reste une notion **de salle** : aucune entité ne la porte, elle ne sert qu'à se
repérer à l'écran.

**Le gabarit de salle reste une *liste*, pas un plan.** La salle du club rentre dans une grille
régulière : un gabarit est « N cibles, chacune avec son plafond de couloirs ». Ni coordonnées, ni
obstacles, ni éléments non-cibles (table d'organisation, échauffement, entrée du public). La
variante « plan libre » de la maquette A10 est **écartée**.

**Le plafond reste un majorant.** Le nombre de couloirs réglé sur une cible est un **maximum** : le
placement en installe au plus autant, et souvent moins (un blason encombrant occupe la face
entière). Les libellés disent donc « **jusqu'à** N couloirs de tir », jamais « N couloirs ».

## Conséquences

- **ADR-0006 est amendé** : son « `lettre`/`idCible` → `position`/`cible` » et sa « cohérence
  obligatoire du terme entre domaine, API, UI et documentation » ne valent plus pour ce terme. La
  cohérence est **rompue sciemment et temporairement**, le temps du renommage — c'est l'objet de
  **DETTE-042**, cotée *majeur* et rattachée à `E01US019`.
- Les surfaces **lues par l'utilisateur** sont alignées dans l'US : écrans, aide contextuelle, les
  deux **PDF** (feuille de marque, liste de placement), les messages d'erreur d'API, l'alerte de
  routage, la maquette A10, la planche wireframe correspondante, le glossaire.
- **Reliquat déclaré** : les maquettes `a11`, `p02`, `p04`, `s06`, `a09` et plusieurs fiches de
  `docs/fonctionnel/` emploient encore « position » en prose. Porteurs vérifiés : `a11` → E16US005, `p02` → E16US004,
  `s06` → E16US011, `a09` → E16US010/E16US011 — leurs stories portent la consigne de balayage.
  **`p04` n'a aucune US porteuse** : le reliquat y reste sans échéance, et c'est dit plutôt que tu —
  ne pas confondre ce périmètre avec une exhaustivité atteinte.
- **Toute US ultérieure qui voudrait de la géométrie** (coordonnées de cibles, obstacles, repères
  d'orientation sur le plan public — cf. la question ouverte de la maquette P04) **rouvre cet ADR**
  par un ADR nouveau : elle ne l'hérite pas. Le modèle actuel ne peut pas stocker cette information.
- Le glossaire fait foi au quotidien ; cet ADR dit **pourquoi** il dit ce qu'il dit.

## Sources

Questionnaire A10 du 04/08/2026 (`maquettes/questionnaires/a10-plan-de-salle.md`), arbitrage du
05/08/2026, `stories/E16-retours-maquettes.md` (E16US001), `docs/glossaire.md`, `docs/dette.md`
(DETTE-010, DETTE-042).
