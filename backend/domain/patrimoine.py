"""Vocabulaire commun du **patrimoine du club** — les briques réutilisables (E01US023, ADR-0060).

Une **brique** (catégorie, blason, gabarit de salle…) existe sous deux formes, distinguées par son
`tournoi_id` :

- `tournoi_id is None` — c'est un **modèle de bibliothèque**, patrimoine du club. Il vit d'année en
  année et n'appartient à aucune édition ;
- `tournoi_id` renseigné — c'est la **copie** d'un tournoi, ajustable **sans altérer le modèle**.

Ce n'est pas un patron neuf : `gabarit_salle` l'applique depuis E01US007/E01US008 (« appliquer un
modèle (copie), lire et ajuster la copie sans altérer le modèle »). E01US023 le **généralise** aux
catégories et aux blasons, qui portaient jusqu'ici un `tournoi_id` obligatoire — d'où l'atelier qui
promettait « hors tournoi » sans pouvoir le tenir (DETTE-023).

**Pourquoi copier plutôt que référencer** — arbitrage du commanditaire, 30/07/2026. Si un tarif ou
un barème change en 2027, le tournoi 2026 **archivé ne doit pas bouger** : une brique référencée
réécrirait l'histoire, ce que l'archive en lecture seule (EPIC-11) et le journal d'audit
interdisent. Contrepartie assumée : un brouillon ne bénéficie pas d'une correction faite ensuite
dans la bibliothèque.

**Et la remontée** : « si les modifications sont permanentes, on doit pouvoir le dire — cela
modifiera la brique de base de l'atelier ». Une modification locale déclarée **permanente** est
**promue** dans la bibliothèque. Elle ne réécrit pas l'histoire pour autant : les tournois déjà
assemblés gardent leur copie, seuls les **prochains** assemblages héritent de la correction.
"""

from __future__ import annotations

from enum import Enum


class OrigineBrique(str, Enum):
    """D'où vient une brique — ce qui distingue le **référentiel officiel** de la création du club.

    Le commanditaire veut « une liste séparée par officiel FFTA et création utilisateur », et
    pouvoir, en modifiant un officiel, soit « en faire une copie pour garder les deux modèles »,
    soit « l'intégrer au FFTA officiel (le règlement peut évoluer) ».

    ⚠️ **Cette marque ne suffit pas à dire « conforme FFTA ».** Elle dit d'où vient la brique, pas
    si elle a été modifiée depuis, ni contre **quelle version** du règlement elle a été établie. Le
    référentiel versionné et le contrôle de conformité relèvent du lot suivant ; tant qu'ils
    n'existent pas, `FFTA` signifie « issue du préchargement officiel », rien de plus.
    """

    FFTA = "ffta"
    UTILISATEUR = "utilisateur"
