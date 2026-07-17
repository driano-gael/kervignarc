# ADR-0021 — Maille des US au grain « capacité », pas « comportement testable »

- **Statut** : Accepté
- **Date** : 2026-07-17
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/README.md`](../../stories/README.md) (définition de la maille en tête ;
  tables de séquence renumérotées) ; les 11 fichiers `stories/Exx-*.md` du backlog non livré
  (regroupement + table de correspondance en pied de chacun).
- **Introduit par** : refactor de maille du 17/07/2026 (branche `docs/refactor-maille-us`).

## Contexte et problème

Le backlog découpait les EPICs en US à la maille **« un comportement testable »** (ancienne ligne 3
du README). Appliquée strictement, cette maille a produit des US **tranchées par étape technique**
plutôt que par valeur : E04 comptait 18 US dont `saisir` / `valider` / `enregistrer` / `verrouiller`
/ `cumuler` / `diffuser` — six tranches d'un seul geste métier (« saisir une volée de qualif »).
Prises isolément, plusieurs ne sont ni indépendantes ni livrables (violation du *I* et du *V*
d'INVEST), et le backlog gonfle : 137 US actives, dont beaucoup ne portent pas de valeur autonome.

Le coût est réel : une branche + un PR + une passe de `/revue-us` + une fiche fonctionnelle **par
fragment technique**, là où la capacité se conçoit, se teste et se revoit d'un bloc.

## Options

1. **Garder la maille « comportement testable »** — écarté : c'est elle qui fragmente ; le nombre
   d'US et la cérémonie par US ne baissent pas.
2. **Maille « module » (÷4, un epic ≈ une poignée d'US)** — écarté : au grain le plus gros, l'US
   déborde ce qu'une branche revue en une passe peut tenir (la revue dégrade avec la taille du diff),
   et il faudrait désolidariser « unité de spec » et « unité de livraison » — un changement de
   workflow (« une branche par US ») que ce projet ne veut pas payer maintenant.
3. **Maille « capacité » (÷~1,5, retenu)** — une US = une **capacité cohérente, livrable et
   testable d'un bloc**, plus grosse qu'un comportement, plus petite qu'un module ; elle **tient
   encore dans une branche revue en une passe**, donc **« une branche par US » est préservé, sans
   ADR de workflow**.

## Décision

- **Grain « capacité ».** Une US regroupe les comportements d'une même surface métier livrés
  ensemble. Les frontières de **jalon** (J0→J4) ne se franchissent jamais : deux US de jalons
  différents ne fusionnent pas (sinon on ne livre plus par jalon de valeur).
- **Patron de regroupement.** L'US survivante **garde l'ID le plus bas** du groupe ; chaque US
  absorbée devient une **puce de critère d'acceptation** étiquetée `**CA — <aspect> (ex-USxxx)**` —
  aucun comportement n'est perdu (règle 9 : le CA reste l'oracle de test). La survivante porte une
  ligne `**Absorbe** : …` et une table `## Correspondance ancien → nouveau` clôt le fichier d'epic.
- **Le livré est gelé.** Une US **déjà livrée** (code + tests dérivés du CA + `docs/fonctionnel/`)
  n'est **pas** re-tranchée : la fusionner orphelinerait ses tests et sa fiche. Seul le **backlog non
  livré** est regroupé. Idem pour une US **caduque** (E10US004), conservée telle quelle.
- **Redirection des liens dans le même commit.** Tout regroupement laisse des liens pendants (une
  dépendance ou une prose visant un ID absorbé). Ils sont **tous** redirigés vers la survivante —
  dans les stories, `docs/`, les ADR, le CDC et les commentaires de code — sauf les tables de
  correspondance et les lignes `Absorbe`, qui **conservent volontairement** les anciens IDs.
- **Ce qui n'est pas fusionné.** Une US **ancrée par un ADR** (ex. E04US015 / ADR-0016) ou porteuse
  d'un **arbitrage métier distinct** reste séparée : l'ADR référence une décision, pas une étape.

## Conséquences

- **+** Backlog **137 → 91** US actives ; une capacité se conçoit et se revoit d'un bloc ; moins de
  cérémonie par fragment.
- **+** **Workflow inchangé** : « une branche par US » tient, la revue reste d'une passe.
- **−** **Double registre du mapping ancien→nouveau** : les puces `ex-USxxx` (dans le corps) *et* la
  table de correspondance (en pied) disent la même chose et **peuvent diverger** avec le temps ;
  rien n'empêchera une US future de citer `E04US007` (que la mémoire retient comme « la validation »)
  au lieu d'`E04US002`. **Choix assumé : pas de garde-fou mécanique** (un check CI « aucun ID absorbé
  hors table de correspondance » est **sur-dimensionné pour de la doc de backlog** — règle 12, la
  rigueur va au moteur, pas à l'outillage). La table de correspondance **est** le point de vérité ;
  on l'y renvoie en cas de doute. À réévaluer seulement si la divergence se constate dans les faits.
- **−** Le ÷~1,5 n'est **pas** uniforme : plein sur les epics *greenfield* (E03–E07, E09, E11, E12),
  quasi nul sur les epics déjà livrés (E00/E01/E02/E08/E10), où geler le livré ne laisse presque rien
  à regrouper. C'est mécanique, pas un oubli.
- **−** Une **incohérence latente** touchée par le refactor mais **non tranchée** (jalon/dépendance
  d'E04US015 vs « abandon en qualification ») est **remontée comme arbitrage métier**, pas résolue en
  douce — conforme à la règle 9 (ne pas deviner un arbitrage).

## Liens

[ADR-0013](0013-conduite-de-la-revue-d-us.md) (conduite de la revue — même famille : une décision de
*process/convention* ancrée en ADR) ; [ADR-0016](0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)
(exemple d'US non fusionnée car ancrée ADR — E04US015) ; [`stories/README.md`](../../stories/README.md)
(définition de la maille et index).
