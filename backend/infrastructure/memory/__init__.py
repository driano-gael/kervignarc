"""Adapters **in-memory** des ports du domaine (E15US002, ADR-0054).

Magasins `dict` implémentant les ports de `domain/ports.py`, pour rejouer le moteur (qualif → duels
→ classement) **sans rien persister** : la simulation de démo/QA câble les services applicatifs
sur ces adapters au lieu des adapters SQL. Aucun chemin vers SQLite ni vers la file d'écriture — la
non-persistance est **structurelle** (ADR-0054).
"""
