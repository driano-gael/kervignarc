# ADR-0119 — La restauration d'une sauvegarde est une écriture de la file, à chaud, qui oublie l'état volatil

- **Statut** : Accepté
- **Date** : 2026-10-03
- **US** : E11US006
- **Décideurs** : Organisateur / Architecte
- **Précise** : [ADR-0044](0044-sauvegarde-lecture-concurrente-et-tache-periodique.md) § Conséquences,
  qui rangeait la restauration parmi les « maintenances en **lecture** » hors file. Elle n'en est pas
  une : seule sa vérification l'est.

## Contexte

E11US003 dépose des copies horodatées de la base pendant que le serveur tourne. Jusqu'ici, s'en
servir passait par une procédure manuelle (`docs/deploiement.md` §5) : fermer l'application,
remplacer `kervignarc.db`, relancer. Le cadrage d'E11US006 (03/10/2026) a retenu, avec le
commanditaire, une restauration **depuis l'écran admin et à chaud**, sans redémarrage.

Trois contraintes du projet pèsent sur le « comment » :

- **règle 7** — toute écriture passe par la file du writer unique ; une restauration écrit la base
  entière ;
- **le pool SQLAlchemy est câblé une fois** dans la composition root, et une quarantaine de
  repositories tiennent sa fabrique de sessions : rien ne permet de leur substituer un nouvel engine ;
- **cinq registres en mémoire** sont indexés par des identifiants de la base (sessions de poste et de
  scoreur, consignes d'écran, présence des postes, idempotence de la saisie). La base restaurée peut
  avoir réattribué ces identifiants à d'autres lignes.

## Décision

1. **La restauration copie la sauvegarde *dans* la base vive par l'API `backup` de SQLite**, au lieu
   de remplacer le fichier. Les connexions déjà ouvertes du pool voient le nouveau contenu à leur
   transaction suivante : ni engine à rouvrir, ni fichier à écraser sous des descripteurs ouverts.
2. **C'est une commande de la file d'écriture**, comme toute autre écriture. La vérification, la copie
   de sécurité et la copie s'enchaînent dans la même commande : aucune écriture ne s'intercale entre
   le contrôle et le remplacement. La règle 7 est tenue **sans exception** à ADR-0044.
3. **La vérification est une lecture hors file** (le précédent d'ADR-0044) : la sauvegarde s'ouvre en
   `mode=ro&immutable=1`, puis `PRAGMA integrity_check` et lecture de `alembic_version`. Elle est
   **refaite** dans la commande de restauration : un verdict affiché à l'écran n'est pas cru sur
   parole.
4. **Une sauvegarde n'est restaurable qu'au schéma de la base en service** — même révision Alembic.
   Une sauvegarde plus ancienne n'est **pas** migrée à la volée : elle est refusée et se restaure par
   la procédure manuelle, où la migration du démarrage la met à niveau.
5. **L'état courant est copié avant**, en `avant-restauration-AAAAMMJJ-HHMMSS.db`, sous un préfixe
   distinct de `kervignarc-*.db` pour rester **hors rétention**. Il est listé avec les autres
   sauvegardes : une restauration s'annule en restaurant cette copie. Aucune copie n'en écrase une
   autre (suffixe `-n` dans la même seconde).
6. **Après la copie, les cinq registres en mémoire sont vidés** : les tablettes et les scoreurs se
   rattachent, comme après un redémarrage. La session admin, adossée au `.env`, survit.
7. **Seul un nom présent dans la liste** se vérifie ou se restaure ; aucun chemin n'est construit à
   partir de la requête.

Le volet « arrêt propre » de l'US s'y rattache : la file draine déjà à l'arrêt du `lifespan`
(E00US007), mais la croix de la console Windows tuait le processus sans passer par lui. Un
gestionnaire `SetConsoleCtrlHandler` (ctypes, stdlib) demande l'arrêt à uvicorn et attend sa fin dans
les ~5 s que Windows accorde ; l'attente des connexions est bornée (`timeout_graceful_shutdown`) pour
que le drain tienne dans ce délai.

## Alternatives écartées

- **Remplacer le fichier puis rouvrir l'engine** : demande de drainer la file, de fermer le pool,
  puis de reconstruire un `Database` que quarante repositories tiennent déjà. Écriture hors file, et
  fenêtre où une lecture concurrente rouvre l'ancien fichier.
- **Restaurer au démarrage seulement** (option de lancement) : plus simple et couvre la base
  illisible, mais impose un redémarrage le jour J. Écartée au cadrage par le commanditaire ; la
  procédure manuelle reste le recours pour une base que le serveur ne peut plus ouvrir.
- **Migrer une sauvegarde ancienne avant de la restaurer** : Alembic sur le thread du writer, soit un
  traitement long qui bloque toutes les écritures de la salle (checklist, règle 7), pour un cas — une
  sauvegarde antérieure à une mise à jour de l'application — qui ne se présente pas pendant un
  tournoi.

## Conséquences

- La restauration rend **toute** la base : tous les tournois reviennent en arrière, pas un seul.
  L'écran le dit, et vit hors tournoi (axe Atelier).
- Un registre en mémoire **ajouté plus tard**, et indexé par un identifiant de la base, doit être
  vidé au même endroit. Rien ne le détecte : c'est l'avertissement porté par la composition root.
- Une simulation en cours (registre de sessions de simulation) n'est pas touchée : elle joue sur un
  harnais en mémoire, indépendant de la base.
- ⚠️ La fermeture par la croix n'est éprouvée que par un test de la **décision**
  (`traiter_evenement`) ; l'appel réel à l'API Windows n'a pas pu être rejoué en environnement
  automatisé. Sa vérification est manuelle (`docs/fonctionnel/E11US006.md`).
- Les copies `avant-restauration-*` s'accumulent hors rétention, une par restauration : volume
  négligeable à l'échelle d'un tournoi, à purger à la main si besoin.

## Porté dans le code par

- `backend/application/sauvegardes.py` — `ServiceSauvegardes` : liste, verdict (§3, §4), séquence de
  restauration et ordre des gestes (§5, §6), garde du nom listé (§7).
- `backend/infrastructure/backup/restauration.py` — `MagasinSauvegardesSQLite` : ouverture en
  lecture immuable, `integrity_check`, copie de sécurité hors rétention, `backup` vers la base vive
  (§1, §3, §5).
- `backend/api/v1/sauvegardes.py` — la restauration soumise à la file d'écriture (§2).
- `backend/bootstrap/composition.py` — `_oublier_etat_volatil`, qui vide les cinq registres (§6).
- `backend/release/arret_console.py` et `backend/run.py` — l'arrêt propre par la croix de la console.
