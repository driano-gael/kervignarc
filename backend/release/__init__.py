"""Outillage du binaire de release auto-contenu (E11US001).

Regroupe ce qui est **spécifique au déploiement du jour J** — un exécutable PyInstaller lancé sur
le réseau local, sans internet : `chemins` résout les chemins conscients du gel PyInstaller,
`reseau` donne l'adresse LAN et annonce `kervignarc.local`. Le point d'entrée est `run.py`, pendant
« release » de `run_dev.py`. Rien ici n'est importé par le domaine (règle 1) : c'est de
l'infrastructure d'exploitation.
"""
