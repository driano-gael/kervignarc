# Le journal d'audit se consulte — et tout sort au tableur

*18 septembre 2026 — `E16US016`, dernière US d'`EPIC-16`.*

## Ce qui est nouveau

**Un écran pour le journal d'audit.** Chaque validation, chaque correction de score, chaque forfait
était enregistré depuis des mois — qui, quand, et l'ancienne valeur. Mais rien, dans l'application,
ne permettait de le **regarder**. En cas de contestation, la trace existait et restait hors
d'atteinte.

Elle a désormais son écran, dans l'axe **Gestion** : le tableau des actes **du plus récent au
plus ancien** — on vient y chercher ce qui vient de se passer —, un compteur des corrections à part, une recherche qui ignore majuscules et accents, un
filtre par type d'acte, et le détail « avant → après » qui se déplie sur la ligne. Réservé à
l'administrateur : une pièce de litige ne s'ouvre pas au public.

**Le format Excel.** Vous l'aviez demandé en relisant la planche A18 (« CSV, EXCEL, PDF… ») ; il
avait été repoussé faute de librairie. Il est là, partout où il a du sens. La différence avec le CSV
n'est pas cosmétique : dans un classeur Excel, un montant est un **vrai nombre**. Sélectionnez la
colonne « Dû » de la liste club & paiement, votre tableur vous en donne la somme. Dans un CSV, c'est
du texte, et la somme ne se fait pas.

**Le palmarès rejoint les exports.** Il ne sortait qu'en PDF, l'affiche du mur. Il s'exporte
désormais aussi au tableur, avec le rang scratch, le rang de catégorie et le rang de club en
colonnes — de quoi le reprendre pour le site du club ou la presse.

## Ce que ça change pour vous

- L'écran « Exports & impressions » compte **cinq** documents au lieu de trois, chacun avec **ses**
  formats — la feuille de marque reste en PDF seul (elle se remplit au stylo), et le journal d'audit
  n'a **pas** de PDF : mille lignes ne s'impriment pas, elles se dépouillent.
- Un archer conteste un score : trois clics suffisent pour retrouver qui l'a modifié, quand, et la
  valeur d'avant.

## Deux points à connaître

⚠️ **L'adresse du palmarès en PDF a changé.** Le bouton « Exporter en PDF » est au même endroit et
fait la même chose ; mais si vous aviez mis l'adresse en favori, elle ne répond plus. Le changement
a été fait franchement, sans garder les deux adresses en parallèle, parce que nous sommes **avant le
premier tournoi réel** et qu'aucune adresse n'a été diffusée.

⚠️ **Ces écrans n'ont pas été ouverts dans un navigateur.** Ils sont couverts par des tests
automatiques, mais l'outil qui permettrait de les regarder n'est pas disponible sur le poste de
développement. La mise en page et le rendu des fichiers Excel dans **votre** tableur demandent une
relecture de votre part.

## Où on en est

`EPIC-16` — les retours de votre relecture des 36 maquettes — est **soldé**.
