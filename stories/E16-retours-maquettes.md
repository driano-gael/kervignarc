# EPIC-16 — Retours du questionnaire de maquettes — User Stories

> Issu des **36 questionnaires de maquettes remplis le 04/08/2026**. Voir
> [`epics/EPIC-16`](../epics/EPIC-16-retours-maquettes.md).
>
> **Le lot « front seul » a été livré hors US** le 04/08/2026 (branche
> `feat/retours-maquettes-front`) : tout ce qui ne demandait ni décision métier ni changement de
> domaine ou d'API. Les US ci-dessous sont **le reste** — ce qui exige un arbitrage, du backend, ou
> plus qu'une passe de mise en forme.
>
> **Recette du lot déjà livré** : [`docs/fonctionnel/retours-maquettes-2026-08-05.md`](../docs/fonctionnel/retours-maquettes-2026-08-05.md)
> — neuf scénarios, en langage non technique. La fiche ne suit pas la convention `<ExxUSyyy>.md`
> parce que le lot n'est pas une US numérotée ; elle est rattachée ici pour rester trouvable.
>
> ⚠️ **Chaque US cite la phrase du questionnaire dont elle dérive.** C'est la source du CA (règle 9) :
> ne pas la remplacer par une reformulation au moment de coder — c'est elle qui dit ce qui est
> demandé, et elle est parfois plus étroite ou plus large qu'elle n'en a l'air.

---

### E16US001 — Plan de salle : se mettre d'accord sur ce qu'est un pas de tir
*En tant qu'*organisateur, *je veux* que l'écran de plan de salle parle **de la salle que je connais**, *afin de* pouvoir le valider au lieu de deviner ce qu'il représente.
- **Contexte** : A10 est refusé (🔴) sur un **malentendu de vocabulaire**, pas sur un défaut d'écran. Le commanditaire écrit : *« je ne comprends pas l'usage. Pour moi un pas de tir, c'est le couloir de tir d'un archer et, suivant le nombre de blasons et le nombre d'archers que je positionne sur la cible, exemple 4 archers 2 blasons → A, B, C, D. Explique-moi ce que toi tu vois avant de valider l'écran. »*
- **CA — l'explication d'abord** : avant toute ligne de code, produire une note courte qui met face à face les deux lectures du mot (le **couloir d'un archer** vs la **rangée de cibles**), avec le vocabulaire de [`docs/glossaire.md`](../docs/glossaire.md) et un schéma de la salle réelle. La faire arbitrer. ✅ **Fait le 05/08/2026.**
- **CA — l'écran ensuite** : le gabarit de salle nomme ce qu'il dessine avec le mot retenu, et rend visible le lien **cible → blasons → couloirs A/B/C/D** que le commanditaire décrit.
- **✅ ARBITRÉ le 05/08/2026** *(reversé ici depuis la session, règle 9 — sans quoi ce CA resterait périmé et l'US suivante en dériverait ses tests)* :
  - **« pas de tir » = un groupement de cibles** (la rangée tirée depuis la même ligne de tir). C'est le sens que l'appli employait déjà : **rien à renommer** de ce côté, et les maquettes A10/S01/S07/A13 restent justes.
  - **« couloir de tir » = la place d'un archer devant sa cible** (A, B, C, D) — le champ que le code nomme `position`. Le mot **« poste » ne doit jamais** désigner cette place : dans l'appli livrée, un `poste` est une **tablette ou un écran** (ADR-0064). La maquette A10 disait « nombre de postes par cible » : c'était la collision réelle, corrigée.
  - **Le renommage `position` → `couloir` dans le code, l'API et la base est différé** : appliqué dans l'**application livrée** (écrans, aide, messages d'API, les deux **PDF**, maquette A10 + planche wireframe, glossaire), pas dans les identifiants → **DETTE-042** (majeur, résorption rattachée à `E01US019` avec DETTE-010 — même symbole, même colonne, une seule migration).
  - **Le plafond d'une cible reste un majorant** : les libellés disent « **jusqu'à** N couloirs de tir ». Le placement en installe au plus autant, souvent moins (un blason encombrant occupe la face entière) — écrire « N couloirs » tout court affirmerait une égalité que le moteur contredit.
  - **Reliquat déclaré, à balayer par les US qui rouvrent ces écrans** : plusieurs fiches de [`docs/fonctionnel/`](../docs/fonctionnel/) disent encore « position ». ⚠️ **`E16US004` et `E16US005` corrigent le mot en même temps que l'écran** — ne pas le laisser filer une deuxième fois. Les **questionnaires** (`maquettes/questionnaires/`), eux, ne se corrigent **pas** : ce sont les réponses brutes du commanditaire, un artefact d'archive.
    - *Corrigé le 08/08/2026, en E16US004.* La liste de maquettes qui figurait ici (`a11-placement`, `p02-ma-journee`, `p04-plan-de-cibles`, `s06-routage`, `a09-inscriptions`) était **fausse** : vérification faite, les cinq planches avaient déjà été reprises par E16US001 elle-même — seule la phrase qui les déclarait en retard ne l'avait pas été, ici et dans [`docs/fonctionnel/E16US001.md`](../docs/fonctionnel/E16US001.md). Un reliquat **surdéclaré** est le symétrique du CA périmé de la règle 9 : il s'écrit sans effort, ne se signale par aucune ambiguïté, et coûte à chaque US qui vient re-corriger ce qui l'était déjà. Le reliquat **réel** était dans les fiches fonctionnelles des écrans publics (`E07US001`, `E07US006`, `E07US009`) ; E16US004 l'a balayé. `E16US005` garde la consigne pour ce qu'elle rouvrira.
  - **La salle rentre dans une grille régulière** : le gabarit reste une **liste** (`N cibles × nombre de couloirs`), **sans** coordonnées ni obstacles. La variante « plan libre » de A10 reste écartée.
  - **Le gabarit ne porte que les cibles** : ni table d'organisation, ni zone d'échauffement, ni entrée du public.
- **Notes** : ⚠️ **US bloquante par nature** — elle commence par une question, pas par du code. C'est le cas prévu par la règle « CA ambigu ⇒ questionner avant d'implémenter ». Toucher `docs/glossaire.md` si le mot change. US à **surface visible** → doc fonctionnelle + journal.
  Les deux arbitrages « grille » et « cibles seules » **ferment aussi** la porte à un modèle géométrique : toute US ultérieure qui voudrait des coordonnées (plan libre, repères) rouvre l'arbitrage, elle ne l'hérite pas.
- **Dépend de** : E03 (gabarits, plan de salle) · **Jalon** : J2 · **Origine** : questionnaire A10, 04/08/2026

---

### E16US002 — Phases : une bibliothèque de phases réglables, pas une séquence figée
*En tant qu'*organisateur, *je veux* **lister mes phases, en ajouter depuis un gabarit et ouvrir la fiche de réglages de chacune**, *afin de* pouvoir avoir plusieurs qualifications ou plusieurs tableaux aux réglages différents dans le même tournoi.
- **Contexte** : A07 est refusé (🔴). *« La création/gestion d'une phase est assez compliquée et demande des écrans plus détaillés. Je voudrais une liste des phases dans un écran, avec la possibilité d'en ajouter de nouvelles à partir d'un gabarit de phase. Par exemple je peux avoir plusieurs phases de type qualification, ou duel, qui n'ont pas les mêmes réglages. Sur chaque ligne du tableau on peut ouvrir une fiche de la phase, qui reprend son titre et ses réglages (nb de séries, volées, flèches, sets… suivant le type de phases). »* Et : *« chaque phase reste une brique qui peut servir d'une année sur l'autre, donc il peut y avoir plusieurs phases de même type mais avec des réglages différents. »*
- **CA — liste** : un écran liste les phases du tournoi (titre, type, rang, état), une ligne par phase, avec ajout depuis un **gabarit de phase**.
  - **✅ LIVRÉ le 22/08/2026, et la liste existait déjà.** Vérification faite avant de coder : `Phases.tsx` rendait
    déjà une ligne par phase (rang, type, sources, effectif, profondeur). Ce qui manquait était le **titre** —
    la ligne affiche désormais `titre ?? libellé du type`, le type restant lisible en détail. « Ajout depuis un
    gabarit » reste ce qu'ADR-0060 §5 en a fait : un **préréglage** par type au moment d'ajouter (déjà en place),
    pas une bibliothèque de phases autonomes. L'**état** n'est **pas** sur cette ligne, et c'est ADR-0076 :
    une étape de déroulé n'a pas de statut, l'avancement est par créneau et vit dans « Suivi du déroulé ».
    Ce mot du CA est donc **périmé depuis le 07/08/2026**, pas non tenu.
- **CA — fiche** : ouvrir une ligne ouvre la fiche de la phase — son **titre** et ses **réglages propres au type** (nombre de séries, de volées, de flèches, de sets…).
  - **✅ LIVRÉ le 22/08/2026** ([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md) §5).
    Une bascule « Ouvrir la fiche » par ligne, **pour tous les types**. ⚠️ **C'est la qualification qui portait le
    défaut** : « gérée ailleurs » (son barème se règle sur « Barème & validation »), elle n'ouvrait **aucun**
    formulaire, et ses réglages propres — barrage, découpage, arrêts — traînaient à plat dans la barre d'actions.
    Elle était donc le seul type impossible à nommer, précisément celui dont ce CA dit qu'on peut en avoir plusieurs.
  - **⚠️ Trois points que le CA ne disait pas, tranchés ici** (ADR-0095 §1) : *(a)* un **titre blanc vaut absence
    de titre**, jamais un refus — c'est le geste par lequel on *retire* un titre et on revient au libellé
    automatique ; *(b)* **aucune unicité** — deux phases du même déroulé peuvent porter le même titre, l'identité
    restant l'`id` et le rang (ADR-0045 §3) ; *(c)* le titre **survit à un retypage**, à la différence des cinq
    réglages voisins : il n'appartient à aucun type.
  - **⚠️ Ce qui reste HORS de la fiche** : la génération du **plan de cibles**, qui est une *action* et non un
    réglage. Le dépôt s'est brûlé trois fois sur des plans inatteignables (E05US023, E05US026, E05US030) ; la
    replier derrière un clic aurait rejoué ce risque.
  - **⚠️ Contrepartie assumée** : les réglages de la qualification ne sont **plus visibles sans clic**. Le CA
    demande une fiche qu'on ouvre, pas un mur qu'on parcourt — mais le garde-fou d'E05US035 a dû changer de geste,
    et il faut le savoir.
  - **⚠️ Aucune migration.** Le titre vit à la racine du `config` JSON de l'étape (ADR-0046), comme le découpage
    d'E05US035. La ligne du tracker annonçait « champ neuf → **migration** » : c'était **faux**, vérification faite
    — `deroule_etape` n'a que quatre colonnes (`id`, `tournoi_id`, `ordre`, `type`), *tous* les champs de définition
    vivent dans le JSON. Une colonne pour le seul titre aurait été l'exception, pas la règle.
- **CA — plusieurs phases de même type** : deux qualifications aux réglages différents coexistent dans un même tournoi sans se marcher dessus.
  - **✅ ARBITRÉ le 08/08/2026 — ce CA sort du périmètre d'E16US002 et devient `E05US024` + `E05US025`.**
    Le cadrage a montré que la question n'est **pas** un problème d'écran. Deux constats, vérifiés
    dans le code : (a) le **modèle de composition est déjà générique** — une phase en tête prend les
    inscrits, toute phase en aval prend ce que ses `sources` déclarent, et rien là-dedans ne regarde
    le *type* de la phase ; (b) mais le **moteur d'exécution** ne lit qu'un seul classement, celui de
    la qualification (`application/prelevement.py:preleves`), et tout prélèvement visant une autre
    phase est **ignoré en silence** — la phase reçoit alors *tous* les archers en lice. L'unicité de
    la qualification (`_anomalies_unicite_qualification`, E05US021) n'est que le **pansement** de ce
    raccourci : tant que le moteur dit « **la** » qualification, il faut qu'il n'y en ait qu'une.
    ⚠️ **Conséquence à ne pas perdre** : lever l'unicité **seule** serait le pire des deux mondes —
    l'écran laisserait composer deux qualifications, et en salle le tableau se peuplerait de tous les
    archers au lieu des rangs déclarés. C'est exactement « le tournoi démarrait puis cassait en
    salle » que la docstring d'E05US021 décrit. D'où l'ordre imposé : `E05US024` (le prélèvement lit
    le classement de **sa** phase source) **puis** `E05US025` (plusieurs qualifications).
    *Arbitrage du commanditaire : « la création du déroulé doit permettre de composer les phases
    comme on en a envie, le club est libre de son format de tournoi. »*
- **CA — réutilisable d'une année sur l'autre** : le **gabarit** est ce qui se réutilise, comme le **format** l'est déjà (ADR-0060 §5). ⚠️ Vérifier au cadrage si « gabarit de phase » et « format » sont deux noms d'une même chose ou deux niveaux distincts — la réponse change tout le modèle.
  - **✅ ARBITRÉ le 08/08/2026 — un seul niveau : le format reste la brique.**
    [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §5 est
    **confirmé**, pas amendé : ce qui se range en bibliothèque et se rejoue d'une année sur l'autre
    est la **séquence** (`FormatTournoi`), pas la phase isolée. « Ajouter depuis un gabarit de phase »
    se lit donc comme un **préréglage au moment d'ajouter**, sans nouvel agrégat ni table : on ne
    crée pas de bibliothèque de phases autonomes. Les deux motifs d'ADR-0060 §5 tiennent toujours —
    le barème n'est pas une entité (il vit dans la définition de l'étape), et une phase hors tournoi
    porterait un `ordre` en collision qui casserait l'invariant de séquence 1..N.
- **CA — vocabulaire des deux écrans de composition** *(ajouté au cadrage du 22/08/2026, arbitrage du commanditaire)* :
  les deux destinations qui composent des phases portaient **chacune le mot de l'autre** — « Phases (**format**) »
  composait le déroulé d'un tournoi, « Composer un **déroulé** » fabrique un format de bibliothèque. Elles disent
  désormais ce qu'elles font : **« Phases du tournoi »** et **« Composer un format »**
  ([ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md) §4). ⚠️ **Ce n'est pas
  cosmétique** : c'est le motif exact du refus d'A10 qu'ADR-0073 a fait lever, et il portait sur les deux écrans
  les plus proches l'un de l'autre du parcours. ⚠️ **Un message trompeur est tombé avec** : « composition avancée :
  éditable depuis l'écran de composition du déroulé » désignait l'atelier, qui ne travaille sur **aucun tournoi**
  — un cul-de-sac, antérieur à cette US et mis à nu par le renommage.
- **CA — chiffrage `P-4` de la planche : ❌ HORS PÉRIMÈTRE** *(arbitrage du commanditaire, cadrage du 22/08/2026)*.
  La planche A07 exigeait de « chiffrer la conséquence **au moment du choix** » — un tableau de 120 passe de 128
  à 436 duels selon la profondeur. C'est [`DETTE-035`](../docs/dette.md), qui reste **ouverte** : son remède touche
  la politique `Depth` côté domaine, soit un chantier moteur dans une US déjà large côté IHM. L'écran énonce déjà
  la conséquence en clair, et la simulation (E15US002) en rend le compte exact.
- **Notes** : touche le **domaine et l'API** — aujourd'hui les réglages de qualification vivent sur le barème du tournoi (`bareme`), pas sur la phase. Relire [ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) (catalogue de onze types) et [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) avant de cadrer. **ADR probable**. **Redécoupable** (liste seule / fiche / gabarits) — probablement trop large pour une branche.
  - **✅ Livrée d'un bloc le 22/08/2026, sans redécoupage** — et le pronostic « trop large » était juste **au
    moment où il a été écrit**. Ce qui l'a désamorcé : deux des trois CA étaient sortis du périmètre dès le
    08/08/2026, et les six US de formats (E05US023 → E05US029) avaient livré entre-temps **cinq fiches de réglages**
    plus les arrêts. Il ne restait donc ni moteur ni catalogue à inventer — le titre, la fiche, le vocabulaire.
  - **✅ « ADR probable » confirmé** : [ADR-0095](../docs/adr/0095-un-titre-de-phase-est-un-libelle-pas-une-identite.md).
  - **⚠️ La note « les réglages de qualification vivent sur le barème du tournoi » reste vraie et n'a pas été
    touchée** : le barème se règle par sa propre ressource, et l'exposer une seconde fois dans la fiche aurait
    ouvert deux chemins d'écriture pour une même donnée. La fiche de la qualification lit `nb_volees` en **lecture
    seule**, ce qu'E05US035 avait déjà posé.
  - **⚠️ `DETTE-080` inscrite** : la plomberie d'état des **deux** formulaires de composition est écrite deux fois,
    et le titre en est le 10ᵉ réglage. Antérieure à cette US, aggravée par elle. Une duplication a en revanche été
    **fermée** sur preuve (`configInchangee`, trois occurrences et deux bugs déjà payés).
- **Dépend de** : E05US015, E01US023, E01US024 · **Jalon** : J2 · **Origine** : questionnaire A07, 04/08/2026

---

### E16US003 — Complétude : ne plus mélanger le déroulé et la gestion administrative
*En tant qu'*organisateur, *je veux* que la complétude du **déroulé** soit séparée de la complétude **administrative**, *afin de* ne pas voir des paiements quand je pilote un tour.
- **Contexte** : A14 est refusé (🔴). *« Je n'aime pas le mélange entre le déroulé et la gestion administrative. Complétude en déroulé n'est pas complétude administrative : en déroulé on est centré sur l'événement. »*
- **CA — deux écrans, une source** : le serveur rend déjà `sportif` et `hors_sportif` séparément (`GET /tournois/{id}/completude`). Les deux listes se rendent donc sur **deux destinations** — le sportif au **pilotage**, l'administratif à la **gestion** — sans dupliquer le calcul.
- **CA — le bouton « Terminer » suit le sportif** : c'est lui que « terminer » fige (les paiements restent ouverts), il reste donc du côté déroulé.
- **CA — ~~questions restées sans réponse, à reposer~~ → tranchées le 07/08/2026.** Les deux questions ont été reposées au commanditaire en tête d'US, et **les deux confirment le CA tel qu'il était écrit** :
  - *« la séparation sportif / hors-sportif correspond-elle à ta façon de clore un tournoi ? »* → **oui** ; le refus A14 portait bien sur le **mélange à l'écran**, pas sur le découpage du domaine. Rien à changer côté domaine ni API.
  - *« "Terminer" fige le sportif et laisse les paiements ouverts : est-ce le bon découpage ? »* → **oui** ; le bouton reste au pilotage, et ce qu'il **annonce** ne regarde que le sportif. Il n'est en revanche **jamais bloqué** — ni par le sportif, ni par l'administratif : `D-15` (« l'appli n'empêche pas, elle avertit ; blocage = *terminé* seul », **Actée**) et le CA d'E12US005 (« Terminer n'est jamais bloqué ») valent toujours. `sportif_complet` ne **garde** rien ; il choisit le **libellé de la question** de confirmation (« Terminer quand même ? » vs « Terminer le tournoi ? ») et la mention « complet »/« incomplet » de la section Sportif. L'option écartée est celle d'**exiger l'administratif** avant de clore.
    - ⚠️ **Rédaction corrigée en revue (07/08/2026).** La première version de cette puce écrivait « le bouton … **ne se garde que sur `sportif_complet`** » et donnait « n'exiger rien et se contenter d'avertir » pour **écartée** — soit exactement l'inverse du code livré et de `D-15`. Le code n'a jamais changé (`disabled` ne porte que sur l'appel en cours) : c'est le **CA reversé qui était faux**. Laissé tel quel, il aurait fait dériver à E16US008 un test « bouton désactivé si sportif incomplet » — donc un tournoi impossible à clore pour une cible abandonnée. Un CA faux n'est pas *ambigu* : il s'écrit sans effort et passe le garde-fou de la règle 9. `Completude.test.tsx` porte désormais le cas `D-15` explicitement.
- **CA — la confirmation de « Terminer » continue de chiffrer les impayés.** Séparer les écrans ne coupe **pas** ce lien : la fenêtre de confirmation est le seul moment où les deux mondes doivent se croiser, puisqu'elle annonce ce qui se **fige** et ce qui reste **ouvert**. `messageConfirmationTerminer` lit donc toujours `hors_sportif` — ce n'est pas un résidu du mélange refusé, et `presentation.test.ts` le garde.
- **Notes** : front seul (découpage du domaine confirmé) ; **déplacement d'ossature**, signalé en revue. US à **surface visible** → doc fonctionnelle + journal.
- **⚠️ Arbitrage de mise en œuvre (07/08/2026) — pas de destination neuve.** Le CA dit « **deux destinations** » ; `hors_sportif` ne porte aujourd'hui qu'**une** ligne, `paiements` (`domain/completude.py`), et l'axe gestion a **déjà** une destination `paiements`. La section hors-sportif est donc rendue **en tête de l'écran Paiements** (`CompletudeAdministrative`, hors des onglets), et non sur une destination « Complétude administrative » qui aurait posé un écran d'une ligne au-dessus de l'écran traitant exactement ce sujet. Une destination dédiée se rouvre le jour où le hors-sportif porte **plusieurs** sujets — pas avant (« pas de remède structurel sur une évolution supposée »). Conséquence : la **table des destinations** est inchangée — `AXE_PAR_DESTINATION` et `BESOIN_TOURNOI` intacts, 31/30 destinations, `axes.test.ts` non modifié. Seuls **changent le libellé** de `completude` et **le texte** de deux entrées d'`AIDE_ECRANS` (`completude` et `paiements`) : ce sont des contenus, pas de l'ossature.
- **⚠️ Arbitrage (07/08/2026) — le tableau de bord d'accueil est filtré lui aussi.** Relevé en revue : `accueil` appartient à l'axe **pilotage** (`AXE_PAR_DESTINATION`) et en est la **destination d'ouverture** — y laisser « Paiements 113/120 » dans « À faire » et « Paiements : 7 à compléter » dans les alertes aurait rejoué le refus d'A14 sur l'écran **le plus vu** de l'axe : le trou déplacé, pas fermé. Le commanditaire a tranché « filtrer aussi l'accueil ». La checklist et les alertes ne lisent donc plus que `sportif`. Le **chiffre-clé « Réglés »** de l'entête reste, lui : c'est un **repère**, pas une tâche à faire — la distinction est le critère de partage.
- **⚠️ Arbitrage (07/08/2026) — le libellé : « Prêt à terminer ? », pas « Complétude du déroulé ».** Le premier jet nommait l'écran « Complétude du déroulé ». Écarté en revue : la sidebar du pilotage porte déjà « **Suivi du déroulé** » trois entrées plus haut, et [ADR-0076](../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md) réserve « déroulé » au **plan composé une fois** — deux libellés voisins pour deux choses différentes, soit le motif exact du refus d'A10 ([ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md)). Le nom retenu dit la **question à laquelle l'écran répond**.
  - **Cadrage à ne pas perdre** : le commanditaire vise une **famille** de « prêt à… » — *prêt à démarrer*, *prêt à terminer*, *prêt à archiver*, *prêt à exporter* — chacun répondant « puis-je passer à l'étape suivante, et sinon que manque-t-il ? ». C'est une **refonte de navigation** qui dépasse cette US : elle recouvre la frise du cycle de vie (E14US001, 7 statuts, ADR-0026), le feu vert (`E16US008`) et les exports. À instruire dans une US dédiée (candidate à un ADR), **pas** à improviser écran par écran — sans quoi on obtiendra quatre écrans « prêt à… » incohérents entre eux. Cette US ne livre que le premier, sur le périmètre qui était le sien.
- **⚠️ La planche A14 redessinée du 05/08/2026 est écartée pour cette US.** Elle propose autre chose que la séparation demandée : trois listes « Bloquant / À voir / Vérifié » autour du bouton « Donner le feu vert », **paiements compris** — donc toujours mélangés, ce que le questionnaire refusait. Le motif d'écart est la **réserve 2 d'[ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)** — « un arbitrage explicite du commanditaire l'emporte sur la planche » —, **et pas** le fait qu'elle n'ait pas été validée : les planches sont opposables **sans** validation, et invoquer la non-validation fournirait un prétexte réutilisable pour écarter n'importe laquelle. Ce qu'elle propose reste une piste valable pour `E16US008` (feu vert), pas pour la complétude.
  - **Piège à connaître, appelé à se répéter** : la réserve 2 est illustrée par une planche **en retard** sur l'arbitrage. Ici la planche est **postérieure** au questionnaire (05/08 vs 04/08), ce qui suggère à tort qu'elle l'intègre — alors que ~22 planches ont été redessinées ce jour-là **sans** tour 2. Une planche redessinée après le questionnaire mais **non re-validée** ne vaut donc pas arbitrage : c'est le questionnaire du tour 1 qui fait foi. À porter dans ADR-0074 si le cas se représente une 3ᵉ fois (`P03` / `E16US004` est déjà annoncé).
- **Dépend de** : E12US005, E14US003 · **Jalon** : J3 · **Origine** : questionnaire A14, 04/08/2026

---

### E16US004 — Le public suit **plusieurs** archers, de bout en bout
*En tant que* spectateur ou accompagnateur, *je veux* suivre plusieurs archers et retrouver **leur** classement, **leurs** tableaux et **leur** journée, *afin de* ne pas avoir à chercher chacun à la main.
- **Contexte** : quatre questionnaires disent la même chose sous quatre angles.
  - P01 : *« mettre un filtre de tri par club en plus dans la recherche ; une liste d'archers se met à jour à mesure de la recherche ; dans la ligne d'un archer mettre un état : suivi, à suivre, ne plus suivre »*, et *« il faut pouvoir suivre plusieurs archers »* (mémorisé en `localStorage`, confirmé).
  - P02 : *« à retravailler pour accepter de suivre plusieurs archers »*, *« écran trop personnel, il s'adresse aussi bien au public qu'à un archer »*, *« rendre ça uniforme pour le public comme pour l'archer, écran repliable pour le récapitulatif des informations de la journée, on doit pouvoir retrouver tous les tours de toutes les phases joués »*.
  - P03 (🔴) : *« il me faut les 2 : soit le classement uniquement des archers suivis, soit le classement général »*, *« en direct, dès que les informations sont disponibles, pareil pour les scores en cours »*, et le détail des flèches des autres : *« oui »*.
  - P05 : *« une bascule pour suivre tous les tableaux du tournoi ou uniquement centré sur les archers que l'on choisit de suivre »*.
- **CA — bascule « mes archers / tout »** sur le classement (P03) et sur les tableaux (P05). *(Cadrage du 08/08/2026 : **un seul interrupteur, en tête de l'écran public**, et non un par vue — il gouverne aussi les affectations, le palmarès et le plan de cibles. Le spectateur choisit une fois et ne le redit pas à chaque onglet. Conséquences tranchées en cours d'US : (a) l'interrupteur ne s'affiche que si l'on suit au moins un archer, et retombe sur « tout » sur un tournoi où l'on n'en suit aucun — il est mémorisé globalement alors que les suivis sont par tournoi ; (b) `VueTableaux` **perd** son sélecteur local « Mon chemin / Tableau complet » livré en E07US005 — il disait la même chose, mais **par vue** : la combinaison « mon chemin sur les tableaux **et** classement complet » n'est donc plus exprimable, l'interrupteur global étant tout ou rien ; (c) le palmarès ne centre que le classement final, **jamais les podiums** — un podium amputé ne répond plus à « qui a gagné » ; (d) chaque vue nomme « aucun de vos archers ici » distinctement de son propre vide, et **un vide réel** (aucun inscrit classé) n'est jamais imputé au filtre ; (e) le pas de tir des **affectations** garde ses buttes **entières, adversaire compris** — sur un tableau de duels, le voisin de butte *est* l'adversaire, et le filtrer ligne à ligne cachait contre qui l'archer tire ; (f) l'interrupteur n'est **pas affiché sur l'onglet « Suivi »**, qui ne le lit pas — c'est pourtant l'onglet d'atterrissage, et un réglage sans effet visible y faisait douter du reste de l'écran.)*
  - **⚠️ Arbitrage du commanditaire, 08/08/2026 (revue) — l'interrupteur est armé par défaut.** Le CA d'E07US005 promet que « la lecture *Mon chemin* est celle par défaut **dès qu'on suit quelqu'un** », et `D-09` ouvre déjà l'onglet « Suivi » d'office pour la même raison. L'interrupteur unique ayant dissous les défauts **par vue**, le livrer désarmé **révoquait ce CA en silence** — le défaut d'une US livrée disparaissant comme effet de bord d'une autre. Décision : **l'appli publique s'ouvre centrée** sur les archers suivis, pour les cinq vues ; la retombée « tout » du point (a) rend la valeur inoffensive quand il n'y a personne à centrer. Porté par [ADR-0079](../docs/adr/0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md).
- **CA — recherche** : filtre par club, liste qui se met à jour à la frappe, état de suivi actionnable sur chaque ligne. *(Tranché : un club **choisi seul** liste ses archers, sinon ce n'est pas un filtre mais un raffinage. `club_id = null` — club inconnu, ADR-0014 — ne tombe dans aucun club filtré. La recherche **ne se vide plus** après un « Suivre » : on en suit plusieurs d'affilée. **Un club choisi lève le plafond de résultats** — la borne de 8 visait la recherche par nom ; appliquée au club, elle rendait impossible le parcours même de P01, lister les archers de son club. La liste déroulante ne propose que les clubs **représentés sur ce tournoi**.)*
- **CA — récapitulatif repliable** de la journée, couvrant **tous les tours de toutes les phases** joués. *(Tranché : `<details>` natif, **ouvert par défaut**. P02 demande « repliable », pas « replié », et P03 veut les scores en direct — le livrer fermé aurait caché derrière un clic ce que la carte affichait déjà. Lecture **rétrospective** : les tours à venir en sont exclus, le bloc « Ensuite » d'E07US008 les porte déjà. Un tour d'**exemption** y figure en revanche : il explique un tour sauté, et l'omettre rendrait le parcours incompréhensible. « Toutes les phases » se lit **par archer**, pas par créneau de salle : le récapitulatif couvre les départs où **l'archer suivi** est engagé — sans quoi un archer du matin perdait ses duels dès l'après-midi lancée.)*
- **CA — détail des flèches des autres** accessible depuis le classement.
- **Notes** : le multi-archers **existe déjà** au socle (`sessionSuivisStore`, E07US006) — c'est la lecture qui n'en tire pas parti. Front majoritaire ; vérifier si l'API rend le détail des flèches d'un tiers en lecture publique. **Redécoupable** par écran. US à **surface visible** → doc fonctionnelle + journal.
  - *Vérification faite le 08/08/2026 : l'US est **front seul**, aucune ligne de backend.* `GET /api/v1/tournois/{id}/archers/{id}/deroule` est **déjà** public et anonyme pour n'importe quel archer ([ADR-0039](../docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md), transparence assumée) : le détail des flèches est du câblage, pas une frontière déplacée. Et `GET …/tableaux` rend **toutes** les phases avec tous leurs duels, donc le récapitulatif se compose côté client. **Réserve** : le DTO public tait volontairement manches et zones d'un **duel** (règle 6) — le détail flèche par flèche existe pour la qualification, pas pour les duels ; P03 ne le demandait pas et cette décision n'a pas été rouverte.
  - *Livrée en **une** branche et une PR*, malgré l'avertissement « redécoupable » : la granularité est dans les commits (logique pure → bascule → vue Suivi → doc), conformément à la préférence durable du commanditaire.
- ~~**⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))**~~ — ✅ **vérifié le 24/08/2026 : le reliquat n'existe pas.** `maquettes/a11-placement.html` ne contient pas une seule occurrence de « position » au sens de la place d'un archer (seulement « proposition »), et l'écran expose déjà `aria-label="Couloir de tir A"`. Même cas de figure qu'E16US004, dont la liste de maquettes était fausse pour la même raison : le balayage avait déjà eu lieu. Rien à corriger — mais l'avertissement est **conservé** pour les deux US qui le portent encore (`E16US010`, `E16US011`), où il n'a pas été vérifié.
- **Dépend de** : E07US006, E07US005, E06US001 · **Jalon** : J3 · **Origine** : questionnaires P01, P02, P03, P05, 04/08/2026

---

### E16US005 — Placement : la largeur d'un PC, et un puits de réserve ✅
*En tant qu'*organisateur, *je veux* placer les archers **une cible par ligne** sur toute la largeur de l'écran, et pouvoir **sortir un archer du plan sans le placer ailleurs**, *afin de* ne pas être obligé d'inverser deux archers à chaque ajustement.
- **Contexte** : A11 est validé avec réserves. *« Trop tassé, on doit pouvoir mieux s'adapter sur la largeur d'un écran PC »*, *« une cible par ligne me paraît plus adaptée »*, *« je ne vois pas de puits de réserve pour déplacer des archers sans les positionner, ce qui évite de toujours faire une inversion entre 2 archers »*. Travail **sur PC uniquement** (question 1). Le recalcul après ajout d'un retardataire **préserve les placements manuels** (question 2 : *« oui »*). Contraintes : *« toutes les contraintes déjà énoncées, dans la mesure du possible »*.
- **CA — une cible par ligne**, exploitant la largeur disponible (les jetons `--largeur-app` sont posés depuis le lot front du 04/08).
  - ✅ **Tranché au cadrage du 24/08/2026** : la largeur gagnée ne sert pas qu'à aérer — chaque jeton
    porte, sous le nom, les **repères sur lesquels l'organisateur arbitre** : **club** (mixité, RG-3),
    **catégorie** et **blason** (cloisonnement, RG-4). Sans eux, les deux badges déjà posés par le
    serveur au niveau **cible** (« mixité de club non garantie », « cloisonnement non respecté »)
    désignent un problème sans jamais dire **lequel** des quatre occupants le cause. Un club non
    renseigné se dit « **club inconnu** », jamais « aucun club » ([ADR-0014](../docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md)),
    et un référentiel non chargé **n'affiche rien** plutôt qu'un « Club #7 ».
  - ✅ **Le plan de duels est aligné dans le même diff** (arbitrage du commanditaire, cadrage du
    24/08/2026). Le refus A11 ne visait que la qualification, mais `duels/Duels.tsx` partage la
    classe `.placement__cibles`, le même utilisateur et le même PC : n'en corriger qu'un aurait
    laissé deux écrans jumeaux devenus dissemblables. Coût constaté : le changement s'écrit **deux
    fois** — d'où [`DETTE-085`](../docs/dette.md).
  - **Colonnes alignées d'une cible à l'autre** : le nombre de couloirs est **dérivé de la capacité
    maximale du plan**, jamais écrit en dur — sans quoi ce serait une 4ᵉ copie du plafond `A`→`D`
    (`DETTE-010`).
- **CA — la réserve est un panneau collant**, à droite du plan, ✅ **ajouté au cadrage du
  24/08/2026** : le glisser-déposer HTML5 natif **ne fait pas défiler la page**, donc une réserve en
  pied d'écran rend « sortir un archer de la cible 37 » impraticable — soit exactement le geste que
  le questionnaire demandait de simplifier. Une cible par ligne allonge le plan, et aurait donc
  **aggravé** ce défaut si la réserve était restée en bas. Sous ~64 rem de large, elle repasse sous
  le plan (deux colonnes y seraient illisibles) ; la bande une-cible-par-ligne, elle, ne cède pas —
  c'est le CA.
- **CA — puits de réserve** : une zone où déposer un archer retiré du plan, d'où on le replace ensuite. Un archer en réserve n'est **pas** placé — il doit se distinguer d'un archer sans cible.
  - ✅ **Constat de cadrage du 24/08/2026 : ce CA était DÉJÀ TENU, au-delà de sa lettre.** Non
    seulement la zone existe (E03US004), mais la distinction demandée est **explicite** dans le code
    depuis E03US007 : `presentation.ts` sépare `en_reserve` (« en attente », ton neutre) des trois
    anomalies `sans_blason` / `non_place` / `cloisonnement` (ambre, `DV-03`). L'US n'y a donc rien
    ajouté — elle a **posé un test de non-régression** dessus (`Placement.test.tsx`), puisque rien
    ne gardait cette distinction jusqu'ici.
  - ⚠️ **Ce CA recoupe `E03US004`, livrée** (« CA — réserve » : *une zone **réserve** (banc, sans
    capacité) reçoit les archers non posés* ; le placement auto y range les non-plaçables **avec leur
    raison**, et « Plan final = réserve vide » est déjà un critère). **Ne pas la respécifier** : lire
    le CA d'`E03US004` en premier et n'écrire ici que l'**écart**. Renvoi mutuel posé le 08/08/2026.
- **CA — préservation** : un recalcul après ajout ne défait pas les placements manuels.
  - ✅ **Également déjà tenu** (constat du 24/08/2026) : c'est le bouton « **Placer les restants** »
    (E03US004), qui complète les trous **sans déplacer** les archers posés — et un retardataire
    inscrit après coup apparaît de lui-même en réserve, une inscription sans ligne d'affectation
    valant réserve ([ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md)). La
    régénération complète, elle, écrase bien les ajustements : c'est voulu, et confirmée par la
    fenêtre d'impact chiffrée d'E12US007.
- **⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))** : cette US rouvre des écrans dont la maquette dit encore « position » pour la place d'un archer. **Corriger le mot en « couloir de tir » dans le même diff** — maquette et écran. Le laisser filer rejouerait le refus d'A10 sur un autre écran.
- **Notes** : ~~vérifier si « en réserve » se représente côté serveur (`cible = null` suffit-il ?) ou seulement à l'écran ; la réponse décide si l'US est front seul.~~ **Question fermée le 08/08/2026, sans code à écrire** : la réserve **existe déjà côté serveur** depuis `E03US004` — le modèle de persistance d'[ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md) est *une affectation par inscription, **sans ligne = réserve***. L'US est donc **front seul** sur ce point : ce qui manque est la **zone à l'écran**, pas sa représentation. Le glisser-déposer existe (variante A retenue).
- **Notes de livraison (24/08/2026)** : **front seul, aucune ligne de backend, aucune migration.**
  Deux des trois CA étant déjà tenus (voir ci-dessus), le livrable réel est la **mise en page** et
  ce qu'elle permet d'afficher. `club_id` et `categorie_id` vivent déjà sur `Archer`, `blason_id`
  sur `Placement` : les trois référentiels se lisent par leurs hooks existants (`useClubs`,
  `useCategories`, `useBlasons`), aucun DTO n'a été touché. La traduction des identifiants en clair
  est une fonction **pure** (`reperesArcher`), posée dans `placement/presentation.ts` — le module
  que les duels importent déjà — et non recopiée dans les deux écrans : une seconde copie est
  exactement ce qui a produit le défaut d'E03US007. Le **rendu**, lui, reste double :
  [`DETTE-085`](../docs/dette.md), inscrite ici et à résorber avec `DETTE-083`.
- **Dépend de** : E03US011, E05US010 · **Jalon** : J2 · **Origine** : questionnaire A11, 04/08/2026

---

### E16US006 — Patrimoine : distinguer l'officiel FFTA du local, et porter le logo du club
*En tant qu'*organisateur, *je veux* voir d'un coup d'œil ce qui vient de la **FFTA** et ce que **j'ai créé**, *afin de* ne pas modifier par erreur une référence officielle.
- **Contexte** : A06, deux fois la même phrase (critique **et** évolution) : *« une séparation visible des unités officielles FFTA de celles créées par l'administrateur »*. A05 : *« ajouter un champ de plus pour le logo du club qui organise le tournoi, en plus du logo du tournoi ; bien sûr cela reste optionnel »*.
- **CA — origine visible** : catégories, blasons, clubs et barèmes portent une **origine** (officielle / locale), affichée et filtrable.
- **CA — logo du club** : un second logo, **facultatif**, distinct du logo d'événement.
- **CA — question restée sans réponse, à reposer** : *« l'import depuis un fichier (catégories FFTA, liste de clubs) est-il nécessaire ? »* — il conditionne la façon dont l'origine « officielle » est alimentée.
- **Notes** : demande un **champ de données** sur les référentiels et sur l'identité — donc migration Alembic. Rattaché à E01US016 pour le logo. Relire [ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) : la notion de bibliothèque existe déjà, l'origine s'y ajoute.
- **Dépend de** : E01US023, E01US016 · **Jalon** : J2 · **Origine** : questionnaires A05, A06, 04/08/2026

---

### E16US007 — Impressions, exports et podiums paramétrables
*En tant qu'*organisateur, *je veux* choisir **le format** de chaque export, encaisser **par club**, et configurer **ce que couvre un podium**, *afin de* ne pas dépendre d'une liste figée décidée à l'avance.
- **Contexte** : A18 : *« chaque ligne d'export doit proposer plusieurs formats possibles (CSV, EXCEL, PDF…) »* et, sur les exports attendus : *« ça peut évoluer et donc être paramétrable »* ; le journal d'audit doit être consultable **en cours** de tournoi. A17 : paiements par club, *« oui »* (un chèque pour douze archers) ; le détail des modes de versement **en option**. A16 : *« podium configurable, tout doit être possible »* (par catégorie, scratch, par club, par équipe). A08 : un **QR par scoreur**, en plus du code (seul le PDF groupé existe aujourd'hui).
- **CA — formats** : chaque export propose ses formats disponibles ; l'ajout d'un format ne demande pas de toucher l'écran.
- **CA — paiement groupé par club** : un règlement unique couvre plusieurs archers, et le solde de chacun le reflète.
- **CA — podiums configurables** : la portée d'un podium se règle (catégorie / scratch / club / équipe).
- **CA — audit en cours de tournoi** : consultable sans attendre la clôture.
- **CA — QR par scoreur** : jumeau de celui des cibles, affichable à l'écran.
- **Notes** : entièrement **backend + API**. ⚠️ **Trop large pour une branche** — à redécouper en au moins trois US (exports/formats · paiement par club · podiums). Les équipes relèvent d'EPIC-13, à ne pas anticiper ici.
- **Dépend de** : E09US001, E09US003, E08, E06US004, **E10US005** *(journal d'audit — ~~« E11 (audit) »~~ était faux : l'audit métier est dans **EPIC-10**, `E10US005`, livrée ; EPIC-11 est l'exploitation. Corrigé le 08/08/2026)* · **Jalon** : J3 · **Origine** : questionnaires A08, A16, A17, A18, 04/08/2026

---

### E16US008 — Feu vert : agir depuis la ligne du duel qui bloque
*En tant qu'*organisateur, *je veux* que les **actions** soient sur la ligne du duel qui a un manquement, *afin de* débloquer sans quitter l'écran.
- **Contexte** : A15, évolution : *« les manquements appartiennent à la ligne du duel qui a des manquements, ainsi que ses actions »*. Question 5, qui déclare un forfait : *« admin »*. Question 3, qui appuie sur le bouton : *« un admin, mais suivant la configuration on doit choisir ce qui attend un déclenchement manuel (les phases ou le tour) : selon la configuration, soit ça se déclenche automatiquement quand les conditions sont remplies, soit c'est un déclenchement manuel. »*
- **CA — actions sur la ligne** : chaque duel bloqué porte, à côté de son manquement déjà nommé, l'action qui le lève.
- **CA — forfait par l'admin** : déclarer un forfait de duel devient possible depuis l'administration. ⚠️ Aujourd'hui l'endpoint (`POST /forfaits/duel`) exige un **jeton scoreur** : c'est une décision d'**autorisation**, à trancher explicitement (élargir à l'admin, ou ouvrir une route admin).
- **CA — déclenchement configurable** : par phase ou par tour, le lancement est **automatique** (conditions remplies) ou **manuel**.
- **Notes** : les manquements sont **déjà** nommés par ligne (`afficheDuel`) — c'est le volet « actions » qui manque. Le déclenchement automatique est un vrai changement de moteur : à cadrer séparément. **Redécoupable**.
- **Dépend de** : E12US002, E04US015, E10US001 · **Jalon** : J3 · **Origine** : questionnaire A15, 04/08/2026

---

### E16US009 — Écran de salle : régler ce qui défile, et défiler ce qui ne tient pas
*En tant qu'*organisateur, *je veux* **régler la durée d'une page** projetée et voir les archers **défiler sous le podium**, *afin d'*adapter l'écran à ma salle sans toucher au code.
- **Contexte** : P06, question 2 : *« on peut dire que 20 s (réglable) par écran de liste de noms est correct »* — la pagination est livrée, la **durée est figée à 20 s dans le code**. P07 : *« ok pour les 3 premiers toujours visible, mais défilement de tous les autres archers dessous »* ; le classement projeté montre aujourd'hui une tête figée mais ne fait pas défiler la suite. P07, question 2 : *« je n'ai pas vu le logo sur la maquette »* — l'identité du tournoi n'est pas encore posée sur l'écran de salle.
- **CA — durée réglable** : la cadence d'une page de noms se règle par écran, à côté du déroulé de vues déjà configurable.
- **CA — défilement sous la tête figée** : les archers hors des trois premiers défilent d'eux-mêmes.
- **CA — nombre de noms par page** : `NOMS_PAR_PAGE = 40` est un choix à confirmer **sur le vidéoprojecteur réel** ; le rendre réglable ou le mesurer.
- **CA — logo** : l'identité (événement + club, cf. E16US006) apparaît sur l'écran de salle.
- **Notes** : la durée réglable demande un champ sur la configuration d'écran (API `ecrans`). Le défilement est front. Relire [ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) : tout y est piloté par **état lu**, un réglage local contredirait le principe.
- **Dépend de** : E07US004, E07US008, E01US016 · **Jalon** : J3 · **Origine** : questionnaires P06, P07, 04/08/2026

---

### E16US010 — Chercher partout, et voir d'avance ce qui bloque un lancement
*En tant qu'*organisateur, *je veux* une recherche qui **change de nature selon le moment** et une alerte de complétude **dès la liste des tournois**, *afin de* ne pas découvrir un blocage en ouvrant l'écran.
- **Contexte** : A02, question 2 : *« dans le cycle préparation et après, on doit pouvoir faire une recherche sur tout item-entité, par une liste déroulante et un champ de saisie ; une complétion de recherche montre une liste des items possibles avec la possibilité de cliquer dessus et d'ouvrir la fiche en modification. Dans le cycle déroulé du tournoi, on peut faire une recherche d'un archer du tournoi et ouvrir sa fiche en consultation avec ses informations du tournoi, puis possibilité d'agir dessus si besoin. »* A02, question 1 : *« sur cette liste laisse une pastille d'alerte si tout n'est pas complet ; alerte forte si impossible de lancer en l'état. »* A09 : *« c'est une barre de recherche qui doit rester accessible sur tout le déroulé du pilotage et se concentrer sur le tournoi en cours sélectionné, donc elle ne doit pas polluer le reste de l'écran »* ; doublons : *« on avertit seulement… une simple icône cliquable sur la ligne de l'archer peut suffire »*.
- **CA — recherche transverse hors pilotage** : entité choisie dans une déroulante + champ de saisie, complétion, ouverture de la fiche **en modification**.
- **CA — recherche d'archer en pilotage** : scopée au tournoi, fiche **en consultation** puis action.
- **CA — pastille de complétude en liste** : deux niveaux — incomplet (avertissement) et **impossible à lancer** (alerte forte).
- **CA — doublons discrets** : une icône cliquable sur la ligne de l'archer, qui montre le problème et propose l'action, au lieu d'un écran dédié qui pollue.
- **Notes** : la recherche d'archer existe (E12US006), scopée au tournoi — c'est la **variante toutes entités** qui manque, et elle était déjà annoncée « lot suivant » dans `CoquilleAdmin`. La pastille demande un **agrégat serveur** : la complétude est aujourd'hui un appel **par tournoi**, en faire N sur la liste ne tient pas.
- **⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))** : cette US rouvre des maquettes qui disent encore « position » pour la place d'un archer. **Corriger le mot en « couloir de tir » dans le même diff** — maquette et écran.
- **Dépend de** : E12US005, E12US006, E02US005 · **Jalon** : J3 · **Origine** : questionnaires A02, A09, 04/08/2026

---

### E16US011 — Ce que trois questionnaires « validés » demandaient quand même
*En tant qu'*organisateur, *je veux* que les règles énoncées dans les questionnaires validés soient tenues, *afin de* ne pas croire acquis ce qui n'a jamais été codé.
- **Contexte** : ⚠️ **cette US existe parce que le tri initial était faux.** Le lot du 05/08/2026 avait rangé S06, S08 et S09 parmi les « validés tels quels, aucune évolution demandée » — au motif que leur verdict était ✅. Or leur verdict porte sur **l'écran**, pas sur les réponses aux questions ciblées, et celles-ci énoncent des **règles** qui ne sont nulle part dans le code. Défaut relevé par la revue adversariale du 05/08/2026, et c'est le plus coûteux du lot : un retour classé ✅ n'est **jamais relu**.
- **CA — S06 (routage)** : *« 3 mn si un autre tour suit »* — le panneau de routage doit rendre la tablette à la saisie au bout de trois minutes lorsqu'un tour suit. `PanneauRoutage` n'a aucun minuteur. Et *« visible si classement établi »* pour la place finale du perdant.
- **CA — S08 (validation cible)** : *« plus de modification une fois validé »*. ⚠️ **Cela contredit un endpoint vivant** (`POST /api/v1/saisie/…`, correction d'une volée verrouillée) : c'est un arbitrage, pas une implémentation — à trancher avant de coder. Et *« [une validation peut être annulée] oui, par admin et scoreur »*, qui n'a aucune route.
- **CA — S09 (états système)** : *« hiérarchie → archer < scoreur < admin »* pour trancher un conflit de modification concurrente. C'est une politique d'autorisation, énoncée sans ambiguïté et non implémentée.
- **CA — A09 (inscriptions)** : *« on ne permettra pas 2 fois le même numéro de licence »*. ⚠️ **Contredit [ADR-0014](../docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md) et ADR-0015**, qui écartent explicitement le champ licence. À trancher, pas à implémenter en l'état. Et *« placement manuel obligatoire, mais seulement si possible »* pour un retardataire.
- **CA — A02** : *« une fois un tournoi choisi, on arrive sur la page du déroulé du tournoi avec un accueil qui reprend les informations du tournoi **par départ dans un grand encart** (mettre toutes les informations utiles au déroulé) »*. Seul le bandeau a été livré ; l'encart par départ, non.
- **CA — P05** : *« [les horaires prévisionnels] seulement pour les départs des différentes phases du tournoi, les autres sont trop imprévisibles »*.
- **Notes** : ⚠️ **US de rattrapage — à découper avant de prendre.** Elle rassemble sept règles hétérogènes dont deux sont des **contradictions à arbitrer** (S08 vs endpoint existant, A09 vs ADR-0014/0015) et une une **politique d'autorisation** (S09). Ne pas la coder telle quelle : la lire, poser les deux questions, puis redécouper. Elle est ici pour que rien ne se reperde, pas comme un plan de travail.
- **⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))** : cette US rouvre des maquettes qui disent encore « position » pour la place d'un archer. **Corriger le mot en « couloir de tir » dans le même diff** — maquette et écran.
- **Dépend de** : E04US018 (routage), **E04US002** (saisie & validation de qualification — ~~`E04US003`~~ **n'existe pas** : l'identifiant a été absorbé par `E04US002` le 17/07/2026 à la refonte de maille. Corrigé le 08/08/2026), E10US001 (rôles), E02US002 (inscriptions) · **Jalon** : J3 · **Origine** : revue adversariale du 05/08/2026 sur le tri des questionnaires

---

### E16US012 — La famille des écrans « prêt à… »
*En tant qu'*organisateur, *je veux* qu'à chaque étape du tournoi un écran me dise **si je peux passer à la suivante, et sinon ce qui manque**, *afin de* piloter la journée par jalons plutôt qu'en fouillant les rubriques.

- **Contexte** : née de l'arbitrage d'**E16US003** (07/08/2026). Le commanditaire, interrogé sur le seul libellé de l'écran de complétude, a répondu plus large : *« je viserais plus 2 notions : prêt à démarrer, prêt à terminer, et prêt à archiver, prêt à exporter »*. E16US003 n'a livré **qu'un** membre de cette famille — l'écran de complétude sportive, renommé « **Prêt à terminer ?** » — et a explicitement refusé d'improviser les autres.
- **CA — une forme commune** : chaque écran « prêt à … » répond à **une** question binaire (« puis-je passer à l'étape suivante ? »), liste **ce qui manque** sous forme d'états (pas de barre de progression, `D-17`), et porte **l'action** correspondante. Il **avertit sans bloquer** (`D-15`).
- **CA — les quatre membres** : *prêt à démarrer*, *prêt à terminer*, *prêt à archiver*, *prêt à exporter*. ✅ **Tranché au cadrage du 23/08/2026** : **une forme unique paramétrée** par le membre — un seul type de réponse, une seule route, une seule coquille front — et non quatre écrans jumeaux. La question elle-même se dérive du membre (« Prêt à `<verbe>` ? ») côté serveur, pour que le front ne tienne aucune table de libellés. ⚠️ **Les quatre ne sont PAS de même nature**, constat fait en instruisant et absent de la fiche d'origine : *démarrer*, *terminer* et *archiver* gardent une **transition** du cycle de vie (ADR-0026 §2), *exporter* garde un **geste répétable** qui ne franchit aucun statut. Ce qu'ils partagent n'est donc pas la machine à états, c'est la question posée à l'organisateur — [ADR-0096](../docs/adr/0096-un-jalon-enumere-ses-gardes-au-lieu-de-les-lever.md) §4.
- **CA — ce qui manque ≠ ce qui bloque** *(ajouté le 23/08/2026, découvert en écrivant les tests depuis le CA)*. « Répondre à une question binaire » et « avertir sans bloquer » (`D-15`) ne sont pas compatibles avec un seul drapeau : un tournoi **sans déroulé composé démarre** aujourd'hui, l'écran doit donc le signaler **sans** le refuser. La réponse porte deux champs — `pret` (rien ne manque) et `bloquant` (l'action passera-t-elle quand même) —, et c'est ce second qui porte l'**asymétrie de la famille** : *démarrer* a des gardes de **contenu** (créneaux, effectif), *terminer* n'en a aucune. ⚠️ **Corrigé en revue le 23/08/2026** : « aucune garde » était faux **du statut**. `ServiceTournois` lève `TransitionStatutInvalide` avant toute autre garde — *terminer* n'accepte qu'un tournoi *en cours* (un tournoi **en pause** est refusé) et *démarrer* qu'un tournoi *prêt*. ⚠️ Ne pas confondre avec la portée du **jalon**, qui répond de l'étape et se pose donc dès *brouillon* (CA suivant) — c'est la garde de la **transition** qui est décrite ici. C'est la garde **commune aux trois membres qui gardent une transition**, et c'est la **seule** d'`archiver` : sans elle, le membre suivant n'aurait rien à énumérer. Le jalon la porte donc aussi. ⚠️ **Aucun bouton n'est jamais grisé** sur la foi de ces champs : le refus appartient au serveur (arbitrage E05US021), un front qui garde devient la seconde source que le CA interdit.
- **CA — un jalon répond de l'ÉTAPE, pas du prochain clic** *(ajouté le 23/08/2026, relevé en revue)*. Deux transitions mènent au départ : `vers-pret` (garde : ≥ 1 créneau) puis `demarrer` (garde : l'effectif). « Prêt à démarrer ? » répond de **l'arrivée** — c'est tout l'intérêt de l'US, annoncer l'effectif avant le **premier** clic plutôt qu'au second. Conséquence à ne pas manquer : depuis *brouillon*, l'écran peut dire « pas encore » pendant que le bouton « Marquer prêt » passera sans problème. L'écran doit donc dire **quand** le refus tombe — et **ce moment n'est pas le même pour toutes les gardes** : les créneaux sont réclamés « dès le passage en « prêt » » (`vers_pret`), l'effectif « au démarrage ». Le moment est celui de la **garde qui bloque en premier**, dérivé côté serveur, jamais écrit à l'écran ; « sera refusé » tout court se lit comme un refus immédiat que le clic suivant dément. *(Précision reversée le 23/08/2026 en 3ᵉ passe de revue : la 1ʳᵉ rédaction prescrivait une phrase unique — « au démarrage » — qui est fausse sur l'état initial de tout tournoi neuf.)*
- **CA — ce qui manque est chiffré ET expliqué** *(ajouté le 23/08/2026, relevé en revue)*. La ligne dit *quoi* (« Inscrits · 8/34 ») ; l'écran dit aussi *pourquoi ce chiffre-là*, avec **la phrase du refus serveur elle-même** (`message_de_refus`). Sur un tournoi à deux créneaux de 40 et 8, « 8/34 » seul semble contredire le total affiché ailleurs — c'est le défaut qu'ADR-0075 a mis treize mois à révéler, et `D-16` / `P-4` le disent : « une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection ».
- **CA — ce que contient la liste ne suit pas la garde, et pas de la même façon selon le membre** *(tranché le 23/08/2026 en revue, reversé ici)*. Chez *prêt à démarrer*, la liste **est la préparation** : un tournoi déjà lancé, annulé ou archivé n'a plus rien à préparer, donc **plus rien à lister**. Chez *prêt à terminer*, elle **est l'état sportif** — « où en est la qualification » se lit à **tout** statut, et c'est précisément ce que l'organisateur vient voir pendant la pause déjeuner. Hors transition offerte, ce sont `pret`, `bloquant`, `detail` et le champ **`question_posee`** qui portent la garde — jamais la liste. ⚠️ **Un membre neuf tranche explicitement de quel côté il tombe** : ne pas déduire « la question se pose » de la longueur de la liste. *(Cette puce a coûté trois allers-retours : vidée puis rétablie, l'assertion de test a été écrite dans les deux sens en se réclamant chaque fois du CA — qui, lui, ne disait rien.)*
- **CA — sans doublonner ce qui existe** : la **frise du cycle de vie** (E14US001, 7 statuts, [ADR-0026](../docs/adr/0026-cycle-de-vie-du-tournoi-sept-statuts.md)) porte déjà les transitions et leurs gardes ; le **feu vert** (`E16US008`) est déjà un « prêt à lancer un tour ». Ces écrans doivent s'y **brancher**, pas en fabriquer une seconde source. ⚠️ **Le vrai problème était plus profond que la navigation**, et il n'était pas dans cette fiche : les gardes existent, mais **ne sont lisibles qu'en échouant** — `vers_pret` lève `TournoiSansDepart`, `demarrer` lève `EffectifInsuffisantPourDemarrer`, et une exception ne rend que le **premier** manquement rencontré. Un jalon les **énumère** sans les exécuter. Là où le calcul ne peut pas être mécaniquement partagé, l'accord écran ↔ garde est **épinglé par un test de cohérence**, jamais laissé à la vigilance.
- **Notes** : ✅ **ADR-0096 écrit** — l'« ADR probable » l'était bien. La tension avec l'ossature à trois axes ([ADR-0058](../docs/adr/0058-decoupage-de-l-admin-en-trois-axes-d-activite.md)) est tranchée à son §4 : un jalon **ne déménage aucune activité**, il pose une question là où l'activité se fait déjà — la famille peut donc traverser pilotage et gestion sans contredire les axes. ✅ **La consigne d'ordre est honorée** : `E16US007` et `E16US008` n'ont plus de forme à inventer. **Redécoupée par membre**, comme la fiche l'autorisait : cette tranche livre le **mécanisme** + `démarrer` (membre neuf) et migre `terminer` (existant) sur la coquille commune — deux occurrences réelles, pas une abstraction sur pari. ⚠️ **`archiver` et `exporter` restent à instruire** : ils existent dans l'énumération mais répondent `404` (`jalon_non_instruit`), jamais une liste vide qui se lirait « rien ne manque, allez-y ». ⚠️ **Angle mort assumé** : la frise du cycle de vie porte toujours ses propres boutons « Démarrer »/« Terminer » — deux endroits pour le même geste. À instruire quand `archiver` rejoindra la famille, la frise portant aussi ce bouton.
- **Dépend de** : E14US001, E16US003 · **Jalon** : J3 · **Origine** : arbitrage du commanditaire en revue d'E16US003, 07/08/2026

---

## Retours **écartés** (traités, sans US)

Consignés ici pour qu'aucun questionnaire ne reste sans réponse.

- **A04 — « la frise du cycle de vie n'est peut-être pas utile tout le temps »** : non appliqué. La
  frise **porte les boutons d'action** (démarrer, terminer) ; la replier ou la borner par axe
  risquerait de masquer l'action principale du jour J. Le mot « peut-être » du questionnaire marque
  d'ailleurs une hésitation, pas une demande. À rouvrir si la gêne se confirme à l'usage.
- **A03, A13, A19, S03, S04, S07** : validés ✅, et leurs réponses aux questions ciblées ne
  demandent rien qui ne soit déjà livré. ⚠️ **S06, S08 et S09 ont été retirés de cette liste** le
  05/08/2026 : leur verdict ✅ portait sur l'écran, mais leurs réponses portaient des règles — elles
  sont passées en `E16US011`.
- **Questions restées sans réponse au questionnaire**, à reposer si le sujet revient : A02 Q3
  (« espace » / « étape » / « Résultats »), Q4 (le mot pour un niveau qui boucle) et Q5 (référence ou
  copie des briques à l'assemblage) ; A03 Q1-Q2 ; A05 Q1-Q2 ; A06 Q1-Q2 ; A07 Q1 ; A08 Q2 (comment
  un scoreur reçoit son accès) ; A13 Q1-Q3 ; A15 Q4 (lancement duel par duel) et Q6 (ce qu'il faut
  voir avant d'appuyer) ; A19 Q1-Q2 ; P04 Q1-Q2 ; S03 Q1-Q3 ; S04 Q1-Q2 ; S07 Q1-Q2. Aucune n'est
  bloquante aujourd'hui. **A02 Q5 mérite d'être reposée en priorité** : « si tu changes un tarif en
  2027, le tournoi 2026 archivé doit-il bouger ? » décide du modèle de l'assemblage.
