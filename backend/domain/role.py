"""Les **rôles** du dépôt, et leur ordre — le premier du projet (ADR-0107).

`docs/glossaire.md` § « Rôles » nomme les identités ; cet ordre dit laquelle **prime** quand deux
écritures se croisent sur la même donnée.
"""

from __future__ import annotations

from enum import IntEnum


class Role(IntEnum):
    """Qui écrit, par ordre croissant d'autorité : poste de cible < scoreur < admin (ADR-0107 §1).

    ⚠️ **Le rang le plus bas n'est pas une personne mais un LIEU** : le poste de cible est
    identifié par son jeton de cible, sans authentifier quiconque (ADR-0030, `D-13`). C'est
    précisément ce qui rend un ordre nécessaire plutôt qu'une simple comparaison d'utilisateurs.
    """

    # ⚠️ **`name` est PERSISTÉ** (`volee.role_de_saisie`, migration `0055`) : renommer un membre
    # ci-dessous **exige une migration de données**. Sans elle, `_vers_role` dégrade les lignes
    # existantes vers « aucune préséance », en silence — le refus cesse de tomber et rien ne le dit.
    POSTE_DE_CIBLE = 1
    SCOREUR = 2
    ADMIN = 3
