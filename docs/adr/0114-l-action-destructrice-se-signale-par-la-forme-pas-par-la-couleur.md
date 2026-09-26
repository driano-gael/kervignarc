# ADR-0114 — L'action destructrice se signale par la forme, pas par la couleur

- **Statut** : Accepté
- **Date** : 2026-09-26
- **US** : E17US006
- **Décideurs** : Organisateur (commanditaire) / Architecte
- **Amende** : [ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)
  — sa conséquence « **un bouton destructif devient ambre** — en contour et en texte » est retirée :
  l'ambre redevient le signal de la **seule** alerte.

## Contexte

La charte mesurée (`cahier-des-charges-design.md` §3.3.2, `DV-03`) joue le signal sur la
**luminance** : l'alerte est ambre (`#FFB000`, 9,22:1), le rouge du club n'est **jamais** un signal
(2,55:1 sur l'anthracite). Elle ne prévoit **rien** pour l'action destructrice.
[ADR-0074](0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) a comblé le
trou par défaut — l'ambre, en contour et en texte — en le nommant « trou constaté, pas un choix ».

Conséquence : « ce poste est hors ligne » et « ce bouton supprime le tournoi » partageaient la **même
teinte**. `E17US001` puis `E17US002` l'ont relevé sans pouvoir le fermer, la palette ne se discutant
pas en US d'écran (`EPIC-17` § Exclus).

Inventaire du 26/09/2026 : `--danger` / `--danger-strong` servent ~90 fois, **toutes** à l'alerte ou
à un état, sauf **trois règles** — le bouton destructeur, le dialogue de confirmation destructeur et
le panneau d'impact d'une action massive.

## Décision

**L'action destructrice ne porte aucune couleur propre, ni aucune couleur d'état.** Elle se signale
par la **forme** et par le dialogue de confirmation
d'[ADR-0072](0072-confirmation-destructrice-dialog-natif.md) :

1. **Bouton destructeur** : **contour épais** (2 px) et texte en **encre neutre** (`--text`), sans
   aplat. C'est la troisième forme du produit, lisible sans la couleur : l'action principale est un
   **aplat** de marque, le bouton discret un **contour fin** (`--border`) en texte secondaire.
2. **Dialogue destructeur** : **filet haut** de 4 px en encre neutre (il était ambre).
3. **Panneau d'impact** (`ConfirmationChiffree`, ADR-0040) : rangé **côté destructeur**, contour
   épais neutre. Il annonce le coût d'une action irréversible : il fait partie de sa confirmation,
   pas de l'alerte. Le laisser ambre aurait reconduit, sur ce seul écran, le partage de signal que
   l'ADR ferme.
4. **L'ambre est réservé à l'alerte.** Aucun jeton n'est ajouté à la charte.

Options écartées, soumises au commanditaire le 26/09/2026 :

- **(a) une troisième teinte** : le rouge est exclu par `DV-03`, l'orange aussi (2,34:1 du rouge) ;
  toute autre teinte entre à la charte du club sans étalon sur les planches — le coût d'une
  décision de palette pour un cas que la forme couvre déjà ;
- **(b) deux niveaux d'ambre** (`--danger` avertit, `--danger-strong` escalade) : `#FFB000` et
  `#FFD400` restent **une même famille de teinte** ; la distinction n'aurait tenu que par la forme,
  c'est-à-dire par (c), avec en prime une couleur qui dit le contraire.

## Conséquences

- ✅ Une action irréversible et un avertissement ne partagent plus leur signal, et aucun des deux
  ne repose sur la couleur seule (`DV-03`).
- ✅ Contraste : l'encre neutre `--text` tient 15,16:1 (sombre) et 15,33:1 (clair) sur
  `--surface-1` — bien au-delà du 3:1 exigé pour un contour actionnable (WCAG 1.4.11).
- ⚠️ **Piège de nommage laissé en place — [`DETTE-115`](../dette.md)** : la classe s'appelle
  toujours `bouton--danger` (38 occurrences, 22 fichiers), et la prop `ton="danger"`, alors qu'elles
  ne portent plus le jeton `--danger`. Le renommage est repoussé tant que des branches en vol
  touchent ces fichiers. Le piège est **gardé mécaniquement** par `charte.test.ts` : aucun jeton
  d'état ni encre `--sur-*` (forme à repli comprise) dans les règles destructrices — enfants
  `.confirmation__*` et zone `.panneau-edition__danger` compris ; aucune autre règle ne retouche le
  contour ou l'encre du bouton et du dialogue ; et **seules** les règles destructrices portent le
  contour épais neutre. ⚠️ Ce que le test **ne couvre pas** : une règle destructrice sous un **autre
  nom** de classe. Il connaît des sélecteurs, pas l'intention.
- Au passage : `--danger` et `--danger-strong` portent désormais leur ratio mesuré dans les **trois**
  déclinaisons (`--danger-strong` clair : 6,78:1, jusqu'ici sans commentaire ; la déclinaison claire de
  « Système » n'en portait aucun).

## Porté dans le code par

- `frontend/src/app/App.css` — `.bouton--danger`, `.dialogue--danger`, `.confirmation` (les trois
  règles de la décision, points 1 à 3).
- `frontend/src/index.css` — commentaire du bloc « États » (point 4) et ratios des jetons d'alerte.
- `frontend/src/shared/ui/DialogueConfirmation.tsx` — pose `bouton--danger` sur « Confirmer » quand
  `ton === 'danger'` et donne le focus à « Annuler » (ADR-0072, inchangé).
- `frontend/src/shared/confirmation/ConfirmationChiffree.tsx` — monte le panneau `.confirmation` et
  son bouton `bouton--danger`.
- `frontend/src/shared/charte.test.ts` — les gardes « l'action destructrice se signale par la
  forme » et « les jetons d'alerte portent leur ratio ».
