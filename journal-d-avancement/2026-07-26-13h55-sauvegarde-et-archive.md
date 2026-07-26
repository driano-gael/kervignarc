# 26/07/2026 — L'application se sauvegarde toute seule et sait s'archiver

**US E11US003 — Sauvegarde & archive.** Deux protections contre le pire (un plantage en pleine
compétition, ou tout perdre après l'événement), l'une invisible et l'autre à portée de clic.

## Ce qui est nouveau

- **Des sauvegardes automatiques, sans y penser.** Tant que l'application tourne, elle dépose **toute
  seule**, à intervalle régulier, une **copie datée** de sa base de données dans un dossier `backups/`
  à côté du programme. Les plus anciennes sont effacées au fur et à mesure (on ne remplit pas le
  disque). Aucun écran, aucun réglage : c'est un filet de sécurité de fond. Si la machine plante, on
  repart de la dernière copie.

- **Un écran « Archive » pour tout emporter.** En fin de tournoi, l'organisateur ouvre **Admin → Jour
  J → Archive** et télécharge un **fichier ZIP** unique. Il **coche ce qu'il veut** dedans (tout est
  coché par défaut) :
  - la **base de données complète** (la copie fidèle, pour tout retrouver plus tard) ;
  - les **données en CSV**, ouvrables dans un tableur (archers, inscriptions, scores, paiements…) ;
  - les **documents PDF** régénérés : feuilles de marque, liste de placement, liste club & paiement.
  Un petit **manifeste** décrit le contenu (date, tournoi, tables). Décocher tout grise le bouton :
  une archive vide n'aurait pas de sens.

## Pour qui, et ce que ça change

Pour l'**organisateur**. Avant, une coupure de courant ou un plantage en cours de journée pouvait
coûter des heures de saisie ; désormais la dernière sauvegarde est à quelques minutes près. Et après
la compétition, tout le tournoi tient dans un fichier qu'on archive ou qu'on transmet, sans dépendre
que l'application soit réinstallée.

Avec ça, le tournoi de qualification se tient **de bout en bout** : configuration, inscriptions,
placement, saisie en direct, classement, consultation publique, impressions — et maintenant la
sauvegarde. La suite, c'est un autre chantier : les **duels** des phases finales.
