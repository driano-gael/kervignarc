"""Outillage du binaire de release auto-contenu (E11US001).

Regroupe ce qui est **spécifique au déploiement du jour J** — un exécutable PyInstaller
lancé sur le réseau local, sans internet :

- `chemins` : résolution des chemins conscients du gel PyInstaller (ressources embarquées
  vs base persistante à côté de l'exécutable) ;
- `reseau` : adresse LAN de la machine et annonce mDNS `kervignarc.local`.

Le point d'entrée est `run.py` (racine `backend/`), pendant « release » de `run_dev.py`.
Rien ici n'est importé par le domaine (règle 1) : c'est de l'infrastructure d'exploitation.
"""
