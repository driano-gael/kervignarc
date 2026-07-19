"""Tests du `RegistreIdempotence` (E04US002, ADR-0036) — déduplication des écritures de saisie.

Dérivés du CA « enregistrement » (ex-005 : *un rejeu réseau ne crée pas une volée en double*) et
d'ADR-0036 : premier passage exécuté et mémorisé, rejeu renvoyé sans ré-exécuter, identifiants
distincts indépendants, absence d'identifiant = pas de déduplication, borne LRU. Mécanisme
d'infrastructure (pas de règle métier) — testé contre une commande compteur déterministe.
"""

from __future__ import annotations

from infrastructure.idempotence import RegistreIdempotence


class Compteur:
    """Commande instrumentée : compte ses exécutions, renvoie un résultat distinct par appel."""

    def __init__(self) -> None:
        self.appels = 0

    def __call__(self) -> int:
        self.appels += 1
        return self.appels


def test_execute_une_seule_fois_par_identifiant() -> None:
    """Deux appels de même identifiant : l'acte n'est exécuté qu'une fois."""
    registre = RegistreIdempotence()
    compteur = Compteur()

    premier = registre.executer("saisie-1", compteur)
    rejeu = registre.executer("saisie-1", compteur)

    assert compteur.appels == 1
    assert premier == rejeu == 1


def test_le_resultat_du_premier_passage_est_rejoue() -> None:
    """Le rejeu renvoie le **résultat mémorisé**, pas un nouveau calcul (même ACK au client)."""
    registre = RegistreIdempotence()
    compteur = Compteur()

    registre.executer("saisie-1", compteur)  # -> 1, mémorisé
    rejeu = registre.executer("saisie-1", compteur)

    assert rejeu == 1  # et non 2


def test_identifiants_distincts_sont_independants() -> None:
    """Deux gestes différents (identifiants différents) s'exécutent chacun une fois."""
    registre = RegistreIdempotence()
    compteur = Compteur()

    a = registre.executer("saisie-a", compteur)
    b = registre.executer("saisie-b", compteur)

    assert compteur.appels == 2
    assert (a, b) == (1, 2)


def test_sans_identifiant_pas_de_deduplication() -> None:
    """`None` (client qui n'en fournit pas) → chaque appel s'exécute, aucune mémorisation."""
    registre = RegistreIdempotence()
    compteur = Compteur()

    registre.executer(None, compteur)
    registre.executer(None, compteur)

    assert compteur.appels == 2


def test_identifiant_vide_pas_de_deduplication() -> None:
    """Une chaîne vide vaut absence d'identifiant : pas de déduplication."""
    registre = RegistreIdempotence()
    compteur = Compteur()

    registre.executer("", compteur)
    registre.executer("", compteur)

    assert compteur.appels == 2


def test_eviction_lru_au_dela_de_la_borne() -> None:
    """Garde-fou mémoire : au-delà de la borne, le plus ancien identifiant est oublié (LRU).

    Oublié = un rejeu de cet identifiant **se ré-exécute** (au pire un doublon si la borne est
    atteinte, borne dimensionnée pour que ce cas ne survienne pas en exploitation — ADR-0036).
    """
    registre = RegistreIdempotence(borne=2)
    compteur = Compteur()

    registre.executer("saisie-1", compteur)  # -> 1
    registre.executer("saisie-2", compteur)  # -> 2
    registre.executer("saisie-3", compteur)  # -> 3, évince « saisie-1 »
    rejeu_1 = registre.executer("saisie-1", compteur)  # oublié -> ré-exécuté -> 4

    assert compteur.appels == 4
    assert rejeu_1 == 4


def test_l_acces_recent_preserve_de_l_eviction() -> None:
    """Un identifiant relu récemment remonte en tête (LRU) et n'est pas évincé à sa place."""
    registre = RegistreIdempotence(borne=2)
    compteur = Compteur()

    registre.executer("saisie-1", compteur)  # -> 1
    registre.executer("saisie-2", compteur)  # -> 2
    registre.executer("saisie-1", compteur)  # rejeu : « saisie-1 » redevient le plus récent
    registre.executer("saisie-3", compteur)  # -> 3, évince « saisie-2 » (le plus ancien)

    assert registre.executer("saisie-1", compteur) == 1  # toujours mémorisé
    assert compteur.appels == 3
