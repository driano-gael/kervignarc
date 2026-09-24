# ADR-0113 — Un arbitrage de maquette se lit par l'intention, jamais par la lettre

- **Statut** : Accepté
- **Date** : 2026-09-24
- **US** : E17US008
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)
  — sa **réserve 2** (« un arbitrage explicite du commanditaire l'emporte sur la planche ») supposait
  qu'un arbitrage soit **identifiable** sur la planche. Il ne l'est plus : cet ADR dit comment le lire,
  et quoi faire quand on ne le peut pas.

## Contexte

[ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) rend les
planches **opposables** et pose que l'arbitrage du commanditaire l'emporte sur elles. La procédure
de mesure qui en découle, écrite dans [`EPIC-17`](../../epics/EPIC-17-fidelite-aux-maquettes.md),
tient en trois maillons : **questionnaire → variante retenue → écran livré**.

Le relevé de l'axe saisie a montré que **le maillon du milieu ne tient plus**.

Les 36 questionnaires ont été remplis le **04/08/2026** sur les maquettes **en vignettes**. Les
planches ont été **redessinées le 05/08/2026** en écrans pleins — c'est ce qui a rendu possible de
juger une mise en page plutôt qu'un composant, et c'était nécessaire. Mais les **variantes ont
changé de nombre, de contenu et de lettre**, sans que les questionnaires bougent.

Mesuré sur l'axe saisie : **7 planches sur 9** sont touchées.

- `S01` — le commanditaire coche « **B** — le code court domine » ; la planche intitule sa variante
  **B** « Scan du QR ». La lettre désigne **l'inverse** de ce qu'il a voulu, et son « pourquoi »
  (« pas sûr que les caméras soient toujours accessibles ») le prouve.
- `S04` — les trois options jugées (« lien discret », « sélecteur permanent », « confirmation à la
  validation ») **n'existent plus** sur la planche.
- `S08` — le questionnaire départage une **densité d'affichage** (« totaux par volée » contre
  « détail flèche à flèche ») ; la planche départage **où le scoreur se tient** (« à la cible »
  contre « à distance »). Ce ne sont pas deux réponses à la même question.
- `S05` — le commanditaire coche « **Aucun** — à refaire » sur trois variantes qui ont disparu.

Le phénomène n'était pas inconnu : `maquettes/README.md` le signalait pour **une** planche (« le
questionnaire d'A02 posait encore les questions de la v2 »). Ce qui est neuf, c'est son **ampleur**
et le fait qu'il rende une procédure inapplicable.

⚠️ **Le danger n'est pas l'erreur, c'est la fausse certitude.** Une lettre se cite sans effort et se
lit comme une preuve. `EspacePoste.tsx` en portait une — « retour maquettes (S01), **variante B** » —
posée de bonne foi, exacte quant au choix réel, **fausse quant à sa référence**. Un relecteur qui
serait allé vérifier sur la planche aurait conclu que le produit implémentait le QR.

## Décision

**1. Sur le corpus de maquettes, un arbitrage du commanditaire se lit par son *intention* — le
libellé coché et le « pourquoi » écrit — et jamais par la *lettre* de la variante.** La lettre n'est
pas une référence stable : elle ne vaut que pour la version de la planche affichée le jour du
questionnaire.

**2. Un relevé d'écarts écrit sa table de correspondance.** Quand il mesure un écran contre une
variante retenue, il dit **explicitement** quelle variante de la planche d'aujourd'hui porte
l'intention cochée hier, et à quel titre. Une traduction non écrite est une interprétation qui se
transmettra comme un fait.

**3. Quand l'intention ne se traduit plus, il n'y a pas d'étalon — et alors on ne résorbe rien.**
C'est le point qui coûte : l'absence d'étalon est un **motif d'exclusion**, pas une invitation à
choisir la variante la plus proche. S'aligner sur une planche que le commanditaire n'a pas jugée,
c'est livrer un parti pris qu'il n'a pas retenu — exactement ce qu'ADR-0074 voulait empêcher. Le
seul geste qui rouvre le dossier est de **reposer la question** (tour 2 du questionnaire), et c'est
du temps du commanditaire : cela se **demande**, cela ne se contourne pas.

**4. Aucune lettre de questionnaire ne se cite dans le code.** Un commentaire cite le **libellé** et
le **« pourquoi »**, qui sont stables, jamais « variante B ».

## Conséquences

- La procédure d'`EPIC-17` gagne un préalable : **vérifier la correspondance avant de mesurer**.
  `E17US009` (7 planches publiques `P**`) doit s'y attendre — le redessin du 05/08 a porté sur les
  36 planches, pas sur les 9 de la saisie.
- Trois planches de saisie — `S04`, `S05`, `S08` — sont **hors résorption** jusqu'au tour 2. Le
  besoin est porté au tracker comme une demande au commanditaire, pas comme une US.
- ⚠️ **Cet ADR ne rend pas les questionnaires caducs.** Leurs **réponses aux questions ciblées**
  (« le cumul en permanence », « les autres archers doivent pouvoir relire », « oui, par admin et
  scoreur ») ne dépendent d'aucune variante : elles restent opposables telles quelles, et c'est
  d'ailleurs l'une d'elles qui a fait corriger le cumul dans `E17US008`.
- ⚠️ **Rien de ceci n'est mécanisable.** La correspondance est un jugement ; aucun test ne peut
  dire qu'une intention de 2026 désigne telle variante d'aujourd'hui. La garantie est **procédurale**
  — le relevé écrit sa table, la revue la lit. C'est la limite honnête de cette décision, et la
  raison pour laquelle le point 3 est formulé comme une **interdiction** plutôt qu'une précaution :
  une règle non vérifiable ne tient que si elle est simple à dire.

## Porté dans le code par

- [`epics/EPIC-17-fidelite-aux-maquettes.md`](../../epics/EPIC-17-fidelite-aux-maquettes.md) —
  section « Le maillon du milieu a bougé » : la **table de correspondance** des 9 planches de saisie
  (point 2), et le tableau « Hors périmètre de résorption » qui applique le point 3.
- [`stories/E17-fidelite-aux-maquettes.md`](../../stories/E17-fidelite-aux-maquettes.md) — notes de
  livraison d'`E17US008` (arbitrages reversés) et CA d'`E17US011`.
- `frontend/src/features/poste/EspacePoste.tsx` — commentaire de `FormulaireRattachement` : porte
  l'application du point 4, avec l'avertissement de ne pas citer de lettre.
- [`maquettes/README.md`](../../maquettes/README.md) — avertissement de reprise, pour que la
  prochaine session ne redécouvre pas le décalage en le mesurant.
