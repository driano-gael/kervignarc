"""La carte du code : ce que les imports disent de l'architecture annoncée.

Ce module ne juge pas — il rapproche, comme `avancement.py` le fait des livrables de suivi, et
laisse `controles.verifier_code` dire là où le rapprochement échoue. Il calcule en revanche **tous**
les verdicts affichés (`autorise`, `hors_domaine`, `sans_adapter`) : les recalculer en JavaScript
en ferait une seconde écriture de la règle 2, sur la page dont le sujet est précisément que le code
et la règle ne doivent pas diverger. Le site affiche, il ne décide pas.
"""

from __future__ import annotations

from typing import Any

from atlas.modele import AreteCode, AreteFeature, NoeudEnchevetre, Port
from atlas.sources.code import (
    COUCHES,
    SENS_AUTORISE,
    autorise,
    est_hors_domaine,
    est_sans_adapter,
)


def violations(aretes: tuple[AreteCode, ...]) -> tuple[AreteCode, ...]:
    """Les arêtes qui remontent le sens des dépendances. Vide aujourd'hui — c'est l'objectif."""
    return tuple(arete for arete in aretes if not autorise(arete.couche_source, arete.couche_cible))


def _adapter(qualifie: str) -> dict[str, str]:
    """`infrastructure/db/serie.py::SerieRepositorySQL` → de quoi l'afficher sans le découper en JS.

    Le découpage se fait **ici** et pas côté site : une convention de chaîne interprétée par un
    fichier que ni mypy ni le linter ne regardent (`DETTE-067`) est un contrat que rien ne tient.
    """
    fichier, _, nom = qualifie.partition("::")
    return {"fichier": fichier, "nom": nom}


def construire(
    aretes: tuple[AreteCode, ...],
    ports: tuple[Port, ...],
    aretes_front: tuple[AreteFeature, ...],
    noeuds: tuple[NoeudEnchevetre, ...],
    features: tuple[str, ...],
) -> dict[str, Any]:
    """La charge utile de la page — triée, sans horodatage, sans chemin absolu."""
    couche_a_couche: dict[tuple[str, str], int] = {}
    for arete in aretes:
        cle = (arete.couche_source, arete.couche_cible)
        couche_a_couche[cle] = couche_a_couche.get(cle, 0) + arete.occurrences

    matrice = [
        {
            "source": source,
            "cible": cible,
            "occurrences": couche_a_couche.get((source, cible), 0),
            "autorise": autorise(source, cible),
        }
        for source in COUCHES
        for cible in COUCHES
        if source != cible
    ]

    hors_domaine = [port for port in ports if est_hors_domaine(port)]
    sans_adapter = [port for port in ports if est_sans_adapter(port)]

    clientes: dict[str, set[str]] = {}
    for lien in aretes_front:
        clientes.setdefault(lien.vers, set()).add(lien.de)

    return {
        "couches": list(COUCHES),
        "sens_autorise": {couche: sorted(cibles) for couche, cibles in SENS_AUTORISE.items()},
        "matrice": matrice,
        "paquets": [
            {
                "couche_source": arete.couche_source,
                "couche_cible": arete.couche_cible,
                "source": arete.paquet_source,
                "cible": arete.paquet_cible,
                "occurrences": arete.occurrences,
                "autorise": autorise(arete.couche_source, arete.couche_cible),
                "origines": list(arete.origines),
            }
            for arete in aretes
        ],
        "ports": [
            {
                "nom": port.nom,
                "fichier": port.fichier,
                "couche": port.couche,
                "methodes": list(port.methodes),
                "adapters": [_adapter(qualifie) for qualifie in port.adapters],
                "hors_domaine": est_hors_domaine(port),
                "sans_adapter": est_sans_adapter(port),
            }
            for port in ports
        ],
        "front": {
            # Les features telles que le **disque** les porte : une feature devenue autonome n'a
            # plus d'arête, et disparaîtrait d'un compte dérivé du graphe — le compteur baisserait
            # quand l'architecture s'améliore.
            "features": len(features),
            # `aretes` (142 entrées) était sérialisé, commité, comparé à l'octet… et lu par
            # personne : le site n'affiche que le fan-in et les nœuds. De la donnée morte dans un
            # artefact sous porte mécanique se paie sans rien rendre.
            "enchevetrements": [list(noeud.features) for noeud in noeuds],
            # Le fan-in désigne le **noyau partagé resté dans `features/`** : une feature importée
            # par quinze autres n'est plus une feature, c'est une brique commune qui n'a jamais été
            # nommée. C'est le chiffre qui rend la dérive lisible d'un coup d'œil.
            # L'**union** du disque et du graphe, jamais le seul disque : une feature citée par une
            # arête mais absente de la liste des répertoires disparaîtrait sans un mot du
            # classement. Ce cas ne se produit pas aujourd'hui (toute cible d'arête est un
            # répertoire), et c'est précisément pourquoi il faut le traiter ici : le jour où il se
            # produira, ce sera le signe d'une incohérence, pas une raison de se taire.
            "fan_in": [
                {"feature": feature, "clientes": len(clientes[feature])}
                for feature in sorted(clientes, key=lambda f: (-len(clientes[f]), f))
                if clientes[feature]
            ],
        },
        "resume": {
            "imports": sum(arete.occurrences for arete in aretes),
            # Distingué de `imports` **parce que l'addition ne tombait pas juste** : la carte
            # annonçait 827, la matrice juste en dessous en sommait 700. L'écart (127) est celui
            # des arêtes intra-couche entre paquets (`api/v1 → api`), agrégées sur une diagonale
            # que la matrice n'affiche pas. Sur une page dont l'argument est « un nombre qu'on ne
            # peut pas aller vérifier ne se corrige jamais », c'était le seul endroit invérifiable.
            "imports_entre_couches": sum(
                arete.occurrences for arete in aretes if arete.couche_source != arete.couche_cible
            ),
            "violations": len(violations(aretes)),
            "ports": len(ports),
            "ports_hors_domaine": len(hors_domaine),
            "ports_sans_adapter": len(sans_adapter),
            "features": len(features),
            "aretes_front": len(aretes_front),
            "enchevetrements": len(noeuds),
            # La plus grosse composante : « 4 nœuds » ne dit rien, « dont un de 19 features sur
            # 44 » dit tout. C'est ce nombre-là qui déclenche une décision, pas le compte de nœuds.
            "plus_gros_noeud": max((len(noeud.features) for noeud in noeuds), default=0),
        },
    }
