# EPIC-16 — Retours du questionnaire de maquettes — User Stories

> Issu des **36 questionnaires de maquettes remplis le 04/08/2026**. Voir
> [`epics/EPIC-16`](../epics/EPIC-16-retours-maquettes.md).
>
> **Le lot « front seul » a été livré hors US** le 04/08/2026 (branche
> `feat/retours-maquettes-front`) : tout ce qui ne demandait ni décision métier ni changement de
> domaine ou d'API. Les US ci-dessous sont **le reste** — ce qui exige un arbitrage, du backend, ou
> plus qu'une passe de mise en forme.
>
> ⚠️ **Chaque US cite la phrase du questionnaire dont elle dérive.** C'est la source du CA (règle 9) :
> ne pas la remplacer par une reformulation au moment de coder — c'est elle qui dit ce qui est
> demandé, et elle est parfois plus étroite ou plus large qu'elle n'en a l'air.

---

### E16US001 — Plan de salle : se mettre d'accord sur ce qu'est un pas de tir
*En tant qu'*organisateur, *je veux* que l'écran de plan de salle parle **de la salle que je connais**, *afin de* pouvoir le valider au lieu de deviner ce qu'il représente.
- **Contexte** : A10 est refusé (🔴) sur un **malentendu de vocabulaire**, pas sur un défaut d'écran. Le commanditaire écrit : *« je ne comprends pas l'usage. Pour moi un pas de tir, c'est le couloir de tir d'un archer et, suivant le nombre de blasons et le nombre d'archers que je positionne sur la cible, exemple 4 archers 2 blasons → A, B, C, D. Explique-moi ce que toi tu vois avant de valider l'écran. »*
- **CA — l'explication d'abord** : avant toute ligne de code, produire une note courte qui met face à face les deux lectures du mot (le **couloir d'un archer** vs la **rangée de cibles**), avec le vocabulaire de [`docs/glossaire.md`](../docs/glossaire.md) et un schéma de la salle réelle. La faire arbitrer.
- **CA — l'écran ensuite** : le gabarit de salle nomme ce qu'il dessine avec le mot retenu, et rend visible le lien **cible → blasons → positions A/B/C/D** que le commanditaire décrit.
- **CA — questions restées sans réponse, à reposer** : *« ta salle a-t-elle une disposition particulière (deux pas de tir, cibles décalées, piliers) ? »* et *« le gabarit doit-il porter autre chose que les cibles : table d'organisation, zone d'échauffement, entrée du public ? »* — les deux conditionnent le modèle.
- **Notes** : ⚠️ **US bloquante par nature** — elle commence par une question, pas par du code. C'est le cas prévu par la règle « CA ambigu ⇒ questionner avant d'implémenter ». Toucher `docs/glossaire.md` si le mot change. US à **surface visible** → doc fonctionnelle + journal.
- **Dépend de** : E03 (gabarits, plan de salle) · **Jalon** : J2 · **Origine** : questionnaire A10, 04/08/2026

---

### E16US002 — Phases : une bibliothèque de phases réglables, pas une séquence figée
*En tant qu'*organisateur, *je veux* **lister mes phases, en ajouter depuis un gabarit et ouvrir la fiche de réglages de chacune**, *afin de* pouvoir avoir plusieurs qualifications ou plusieurs tableaux aux réglages différents dans le même tournoi.
- **Contexte** : A07 est refusé (🔴). *« La création/gestion d'une phase est assez compliquée et demande des écrans plus détaillés. Je voudrais une liste des phases dans un écran, avec la possibilité d'en ajouter de nouvelles à partir d'un gabarit de phase. Par exemple je peux avoir plusieurs phases de type qualification, ou duel, qui n'ont pas les mêmes réglages. Sur chaque ligne du tableau on peut ouvrir une fiche de la phase, qui reprend son titre et ses réglages (nb de séries, volées, flèches, sets… suivant le type de phases). »* Et : *« chaque phase reste une brique qui peut servir d'une année sur l'autre, donc il peut y avoir plusieurs phases de même type mais avec des réglages différents. »*
- **CA — liste** : un écran liste les phases du tournoi (titre, type, rang, état), une ligne par phase, avec ajout depuis un **gabarit de phase**.
- **CA — fiche** : ouvrir une ligne ouvre la fiche de la phase — son **titre** et ses **réglages propres au type** (nombre de séries, de volées, de flèches, de sets…).
- **CA — plusieurs phases de même type** : deux qualifications aux réglages différents coexistent dans un même tournoi sans se marcher dessus.
- **CA — réutilisable d'une année sur l'autre** : le **gabarit** est ce qui se réutilise, comme le **format** l'est déjà (ADR-0060 §5). ⚠️ Vérifier au cadrage si « gabarit de phase » et « format » sont deux noms d'une même chose ou deux niveaux distincts — la réponse change tout le modèle.
- **Notes** : touche le **domaine et l'API** — aujourd'hui les réglages de qualification vivent sur le barème du tournoi (`bareme`), pas sur la phase. Relire [ADR-0062](../docs/adr/0062-catalogue-de-types-de-phase.md) (catalogue de onze types) et [ADR-0060](../docs/adr/0060-briques-patrimoine-du-club.md) avant de cadrer. **ADR probable**. **Redécoupable** (liste seule / fiche / gabarits) — probablement trop large pour une branche.
- **Dépend de** : E05US015, E01US023, E01US024 · **Jalon** : J2 · **Origine** : questionnaire A07, 04/08/2026

---

### E16US003 — Complétude : ne plus mélanger le déroulé et la gestion administrative
*En tant qu'*organisateur, *je veux* que la complétude du **déroulé** soit séparée de la complétude **administrative**, *afin de* ne pas voir des paiements quand je pilote un tour.
- **Contexte** : A14 est refusé (🔴). *« Je n'aime pas le mélange entre le déroulé et la gestion administrative. Complétude en déroulé n'est pas complétude administrative : en déroulé on est centré sur l'événement. »*
- **CA — deux écrans, une source** : le serveur rend déjà `sportif` et `hors_sportif` séparément (`GET /tournois/{id}/completude`). Les deux listes se rendent donc sur **deux destinations** — le sportif au **pilotage**, l'administratif à la **gestion** — sans dupliquer le calcul.
- **CA — le bouton « Terminer » suit le sportif** : c'est lui que « terminer » fige (les paiements restent ouverts), il reste donc du côté déroulé.
- **CA — questions restées sans réponse, à reposer** : *« la séparation sportif / hors-sportif correspond-elle à ta façon de clore un tournoi ? »* et *« "Terminer" fige le sportif et laisse les paiements ouverts : est-ce le bon découpage ? »* — le refus porte sur le mélange à l'écran, pas forcément sur le découpage du domaine ; le confirmer avant de déplacer quoi que ce soit.
- **Notes** : front seul **si** le découpage du domaine est confirmé ; c'est un **déplacement d'ossature** (une destination change d'axe), donc à signaler explicitement en revue. US à **surface visible** → doc fonctionnelle + journal.
- **Dépend de** : E12US005, E14US003 · **Jalon** : J3 · **Origine** : questionnaire A14, 04/08/2026

---

### E16US004 — Le public suit **plusieurs** archers, de bout en bout
*En tant que* spectateur ou accompagnateur, *je veux* suivre plusieurs archers et retrouver **leur** classement, **leurs** tableaux et **leur** journée, *afin de* ne pas avoir à chercher chacun à la main.
- **Contexte** : quatre questionnaires disent la même chose sous quatre angles.
  - P01 : *« mettre un filtre de tri par club en plus dans la recherche ; une liste d'archers se met à jour à mesure de la recherche ; dans la ligne d'un archer mettre un état : suivi, à suivre, ne plus suivre »*, et *« il faut pouvoir suivre plusieurs archers »* (mémorisé en `localStorage`, confirmé).
  - P02 : *« à retravailler pour accepter de suivre plusieurs archers »*, *« écran trop personnel, il s'adresse aussi bien au public qu'à un archer »*, *« rendre ça uniforme pour le public comme pour l'archer, écran repliable pour le récapitulatif des informations de la journée, on doit pouvoir retrouver tous les tours de toutes les phases joués »*.
  - P03 (🔴) : *« il me faut les 2 : soit le classement uniquement des archers suivis, soit le classement général »*, *« en direct, dès que les informations sont disponibles, pareil pour les scores en cours »*, et le détail des flèches des autres : *« oui »*.
  - P05 : *« une bascule pour suivre tous les tableaux du tournoi ou uniquement centré sur les archers que l'on choisit de suivre »*.
- **CA — bascule « mes archers / tout »** sur le classement (P03) et sur les tableaux (P05).
- **CA — recherche** : filtre par club, liste qui se met à jour à la frappe, état de suivi actionnable sur chaque ligne.
- **CA — récapitulatif repliable** de la journée, couvrant **tous les tours de toutes les phases** joués.
- **CA — détail des flèches des autres** accessible depuis le classement.
- **Notes** : le multi-archers **existe déjà** au socle (`sessionSuivisStore`, E07US006) — c'est la lecture qui n'en tire pas parti. Front majoritaire ; vérifier si l'API rend le détail des flèches d'un tiers en lecture publique. **Redécoupable** par écran. US à **surface visible** → doc fonctionnelle + journal.
- **Dépend de** : E07US006, E07US005, E06US001 · **Jalon** : J3 · **Origine** : questionnaires P01, P02, P03, P05, 04/08/2026

---

### E16US005 — Placement : la largeur d'un PC, et un puits de réserve
*En tant qu'*organisateur, *je veux* placer les archers **une cible par ligne** sur toute la largeur de l'écran, et pouvoir **sortir un archer du plan sans le placer ailleurs**, *afin de* ne pas être obligé d'inverser deux archers à chaque ajustement.
- **Contexte** : A11 est validé avec réserves. *« Trop tassé, on doit pouvoir mieux s'adapter sur la largeur d'un écran PC »*, *« une cible par ligne me paraît plus adaptée »*, *« je ne vois pas de puits de réserve pour déplacer des archers sans les positionner, ce qui évite de toujours faire une inversion entre 2 archers »*. Travail **sur PC uniquement** (question 1). Le recalcul après ajout d'un retardataire **préserve les placements manuels** (question 2 : *« oui »*). Contraintes : *« toutes les contraintes déjà énoncées, dans la mesure du possible »*.
- **CA — une cible par ligne**, exploitant la largeur disponible (les jetons `--largeur-app` sont posés depuis le lot front du 04/08).
- **CA — puits de réserve** : une zone où déposer un archer retiré du plan, d'où on le replace ensuite. Un archer en réserve n'est **pas** placé — il doit se distinguer d'un archer sans cible.
- **CA — préservation** : un recalcul après ajout ne défait pas les placements manuels.
- **Notes** : vérifier si « en réserve » se représente côté serveur (`cible = null` suffit-il ?) ou seulement à l'écran ; la réponse décide si l'US est front seul. Le glisser-déposer existe (variante A retenue).
- **Dépend de** : E03US011, E05US010 · **Jalon** : J2 · **Origine** : questionnaire A11, 04/08/2026

---

### E16US006 — Patrimoine : distinguer l'officiel FFTA du local, et porter le logo du club
*En tant qu'*organisateur, *je veux* voir d'un coup d'œil ce qui vient de la **FFTA** et ce que **j'ai créé**, *afin de* ne pas modifier par erreur une référence officielle.
- **Contexte** : A06, deux fois la même phrase (critique **et** évolution) : *« une séparation visible des unités officielles FFTA de celles créées par l'administrateur »*. A05 : *« ajouter un champ de plus pour le logo du club qui organise le tournoi, en plus du logo du tournoi ; bien sûr cela reste optionnel »*.
- **CA — origine visible** : catégories, blasons, clubs et barèmes portent une **origine** (officielle / locale), affichée et filtrable.
- **CA — logo du club** : un second logo, **facultatif**, distinct du logo d'événement.
- **CA — question restée sans réponse, à reposer** : *« l'import depuis un fichier (catégories FFTA, liste de clubs) est-il nécessaire ? »* — il conditionne la façon dont l'origine « officielle » est alimentée.
- **Notes** : demande un **champ de données** sur les référentiels et sur l'identité — donc migration Alembic. Rattaché à E01US016 pour le logo. Relire [ADR-0060](../docs/adr/0060-briques-patrimoine-du-club.md) : la notion de bibliothèque existe déjà, l'origine s'y ajoute.
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
- **Dépend de** : E09US001, E09US003, E08, E06US004, E11 (audit) · **Jalon** : J3 · **Origine** : questionnaires A08, A16, A17, A18, 04/08/2026

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
- **Dépend de** : E12US005, E12US006, E02US005 · **Jalon** : J3 · **Origine** : questionnaires A02, A09, 04/08/2026

---

## Retours **écartés** (traités, sans US)

Consignés ici pour qu'aucun questionnaire ne reste sans réponse.

- **A04 — « la frise du cycle de vie n'est peut-être pas utile tout le temps »** : non appliqué. La
  frise **porte les boutons d'action** (démarrer, terminer) ; la replier ou la borner par axe
  risquerait de masquer l'action principale du jour J. Le mot « peut-être » du questionnaire marque
  d'ailleurs une hésitation, pas une demande. À rouvrir si la gêne se confirme à l'usage.
- **A13, A03, A19, S03, S04, S06, S07, S08, S09** : validés ✅ tels quels, aucune évolution demandée.
- **A03 question 1 (« des statuts que tu n'utiliseras jamais ? »), A05 questions 1-2, A06 question 1,
  A13 questions 1-3, A19 questions 1-2, S03 questions 1-3, S04 questions 1-2** : restées **sans
  réponse** au questionnaire. À reposer si le sujet revient — aucune n'est bloquante aujourd'hui.
