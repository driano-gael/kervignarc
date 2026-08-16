"""Générateur de l'atlas — cartographie navigable du dépôt (E00US018, ADR-0086).

Lit les sources versionnées (`CLAUDE.md`, `docs/adr/`) et émet les données que le site statique
`atlas/` consomme. Stdlib pure : le générateur ne doit **jamais** acquérir de dépendance (règle 11),
c'est ce que prouve son job de CI, qui tourne sans `pip install`.
"""
