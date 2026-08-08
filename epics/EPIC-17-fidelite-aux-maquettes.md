# EPIC-17 — Fidélité de l'application aux maquettes

- **ID** : EPIC-17
- **Statut** : En cours *(la charte est posée ; la confrontation écran par écran reste à faire)*
- **Priorité** : MVP *(l'application est montrée au club ; elle ne ressemble pas à ce qui a été validé)*
- **Dépend de** : EPIC-14 (ossature admin à trois axes), EPIC-16 (retours du questionnaire)
- **Réfs** : [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) ·
  [`maquettes/`](../maquettes/) · [`cahier-des-charges-design.md`](../cahier-des-charges-design.md) §3.3

## Objectif / valeur

**Distinguer cet épic d'[EPIC-16](EPIC-16-retours-maquettes.md) : celui-ci traite les retours *sur*
les maquettes, celui-là amène le *produit* jusqu'aux maquettes.** Les deux sont nés du même dossier
et se lisent facilement l'un pour l'autre — ce sont pourtant deux directions opposées.

Le dossier de maquettes le disait déjà, sans que personne n'en fasse une suite :

> *« "Écran existant" ne veut pas dire "conforme". La mention signale qu'un composant du même rôle
> vit dans `frontend/src/features/` — elle ne dit rien de la ressemblance entre l'écran livré et la
> maquette. **Confronter les deux reste à faire.** »*
> — [`maquettes/README.md`](../maquettes/README.md)

La confrontation a été faite le 05/08/2026 et l'écart de départ était **total** : le front tournait
encore sur le socle du walking skeleton — accent violet `#aa3bff`, fond blanc, `system-ui` — parce
que les « US design » annoncées en tête d'`index.css` n'avaient jamais été écrites. Aucune des 98 US
livrées n'avait de raison de s'en apercevoir : chacune était conforme à *son* CA.

## Périmètre

### Inclus

- **La charte, posée une fois pour toutes** : jetons, thème de référence, typographie (E17US001).
- **La confrontation planche par planche** des 36 écrans, et la correction des écarts de mise en
  page et de hiérarchie de l'information.
- **Le maintien de la correspondance** : `maquettes/assets/appareils.js` se désynchronise d'`axes.ts`
  à chaque US qui renomme une destination — la resynchronisation fait partie de l'épic.

> ⚠️ **Méthode — lire le questionnaire avant la planche.** Une planche montre **plusieurs partis
> pris** ; c'est le questionnaire qui dit lequel a été **retenu**, et la réponse est parfois
> « **telles que livrées** » — c'est-à-dire le front lui-même. Cas vérifié sur **A00** : le
> commanditaire a coché « A — Les quatre portes telles que livrées » et « ✅ Validé tel quel », alors
> que la planche propose à côté une liste verticale à URL affichées. S'aligner sur la première
> variante venue aurait **défait un écran validé**. L'ordre est donc : questionnaire → variante
> retenue → comparaison → alignement. *(Ajouté le 06/08/2026 : la première rédaction de cet épic
> disait « confronter les planches », sans cette précaution.)*

### Exclus

- **La palette elle-même ne se discute pas ici** : elle vient de la charte mesurée, où chaque valeur
  porte son ratio de contraste. La contester est légitime, mais en ADR, pas en US d'écran
  (`cahier-des-charges-design.md` §3.3).
- **L'identité visuelle *par tournoi*** (`E01US016`), qui surcharge ces jetons pour le public et
  l'écran de salle seulement (`D-27`).
- *(Levé)* Les écrans de l'Atelier étaient exclus tant que **DETTE-023** tenait — ils portaient encore
  un identifiant de tournoi côté serveur, donc l'écran maquetté ne pouvait pas exister. La dette est
  **résorbée depuis le 31/07/2026** (E01US023, [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)) :
  les six destinations de l'atelier s'ouvrent sans tournoi. Ils rentrent donc dans le périmètre.
  *(`maquettes/README.md` portait encore l'avertissement inverse au 05/08 ; corrigé dans le même
  commit — c'est exactement le genre de note qui survit à sa cause et fait renoncer à un écran
  faisable.)*

## Capacités

> **Chaque capacité nomme l'US qui la porte.** *(Instituée le 08/08/2026 : six capacités sur onze
> n'en avaient aucune, et comme les cinq restantes étaient cochées, l'épic se lisait comme
> **terminé**. Une capacité sans US n'est pas planifiée — elle ne se fera qu'à la faveur d'un autre
> travail, ou pas du tout.)*

- [x] Poser la charte du club dans l'application (`E17US001`).
- [x] Aligner le catalogue de composants sur les formes des planches (`E17US002`).
- [x] Relever les écarts des 19 planches admin (`A01`→`A19`, ci-dessous).
- [x] A01 connexion + A02 accueil des axes (`E17US003`).
- [x] A13 supervision — la grille de tuiles (`E17US004`).
- [ ] Embarquer **Inter** pour le jour J, sans réseau (`DV-07`) — `E17US005`.
      ⛔ **Arbitrage d'actif en attente (règle 11)** : l'US est spécifiée, **pas prenable**.
- [ ] Trancher la **couleur d'une action destructrice** — trou de la charte (`DV-03` exclut le rouge,
      rien n'est prévu pour ce cas) : aujourd'hui contour ambre — `E17US006`.
      ⛔ **Arbitrage en attente** : ADR attendu, l'US est spécifiée, **pas prenable**.
- [ ] **Résorber** les écarts relevés sur les planches `A**` (admin) — `E17US007`.
      *(Le relevé est **fait** ; ce qui manquait était l'US qui le solde. Un relevé sans US de
      résorption se périme sur place.)*
- [ ] Confronter les 9 planches `S**` (saisie & scoreur) et résorber — `E17US008`.
- [ ] Confronter les 7 planches `P**` (public & écran de salle) et résorber — `E17US009`.
- [ ] Resynchroniser `maquettes/assets/appareils.js` sur `axes.ts`, **et rendre la dérive détectable
      mécaniquement** — `E17US010`. *(À prendre **avant** `E17US008`/`E17US009` : elles relisent
      16 planches, autant qu'elles décrivent l'application d'aujourd'hui.)*

> **Compte des planches** : **36** — 1 porte d'entrée (`a00`) + 19 admin (`a01`→`a19`) + 9 saisie
> (`s01`→`s09`) + 7 public (`p01`→`p07`). La formulation « les 19 `A**`, 9 `S**`, 7 `P**` » de la
> version précédente en **oubliait `a00`** et ne couvrait donc que 35 planches — corrigé le
> 08/08/2026 en comptant le dossier plutôt qu'en recopiant un chiffre. `a00` **est confrontée** :
> elle figure au relevé admin ci-dessous, verdict **conforme**.

## Relevé d'écarts — les 19 planches admin (06/08/2026)

Méthode appliquée : **questionnaire → variante retenue → écran livré**. Les écarts ci-dessous sont
mesurés contre la **variante retenue**, jamais contre la première proposition d'une planche. Sources
vérifiées : questionnaires du 04/08, balisage des planches, code des features, et rendu réel au
navigateur pour les écrans atteignables sans jeu de données.

**Hors périmètre d'E17, et pourquoi :**

| Planche | Motif |
|---|---|
| A07 · phases | 🔴 **« à refaire »**, aucune variante retenue — il n'y a rien à quoi s'aligner. `E16US002`. |
| A14 · complétude | **Tranchée le 07/08/2026 par `E16US003`** : l'**écran livré fait foi**, pas la planche. `maquettes/a14-completude.html` a été redessinée le 05/08 **après** le questionnaire et **sans** tour 2 de validation ; elle range les impayés dans une liste « À voir » à côté des contrôles sportifs — donc elle **re-mélange** ce que le commanditaire a refusé. Écartée au titre de la **réserve 2 d'[ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)** (« un arbitrage explicite du commanditaire l'emporte sur la planche »). Ce n'est **pas** un écart de fidélité à résorber ; sa proposition reste une piste pour `E16US008` (feu vert). |
| A10 · plan de salle | 🔴 levé par `E16US001` (le refus portait sur le vocabulaire). |
| A05 · identité | L'écran **n'existe pas** : `E01US016` est ⬜. Ce n'est pas un écart de fidélité, c'est une US non livrée. |
| A00 · portes, A03 · accueil-statuts, A19 · écran de salle | **Conformes.** A03 adapte bien son contenu au statut (`FriseCycleDeVie`) ; A19 porte emplacement, cadence, QR et pilotage. |

### 🔴 Le produit implémente une variante **écartée** — le plus grave

Ces trois écrans ont un parti pris explicitement **non retenu** par le commanditaire. Corriger coûte
une refonte d'écran, mais ne pas corriger, c'est livrer ce qu'il a refusé.

| Planche | Retenu | Livré | Constat |
|---|---|---|---|
| ~~**A13 · supervision** ✅~~ **corrigé** (E17US004) | **B — grille de tuiles** (« 30 d'un œil ») | ~~`<table>` = variante **A**~~ → **grille de tuiles** | Les cibles se lisent désormais en tuiles ; l'IP et la révocation, absentes de la planche, ont été **conservées dans la tuile**. Le tableau des **écrans de salle** reste (A19 est conforme). |
| **A06 · référentiels** 🟡 | **B — panneau latéral d'édition** | édition **en place** = variante **A** | `Blasons.tsx` bascule tout l'écran en formulaire (`if (edition) …`). Le panneau latéral (`.avec-panneau` des planches) n'existe pas dans le front. |
| **A09 · inscriptions** 🟡 | **B — recherche d'abord, liste ensuite** | formulaire puis liste = variante **A** | Ni recherche en tête, ni compteurs d'entrée (« Voir les 156 inscrits », « Non placés · 3 », « Non réglés · 12 », « Doublons · 2 »). |

### 🟠 Les listes du produit ne sont pas des tableaux à colonnes

L'écart le plus **systématique** : les planches présentent les données d'administration en
**carte-tableau à colonnes nommées**, le produit en listes ou en cartes. Cinq écrans n'ont **aucun**
`<table>`.

| Planche | Colonnes attendues | Livré |
|---|---|---|
| **A12 · postes** 🟡 | POSTE · TYPE · RATTACHEMENT · APPAREIL · SIGNE DE VIE · JETON | aucune table ; actions « Régénérer un jeton », « Détacher », « Réactiver » non repérées |
| **A08 · scoreurs** 🟡 | NOM · CODE D'ACCÈS · ÉTAT · PÉRIMÈTRE · DERNIÈRE VALIDATION | aucune table ; l'impression des accès existe |
| **A15 · bascule de tour** 🟡 | DUEL · CIBLE · ARCHER A · ARCHER B · HEURE, + encart « CE QUI SE FIGE / CONSÉQUENCE » | aucune table (recoupe `E16US008`) |
| **A18 · exports** 🟡 | DOCUMENT · FORMAT · POUR QUI · CONTENU, + « Tout télécharger » | aucune table (recoupe `E16US007`) |
| **A11 · placement** 🟡 | panneaux « Non placés — 3 » et « Contraintes actives » | aucune table (recoupe `E16US005`) |
| **A04 · tournois** 🟡 | ÉTAT · NOM · DATE · INSCRITS · CIBLES · AVANCEMENT · CE QUI RESTE | ligne simple + pastille ; **les colonnes de droite supposent des données que l'écran ne va pas chercher** |
| **A17 · paiements** ✅ | ARCHER · CLUB · CAT. · TARIF · DÛ · DEPUIS, + bandeau Attendu / Encaissé / Restant dû / Archers concernés, + « Exporter pour le trésorier » | table présente mais colonnes ARCHER · DÛ · PAYÉ · RESTE · STATUT · ACTION ; **ni bandeau de totaux, ni export trésorier, ni ancienneté** — et l'écran est ✅ |

### 🟡 Écarts de forme, peu coûteux

| Planche | Écart |
|---|---|
| ~~**A01 · connexion** 🟡~~ **corrigé** (E17US003) | La planche retient « **formulaire sobre plein cadre** » ; le produit affichait une carte collée en haut à gauche. Désormais colonne centrée, bandeau de titre, libellés visibles, bouton pleine largeur, échappatoire centrée sous la carte. |
| ~~**A02 · ossature** 🟡~~ **partiellement corrigé** (E17US003) | La question « Que venez-vous faire ? » et la ligne de contexte de l'axe Pilotage sont posées. ⚠️ **Le relevé initial se trompait** sur les compteurs : le front affichait **déjà** « N en cours » (`CoquilleAdmin.tsx`) — je l'avais jugé sur un tournoi en **brouillon**, donc sur un état où le compteur ne s'affiche pas. C'est exactement la limite annoncée plus bas (« les écrans sans jeu de données n'ont pu être vus qu'à l'état vide »). Restent hors périmètre : la pastille d'alerte de complétude (`E16US010`) et « 28/30 postes en ligne » (agrégat absent du serveur). |

### Ce que ce relevé ne dit pas

- Il compare des **structures**, pas des pixels : un écran peut être structurellement conforme et mal
  proportionné, et l'inverse.
- Les écrans sans jeu de données n'ont pu être vus qu'à l'état vide ; les écarts de **densité de
  liste** y sont invisibles.
- Un écart marqué « recoupe `E16Uxxx` » **ne doit pas être traité deux fois** : l'US E16 porte déjà le
  besoin, E17 n'ajoute que l'exigence de ressemblance.

## Critères d'acceptation (epic)

- Un écran livré et sa planche sont **superposables** : mêmes zones, même hiérarchie, mêmes formes,
  aux écarts documentés près. **La densité fait exception** : le commanditaire a demandé en A02 « plus
  d'espace, plus aéré […] pour tous les écrans », donc le produit est **volontairement plus aéré** que
  les planches, et c'est la planche qui est en retard.
- Aucune couleur du front n'est écrite hors de la charte ; les jetons sont **sémantiques**, jamais
  des noms de couleur.
- Tout écart assumé est **écrit** — registre de dette ou note de planche —, jamais laissé au constat.

## Risques

- **Les planches vieillissent pendant qu'on les relit.** Le cas s'est déjà produit (A15, corrigée le
  jour même où E12US002 a livré le feu vert). Vérifier `git log main --first-parent` quand un écran a
  l'air d'avoir bougé.
- **Trois arbitrages du dossier restent ouverts** (noms des trois axes, niveau sous l'axe,
  étanchéité de l'Atelier le jour J). Les écrans qu'ils touchent ne peuvent pas être figés avant
  réponse — ADR-0074 rend les planches opposables, il ne tranche pas ces trois points.
  *(Le « verdict d'A01 », longtemps compté comme quatrième, **a été rendu** : le questionnaire du
  04/08 coche « A — Formulaire sobre plein cadre » et « 🟡 validé avec réserves ». C'est
  `maquettes/README.md` qui était périmé, et cet épic l'avait recopié — corrigé à la revue
  d'E17US003.)*
- **La fidélité peut se retourner contre l'ergonomie.** Une planche est jugée à l'arrêt ; un écran de
  saisie est jugé une flèche à la main, à 3 m d'une cible. Là où les deux s'opposent, l'usage gagne
  et la planche est corrigée — pas l'inverse.
