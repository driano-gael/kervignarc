# ADR-0084 — Un seul port de lecture de classement, résolu par type

- **Statut** : Accepté
- **Date** : 2026-08-15
- **Décideurs** : Organisateur / Architecte
- **Précise** : [ADR-0083](0083-le-contrat-de-phase-jouable.md) (le contrat de phase jouable) —
  celui-ci unifie les **tables** de capacités, celui-ci le **câblage** qui les honore
- **S'appuie sur** : [ADR-0080](0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)
  (un prélèvement lit le classement de sa phase source) · [ADR-0081](0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
- **Porté dans le code par** : `application/prelevement.py` (`LecteurClassementDePhase`) ·
  `application/saisie_duels.py` (`TYPES_DELEGUES`, `ServiceSaisieDuels.brancher_lecteur`,
  `_classement_de_l_ordre`) · `bootstrap/composition.py` (les branchements tardifs) ·
  `domain/contrat_phase.py` (`TYPES_CLASSANTS_LUS`, dont `TYPES_DELEGUES` dérive)

## Contexte et problème

`ServiceSaisieDuels._classement_de_l_ordre` est le **point unique** où le moteur transforme
« l'ordre d'une phase amont » en classement prélevable. Il sait produire lui-même deux classements —
celui d'une qualification et celui d'un arbre qu'il reconstruit — et doit **déléguer** les autres :
rejouer une phase de poules ou un Big Shoot Off demande son réglage, son plan et ses tirs, soit
trois repositories qu'un service de tableau n'a aucune raison de connaître.

La délégation ne peut pas passer par un appel direct : les deux côtés se tiennent par les deux
bouts. `ServicePoules` reçoit `ServiceSaisieDuels` dans son constructeur (il a besoin de son
classement amont et de son pavé de saisie), et `ServiceSaisieDuels` a besoin de `ServicePoules` pour
lire ce qu'une phase de poules a classé. Un import mutuel serait un **cycle de modules**, et aucun
ordre de construction ne satisfait les deux. D'où un **port** — une interface déclarée dans le
module que les deux partagent — et un **branchement tardif**, explicite au composition root.

**Le problème n'est pas le port, c'est qu'il a été recopié.** E05US023 a écrit
`LecteurClassementPoules` ; E05US028 l'a dupliqué en `LecteurClassementBigShootOff`, à la signature
**strictement identique** — au point qu'un service satisfaisant l'un satisfait l'autre par typage
structurel. Chaque format ajoutait alors quatre choses : un protocole, un attribut, une méthode
`brancher_<format>`, et une branche de `if` dans `_classement_de_l_ordre` — les deux dernières
branches ne différant que par le type testé et le slot lu.

La duplication était **assumée et datée** : `CLAUDE.md` veut qu'un remède structurel repose sur une
**3ᵉ occurrence réelle** dans le code d'aujourd'hui, pas sur une évolution supposée. Le code le
disait lui-même — *« 2ᵉ occurrence, pas 3ᵉ. E05US026 et E05US027 la porteront à quatre : c'est là
que le `dict[TypePhase, …]` se justifiera sur preuve. »*

E05US026 (système suisse) est cette 3ᵉ occurrence.

## Décision

### 1. Un port unique, `LecteurClassementDePhase`

Les deux protocoles sont fondus en un. Il pose **une** question — « quel classement cette phase
a-t-elle produit ? » — et il est réalisé par chaque service de format.

### 2. Le type de phase devient un **argument**, pas un nom de méthode

`brancher_poules(...)` et `brancher_big_shoot_off(...)` deviennent
`brancher_lecteur(TypePhase.POULES, ...)`. Les slots nommés deviennent un
`dict[TypePhase, LecteurClassementDePhase]`, et la cascade de `if` une **recherche**. Ajouter un
format ne touche plus ni le port, ni le service : seulement une ligne au composition root.

### 3. La liste des types délégués **dérive du registre de contrat**

```python
TYPES_DELEGUES = TYPES_CLASSANTS_LUS - {QUALIFICATION, ELIMINATION_DIRECTE}
```

Elle n'est pas énumérée à la main. Un format qui devient `classement_lisible` au registre
(ADR-0083) entre ici **automatiquement** ; les deux soustraits sont exactement ceux que le service
résout sur place. C'est la promesse d'ADR-0083 — « une table qui diverge devient impossible plutôt
qu'improbable » — appliquée au câblage et non plus seulement aux capacités.

### 4. Le branchement d'un type non délégué est **refusé au démarrage**

Passer le type en argument ouvre une porte que les méthodes nommées fermaient : rien n'empêchait
plus de brancher un lecteur pour un type que le registre ne déclare pas lisible, ou pour un type
que le service résout lui-même. Le lecteur serait alors branché et **jamais consulté** — un câblage
muet, soit exactement la classe de défaut qu'ADR-0083 combat.

`brancher_lecteur` lève donc une `ValueError` sur un type hors `TYPES_DELEGUES`. C'est une faute de
programmation, pas une donnée d'exécution : elle casse au démarrage, jamais en salle.

### 5. Une entrée absente reste **licite**

`self._lecteurs.get(type)` rendant `None` n'est pas un défaut de câblage silencieux : c'est le
régime légitime de tout montage qui n'a pas ce format — le harnais de simulation, les tests de
tableau. Le prélèvement retombe alors **inerte**, comme avant que le format ne soit jouable, plutôt
que d'inventer un ordre. Le prix est connu et inchangé : l'oubli au composition root ne casse
aucune compilation, il *lit* moins bien. C'est `test_poules_api` qui le garde, pas le typage.

## Conséquences

**Positives**

- Ajouter la colline (`E05US027`) ne demande plus qu'une ligne de câblage : le 4ᵉ format ne paie
  plus le prix du 2ᵉ et du 3ᵉ.
- La règle « qui sait lire quoi » a **une** source (`domain/contrat_phase.py`) et un seul lieu
  d'application, au lieu de deux tables parallèles à tenir d'accord.
- La garde du §4 transforme en erreur de démarrage un défaut qui, jusqu'ici, aurait été silencieux.

**Négatives, et assumées**

- ⚠️ **Écart à la règle « un remède structurel se traite en ADR + US dédiée, jamais en douce dans
  l'US courante »** (`CLAUDE.md`, § Dette). Tranché par le commanditaire le 15/08/2026, sur
  l'argument suivant : la 3ᵉ preuve **naît dans ce diff**, et différer aurait obligé à écrire un 3ᵉ
  port jetable pour le défaire aussitôt après. La contrepartie exigée est la **lisibilité de la
  revue** — le remède voyage dans un commit séparé, en tête de branche, sans une ligne de système
  suisse dedans. L'écart est ici pour être relevé, pas pour faire précédent : le cas qui l'autorise
  est celui où l'US courante *est* la preuve, et il ne se généralise pas.
- Le typage est **un cran plus faible** : `brancher_lecteur(TypePhase.X, lecteur)` accepte
  n'importe quel type à la compilation, là où `brancher_poules` ne pouvait pas se tromper de
  format. C'est le prix de la table, et c'est précisément ce que la garde du §4 rachète — à
  l'exécution, au démarrage, avec un message qui nomme la règle violée.
- Le port perd les mentions de format dans son nom : une lecture rapide voit moins vite *qui* le
  réalise. La docstring nomme donc explicitement les trois services, et le composition root reste
  l'endroit où la réponse se lit en trois lignes.
