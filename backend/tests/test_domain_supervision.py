"""Tests de la politique d'état de poste (E12US001, ADR-0038) — **dérivés du CA**, avant impl.

Source : `stories/E12-pilotage-jour-j.md`, E12US001, puce « CA » (« son **état** : *en ligne* ·
*hors ligne* · *non rattaché* ») et l'arbitrage heartbeat (ADR-0038). `etat_poste` est **pure** :
aucun `datetime`, aucune horloge — le service lui passe un écart déjà calculé. On y prouve la règle
métier seule ; le calcul de l'écart et son horodatage sont couverts côté service/infra.
"""

from __future__ import annotations

from domain.supervision import EtatPoste, etat_poste

SEUIL = 30.0  # secondes ; cf. ADR-0038 §1 (heartbeat ~10 s, hors ligne > 30 s)


def test_non_rattache_quel_que_soit_le_heartbeat() -> None:
    # Aucune tablette dessus : ni « en ligne » ni « hors ligne » — un troisième état à part entière.
    # Même un heartbeat récent (résidu d'une session fermée) ne le rend pas « rattaché ».
    assert (
        etat_poste(rattache=False, secondes_depuis_heartbeat=1.0, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.NON_RATTACHE
    )
    assert (
        etat_poste(rattache=False, secondes_depuis_heartbeat=None, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.NON_RATTACHE
    )


def test_rattache_et_vu_recemment_est_en_ligne() -> None:
    assert (
        etat_poste(rattache=True, secondes_depuis_heartbeat=5.0, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.EN_LIGNE
    )


def test_rattache_mais_silencieux_au_dela_du_seuil_est_hors_ligne() -> None:
    # « tablette morte » : rattachée (session ouverte) mais plus de heartbeat depuis > seuil.
    assert (
        etat_poste(rattache=True, secondes_depuis_heartbeat=45.0, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.HORS_LIGNE
    )


def test_rattache_jamais_vu_est_hors_ligne() -> None:
    # Session ouverte mais aucun heartbeat encore reçu : traité comme hors ligne (prudence).
    assert (
        etat_poste(rattache=True, secondes_depuis_heartbeat=None, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.HORS_LIGNE
    )


def test_borne_du_seuil_est_inclusive_cote_en_ligne() -> None:
    # Pile au seuil = encore en ligne ; un cheveu au-delà = hors ligne. La borne évite le
    # clignotement au ras de l'intervalle de heartbeat (ADR-0038, piège à surveiller).
    assert (
        etat_poste(rattache=True, secondes_depuis_heartbeat=SEUIL, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.EN_LIGNE
    )
    assert (
        etat_poste(rattache=True, secondes_depuis_heartbeat=SEUIL + 0.001, seuil_hors_ligne_s=SEUIL)
        is EtatPoste.HORS_LIGNE
    )
