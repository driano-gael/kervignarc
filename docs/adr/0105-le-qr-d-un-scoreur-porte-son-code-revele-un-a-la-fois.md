# ADR-0105 — Le QR d'un scoreur porte son code, révélé un à la fois

- **Statut** : Accepté
- **Date** : 2026-09-04
- **US** : E16US015
- **Décideurs** : Organisateur / Architecte
- **Amende** : [ADR-0025](0025-mode-d-identite-scoreur-par-code-individuel.md) § Décision 2 (canal de
  distribution du code)
- **Liés** : [ADR-0059](0059-routage-par-role-dans-l-url-routeur-maison.md) (routeur maison),
  [ADR-0042](0042-modele-d-entree-choix-de-role-explicite.md) (précédence d'entrée),
  [ADR-0031](0031-bibliotheque-pdf-reportlab.md) (rendu ReportLab)

## Contexte

*Origine : questionnaire de maquettes A08 (04/08/2026) ; les points 2 et 3 de la décision
viennent de la revue d'US du 04/09/2026.*

ADR-0025 § Décision 2 définit le code d'un scoreur comme *« un **secret d'usage** distribué sur
papier et **retapé** par le scoreur »*. C'est cette phrase qui justifie tout le reste du design :
alphabet sans caractères confondables, 6 caractères, distribution par un PDF de cartes à découper.

E16US015 ajoute un **QR par scoreur**, affiché à l'écran de l'admin. Le canal de distribution du
secret change donc — il n'est plus seulement *retapé*, il devient *scannable*. Laisser ADR-0025
inchangé aurait reproduit le défaut d'[ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md) : une
décision écrite quelque part, contredite en silence par le code, et personne pour s'en apercevoir
avant des mois.

Un fait cadre l'arbitrage et doit être posé avant tout : **le code est déjà en clair partout**. En
base (`domain/scoreur.py` — aucun hachage), dans la réponse admin `GET /tournois/{id}/scoreurs`,
sur le PDF `cartes-codes`, et affiché en clair dans la liste de l'écran d'administration. Le QR
**n'ajoute aucune divulgation** ; il change la **facilité de capture**. Un code à six caractères se
lit par-dessus une épaule en s'approchant ; un QR se photographie **d'un mètre et sans être vu**.

Ce que le code protège n'est pas non plus un accès quelconque : c'est **la traçabilité des
validations** (E10US005 — qui a validé quoi). C'est ce qui distingue ce code de celui d'une cible,
lequel rattache un appareil à un lieu et n'a rien de personnel.

## Décision

**1. Le QR porte le code personnel en clair.** L'URL encodée contient le code tel quel. Cohérent
avec le fait que quatre autres surfaces le portent déjà en clair ; l'alternative « jeton » est
écartée ci-dessous.

**2. La révélation est le geste de sécurité, pas le contenu.** L'écran d'administration **ne charge
aucun QR à son montage** : un bouton « Afficher le QR » par ligne, et **un seul ouvert à la fois**.
Ouvrir la rubrique « Scoreurs » ne met donc jamais tous les codes du tournoi sous une forme
scannable d'un seul cliché.

⚠️ **La garde est le montage conditionnel du composant, pas un drapeau `enabled`.** Une première
implémentation passait un `enabled` à React Query qu'aucun appelant ne mettait jamais à `false` :
un garde-fou nommé au mauvais endroit se fait contourner par le lecteur suivant, qui le croit actif.
⚠️ **L'état d'ouverture est indexé sur le `code`, jamais sur l'`id`** : SQLite réattribue les `id`
(clé primaire sans `AUTOINCREMENT`), si bien qu'un scoreur supprimé puis remplacé rouvrirait le QR
de son successeur **sans clic**. La suppression purge en outre le cache du QR révoqué.

**3. L'URL nomme le monde dans le chemin et porte le code dans le FRAGMENT** :
`{origine}/scoreur#code=<code>`.

- Le **chemin** (`/scoreur`) plutôt que la racine : le routeur d'adresses (ADR-0059) aiguille alors
  seul, sans qu'on ajoute une cinquième règle de précédence à `resoudreRole` (ADR-0042), que son
  propre en-tête nomme « le cœur risqué de l'aiguillage d'entrée ». Repli utile : un code refusé
  atterrit sur l'écran de connexion scoreur — le bon endroit — et non sur l'écran de choix.
- Le **fragment** plutôt que la query : un fragment n'est **jamais envoyé au serveur**. Un `?code=`
  aurait été écrit dans le journal d'accès d'uvicorn à chaque scan, puis dans l'en-tête `Referer`
  de chaque sous-ressource. Le code est retiré de l'adresse dès l'arrivée, **au shell** — donc y
  compris quand le verrou de poste (`D-13`) détourne l'appareil vers l'écran de cible.

⚠️ Cette forme **diffère volontairement** de celle du QR de cible (`{origine}/?poste=<code>`), qui
précède E14US003 : à l'époque l'adresse n'était pas encore une source d'entrée. Les QR de cible déjà
imprimés restent valides, aucune migration n'est due.

## Alternatives écartées

**Un jeton à usage unique ou expirant**, échangé contre une session, le code personnel ne circulant
jamais dans une URL. C'est la seule option strictement plus sûre. Écartée parce qu'**aucun mécanisme
de ce genre n'existe dans le produit** : ni la session scoreur ni le rattachement de poste n'expirent
(`infrastructure/scoreurs/sessions.py` le dit explicitement), et il aurait fallu créer génération,
persistance, expiration et révocation. Le gain est réel, le coût transforme une petite US en
chantier — et le modèle de menace (mono-club, réseau local, écran d'admin tenu par l'organisateur)
ne le justifie pas. À rouvrir si le produit sort du cadre mono-club.

**La forme racine `{origine}/?scoreur=<code>`**, jumelle littérale du QR de cible. Écartée : elle
impose une cinquième règle de précédence dans `resoudreRole`, pour aucun gain fonctionnel.

**Le QR uniquement dans le PDF des cartes**, remis en main propre. Écartée par le commanditaire :
le geste visé est justement d'éviter l'impression le matin du tournoi.

## Conséquences

- **+** Un scoreur ouvre sa session sans recopier son code : plus de faute de frappe, plus
  d'aller-retour vers l'organisateur au moment où tout le monde arrive.
- **+** Aucune dépendance ajoutée (règle 11) : ReportLab rend déjà le SVG, et le port
  `GenerateurDocumentsSalle.qr_rattachement(url)` reçoit une URL déjà composée — il a été réutilisé
  tel quel plutôt que doublé.
- **+** Le code ne transite jamais par le serveur (fragment), ni ne survit dans l'historique du
  téléphone.
- **−** **Un QR photographié n'est pas révocable.** Il n'existe aucune rotation de code : la seule
  parade est de supprimer le scoreur et de le recréer, ce qui coupe sa session en cours. Écarté du
  périmètre par le commanditaire au cadrage du 04/09/2026 ; à reprendre en US dédiée si le besoin
  se confirme.
- **−** La route hérite de `DETTE-012` en **3ᵉ site** : l'URL est bâtie sur l'origine de la requête
  admin. Générer depuis `localhost` produit un QR porteur du code mais inutilisable.
- **−** Le code reste **en clair en base** : ce point n'est pas tranché ici, il préexiste
  (ADR-0025) et cet ADR ne le change pas.

## Porté dans le code par

*(Vérifié dans le code du 04/09/2026, pas déduit de la décision — cf. `CLAUDE.md` § Workflow.)*

| Module | Ce qu'il porte |
|---|---|
| `backend/application/documents_salle.py` — `ServiceDocumentsSalle.qr_scoreur` | Décision 1 : compose l'URL et la confie au port ; garde d'appartenance au tournoi (`par_id` n'est pas borné au tournoi) |
| `backend/application/documents_salle.py` — `_url_scoreur` | Décision 3 : chemin `/scoreur`, code dans le fragment, échappement `quote` |
| `backend/api/v1/documents_salle.py` — `qr_scoreur` | Frontière : SVG, `Depends(exiger_admin)` |
| `frontend/src/features/scoreurs/Scoreurs.tsx` — état `qrOuvert` | Décision 2 : révélation une par une, indexée sur le **code** ; c'est **ici**, et nulle part ailleurs, que vit la garde |
| `frontend/src/features/scoreurs/hooks.ts` — `useSupprimerScoreur` | Décision 2 : purge du cache du QR révoqué |
| `frontend/src/features/scoreur-session/url.ts` | Décision 3 : lecture et effacement ciblé du fragment |
| `frontend/src/app/App.tsx` | Décision 3 : l'effacement au **shell**, seul niveau traversé par tous les mondes |

**Épinglé par** : `frontend/src/features/scoreurs/Scoreurs.test.tsx` (aucun QR chargé au montage, un
seul ouvert, id réattribué), `frontend/src/app/App.entree.test.tsx` (effacement malgré le verrou de
poste), `backend/tests/test_service_documents_salle.py` (forme d'URL, échappement, garde de tournoi).
