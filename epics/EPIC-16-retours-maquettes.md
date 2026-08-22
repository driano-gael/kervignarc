# EPIC-16 — Retours du questionnaire de maquettes (04/08/2026)

- **ID** : EPIC-16
- **Statut** : En cours *(premier lot front livré ; le reste est à prendre US par US)*
- **Priorité** : MVP *(retours du commanditaire sur les 36 planches de maquettes)*
- **Dépend de** : EPIC-14 (ossature admin), EPIC-07 (affichage public & écran de salle), EPIC-05
  (moteur de phases), EPIC-03 (placement)
- **Réfs** : [`maquettes/questionnaires/`](../maquettes/questionnaires/) — 36 questionnaires remplis
  le 04/08/2026 ; [`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) ;
  [`cahier-des-charges-design.md`](../cahier-des-charges-design.md)

## Objectif / valeur

Le commanditaire a **passé en revue les 36 planches** du dossier de maquettes et rempli un
questionnaire par écran : parti pris retenu, verdict, critiques, évolutions souhaitées, réponses aux
questions ciblées et corrections de vocabulaire. C'est le retour le plus large reçu depuis le début
du projet, et il porte sur **toutes les surfaces à la fois** — admin, public, écran de salle, poste
de cible, scoreur.

Quatre écrans avaient été **refusés en l'état** (🔴 « à refaire ») ; **il n'en reste aucun** : ~~`A07` phases~~ (**levé le 22/08/2026 par E16US002**, [ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md) — titre de phase, fiche dépliable par ligne, et les deux destinations de composition renommées, chacune portant jusque-là le mot de l'autre), ~~`A10` plan de salle~~ (**levé le 05/08/2026 par E16US001**, ADR-0073 — le refus ne portait que sur le vocabulaire), ~~`A14`
complétude~~ (**levé le 07/08/2026 par E16US003** — le refus portait sur le **mélange à l'écran** : le sportif est resté au pilotage sous « Prêt à terminer ? », l'administratif est parti sur l'axe gestion) — plus ~~`P03` classements publics~~ (**levé le 08/08/2026 par E16US004**, ADR-0079). ⚠️ **Cette phrase annonçait « il en reste deux » alors que `P03` était levé depuis le 08/08** : corrigé le 22/08/2026, en même temps que le dernier refus. Vingt sont validés **avec réserves** (🟡). Le reste est
validé tel quel.

L'objectif de cet épic est de **traiter ces retours jusqu'au bout**, sans en perdre en route : c'est
précisément ce qu'un dossier de 36 questionnaires rend facile à faire.

## Périmètre

### Déjà livré — le lot « front seul » (04/08/2026)

Livré en une passe, hors US numérotée, parce que ces points ne demandaient **aucune décision
métier** ni aucun changement de domaine ou d'API : cinquième porte « écran de salle » et vocabulaire
(A00), sortie de la connexion (A01), largeurs par surface et aération (A02/A11), pilotage en premier
axe + bandeau de contexte tournoi/départ (A02), tri et filtre des tournois (A04), pavé de saisie
appelé + relecture par les autres archers (S02), cases de flèches sur deux hauteurs (S05), pavé de
code sans confondables (S01), pagination de l'écran de salle (P06), tête figée du classement et
règle de départage à la demande (A16/P07), dialogue de confirmation en remplacement des huit
`window.confirm` (A15), bandeaux repliables de supervision et impression des étiquettes/cartes
(A12/A08).

### Inclus (US à prendre)

- **Ce qui exige un arbitrage métier** : le modèle du plan de salle (A10), la gestion des phases
  (A07), le découpage de la complétude (A14).
- **Ce qui exige du domaine ou de l'API** : origine FFTA/local des référentiels, logo du club,
  formats d'export, paiement par club, podiums configurables, forfait déclaré par l'admin,
  agrégat de complétude par tournoi, QR par scoreur, réglage de la durée de page en salle.
- **Ce qui reste du front mais dépasse une passe de mise en forme** : le suivi multi-archers de
  bout en bout côté public, le placement (puits de réserve), la recherche transverse.

### Exclus

- La refonte de l'identité visuelle par tournoi (**E01US016**), qui porte déjà le logo d'événement.
  L'ajout d'un **logo de club** (A05) s'y rattache et est traité ici seulement pour mémoire.
- Toute reprise des planches `maquettes/` elles-mêmes : elles servent ici de support au
  questionnaire. ⚠️ **Amendé le 05/08/2026 par [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)** :
  les planches sont devenues la **référence opposable** de mise en page du front. « Pas de
  spécification vivante » ne vaut plus que **pour cet épic-ci**, qui traite les retours *sur* les
  maquettes ; amener le produit *jusqu'aux* maquettes est le sujet de
  [`EPIC-17`](EPIC-17-fidelite-aux-maquettes.md).

## Capacités

- [x] Lot front seul du 04/08/2026 (cf. ci-dessus).
- [x] Plan de salle : lever le malentendu de modèle (E16US001).
- [ ] Phases : catalogue, gabarits, fiche de réglages (E16US002). ⚠️ **Rétrécie le 08/08/2026** : le
      CA « plusieurs qualifications » en est sorti (→ `E05US024` livrée + `E05US025`), le CA
      « gabarit » est tranché (ADR-0060 §5 confirmé, la brique reste le **format**). Restent liste,
      titre de phase et fiche de réglages.
- [x] Complétude : séparer le déroulé de l'administratif (E16US003).
- [x] Public : suivre plusieurs archers de bout en bout (E16US004).
- [ ] Placement : largeur, une cible par ligne, puits de réserve (E16US005).
- [ ] Patrimoine : origine FFTA/local, logo du club (E16US006).
- [ ] Impressions, exports et podiums paramétrables (E16US007).
- [ ] Feu vert : agir sur la ligne du duel (E16US008).
- [ ] Écran de salle : réglages et défilement (E16US009).
- [ ] Recherche transverse et alerte de complétude en liste (E16US010).
- [ ] Rattrapage : les règles de S06, S08, S09, A09, A02 et P05 (E16US011).
- [ ] Famille « prêt à… » : démarrer / terminer / archiver / exporter (E16US012) — **née d'E16US003**,
      refonte de navigation, ADR probable.

## Critères d'acceptation (epic)

- Chacun des 36 questionnaires a reçu une suite : livrée, programmée en US, ou **explicitement
  écartée avec sa raison**. Aucun retour ne reste sans réponse.
- Les trois écrans 🔴 (A07, A10, A14) et le 🔴 public (P03) ont été retravaillés et re-soumis.

## Risques

- **A10 est un malentendu de vocabulaire, pas un défaut d'écran.** Le commanditaire écrit : *« je ne
  comprends pas l'usage… explique-moi ce que toi tu vois avant de valider l'écran »*. Coder avant de
  s'être mis d'accord sur ce qu'est un « pas de tir » ferait reconstruire deux fois.
- **A07 touche le moteur.** « Plusieurs phases de même type avec des réglages différents » suppose
  que la phase devienne un objet configurable à part entière, ce qui recoupe le catalogue de types
  d'[ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) — à relire avant de cadrer.
- **Le questionnaire mêle des demandes de niveaux très différents** (une couleur, un modèle de
  données). Le tri fait ici peut se révéler faux sur un ou deux points : le relire au cadrage de
  chaque US plutôt que de le tenir pour acquis.
