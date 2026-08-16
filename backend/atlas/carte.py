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
from atlas.sources.code import COUCHES, SENS_AUTORISE, autorise


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

    hors_domaine = [port for port in ports if port.couche != "domain"]
    sans_adapter = [port for port in ports if port.methodes and not port.adapters]

    clientes: dict[str, set[str]] = {}
    for lien in aretes_front:
        clientes.setdefault(lien.vers, set()).add(lien.de)
    features = sorted({arete.de for arete in aretes_front} | {arete.vers for arete in aretes_front})

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
                "herite": [_adapter(qualifie) for qualifie in port.herite],
                "hors_domaine": port.couche != "domain",
                "sans_adapter": bool(port.methodes) and not port.adapters,
            }
            for port in ports
        ],
        "front": {
            "features": len(features),
            "aretes": [
                {"de": arete.de, "vers": arete.vers, "occurrences": arete.occurrences}
                for arete in aretes_front
            ],
            "enchevetrements": [list(noeud.features) for noeud in noeuds],
            # Le fan-in désigne le **noyau partagé resté dans `features/`** : une feature importée
            # par quinze autres n'est plus une feature, c'est une brique commune qui n'a jamais été
            # nommée. C'est le chiffre qui rend la dérive lisible d'un coup d'œil.
            "fan_in": [
                {"feature": feature, "clientes": len(clientes.get(feature, set()))}
                for feature in sorted(features, key=lambda f: (-len(clientes.get(f, set())), f))
                if clientes.get(feature)
            ],
        },
        "resume": {
            "imports": sum(arete.occurrences for arete in aretes),
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
