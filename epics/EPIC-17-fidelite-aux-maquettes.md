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

- [x] Poser la charte du club dans l'application (E17US001).
- [x] Aligner le catalogue de composants sur les formes des planches (E17US002).
- [ ] Embarquer **Inter** pour le jour J, sans réseau (`DV-07`) — **arbitrage d'actif en attente**.
- [ ] Confronter les 19 planches `A**` (admin) aux écrans livrés et lister les écarts.
- [ ] Confronter les 9 planches `S**` (saisie & scoreur).
- [ ] Confronter les 7 planches `P**` (public & écran de salle).
- [ ] Resynchroniser `maquettes/assets/appareils.js` sur `axes.ts`.

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
- **Quatre arbitrages du dossier restent ouverts** (noms des trois axes, niveau sous l'axe,
  étanchéité de l'Atelier le jour J, verdict d'A01). Les écrans qu'ils touchent ne peuvent pas être
  figés avant réponse — ADR-0074 rend les planches opposables, il ne tranche pas ces quatre points.
- **La fidélité peut se retourner contre l'ergonomie.** Une planche est jugée à l'arrêt ; un écran de
  saisie est jugé une flèche à la main, à 3 m d'une cible. Là où les deux s'opposent, l'usage gagne
  et la planche est corrigée — pas l'inverse.
