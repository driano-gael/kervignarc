# Résumé du projet — où on en est au 15 août 2026

> Ce fichier est la **photo d'ensemble** : ce qui existe et fonctionne aujourd'hui, dans l'ordre où
> ça a été construit. Pour le détail « quelle US est faite, quelle est la suivante », voir
> [`SUIVI-US.md`](SUIVI-US.md). Pour le dernier fait marquant, voir le fichier daté le plus récent.

## Ce qu'est le produit

Kervignarc gère un **tournoi de tir à l'arc en salle (18 m)** pour un seul club, le jour J, sur un
réseau local **sans internet**. Un serveur fait autorité (FastAPI), sert l'application (React), et
pousse les changements en direct par WebSocket vers une trentaine de tablettes personnelles des
bénévoles. La rigueur est concentrée dans le **moteur métier** ; l'infrastructure reste simple parce
que le contexte est petit et local.

## L'état en une phrase

**Les fondations techniques sont complètes, la configuration d'un tournoi et les inscriptions
fonctionnent, le placement des archers sur les cibles existe, la saisie des scores de qualification
tourne en temps réel — y compris quand le wifi saute — et un tournoi de qualification se suit
désormais de bout en bout : les postes de saisie se supervisent, le classement se calcule, et le
public le consulte en direct sans compte — jusqu'à suivre un archer et voir sa feuille de marque se
remplir volée par volée. Côté organisateur, le **suivi des paiements** (qui a réglé, combien reste-t-il
dû, par archer et par club) est en place — et une somme déjà encaissée ne disparaît plus en silence :
annuler une inscription **payée** ouvre un **remboursement à traiter** que l'organisateur marque
remboursé ou reporté. Un écran de **complétude** dit d'un coup d'œil ce qui
manque avant de terminer le tournoi, une **recherche d'archer** permanente répond à « je tire
où ? » depuis n'importe quel écran admin, et un écran **« Doublons »** repère les fiches en double
et les **fusionne** sans rien perdre. Et l'application se **déploie désormais en un seul fichier**
exécutable qui crée sa base au premier lancement, s'ouvre sur le réseau local, **se sauvegarde toute
seule** et sait produire une **archive complète** du tournoi — prêt pour le jour J, sans installation
ni internet.** Le jalon « qualification de bout en bout » est ainsi **terminé** (à un reliquat de
confort près), et le chantier suivant — les **duels** — est **bien avancé** : l'organisateur **compose
le format** de son tournoi (la séquence des phases) et place les duellistes côte à côte. Et le **scoreur
score désormais un duel de bout en bout** sur son appareil — manche par manche, barrage à l'égalité,
validation du vainqueur qui fait avancer le tableau jusqu'au podium. Le scoreur peut aussi désormais
**déclarer un abandon ou une disqualification** — en qualification (l'archer est relégué ou sorti du
classement, ses flèches conservées) comme en duels (l'adversaire passe d'office) —, un geste
**réversible** qui remplace la suppression. Et un **créneau de tir affiche désormais son état**
(ouvert / lancé / clos, déduit du tir réel) et **se protège** d'une modification ou d'une suppression
accidentelle une fois qu'une session de tir y a commencé. Enfin, pour la démo et la mise au point, un
**cockpit de simulation** rejoue un tournoi **en accéléré et sans rien enregistrer** : un robot génère
des scores et déroule qualifications puis duels, qu'on peut **mettre en pause pour saisir soi-même** à
la place d'un rôle (cible, scoreur) avant de rendre la main — le tout observé par une navbar
cible / archer / scoreur / public. Et le **pilotage de la bascule de tour** commence : un écran
**« Feu vert »** montre en continu, duel par duel, ce qui est **prêt à faire tirer** et ce qui bloque
(nommé), puis un **bouton chiffré lance** les duels prêts d'un geste. Et ce signal a désormais son
**premier écran récepteur** : la tablette de la cible bascule d'elle-même, une fois les tirs validés,
sur un panneau **« Où tire-t-on ensuite ? »** qui donne à chaque archer sa **cible et sa place** en
gros caractères — de même après chaque duel, pour ses deux duellistes. Ce que l'appli ne sait pas
encore (la cible des tours suivants, l'adversaire pas encore sorti de son duel, le rang d'un battu),
elle l'**écrit en clair** plutôt que de laisser un vide. Enfin, le **moteur sait désormais classer
tout le monde** : au lieu de désigner quatre archers et de renvoyer les autres sans rang, il fait
**redescendre chaque perdant** dans le tableau des places qu'il peut encore atteindre, jusqu'à un
rang unique de 1 à N — et un **format préparé pour 120 archers s'ajuste** quand il n'y en a que 82.
Le classeur réel du club (120 archers, 484 matchs) est devenu un **test automatique** qui vérifie ce
moteur à chaque modification. Et l'organisateur peut enfin **décrire son vrai déroulé au lieu de
l'approcher** : l'écran « Phases » propose six formats de plus — **échauffement, barrage, poules,
Big Shoot Off, système suisse, colline** —, chacun expliqué d'une ligne, auxquels s'ajoutent le
**repêchage** et le **handicap** de l'archer. La question du **Big Shoot Off**, restée ouverte au
cahier des charges depuis l'origine du projet, est **fermée** : sa règle a été donnée, et c'est bien
un format à N archers (le « Big » désigne le nombre d'archers, pas de flèches). Et depuis le
01/08/2026, ces formats ne se déclarent plus seulement : ils se **composent, se voient et se font
tourner**. Un écran **« Composer un déroulé »** assemble la séquence complète d'un tournoi type — les
phases, ce qu'on y demande, d'où viennent les archers de chacune —, l'**enregistre même à moitié
faite** (un déroulé n'a besoin d'être complet que le jour où on l'applique) et la **dessine** : une
case par phase, une flèche par groupe d'archers qui passe, et les « braquets » — la tranche de rangs
que se partagent les battus de chaque tour. Changer le nombre d'archers **redessine tout** sans
retoucher le format. Enfin, un bouton **fait jouer le déroulé** sur des archers fictifs et rend la
charge réelle : combien de duels, combien de tours, et le classement produit. Il a immédiatement
corrigé une erreur de comptage que personne n'aurait vue autrement — un tableau à 32 coûte 32 duels
et non 31, la petite finale comprise. Ce déroulé composé se **projette** désormais dans le gymnase :
un **écran branché en salle** se rattache exactement comme une tablette de cible, fait défiler tout
seul classement, plan de cibles et avancement du tournoi, et l'organisateur peut lui **imposer une
vue à distance** (« le classement 10 minutes ») sans traverser la salle — après quoi l'écran reprend
son défilé sans que personne y retourne. Enfin, depuis le 02/08/2026, **l'archer qui a quitté la
salle n'a plus à revenir demander où il tire** : son téléphone lui annonce sa **cible** et sa
**place** pour le duel suivant, son **rang** s'il est sorti — et « 5ᵉ-8ᵉ » quand aucun match n'a
départagé les battus, plutôt qu'un chiffre inventé —, ou la **phase qui le reprend** s'il est
repêché. La même information s'affiche en **panneau complet** pour la table de l'organisation et sur
l'écran de salle : tout le pas de tir d'un coup d'œil, dans l'ordre des cibles. Enfin, l'organisateur
**décide jusqu'où son tournoi classe** (podium, top N, ou un rang unique gagné au tir pour chacun) et
**ce qu'une cible n'a pas le droit de mélanger** — rien, la catégorie, le blason, ou les deux : une
règle d'arbitre que le placement automatique respecte sans exception et qu'aucun glisser-déposer ne
contourne. Enfin, le **05/08/2026**, les **36 planches de maquettes** ont été relues une par
une par le commanditaire et le produit s'est aligné sur ce qui pouvait l'être sans décision à
prendre : une **cinquième porte** pour le vidéoprojecteur, des **largeurs par surface** (le PC
d'organisation n'a plus la même que le téléphone d'un spectateur, et l'écran de salle passe en plein
cadre), le **déroulé en premier** dans l'administration avec un **bandeau permanent** disant sur quel
tournoi et quel départ on travaille, une **liste de tournois triée** par état puis par date, une
**salle qui pagine** enfin ses 200 archers avec compteur et râteau de lettres lisibles de loin, un
**pavé de saisie appelé** au lieu d'imposé — chaque archer pouvant relire ses volées sans prendre la
tablette —, un **pavé de code** qui n'offre que des touches valides, de **vraies fenêtres de
confirmation** à la place des huit boîtes grises du navigateur, et **deux impressions** (étiquettes de
cible, cartes de scoreur) que le serveur produisait depuis longtemps sans qu'aucun écran ne puisse les
déclencher. Enfin, le **05/08/2026 au soir**, l'application a **pris les couleurs du club** : elle
tournait encore sur le jeu de couleurs provisoire posé le premier jour — un violet qui n'appartient à
personne, sur fond blanc — parce que les « US design » annoncées dans le code n'avaient jamais été
écrites. Elle porte désormais la **charte mesurée** : anthracite de la banderole en fond, rouge du
club en aplats (jamais en texte : sur le sombre, il ne se lit pas), **ambre** pour les alertes,
chiffres alignés en colonnes. Une tablette neuve s'ouvre en **sombre** quel que soit le goût de son
propriétaire, tout en gardant son réglage de luminosité par poste. Et les **maquettes font désormais
foi** : un écart entre un écran livré et sa planche est devenu un défaut constatable, là où le dossier
se déclarait jusqu'ici sans autorité. Dans la foulée, le **06/08/2026**, elle en a pris la **forme** :
boutons, champs, cartes, onglets et étiquettes reprennent les valeurs des planches — l'ossature
s'arrondit franchement, le contenu très peu, là où l'application appliquait le même arrondi partout.
Deux exceptions assumées : l'**espacement** reste celui, plus aéré, que vous aviez demandé, et les
tableaux gardent leur vraie structure sous l'apparence des planches. Les écrans ont cette fois été
ouverts **un par un dans un navigateur**, ce qui a fait apparaître deux défauts qu'aucun test ne
voyait — dont un bouton « Annuler le tournoi » qui criait plus fort que l'action principale. Les **19
planches d'administration** ont ensuite été confrontées une par une aux écrans livrés — en lisant
d'abord, pour chacune, **quelle proposition avait été retenue** au questionnaire —, et trois écrans
ont été repris : la **connexion** (colonne centrée, étiquettes au-dessus des champs, bouton pleine
largeur), l'**accueil de l'administration** (la question « Que venez-vous faire ? » et le tournoi sur
lequel le pilotage travaille) et surtout la **supervision des postes**, qui passe en **grille de
tuiles** : l'écran du jour J affichait un tableau, c'est-à-dire la présentation écartée, alors qu'on
lui demande de répondre d'un coup d'œil à « qui s'est tu ? ». Une tablette muette s'y repère
désormais au cadre ambre de sa tuile — sans perdre l'adresse IP ni la révocation, absentes de la
maquette mais indispensables sur le terrain. Enfin, le **07/08/2026**, **chaque départ rejoue le
tournoi** : l'application classait jusque-là tous les créneaux ensemble — sur quatre départs de cent
archers, **un** classement de quatre cents, où l'archer du matin était rangé contre celui du soir
qu'il n'a jamais croisé. Elle en produit désormais **quatre de cent**. Et la distinction se voit à
l'écran : ce qui se **prévoit** (la suite des phases) se compose **une seule fois** pour le tournoi,
ce qui se **tire** se pilote **créneau par créneau** — le matin peut être en duels pendant que
l'après-midi qualifie, ce qui était impossible avant. La relecture de cette correction en a trouvé
**trois autres du même tonneau**, corrigées dans la foulée : le jour J, les quatre écrans qui
répondent à « où est-ce que je tire ensuite ? » envoyaient les archers de l'après-midi vers le
tableau du **matin** ; le suivi du déroulé se dessinait **en double** et dimensionnait ses tableaux
sur la somme des inscrits ; et le contrôle d'effectif laissait démarrer un tournoi de deux créneaux
à 40 et 8 inscrits, pour échouer en salle l'après-midi. Il porte désormais sur le créneau **le moins
garni**, et le refus le **nomme**. Enfin, le **07/08/2026 au soir**, l'écran qui répond à « où en est
mon tournoi ? » a **cessé de mélanger le déroulé et l'argent** : il affichait, l'un sous l'autre, les
cibles restant à terminer et les archers n'ayant pas réglé, alors qu'au milieu d'une journée de tir
on pilote un tour. Le sportif reste au pilotage sur un écran renommé « **Prêt à terminer ?** », le
compte des archers à encaisser a rejoint l'écran **Paiements** — même information, calculée une seule
fois, donc jamais contradictoire. Le **tableau de bord d'accueil** a été filtré au passage : lui aussi
ouvrait l'axe pilotage en mêlant cibles et impayés. Le bouton « Terminer » ne bouge pas : ce qu'il
fige, c'est le sportif, il n'est **jamais bloqué** par un manque, et il continue de rappeler les
impayés **au moment de confirmer** — seul endroit où les deux mondes doivent se croiser. Enfin, le
**08/08/2026**, le public **suit plusieurs archers de bout en bout**. L'application savait le faire
depuis longtemps, mais un seul écran s'en servait : partout ailleurs il fallait chercher ses archers
à l'œil dans cent cinquante lignes. Un **interrupteur unique** en tête de l'écran public — « Tout le
tournoi » / « Mes archers » — centre désormais **tous** les onglets à la fois : classement, tableaux,
affectations, palmarès, plan de cibles. On le règle une fois, il est retenu. La **recherche accepte
le club** en plus du nom (un club choisi seul suffit à lister ses archers), on **suit et on cesse de
suivre depuis la liste** sans la quitter, et chaque archer suivi porte un **récapitulatif repliable
de sa journée** : sa qualification, puis **tous ses tours de toutes les phases** disputées. Enfin, le
**détail des flèches de n'importe quel archer** se déplie d'un clic depuis le classement — y compris
ceux qu'on ne suit pas. Deux garde-fous : les **podiums ne sont jamais amputés** (un podium sans ses
médaillés ne répond plus à « qui a gagné »), et aucun écran ne se vide en silence — quand vos archers
ne sont pas sur l'écran regardé, il le **dit** et propose de revenir à l'affichage complet.

Le **15/08/2026**, le projet s'est doté d'un **atlas** — un dossier qu'on ouvre d'un double-clic,
sans rien lancer, pour voir **ce qui fait règle aujourd'hui et depuis quand**. Il montre le règlement
en vigueur, puis l'histoire datée de chaque règle, lue directement dans l'historique du dépôt. Il
répond surtout à une question qui n'en avait pas : **85 des 86 décisions d'architecture portent la
mention « Accepté »** et une seule est marquée « remplacée », alors que **22 ont été amendées** par
une décision plus récente — information qui ne figurait sur aucune des fiches concernées. L'atlas la
calcule, et confronte au passage les centaines de modules et de symboles que ces décisions promettent
au code réellement présent. Ce n'est pas une documentation de plus à tenir : tout y est **regénéré
depuis les fichiers du projet**, et la vérification automatique échoue si l'affichage ne correspond
plus aux sources. Détail dans
[`2026-08-15-16h48-l-atlas-du-projet.md`](2026-08-15-16h48-l-atlas-du-projet.md).

Le **16/08/2026**, l'atlas a gagné une page **« L'avancement »** : les US regroupées par jalon avec
leur état, l'ordre dans lequel les grands chantiers peuvent s'enchaîner, la dette encore ouverte, et
une fiche par US qui rassemble ce que les quatre documents de suivi en disent. Surtout, il **refait
lui-même les comptes** au lieu de recopier ceux qui sont écrits — et il refuse de valider tant qu'un
écart subsiste. Il a trouvé **trois erreurs réelles le jour même** : un compteur de jalon qui
annonçait 12 US faites sur 15 quand il y en avait 16 dont 14 faites ; deux US **livrées** qui
n'apparaissaient dans aucun tableau de suivi ; et deux dettes différentes portant le même numéro,
arrivées sur `main` sans que rien ne s'en aperçoive. Détail dans
[`2026-08-16-16h19-l-avancement-qui-se-verifie-lui-meme.md`](2026-08-16-16h19-l-avancement-qui-se-verifie-lui-meme.md).

Le **16/08/2026** toujours, l'atlas a cessé de ne lire que des documents : la page **« La carte du
code »** lit le **code**. Elle compte les 827 liens entre les morceaux du programme et **refuse de
valider** si l'un d'eux remonte le courant — la règle de construction du projet (« tout pointe vers
le cœur métier ») n'était vérifiée automatiquement que pour le cœur métier lui-même ; les quatre
autres sens ne l'étaient par rien. Aucun ne remonte aujourd'hui : le verrou arrive à temps. La même
page a mesuré, côté écrans, que **19 des 44 morceaux** sont pris dans un même nœud de dépendances
croisées — plus aucun ne peut être lu ni testé seul. Rien n'est corrigé : **quatre chantiers** ont
été écrits et rangés en attente d'arbitrage. Détail dans
[`2026-08-16-18h02-la-carte-du-code.md`](2026-08-16-18h02-la-carte-du-code.md).

---

## Ce qui a été construit, par blocs

### 1. Les fondations (socle technique) — *terminé*

Tout l'échafaudage sur lequel le reste s'appuie est en place et verrouillé :

- Le **monorepo** (backend Python + frontend React) avec les outils qualité — formatage, typage
  strict, linters — vérifiés automatiquement **avant chaque commit** et en **intégration continue
  bloquante**. Rien de non conforme ne peut entrer.
- L'**architecture en couches** avec son garde-fou : le cœur métier ne peut importer aucun framework,
  c'est vérifié par un test. C'est ce qui garantit que le moteur du tournoi reste pur et testable.
- La **base de données** (SQLite) avec un **writer unique** : toutes les écritures passent par une
  file d'attente, une seule à la fois, pour éviter la corruption quand 30 tablettes écrivent ensemble.
- Le **canal temps réel** (WebSocket) qui diffuse un événement dès qu'une écriture est validée.
- Le **shell React** (gestion de l'état serveur, de l'état d'interface, client temps réel) et un
  **exécutable de développement** qui sert l'application façon production.

### 2. Configurer un tournoi — *terminé*

Tout ce qu'il faut pour préparer un tournoi avant le jour J. **Depuis le 31/07/2026, ce matériel
appartient au club, plus à un tournoi** : catégories, blasons et déroulés types se préparent une fois
dans l'Atelier et vivent d'une année sur l'autre ; monter un tournoi en prend une **copie**, qu'on
ajuste sans rien changer ailleurs — et une modification qu'on veut garder se **remonte** au club d'un
clic (« Rendre permanent »). Choix assumé de la copie plutôt que du lien : un réglage changé en 2027
ne doit pas réécrire le tournoi 2026 déjà archivé. Détail dans
[`2026-07-31-00h03-briques-du-club.md`](2026-07-31-00h03-briques-du-club.md).

- **Créer, éditer et lister des tournois**, avec un **cycle de vie enrichi à 7 statuts** (brouillon →
  prêt → en cours ⇄ en pause → terminé → archivé, plus annulé). Passer « prêt » exige **au moins un
  départ**, et on ne peut plus retirer le dernier créneau d'un tournoi déjà lancé. Plusieurs tournois
  peuvent être « en cours » en même temps (intérieur + extérieur).
- **Les catégories** (CRUD, pré-chargement des catégories officielles FFTA salle, éligibilité sur
  plusieurs tranches d'âge).
- **Les blasons** (la cible en papier) : taille, capacité, et les valeurs de score admises.
- L'**association catégorie ↔ blason**, désormais **pré-remplie par la FFTA** : pré-charger les
  catégories crée aussi les **quatre blasons** prévus à 18 m (80, 60, 40 cm et triple 40) et relie
  **chaque catégorie au sien** (les U11 sur 80 cm, les adultes sur 40, les poulies sur triples…).
  Plus besoin de se demander « par défaut, ça vaut quoi ? » ni de tout saisir à la main — et le
  blason **hérité** s'affiche à côté de chaque archer et sous la catégorie qu'on choisit à
  l'inscription. Tout reste modifiable. Détail dans
  [`2026-07-28-09h54-blason-par-defaut-des-categories.md`](2026-07-28-09h54-blason-par-defaut-des-categories.md).
- Les **gabarits de salle** (le plan des cibles, réutilisable et ajustable).
- Les **déroulés types** (« FFTA officiel 18 m », « Format club ») : appliqués à un tournoi, ils en
  **créent les phases** ; le déroulé d'un tournoi déjà composé peut à l'inverse être enregistré comme
  format du club. Depuis le 01/08/2026, un écran **« Composer un déroulé »** permet de les
  **fabriquer de bout en bout** dans l'Atelier — au lieu de devoir monter un tournoi pour obtenir un
  modèle —, de les **voir en schéma**, de savoir si le déroulé tient debout, et de le **faire
  tourner** sur des archers fictifs. Détail dans
  [`2026-08-01-19h30-composer-un-deroule.md`](2026-08-01-19h30-composer-un-deroule.md).
- Le **barème de qualification** et le **grain de validation** d'une phase.
- Le **tarif par départ** (le montant d'inscription).
- L'**import en masse du référentiel des clubs** (une liste collée, un club par ligne, avec un
  compte-rendu de ce qui a été ajouté, de ce qui était déjà connu et des lignes vides).

### 3. Les inscriptions — *terminé pour l'essentiel*

- Le **référentiel des clubs**.
- **Créer, éditer, supprimer un archer**.
- Configurer les **départs** (les créneaux de tir) et **inscrire un archer** sur des départs. Un
  créneau porte un **état de cycle de vie** (ouvert / lancé / clos), affiché par un **badge** et
  **déduit tout seul** du tir réel : tant que personne n'a tiré il reste **ouvert** (librement
  éditable) ; dès qu'une flèche est validée il passe **lancé**, puis **clos** quand tout le monde a
  fini. Modifier ou supprimer un créneau **lancé/clos** demande alors une **confirmation chiffrée**
  (« ce créneau est lancé, N archers ont tiré ») — on ne détruit plus une session de tir par mégarde.
- **Contrôler les quotas** (fait en avance de phase).
- Le **calcul du montant dû** par un archer.
- Le **suivi des paiements** : un écran « Paiements » montre, **par archer** (dû / payé / reste,
  filtrable) et **par club** (mêmes totaux + détail), qui a réglé. On marque un paiement à la ligne,
  ou d'un geste **tout un archer** ou **tout un club** (règlement groupé) ; chaque marquage laisse une
  **trace** dans le journal d'audit (c'est de l'argent). Pas d'encaissement en ligne : c'est un statut.
- **Rembourser une inscription payée annulée** : quand une inscription **déjà réglée** est effacée
  (archer désinscrit, ou créneau supprimé), la somme encaissée ne disparaît pas — elle passe dans un
  **registre de remboursements** (onglet « Remboursements » de l'écran Paiements) qui garde le nom de
  l'archer, le créneau et le montant, **même si le créneau a été supprimé**. L'organisateur marque
  chaque poste **remboursé** (argent rendu) ou **reporté** (réaffecté), acte **tracé** au journal. Et
  désinscrire un archer **payé** demande désormais une **confirmation chiffrée** (« 8,10 € à
  rembourser ») — on ne fait plus disparaître de l'argent par mégarde. Détail dans
  [`2026-07-29-09h53-rembourser-une-inscription-payee.md`](2026-07-29-09h53-rembourser-une-inscription-payee.md).
- **Détecter et fusionner les doublons** : un écran « Doublons » repère les fiches qui désignent
  probablement le même archer saisi deux fois — mêmes nom/prénom/club, ou rapprochement approximatif
  (faute de frappe, prénom abrégé) classé « à vérifier ». L'organisateur choisit la fiche à **garder** ;
  l'autre y est **fusionnée** (ses inscriptions et scores sont repris) puis supprimée. Rien n'est perdu,
  et le geste demande une confirmation explicite.

*Restent à venir : import de fichiers d'inscription.*

### 4. Les rôles et l'accès — *socle en place*

- **Consultation publique ouverte** (n'importe qui sur le réseau peut regarder) et **accès
  administrateur protégé** (les écritures sont derrière un mot de passe).
- Les **scoreurs** du tournoi (définition et session de travail).
- Un **journal d'audit métier** qui trace les actions importantes.
- Le principe : les écritures ont d'abord été **toutes fermées à l'admin**, et seront **élargies**
  ensuite rôle par rôle (le scoreur, l'archer) — sans créer de route parallèle.

### 5. Le placement des archers — *base en place*

- **Placement automatique** des archers sur le plan de cibles.
- **Ajustement manuel** par glisser-déposer.
- **Alerte par calcul d'impact** avant de régénérer un plan : l'appli **ne prévient que quand ça
  compte** — silence tant qu'aucun score n'existe, et **alerte chiffrée** (« 156 archers vont être
  replacés ; 4 cibles ont déjà des scores, conservés ») quand la partie est engagée, où il faut alors
  **taper un mot** pour confirmer. Chaque replacement de ce type laisse une **trace** dans le journal.
- **Mixité des clubs (≥ 2 clubs par cible)** : le placement automatique **cherche à mêler les clubs**
  sur chaque cible (équité — éviter qu'un seul club occupe une cible entière), sans jamais bloquer ni
  passer avant l'essentiel (place, hauteur de butte). Quand il **ne peut pas** garantir deux clubs
  (un seul club présent, ou club **inconnu** — jamais deviné), la cible est **signalée** par un
  **badge ambre** et une **bannière** récapitulative sur l'écran de placement : à l'organisateur de
  décider s'il ajuste à la main.
- **Placer les duellistes côte à côte** : pour une **phase de duels** (élimination directe), un écran
  **« Plan de duels »** place les **deux adversaires d'un match** (du 1er tour) **l'un à côté de
  l'autre** — même cible, positions voisines — pour faciliter la conduite des tirs. C'est le classement
  qui décide qui affronte qui (recalculé, déterministe) ; seule la **pose** est enregistrée et
  **ajustable au glisser-déposer**. Même logique que la mixité (une **préférence**, jamais un blocage) :
  les duels qu'on n'a pas pu rapprocher sont **signalés** (badge ambre « duel non côte à côte » +
  bannière). *(MVP : premier tour, ensemencement au classement scratch, gabarit du tournoi ; les duels
  d'équipes viendront plus tard.)*

- **Retour de génération lisible & position visible** (dernier fait marquant, 27/07) : sur l'écran de
  placement, le bouton **« Générer le plan »** ne *paraît plus muet* — il affiche « Génération… »
  pendant qu'il travaille puis **confirme ce qu'il a produit** (tous placés, ou le nombre en réserve,
  ou « aucun archer à placer » si le départ est vide) ; en cas d'échec, un message lisible s'affiche.
  Et la **position** de chaque archer (A, B, C, D…) est maintenant **affichée côté organisateur**,
  comme côté public — elle n'apparaissait que sur les cases vides. Détail dans
  [`2026-07-27-23h16-retour-generation-et-position-au-placement.md`](2026-07-27-23h16-retour-generation-et-position-au-placement.md).

*Restent à venir : la séparation catégorie/blason et le placement intégral 1→N du grand format.*

### 6. La saisie des scores de qualification — *terminé, et robuste*

C'est le cœur du jour J, et c'est le travail le plus récent :

- **Rattacher une tablette à sa cible** en scannant un **QR code**, avec impression des QR de cible
  et des codes scoreurs.
- Un **poste de cible peut saisir sans s'identifier** (le bénévole n'a pas de compte à créer).
- La **saisie en temps réel** : les volées et flèches se saisissent sur une grille tactile, le total
  se met à jour, et le score validé apparaît en direct sur les autres écrans.
- **La résilience réseau** (dernier fait marquant, 20/07) : si le wifi saute en pleine saisie, rien
  n'est perdu — les volées sont mises en file et **renvoyées automatiquement** au retour du réseau,
  sans doublon, et un **voyant de connexion** indique en permanence l'état. Détail dans
  [`2026-07-20-00h35-saisie-resiste-aux-coupures.md`](2026-07-20-00h35-saisie-resiste-aux-coupures.md).

### 7. Les documents imprimables — *les premières listes du jour J*

- Le **socle PDF** et la **feuille de marque**.
- L'**impression des QR de cible et des codes scoreurs** (branché sur la saisie ci-dessus).
- Un écran **« Exports »** avec les **deux premières listes à imprimer** (dernier fait marquant,
  25/07) : la **liste de placement** (qui tire où — triable par cible ou par nom, et filtrable sur un
  seul départ) et la **liste club & paiement** (par club : départs, dû, réglé ou non, totaux). Détail
  dans [`2026-07-25-20h08-listes-imprimables.md`](2026-07-25-20h08-listes-imprimables.md).
  *Restent à venir : les classements et le déroulé horaire imprimables.*

### 10. Déployer le jour J — *l'application tient dans un fichier*

- **Un exécutable unique** (`kervignarc.exe`) embarque tout — interface, base de données, PDF — et
  se lance sans rien installer (ni Python, ni Node, ni internet). C'est la base concrète du jour J.
- Au **premier lancement**, il **crée sa base de données** (vide, prête) à côté de lui, puis s'ouvre
  sur le **réseau local** (port fixe). Les tablettes y accèdent par l'**adresse IP** affichée **ou**
  par un **nom mémorisable**, `kervignarc.local`, que le serveur annonce lui-même sur le réseau.
- La **procédure complète** (fabriquer le fichier, brancher le routeur, connecter les tablettes,
  pièges à éviter) est écrite dans [`docs/deploiement.md`](../docs/deploiement.md). Détail dans
  [`2026-07-26-12h26-deploiement-jour-j.md`](2026-07-26-12h26-deploiement-jour-j.md).
- **Sauvegardes automatiques & archive** (26/07) : pendant que l'appli tourne, elle dépose **toute
  seule**, à intervalle régulier, une **copie horodatée** de sa base dans un dossier `backups/`
  (protection de fond, sans écran, avec purge des plus anciennes). Et un écran **« Archive »** produit
  à la demande un **paquet ZIP** de fin de tournoi — l'organisateur **coche** ce qu'il emporte : base
  complète, données en **CSV** (tableur), et documents **PDF** (feuilles de marque, listes), avec un
  manifeste. Détail dans
  [`2026-07-26-13h55-sauvegarde-et-archive.md`](2026-07-26-13h55-sauvegarde-et-archive.md).
- **Accès réseau en développement + QR de cible à l'écran** (dernier fait marquant, 27/07) : le
  lancement de développement s'ouvre lui aussi **sur le réseau local** (comme le fichier exécutable),
  et affiche au démarrage l'**adresse à taper depuis une tablette** — on peut donc tester le jour J
  depuis un vrai appareil. Et l'écran **Postes de cible** montre désormais, pour chaque cible, son
  **QR de rattachement à l'écran** (agrandissable pour être scané), en plus du code : plus besoin
  d'imprimer pour rattacher une tablette. Détail dans
  [`2026-07-27-21h01-acces-reseau-et-qr-a-l-ecran.md`](2026-07-27-21h01-acces-reseau-et-qr-a-l-ecran.md).

### 8. L'interface d'administration — *rangée en trois axes de travail*

- L'administration s'ouvre sur **trois cartes** — **Atelier** (fabriquer ce qui ressert d'une année
  sur l'autre, **sans tournoi**), **Pilotage** (faire tourner la journée), **Gestion**
  (inscriptions, paiements, exports). On entre dans un axe et on ne voit **que** ses écrans. Le
  rangement précédent suivait le *temps du tournoi* et, en pratique, l'ordre de développement : il
  alignait 25 entrées dans deux tiroirs et coupait en morceaux les activités qui durent. Détail dans
  [`2026-07-30-19h05-admin-en-trois-axes.md`](2026-07-30-19h05-admin-en-trois-axes.md).
- **Chaque écran a une adresse** (`…/admin/12/pilotage/supervision`) : un rafraîchissement ne fait
  plus perdre son écran ni son tournoi, un lien s'envoie, et plusieurs écrans s'ouvrent côte à côte
  pour vérifier le produit. Les quatre mondes ont la leur — `/public`, `/scoreur`, `/cible`,
  `/admin` — et **les QR déjà imprimés continuent de fonctionner**.
- L'**ossature de navigation** de l'application admin (la coquille dans laquelle les écrans viennent
  se loger).
- Un **écran d'accueil qui demande le rôle de l'appareil** au premier lancement — **Tablette**,
  **Téléphone (public)**, **Scoreur** ou **Administration** — puis **s'en souvient** et va droit au bon
  écran ensuite. Le spectateur ne peut plus accéder par mégarde au mot de passe admin ou au code
  scoreur ; on change de rôle par un lien discret. Détail dans
  [`2026-07-21-22h10-choisir-son-role-au-lancement.md`](2026-07-21-22h10-choisir-son-role-au-lancement.md).
- Un **accueil-tableau de bord par tournoi** (dernier fait marquant, 28/07) qui « raconte l'histoire »
  du tournoi : une **frise des 7 étapes** de sa vie (brouillon → prêt → en cours → terminé → archivé,
  plus en pause / annulé) avec le statut courant surligné et les **boutons d'action** du moment
  (marquer prêt, démarrer, mettre en pause, terminer, archiver, annuler) ; dessous, des **chiffres-clés**
  (inscrits, réglés, postes en ligne), une **checklist « à faire »** et les **alertes**. Il ne fait
  qu'**assembler** des informations déjà là (complétude, supervision, paiements). Au passage, un bug est
  corrigé : le pilotage ne connaissait que 3 états et se **bloquait** dès « prêt »/« en pause » — la
  frise couvre désormais les 7 partout. Détail dans
  [`2026-07-28-11h04-accueil-tableau-de-bord.md`](2026-07-28-11h04-accueil-tableau-de-bord.md).
- Une **aide contextuelle sur chaque écran** (dernier fait marquant, 28/07) : en tête de tout écran
  d'administration, un bouton **« ⓘ Aide »** discret, replié par défaut, qui **se déplie au toucher**
  pour expliquer, en langage d'organisateur, **ce qui se saisit là et à quoi ça sert** ensuite. Pensé
  pour la tablette (ouverture au toucher, jamais au survol). C'est de l'affichage : aucun champ ni
  règle ajoutés. Réponse au retour de démo « je ne veux pas de formation ». Détail dans
  [`2026-07-28-12h03-aide-contextuelle-par-ecran.md`](2026-07-28-12h03-aide-contextuelle-par-ecran.md).

### 9. Suivre la qualification et l'afficher au public — *en place*

Ce qui transforme la saisie brute en tournoi qu'on suit en direct, dernier bloc construit :

- **Superviser les postes de saisie** : l'organisateur voit, sur un seul écran, l'état de chaque
  cible (rattachée, en ligne, en retard, à valider) — *un poste figé ne se plaint pas, seule la
  supervision le révèle*.
- **Le classement de qualification** : à partir des scores validés, le classement se calcule et se
  met à jour tout seul, par catégorie.
- **Les vues publiques** : n'importe qui sur le réseau consulte, sans authentification et depuis son
  téléphone, les **classements**, le **plan de cibles** (qui tire où), le tout **en direct** — chaque
  validation met les écrans à jour sans rien rafraîchir.
- **Suivre des archers** : on cherche un archer par son nom, on le **suit**, et l'application mémorise
  ce choix sur l'appareil (sans compte) — à la réouverture, elle affiche directement **sa cible / sa
  position / son départ**, à jour en direct. On peut en suivre plusieurs.
- **Le déroulé du tour en direct** : sous la place de l'archer suivi, sa **feuille de marque se remplit
  toute seule** — chaque volée avec ses flèches et son total, marquée **« en attente »** (en ambre,
  score provisoire) tant que le scoreur ne l'a pas confirmée, puis **« validé »** (en vert). Le public
  voit donc le tour se dérouler **avant** validation (choix assumé) ; le total « officiel » reste celui
  du classement, et la vue ne révèle jamais qui a saisi.
- **La complétude du tournoi** : un écran répond à « **qu'est-ce qui manque pour finir ?** » — le
  **sportif** (qualification cible par cible, classement) et le **hors sportif** (paiements) comptés
  **séparément**, chacun avec son état (terminé / à finir / en attente). L'écran dit **ce que
  « terminer » va figer** (le sportif ; les paiements restent modifiables) et, au moment de terminer —
  la seule action irréversible —, **chiffre ce qui reste** avant de laisser confirmer. Détail dans
  [`2026-07-22-00h40-completude-du-tournoi.md`](2026-07-22-00h40-completude-du-tournoi.md).
- **Rechercher un archer depuis n'importe où** : un champ de recherche **toujours présent en haut de
  la barre de navigation admin** — quel que soit l'écran affiché, le bénévole de la table
  d'organisation tape un nom et voit **immédiatement où l'archer tire** (départ, horaire, cible,
  position, pour chaque créneau), sans quitter sa page. C'est le **4ᵉ canal** pour répondre à « je tire
  où ? » (après les tablettes, les téléphones du public et « ma journée »). Détail dans
  [`2026-07-22-14h39-rechercher-un-archer.md`](2026-07-22-14h39-rechercher-un-archer.md).
- **Les écrans de salle** : un ou plusieurs écrans branchés dans le gymnase, rattachés **comme une
  tablette de cible** (même code, même geste), qui font défiler tout seuls classement, plan de cibles,
  affectations, **tableaux de duels**, palmarès et suivi du déroulé — chacun avec son propre défilé. Ils apparaissent dans la console de
  supervision (*un écran figé ne se plaint pas non plus*), et l'organisateur peut leur **imposer une
  vue à distance** avec une durée, après quoi l'écran **reprend son défilé sans que personne y
  retourne**. Détail dans
  [`2026-08-02-00h29-ecran-de-salle-et-suivi-du-deroule.md`](2026-08-02-00h29-ecran-de-salle-et-suivi-du-deroule.md).
- **Les tableaux de duels en direct** (dernier fait marquant, 04/08) : le public gagne un onglet
  **« Tableaux »** et voit enfin **contre qui** on tire. Deux façons de lire le même arbre — **« Mon
  chemin »**, le parcours de chaque archer suivi tour par tour, et le **tableau complet** groupé par
  tour. L'écran de salle sait projeter la même chose, sur le tableau qui se joue. Détail dans
  [`2026-08-04-22h40-tableaux-de-duels-en-direct.md`](2026-08-04-22h40-tableaux-de-duels-en-direct.md).
- **Le plan du tournoi qui se remplit** : le schéma en cases et flèches composé à l'atelier devient
  un **suivi** — phase terminée / en cours / à venir, tour en cours, duels joués sur duels attendus.
  Le **même dessin** à trois endroits (atelier, poste de l'organisateur, écran projeté) : on ne
  réapprend pas à le lire en changeant d'écran.

*Les **affectations du prochain tour** (E07US008) et les **tableaux de duels** (E07US005) sont
désormais livrées : ce paragraphe annonçait leur absence, il n'a plus lieu d'être. Ce qui reste hors
de portée du public tient à ce que l'application ne planifie pas : il n'y a **pas d'horaire
prévisionnel** de duel — c'est le lancement d'un tour par l'organisateur qui fait partir les
rencontres.*

### 11. Scorer les duels — *premier écran du chantier duels*

- **Saisie en duels (écran scoreur)** : une fois sa session ouverte, le scoreur choisit une **phase de
  tableau**, voit la **liste des duels groupés par tour** (finale en tête, chacun avec son état : à
  saisir / en cours / à valider / validé), en ouvre un et le score **manche par manche** sur un pavé
  tactile qui ne propose que les valeurs autorisées du blason. Le **format** est décidé par le serveur
  (système de **sets**, ou **cumul** pour l'arc à poulies) et l'écran s'y adapte ; le **score courant**
  s'affiche à chaque manche. À égalité, un **barrage** (une flèche chacun) départage — avec
  **désignation manuelle** du plus près du centre si les flèches valent pareil. La **validation** du
  vainqueur **verrouille** le duel et le fait **avancer au tour suivant**, jusqu'au **podium**. Comme
  la qualification, la saisie **résiste aux coupures réseau** (file + renvoi automatique) et refuse
  d'écrire sur un duel dont les adversaires auraient changé. Détail dans
  [`2026-07-27-11h44-scorer-un-duel.md`](2026-07-27-11h44-scorer-un-duel.md). *(Le moteur — tableau,
  scoring, progression — avait été livré juste avant, sans écran.)*
- **Abandon / disqualification** : depuis son espace, le scoreur peut **déclarer** qu'un archer
  **abandonne** ou est **disqualifié**, **en qualification comme en duels**. En qualification, un
  **abandon** relègue l'archer en fin de classement (il reste rangé, son score s'affiche, badgé
  « Abandon ») et une **disqualification** l'en **sort** (plus de rang, score conservé) ; en duels,
  le forfaitaire **cède** son match et l'adversaire passe. Contrairement à la **suppression** (qui
  efface tout), le forfait **préserve les flèches déjà tirées** — c'est ce qui les distingue. Le
  geste est **réversible** (« Annuler ») tant que le tournoi n'est pas terminé, et **tracé** au
  journal d'audit. Détail dans
  [`2026-07-27-13h33-abandon-et-disqualification.md`](2026-07-27-13h33-abandon-et-disqualification.md).
- **Feu vert : voir ce qui est prêt, puis lancer le tour** (dernier fait marquant, 28/07) : un écran
  admin **« Feu vert »** (groupe « Jour J ») s'attaque au **temps mort entre deux tours**. Il montre
  **en continu**, duel par duel du prochain tour, s'il est **prêt à partir** — ses **adversaires
  sont-ils connus**, leur **cible attribuée** — et **nomme** ce qui bloque (« en attente du duel n°2 »,
  « cible non attribuée ») plutôt que de seulement le signaler. Rien n'est empêché : l'écran montre,
  l'organisateur décide. Un **bouton chiffre** ce qu'il déclenche (« Lancer — 2 duels · cibles 1 ·
  4 archers prévenus ») et **fait partir** les duels prêts d'un geste ; l'acte est **tracé** au journal.
  Le signal est **émis** vers les postes et écrans — mais les **écrans qui l'afficheront aux archers**
  (tablette, public, salle) ne sont **pas encore construits** : ils le recevront avec leurs propres US.
  Détail dans [`2026-07-28-22h04-feu-vert-lancer-le-tour.md`](2026-07-28-22h04-feu-vert-lancer-le-tour.md).

### 12. Peupler et rejouer — le jeu d'essai — *première brique*

- **Générer des inscrits & instancier des scénarios** (dernier fait marquant, 28/07) : un écran
  admin **« Jeu d'essai »** permet de **remplir un tournoi sans tout saisir à la main**. Deux gestes :
  **peupler** le tournoi courant d'un **nombre choisi** d'archers factices mais réalistes (noms,
  clubs, catégories cohérentes), ou **instancier un scénario** d'un clic — **petit**, **gros** ou
  **multi-format** — qui crée un **nouveau tournoi complet et prêt à lancer** (catégories, départs,
  archers inscrits). Ce sont de **vraies données** enregistrées (à réserver aux tournois de test) ;
  une **graine** permet de **rejouer exactement le même jeu**. Sert la **démo** et la **QA**. Détail
  dans [`2026-07-28-13h36-jeu-d-essai-generer-des-inscrits.md`](2026-07-28-13h36-jeu-d-essai-generer-des-inscrits.md).
- **Rejouer le moteur sans rien enregistrer** — le **moteur de simulation** (E15US002) existe
  **sous le capot** : il rejoue un tournoi (classement → tableaux) **avant démarrage** sur des copies
  **en mémoire**, sans jamais toucher la vraie base — un garde-fou refuse d'ailleurs de simuler un
  tournoi déjà lancé. C'est une brique **technique, sans écran**.
- **Le cockpit de simulation** (dernier fait marquant, 28/07) : l'**écran** qui pilote ce moteur, dans
  la coquille admin (« Simulation »). Un **robot** génère des scores plausibles (déterministes par
  graine) et fait avancer le tournoi tout seul — **pilote automatique pausable** — jusqu'au classement
  et au podium. **En pause**, l'organisateur peut **saisir à la place d'un rôle** (une volée comme la
  cible, un vainqueur comme le scoreur) sur l'action que le robot allait jouer, puis **rendre la main**.
  Une **navbar** bascule entre les vues **cible / archer / scoreur / public** du tournoi simulé, diffusé
  sur un **canal séparé** du temps réel réel. **Rien n'est enregistré** : idéal pour **démontrer** le
  déroulé ou **vérifier** que tout s'enchaîne. **EPIC-15 est ainsi terminée.** Détail dans
  [`2026-07-28-19h48-cockpit-de-simulation.md`](2026-07-28-19h48-cockpit-de-simulation.md).

---

## Ce qui n'existe pas encore (les grands chantiers restants)

Dans l'ordre de valeur prévu par le backlog :

1. **Finir le tournoi de qualification** : l'appli publique ouverte directement sur **« ma journée »**
   (« c'est moi » mémorisé) et les **classements imprimables**. C'est **le dernier reliquat** de J1 :
   le jalon est sinon **terminé**.
   *(Supervision des postes, classement, vues publiques, suivi des paiements, complétude du tournoi,
   recherche d'un archer, **premières listes imprimables** (placement, club & paiement), la **mise en
   réseau / déploiement en un fichier** (E11US001) et les **sauvegardes / archive** (E11US003) :
   faits — cf. blocs 3, 7, 9 et 10.)*
2. **Les duels** (phases finales) : l'arbre d'élimination directe, la saisie en duels (sets/cumul,
   barrage, podium) et l'**abandon / disqualification** sont **faits**, et la **bascule de tour** est
   **amorcée** — l'écran **« Feu vert »** montre ce qui est prêt et **lance** les duels prêts
   (E12US002). Ses **quatre canaux récepteurs sont désormais livrés** : la **tablette de la cible**
   (E04US018), le **téléphone de l'archer** et le **panneau collectif des affectations** (E07US008),
   et l'**écran de salle** (E07US004). Restent, pour ce jalon, le **barrage de tir** (E06US003) et le
   **podium / l'agrégation des rangs** (E06US004). *L'organisateur **compose la séquence de phases**
   de son tournoi (E05US001), place les duellistes, le scoreur score les duels, l'organisateur
   **lance le tour**, et l'archer voit sa destination — sur la tablette de sa cible s'il est encore
   là, sur son téléphone s'il est parti.*
3. **Le placement intégral 1→N** (le grand format du classeur 120) est **fait** ; l'**écran de salle**
   aussi — reste à l'habiller de l'**identité visuelle du tournoi** (E01US016).
4. **Confort et robustesse** : import inscript'arc, presets de barèmes, déroulé horaire, sauvegarde
   et restauration.

Un chantier transverse a été acté à l'entretien du 18/07/2026 : le **cycle de vie enrichi à 7 statuts**
est désormais **livré** (E01US017) ; restent le **vocabulaire de score configurable** et les
**épreuves par équipes** (nouvel EPIC-13, désormais dans le périmètre MVP), pas encore implémentés.

---

## Chiffres repères

- **113 US livrées** sur `main` (mergées, revues, CI verte) à la date du 16/08/2026, la dernière
  étant `E00US020` — la **carte du code de l'atlas** et son verrou sur le sens des dépendances. **`SUIVI-US.md` fait foi sur le compte exact** ; ce résumé le **reflète** et ne
  tient pas un second décompte.
  ⚠️ **Un `grep` sur `git log` ne donne pas ce chiffre**, et se tromper dans les deux sens se
  compense : `E00US016`, `E01US018` et `E01US019` ont un commit `docs(...)` dans `main` **sans une
  ligne de code** (elles sont ⬜), tandis qu'`E17US003` et `E17US004` ont été livrées sous la
  branche d'`E17US001` (PR #138) et n'apparaissent pas sous leur propre nom.
  **Quatre US sont *absorbées*** — leur capacité est livrée par une autre, elles ne comptent nulle
  part : `E12US004` (« tracer un forfait », par `E04US015`, qui livre l'abandon/DSQ en qualif *et*
  en duels — d'où un J2 de 14 et non 15), `E05US016` (par `E05US015`), `E05US018` et `E05US019`
  (par `E05US010` et `E01US023`). Après les
  **cinq bugs** de la démo du 27/07 (cycle de vie 7 statuts E01US017, horaire `HH:MM` E02US010, accès
  réseau LAN + QR E11US008, retour visuel de génération + position A..D E03US011, blason FFTA par
  défaut E01US022), le **lot démo a bouclé EPIC-14** (lisibilité admin : accueil-tableau de bord
  E14US001 + aide contextuelle par écran E14US002) **et EPIC-15** (jeu d'essai & simulation) : le
  **générateur d'inscrits + scénarios rejouables** (E15US001), le **moteur de simulation éphémère**
  (E15US002, technique, sans écran) puis le **cockpit de simulation** (E15US003, bot pausable + reprise
  en main + canal isolé). La séquence **J2** a ensuite repris avec le **feu vert + lancement d'un tour**
  (E12US002), le **remboursement d'une inscription payée annulée** (E08US005), puis le **panneau de
  routage sur la tablette** (E04US018). Enfin, l'**administration a été rangée en trois axes
  d'activité** (E14US003) et les **briques de configuration sont devenues le patrimoine du club**
  (E01US023), ce qui rend l'axe « Atelier » réellement hors tournoi. Le **chantier du moteur de
  phases** s'est alors ouvert par son verrou : le **placement intégral 1→N** (E05US010), qui livre la
  cascade de routage, les **sources multiples et relatives**, et l'**oracle 120** — le rejeu
  automatique du classeur réel, jusqu'ici cité par la doctrine mais jamais outillé. Il s'est poursuivi
  par le **catalogue de types de phase** (E05US015) : six formats de plus à l'écran « Phases »
  (échauffement, barrage, poules, **Big Shoot Off**, système suisse, colline), chacun expliqué d'une
  ligne, plus le **handicap** de l'archer et le **repêchage**. La question **Q9** du cahier des
  charges — « qu'est-ce qu'un Big Shoot Off ? » —, bloquante depuis l'origine du projet, est
  **fermée** : le commanditaire en a fourni la règle, comme celles des poules, de l'échauffement, du
  handicap, du système suisse, du King of the Hill, du Ladder et de la finale spectacle.
- **Retours du questionnaire de maquettes (04/08/2026)** : 36 planches relues, verdict par écran.
  **Quatre écrans refusés** en l'état (A07 phases, A10 plan de salle, A14 complétude, P03 classements
  publics), vingt validés avec réserves. Le **lot « front seul »** a été livré le 05/08/2026 — **hors
  US numérotée**, d'où un compte d'US inchangé : il ne portait aucune décision métier ni changement de
  domaine. Le reste est spécifié en **douze US** dans [`stories/E16`](../stories/E16-retours-maquettes.md)
  ([EPIC-16](../epics/EPIC-16-retours-maquettes.md)), et les retours **écartés** y sont consignés avec
  leur raison — aucun questionnaire ne reste sans suite. **Premier écran refusé relevé : A10 (plan de
  salle)**, par E16US001 — le refus ne portait que sur le **vocabulaire**, désormais arbitré. **A14
  (complétude) a été levé le 07/08/2026** par E16US003, et **P03 (classements publics) le 08/08/2026**
  par E16US004 — la bascule « mes archers / tout » qu'il réclamait vaut désormais pour tout l'onglet
  public, pas seulement pour le classement. Reste **un** écran refusé : A07 (phases), à recadrer avant
  d'être pris (ADR-0076 en a changé la nature).
- **Les maquettes montrent désormais l'écran entier (05/08/2026)** — **hors US numérotée**, support de
  conception, compte d'US inchangé. Le commanditaire ne voyait *« que des composants de pages »* :
  chaque planche était bornée à 430 px et **aucune ossature n'était dessinée** (ni navigation, ni
  bandeau, ni en-tête). Les 36 écrans sont maintenant rendus **à la taille réelle de leur appareil** —
  PC 1600 × 900, tablette 1280 × 800, vidéoprojecteur 1920 × 1080, téléphone 390 × 844 — soit
  **151 écrans pleins**, avec une **hauteur fixe** qui fait enfin exister la ligne de flottaison :
  43 planches signalent ce qui tombe sous le bord de l'écran. Les 36 questionnaires repartent sur une
  trame en onze sections ; les réponses du tour 1 sont **archivées, pas effacées**
  (`maquettes/questionnaires/tour-1-2026-08-04/`). L'exercice a fait remonter **deux écrans qui
  n'existaient nulle part** — le *barrage* (égalité 5–5 en duel) et le *conflit de saisie* (deux postes
  sur la même volée) —, un **écran livré jamais maquetté** (la création du compte administrateur au
  tout premier lancement), et une **erreur de fond sur A07** : « 1/8 » et « 1/4 » y étaient présentés
  comme des phases alors qu'une seule phase porte tout le tableau.
- **L'application a pris les couleurs du club (05–06/08/2026, E17US001 → E17US004)** — quatre US, et
  le changement le plus **visible** de la semaine. En comparant l'outil aux maquettes validées, le
  commanditaire a constaté qu'ils n'avaient « rien à voir ». La cause n'était pas un écran mais **la
  palette, jamais posée** : le front tournait encore sur le décor du tout premier squelette
  technique — accent violet, fond blanc, police système —, parce que les « US design » annoncées
  dans le code n'avaient jamais été écrites, et qu'**aucune des 98 US livrées n'avait de raison de
  s'en apercevoir** (chacune était conforme à son propre cahier). Ont suivi, dans l'ordre :
  la **charte du club** posée une fois pour toutes (anthracite, rouge club en aplat seulement,
  alerte **ambre**, thème sombre par défaut) ; le **catalogue de composants** — boutons, champs,
  cartes, onglets, pastilles — aligné sur les **formes** des planches ; l'**écran de connexion** et
  l'**accueil** conformes à leur maquette ; et la **supervision des tablettes** passée en **grille de
  tuiles**, le jour J, pour repérer d'un coup d'œil celle qui s'est tue au lieu de lire trente
  lignes. Décision de fond au passage : **les maquettes font foi**
  ([ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)) —
  un écart entre un écran et sa planche est désormais un **défaut constatable**, plus une divergence
  que personne n'avait à relever. **Deux points attendent une réponse du commanditaire** : embarquer
  la police du dossier de maquettes (elle ne se chargera pas le jour J, qui tourne sans internet) et
  la **couleur d'une action irréversible**, que la charte ne prévoit pas — aujourd'hui la même que
  celle d'un avertissement.
  *(⚠️ Ces quatre US étaient **absentes de ce résumé** jusqu'au 08/08/2026, alors que le tracker les
  affichait livrées. Un résumé plus court que le tracker est **périmé**, pas synthétique.)*
- **Le départ est devenu la portée sportive (07/08/2026, E01US025)** — une correction de fond, pas un
  écran. Une décision prise en **juillet 2025** (« un départ rejoue le tournoi ») n'avait été portée
  que par la logistique : le moteur est resté à la maille tournoi **treize mois**, produisant un
  classement de 400 là où il en fallait quatre de 100. En la corrigeant, un second défaut est
  apparu — le déroulé était **recopié** sur chaque créneau, donc libre de diverger en silence : il se
  définit maintenant **une fois**, et chaque départ n'en porte que l'avancement. Deux décisions
  d'architecture ([ADR-0075](../docs/adr/0075-le-depart-est-la-portee-sportive.md),
  [ADR-0076](../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)), deux
  migrations, et un **garde-fou mécanique** qui fait désormais échouer les tests si quelqu'un
  rebranche une phase sur le tournoi — c'est précisément ce qui manquait à la décision de 2025. Trois
  limites restent **tracées** plutôt que corrigées à la hâte : palmarès mono-départ (`DETTE-045`,
  dont la résorption demande un arbitrage du commanditaire), série unique par tournoi pour un archer
  inscrit sur deux créneaux (`DETTE-046`), et l'absence de vue d'ensemble des N classements.
  ⚠️ **Cette US a été spécifiée après avoir été écrite** : partie d'un constat de bug, elle n'avait
  ni fiche ni entrée au tracker. Ses critères d'acceptation décrivent donc le livré et valent comme
  non-régression, pas comme preuve que le besoin a été compris — c'est à la recette de le confirmer.
- Jalon **J0 (walking skeleton) : 100 %**. Jalon **J1 (qualification de bout en bout) : terminé
  (46/46)** — supervision, classement, vues publiques, suivi d'archers, déroulé du tour en direct,
  alerte par calcul d'impact, suivi des paiements, complétude du tournoi, recherche d'un archer,
  détection/fusion des doublons, **listes imprimables**, **déploiement en un fichier / mise en réseau**
  et **sauvegarde & archive** faits. *(Le confort « ma journée » ouverte sur « c'est moi » et les
  classements imprimables restent, hors décompte du jalon.)* Jalon **J2 (les duels) : terminé (14/14)**
  avec la **séquence de phases** (E05US001), les **politiques injectables** (E05US003), le **tableau
  d'élimination directe** (E05US005 — posé sur l'**abstraction Participant** E13US001), la
  **mixité des clubs au placement** (E03US006), le **placement des duellistes côte à côte**
  (E03US009), la **saisie en duels** (E04US013 — backend *et* **écran scoreur**), l'**abandon /
  disqualification** (E04US015 — qualif *et* duels), le **cycle de vie d'un départ** (E12US008), le
  **feu vert + lancement d'un tour** (E12US002), le **remboursement d'une inscription payée
  annulée** (E08US005) l'**affichage de la prochaine cible après validation** (E04US018), le **barrage de tir pour les places décisives** (E06US003) et le **palmarès** (E06US004), qui le referme.
- **Le club est enfin libre de son format (08/08/2026, E05US024)** — une correction de fond.
  L'organisateur pouvait déjà **composer** ce qu'il voulait : « les rangs 5 à 8 de mon tableau
  principal », autrement dit les battus des quarts. L'écran l'acceptait, le diagnostic le
  validait — mais **le moteur ne savait lire qu'un seul classement**, celui de la qualification. Tout
  prélèvement visant une autre phase était **ignoré sans rien dire**, et la phase récupérait *tous*
  les archers encore en lice : un tableau d'apparence normale, et faux, qui ne se serait vu que le
  jour J. Désormais chaque prélèvement est lu **dans la phase qu'il désigne**, sur autant de crans que
  le format en compte, et le seuil « il vous faut au moins N inscrits » suit la même chaîne au lieu de
  s'arrêter à la première phase. Et **ce qui n'est pas encore joué est annoncé comme tel** : une
  consolante composée le matin affiche « les places disputées ici ne sont pas encore connues »
  plutôt qu'une liste d'archers plausible et fausse — le défaut le plus dangereux qu'ait trouvé la
  relecture de cette US, le tableau affiché ayant le bon nombre d'archers et des noms crédibles.
  ⚠️ Les phases en système suisse et colline restent hors du dispositif : leur moteur existe mais
  rien ne l'appelle encore (E05US026, E05US027). ✅ Les **poules** y sont entrées le jour même, et le
  **Big Shoot Off** le 14/08/2026 — voir ci-dessous. ✅ La limite « une seule qualification par tournoi »,
  qui restait volontairement en place à cette date, **a été levée le lendemain par `E05US025`** (voir
  ci-dessous). Décision d'architecture :
  [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md).
- **Plusieurs tours de qualification dans un même tournoi (09/08/2026, E05US025).** Le format
  demandé par le club : 120 archers tirent 3×20, puis la moitié haute et la moitié basse rejouent
  3×15 chacune. L'application le refusait — non par règle de tir à l'arc, mais parce qu'un garde-fou
  posé quelques semaines plus tôt interdisait le cas au lieu de réparer les neuf endroits du code qui
  lisaient « **la** » qualification, dont deux ne désignaient pas la même. Désormais : **chaque tour
  a son barème** (l'écran « Barème & validation » liste une section par qualification), **chaque
  archer une feuille par tour** (une flèche du second tour ne peut plus atterrir dans le premier), et
  le **classement final va de 1 à 120** — la haute occupe les places 1 à 60, la basse 61 à 120. À
  connaître, et voulu : le premier de la basse reste **derrière** le dernier de la haute même s'il a
  mieux tiré, la place étant décidée par le tour qui a réparti les archers. Aucune médaille n'est
  décernée par une qualification : le podium se joue en finale. Corrigé au passage, un défaut connu
  depuis le 6 août — un archer inscrit sur **deux créneaux** n'avait qu'un emplacement pour ses
  flèches, sa seconde feuille écrasant la première. ⚠️ Le **plan de cibles reste commun** aux tours :
  les archers ne changent pas de cible entre le premier et le second. Décision d'architecture :
  [ADR-0082](../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md).
- **La finale spectacle se joue, et sa règle a changé (14/08/2026, E05US028).** Le « Big Shoot Off »
  était proposé à la composition sans mener nulle part, comme les poules avant lui. En préparant son
  écran, une contradiction est apparue : la fiche de l'US promettait un réglage que ni la règle ni le
  moteur ne connaissaient. Question posée au club, **règle élargie** : une finale sort **plusieurs**
  archers par tour, et le rythme se dit **tour par tour**. L'organisateur écrit donc une liste — « 4,
  2, 1 » — et le nombre de rescapés a **disparu des réglages**, puisqu'il se déduit de ce que la
  liste n'élimine pas. L'atelier montre la projection en direct (« à 12 archers : 12 → 8 → 6 → 5 »)
  et **nomme les manches qui ne se joueront pas** si l'effectif ne porte pas la liste : le format ne
  refuse rien, il s'écourte, parce qu'il se réutilise d'une année sur l'autre. Au pas de tir, une
  **ligne de tir** remplace le pavé de duel — il n'y a pas d'adversaire. Une égalité à la frontière
  **suspend** la manche et le dit plutôt que de deviner qui sort. Le palmarès reprend les rangs
  décernés, et une phase suivante peut y prélever. ⚠️ **Corriger une flèche défait l'élimination
  qu'elle avait causée** : rien n'est stocké de « untel est sorti », tout se rejoue depuis les
  scores. ⚠️ Deux limites nommées : le panneau de routage dit **quelle** manche vient mais pas **où**
  tirer (une question de règle reste ouverte — cibles de qualification ou cibles dédiées ?), et cet
  écran n'a **pas** de file hors-ligne. Référentiel §10.1 amendé ;
  [ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md) amendé — le contrat de phase a cédé
  sur un nom, à l'endroit exact où il annonçait qu'il céderait.
- **Les poules se jouent vraiment (09/08/2026, E05US023).** Le type « poules » était proposé à la
  composition depuis des semaines, et ne menait nulle part : aucun réglage n'était saisissable,
  aucun groupe n'était formé, aucune rencontre n'était tirable — l'organisateur pouvait dessiner un
  tournoi que l'application ne savait pas jouer. C'est fini pour ce format. Il **règle** ses poules
  à l'atelier (« des poules de 4 », le barème, ce que la poule produit) et **voit en direct** ce que
  cela donnera sur son effectif : « à 30 archers, 7 poules — deux de 5, cinq de 4 ». Le jour J, les
  poules se **posent en salle** sur des couloirs voisins, la salle se remplissant sans trou d'une
  poule à l'autre. Le scoreur les fait tirer avec **le pavé qu'il connaît déjà** — celui des duels
  de tableau, à l'identique, y compris quand le wifi saute. Chaque poule se **classe** aux cinq
  critères fédéraux, annonce un **barrage** quand ces critères ne suffisent pas, et la **phase
  suivante consomme ce qu'elle a qualifié**.
  ⚠️ Deux choses valent d'être connues, toutes deux voulues. Une poule de 5 n'occupe que **quatre**
  couloirs : à chaque tour un membre se repose, et lui réserver une place la laisserait vide toute
  la journée. Et les vainqueurs de poule sont **à égalité entre eux** par défaut : une phase
  suivante peut les prendre tous, mais pas en choisir une partie — l'application le **refuse et le
  dit**, au lieu de trancher sur un ordre d'affichage. Une option de départage existe, et l'outil
  indique quand elle devient nécessaire.
  Décision d'architecture : [ADR-0083](../docs/adr/0083-le-contrat-de-phase-jouable.md), qui pose
  aussi le **contrat de phase jouable** — la pièce technique qui rendra les trois formats restants
  beaucoup moins coûteux à livrer.
- Dernière US livrée : **E05US023** (les poules jouables de bout en bout) — US **à surface
  visible**, avec son [fait marquant daté](2026-08-09-21h50-les-poules-se-jouent-vraiment.md) et sa
  [fiche de recette](../docs/fonctionnel/E05US023.md).
- Avant elle, **E05US025** (plusieurs qualifications dans un même déroulé) — US **à surface
  visible**, avec son
  [fait marquant daté](2026-08-09-13h12-plusieurs-qualifications-dans-un-tournoi.md) et sa
  [fiche de recette](../docs/fonctionnel/E05US025.md).
- Avant elle, **E05US024** (un prélèvement lit le classement de sa phase source) — US de
  **moteur**, sans écran neuf : elle change ce que la salle joue, pas ce que l'organisateur voit.
- Avant elle, **E16US004** (le public suit plusieurs archers de bout en bout) — US **à surface
  visible**, avec son [fait marquant daté](2026-08-08-00h44-le-public-suit-plusieurs-archers.md).
- Et avant, **E16US003** (piloter un tour sans avoir les impayés sous les yeux) — US **à
  surface visible**, décrite plus haut et dans son
  [fait marquant daté](2026-08-07-21h29-piloter-un-tour-sans-voir-les-impayes.md).
- Avant elle, **E16US001** (le plan de salle parle enfin de la salle que l'organisateur
  connaît) — US **à surface visible**. L'écran de plan de salle avait été **refusé** à la relecture
  des maquettes pour un seul mot : le logiciel appelait « pas de tir » une rangée de cibles et
  « poste » la place d'un archer, alors que « poste » désigne déjà les **tablettes**. Le vocabulaire
  est **tranché** (ADR-0073, qui amende ADR-0006) et appliqué dans toute l'application — jusqu'aux **papiers imprimés du jour J** : un **pas de tir** est un groupement de
  cibles, un **couloir de tir** est la place d'un archer (A, B, C, D), un **poste** reste une
  tablette ou un écran. L'écran ne se contente plus de nommer, il **montre** : en face de chaque
  cible, quatre cases portent les lettres, pleines pour les couloirs occupables, en pointillés pour
  les autres — et elles s'éteignent à la seconde où l'on réduit une cible, avant même
  d'enregistrer. Deux questions ouvertes depuis les maquettes sont fermées du même coup : la salle
  **rentre dans une grille**, donc le plan reste une **liste** (tant de cibles, tant de couloirs) et
  non un dessin à l'échelle ; et il ne porte **que les cibles**. Ce qui écarte pour de bon la
  variante « plan libre ». Rien ne change au fonctionnement — placement, saisie et classements sont
  identiques ; ce qui change, c'est qu'on peut **valider l'écran** au lieu de deviner ce qu'il
  représente. ⚠️ À l'intérieur du logiciel, la place d'un archer s'appelle encore techniquement
  « position » : écart assumé et tracé (**DETTE-042**), invisible pour l'utilisateur.
- Avant-dernière US livrée : **E07US005** (voir les tableaux de duels en direct) — US **à surface
  visible**. L'arbre des duels n'était visible que du scoreur : le public savait qui tirait où et
  qui avait gagné à la fin, mais pas **contre qui** ni **où en était** la compétition. Un onglet
  **« Tableaux »** l'ouvre au public, avec deux lectures du même arbre — **« Mon chemin »**, le
  parcours de chaque archer suivi tour par tour, et **« Tableau complet »**, tous les duels groupés
  par branche (quarts, demies, finale, petite finale, et les blocs de placement quand le tournoi
  classe au-delà du podium). L'écran de salle sait désormais **projeter** ces tableaux.
- Antépénultième US livrée : **E03US007** (cloisonner les cibles par catégorie ou par blason) — US **à
  surface visible**. Le placement automatique remplissait une cible avec ce qui tenait dedans : deux
  catégories pouvaient s'y retrouver côte à côte, ce que l'arbitre interdit sur certains tournois.
  L'organisateur **choisit désormais ce qu'une cible n'a pas le droit de mélanger** — rien (défaut),
  la catégorie, le blason, ou les deux. Le réglage est **strict** : ni le placement automatique ni un
  glisser-déposer ne peut le contourner — **ni sur le plan de cibles, ni sur celui des duels** —, et
  ce qu'il empêche de poser part en réserve avec la mention **« exclu par le cloisonnement »**,
  distincte de « aucune cible possible » : la salle pleine et le réglage trop serré ne se corrigent
  pas du même geste. Changer le réglage **ne déplace personne** :
  les cibles devenues non conformes sont signalées (badge + bandeau qui dit de régénérer), c'est
  l'organisateur qui décide du moment. ⚠️ Cloisonner **coûte des cibles** (chaque catégorie entame sa
  propre butte) : sur une salle juste, il y aura plus d'archers en réserve — visible aussitôt, et
  réversible. *(Livré juste avant : **E06US006**, jusqu'où le tournoi classe ses archers.)*
- Livrée avant : **E06US006** (choisir jusqu'où le tournoi classe ses archers) — US **à surface
  visible**. Un tableau de duels s'arrêtait toujours au podium : on tirait la finale et la petite
  finale, et les archers sortis plus tôt restaient groupés — les quatre battus des quarts partageaient
  « 5ᵉ-8ᵉ », sans que rien ne dise lequel était 5ᵉ. Le moteur savait pourtant faire autrement depuis
  E05US010, mais le choix était **figé dans le logiciel** : aucun écran ne permettait de le demander.
  Il devient un réglage, **phase par phase**, sur les deux écrans où l'on compose des phases. Deux
  options : s'arrêter au podium (ou à un rang de son choix), ou **classer intégralement** — un duel
  pour chaque rang, si bien que **chaque archer repart avec un rang unique qu'il a gagné au tir**, du
  1ᵉʳ au dernier. Le palmarès le montre aussitôt : plus aucune fourchette, plus aucun rang emprunté au
  classement du matin. ⚠️ Le classement intégral fait tirer **près de quatre fois plus de duels** (128 → 436
  sur un tableau de 120) : c'est une décision d'organisation, l'écran le
  rappelle et la simulation en donne le compte exact. Ne rien changer ne change rien — les tournois
  déjà composés continuent de se jouer au podium. *(Livré juste avant : **E05US021**, un tournoi ne se
  lance plus s'il manque des archers.)*
- Livrée avant : **E05US021** (un tournoi ne se lance plus s'il manque des archers) — US **à
  surface visible**. Un déroulé composé pour 120 archers appliqué à une édition qui en réunit 28
  démarrait sans rien dire, et le problème n'éclatait qu'**en pleine compétition**, sur une tablette,
  au moment de monter un tableau vide. Le contrôle remonte là où la décision se prend : l'application
  **déduit du déroulé** combien d'inscrits il faut au minimum (« les rangs 33 et suivants » en exige
  34), l'affiche en continu sur l'écran du tournoi (« 28 inscrits / 34 requis », avec la phase en
  cause), et **refuse** le démarrage tant que le compte n'y est pas. Un club peut exiger davantage
  (« pas de tournoi de ce type sous 40 archers ») — jamais moins. *(Livré juste avant : **E05US020**,
  le déroulé composé est celui qui se joue.)*
- Encore avant : **E05US020** (le déroulé composé est celui qui se joue) — US **à surface
  visible**. L'organisateur décrivait sa journée (« le tableau prend les rangs 1 à 32 »), l'outil la
  dessinait, la contrôlait, la validait — et le jour J montait un tableau avec **tous** les archers.
  C'est fini : le prélèvement déclaré est honoré, « les rangs 33 et suivants » s'adapte à l'effectif
  réel, et un abandon ne laisse pas de trou. L'avertissement qui prévenait de l'écart a disparu, sauf
  pour les deux formes de prélèvement que le moteur ne sait toujours pas honorer.
- Quatrième US la plus récente : **E06US004** (le palmarès) — US **à surface visible**, qui **clôt le jalon
  J2**. Le tournoi savait dire qui avait le mieux tiré le matin, et qui avait gagné un tableau — mais
  ces deux réponses vivaient sur deux écrans différents, et aucune ne donnait le **classement final**.
  C'est fait : un onglet **« Palmarès »** montre les **podiums** puis le
  **classement complet**, où le vainqueur des duels est 1ᵉʳ même s'il n'était que 6ᵉ le matin, et où
  l'archer qui n'a pas disputé de duel garde un rang, à la suite. L'écran se remplit **au fil des
  duels** : le bronze s'affiche dès la petite finale sans attendre la finale, et tant que la finale
  n'est pas tirée les deux finalistes partagent « 1ᵉʳ-2ᵉ » — l'application ne désigne **jamais** un
  vainqueur à la place du tir. Quand aucun match n'a départagé des archers sortis au même tour, ils
  sont rangés sur leur classement de qualification, comme le veut l'usage. Le tout s'**exporte en
  PDF** — podiums puis classement, prêt à afficher au mur — et se **projette sur l'écran de salle**,
  qui gagne la vue qu'on attendait pour 17 h. *(Livré juste avant : **E06US003**, le barrage des
  places décisives.)*
- Avant-dernière US livrée : **E06US003** (le barrage de tir pour les places décisives) — US **à surface
  visible**. À score égal, le classement départage au nombre de 10 puis de 9 ; quand cela ne suffit
  pas, deux archers **partageaient** leur rang. C'est acceptable au milieu du tableau, pas quand la
  place décide de quelque chose — la dernière qualificative, une marche du podium. L'organisateur
  peut désormais déclarer « je départage au tir jusqu'au rang N » : le classement **signale** les
  places concernées, il fait tirer, saisit la flèche de chacun, et les rangs deviennent consécutifs.
  Si les flèches sont encore égales, on compare la distance au centre ; si elle n'a pas été mesurée,
  l'application **fait retirer** plutôt que de trancher sur une inconnue. Un archer absent au barrage
  annoncé est déclaré perdant, comme le veut le règlement — et cela se **coche**, jamais ne se
  déduit d'un champ vide. Un barrage ouvert par erreur s'**annule**, une flèche mal notée se
  **corrige**. Les **poules** et le **Big Shoot Off** sont servis eux aussi, à une différence près :
  l'organisateur y désigne lui-même les archers à départager, et le résultat ne remonte dans aucun
  classement — l'application ne déroule pas encore ces formats. **Rien ne change pour un tournoi qui
  ne demande rien** : c'est le défaut, et il est resté intact. *(Livré juste avant : **E07US008**, les affectations du prochain tour.)*
- Livrée peu avant : **E07US008** (les affectations du prochain tour) — US **à surface visible**,
  qui referme les **quatre canaux de routage**. L'archer parti de la salle retrouve sur son téléphone
  sa **cible** et sa **place** pour le duel suivant ; l'archer sorti voit le **rang qu'il a acquis**,
  en fourchette (« 5ᵉ-8ᵉ ») quand aucun match n'a départagé les battus — c'est le résultat réel, pas
  une approximation ; l'archer **repêché** voit la phase qui le reprend au lieu d'un « éliminé » qui
  l'aurait fait rentrer chez lui. Un **panneau « Affectations »** montre tout le pas de tir d'un coup,
  pour la table de l'organisation comme pour l'écran de salle, qui gagne ainsi la dernière vue qui lui
  manquait. *(Livré juste avant : **E07US004**, l'écran de salle et le suivi du déroulé.)*
- Livrée peu avant : **E07US004** (écran de salle & suivi du déroulé) — US **à surface visible**,
  qui referme le chantier du moteur de phases par sa sortie visuelle. Un **écran branché dans le
  gymnase** se rattache exactement comme une tablette de cible (même code, même geste) puis fait
  défiler tout seul classement, plan de cibles et suivi ; l'organisateur peut lui **imposer une vue à
  distance** (« le classement 10 minutes »), après quoi l'écran **reprend son défilé sans que
  personne y retourne** — et une vue imposée sans échéance reste signalée en console tant qu'on n'a
  pas rendu la main. Surtout, le **schéma en cases et flèches composé à l'atelier se remplit** : phase
  terminée / en cours / à venir, tour en cours, duels joués sur duels attendus. C'est **le même
  dessin** aux trois endroits (atelier, poste de l'organisateur, écran projeté) : on ne réapprend pas
  à le lire en changeant d'écran. *(Livré juste avant : **E01US024**, composer, diagnostiquer et
  simuler un déroulé ; puis **E05US015**, le catalogue de types de phase.)*
- Prochaine US prévue : cf. [`SUIVI-US.md`](SUIVI-US.md) — **E06US006** (classement intégral 1→N &
  profondeur configurable). Le fil **équipes** est débloqué (E13US002+).
