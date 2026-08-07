# ADR-0076 — Un déroulé défini une fois, un avancement par départ

- **Statut** : Accepté
- **Date** : 2026-08-07
- **Décideurs** : Organisateur / Architecte
- **Complète** : [ADR-0075](0075-le-depart-est-la-portee-sportive.md) — le départ reste la portée
  **sportive** (classements, tableaux, duels étanches par créneau) ; cet ADR précise que c'est la
  portée d'**exécution** et non d'**édition**
- **Amende** : [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (la séquence 1..N
  devient celle du **déroulé du tournoi**, pas d'un départ) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (table `deroule_etape` neuve, `PHASE` allégée) ; [`docs/glossaire.md`](../glossaire.md)
  (*Déroulé*, *Étape*, *Phase*)
- **Introduit par** : E01US025

## Contexte et problème

ADR-0075 a fait du départ la portée sportive, et `FormatTournoi.appliquer` produit depuis une
**séquence par départ**. Un tournoi de 4 créneaux porte donc **4 copies complètes** de chaque phase
— chacune avec son barème, son grain, ses prélèvements, sa profondeur.

Cette duplication a trois défauts, constatés en écrivant le code :

1. **Les copies peuvent diverger en silence.** Rien n'empêche le barème du départ 3 de s'écarter des
   autres. Le code a dû s'en accommoder : `application/portee.py` expose une
   `qualification_representative` dont la docstring reconnaît rendre « une **approximation
   d'affichage**, jamais une base de calcul ». Un helper qui doit s'excuser signale un modèle bancal.
2. **Éditer le déroulé devient une écriture en éventail**, et « la phase 2 » désigne alors N objets
   aux N identifiants. La question « adresse-t-on par `ordre` ou par `phase_id` ? » n'a pas de bonne
   réponse — elle naît du modèle, pas de l'API.
3. **`Phase` mêle deux natures** : sa *définition* (type, barème, grain, sources, effectif,
   profondeur) et son *avancement* (`statut`). La première est commune au tournoi, la seconde
   propre au créneau. Les tenir dans un seul objet oblige à dupliquer la première pour faire varier
   la seconde.

**L'arbitrage de l'organisateur (06/08/2026)** a tranché la maille : « *l'écran phase n'est pas
concerné par le départ, ni le format de tournoi ; seul le tournoi concret a besoin de savoir sur
combien de départs on le joue* », et « *on doit pouvoir les placer en dehors de l'atelier sur un
créneau de départ* ». Autrement dit : on compose **un** déroulé, on le fait vivre **par créneau**.

## Décision

**Le déroulé est défini une fois, au tournoi ; l'avancement est porté par chaque départ.**

```
Tournoi ──► Déroulé : suite d'ÉTAPES (définition, une seule fois)
   ├── Départ 1 ──► PHASES : l'avancement de chaque étape dans ce créneau
   └── Départ 2 ──► PHASES : idem, indépendant
```

1. **`EtapeDeroule`** — la **définition** d'une étape, portée par le tournoi : `ordre`, `type`,
   `bareme`, `validation`, `sources`, `effectif`, `profondeur`, `barrage_jusqu_au`. Aucun statut,
   aucun départ. C'est `ModelePhase` (le contenu d'un format) doté d'un tournoi et d'une identité.
2. **`Phase`** — l'**instance** d'une étape dans un créneau : `depart_id`, `ordre`, `statut`, `id`.
   Elle **reste l'objet du moteur** : en mémoire, elle porte toujours sa définition, mais
   **assemblée** par le repository depuis l'étape de même `ordre`. Les 34 modules qui lisent
   `phase.bareme` ne changent pas d'une ligne.
3. **La séquence 1..N est celle du déroulé** (ADR-0045 §3 conservé, portée déplacée). Les instances
   d'un départ en héritent : elles ne peuvent pas avoir d'ordres différents des étapes.
4. **Composer** (ajouter, éditer, réordonner, supprimer une étape) se fait au **tournoi**, à
   l'atelier — **une** écriture, plus d'éventail.
5. **Faire vivre** (démarrer, mettre en pause, terminer) se fait au **départ**, au pilotage : le
   créneau du matin peut être en duels pendant que celui de l'après-midi qualifie.
6. **`phase_id` garde son sens** : il désigne une phase *dans un créneau*, ce qui est exactement ce
   dont les artefacts d'exécution ont besoin. `forfait`, `duel`, `placement_tableau` et `barrage`
   ne bougent pas.

### Ce qui a été écarté

- **Ne garder que la définition, et calculer l'avancement.** Impossible : les forfaits, duels et
  plans de duels pendent à une phase *persistée* d'un créneau. Sans ligne, plus de clé étrangère.
- **Garder les copies et interdire la divergence par une garde.** Une garde qu'on peut contourner
  n'est pas un invariant. Le modèle doit rendre la divergence **impossible**, pas improbable.
- **Faire de `Phase` un simple couple (départ, ordre) sans définition en mémoire.** Correct sur le
  papier, mais 34 modules liraient alors une définition par jointure explicite : beaucoup de bruit
  pour un gain nul, la jointure étant l'affaire du repository (ADR-0003).

## Conséquences

**Positives**

- **La divergence devient impossible** : il n'y a qu'une définition. `qualification_representative`
  et son avertissement disparaissent — la lecture transverse redevient exacte, non approximative.
- **L'édition n'a plus de question d'adressage** : une étape, un `ordre`, une écriture.
- **Un défaut préexistant est corrigé structurellement** : `ModelePhase` ne portait pas
  `barrage_jusqu_au` alors que `Phase` l'a, donc promouvoir un tournoi dont une phase avait un seuil
  de barrage **perdait ce seuil** en silence. Avec une définition unique, l'écart de champs ne peut
  plus exister.
- L'oracle multi-départ et le garde-fou de portée d'ADR-0075 **restent valables** : ils éprouvent
  l'étanchéité des classements, que cet ADR ne touche pas.

**Coûteuses / à surveiller**

- **Troisième révision du modèle dans la même US**, après le changement de portée et la migration
  `0042`. Assumé : le découvrir maintenant coûte moins cher que dans six mois, et la suite verte
  d'ADR-0075 sert de filet.
- **Migration `0043`** : table `deroule_etape` créée, `phase.config` retirée. Les définitions sont
  reprises depuis les phases du **premier départ** de chaque tournoi — les copies des autres
  créneaux sont donc **perdues si elles avaient divergé**. C'est le sens de la décision (elles
  n'auraient pas dû pouvoir diverger), mais c'est une perte réelle, à dire.
- **Synchronisation instances ↔ étapes** : ajouter une étape doit créer son instance dans chaque
  créneau, en supprimer une doit les retirer. C'est le seul endroit où l'éventail subsiste — mais
  il porte sur des lignes vides de définition, pas sur des réglages.
- **Renuméroter devient une écriture d'ensemble** *(découvert à l'implémentation, 07/08/2026)*. Le
  rang est à la fois la clé de la séquence **et** la clé de jointure définition ↔ avancement, d'où
  l'unicité `(tournoi, ordre)` et `(départ, ordre)`. Or tout réordonnancement, tout recompactage
  après suppression et toute insertion de la qualification en tête passent par un état où deux
  lignes portent le même rang : les écrire une à une bute sur la contrainte. `DerouleRepository` et
  `PhaseRepository` gagnent donc un `reordonner` — l'adapter SQL gare les rangs hors de portée avant
  de les reposer, en une transaction. Ce n'est pas un contournement de la contrainte mais sa
  contrepartie : on la garde *parce qu'*elle dit vrai, et on paie le prix d'écriture qu'elle impose.
  Le service, lui, dit quel déroulé il veut — l'ordre des `UPDATE` ne le regarde pas (ADR-0003).

## Porté dans le code par

- `backend/domain/deroule_etape.py` (`EtapeDeroule`) et `backend/domain/phase.py` (`Phase`,
  `SequencePhases` sur les étapes)
- `backend/domain/format_tournoi.py` (`appliquer` produit **un** déroulé)
- `backend/application/departs.py` (`ServiceDeparts.creer`) : le **sens inverse** de la
  synchronisation — un créneau créé après coup rejoue le déroulé **déjà** composé, une instance par
  étape. L'ADR n'énonçait l'invariant que dans un sens (« ajouter une étape l'instancie dans chaque
  créneau ») ; c'est cette asymétrie qui avait produit le défaut, et la migration `0043` porte le
  même geste pour les bases existantes
- `backend/application/phases.py` (composition au tournoi, cycle de vie au départ), et
  `backend/application/portee.py`, où `qualification_representative` devient
  `qualification_du_tournoi` — la lecture transverse n'est plus une approximation
- `backend/application/grain_validation.py` (le grain s'écrit **une fois**, sur l'étape : il passait
  par `PhaseRepository`, qui depuis cet ADR ne déplace que l'avancement — l'écriture *paraissait*
  réussir sans rien changer)
- `backend/api/v1/phases.py` : deux lectures pour deux mailles — `GET /tournois/{id}/phases` rend le
  déroulé prévu (sans statut), `GET /departs/{id}/phases` rend l'avancement du créneau
- `backend/infrastructure/db/models.py` (`DerouleEtapeORM`, `PhaseORM` allégée) + migration `0043`
- `backend/tests/test_portee_sportive.py` (garde-fou élargi : la définition n'est pas dupliquée)
