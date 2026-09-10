# ADR-0107 — Une écriture concurrente est arbitrée par le rang de qui écrit

- **Statut** : Accepté *(la **décision** est prise ; **rien ne l'implémente encore** — cf. § « Porté dans le code par », qui le dit au lieu de le laisser croire)*
- **Date** : 2026-09-10
- **US** : `E16US020` *(non prise à ce jour)*
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0030](0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md) — la saisie est autorisée
    **au poste de cible**, sans authentification de personne. C'est lui qui fixe l'identité du rang
    le plus bas, et donc ce que cet ADR peut ordonner
  - [ADR-0035](0035-atomicite-acte-trace-session-partagee.md) — l'acte tracé et la session partagée :
    le contexte dans lequel deux écritures se croisent
  - [ADR-0102](0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) — la **forme** de cet
    ADR : décision prise, section « Porté dans le code par » qui dit franchement qu'elle ne porte
    rien encore

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'ADR-0075 § « Portée de la règle »** : il porte
> une politique d'**autorisation**, pas le moteur sportif, la portée, ni une politique injectable au
> sens de la règle 2. C'est écrit ici pour qu'un trou non commenté ne produise pas la prochaine
> omission.

## Contexte

Le questionnaire de maquettes S09 (04/08/2026) demandait comment trancher un conflit de modification
concurrente. Réponse du commanditaire, sans ambiguïté :

> « hiérarchie → archer < scoreur < admin »

Trois constats, tous vérifiés dans le code du 10/09/2026, cadrent ce que cette réponse peut vouloir
dire :

1. **Il n'existe aujourd'hui aucun mécanisme de conflit.** `RegistreIdempotence` ne dédoublonne qu'un
   **rejeu du même client** (`identifiant_saisie` identique). Deux écritures d'identifiants
   différents sur la même volée non validée : `Serie.saisir_volee` écrase la première **en silence**,
   sans version, sans horodatage comparé, sans `409`.
2. **La file d'écriture ne protège de rien ici.** Le writer unique (règle 7) **sérialise** les
   écritures — il n'y a donc pas de course en base. Mais *sérialiser n'est pas arbitrer*, et c'est
   précisément ce qui rend le défaut invisible : tout se passe bien, et une saisie disparaît.
3. **Les rangs n'ont aucun ordre.** `exiger_admin`, `exiger_scoreur`, `exiger_poste_de_cible`,
   `autoriser_saisie`, `autoriser_forfait` sont cinq **prédicats indépendants**. Aucune comparaison
   n'existe entre eux : cet ADR introduit le **premier** ordre entre rangs du dépôt.

⚠️ **Le rang nommé « archer » n'existe pas, et n'existera pas.** ADR-0030 et `D-13` (14/07/2026) ont
aboli la notion : il n'y a pas de rôle archer, il y a **un poste ouvert**, dont l'identité est le
**lieu** et non la personne. La réponse du questionnaire doit donc se lire sur les trois identités
réelles.

## Décision

**1. L'ordre est `poste de cible < scoreur < admin`.** Une écriture d'un rang **supérieur** à celui
qui a déjà écrit **écrase**. Une écriture d'un rang **inférieur** est **refusée** (`409`), et l'écran
dit pourquoi — un refus muet serait pire que l'écrasement qu'il remplace.

**2. Le rang est celui du jeton, jamais celui du message.** `Volee.saisie_par` **existe** mais sa
propre docstring le qualifie de **déclaratif** : c'est un nom libre, issu du corps de la requête.
L'employer comme source d'autorité livrerait une hiérarchie qu'un poste contourne en se déclarant
admin. Le rang se lit sur l'identité **authentifiée**, résolue à la frontière API.

**3. À rangs égaux, la règle n'arbitre rien** — et c'est assumé. Deux tablettes de cibles différentes
portent le **même** rang : entre elles, le dernier écrit gagne, exactement comme aujourd'hui.

**4. La préséance ne survit pas au conflit.** Le rang de la dernière écriture ne verrouille pas la
volée pour toujours contre les rangs inférieurs. Sans cette borne, un admin qui annule une validation
(`E16US019`) rendrait la volée inaccessible au scoreur **et** à la tablette — c'est-à-dire à ceux qui
doivent la corriger. La fenêtre exacte est à définir à l'implémentation.

## Alternative écartée — le refus explicite symétrique

Refuser **tout** second écrivain (`409` + rafraîchir, indépendamment du rang) et lui montrer la
saisie de l'autre. Recommandée par l'assistant, **écartée par le commanditaire** le 10/09/2026, qui a
retenu la lettre du questionnaire.

⚠️ **Elle est écartée, pas oubliée, et son avantage est réel** : elle traite le cas que la hiérarchie
ne peut pas traiter — deux postes de même rang, qui est **le cas le plus fréquent en salle**. Si le
silence de la hiérarchie se paie un jour de tournoi, c'est elle qu'on reprend.

## Conséquences

- Une hiérarchie **tranche sans prévenir** : celui qui est écrasé ne l'apprend pas. C'est le revers,
  il a été exposé avant la décision et accepté.
- Le rang doit être **connu au moment d'écrire**. Deux voies restent ouvertes, à trancher à
  l'implémentation : le **dériver de la garde** (les trois rangs sont déjà discriminables à la
  frontière — `autoriser_saisie` rend `Poste | None`, `exiger_scoreur` rend `Scoreur`) ou le
  **persister** sur la volée, ce qui coûte une colonne et une migration.
- Si la règle vaut pour tous les formats, elle atterrit sur les **sept sites** de `DETTE-065` (le
  garde d'autorisation des routeurs d'écriture, recopié sept fois). Elle doit alors vivre en **un**
  endroit — service ou domaine —, jamais recopiée dans chaque routeur.
- ⚠️ Cet ADR **interagit** avec l'élargissement d'`autoriser_saisie` au scoreur décidé pour
  `E16US019` : sans lui, le scoreur n'a aucune identité sur `POST /volees` et le rang du milieu
  n'aurait aucun porteur sur le chemin d'écriture ordinaire.

## Porté dans le code par

⚠️ **Rien à ce jour, et c'est écrit exprès.**

La décision est prise ; `E16US020` n'est pas prise. Nommer ici `backend/api/dependances.py` ou
`backend/domain/serie.py` ferait exactement ce qu'ADR-0017 a fait pendant treize mois : désigner un
module qui ne porte pas la décision, et rendre la vérification impossible en la faisant croire faite.

À l'implémentation, cette section nommera les modules qui **comparent** effectivement deux rangs — et
le test qui prouve qu'une écriture de rang inférieur est refusée.
