# ADR-0085 — Un atlas généré : le dépôt cartographié en site statique, sans dépendance de rendu

- **Statut** : Accepté
- **Date** : 2026-08-15
- **Décideurs** : Organisateur / Architecte
- **Introduit par** : E00US018
- **S'appuie sur** : [ADR-0001](0001-adopter-les-adr.md) (le Markdown versionné fait autorité) ·
  [ADR-0009](0009-gouvernance-dependances.md) (parcimonie) ·
  [ADR-0063](0063-brouillon-de-format-invariant-a-l-application.md) (précédent du SVG maison)
- **Lie** : [ADR-0075](0075-le-depart-est-la-portee-sportive.md) (la règle « un ADR nomme les
  modules qui le portent », que cet atlas rend mécaniquement vérifiable)

## Contexte et problème

Le dépôt compte **83 ADR**, 29 règles de projet, 109 US livrées et ~56 000 lignes de backend. Tout
est écrit et versionné, mais rien n'est consultable d'un coup d'œil. Le commanditaire a formulé le
manque ainsi : *« j'ai du mal à bien suivre les règles qui sont édictées, si elles sont toujours
d'actualité, si elles évoluent, du coup je ne vois pas bien l'état réel du projet, et son
historique. »*

Ce n'est pas un besoin de dessin d'architecture, et la mesure le confirme :

| Constat | Chiffre |
|---|---|
| ADR au statut `Accepté` | **82 sur 83** |
| ADR explicitement `Remplacé` | **1** |
| Arêtes « Amende » déclarées entre ADR | **42**, dont **19 ADR** effectivement amendés |
| Libellés de **relation** distincts | **26**, pour ~6 sens réels (33 libellés d'en-tête toutes natures confondues) |
| Amendements datés en clair dans `CLAUDE.md` | **6**, pour **19** commits ayant touché le fichier |

Autrement dit : **le champ `Statut` ne discrimine rien.** La péremption réelle d'une décision est
*partielle et implicite* — portée par les arêtes d'amendement — et elle n'est écrite **sur aucune
des deux fiches concernées**. Un lecteur qui ouvre `ADR-0075` y lit « Accepté » et n'apprend nulle
part qu'`ADR-0076` et `ADR-0079` l'ont amendé depuis.

Le même angle mort existe côté code : `ADR-0075` a institué la section « Porté dans le code par »
après avoir constaté qu'une décision non rattachée au code peut diverger **treize mois** en
silence. Vingt-cinq ADR portent aujourd'hui cette section, qui nomme 90 modules et 234 symboles —
**et rien ne vérifie que ces promesses tiennent encore**.

## Options envisagées

1. **Des diagrammes Mermaid dans les `.md`, rendus par GitHub.** Zéro outillage. Écarté par le
   commanditaire sur le rendu (« trop de courbes et de chevauchements ») et, plus fondamentalement,
   parce qu'un diagramme ne répond pas à la question posée : le manque est une **traçabilité**, pas
   une illustration.
2. **Un outil de documentation tiers** (wiki, générateur de site). Écarté : c'est exactement ce
   qu'[ADR-0001](0001-adopter-les-adr.md) a rejeté, « parce qu'il se désynchronise du code ».
3. **Un site statique généré depuis les sources versionnées, vérifié en CI.** Retenu.

## Décision

**Cinq points.**

**1. Un site isolé, généré, sans autorité.** `atlas/` sert un site statique lu depuis `CLAUDE.md`
et `docs/adr/`. L'atlas **ne remplace rien** : chaque page nomme sa source, aucun corps de texte
n'y est dupliqué, et le supprimer ne perdrait aucune information.

*Pourquoi ce n'est pas le wiki rejeté par ADR-0001.* Le mode de défaillance qu'ADR-0001 redoutait
est la **désynchronisation**. Ici elle est rendue impossible par construction : les données sont
régénérées depuis le dépôt et la CI échoue si elles divergent. Un wiki externe se désynchronise
parce que personne ne le régénère ; un artefact dérivé sous porte mécanique, non. **Sans la porte,
cet ADR contredirait ADR-0001** — c'est le point 3 qui rend le point 1 acceptable.

**2. SVG maison, aucune bibliothèque de rendu.** Les schémas sont construits à la main à partir de
géométries connues d'avance (trois colonnes fixes pour le voisinage d'un ADR, un rang par date pour
les chaînes d'amendement). Segments strictement horizontaux et verticaux, coudes à angle droit.
Précédent : [ADR-0063](0063-brouillon-de-format-invariant-a-l-application.md) §5 bis.

*Limite assumée, écrite ici pour ne pas être redécouverte plus tard :* **aucun moteur de mise en
page de graphe n'est écrit ni importé.** Un Sugiyama correct, c'est 800 à 1 500 lignes et des
semaines de réglage. On ne l'écrit pas, et on ne le sous-traite pas non plus : on **choisit des
vues dont la forme est connue**. Le jour où un graphe libre s'imposera (le graphe d'imports du
backend, ~250 nœuds), la réponse sera de **changer de forme** — une matrice de dépendances, qui n'a
aucune mise en page et où les cycles se lisent sous la diagonale — et non de monter en échelle.

**3. Données générées, commitées, vérifiées en CI.** `atlas/donnees/*.js` est du généré committé :
l'atlas est ainsi consultable après un simple clone, sans rien lancer. La CI régénère et compare.
Le bruit de diff, contrepartie assumée, est borné par `linguist-generated` dans `.gitattributes`,
par une sortie triée sans horodatage, et par un `indent=1` qui donne des diffs à la ligne.

*La comparaison a **une** exemption, et il faut la nommer ici puisque c'est cette porte qui rend le
point 1 acceptable.* Quatre fichiers sur cinq se comparent à l'octet près. `historique.js`, dérivé
de git, ne le peut pas : au moment du hook pre-commit le commit en cours n'existe pas encore, alors
que la CI le voit — une comparaison stricte serait **rouge en permanence**, donc désactivée. Il se
compare donc par **tolérance d'ajout** : la régénération peut contenir des entrées de plus, mais
aucune entrée commitée ne peut disparaître **ni être modifiée**, et une règle vidée est signalée.
Ce qui reste toléré, et qu'il faut savoir : l'histoire d'une règle est **toujours en retard de son
dernier commit**, rattrapée à la régénération suivante.

*Deux garde-fous en découlent.* La génération **refuse de tourner sans git** — sans lui,
`historique()` rendrait un dictionnaire vide qui serait écrit et annoncé « atlas généré », effaçant
toute l'histoire sans un mot. Et `.gitattributes` porte `linguist-generated` **sans** `-diff` :
marquer ces fichiers binaires pour git rendait `git diff`, `git blame` et la vue PR muets, si bien
qu'une falsification n'était visible sur aucun canal.

**4. Le partage généré / manuel, et deux calibrages de sévérité.**

- Un **libellé de relation inconnu fait échouer le générateur**. Le vocabulaire des ADR est ouvert
  (26 libellés de relation, un nouveau tous les 3-4 ADR) : sans échec bruyant, le graphe perdrait
  des arêtes en silence. Le message d'erreur donne la ligne à coller.
- Une **incise datée de nature inconnue ne fait pas échouer** : c'est de la prose. Une porte qui
  rougit sur un choix de style est désactivée en un mois, et on perd alors aussi les contrôles
  justes.
- Les **contrôles** suivent la même logique : `bloquant` pour un constat sans ambiguïté (chemin
  inexistant, ADR cité absent), `signal` pour l'heuristique (symbole introuvable) et la forme (11
  ADR datent en `JJ/MM/AAAA` au lieu de l'ISO du reste du registre — accepté, normalisé, signalé).

**5. L'ancre comme identité d'une règle.** Chaque règle de `CLAUDE.md` porte
`<!--regle:slug-->`. Un identifiant dérivé du numéro ou du titre se détacherait de sa règle au
premier réordonnancement — `CLAUDE.md` a bougé dix-neuf fois en cinq semaines — et l'atlas
afficherait alors l'histoire d'une règle sous une autre **sans rien casser de visible**.

⚠️ *Ce que l'ancre ne fait pas, dit ici pour ne pas sur-promettre.* Elle **nomme** l'identité ;
elle ne la **prouve** pas. L'historique vient de `git log -L <bornes>`, donc de la **position** des
lignes : échanger deux ancres, ou réécrire une règle sous une ancre héritée, produit un atlas faux
que `--verifier` ne peut pas voir — il compare du généré à du généré. Une revue l'a démontré en
clone jetable. La fiche d'une règle dit donc ce que sa part git est réellement : *l'histoire des
lignes qui portent cette règle aujourd'hui*.

*Périmètre :* les quatre sections d'ingénierie (Règles non négociables, Dette, Économie de
contexte, Workflow). Le `guide-architecture.md` §12 n'est **pas** ancré : c'est une checklist de
rappel des mêmes règles, et lui donner des ancres créerait deux identités pour une seule règle.

**6. Le générateur vit sous `backend/`, hors de l'hexagone et hors du paquet livré.** Ce n'est ni
une couche ni un détail d'arborescence : `backend/pyproject.toml` déclare `mypy files=["."]`,
`ruff src=["."]` et `pytest testpaths=["tests"]` **relativement à `backend/`**. Du Python posé
ailleurs échapperait aux trois portes de qualité. Il est en revanche **exclu** de
`[tool.setuptools.packages.find]` : c'est de l'outillage, il n'a rien à faire dans la wheel ni dans
le binaire PyInstaller. Précédent assumé : `backend/build_release.py` et `backend/release/`.

*Conséquence à tenir :* `backend/atlas/` **n'appartient à aucune couche** et n'a le droit d'importer
aucune d'elles ni d'être importé par elles. C'est pourquoi `atlas` a été ajouté à la denylist de
`backend/tests/test_domain_isolation.py` — sans quoi le domaine aurait pu l'importer en silence,
la denylist ne protégeant que ce qu'on a pensé à y écrire.

## Conséquences

**Ce que ça apporte.** La question « cette décision tient-elle encore ? » reçoit une réponse
calculée plutôt que devinée : 19 ADR sont affichés « partiellement dépassés ». Les 234 symboles
promis par les sections « Porté dans le code par » sont confrontés au dépôt — le contrôle retrouve
le cas dont `CLAUDE.md` avertit, `ADR-0028` promettant une classe `Equipe` qui n'existe pas.

**Ce que ça coûte.** ~350 Ko de généré committé, touché à chaque US qui bouge une source. Une ligne
de table de relations tous les trois ou quatre ADR. Une casse de parseur à chaque fois qu'un
fichier lu change de forme.

**Le coût le moins évident : deux branches parallèles périment l'atlas sans se toucher.** Deux US
menées de front peuvent n'avoir **aucun conflit git** — fichiers distincts, régions disjointes — et
laisser malgré tout `main` avec des données périmées : il suffit que l'une ajoute un ADR et que
l'autre ait généré ses cartes avant. La seconde fusion rend alors le job de l'atlas **rouge sur
`main`**, avec un message qui dit quoi faire (`cd backend && python -m atlas`).

*Constaté dès la première livraison* : `E00US018` et la branche du système suisse fusionnaient sans
un seul conflit, tout en se périmant mutuellement par ADR-0084 interposé.

C'est la contrepartie assumée du généré committé, et elle se traite par une **règle de merge**, pas
par du code : **la PR qui fusionne en second régénère l'atlas avant son merge**. Un commit d'une
ligne, dans la branche, avant de merger. On ne cherche pas à automatiser : régénérer à la fusion
demanderait d'écrire dans un dépôt depuis la CI, ce qui coûte bien plus cher que le geste qu'on
évite. C'est le même compromis, et le même geste, que le contrôle de synchronisation
`requirements.txt` ↔ `pyproject.toml` déjà en place.

**Ce que ça ne fera jamais.** Dire si une règle est *encore d'actualité* — indécidable
mécaniquement. L'atlas affiche des **signaux à vérifier**, jamais un verdict. Et le contrôle de
portage vérifie qu'un fichier **existe**, pas qu'il **fait** ce que l'ADR promet : c'est un
garde-fou grossier, présenté comme tel.

**Objection à traiter de front.** [`docs/audit-maintenabilite.md`](../audit-maintenabilite.md) §5
conclut « Documentation, tests, procédure de revue → ne rien changer ». Cette conclusion visait
l'ajout de **charge de procédure** : l'atlas n'ajoute **aucun geste** au développeur, tout y est
généré. Il ajoute une porte mécanique, de la même famille que `domain-isolation`. Et il attaque le
chiffre que le même audit relève — le rayon d'impact d'une US passé de 6 à 18 fichiers touchés.

**Dépendances : aucune.** Le générateur est en stdlib pure. C'est vérifié par construction : son
job de CI tourne **sans `pip install`**.

⚠️ **Le job n'est une porte qu'après un geste manuel.** Comme les deux autres, `Atlas — cartes
générées à jour` ne bloque un merge que s'il est ajouté aux *required status checks* côté GitHub.
Piège de second ordre, à connaître : sur une *pull request*, GitHub exécute le workflow **de la
tête de PR** — une branche ouverte avant cette US n'a pas le job, mergera sans jamais le lancer, et
laissera `main` rouge jusqu'à la régénération suivante.

**Dette ouverte :** [DETTE-065](../dette.md) — le JavaScript du site n'est ni typé ni linté,
`eslint` et `prettier` ne voyant que `frontend/`.

## Porté dans le code par

> *Vérifié dans le code du jour, pas déduit de cet ADR — nommer un module vide reproduirait
> exactement le défaut que la section existe pour empêcher.*

- `backend/atlas/normalisation.py` — la table `_RELATIONS`, garde-fou du vocabulaire (point 4)
- `backend/atlas/sources/reglement.py` — `lire_regles`, la lecture par ancre (point 5)
- `backend/atlas/sources/adr.py` — `lire_decisions`, le graphe d'amendement et le portage (point 1)
- `backend/atlas/controles.py` — `verifier`, les deux sévérités (point 4)
- `backend/atlas/rendu.py` — `serialiser` et `ecarts`, le déterminisme et la porte (point 3)
- `backend/tests/test_atlas_corpus.py` — les garde-fous sur le dépôt réel
- `backend/tests/test_atlas_contrats.py` — les promesses de l'US, éprouvées hors du dépôt réel
- `backend/tests/test_atlas_historique.py` — `git log -L` éprouvé sur un dépôt jetable (point 5)
- `backend/tests/test_atlas_site.py` — les contraintes du site statique (point 2)
- `backend/tests/test_domain_isolation.py` — `atlas` dans la denylist du domaine (point 6)
- `atlas/statique/pages.js` — les schémas en SVG maison (point 2)
- `.github/workflows/ci.yml` — le job qui régénère et compare, sans installer de dépendance
- `.pre-commit-config.yaml` — la moitié locale de la porte, à couverture partielle assumée
- `.gitattributes` — `linguist-generated` sans `-diff` (point 3)
