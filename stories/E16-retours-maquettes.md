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
- **⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))** : cette US rouvre des écrans dont la maquette dit encore « position » pour la place d'un archer. **Corriger le mot en « couloir de tir » dans le même diff** — maquette et écran. Le laisser filer rejouerait le refus d'A10 sur un autre écran.
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
    maximale du plan**, jamais écrit en dur. ⚠️ Il est cependant **borné par `POSITIONS`**
    (`Math.min`) : la grille n'est pas le porteur du plafond `A`→`D`, c'est `POSITIONS` qui l'est
    côté front et `CAPACITE_CIBLE_MAX` côté domaine (`DETTE-010`, marqueurs posés par cette US).
    Le `min` protège d'un désaccord front/serveur, pas d'un cas courant — le serveur refuse déjà
    toute capacité hors `[1, 4]`.
  - **Repères sur deux lignes** (club, puis catégorie et blason), tronqués **dans une case** et
    entiers dans la réserve. ⚠️ Tranché en 2ᵉ passe de revue : une ligne unique tronquée ne rendait
    que le club à 1366 px, donc la **mixité** (RG-3) sans jamais le **cloisonnement** (RG-4) — la
    moitié du CA.
- **CA — la réserve est un panneau collant**, à droite du plan, ✅ **ajouté au cadrage du
  24/08/2026** : le glisser-déposer HTML5 natif **ne fait pas défiler la page**, donc une réserve en
  pied d'écran rend « sortir un archer de la cible 37 » impraticable — soit exactement le geste que
  le questionnaire demandait de simplifier. Une cible par ligne allonge le plan, et aurait donc
  **aggravé** ce défaut si la réserve était restée en bas. Sous **78 rem** de fenêtre (~880 px de
  colonne réelle : une *media query* mesure le viewport, la coquille admin en retranche 368 px), elle
  repasse sous le plan ; sous 62 rem, les couloirs passent à deux par ligne. La bande
  une-cible-par-ligne, elle, ne cède **jamais** — c'est le CA. *(Seuil corrigé en 2ᵉ passe de revue :
  la 1ʳᵉ version mesurait le viewport comme s'il était la colonne de contenu, et ne basculait donc
  jamais assez tôt.)*
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
- ~~**⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))**~~ — ✅ **vérifié le 24/08/2026 : le reliquat n'existe pas.** `maquettes/a11-placement.html` — la planche de **cette** US — ne contient pas une seule occurrence de « position » au sens de la place d'un archer (seulement « proposition »), et les deux écrans rouverts exposent déjà `aria-label="Couloir de tir A"`. Les identifiants de code (`POSITIONS`, `place.position`, `case__position`) restent, mais ils ne sont **pas visibles par l'utilisateur** et relèvent de [`DETTE-042`](../docs/dette.md), qui assume explicitement cet écart jusqu'à E01US019. Même cas de figure qu'`E16US004`, dont la liste de maquettes était fausse pour la même raison : le balayage avait déjà eu lieu. ~~L'avertissement reste **vif** sur `E16US010` et `E16US011`, où il n'a pas été vérifié.~~ ✅ **Éteint le 10/09/2026** : vérifié une 5ᵉ et dernière fois au découpage d'`E16US011`, faux là aussi. Il n'est reconduit sur aucune US. *(E16US010 l'a vérifié le 29/08/2026 : faux là aussi — 4ᵉ fois d'affilée.)*
  - ⚠️ **Cette puce a d'abord été barrée dans le bloc d'`E16US004`** (relevé par trois axes de revue le 24/08/2026) : le texte de l'avertissement est identique dans **deux** blocs (`E16US004` et celui-ci ; deux autres en portent une variante voisine), et un remplacement de la première occurrence a visé la mauvaise. Une collision à deux suffit — c'est même le cas le plus traître, puisqu'on ne s'en méfie pas. Une US livrée s'est ainsi retrouvée annotée d'une vérification portant sur une planche qui n'est pas la sienne, pendant que `E16US005` sortait avec un ⚠️ ouvert que le tracker déclarait fermé.
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

### E16US006 — L'identité visuelle du tournoi : deux logos, deux couleurs
*En tant qu'*organisateur, *je veux* déposer **le logo de mon tournoi, celui de mon club et mes deux couleurs**, *afin que* l'écran de salle et le téléphone des archers affichent **ma compétition**, pas un logiciel.

> ⚠️ **Fiche recadrée le 25/08/2026 au cadrage, et le recadrage l'a presque entièrement réécrite.**
> Ce qui suit remplace la version d'origine (« Patrimoine : distinguer l'officiel FFTA du local, et
> porter le logo du club »), dont **trois CA sur quatre étaient caducs ou déjà livrés** — constat
> fait en vérifiant dans le code du jour, pas en relisant la fiche. Le détail est en « Ce que le
> cadrage a démenti », plus bas : c'est la partie qui vaut d'être lue.

- **Contexte** : A05 : *« ajouter un champ de plus pour le logo du club qui organise le tournoi, en plus du logo du tournoi ; bien sûr cela reste optionnel »*. Le premier logo n'existait pas — `E01US016` (identité visuelle) était ⬜ —, d'où la **fusion des deux US** décidée par le commanditaire : livrer « un second logo » sans le premier n'a pas de sens. `DV-06` ferme `Q-D8` : *« identité par tournoi = logo + 2 accents, le système dérive tout le reste »*.
- **CA — deux logos, tous deux facultatifs** : celui de l'**édition** et celui du **club organisateur**, distincts ; déposer l'un ne remplace pas l'autre. SVG ou PNG, 512 Ko au plus, **utilisés tels quels**.
- **CA — deux couleurs d'accent, et rien d'autre** : le système **dérive** aplat, contour et variantes de texte, en thème **sombre et clair** — teinte et saturation conservées, clarté ajustée jusqu'au seuil AA (`DV-05`).
- **CA — contrôle de contraste chiffré et non bloquant** (`P-4`) : la couleur exacte est **acceptée** en aplat, une variante AA est dérivée pour texte et bordure. **Rien n'est jamais refusé** sur un contraste faible — le refuser retirerait sa marque à un club dont la charte est faible. Le message distingue **deux niveaux** *(tranché en cours d'US, reversé ici le 26/08/2026)* : « trop faible pour du texte » quand seul le seuil de 4,5:1 est manqué, « ni même pour un contour » quand celui de 3:1 l'est aussi. Le CA d'origine ne distinguait pas ; l'organisateur qui choisit sa charte, si — les deux situations n'appellent pas la même décision.
- **CA — un logo corrigé se voit tout de suite** *(tranché en cours d'US, reversé ici le 26/08/2026)* : redéposer un fichier par-dessus un logo existant met la vignette à jour **sans rechargement de page ni vidage de cache**, sur l'écran de préparation comme sur les surfaces déjà ouvertes (`P-3` : modifiable tournoi en cours). L'adresse d'un logo est versionnée par l'**empreinte de son contenu** — cf. [ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md) § Conséquences.
- **CA — un logo doit se suffire à lui-même** *(tranché en cours d'US, reversé ici le 26/08/2026)* : « utilisés tels quels » ne veut pas dire « acceptés tels quels ». Un fichier est **refusé, en le disant**, s'il porte de quoi **exécuter** (script, gestionnaire `on…`, lien `javascript:`, `<foreignObject>`, animation SMIL, `@import`) ou d'**aller chercher un document ailleurs** (`<use>`/`<image>`/`url()` pointant hors du fichier, entité ou DTD externe), et si un PNG n'a pas la structure d'un PNG. Restent **acceptées** les formes normales d'un export vectoriel : réutilisation locale (`<use href="#symbole">`), raster embarqué (`data:image/png…`), `<!DOCTYPE PUBLIC>` et entités littérales d'Illustrator, texte accentué échappé. ⚠️ Le refus au dépôt est la **première** des trois barrières, jamais la seule : les en-têtes de la route (`CSP: default-src 'none'`, `nosniff`) et le rendu en `<img>` portent le reste — cf. [ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md) §2.
- **CA — les couleurs sémantiques ne sont jamais personnalisables** (`DV-03`) : alerte, succès, info appartiennent au produit. Ni les neutres (verrou 2 de `DV-06`).
- **CA — défaut = identité du club si rien n'est fourni**, et **« hérité » se distingue de « choisi »** : un tournoi dont on a seulement déposé le logo ne se présente pas comme configuré.
- **CA — portée : le public et l'écran de salle uniquement** (`D-27`) — jamais l'admin ni la saisie.
- **CA — aperçu sur les surfaces réelles**, pas un nuancier (`DV-05`), et **modifiable à tout moment**, tournoi en cours compris (`P-3`).
- **Arbitrages du commanditaire, 25/08/2026** (tous reversés ici) :
  - **`Q-UX10` fermée** — le logo est fourni **déjà calibré**. L'application ne recadre, ne détoure ni ne redimensionne : elle **refuse en le disant**. Donc aucune dépendance de traitement d'image (règle 11).
  - **Stockage en base** (blob), pas sur le disque — [ADR-0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md) §1. Ferme `Q-UX11` par construction.
  - **Pas d'import de fichier** pour alimenter un référentiel « officiel » (question A06 restée ouverte) : hors périmètre.
- **Ce que le cadrage a démenti** — les quatre CA d'origine, vérifiés dans le code :
  - ⚠️ **« origine officielle FFTA / locale » était DÉJÀ LIVRÉ** par `E01US023` : `domain/patrimoine.py` porte l'enum `OrigineBrique`, `Categorie` et `Blason` la portent en champ, l'origine **suit** à la copie et à la promotion, et `Bibliotheque.tsx` rend déjà **deux listes séparées** avec la réserve d'[ADR-0060](../docs/adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) §4 écrite en clair. `FormatTournoi` la porte aussi, sans que le CA l'ait demandé.
  - ⚠️ **« les clubs portent une origine » n'a pas de porteur.** Un `Club` n'a **pas** de `tournoi_id` : portée globale, aucune bibliothèque, ce n'est pas une brique au sens d'ADR-0060. Un import en masse existe (coller une liste), mais tout ce qui y entre est indifférencié — et sans import FFTA (écarté ci-dessus), **rien ne peut alimenter l'« officiel »**. CA **caduc**.
  - ⚠️ **« les barèmes portent une origine » n'a pas de porteur non plus.** `BaremeQualification` est un **value object** (`nb_volees` × `nb_fleches_par_volee`), réglé par phase, sans identité ni persistance propre : il n'existe aucune liste de barèmes à afficher ou filtrer. Ce que le questionnaire visait est très probablement le **format de tournoi**, qui porte déjà l'origine. CA **caduc**.
  - **Reliquat non pris, à instruire si le besoin se confirme** : sur les écrans **par tournoi** (`Categories.tsx`), `origine` est dans le DTO mais **n'est pas rendue** — seule la bibliothèque l'affiche. Personne ne l'a demandé ; c'est noté pour ne pas se reperdre.
- **Notes** : migration Alembic `0050` (table `identite_tournoi`). ⚠️ **L'accent secondaire est posé mais son usage reste mince** — aucune planche ne dit encore ce qu'il doit peindre, et l'inventer aurait été du design (cf. ADR-0097 § Conséquences).
- **Dépend de** : ~~E01US023~~ (constat : rien à en tirer), **E01US016 — absorbée** · **Jalon** : J2 · **Origine** : questionnaires A05, A06, 04/08/2026 · **ADR** : [0097](../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md)

---

### E16US007 — Exports : choisir le format de chaque document
*En tant qu'*organisateur, *je veux* choisir **le format** de chaque document que je sors, *afin de* ne pas dépendre d'un format figé décidé à l'avance.
- **Contexte** : A18 : *« chaque ligne d'export doit proposer plusieurs formats possibles (CSV, EXCEL, PDF…) »* et, sur les exports attendus : *« ça peut évoluer et donc être paramétrable »*. ✅ **Découpée le 30/08/2026 au cadrage**, comme les Notes d'origine le prescrivaient : cette fiche garde le **volet formats** ; les podiums configurables partent en `E16US014` et le QR par scoreur en `E16US015`.
- **CA — formats** : chaque export propose ses formats disponibles ; l'ajout d'un format ne demande pas de toucher l'écran.
- **CA — le catalogue est servi par le serveur** *(ajouté au cadrage du 30/08/2026)*. Le CA ci-dessus n'est **vérifiable** que si l'écran ne tient aucune liste de formats : c'est le serveur qui énumère, pour chaque export, ce qu'il sait produire. ⚠️ Le catalogue porte les **formats**, pas les **URL** ni les paramètres (tri, départ) — ceux-là sont des choix d'IHM. Ajouter un *format* ne touche donc pas l'écran ; ajouter un *export*, si — et ce n'est pas ce que le CA demande.
- **CA — un export n'offre que les formats qui ont un sens** *(ajouté au cadrage du 30/08/2026)*. La liste est **par export**, pas globale : une **feuille de marque** se remplit à la main, elle n'existe qu'en PDF ; une **liste** part au tableur, elle existe aussi en CSV. Un catalogue où toutes les entrées offriraient les mêmes formats ne prouverait rien.
- **Notes** : **backend + API + l'écran « Exports & impressions »** — périmètre front arbitré au cadrage du 30/08/2026 : le catalogue est servi pour les exports de cet écran, les boutons d'archive, d'étiquettes QR et de cartes scoreur restent dans leur contexte de travail (ADR-0058). ⚠️ **Formats livrés : PDF et CSV, sans nouvelle dépendance** (ReportLab est déjà là, `csv` est stdlib) — arbitrage du commanditaire du 30/08/2026 : `xlsx` demanderait `openpyxl`/`xlsxwriter`, donc la règle 11, et la plupart des tableurs ouvrent un CSV. **Il reste dû**, cf. `E16US016`. ⚠️ **Deux CA d'origine étaient CADUCS**, vérifié dans le code au cadrage : *paiement groupé par club* est livré depuis `E08US002` (`recap_par_club` / `marquer_club`, `api/v1/paiements.py`), ⚠️ **et *audit consultable en cours de tournoi* ne l'est PAS — conclusion corrigée en revue (axe D)** : le jugement avait été porté sur le **serveur** (`ServiceAudit.lister` n'a aucune restriction de statut, la route existe) alors que le CA est écrit du point de vue de l'organisateur. **Aucun écran ne consomme la route** (`grep` sur `frontend/src` : zéro appelant, pas de feature `audit`) : le journal n'est consultable **à aucun moment**, ni pendant ni après. Le CA reste **dû**, reporté en `E16US016` — c'est le piège exact de la règle 9, un CA jugé caduc sur une lecture partielle. ⚠️ **Le palmarès est hors tranche** : sa route s'appelle littéralement `/palmares.pdf` et elle est **publique**, donc lui ajouter un format est un renommage d'API publique — arbitrage à part, et `DETTE-031` y multiplie un coût de recalcul déjà signalé. Cf. `E16US016`.
- **Dépend de** : E09US001, E09US003 · **Jalon** : J3 · **Origine** : questionnaire A18, 04/08/2026 — découpée le 30/08/2026

---

### E16US014 — Podiums configurables
*En tant qu'*organisateur, *je veux* configurer **ce que couvre un podium**, *afin de* récompenser ce que mon club a décidé de récompenser.
- **Contexte** : sortie d'`E16US007` au découpage du 30/08/2026. A16 : *« podium configurable, tout doit être possible »* (par catégorie, scratch, par club, par équipe). ⚠️ **Découpée en deux au cadrage du 31/08/2026** (maille INVEST) : cette fiche livre les podiums d'**archers** — le regroupement change, le calcul ne change pas —, et le classement des **clubs entre eux** part en `E16US017`, parce que c'est un classement **neuf** et non un regroupement.
- **CA — plusieurs portées cohabitent** : l'organisateur choisit ce qu'il récompense parmi *catégorie*, *scratch* et *club* ; les portées se **cumulent** (l'écran empile les blocs demandés) et non s'excluent — *« tout doit être possible »* (A16, tranché au cadrage du 31/08/2026). **N'en cocher aucune est un réglage valide** : le tournoi qui ne remet rien affiche son classement sans podium. Défaut : *catégorie* seule, à l'identique d'E06US004 — un tournoi existant ne change pas d'affichage.
- **CA — la profondeur se règle** : le nombre de places d'un podium est un réglage, défaut **4** (la valeur d'E06US004, portée par `PROFONDEUR_PODIUM_PAR_DEFAUT` (`domain/podium.py`)). La profondeur est bornée **1 à 64**, au domaine et non à la frontière (le refus reste un 422 métier, parti d'`ReglagePages`/E16US009) ; une profondeur hors bornes est refusée : « ne rien récompenser » se dit en ne cochant aucune portée, pas en demandant zéro place. Une **seule** profondeur pour toutes les portées actives (arbitrage du 31/08/2026 : une profondeur par portée n'a pas de demandeur).
- **CA — les blocs d'une même portée sortent dans l'ordre du palmarès** *(arbitrage du 31/08/2026, reversé après revue)* : un groupe est **situé par son meilleur archer**, si bien que le club du vainqueur passe devant. L'ordre **entre** portées, lui, est fixe (toutes catégories, puis catégorie, puis club) : deux réglages équivalents doivent rendre le même écran.
- **CA — un bloc sans place décernée reste affiché à l'écran, et disparaît du PDF** *(arbitrage du 31/08/2026, reversé après revue)* : à l'écran, un groupe qui s'efface se lit comme un groupe sans archers alors qu'il est en cours (parti `P-3`) ; sur le papier, un tableau à en-tête seul ne veut rien dire. ⚠️ **L'écran distingue « pas encore » de « jamais »** : avec la portée club, la plupart des clubs n'ont personne au tableau (`DETTE-028`), et « les finales ne sont pas toutes tirées » y serait faux deux fois.
- **CA — le podium sans regroupement se dit « Toutes catégories »** *(tranché en revue le 31/08/2026)* et **jamais « Scratch »** : le glossaire réserve ce mot à un **libellé de catégorie** (arc nu). Un club qui nomme ainsi sa catégorie arc nu aurait vu deux blocs de même titre sur la même page du PDF. Le **code** de la portée reste `scratch`, cohérent avec `rang_scratch`.
- **CA — un podium est celui du TOURNOI, pas de la vue** *(bloquant de revue, 31/08/2026)* : le filtre par catégorie d'E06US001 restreint le **classement** affiché, jamais les blocs de podium. Les composer sur la vue filtrée rendait un « Toutes catégories » amputé — vide, avec « Podium en cours » sur un tournoi terminé — jusque sur le PDF affiché au mur.
- **CA — tant qu'aucune phase à duels ouverte n'a livré, aucun bloc n'est définitif** *(arbitrage du commanditaire, 01/09/2026, reversé après la 4ᵉ passe de revue)* : pendant toute la qualification, personne n'est « en lice » — les blocs annonçaient « aucun duel n'a départagé ce groupe », la phrase du **définitif**, sur le provisoire le plus long de la journée. Le créneau porte donc le fait et **prime** sur le groupe. ⚠️ **La règle exacte** : les **trois** familles à duels comptent (tableau, poules/suisse/colline, Big Shoot Off) ; le fait retombe au **premier résultat lisible**, pas à la fin du tournoi — l'attente se lit ensuite archer par archer, ce qui est juste pour un groupe jamais entré au tableau ; et les phases **terminées** en sont exclues, sans quoi une consolante abandonnée laissait « en cours » pour toujours.
- **CA — « ce tournoi est-il classé ? » est dit par le serveur, jamais déduit** *(4ᵉ passe de revue)* : ni les podiums (qu'un réglage sans portée vide à bon droit) ni les lignes affichées (que le filtre restreint) ne répondent à cette question. Quatre gardes successives ont tenté de l'inférer et se sont trompées dans quatre coins différents.
- **CA — les trois portées obéissent aux mêmes conditions** : un bloc de podium retient les archers dont le rang **vient des duels**, n'est **plus en lice** et est **exact** (pas d'*ex æquo* — on ne remet pas une médaille à quatre 5ᵉ-8ᵉ), chacun sur **son** rang : scratch, catégorie ou club. Les trois conditions sont celles d'E06US004 ; seul le rang lu change.
- **CA — un archer sans club n'entre dans aucun podium de club** : `club_id is None` est l'anomalie « club inconnu » qu'ADR-0014 impose de **signaler**, pas un club de rattachement. Ces archers restent au classement complet ; aucun bloc « sans club » n'est fabriqué.
- **CA — le réglage vaut partout où le palmarès se rend** : écran admin, appli publique, écran de salle et **PDF** — c'est le même `ServicePalmares` pour les quatre (E06US004), un document qui recalculerait de son côté finirait par contredire l'écran.
- **CA — se règle en admin, se lit en public** : poser le réglage est une action admin (`exiger_admin`) ; le **lire** est ouvert, comme le palmarès lui-même — c'est une donnée d'affichage, pas un secret. Même partage que le cloisonnement (E03US007).
- **Notes** : `application/palmares.py` ne connaît aujourd'hui que **deux** portées — *scratch* et *catégorie* (`pour_tournoi(tournoi_id, categorie_id)`), constat fait au cadrage du 30/08/2026. *Club* et *équipe* n'ont aucun porteur. ⚠️ **Les équipes relèvent d'EPIC-13** ([ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md)) : ne pas les anticiper ici — une portée « équipe » sans classe `Equipe` livrerait un réglage qui ne peut rien rendre. ⚠️ La portée d'un podium est un **réglage**, donc de la configuration et non du code (règle 2) — même parti que le mode de composition d'une poule ([ADR-0094](../docs/adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md)). ✅ **La question ouverte de cette fiche est tranchée** (31/08/2026) : un podium *par club* classe les **archers d'un club entre eux** ; les **clubs entre eux** existent aussi, mais en `E16US017`. ⚠️ **Ne pas écrire une seconde arithmétique d'ex æquo** : `_numeroter(paquets, retenir=…)` renumérote déjà un sous-ensemble depuis 1 (c'est ce qui produit le rang de catégorie) — un rang par club est le **même** appel avec un autre filtre. En écrire un autre ajouterait un 5ᵉ site à `DETTE-029`.
- **ADR** : [ADR-0103](../docs/adr/0103-la-portee-d-un-podium-est-un-reglage-du-tournoi.md) — écrit **en revue** : le corps du commit avait conclu « pas d'ADR » au motif d'un « patron déjà posé », or ce patron (le cloisonnement, 0041) était **lui-même venu avec ADR-0071**. Révise [ADR-0067](../docs/adr/0067-palmares-agregation-des-rangs-de-phases.md) § Décision 5.
- **Dépend de** : E06US004, E16US007 · **Jalon** : J3 · **Origine** : questionnaire A16, 04/08/2026 — sortie d'`E16US007` le 30/08/2026

---

### E16US017 — Le classement des clubs entre eux ✅
*En tant qu'*organisateur, *je veux* un podium **des clubs**, *afin de* remettre le trophée du club le plus performant de la journée.
- **Contexte** : tranche B du découpage d'`E16US014` (31/08/2026). `E16US014` livre les podiums d'**archers**, y compris « club par club » ; celui-ci classe les **clubs eux-mêmes**, ce qu'aucun classement du produit ne sait faire.
- **CA — le barème est le décompte de médailles** : les clubs se comparent à l'**or**, puis à l'**argent**, puis au **bronze** — l'ordre olympique, tranché par le commanditaire le 31/08/2026. ⚠️ Ce barème n'utilise **que** ce que le palmarès porte déjà (les rangs décernés) : aucune donnée neuve à faire remonter, et un résultat que personne ne conteste au pied du podium. Les deux autres pistes ont été écartées : la **somme des scores de qualification** ignore les duels — c'est-à-dire le tournoi ; un **barème de points par rang** fait du barème lui-même une configuration à saisir et à défendre (une US et un ADR à soi seul).
- **CA — la portée du décompte suit le réglage des podiums** : les médailles comptées sont celles que le tournoi **décerne** (`E16US014`) — si l'organisateur ne récompense que par catégorie, ce sont ces médailles-là qui alimentent le classement des clubs. Un archer 3ᵉ scratch mais 1ᵉʳ de sa catégorie rapporte donc un **or** à son club sous ce réglage, pas un bronze.
- **CA — l'or décerné deux fois compte deux fois** *(arbitrage du 04/09/2026, au cadrage — le point que la version précédente de cette fiche laissait « à vérifier »)* : un tournoi qui cumule *scratch* **et** *catégorie* remet deux ors au même archer, et son club en encaisse deux. Le décompte affiché **coïncide alors avec le nombre de médailles physiquement remises**, ce qui est la seule propriété vérifiable au pied du podium. ⚠️ Effet assumé, énoncé avant l'arbitrage : un club à un seul archer très fort double son score. ⚠️ **Limite trouvée en revue (axe D)** : la propriété « le décompte colle aux médailles remises » **tombe si le tournoi n'a qu'une catégorie** — les deux podiums sont alors identiques, un seul jeu de médailles est remis et deux sont comptés. Documentée plutôt que corrigée (dédoublonner casserait le cas nominal), rendue lisible par la ligne « Compté sur : … » et épinglée par un test. L'alternative écartée (dédoublonner par archer) récompensait la profondeur d'effectif au prix d'un tableau qui ne collait plus au réel.
- **CA — la portée *club* est exclue du décompte** *(arbitrage du 04/09/2026)* : le podium « club par club » d'`E16US014` décerne un or **à l'intérieur de chaque club**, donc à tous — et jusqu'à quatre médailles à ceux qui ont assez d'archers pour remplir leur propre podium. Le compter ferait mesurer l'**effectif** au classement, exactement ce que les Notes ci-dessous excluent. Seules les portées **inter-clubs** (*toutes catégories*, *catégorie*) alimentent le décompte. ⚠️ **Corollaire** : un tournoi réglé sur la seule portée *club* n'a **aucun classement des clubs** — pas un classement où tout le monde est premier. L'écran le **dit** (« les podiums réglés récompensent à l'intérieur de chaque club »), il ne laisse pas un blanc que l'organisateur prendrait pour une panne.
- **CA — tant qu'aucun club n'a de médaille, il n'y a pas de classement** *(arbitrage de revue, 04/09/2026 — axe C1)* : un décompte où tous les clubs sont à zéro les met **tous *ex æquo* 1ᵉʳˢ**, c'est-à-dire exactement « un classement où tout le monde est premier » que le CA ci-dessus interdit — atteint par la porte du **décompte** au lieu de celle de la **portée**. ⚠️ Le cas dure **toute la matinée** d'un tournoi et se projetait sur l'écran de salle. Le serveur ne rend donc aucune ligne, et les trois surfaces disent « Aucun club n'a encore de médaille. » ⚠️ La même phrase couvre trois causes (aucun club inscrit, aucune médaille encore décernée, médailles toutes revenues à des archers **sans club**) : elle est vraie des trois.
- **CA — un tournoi qui ne récompense rien n'affiche pas la section** *(arbitrage de revue, 04/09/2026 — axe C2)* : réglage **vide** (aucune portée, licite — ADR-0103 §1), il n'y a pas de question à se voir répondre. ⚠️ À **distinguer** de « seuls des podiums internes aux clubs sont réglés », qui affiche la section et **nomme** la cause : le serveur porte les deux faits séparément (`portees_reglees` / `portees_comptees`), l'écran ne les déduit pas de la liste des podiums.
- **CA — trois métaux, pas un de plus** : or, argent, bronze. ⚠️ La profondeur d'un podium vaut **4 par défaut** (ADR-0103 §4) : la 4ᵉ place est donc le cas **nominal**, et elle ne rapporte rien.
- **CA — le classement suit les quatre surfaces du palmarès** *(cadrage du 04/09/2026)* : écran d'organisateur, appli publique, écran de salle et PDF — le trophée du club se remet en même temps que les médailles, il se lit donc au même endroit. ⚠️ Le **papier saute** la section quand elle n'a pas de base : une table vide imprimée se lirait « aucun club » sans que rien ne puisse la commenter.
- **CA — les clubs à égalité parfaite sont *ex æquo*** : même décompte or/argent/bronze = même rang, sans départage inventé.
- **Notes** : ⚠️ **Aucun effectif minimum** n'est exigé d'un club pour être classé (arbitrage du 31/08/2026) : un seuil masquerait des clubs en silence, et le décompte de médailles ne favorise déjà pas les petits effectifs. ⚠️ Un club **sans aucune médaille** finit à zéro, à égalité avec un club dont personne n'est monté sur un podium — c'est la limite assumée du barème retenu, elle a été énoncée avant l'arbitrage.
- **Notes (livraison)** : ⚠️ Le décompte se lit sur les **blocs de podium déjà décernés**, jamais sur une seconde traversée des rangs — c'est ce qui interdit structurellement aux deux barèmes de diverger. ⚠️ La garde d'`E16US014` sur `_libelles_club` **tombe** : le référentiel des clubs n'était lu que si la portée *club* était réglée, or il faut désormais **nommer** les clubs dès qu'une portée inter-club l'est. ⚠️ 5ᵉ site de `DETTE-029` (arithmétique d'*ex æquo*) — ligne du registre élargie, pas de contournement local.
- **Dépend de** : E16US014 · **Jalon** : J3 · **Origine** : découpage d'`E16US014`, 31/08/2026 · **ADR** : [ADR-0104](../docs/adr/0104-le-classement-des-clubs-se-compte-en-medailles-inter-clubs.md)

---

### E16US015 — Un QR par scoreur ✅
*En tant qu'*organisateur, *je veux* un QR **par scoreur**, en plus de son code, *afin de* rattacher une tablette sans faire recopier un code à la main.
- **Contexte** : sortie d'`E16US007` au découpage du 30/08/2026. A08 : un **QR par scoreur**, en plus du code.
- **CA — QR par scoreur** : jumeau de celui des cibles, affichable à l'écran.
- **CA — l'URL porte le code personnel en clair** *(arbitrage du 04/09/2026, question de sécurité ci-dessous tranchée)*. Le QR n'expose **rien de plus** que ce que l'écran montre déjà : le code est en clair en base (`domain/scoreur.py`), en clair dans la réponse admin `GET /scoreurs`, en clair sur le PDF des cartes, et affiché en clair dans la liste. Le risque n'est donc **pas cryptographique** mais **contextuel** — un QR se scanne d'un mètre et sans être vu, là où lire un code demande de s'approcher. Écartée : l'option « jeton à usage unique », qui n'existe nulle part (ni session scoreur ni rattachement de poste n'expirent) et ferait de cette petite US un chantier à ADR.
- **CA — révélé UN scoreur à la fois, sur geste explicite** *(même arbitrage)*. L'écran admin ne charge aucun QR au montage : un bouton « Afficher le QR » par ligne, un seul ouvert à la fois. C'est **là** que se traite le risque contextuel — sans quoi la liste entière des codes deviendrait scannable d'un seul cliché. L'exclusivité est portée par l'état du **parent**, donc structurelle, et le QR n'est pas seulement caché : **il n'est pas demandé**, parce que le composant qui le charge n'est **monté** que sur geste. ⚠️ **Corrigé en revue le 04/09/2026** : la 1ʳᵉ rédaction attribuait cette garde à un `enabled` (React Query) qu'aucun appelant ne mettait jamais à `false` — un CA qui nomme le mauvais mécanisme est pire qu'un CA muet, l'US suivante en dérive ses tests. ⚠️ **Rien n'est indexé sur l'`id`** — ni l'état d'ouverture, ni la clé de cache du QR, ni la `key` de ligne : SQLite réattribue les `id`, si bien qu'un scoreur supprimé puis remplacé rouvrait le QR de son successeur **sans clic**, se voyait servir le SVG révoqué depuis le cache, et héritait de l'état armé de « Confirmer la suppression » (bloquant, puis deux majeurs de revue). ⚠️ Le code d'arrivée est **consommé** : lu par abonnement et retiré de l'adresse, jamais mémorisé — le mémoriser rouvrait la session à la déconnexion.
- **Notes** : ✅ **Périmètre confirmé au cadrage du 04/09/2026 — le QR seul.** La **rotation d'un code** (« nouveau code » si une carte se perd ou si un QR a été photographié) a été posée au commanditaire et **écartée du périmètre** : c'est un geste de cycle de vie (révoquer les sessions ouvertes, réimprimer la carte, décider ce que voit un scoreur déconnecté en pleine saisie), pas un corollaire du QR. À reprendre en fiche propre si le besoin se confirme.
- ⚠️ **La forme de l'URL n'est PAS celle du jumeau, et c'est délibéré** *(décision d'implémentation du 04/09/2026)*. Le QR de cible vise la **racine** (`…/?poste=<code>`) parce qu'il précède `E14US003` : à l'époque l'adresse n'était pas une source d'entrée. Reproduire cette forme obligeait à ajouter une **cinquième règle de précédence** dans `resoudreRole` — le module que son propre en-tête nomme « le cœur risqué de l'aiguillage d'entrée » ([ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md)). Le QR d'un scoreur encode donc `…/scoreur#code=<code>` : le **chemin nomme le monde**, le routeur d'adresses ([ADR-0059](../docs/adr/0059-routage-par-role-dans-l-url-routeur-maison.md)) aiguille seul, **zéro ligne** touchée dans l'entrée. Bénéfice de repli : si le code est refusé, on atterrit sur l'écran de connexion scoreur — le bon endroit — et non sur l'écran de choix des portes. ⚠️ **Le code vit dans le FRAGMENT, pas dans la query** (corrigé en revue) : un fragment n'est jamais envoyé au serveur, là où un `?code=` serait écrit dans le journal d'accès d'uvicorn à chaque scan puis dans le `Referer` de chaque sous-ressource. Et l'effacement de l'adresse est **au shell** : une tablette déjà rattachée ne monte pas l'espace scoreur, le code y serait resté affiché toute la journée. Tout ceci est désormais porté par [ADR-0105](../docs/adr/0105-le-qr-d-un-scoreur-porte-son-code-revele-un-a-la-fois.md), **qui amende ADR-0025** — sa Décision 2 disait le code « distribué sur papier et retapé », ce que ce QR rendait faux en silence.
- **Notes (état des lieux du 30/08/2026)** : le **jumeau existe** et sert de patron, constat fait au cadrage du 30/08/2026 : `GET /tournois/{id}/postes/{cible_index}/qr` rend le QR d'**une** cible en **SVG** affichable à l'écran (`GenerateurDocumentsSalle.qr_rattachement`, `frontend/src/features/postes/QrCible.tsx`). Côté scoreur, seul le **PDF groupé** existe (`/scoreurs/cartes-codes`, une page par scoreur) — il n'y a rien par scoreur. ⚠️ **Question à trancher** : que contient l'URL du QR d'un scoreur ? Celui d'une cible porte une URL de **rattachement de poste** ; un code scoreur est un secret **personnel** (E10US002), et l'afficher en QR à l'écran de l'admin le rend photographiable par n'importe qui passant derrière — c'est une question de sécurité, pas d'IHM.
- **Dépend de** : E09US008, E10US002 · **Jalon** : J3 · **Origine** : questionnaire A08, 04/08/2026 — sortie d'`E16US007` le 30/08/2026

---

### E16US016 — Exports : les formats et les documents qui restent dus
*En tant qu'*organisateur, *je veux* sortir **le classement** et **le journal d'audit** au format de mon choix, *afin de* les reprendre dans un tableur.
- **Contexte** : reliquat écrit d'`E16US007` (30/08/2026). Cette fiche existe pour que trois manques constatés au cadrage ne se reperdent pas ; elle n'est **pas** un plan de travail, elle est à découper quand elle sera prise.
- **CA — le palmarès sort aussi en tableur** : le classement final s'exporte dans les formats du catalogue, pas seulement en PDF. ⚠️ **Arbitrage requis d'abord** : la route est `GET /tournois/{id}/palmares.pdf`, **publique et non authentifiée**, et son chemin **nomme le format**. Lui ajouter un format demande de généraliser le chemin, donc de renommer une route publique. À trancher avec le commanditaire, avec `DETTE-031` en vis-à-vis (chaque lecture reconstruit toutes les phases à tableau — un format de plus multiplie ce coût).
- **CA — le journal d'audit se CONSULTE, puis s'exporte** : ⚠️ **corrigé en revue le 30/08/2026** — la première rédaction disait la consultation « déjà acquise ». C'est faux côté produit : la route `GET /tournois/{id}/audit` existe et n'a aucune restriction de statut, mais **aucun écran ne l'appelle**. Il faut donc livrer **l'écran** (le CA d'origine, A18, dit « consultable en cours de tournoi ») **puis** l'export.
- **CA — le format Excel** : `xlsx` était demandé par A18 (*« CSV, EXCEL, PDF… »*) et a été écarté d'`E16US007` faute de dépendance. ⚠️ **Ajout de dépendance = règle 11** : `openpyxl` ou `xlsxwriter` à justifier, auditer (`pip-audit`), documenter — arbitrage du commanditaire, jamais de l'assistant. Une fois tranché, le coût de code est **une entrée de registre et un adapter** : c'est ce que `E16US007` a livré pour que cette US soit petite.
- **Dépend de** : E16US007, E06US004, E10US005 · **Jalon** : J3 · **Origine** : reliquat d'`E16US007`, 30/08/2026

---

### E16US008 — Feu vert : agir depuis la ligne du duel qui bloque ✅
*En tant qu'*organisateur, *je veux* que les **actions** soient sur la ligne du duel qui a un manquement, *afin de* débloquer sans quitter l'écran.
- **Contexte** : A15, évolution : *« les manquements appartiennent à la ligne du duel qui a des manquements, ainsi que ses actions »*. Question 5, qui déclare un forfait : *« admin »*. Question 3, qui appuie sur le bouton : *« un admin, mais suivant la configuration on doit choisir ce qui attend un déclenchement manuel (les phases ou le tour) : selon la configuration, soit ça se déclenche automatiquement quand les conditions sont remplies, soit c'est un déclenchement manuel. »*
- **CA — actions sur la ligne** ✅ : chaque duel bloqué porte, à côté de son manquement déjà nommé, l'action qui le lève.
  ⚠️ **Arbitrage tranché au cadrage, le 28/08/2026 — l'action dépend du manquement, et il y en a
  trois**, ceux que `ServicePilotageTour._blocage` sait nommer. *« en attente du duel n°3 »* → le
  duel amont se **déplie sur place** (ses occupants, sa cible) et porte le bouton de forfait ;
  *« cible non attribuée »* → renvoi au plan de duels ; *« adversaire non déterminé »* → **aucune
  action**, cela se répare à la composition de la phase, pas au feu vert.
  ⚠️ **« Ouvrir le duel amont » a été écarté, et c'est un fait de code, pas un choix de confort** :
  `SaisieDuels` n'est monté que dans `EspaceScoreur`, derrière un code scoreur. Un lien y aurait
  posé l'organisateur devant un écran de connexion qu'il ne peut pas franchir. Ouvrir la validation
  de duel à l'admin est un autre sujet — la règle « validation = scoreur seul » (E10US003) —, à
  instruire ailleurs.
- **CA — forfait par l'admin** ✅ : déclarer un forfait de duel devient possible depuis l'administration.
  ⚠️ **Décision d'autorisation tranchée le 28/08/2026 : la route existante est ÉLARGIE** (admin
  **ou** scoreur), pas doublée d'une route admin. C'est la ligne du dépôt (`autoriser_saisie`,
  E10US007 : une route, deux identités) ; deux routes vers la même écriture demanderaient de tenir
  idempotence, audit et règles métier en double. `declare_par` vaut alors `"Administrateur"`.
  **Élargi aussi à l'annulation** (`D-15`) : qui peut déclarer doit pouvoir défaire, sinon une
  faute de frappe reste irréparable sans aller chercher un scoreur. ~~**Borné aux duels** : la
  qualification reste au scoreur seul, aucun écran admin ne la demande.~~ ✅ **Caduc depuis le
  30/08/2026** : le commanditaire a tranché d'élargir aussi la **qualification** — même patron
  (élargie, pas doublée), geste posé sur la fiche d'archer, livré avec `E16US007`.
  ⚠️ **Reversé de la revue du 28/08/2026 — l'annulation est livrée SANS SURFACE** (`DETTE-090`) :
  la route est ouverte à l'admin et testée, mais **aucun écran ne l'appelle** (`useAnnulerForfaitDuel`
  n'a aucun appelant). Le motif de `D-15` n'est donc pas tenu côté produit. Poser le bouton demandait
  une surface neuve — le duel amont **quitte la liste** dès qu'il est tranché par le walkover, une
  action sur sa ligne serait hors d'atteinte l'instant d'après —, soit un choix de périmètre, pas une
  correction de revue. Le dialogue de confirmation **avertit** au lieu de promettre.
  ⚠️ **Le bornage aux duels tenait par une seule de ses deux portes** (revue, axe A) : `phase_id`
  vient du client, et rien ne vérifiait le **type** de la phase — un `phase_id` de qualification posté
  sur la route des duels écrivait un forfait relu par le classement de qualification, contournant
  `exiger_scoreur`. La route **refuse désormais explicitement** une phase de qualification. Un test
  fermé sur une porte seule est une assurance fausse, pas une demi-garde.
- **CA — déclenchement configurable** ➡️ **sorti du périmètre** le 28/08/2026, devient **`E16US013`** : par phase ou par tour, le lancement est **automatique** (conditions remplies) ou **manuel**. Les notes ci-dessous l'annonçaient déjà (« vrai changement de moteur : à cadrer séparément »), le cadrage l'a acté.
- **Notes** : les manquements sont **déjà** nommés par ligne (`afficheDuel`) — c'est le volet « actions » qui manque. Le déclenchement automatique est un vrai changement de moteur : à cadrer séparément. **Redécoupable**.
  ⚠️ **Un angle mort découvert au cadrage, absent de la fiche** : au **tour ≥ 2**, aucune cible
  n'est attribuée (`place = match.tour == 1`, garde délibérée de `DETTE-019` — la pose persistée est
  celle du tour 1, l'annoncer enverrait les finalistes sur la mauvaise butte). *« cible non
  attribuée »* n'y est donc **levable par aucun geste**, et le renvoi au plan de duels serait une
  fausse porte. La ligne **dit la limite** au lieu de l'offrir ; `DETTE-019` gagne un site qui la
  constate (**4ᵉ** au total, la table en sous-comptait un dans le front). Le jour où le placement 1→N
  sera posé, c'est **ici aussi** qu'il faudra revenir.
  ⚠️ **La même arithmétique vaut pour l'autre branche, et le cadrage ne l'y avait PAS rejouée**
  (revue du 28/08/2026, axe adversarial). Un duel qui attend un duel amont est **forcément** au tour
  ≥ 2 (`VainqueurDe`/`PerdantDe` ne sont engendrés qu'à `tour + 1`) : le forfait déclaré depuis le feu
  vert fait donc avancer le tableau, mais **ne rend jamais la ligne prête**.
  ⚠️⚠️ **Ce point a reçu QUATRE formulations fausses en TROIS passes de correctifs, et l'oracle n'est plus ici.** La 1ʳᵉ
  passe a écrit « un duel attend une source », la 2ᵉ « il en attend deux », la 3ᵉ « deux, sauf
  byes », puis « deux sur une puissance de 2 » : les quatre sont fausses — la 3ᵉ passe en a produit
  deux, l'une en prose, l'autre en généralisant un test mesuré sur un tableau vierge. La règle réelle est **« une ou deux, à tout
  effectif »** — un `VainqueurDe`/`PerdantDe` ne compte comme attente que si son camp est **vide**,
  et un camp se remplit de **deux** façons : un bye à la construction, **ou un duel amont déjà
  tranché**. C'est cette seconde cause qui a été manquée trois fois. Une ligne n'attend jamais plus
  de deux duels — un match n'a que deux camps — et souvent un seul, **y compris sur une puissance de
  2** dès que le tour avance.
  Conséquences : (a) le forfait tranche **une** attente — la ligne passe à « en attente du duel n°X »
  s'il en restait deux, à « cible non attribuée » s'il n'en restait qu'une ; (b) le compteur
  « Lancer » **diminue seulement si le duel tranché y figurait**, donc jamais quand l'amont est au
  tour ≥ 2 (aucune cible n'y est posée, il n'était pas compté).
  ⚠️ **Ne pas redériver ces phrases de tête : elles sont la traduction d'un test.**
  `test_une_ligne_bloquee_attend_une_ou_deux_sources_selon_ce_qui_reste_a_trancher` et
  `test_un_duel_de_tour_2_n_est_jamais_pret_a_lancer` (`backend/tests/test_service_pilotage_tour.py`)
  portent l'oracle ; la CI les relit. Deux leçons, et la seconde a coûté une passe de plus :
  **(1)** tant qu'un oracle ne vit que dans de la prose, chaque passe de revue en produit une version
  fausse ; **(2)** un oracle en test ne vaut que si son **fixture est l'état que l'utilisateur
  observe** — le premier test a été écrit sur un tableau **vierge**, alors que l'organisateur lit le
  feu vert **pendant** le tour, d'où une 4ᵉ version fausse. Il balaie désormais aussi un tableau en
  cours.
  ⚠️ **Le forfait n'est offert que si le duel amont a ses DEUX camps** (revue, bloquant).
  `ServiceSaisieDuels._appliquer_forfaits` **saute** un match dont un camp est vide : un forfait posé
  là s'écrivait en base, sans rien débloquer et sans le moindre retour d'écran — l'organisateur
  recliquait jusqu'au `ForfaitDejaDeclare`. La fiche fonctionnelle l'exigeait déjà (« aucun bouton de
  forfait ne doit apparaître ») ; c'est le **test** qui avait consacré l'inverse, dérivé du code au
  lieu du CA.
- **Dépend de** : E12US002, E04US015, E10US001 · **Jalon** : J3 · **Origine** : questionnaire A15, 04/08/2026

---

### E16US009 — Écran de salle : régler ce qui défile, et défiler ce qui ne tient pas ✅
*En tant qu'*organisateur, *je veux* **régler la durée d'une page** projetée et voir les archers **défiler sous le podium**, *afin d'*adapter l'écran à ma salle sans toucher au code.
- **Contexte** : P06, question 2 : *« on peut dire que 20 s (réglable) par écran de liste de noms est correct »* — la pagination est livrée, la **durée est figée à 20 s dans le code**. P07 : *« ok pour les 3 premiers toujours visible, mais défilement de tous les autres archers dessous »* ; le classement projeté montre aujourd'hui une tête figée mais ne fait pas défiler la suite. P07, question 2 : *« je n'ai pas vu le logo sur la maquette »* — l'identité du tournoi n'est pas encore posée sur l'écran de salle.
- **CA — durée réglable** ✅ : la cadence d'une page de noms se règle par écran, à côté du déroulé de vues déjà configurable.
- **CA — défilement sous la tête figée** ✅ : les archers hors des trois premiers défilent d'eux-mêmes.
  ⚠️ **Arbitrage tranché en cours d'US, le 26/08/2026 — « défiler » se réalise par une PAGINATION**
  ([ADR-0098](../docs/adr/0098-un-ecran-projete-pagine-au-lieu-de-defiler.md)). Un cadre à ascenseur
  sur un vidéoprojecteur est un cadre que **personne ne peut actionner** (« aucune interaction »,
  CA E07US004) — c'est pour cela que `E16US005` avait laissé la tête figée **à zéro** sur cette
  surface. La forme retenue est celle que le questionnaire **P06 accepte déjà** pour une liste de
  noms projetée, compteur de pages compris. **Le lien est mécanique** : la tête figée ne passe à 3
  que si un réglage de pages est fourni, sinon elle retombe à zéro — on ne peut donc pas livrer
  « 3 lignes et rien d'autre ».
- **CA — nombre de noms par page** ✅ : `NOMS_PAR_PAGE = 40` est un choix à confirmer **sur le vidéoprojecteur réel** ; le rendre réglable ou le mesurer.
  ⚠️ **L'alternative est tranchée : réglable, pas mesuré.** Mesurer suppose un vidéoprojecteur, une
  salle et une distance — c'est un geste d'**exploitation**, pas de code. L'US rend donc la valeur
  corrigeable sans recompiler et **le dit à l'organisateur sous les deux champs** ; l'incertitude,
  elle, **reste ouverte** (`docs/dette.md`, section DETTE-039 conservée).
- **CA — logo** ✅ : l'identité (événement + club, cf. E16US006) apparaît sur l'écran de salle.
  ⚠️ **Déjà livré la veille par `E16US006`** (`EcranSalle.tsx`, deux logos dans le bandeau, deux
  tests) — constat fait au cadrage du 26/08/2026, dans le code. Ce CA n'a rien coûté à cette US.
- **Notes** : la durée réglable demande un champ sur la configuration d'écran (API `ecrans`). Le défilement est front. Relire [ADR-0064](../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) : tout y est piloté par **état lu**, un réglage local contredirait le principe.
  ✅ **ADR-0064 est respecté** : le réglage est persisté sur le **poste** (migration `0051`) et servi
  **avec l'affichage** que l'écran répète — jamais un réglage local, jamais un ordre poussé. Il
  accompagne aussi les prises de contrôle : une prise change *ce qu'on montre*, pas *comment une
  liste se lit de loin*.
  ⚠️ **Un piège découvert en implémentant, absent de la fiche** : le cumul du temps d'affichage
  d'une vue vivait dans **une seule** variable de module, sous le postulat « une seule surface
  projetée par onglet ». Ce postulat tombe dès qu'une **deuxième** vue pagine — les pages du
  classement avançaient pendant que l'écran montrait les affectations. Le compteur est désormais
  **indexé par vue**, avec un test qui le garde.
  ⚠️ **Le réglage appartient à l'ÉCRAN, pas à la vue** : les deux valeurs dépendent de la diagonale
  du projecteur, de la distance de lecture et de la longueur des noms du club — trois propriétés du
  **lieu**. Les porter sur `VueProgrammee` aurait obligé à les répéter à chaque étape du déroulé.
- **Dépend de** : E07US004, E07US008, E01US016 · **Jalon** : J3 · **Origine** : questionnaires P06, P07, 04/08/2026

---

### E16US010 — Chercher partout, et voir d'avance ce qui bloque un lancement ✅
*En tant qu'*organisateur, *je veux* une recherche qui **change de nature selon le moment** et une alerte de complétude **dès la liste des tournois**, *afin de* ne pas découvrir un blocage en ouvrant l'écran.
- **Contexte** : A02, question 2 : *« dans le cycle préparation et après, on doit pouvoir faire une recherche sur tout item-entité, par une liste déroulante et un champ de saisie ; une complétion de recherche montre une liste des items possibles avec la possibilité de cliquer dessus et d'ouvrir la fiche en modification. Dans le cycle déroulé du tournoi, on peut faire une recherche d'un archer du tournoi et ouvrir sa fiche en consultation avec ses informations du tournoi, puis possibilité d'agir dessus si besoin. »* A02, question 1 : *« sur cette liste laisse une pastille d'alerte si tout n'est pas complet ; alerte forte si impossible de lancer en l'état. »* A09 : *« c'est une barre de recherche qui doit rester accessible sur tout le déroulé du pilotage et se concentrer sur le tournoi en cours sélectionné, donc elle ne doit pas polluer le reste de l'écran »* ; doublons : *« on avertit seulement… une simple icône cliquable sur la ligne de l'archer peut suffire »*.
- **CA — recherche transverse hors pilotage** : entité choisie dans une déroulante + champ de saisie, complétion, ouverture de la fiche **en modification**. ✅ **Périmètre tranché au cadrage du 29/08/2026 : trois entités — tournois, archers, clubs**, les seules qui aient aujourd'hui une fiche modifiable, donc les seules dont un résultat puisse tenir la promesse « ouvrir la fiche ». Les briques de l'atelier (catégories, blasons, formats) sont **hors périmètre** : six formes de résultat et six destinations d'ouverture auraient demandé de couper l'US en deux.
- **CA — recherche d'archer en pilotage** : scopée au tournoi, fiche **en consultation** puis action. ✅ **Les actions sont tranchées au cadrage** : *corriger sa fiche* et *modifier son placement*. ~~⚠️ **Le forfait est demandé mais NON livré comme geste** : la route de forfait **en qualification** est réservée au scoreur (`exiger_scoreur`)… **Élargir cette route à l'organisateur est un choix de rôles, laissé au commanditaire.**~~ ✅ **Tranché par le commanditaire le 30/08/2026 et livré avec `E16US007`** : la route de qualification est **élargie** à l'admin (`autoriser_forfait`), pas doublée — même patron qu'`E16US008`. Le geste vit sur la **fiche d'archer**, la place que ce CA désignait déjà, derrière la confirmation commune (`BoutonConfirme`) qui nomme l'archer et avertit **avant** le clic. ⚠️ **L'annulation n'est PAS livrée depuis cette fiche** : elle reste au panneau « Forfaits — qualification » de l'espace scoreur, seul écran qui affiche le classement, donc seul à savoir *qui* est déjà forfait. `D-15` n'est donc **pas tenu côté produit** pour l'organisateur — même défaut que `DETTE-090` sur les duels, dont la ligne est élargie.
- **CA — pastille de complétude en liste** : deux niveaux — incomplet (avertissement) et **impossible à lancer** (alerte forte). ✅ **Dérivée du jalon « prêt à démarrer »** (ADR-0096) et non recalculée : le CA d'`E16US012` interdit une seconde source de complétude. Une **route d'agrégat** rend le niveau de tous les tournois en un appel.
- **CA — doublons discrets** : une icône cliquable sur la ligne de l'archer, qui montre le problème et propose l'action, au lieu d'un écran dédié qui pollue. ✅ **Arbitrage du commanditaire au cadrage : l'icône REMPLACE l'écran dédié**, elle ne s'y ajoute pas. La vue d'ensemble perdue est compensée par une phrase chiffrée en tête de la liste des inscrits (« 3 rapprochements de fiches »). Rien n'était à détecter — `detecter_doublons`, la route et la fusion existaient depuis `E02US005` : c'était une **affordance à déplacer**, le CA le moins cher des quatre.
- **Notes** : la recherche d'archer existe (E12US006), scopée au tournoi — c'est la **variante toutes entités** qui manque. ⚠️ **Deux affirmations de cette fiche étaient FAUSSES, vérifiées au cadrage** : (a) la variante toutes entités n'était **pas** « annoncée *lot suivant* dans `CoquilleAdmin` » — la formule n'existe nulle part dans le code, seule cette fiche la contenait ; (b) `Archer` **n'existe pas hors tournoi** (`tournoi_id` obligatoire, aucun listing global au port), donc chercher « hors pilotage » veut dire chercher **à travers toutes les éditions** — d'où `ArcherRepository.tous()`. ✅ La pastille demandait bien un **agrégat serveur**, comme annoncé. ⚠️ **Obstacle absent de la fiche, découvert en implémentant** : rien ne permettait d'ouvrir une fiche depuis l'extérieur — l'état d'édition était un `useState` **local à la ligne** et l'adresse d'admin n'avait que trois segments. D'où [ADR-0100](../docs/adr/0100-une-destination-d-admin-porte-l-element-qu-elle-ouvre.md), qui fait entrer l'élément ouvert dans l'adresse. Bénéfice non demandé : une fiche devient **adressable** (lien copiable, F5, bouton *Précédent*).
- **⚠️ Vocabulaire (E16US001, [ADR-0073](../docs/adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md))** : ~~cette US rouvre des maquettes qui disent encore « position »~~ — ✅ **vérifié le 29/08/2026, et l'avertissement était FAUX pour la 4ᵉ fois d'affilée** (après `E16US004` et `E16US005`) : le composant de recherche affichait déjà « couloir », et ni la fiche archer ni la liste des tournois ne disent « position ». Le seul reliquat réel était dans `docs/fonctionnel/E12US006.md`, corrigé ici. **L'avertissement est retiré de cette fiche ; il subsiste sur `E16US011`, où il n'a pas été vérifié.** *(Vérifié le 10/09/2026 au découpage d'`E16US011` : faux une 5ᵉ fois. L'avertissement est éteint partout.)*
- **Dépend de** : E12US005, E12US006, E02US005, **E16US012** *(le jalon dont la pastille dérive ; ajouté le 29/08/2026 — la fiche ne le mentionnait pas, l'US n'existait pas encore à sa rédaction)* · **Jalon** : J3 · **Origine** : questionnaires A02, A09, 04/08/2026

---

### E16US011 — Ce que trois questionnaires « validés » demandaient quand même ✅ *(carte de découpage, close le 10/09/2026)*
*En tant qu'*organisateur, *je veux* que les règles énoncées dans les questionnaires validés soient tenues, *afin de* ne pas croire acquis ce qui n'a jamais été codé.
- **Contexte** : ⚠️ **cette US existe parce que le tri initial était faux.** Le lot du 05/08/2026 avait rangé S06, S08 et S09 parmi les « validés tels quels, aucune évolution demandée » — au motif que leur verdict était ✅. Or leur verdict porte sur **l'écran**, pas sur les réponses aux questions ciblées, et celles-ci énoncent des **règles** qui ne sont nulle part dans le code. Défaut relevé par la revue adversariale du 05/08/2026, et c'est le plus coûteux du lot : un retour classé ✅ n'est **jamais relu**.
- **⛔ NE PLUS PRENDRE — cette fiche est une CARTE, pas un plan de travail.** Découpée le 10/09/2026
  comme ses propres Notes le prescrivaient. Les sept règles ont été **vérifiées une par une dans le
  code du jour avant tout arbitrage**, et le rendement de ce contrôle justifie à lui seul la séance :
  **sept des dix lignes du tableau ci-dessous corrigent la rédaction d'origine**, et deux CA sont
  tombés sans coûter une ligne. ⚠️ **La leçon de pilotage est la même qu'aux quatre US précédentes** :
  une fiche de rattrapage décrit le code du jour où elle a été écrite (ici le 05/08/2026), pas celui
  du jour où on la prend. La relire contre le code **avant** de poser les questions au commanditaire
  a évité deux arbitrages inutiles.
  ⚠️ **Ce compte a lui-même dû être corrigé en revue** : la 1ʳᵉ rédaction annonçait « trois des sept
  constats », chiffre qu'aucune lecture du tableau ne donnait — un décompte mis en avant comme
  conclusion de l'US, et faux. Il est désormais aligné sur le grain qu'il annonce (les **lignes** du
  tableau), le seul qui soit vérifiable en le lisant.
  ⚠️ **Et la vérification elle-même avait un angle mort, trouvé par la revue adversariale** : tout a
  été relu contre **le code**, rien contre les **questionnaires bruts** — les extraits recopiés dans
  cette fiche il y a cinq semaines ont été pris pour argent comptant, alors que toute la séance
  consistait à ne pas faire confiance à cette fiche. Deux réponses étaient **tronquées** (S08) ou
  **lues dans un seul sens** (P05). Les questionnaires vivent dans
  [`maquettes/questionnaires/tour-1-2026-08-04/`](../maquettes/questionnaires/tour-1-2026-08-04/) :
  les rouvrir coûte une minute, ne pas le faire a coûté deux bloquants.

  | CA d'origine | Ce que disait la fiche | Ce que dit le code au 10/09/2026 | Destination |
  |---|---|---|---|
  | S06 minuteur | absent | ✅ exact — aucun minuteur, sortie par bouton seul | `E16US018` |
  | S06 place finale | absente | ⚠️ **inexact** — le rang est calculé et affiché ; la règle existe *par accident*, par repli sur `None` | `E16US018` |
  | S08 plus de modification | contredit un endpoint vivant | ⚠️ **à moitié** — les **duels** refusent déjà toute réécriture (`DuelVerrouille`) ; la **qualification** a `corriger_volee`, et le **barrage de places** réécrit une manche close | `E16US019` |
  | S08 annuler une validation | aucune route | ⚠️ **inexact** — vrai pour la volée, la série et le duel ; **faux pour le barrage**, que `DELETE …/barrages/{id}` annule même clos | `E16US019` |
  | S09 hiérarchie des rôles | non implémentée | ✅ exact, **et pire** — aucun mécanisme de conflit : *last-write-wins* silencieux | `E16US020` |
  | A09 licence unique | contredit ADR-0014/0015 | ⚠️ **mal cadré** — les ADR **nomment le point de réouverture** : `E02US007` | `E02US007` |
  | A09 retardataire | à faire | ❌ **déjà tenu** — mais ⚠️ **pas pour la raison d'abord écrite** : ce qui le tient, c'est que **rien ne place tout seul** à l'inscription (ADR-0024) | — écarté, tracé |
  | A02 encart par départ | seul le bandeau livré | ✅ exact — l'accueil ne porte que des **totaux tournoi** | `E16US021` |
  | P05 horaires prévisionnels | à restreindre | ⚠️ **deux lectures possibles**, et la réponse ne tranche pas entre elles — l'une demande une **création**, l'autre un **bornage** de `Depart.horaire` | — **question ouverte**, à reposer |
  | Vocabulaire « position » | reliquat à corriger | ❌ **faux, 5ᵉ fois d'affilée** | — retiré |

- **✅ QUATRE ARBITRAGES RENDUS le 10/09/2026** *(reversés ici, règle 9)* :
  1. **S08 n'était pas une contradiction, mais une procédure en deux temps.** *« Plus de modification
     une fois validé »* et *« une validation peut être annulée, par admin et scoreur »* décrivent un
     seul parcours : on n'édite pas un score validé, on **annule la validation**, on corrige, on
     revalide. La fiche d'origine avait lu deux règles qui s'opposent là où le questionnaire
     décrivait un enchaînement. **Décision : `corriger_volee` disparaît** au profit de ce parcours —
     un seul chemin d'écriture sur un score validé, donc un seul endroit où tenir l'audit, et la
     qualification s'aligne sur les duels. → `E16US019`
     ⚠️ **RECTIFIÉ le 10/09/2026 en revue — la réponse S08 était TRONQUÉE depuis l'origine**, et
     l'arbitrage tel que rendu supprimait la moitié perdue. Texte intégral
     ([`s08-validation-cible.md`](../maquettes/questionnaires/tour-1-2026-08-04/s08-validation-cible.md),
     Q2 — *« la cible peut-elle corriger seule, ou le scoreur corrige-t-il lui-même sur place ? »*) :
     > « **les deux, archer et scoreur** mais plus de modification une fois valider »

     La fiche d'origine n'avait retenu que la subordonnée. Or `corriger_volee` est **le seul chemin
     par lequel un scoreur peut écrire une valeur de score** : `saisir_volee` est gardée par
     `autoriser_saisie`, qui ne rend qu'un `Poste` ou l'admin — **le scoreur n'y a aucune identité**.
     ⚠️ **DÉCISION RECTIFIÉE UNE SECONDE FOIS, le 10/09/2026, en 2ᵉ passe de revue : `corriger_volee`
     est CONSERVÉ.** Une première rectification avait retenu d'élargir `autoriser_saisie` au scoreur ;
     la 2ᵉ passe a chiffré ce que cela coûtait, et le commanditaire a tranché l'inverse. **Quatre
     coûts, tous vérifiés dans le code :**
     1. **La garde inter-tournois disparaîtrait.** `_exiger_meme_tournoi` est appelée par
        `valider_serie` et `corriger_volee`, **jamais** par `saisir_volee`. Or plusieurs tournois
        tournent **en même temps** par conception : un scoreur du tournoi B aurait écrit dans le
        tournoi A.
     2. **La trace d'audit disparaîtrait.** `corriger_volee` écrit une entrée portant l'**avant et
        l'après** avec un auteur **authentifié** ; `saisir_volee` « persiste **sans trace** » et son
        auteur est `saisie_par`, déclaratif. L'US aurait **retiré** de la traçabilité.
     3. **`autoriser_saisie` rend `Poste | None`, et `None` signifie « admin, non borné ».** Les
        appelants s'écrivent `if poste is not None:` — y faire entrer le scoreur comme troisième sens
        de `None` lui donnait une écriture sans contrôle de tournoi ni de cible.
     4. **`D-03` serait abandonné en silence** : *« la validation par le scoreur tient lieu de
        **seconde marque** »* (**actée**, source **FFTA B.6.1.1**). Un scoreur qui saisit **et**
        valide la même série auto-signe la double marque.

     **Décision finale : on ajoute l'annulation de validation, et `corriger_volee` reste.** Deux
     chemins d'écriture sur un score validé — c'est le prix, il est assumé et bien moindre que les
     quatre ci-dessus. Le « les deux, archer et scoreur » de la réponse est alors tenu **tel quel**,
     sans toucher à aucune garde. ⚠️ **Rien de `D-03`, `D-13`, `ADR-0030` ni `ADR-0035` n'est
     rouvert** : c'était le cas de la version précédente, ce ne l'est plus.
  2. **A09 est redirigé vers `E02US007`**, ce qu'ADR-0014 et ADR-0015 avaient déjà prévu mot pour
     mot : la licence arrive avec le fichier inscript'arc **qui la porte déjà**, sans imposer la
     saisie d'un numéro à 7 chiffres au guichet. ⚠️ Contrepartie assumée et écrite : jusque-là, deux
     homonymes du même club restent indécidables autrement que par la confirmation d'homonyme
     existante (ADR-0015). → CA déplacé dans [`stories/E02`](E02-inscriptions.md)
  3. **S09 : la hiérarchie est retenue**, au pied de la lettre du questionnaire — mais **sur les
     identités réelles du dépôt**. ⚠️ **RECTIFIÉ le 10/09/2026 en revue : la 1ʳᵉ rédaction disait
     `archer < scoreur < admin`, et ce rang du bas N'EXISTE PAS.**
     [`stories/E10`](E10-acces-roles.md) le dit en gras depuis le 14/07/2026 (`D-13`,
     [ADR-0030](../docs/adr/0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md)) : *« **Il n'y
     a pas de rôle archer** : il y a **un poste ouvert** »* — l'identité y est **le lieu**, pas la
     personne. Le scénario sur lequel l'arbitrage avait été présenté (« un scoreur écrasera un
     archer ») **ne peut pas se produire** : le scoreur n'a aucun accès à `POST /volees`.
     **Décision rectifiée : `poste de cible < scoreur < admin`.** ⚠️ **Le revers reste exposé et
     assumé** — une hiérarchie *tranche* sans *prévenir*. ⚠️ **Et elle ne couvre pas tout, ce qui a
     été dit au commanditaire avant qu'il confirme** : deux tablettes de cibles différentes portent
     le **même** rang, donc la hiérarchie n'arbitre **rien** entre elles — le dernier écrit gagne,
     comme aujourd'hui. Elle ne règle que *poste vs admin* (et *vs scoreur*, celui-ci entrant par
     l'élargissement d'`autoriser_saisie` décidé en 1). L'alternative (`409` + rafraîchir) est
     **écartée, non oubliée** : c'est elle qu'on reprend si le silence se paie en salle. → `E16US020`
  4. **A02 : l'encart va sur l'ACCUEIL**, pas sur « Suivi du déroulé ». L'organisateur qui ouvre un
     tournoi y atterrit (`axes.ts`, destination par défaut de l'axe pilotage) ; l'y renvoyer d'un
     clic aurait laissé le besoin « j'arrive et je vois » à un clic. → `E16US021`

- ~~**CA — S06 (routage)**~~ → `E16US018` : *« 3 mn si un autre tour suit »* — le panneau de routage doit rendre la tablette à la saisie au bout de trois minutes lorsqu'un tour suit. `PanneauRoutage` n'a aucun minuteur. Et *« visible si classement établi »* pour la place finale du perdant.
- ~~**CA — S08 (validation cible)**~~ → `E16US019` : *« plus de modification une fois validé »*. ~~⚠️ **Cela contredit un endpoint vivant**~~ ✅ **Requalifié le 10/09/2026 : ce n'est pas une contradiction** (cf. arbitrage 1 ci-dessus) — et le constat était **à moitié faux**, les duels tenant déjà la règle. Et *« [une validation peut être annulée] oui, par admin et scoreur »*, qui n'a aucune route.
- ~~**CA — S09 (états système)**~~ → `E16US020` : *« hiérarchie → archer < scoreur < admin »* pour trancher un conflit de modification concurrente. C'est une politique d'autorisation, énoncée sans ambiguïté et non implémentée.
- ~~**CA — A09 (inscriptions)**~~ → **`E02US007`** : *« on ne permettra pas 2 fois le même numéro de licence »*. ~~⚠️ **Contredit ADR-0014 et ADR-0015**~~ ✅ **Requalifié le 10/09/2026** : les deux ADR n'écartent pas la licence, ils **nomment son point de réouverture** (cf. arbitrage 2). ❌ **Le second CA est tenu** — *« placement manuel obligatoire, mais seulement si possible »*. ⚠️ **La justification a été REFAITE en revue le 10/09/2026, l'originale invoquait l'option refusée.** La question brute ([`a09-inscriptions.md`](../maquettes/questionnaires/tour-1-2026-08-04/a09-inscriptions.md), Q1) était **binaire** : *« proposition **automatique**, ou placement **manuel obligatoire** ? »* — et le commanditaire a choisi le manuel. Citer « Placer les restants » comme preuve, ainsi que le faisait la 1ʳᵉ rédaction, revenait à **invoquer la branche refusée** : ce bouton *est* la proposition automatique. Ce qui tient réellement le CA, c'est que **rien ne place tout seul à l'inscription** — une inscription tardive vaut réserve ([ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md)), et « Placer les restants » est un **geste de l'organisateur**, pas un automatisme. ⚠️ **Ne pas en déduire qu'un auto-placement à l'inscription honorerait A09 : il le violerait.**
- ~~**CA — A02**~~ → `E16US021` : *« une fois un tournoi choisi, on arrive sur la page du déroulé du tournoi avec un accueil qui reprend les informations du tournoi **par départ dans un grand encart** (mettre toutes les informations utiles au déroulé) »*. Seul le bandeau a été livré ; l'encart par départ, non.
- ⚠️ **CA — P05 : QUESTION OUVERTE, à reposer au commanditaire** *(statut rectifié en revue le 10/09/2026 — la 1ʳᵉ rédaction l'écartait, à tort)*. *« [les horaires prévisionnels] seulement pour les **depart** des differentes phases du tournoi, les autres sont trop imprevisible »*. **La réponse admet deux lectures, et elle ne tranche pas entre elles** :
  - **(a) un horaire prévisionnel par phase** — n'existe pas dans le domaine : le CA demande une **création**, pas un bornage ;
  - **(b) l'heure des DÉPARTS** — *départ* est un terme du domaine (créneau, [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md)) et `Depart.horaire` existe déjà, **obligatoire**, en `HH:MM`. Sous cette lecture la réponse dit « affichez l'heure des départs, pas des prévisions de tour » : c'est un **bornage d'existant**, front seul, quelques lignes.

  ⚠️ **L'autorité invoquée par la 1ʳᵉ rédaction était circulaire** : elle s'appuyait sur le commentaire de `frontend/src/features/tableaux/VueTableaux.tsx` (*« arbitrage du 04/08/2026 »*) — or ce prétendu arbitrage n'existe **ni en ADR, ni en story, ni au journal**, et le 04/08/2026 est la date **du questionnaire**, dont la réponse est un *oui* qualifié. Fermer un CA du commanditaire en citant le commentaire de code qui aurait dû l'implémenter est exactement la boucle que la règle 9 interdit — et le défaut qu'`E16US007` avait commis sur « audit consultable ». **Le CA reste dû tant qu'il n'est pas tranché.**
- ~~**⚠️ Vocabulaire (E16US001, ADR-0073)**~~ — ❌ **vérifié le 10/09/2026 : l'avertissement était FAUX, pour la 5ᵉ fois d'affilée** (après `E16US004`, `E16US005`, `E16US010`). Tout texte visible dit déjà « couloir » (`presentation.ts`, `VueSuivi.tsx`, `PlaceDeLArcher.tsx`, et les `aria-label` de `Placement.tsx`/`Duels.tsx`). Les occurrences restantes sont du CSS, des identifiants couverts par `DETTE-042`, ou un **autre sens** (`ClassementColline.tsx` : « Position » = le **rang**, hors périmètre d'ADR-0073). ⚠️ **Enseignement à ne pas reperdre** : cet avertissement a été recopié de fiche en fiche sans jamais être vérifié, et il a coûté cinq contrôles pour zéro correction. **Il n'est reconduit sur aucune des quatre US filles.**
- **Notes** : ~~⚠️ **US de rattrapage — à découper avant de prendre.**~~ ✅ **Découpage fait le 10/09/2026**, et la consigne s'est vérifiée : prise telle quelle, cette fiche aurait fait implémenter deux CA déjà tenus, poser un arbitrage prématuré (A09) et corriger un vocabulaire correct. ⚠️ **Ce que le découpage a ajouté et qui n'était dans aucune rédaction** : `saisie_par` est **déclaratif** (un nom libre, dit tel quel par sa docstring), donc **inutilisable comme source d'autorité** — la hiérarchie de S09 exige de persister le **rôle**, tiré du **jeton d'authentification** et jamais du corps de la requête. Sans ce constat, `E16US020` se serait livrée avec une hiérarchie qu'un poste peut contourner en se déclarant admin.
- **Dépend de** : E04US018 (routage), **E04US002** (saisie & validation de qualification — ~~`E04US003`~~ **n'existe pas** : l'identifiant a été absorbé par `E04US002` le 17/07/2026 à la refonte de maille. Corrigé le 08/08/2026), E10US001 (rôles), E02US002 (inscriptions) · **Jalon** : J3 · **Origine** : revue adversariale du 05/08/2026 sur le tri des questionnaires

---

### E16US018 — Le panneau de routage rend la tablette tout seul
*En tant que* **marqueur au poste de cible** (et scoreur en duels), *je veux* que le panneau de routage se referme seul quand un tour suit, *afin de* ne pas laisser une tablette bloquée sur un écran d'annonce pendant que la cible attend.

- **Contexte** : CA S06, sorti d'`E16US011` au découpage du 10/09/2026. Questionnaire S06 : *« 3 mn si un autre tour suit »* et *« visible si classement établi »*.
- ⚠️ **LE PANNEAU PORTE PLUSIEURS ARCHERS À LA FOIS — lire ce point avant les CA** *(relevé en revue le 10/09/2026, absent de la 1ʳᵉ rédaction)*. `PanneauRoutage` reçoit `archerIds: number[]` et rend **une ligne par archer**. Ses deux appelants : `SaisieDuels.tsx` le monte pour **les deux duellistes** du duel qu'on vient de valider — donc **un `prochain_duel` et un `termine`**, c'est le cas **nominal**, pas un cas limite — et `Saisie.tsx` pour **tous les archers de la cible** (jusqu'à quatre issues différentes). Les CA ci-dessous étaient écrits au singulier et se contredisaient dès le premier duel validé.
- **✅ ARBITRÉ le 10/09/2026 au cadrage — UN SEUL MINUTEUR, 3 minutes, quelle que soit l’issue.** *(Les deux « questions de cadrage » de la rédaction précédente — l’**agrégation** et le **cas terminal** — sont closes par cette réponse unique, et c’est ce qui la rend bonne : elles **disparaissent** au lieu d’être arbitrées séparément.)* Ni règle d’agrégation, ni classification d’issue. ⚠️ **La règle « il reste dès qu’une ligne est terminale » a été écartée sur mesure** : en duels le panneau est monté sur les **deux duellistes** du duel qu’on vient de valider, il y a donc une ligne terminale à **chaque** duel, à **tous** les tours — elle aurait rendu l’US **morte-née** sur cet écran, tests verts compris. La **fermeture par ligne** tombe pour la même raison : la ligne terminale reste, donc la tablette de duels ne revient jamais.
- **CA — le panneau se referme au bout de 3 minutes, dans tous les cas** : passé ce délai, la tablette revient d’elle-même à la saisie, sans geste. ⚠️ **Écart assumé au libellé du questionnaire** (*« 3 mn si un autre tour suit »*, muet sur le cas contraire) : la condition « si un tour suit » est **retirée**. Trois minutes suffisent à lire « 3ᵉ du tableau » ; un « jamais » laissait chaque tablette de la salle bloquée sur son annonce **au dernier tour**, l’inverse de l’intention de l’US.
- **CA — les duels gagnent la poignée de réouverture que la qualification a déjà** : un bouton « Où tire-t-on ensuite ? » sur la liste des matchs rouvre le panneau du dernier duel validé. ⚠️ **C’est ce qui rend la fermeture automatique sans danger**, et la raison pour laquelle le cas terminal n’a plus besoin de règle : `Saisie.tsx` porte cette poignée depuis `E04US018` (*« une porte automatique a toujours besoin d’une poignée »*), `SaisieDuels.tsx` **non** — une fermeture y était irréversible pour ce duel. Ferme du même coup les **deux cas adverses** rendus par la revue (repêché sans destination, `TERMINE` sans aucune place) : l’écran perdu se rouvre.
- **CA — un ÉCRITEAU ne se referme pas** *(ajouté en revue le 10/09/2026, arbitré par le
  commanditaire)*. Un avis **global** — « tir suspendu : restez à disposition », « phase finale non
  configurée », « tableau non constitué » — vaut **tant que la situation dure** : une pause tient 15
  à 20 minutes, et le minuteur l'emportait au tiers. ⚠️ **La question n'était donc PAS sans objet**,
  contrairement à ce que la 1ʳᵉ rédaction d'après-cadrage affirmait : le minuteur est aveugle aux
  issues **de routage**, pas aux avis permanents. ⚠️ **C'est le serveur qui les distingue**
  (`Routage.avis_permanent`, posé par l'unique constructeur `_tous_indisponibles`) : déduire l'écriteau
  côté client de « toutes les lignes sont en attente » confondrait la pause avec une ronde suisse où
  les quatre archers d'une cible portent un bye.
- **CA — la poignée des duels NOMME son duel** (« Où tire-t-on ensuite ? — duel n°3 ») *(ajouté en
  revue)*. L'état survit à la fermeture : à 11 h, un lien muet rouvre le duel validé à 9 h 40 en
  promettant celui qu'on regarde. ⚠️ **La parité avec la qualification était fausse** — là-bas le
  panneau suit la **cible affichée**, recalculée à chaque rendu ; ici c'est un instantané.
- **CA — le retour automatique s’annonce par un signal DISCRET, non chiffré** : une barre de progression et la mention « retour automatique », **sans compter les secondes**. ⚠️ **Le compte à rebours chiffré a été explicitement écarté au cadrage** : c’est la signature de la variante **C** du questionnaire S06, elle-même écartée au profit de la variante **A**. Un écran qui disparaît sans prévenir se lit comme un plantage, d’où le signal ; le chiffre, lui, rouvrait une variante déjà tranchée. ⚠️ **Reste un écart à la planche S06**, qui ne montre aucun signal : à tracer dans [`docs/maquettes.md`](../docs/maquettes.md), faute de quoi `E17US008` le relèvera comme écart de structure et le retirera.
- **CA — la place finale n’est annoncée que si le rang est établi** : sinon l’écran dit ce qu’il sait (fourchette, ou tour de sortie), sans jamais laisser croire à un classement acquis.
- **Notes** : ⚠️ **Vérifié dans le code au découpage — la moitié du travail est déjà là, l'autre pas du tout.**
  - **Le minuteur est absent, sans ambiguïté** : `grep` vide sur `frontend/src/features/routage/`. La seule sortie est le bouton `onRetour`/`libelleRetour` (`PanneauRoutage.tsx`), câblé par `Saisie.tsx` et `SaisieDuels.tsx`. Le panneau s'**ouvre** seul (`presentation.ts`, `panneauOuvert`) — rien ne le **ferme** seul.
  - **La distinction « un tour suit » existe DÉJÀ côté serveur** et c'est ce qui rend l'US petite : `IssueRoutage` porte `prochain_duel`, `prochaine_manche`, `termine`, `repeche`, `en_attente`, `indisponible`. **Front seul côté production** — mais ⚠️ le test qui épingle le CA *la place finale…* est un test **backend** (`rang_final` se calcule côté serveur). Aucune route, aucune migration, aucun DTO touché. ⚠️ **Le cadrage a rendu cette distinction INUTILE au minuteur** *(10/09/2026)* : il ne regarde aucune issue. Elle reste ce qui rend l’US petite pour l’autre moitié — le CA de la place finale — mais ne conditionne plus la fermeture.
  - **✅ Clos par l’arbitrage du 10/09/2026** : les deux points que la rédaction précédente demandait de trancher — **(1)** quelles issues comptent comme « un tour suit », **(2)** comment on **agrège** plusieurs lignes — n’ont **plus d’objet**. ⚠️ **Ne pas réintroduire de classification d’issue « par prudence »** à l’implication : `presentation.ts` porte déjà `encoreEnLice` (un `Record<IssueRoutage, boolean>` exhaustif), et s’en servir **ici** rétablirait précisément la règle d’agrégation que le cadrage a écartée.
  - ⚠️ **Deux cas adverses à couvrir, rendus par la revue** : un **repêché sans destination** (`REPECHAGE_SANS_DESTINATION`, `destination = None`) a « une suite », donc le minuteur emporterait le seul écran qui lui dit qu'il est repêché **sans lui dire où aller** ; et un **`TERMINE` sans aucune place** (`rang_final`, `rang_min` et `rang_max` tous `None`, motif `RANG_A_VENIR`) fait tomber la prémisse du CA « il reste, c'est là qu'il lit sa place » — il n'y a aucune place à lire. ✅ **Les deux sont couverts par le CA de la poignée de réouverture**, pas par une exception au minuteur : l’écran se referme comme les autres, et se rouvre à la main.
  - ⚠️ **Le CA *la place finale…* est en grande partie tenu, mais par accident, et c'est le piège** : `rang_final` est calculé **inconditionnellement** dès l'issue `TERMINE` (`backend/application/routage.py`), et le front replie sur `rang_min`/`rang_max` puis sur `tour_sortie` (`presentation.ts`). Le comportement observable ressemble à la règle ; **rien dans le code ne la porte**. Un `null` qui cesse d'être `null` la révoque en silence — d'où un test qui l'épingle. ⚠️ **Un test qui épingle une règle que le code ne fonde pas EST de la dette de conception** : à l'implémentation, soit la règle entre dans le code, soit elle s'inscrit au registre.
  - ⚠️ **`docs/fonctionnel/E04US018.md` est PÉRIMÉE sur ce point, pas seulement incomplète** *(corrigé en revue)* : elle affirme que pour un archer sorti avant les demi-finales « la mention **reste** *rang publié en fin de phase* », alors que depuis `E07US008` le front rend une **fourchette** (« 5ᵉ-8ᵉ du tableau ») et que `RANG_A_VENIR` ne subsiste **que** là où rien n'est acquis. L'US la **reprend**, elle ne fait pas que l'étendre. Elle ne mentionne par ailleurs aucune fermeture automatique.
  - **✅ Décisions de comportement, reversees ici en revue** (elles ne vivaient que dans le code et la
    fiche de recette) : **(a)** le décompte part de l'**ouverture du panneau**, pas de l'arrivée des
    données — un écran resté 3 min sur « Recherche des destinations… » se rend quand même ; **(b)** le
    minuteur **ne se réarme pas** à l'interaction ; **(c)** le panneau est rendu **avant** les sorties
    `isPending` / `isError` de ses deux appelants — son ancre est son instant de **montage**, donc
    placé après, un refetch en échec (`retry: false`) le démontait et le remontait avec trois minutes
    neuves : il ne se refermait **jamais** sur un wifi de salle. ⚠️ **L'ordre des branches est la
    règle** ; aucun test de rendu ne le protège (ils montent le composant une fois). Une US suivante
    qui dérive ses tests des CA ne verrait aucune des trois.
  - ⚠️ **COÛT ASSUMÉ — le décompte court écran éteint** *(arbitré par le commanditaire le
    10/09/2026 : temps d'horloge, pas temps visible)*. Sur une tablette BYOD qui se met en veille
    (30 s à 2 min), les archers rangent leurs flèches, reviennent, réveillent l'écran — le panneau a
    déjà disparu. Un seul concept a été préféré à deux ; la poignée rattrape, à condition de savoir
    qu'il y avait quelque chose à lire. **À rouvrir si un tournoi réel remonte le cas.**
  - ⚠️ **L'étape « ne touchez à rien pendant trois minutes » de la fiche de recette n'est pas
    exécutable telle quelle** sur une vraie tablette : le testeur devra l'empêcher de dormir, donc ne
    testera pas tout à fait le comportement livré. Conséquence directe du point ci-dessus.
- **Dépend de** : E04US018 (routage) · **Jalon** : J3 · **Origine** : questionnaire S06, 04/08/2026 — sortie d'`E16US011` le 10/09/2026

---

### E16US019 — Annuler une validation pour corriger
*En tant que* scoreur, *je veux* **annuler une validation** au lieu de réécrire un score validé, *afin de* corriger une erreur sans qu'il existe deux façons d'écrire sur le même résultat.

- **Contexte** : CA S08, sorti d'`E16US011` au découpage du 10/09/2026. Questionnaire S08 : *« plus de modification une fois validé »* et *« [une validation peut être annulée] oui, par admin et scoreur »*.
- **✅ ARBITRÉ le 10/09/2026 — ce n'étaient pas deux règles contradictoires, mais UNE procédure en deux temps.** La fiche d'origine annonçait un affrontement entre le questionnaire et un endpoint vivant ; la relecture du code montre un **enchaînement** : on n'édite pas un score validé, on **annule la validation**, on corrige, on revalide. Décision du commanditaire : **c'est ce parcours, et lui seul**.
- **CA — annuler une validation est un acte à part entière** : ouvert à l'**admin et au scoreur** (élargi, pas doublé — la ligne du dépôt depuis `E16US008`), **tracé à l'audit**, et il **rouvre** la volée à l'écriture.
- **CA — `corriger_volee` est CONSERVÉ** *(tranché en 2ᵉ passe de revue le 10/09/2026, cf. arbitrage 1 : la 1ʳᵉ rédaction le supprimait, la 2ᵉ l'élargissait, la 3ᵉ le garde)*. La réponse S08 complète — *« **les deux, archer et scoreur** »* — est alors tenue **sans toucher à aucune garde** : le poste de cible saisit par `saisir_volee`, le scoreur corrige par `corriger_volee`. ⚠️ **Deux chemins d'écriture coexistent sur un score validé, et c'est assumé** : le prix est réel (idempotence, audit et règles métier à tenir aux deux endroits) mais il est **bien moindre** que les quatre coûts chiffrés à l'arbitrage 1 — garde inter-tournois perdue, trace d'audit perdue, `None` polysémique, et `D-03` auto-signé.
- **CA — l'annulation ne se substitue à rien, elle s'ajoute** : c'est la moitié manquante de S08 (*« une validation peut être annulée »*), pas un remplacement du chemin de correction. ⚠️ **Ne pas en déduire un CA « un seul chemin d'écriture »** : il serait faux le jour de sa livraison, cf. l'inventaire des surfaces ci-dessous.
- **CA — annuler rouvre LE LOT VALIDÉ, pas une volée isolée, et le lot est IDENTIFIÉ EN BASE** *(arbitré au cadrage du 11/09/2026 : la recommandation « le lot » a été confirmée par le commanditaire ; le **moyen** a été tranché par l'assistant en cours d'US)*. `Serie.valider` verrouille un **lot** dont la taille vient de la politique injectée `GrainValidation` (`FIN_DE_SERIE`, ou `TOUTES_LES_N_VOLEES` avec reliquat de fin de barème) : annuler sur la volée `n` rouvre **toutes les volées validées par le même acte**. ⚠️ **Ne pas rouvrir une volée seule** : cela laisserait un trou au milieu d'un bloc validé, et « bloc validé » cesserait d'être une notion vérifiable. ⚠️ **Et NE PAS reconstituer le lot par le calcul** — la voie « tranche de rang `(n-1) // N` » a été essayée puis écartée le 11/09/2026 : `saisir_volee` **n'impose aucun ordre** de saisie (`backend/domain/serie.py`, il ne valide que le rang `1..N`) alors que `valider` prend « les `N` premières **non validées** », si bien qu'un lot réel peut être **non contigu** — volées 1 et 3 si la 2 n'était pas encore saisie. Le calcul rouvrirait alors des volées que personne n'a annulées. `validee_par` étant un **nom** et non un identifiant d'acte, l'identité du lot est **portée par une colonne** posée à la validation.
- **CA — la volée rouverte RESTE COMPTÉE dans les totaux, signalée « en correction »** *(arbitré au cadrage du 11/09/2026 — le commanditaire a écarté les DEUX branches que la fiche proposait, « fenêtre assumée » et « acte unique », pour une troisième voie)*. Le score reste au classement, au palmarès et à l'écran de salle pendant toute la correction, avec un **marqueur visible** ; c'est le **droit d'écrire** qui se rouvre, pas le **compte**. ⚠️ **Conséquence de conception, et elle invalide la note « aucune migration » plus bas** : `Volee.verrouillee` porte aujourd'hui **deux sens à la fois** — « interdite à l'écriture » **et** « comptée dans les totaux ». Les tenir séparés demande un **état de plus sur la volée**, donc une **migration**. ⚠️ **Le cas qui justifie l'arbitrage** : une annulation jamais suivie de ressaisie — le scoreur annule, part en pause, personne ne corrige. Sous « fenêtre assumée » l'archer sortait du classement **indéfiniment** ; ici il n'en sort jamais. Contrepartie **assumée** : le classement affiche un temps un score que le scoreur a déclaré faux — d'où le marqueur, qui n'est pas décoratif mais **la moitié du CA**. ⚠️ **La ressaisie ne doit pas faire sortir la volée du compte non plus** : `saisir_volee` reconstruit une `Volee` neuve, donc il doit **préserver** l'état de validation d'une volée en correction — sans quoi l'arbitrage est perdu à l'endroit même où il sert.
- **CA — l'US livre AUSSI la surface scoreur de la qualification** *(périmètre arbitré au cadrage du 11/09/2026)*. ⚠️ **Le CA « l'écran dit ce qu'il fait » était insatisfaisable en l'état** : le backend expose `POST /saisie/validations` et `/corrections` depuis `E04US002`, mais **aucun composant front ne les appelait** — `EspaceScoreur.tsx` renvoyait à « une surface distincte, §7.3 » et `docs/fonctionnel/E04US002.md` la notait « à venir ». Le découpage d'`E04US002` le dit en toutes lettres : la surface scoreur n'était dans **aucune** de ses quatre tranches, et **aucune US ne l'a reprise depuis** — c'est un trou de backlog, pas un oubli d'exploration. Périmètre retenu : **voir les feuilles d'un créneau, valider, annuler**. La **correction directe** depuis cet écran reste hors tranche — le parcours S08 passe par la ressaisie sur la **tablette**, qui existe déjà. ⚠️ Conséquence technique : la lecture `GET /saisie/series/…`, gardée `autoriser_saisie` (admin **ou poste**), est **élargie au scoreur** — sans quoi l'écran qui valide ne peut pas afficher ce qu'il agit.
- **CA — `corriger_volee` opère sur une volée COMPTÉE, pas verrouillée** *(retourné en 2ᵉ passe de
  revue, 11/09/2026)*. Une rédaction précédente disait « les deux chemins ne se croisent pas ». Ils
  se croisent, et il le faut : c'est le seul recours **au service** quand une pause tombe **entre**
  l'annulation et la ressaisie — les deux gestes qui referment une correction sont gelés, celui-ci
  ne l'est pas. ⚠️ **Recours d'API, pas geste d'organisateur** : aucun écran n'expose la correction
  directe, ni avant cette US ni après. À l'écran, une volée rendue avant une pause **attend la
  relance** (précisé en 3ᵉ passe de revue : la rédaction précédente promettait un chemin utilisateur
  qui n'existe pas).
  ⚠️ **L'arbitrage du commanditaire prime sur le CA dérivé** : E05US033 dit « la pause gèle ce qui
  *avance*, jamais ce qui *répare* », et la rédaction précédente restreignait cette règle sans
  l'avoir demandé. Corriger ne **referme pas** la correction : le scoreur revalide ensuite.
- **CA — refermer une correction est un geste NOMMÉ** *(bloquant de 3ᵉ passe de revue, sondé)*.
  `POST /saisie/refermetures` porte le **numéro** de volée, donc le lot ; `POST /saisie/validations`,
  qui ne reçoit aucune cible, **refuse** tant qu'une correction est ouverte. ⚠️ **Deux rédactions ont
  essayé de deviner** — « toutes les corrections », puis « la plus ancienne » — et les deux
  re-signaient des volées jamais relues sous le nom de qui cliquait. *(Remplace le CA ci-dessous,
  gardé pour mémoire du raisonnement.)*
- ~~**CA — revalider referme UN lot, le plus ancien**~~ *(bloquant de revue, 11/09/2026, sondé à
  l'exécution)*. Une première implémentation refermait **toutes** les corrections de la feuille :
  deux lots annulés par deux personnes pour deux motifs se retrouvaient re-signés d'un seul clic —
  les volées **jamais ressaisies** redevenaient « valides » avec leurs valeurs fausses et changeaient
  de validateur. Refermer est un **acte**, comme annuler : un lot par geste. ⚠️ Conséquence à dire à
  l'écran : tant qu'une correction est ouverte, « Valider » **referme** au lieu de valider une
  saisie neuve — le bouton doit donc nommer le geste qu'il déclenche.
- **CA — annuler est REFUSÉ pendant une pause** *(retourné en revue le 11/09/2026 — la première
  rédaction disait l'inverse)*. « La pause gèle ce qui *avance*, jamais ce qui *répare* » (E05US033)
  reste vrai, mais les **deux** gestes qui referment une correction sont gelés, eux : `saisir_volee`
  (la ressaisie, sur la tablette) et `refermer_correction` (chez le scoreur) portent
  `refuser_si_en_pause`. Annuler pendant une pause rouvre donc une volée que **plus rien** ne peut
  refermer avant la relance. ⚠️ `corriger_volee`, lui, **répare** sans être gelé — mais il ne
  referme pas la fenêtre, et aucun écran ne l'expose *(rédaction corrigée en 4ᵉ passe : la
  précédente nommait `valider`, qui ne referme plus rien, et prêtait à `corriger_volee` un refus que
  le CA voisin lui avait retiré)*. ⚠️ **Le test d'origine prouvait la permissivité sans jamais dérouler la suite du
  parcours qu'elle rendait possible** — vert, et le parcours mort.
- **CA — la ressaisie d'une volée rouverte est TRACÉE** *(ajouté en revue le 11/09/2026)*. Elle est
  déjà comptée au classement : la réécrire est un acte sensible. Sans trace, l'annulation **baissait**
  la traçabilité — le seul chemin d'écriture restant est `saisir_volee`, ouvert au **poste de cible**
  et muet, là où `corriger_volee` exigeait le scoreur et écrivait l'avant/après.
- **CA — le statut PUBLIC d'une volée suit le compte, pas le verrou** *(bloquant de revue,
  11/09/2026)*. `deroule.py` dérivait « valide / en attente » de `verrouillee` : le public lisait
  « en attente » sur des volées dont les points étaient dans le **même** `cumul`. Amende
  [ADR-0039](../docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md) § Décision 2.
- **CA — l'écran dit ce qu'il fait** : annuler une validation n'est pas anodin ; le geste passe par une confirmation qui **nomme** ce qui va être rouvert, comme le forfait depuis `E16US007`.
- **Notes** : ⚠️ **Le constat d'origine était à moitié faux, et cela réduit l'US.**
  - ⚠️ **L'INVENTAIRE DES SURFACES — refait en revue, la 1ʳᵉ rédaction en oubliait deux.** Il y a **quatre** surfaces où un résultat s'acte, pas deux :

    | Surface | État au 10/09/2026 | Dans l'US ? |
    |---|---|---|
    | **Qualification** | `corriger_volee` (`POST /saisie/corrections`, `exiger_scoreur`, tracé `CORRECTION_SCORE`) réécrit une série verrouillée ; aucune annulation | **oui** — c'est le périmètre, et le seul |
    | **Duels** | `DuelVerrouille` refuse `saisir_manche`, `saisir_barrage` et une seconde `valider`. ⚠️ **L'agrégat `Duel` est écrit par QUATRE routeurs**, pas un : `/api/v1/duels/`, mais aussi `poules.py`, `suisse.py` et `colline.py` — tous sains, tous passant par le même agrégat. Vérifier un seul routeur ne prouve rien | **non** — S08 y est **déjà tenu** |
    | **Barrage de places** | `PUT …/barrages/{id}/manche` réécrit une manche close, `DELETE …/barrages/{id}` annule un barrage clos. ⛔ **CE N'EST PAS UN TROU, C'EST UNE DÉCISION** *(requalifié en 2ᵉ passe)* : `application/barrages.py` le motive en toutes lettres — *« saisir une manche sur un barrage clos le **rouvre** : on vient de dire que son résultat n'était pas le bon »*, et *« garder les deux portes fermées laissait un juge ayant acté un verdict inversé envoyer le mauvais archer au tableau, **définitivement** »* | **NON, et surtout pas** — y appliquer S08 **restaurerait ce bug** |
    | **Big Shoot Off** | l'agrégat `Serie` se verrouille ; `POST /validations` mais **aucune** route de correction **ni d'annulation** | **non** — immuable, donc S08 tenu à moitié ; l'autre moitié y serait une capacité neuve, hors tranche |

    ⚠️ **Cet inventaire est la raison pour laquelle aucun CA de cette fiche ne dit « un seul chemin d'écriture »** : la formule serait fausse le jour de sa livraison. Le périmètre est la **qualification**, et lui seul.
  - **Le verrou est dérivé, pas stocké** : `Volee.verrouillee` est une property qui vaut `validee_par is not None` (`backend/domain/serie.py`). ⚠️ **~~donc probablement aucune migration~~ — CADUC depuis le cadrage du 11/09/2026** : le CA « la volée rouverte reste comptée » sépare le verrou d'écriture de la prise en compte, ce qu'une property à un seul champ ne peut plus porter. **Annuler n'est donc PAS « reposer `validee_par` à `None` »** — ce geste-là effacerait aussi le compte, qui est exactement ce que le CA veut garder.
  - ⚠️ **LE POINT LE PLUS COÛTEUX DE L'US — NEUTRALISÉ par l'arbitrage du 11/09/2026, et c'est précisément ce que cet arbitrage achetait.** Le constat reste exact sur le code d'**avant** l'US : `Serie.cumul`, `compter`, `nb_fleches_validees` et `est_complete` ne somment que les volées **verrouillées**, si bien qu'une volée dévalidée sortait du total (versant visible : classement, palmarès, écran de salle, et l'exposition publique qui rebascule en `en_attente`, ADR-0039) **et désarmait trois gardes** (versant invisible, manqué en 1ʳᵉ correction : `nb_fleches_validees` n'alimente aucun total, c'est la mesure de « **l'archer a déjà tiré** »). ⚠️ **La liste qui suit n'est donc plus une fatalité à assumer : c'est la PREUVE À ÉCRIRE.** Trois tests doivent montrer que chacune de ces décisions est **inchangée** pendant qu'une volée est en correction —
    - `application/archers.py` → `ChangementCategorieArcherEngage` (E02US003) : pendant la fenêtre, un admin change la catégorie **sans l'avertissement**, et les flèches revalidées atterrissent dans le nouveau classement ;
    - `application/placement.py` → `_impact` : « cibles avec scores » **sous-compte**, et l'organisateur confirme une régénération de plan sur un chiffre faux (`DETTE-037` est juste à côté) ;
    - `application/completude.py` → `_a_tire` / `_est_clos` : la complétude du créneau **régresse** le temps de la correction.

    **Le chemin actuel n'a pas cette fenêtre** — `corriger_volee` réécrit en place sans déverrouiller, ce qui est un argument de plus pour l'avoir conservé. **Arbitrage attendu au cadrage** : annulation + ressaisie doivent être **un seul acte de service** (la volée ne quitte jamais le total), sinon **trois gardes se désarment sans que personne l'ait décidé**. ⚠️ **Le cas qui tranche** : une annulation **jamais suivie de ressaisie** — le scoreur annule, part en pause, personne ne corrige. Sous « fenêtre assumée », l'archer reste hors classement **indéfiniment**, sans que rien ne le signale.
  - ⚠️ **Tension à lever avec `E16US020`** : un **admin** qui annule devient le dernier écrivain ; sous la hiérarchie de `E16US020`, la volée se verrouille alors contre le scoreur **et** contre la tablette — c'est-à-dire contre ceux qui doivent la corriger. **Invariant qui borne les deux fiches, à écrire des deux côtés** : *une annulation de validation remet la préséance à zéro sur la volée concernée*. Sans lui, les deux CA produisent des tests **contradictoires** dès que c'est le scoreur qui annule — le cas majoritaire.
  - ⚠️ **ASYMÉTRIE LAISSÉE OUVERTE, constatée au cadrage du 11/09/2026** : l'annulation est ouverte à l'**admin et au scoreur** (réponse S08), mais `POST /saisie/validations` reste `exiger_scoreur` — un admin qui annule **ne peut pas revalider lui-même**. Rien ne se bloque (la volée reste comptée, cf. le CA ci-dessus), mais élargir la validation demanderait un CA que S08 **ne donne pas** : ce serait le décider seul. À rouvrir si un tournoi réel montre un admin coincé.
  - ⚠️ **Aucune route n'est retirée** *(depuis l'arbitrage du 10/09/2026)* : pas de changement d'API, pas d'appelant front à reprendre, et les deux fiches fonctionnelles qui décrivent la correction directe **restent vraies**. ⚠️ **`ADR-0035` n'est PAS rouvert** non plus — ses § Décision 2 et 3 nomment la réécriture d'un score corrigé et `CORRECTION_SCORE`, qui **survivent** tous les deux. *(Les deux rédactions précédentes annonçaient l'inverse ; c'est la suppression de `corriger_volee` qui les rouvrait.)* L'audit **gagne** simplement un type de trace pour l'annulation (`E10US005`).
- **Dépend de** : E04US002 (saisie & validation de qualification), E10US001 / E10US003 (rôles), E10US005 (audit) · **Jalon** : J3 · **Origine** : questionnaire S08, 04/08/2026 — sortie d'`E16US011` le 10/09/2026

---

### E16US020 — Deux écritures, une même volée : le rôle tranche
*En tant qu'*organisateur, *je veux* qu'une écriture concurrente sur la même volée soit arbitrée par le **rang** de qui écrit, *afin qu'*une saisie de tablette n'efface pas la correction que le scoreur vient de faire.

- **Contexte** : CA S09, sorti d'`E16US011` au découpage du 10/09/2026. Questionnaire S09 : *« hiérarchie → archer < scoreur < admin »* pour trancher un conflit de modification concurrente.
- **✅ ARBITRÉ le 10/09/2026, puis RECTIFIÉ le même jour en revue.** La **hiérarchie** est retenue — mais sur les identités réelles du dépôt. ⚠️ **La 1ʳᵉ rédaction disait `archer < scoreur < admin` : ce rang du bas N'EXISTE PAS.** [`stories/E10`](E10-acces-roles.md) le dit en gras depuis le 14/07/2026 (`D-13`, [ADR-0030](../docs/adr/0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md)) : *« **Il n'y a pas de rôle archer** : il y a **un poste ouvert** »*. Le scénario sur lequel l'arbitrage avait été présenté au commanditaire — « un scoreur écrasera un archer » — **ne pouvait pas se produire** : le scoreur n'a aucun accès à `POST /volees`.
- **CA — le rôle supérieur écrase, l'inférieur est refusé en `409`** : **`poste de cible < scoreur < admin`**, les trois identités que le dépôt porte vraiment. L'écran dit pourquoi le refus tombe — un refus muet serait pire que l'écrasement qu'il remplace. ⚠️ **Ce qui a été écarté est le refus SYMÉTRIQUE**, indépendant du rôle, qui aurait montré le conflit aux **deux** parties : ne pas lire « le `409` est écarté ».
- **CA — à rôles ÉGAUX, la règle n'arbitre rien** *(conséquence dite au commanditaire avant qu'il confirme)*. Deux tablettes rattachées à la **même** cible portent le même rôle : entre elles, le dernier écrit gagne, exactement comme aujourd'hui. ⚠️ **C'est le cas le plus fréquent en salle**, et c'est celui que le refus symétrique aurait couvert. Le CA se prouve par un **test négatif** — « deux postes écrivent successivement : le second gagne, `200`, aucun `409` » — sans lequel ce renoncement serait invisible dans le code. **Critère de réouverture écrit** : on reprend l'alternative si un tournoi réel remonte ≥ 1 saisie perdue entre deux postes.
- **CA — le rôle est celui de la GARDE, jamais celui du message** : l'arbitrage se fait sur l'identité résolue à la frontière (jeton de poste, session scoreur, session admin), pas sur ce que la requête déclare. ⚠️ **Ne pas écrire « identité authentifiée »** : le rôle le plus bas ne l'est justement **pas** — `autoriser_saisie` rend un `Poste`, c'est-à-dire un **lieu**. C'est une conséquence assumée d'`E10US007`, et c'est précisément ce qui rend l'ordre nécessaire.
- **CA — une annulation de validation remet la préséance à ZÉRO sur la volée concernée** *(la notion de « volée rouverte » dont ce CA dépend est **définie et livrée** depuis `E16US019` — [ADR-0109](../docs/adr/0109-une-volee-en-correction-reste-comptee.md) : `Volee.en_correction`. Borne rendue testable en 2ᵉ passe — la rédaction précédente disait « fenêtre à définir au cadrage », ce dont aucun test ne se dérive)*. Sans elle, un scoreur ou un admin qui annule une validation (`E16US019`) devient le dernier écrivain et verrouille la volée contre **ceux qui doivent la corriger** — et les deux fiches produisent des tests **contradictoires** dès que c'est le scoreur qui annule, le cas majoritaire. La règle arbitre une **concurrence**, pas une préséance permanente.
- **CA — la règle ne vaut que pour la volée de QUALIFICATION** *(arbitrage du commanditaire, 12/09/2026 — la question était ouverte dans les Notes)*. Duels, poules, système suisse, colline et Big Shoot Off gardent le **dernier écrit gagne**. ⚠️ **Ce n'est pas un oubli, et ce n'est pas non plus un cas particulier dans le code** : la préséance est portée par la **donnée** (`Volee.role_de_saisie`), et une surface qui n'en revendique aucune (`None`) n'oppose rien — la règle y est inerte **par construction**. Conséquence assumée : deux comportements coexistent dans l'application selon le format. ⚠️ **Ce qui découle de ce périmètre** : la hiérarchie **ne vit qu'au service de saisie**, donc `DETTE-065` (le garde d'autorisation recopié dans sept routeurs d'écriture) n'est **ni élargie ni résorbée** ici. L'élargir à tous les formats serait une **seconde US**, et c'est à ce moment-là que la ligne de dette se résorbe — pas avant.
- **CA — le sens descendant refuse AUSSI, et c'est assumé** *(arbitrage du commanditaire, 12/09/2026)*. Un **admin** saisit par erreur sur la cible 7 ; le **poste de cible 7** ne peut plus corriger — `409`. ⚠️ **Si le rang inférieur pouvait reprendre la main, l'ordre ne servirait à rien** : la règle ne serait plus une hiérarchie mais une politesse. **Le recours est que l'organisateur ressaisisse lui-même la valeur juste** — rang égal, donc accepté. ⚠️ **Ce n'est PAS « il annule la validation »** : la 1ʳᵉ rédaction l'affirmait dans cinq artefacts, et c'est **faux** — le `409` ne tombe que sur une volée **non verrouillée**, où `annuler_validation` lève `VoleeNonVerrouillee` (« il n'y a rien à annuler », ou « déjà en correction »). L'annulation ne remet la préséance à zéro que sur une volée **déjà validée**. Épinglé par `test_le_recours_au_refus_vers_le_bas_est_la_ressaisie_par_l_organisateur`, sans quoi la doc rediverge. ⚠️ **Le refus doit donc nommer ce recours à l'écran**, sinon le marqueur lit un mur : c'est le même raisonnement que « un refus muet serait pire que l'écrasement qu'il remplace ».
- **CA — CORRIGER est une écriture comme une autre** *(ajouté en revue le 12/09/2026 — quatre axes ont trouvé le même trou)*. `POST /saisie/corrections` (garde `exiger_scoreur`) **pose** `Role.SCOREUR` sur la volée. ⚠️ **Sans ce CA, l'US ne tenait pas sa propre promesse** : le scoreur corrigeait une volée rouverte, sa correction ne revendiquait rien, et la tablette l'écrasait **en silence** — le défaut que l'US existe pour fermer, déplacé d'un endpoint à l'autre, et sur le croisement (scoreur, poste) que le questionnaire S09 visait en premier. ⚠️ **C'est aussi le SEUL site où `Role.SCOREUR` s'inscrit en base** : la saisie n'admet que l'admin et le poste. Sans lui, le rang du milieu n'existait que dans l'énumération.
- **Notes** : ✅ **ADR écrit** — [ADR-0107](../docs/adr/0107-une-ecriture-concurrente-est-arbitree-par-le-role-de-qui-ecrit.md). Un ordre entre rangs est une politique d'autorisation, là où le dépôt n'a aujourd'hui que des prédicats indépendants : c'est le **premier** du dépôt. *(Écrit **avant** l'implémentation, sur le patron d'[ADR-0102](../docs/adr/0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) : § « Porté dans le code par » = « rien à ce jour, et c'est écrit exprès » — ce qui évite le défaut d'ADR-0017 sans pour autant laisser la décision sans trace.)*
  - ⚠️ **Le piège central, trouvé au découpage et absent de toutes les rédactions** : `Volee.saisie_par` **existe** mais sa propre docstring le qualifie de **« déclaratif »** — c'est un **nom libre**, pas un rôle, et il vient du corps de la requête. **L'utiliser comme source d'autorité livrerait une hiérarchie qu'un poste contourne en se déclarant admin.**
  - ⚠️ **UN ÉTAT PERSISTÉ EST REQUIS — et ce point a été corrigé deux fois en sens inverse.** La 1ʳᵉ rédaction disait « migration attendue » ; la 1ʳᵉ correction l'a ramenée à « probable », au motif que le rôle pouvait se **dériver de la garde** ; la 2ᵉ passe a montré que cette voie **n'existe pas**, et quatre axes l'ont trouvé indépendamment. La règle compare le rôle entrant à celui **qui a déjà écrit** — or la garde ne fournit jamais que le premier, et le second n'est stocké **nulle part** (`saisie_par` est interdit par le CA « le rôle est celui de la garde », et `validee_par` n'existe qu'une fois la volée validée, alors que le cas visé est la volée **non validée**). Deux voies réelles : **une colonne** (migration) ou **un registre en mémoire** à la manière de `RegistreIdempotence` — volatile, donc la préséance est perdue au redémarrage, ce qui doit être assumé et inscrit au registre. ⚠️ **Leçon** : j'avais corrigé un énoncé qui était juste.
  - ⚠️ **La discrimination des trois rôles à la frontière n'est pas acquise sur la route concernée** : sur `POST /saisie/volees`, seul `autoriser_saisie` est monté, et il ne distingue que **deux** états (admin = `None`, poste). Composer une troisième identité y suppose une dépendance neuve.
  - ⚠️ **Si la hiérarchie vaut pour tous les formats, elle atterrit sur les 7 sites de `DETTE-065`** (le garde d'autorisation des routeurs d'écriture, recopié sept fois). La règle doit alors vivre en **un** endroit — service ou domaine —, pas dans chaque routeur, et la ligne de `DETTE-065` sera à élargir ou à résorber au même moment.
  - **Il n'y a aucun mécanisme de conflit aujourd'hui** : `backend/infrastructure/idempotence.py` ne dédoublonne qu'un **rejeu du même client** (`identifiant_saisie` identique). Deux écritures d'identifiants différents sur la même volée non validée → la seconde écrase la première **en silence** (`Serie.saisir_volee`), sans version, sans horodatage comparé, sans `409`.
  - **La file d'écriture (règle 7) ne protège de rien ici** : le writer unique **sérialise** les écritures, donc il n'y a pas de course en base — mais sérialiser n'est pas arbitrer, et c'est exactement ce qui rend le défaut invisible.
  - **Les rôles n'ont aucun ordre** : `exiger_admin`, `exiger_scoreur`, `exiger_poste_de_cible`, `autoriser_saisie`, `autoriser_forfait` (`backend/api/dependances.py`) sont des prédicats indépendants. L'US introduit la **première** notion de rang entre rôles du dépôt — d'où l'ADR.
  - ~~⚠️ **Un cas adverse rendu par la revue**~~ → ✅ **tranché le 12/09/2026**, cf. le CA « le sens descendant refuse aussi » ci-dessus.
  - ~~⚠️ **Question de périmètre à trancher au cadrage**~~ → ✅ **tranché le 12/09/2026**, cf. le CA de périmètre ci-dessus. `DETTE-065` n'est donc **ni élargie ni résorbée** par cette US : la règle ne vit qu'au service de saisie de qualification, elle ne touche aucun des sept gardes recopiés.
  - ⚠️ **Inscrit en `DETTE-100` : le refus reste injoignable depuis les écrans** — mais pas pour la raison écrite en 1ʳᵉ passe. L'unique appelant front de `POST /saisie/volees` est la tablette (portée `'poste'` en dur), et deux tablettes sont à **rang égal**. ⚠️ **La 1ʳᵉ rédaction disait « aucun écran ne fait se croiser deux rangs » : c'était FAUX** — le scoreur écrit au rang 2 depuis l'écran d'`E16US019` (`corriger_volee`), et le poste depuis le sien. Les rangs se croisent bel et bien à l'écran ; ce qui manquait, c'est que la correction **revendique** son rang, corrigé par le CA ci-dessus. Reste injoignable : le refus **vers le bas**, faute d'écran d'administration qui saisisse. La règle est donc **tenue et prouvée côté serveur**, et le rendu ambre livré est **prêt mais injoignable**. ⚠️ **Ne pas lire « le front est inutile »** : le laisser retomber sur le message générique afficherait, le jour où un admin écrit par l'API, une phrase de conflit **sans recours**. Le scénario de recette le dit franchement plutôt que de faire semblant.
- **Dépend de** : E04US002 (saisie), E10US001 (rôles), **E10US007** ✅ *(livrée — « **Poste de cible : saisir sans s'identifier** ». ⚠️ La 1ʳᵉ rédaction la nommait « saisie par l'archer » et la disait prérequise : elle est livrée, et c'est **elle** qui fixe l'identité du rang le plus bas — le **lieu**, pas la personne.)* · **Jalon** : J3 · **Origine** : questionnaire S09, 04/08/2026 — sortie d'`E16US011` le 10/09/2026

---

### E16US021 — L'accueil du tournoi parle par départ
*En tant qu'*organisateur, *je veux* qu'en ouvrant un tournoi je voie **chaque départ** avec ce qui sert à le dérouler, *afin de* piloter la journée sans aller chercher un créneau à la fois.

- **Contexte** : CA A02, sorti d'`E16US011` au découpage du 10/09/2026. Questionnaire A02 : *« une fois un tournoi choisi, on arrive sur la page du déroulé du tournoi avec un accueil qui reprend les informations du tournoi **par départ dans un grand encart** (mettre toutes les informations utiles au déroulé) »*.
- **✅ ARBITRÉ le 10/09/2026 — l'encart va sur l'ACCUEIL**, pas sur « Suivi du déroulé ». C'est là que l'organisateur atterrit en ouvrant un tournoi (`frontend/src/features/admin/axes.ts`, destination par défaut de l'axe pilotage) ; le renvoyer ailleurs aurait laissé le besoin « j'arrive et je vois » à un clic.
- **CA — un bloc par départ** : chaque créneau porte ce qui sert au déroulé, tous visibles **côte à côte** et non un à la fois. ⚠️ **L'énumération qui suit est une PISTE à confirmer au cadrage, pas le CA** — horaire, effectif, avancement des phases, pauses en cours. La 1ʳᵉ rédaction la posait comme normative tout en demandant deux puces plus bas de borner la formule avec le commanditaire : un test en aurait dérivé l'énumération et l'arbitrage n'aurait jamais eu lieu.
- **CA — sans fabriquer une seconde source** : les chiffres et les états viennent de ce qui les calcule déjà ; l'accueil **lit**, il ne recalcule pas.
- **Notes** : ⚠️ **Le constat de la fiche d'origine est exact, et le trou est réel.**
  - **L'accueil ne porte aujourd'hui que des totaux tournoi** : `frontend/src/features/accueil/Accueil.tsx` rend le nom + `BadgeStatut`, `PastilleDeRelance` (E05US034), `FriseCycleDeVie`, trois chiffres agrégés (Inscrits / Réglés / Postes en ligne) et deux cartes « À faire » / « Alertes ». **Rien n'y est ventilé par créneau.**
  - **L'écran par créneau existe, mais fait l'inverse de ce que le CA demande** : `SuiviDeroule.tsx` montre **un seul** départ à la fois via un sélecteur `ChoixCreneau`, et `PilotageCreneau.tsx` en porte le détail. Le CA veut **tous les départs d'un coup**.
  - ⚠️ **Le vrai risque est le doublon d'affordance, pas le rendu** : l'accueil porte déjà la frise (avec ses boutons « Démarrer »/« Terminer »), la pastille de relance de pauses, et « Prêt à démarrer ? » vit à côté (`E16US012`). C'est **`DETTE-082`** — *deux endroits pour démarrer le même tournoi* —, dont la section *Résorption* désigne nommément la refonte de navigation d'`EPIC-16` plutôt qu'un correctif local : **cette US en est le candidat naturel**. Elle **ajoute une troisième surface au même écran** et doit donc dire ce qu'elle **enlève**, pas seulement ce qu'elle ajoute. *(La 1ʳᵉ rédaction décrivait cette dette en prose sans la nommer — ce qui casse le geste de résorption, un `grep DETTE-082`.)*
  - ⚠️ **Point à vérifier au cadrage** : existe-t-il une lecture **agrégée par départ** côté serveur, ou faut-il la construire ? L'accueil ne doit pas monter une requête par créneau — un tournoi à quatre départs paierait quatre allers-retours à chaque poll. ADR-0075 (*le départ est la portée sportive*) rend cette agrégation légitime ; `DETTE-031` (chaque lecture reconstruit les phases à tableau) dit ce qu'elle coûtera.
  - ⚠️ **« toutes les informations utiles au déroulé » est la formule la plus large de tout le questionnaire** : à borner **avec le commanditaire avant de coder**, sinon l'US n'a pas de fin.
- **Dépend de** : E14US001 (frise), E16US012 (jalons), E05US034 (pauses visibles) · **Jalon** : J3 · **Origine** : questionnaire A02, 04/08/2026 — sortie d'`E16US011` le 10/09/2026

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

### E16US013 — Le lancement d'un tour : automatique ou manuel, au choix

*En tant qu'*organisateur, *je veux* choisir **par phase ou par tour** si le lancement part **tout seul** quand les conditions sont remplies ou s'il attend mon geste, *afin de* ne pas rester la main sur le bouton toute la journée sur les formats qui n'en ont pas besoin.

- **Contexte** : sortie d'`E16US008` au cadrage du 28/08/2026 — sa fiche annonçait déjà « un vrai changement de moteur, à cadrer séparément ». Questionnaire A15, question 3 : *« un admin, mais suivant la configuration on doit choisir ce qui attend un déclenchement manuel (les phases ou le tour) : selon la configuration, soit ça se déclenche automatiquement quand les conditions sont remplies, soit c'est un déclenchement manuel. »*
- **CA — le mode est un réglage** : chaque phase (et, dans une phase, chaque tour) se règle en lancement **automatique** ou **manuel**. Le réglage est **persisté** et se lit à l'atelier, comme les autres réglages d'étape.
- **CA — l'automatique lance ce qui est prêt** : quand toutes les conditions d'un duel sont remplies, il part **sans clic**, et les postes et écrans sont prévenus exactement comme au lancement manuel (même trace d'audit, même diffusion).
- **CA — le manuel ne change pas** : le feu vert garde son bouton chiffré et sa confirmation (`E12US002`, ADR-0056).
- **Notes** : ⚠️ **Trois questions à trancher avant d'implémenter, aucune n'est dans le questionnaire.** (1) **Qui évalue les conditions ?** Aujourd'hui le feu vert est calculé **à la lecture**, par le poll de l'écran (5 s) : personne ne l'évalue côté serveur quand aucun organisateur ne regarde. Un lancement automatique demande un déclencheur serveur — au fil des validations de duel (le flux qui fait bouger le tableau), ou une boucle. C'est le vrai coût de l'US. (2) **Que fait l'automatique d'un duel bloqué par une cible manquante ?** Il ne peut pas l'inventer : le mode ne supprime pas les manquements, il supprime le clic. (3) **La maille « par tour » existe-t-elle ?** Un réglage par phase est immédiat (`Reglage*` d'étape) ; « par tour » n'a aucun support persistant aujourd'hui. Candidate à un **ADR** (le lancement cesse d'être un geste pour devenir une politique).
- **⛔ Cadrée puis REPOSÉE le 05/09/2026** (arbitrage du commanditaire). Le cadrage a établi trois
  faits, tous vérifiés dans le code, qui rendaient l'US sans valeur en l'état :
  1. **Le feu vert n'existe que pour les phases à tableau.** `ServicePilotageTour.feu_vert` refuse
     tout le reste (`PhasePasUnTableau`) : ni poules, ni système suisse, ni colline, ni Big Shoot
     Off, ni qualification n'ont de bouton « lancer ». Or c'est **pour eux** que la fiche voulait
     l'automatique (« les formats qui n'en ont pas besoin ») : il ne s'agirait pas d'automatiser un
     geste, mais d'**inventer le geste** d'abord.
  2. **« Lancer » n'autorise rien** ([ADR-0056](../docs/adr/0056-lancement-d-un-tour-acte-audite-et-diffuse.md) §3) :
     l'acte consigne une trace `LANCEMENT` et émet un `LiveEvent`, sans poser aucun statut. Un
     scoreur peut saisir un duel jamais lancé. Le bouton **prévient**, il ne déverrouille pas.
  3. **Aucun duel n'était prêt au-delà du tour 1**, faute de cibles posées. L'automatique n'aurait
     donc émis **qu'une annonce par tableau**, au tour 1, où tout devient prêt d'un coup — pas
     « ne plus rester la main sur le bouton toute la journée ».
  ✅ **Arbitrage** : lever le verrou d'abord. C'est `E03US012` (poser les cibles des tours suivants,
  [ADR-0106](../docs/adr/0106-la-pose-d-une-cible-appartient-a-un-tour.md)), **livrée**.
  ⚠️ **Question à trancher AVANT de reprendre cette fiche**, et absente de la rédaction d'origine :
  [ADR-0091](../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §5 affirme
  déjà que « le pilotage tour par tour reste possible **sans second mode** : il suffit de programmer
  un arrêt à chaque tour ». Les deux leviers ne font pourtant pas la même chose — l'arrêt **gèle la
  saisie**, le lancement ne gèle rien. Reprendre l'US suppose de dire lequel des deux le
  commanditaire veut, sous peine de livrer un doublon de l'arrêt programmé.
  ⚠️ **Le cadrage retenu au 05/09/2026** (à reconfirmer, il a plus de valeur que la fiche d'origine) :
  « automatique » = **l'annonce part seule** (trace + diffusion aux postes et écrans), jamais un
  verrou ; et la maille est la **phase**, pas le tour.
- **Dépend de** : E12US002, E16US008, **E03US012** · **Jalon** : J3 · **Origine** : questionnaire A15 Q3, 04/08/2026 — sortie d'`E16US008` le 28/08/2026

---

## Retours **écartés** (traités, sans US)

Consignés ici pour qu'aucun questionnaire ne reste sans réponse.

- **A04 — « la frise du cycle de vie n'est peut-être pas utile tout le temps »** : non appliqué. La
  frise **porte les boutons d'action** (démarrer, terminer) ; la replier ou la borner par axe
  risquerait de masquer l'action principale du jour J. Le mot « peut-être » du questionnaire marque
  d'ailleurs une hésitation, pas une demande. À rouvrir si la gêne se confirme à l'usage.
- **A09 (2ᵉ règle) — « placement manuel obligatoire, mais seulement si possible »** *(traité le
  10/09/2026, au découpage d'`E16US011`)* : **tenu**, et voici par quoi — **rien ne place un
  retardataire tout seul**. Une inscription tardive vaut réserve
  ([ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md)), et « Placer les restants »
  (`placer_les_restants`) est un **geste de l'organisateur**, pas un automatisme. ⚠️ **Ne pas
  invoquer ce bouton comme preuve** : la question était **binaire** (*« proposition automatique, ou
  placement manuel obligatoire ? »*) et il *est* la branche automatique, celle qui a été refusée —
  en déduire qu'un auto-placement à l'inscription honorerait A09 le **violerait**. Rouvrir si
  l'organisateur veut un **blocage explicite** plutôt qu'une simple absence d'automatisme.
  *(Inscrit ici parce que la 1ʳᵉ rédaction le classait « caduc » dans une fiche close ⛔ : un CA
  rangé là n'est jamais relu — c'est le mécanisme même qui a fait naître `E16US011`.)*
- **A03, A13, A19, S03, S04, S07** : validés ✅, et leurs réponses aux questions ciblées ne
  demandent rien qui ne soit déjà livré. ⚠️ **S06, S08 et S09 ont été retirés de cette liste** le
  05/08/2026 : leur verdict ✅ portait sur l'écran, mais leurs réponses portaient des règles — elles
  sont passées en `E16US011` — **puis, le 10/09/2026, dans les US filles de son découpage** :
  S06 → `E16US018`, S08 → `E16US019`, S09 → `E16US020`.
- ⚠️ **P05 Q2 — « les horaires prévisionnels » : question à REPOSER en priorité**, le CA reste **dû**
  *(statut fixé le 10/09/2026 en revue d'`E16US011` — la 1ʳᵉ rédaction l'écartait à tort)*. Réponse
  brute : *« seulement pour les **depart** des differentes phases du tournoi, les autres sont trop
  imprevisible »*. **Deux lectures, et la réponse ne tranche pas** : **(a)** un horaire prévisionnel
  **par phase**, qui n'existe pas dans le domaine — c'est une **création** ; **(b)** l'heure des
  **départs**, terme du domaine ([ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md))
  dont `Depart.horaire` est déjà **obligatoire** — c'est un **bornage** d'existant, front seul.
  ⚠️ **Ne pas refermer ce CA en citant le commentaire de `VueTableaux.tsx`** : l'« arbitrage du
  04/08/2026 » qu'il invoque n'existe **ni en ADR, ni en story, ni au journal**, et cette date est
  celle **du questionnaire**. Fermer un CA en citant le code qui aurait dû l'implémenter est la
  boucle que la règle 9 interdit.
- **Questions restées sans réponse au questionnaire**, à reposer si le sujet revient : A02 Q3
  (« espace » / « étape » / « Résultats »), Q4 (le mot pour un niveau qui boucle) et Q5 (référence ou
  copie des briques à l'assemblage) ; A03 Q1-Q2 ; A05 Q1-Q2 ; A06 Q1-Q2 ; A07 Q1 ; A08 Q2 (comment
  un scoreur reçoit son accès) ; A13 Q1-Q3 ; A15 Q4 (lancement duel par duel) et Q6 (ce qu'il faut
  voir avant d'appuyer) ; A19 Q1-Q2 ; P04 Q1-Q2 ; S03 Q1-Q3 ; S04 Q1-Q2 ; S07 Q1-Q2. Aucune n'est
  bloquante aujourd'hui. **A02 Q5 mérite d'être reposée en priorité** : « si tu changes un tarif en
  2027, le tournoi 2026 archivé doit-il bouger ? » décide du modèle de l'assemblage.
