"""Les arrêts programmés à la frontière : routes, câblage, persistance (E05US033, [ADR-0091]).

Tests d'**intégration**, donc écrits **après** l'implémentation (règle 9 : « API, repository,
câblage : tests après l'implémentation — il n'y a pas d'oracle en jeu »). Ils n'existaient pas
à la première livraison, et les quatre axes de revue l'ont relevé comme majeur : le diff ajoutait
deux routes, une
table, une migration et un aller-retour JSON **sans une ligne de test d'intégration**. Un round-trip
cassé aurait rendu toute l'US inerte sans qu'un seul test rougisse.

⚠️ **Le test de câblage est le plus important du fichier**, et il répare une promesse. Le
composition root écrivait « d'où le test de composition qui exige la présence du branchement » — ce
test n'existait pas. Or c'est le mode de panne nommé juste au-dessus : un branchement oublié rend
toute l'US **inerte** sans rien faire rougir (`DETTE-028`, six moteurs livrés dont aucun appelé). La
première livraison n'en branchait que **deux sur cinq**, et rien ne l'a dit.

[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.arret_programme import (
    ArretDeCirconstance,
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
)
from domain.erreurs import ArretProgrammeInvalide
from domain.phase import PhaseId, StatutPhase, TypePhase
from infrastructure.db import (
    ArretDeCirconstanceRepositorySQL,
    FranchissementArretRepositorySQL,
    PhaseRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin


@pytest.fixture
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _tournoi(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    connecter_admin(client)
    return int(
        client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
            "id"
        ]
    )


def _depart(client: TestClient, tournoi_id: int) -> int:
    """Le créneau porteur de la séquence (ADR-0075) — les phases y pendent, pas au tournoi."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"horaire": "09:00", "tarif_centimes": 800},
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _depots(app: FastAPI) -> tuple[PhaseRepositorySQL, FranchissementArretRepositorySQL]:
    """Les deux adapters, construits **depuis la fabrique de session** de l'application.

    ⚠️ Pas depuis `app.state` : le composition root les garde en variables locales, et les y exposer
    pour la seule commodité d'un test élargirait la surface publique de l'application à cause de sa
    suite de tests — l'inverse du sens des dépendances. La fabrique de session, elle, est déjà sur
    `app.state.database` et sert au démontage du décor.
    """
    fabrique = app.state.database.session_factory
    return PhaseRepositorySQL(fabrique), FranchissementArretRepositorySQL(fabrique)


# ─────────────────────────── Le câblage (règle 8) ───────────────────────────


def test_les_cinq_services_qui_ecrivent_un_resultat_signalent_les_arrets(
    app_session: FastAPI,
) -> None:
    """Le branchement du déclencheur sur les **cinq** chemins d'écriture, prouvé.

    ⚠️ **C'est le test que le composition root annonçait sans qu'il existe.** La première livraison
    ne branchait que la qualification et l'élimination directe : un arrêt programmé sur une phase de
    poules, de suisse ou de Big Shoot Off ne se déclenchait **jamais**, puisque ces phases tournent
    seules et qu'aucune validation n'atteignait le déclencheur. Bloquant relevé par les quatre axes.

    Rien ne protège automatiquement contre l'oubli d'un sixième format : ce test **est** le
    garde-fou, et son échec sera le seul signal.

    Il touche un attribut privé, comme son voisin d'E05US032 sur les lecteurs d'avancement, et pour
    la même raison : le composition root n'expose pas ce qu'il a branché, et c'est précisément ce
    branchement qu'on veut garder.
    """
    services = (
        app_session.state.service_saisie,
        app_session.state.service_saisie_duels,
        app_session.state.service_poules,
        app_session.state.service_suisse,
        app_session.state.service_big_shoot_off,
    )
    attendu = app_session.state.service_arrets_programmes

    for service in services:
        assert (
            service._arrets._evaluateur is attendu
        ), f"{type(service).__name__} n'est pas branché : ses arrêts programmés seraient inertes."


def test_le_service_d_arrets_lit_l_avancement_par_le_suivi(app_session: FastAPI) -> None:
    """La couture d'avancement est `ServiceSuiviDeroule`, seul à répondre pour tous les formats.

    Un second registre par type aurait laissé l'**élimination directe** hors du mécanisme — elle n'a
    aucun `LecteurAvancementDePhase` branché, son avancement étant reconstruit des braquets. Le test
    garde le choix d'ADR-0091 §7, que rien d'autre ne rendrait visible.
    """
    service = app_session.state.service_arrets_programmes

    assert service._suivi is app_session.state.service_suivi_deroule


def test_aucun_lecteur_d_avancement_n_est_ajoute_par_cette_tranche(app_session: FastAPI) -> None:
    """Le registre d'avancement est **inchangé** — et c'est ce qui borne le périmètre des arrêts.

    Les quatre types branchés sont ceux d'E05US032 (poules, suisse, Big Shoot Off ; l'élimination
    directe lit ses tours de sa projection, sans lecteur). Cette tranche n'en ajoute aucun : dériver
    le tour d'une qualification demande de résoudre sa population réelle (deux qualifications
    peuvent coexister dans un créneau, ADR-0082), le plan de cibles et les forfaits — repris par
    `E05US034`.

    ⚠️ **Ce test est le pendant du refus par type.** Tant que la qualification n'a pas de lecteur, un
    arrêt posé dessus serait inerte, d'où le 422 de `EtapeDeroule`. Le jour où `E05US035` la
    branchera, **les deux devront bouger ensemble** : ce test tombera, et il faudra retirer la
    qualification de `TYPES_DEROULES` côté refus. Les faire tomber ensemble est l'intérêt de les
    écrire tous les deux.
    """
    branches = app_session.state.service_suivi_deroule._avancements

    assert TypePhase.QUALIFICATION not in branches
    assert TypePhase.ECHAUFFEMENT not in branches


# ─────────────────────────── Les routes (règle 6) ───────────────────────────


def test_lister_les_arrets_en_attente_exige_un_admin(app_session: FastAPI) -> None:
    """Lecture d'exploitation, donc gardée : un créneau arrêté n'est pas public."""
    with TestClient(app_session) as client:
        reponse = client.get("/api/v1/departs/1/arrets/en-attente")

        assert reponse.status_code == 401


def test_relancer_un_arret_exige_un_admin(app_session: FastAPI) -> None:
    """Le geste qui remet la salle en marche est réservé à l'admin.

    `tests/test_acces_public.py` énumère déjà dynamiquement les écritures du schéma OpenAPI et exige
    un 401 sans jeton ; ce test **nomme** le cas, pour qu'un futur retrait de la dépendance produise
    un échec dont le message parle des arrêts plutôt qu'un compte global qui bouge.
    """
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/departs/1/arrets/1/relancer")

        assert reponse.status_code == 401


def test_relancer_un_arret_inconnu_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un identifiant qui ne désigne rien de relançable est un 404 explicite, pas un silence.

    Le geste vient d'un écran : un silence laisserait l'organisateur devant une salle arrêtée qu'il
    croit avoir relancée.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)

        reponse = client.post(f"/api/v1/departs/{depart_id}/arrets/999999/relancer")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "arret_introuvable"


def test_la_liste_des_arrets_en_attente_est_vide_par_defaut(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — l'enchaînement automatique est le défaut : aucun arrêt, donc rien à relancer."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)

        reponse = client.get(f"/api/v1/departs/{depart_id}/arrets/en-attente")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == []


# ─────────────────────── La persistance (ADR-0046, ADR-0076) ───────────────────────


def test_la_definition_d_un_arret_fait_l_aller_retour_par_le_json_de_l_etape(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les arrêts et le découpage voyagent dans `deroule_etape.config`, **sans migration**.

    C'est la propriété qu'ADR-0046 achète en laissant le document libre à la racine, et c'est elle
    qui rend la livraison sûre : une base non migrée relit `arrets` absent comme « aucun arrêt »,
    donc en comportement inchangé.

    Le round-trip est testé **par l'API**, pas par le repository seul : c'est la chaîne entière —
    DTO → agrégat → JSON → agrégat → DTO — qui doit être fidèle, et c'est elle qui portait le
    risque.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        _depart(client, tournoi_id)

        corps = {
            "type": "suisse",
            "arrets": [
                {"apres_tour": 2, "portee": "phase"},
                {"apres_tour": 4, "portee": "depart"},
            ],
        }
        creation = client.post(f"/api/v1/tournois/{tournoi_id}/phases", json=corps)
        assert creation.status_code == 201, creation.text

        relu = client.get(f"/api/v1/tournois/{tournoi_id}/phases")
        assert relu.status_code == 200, relu.text
        (etape,) = [e for e in relu.json() if e["type"] == "suisse"]
        assert etape["arrets"] == [
            {"apres_tour": 2, "portee": "phase"},
            {"apres_tour": 4, "portee": "depart"},
        ]


def test_deux_arrets_apres_le_meme_tour_sont_refuses_par_l_api(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'invariant de liste remonte en 422 à la frontière, pas en 500.

    Le refus vit sur l'`EtapeDeroule` (là où le nombre de tours est connu) et traverse la frontière
    comme une `DomainError`, donc un 422 au format `{code, message}` — jamais un message interne.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        _depart(client, tournoi_id)

        corps = {
            "type": "suisse",
            "arrets": [
                {"apres_tour": 3, "portee": "phase"},
                {"apres_tour": 3, "portee": "depart"},
            ],
        }
        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/phases", json=corps)

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "arret_programme_invalide"


def test_un_arret_sur_un_type_sans_tour_observable_est_refuse_a_la_frontiere(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le refus par type, jusqu'au client — et **sur la route de composition**, pas à la lecture.

    ⚠️ La garde vit sur `EtapeDeroule` et non sur `Phase` seule, parce que `ServicePhases.modifier`
    n'instancie **aucune phase** : posée là, l'étape aurait été persistée, puis chaque lecture
    (suivi, pilotage, affichage public) serait tombée en 422 à l'`instancier`. Une entrée client
    qu'aucun agrégat porteur ne juge, avec pour rayon d'explosion « créneau illisible ». Relevé par
    l'axe C1 de la revue.

    Le message part au client : l'organisateur doit lire pourquoi ici non, et où oui.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        _depart(client, tournoi_id)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={
                "type": "barrage",
                "arrets": [{"apres_tour": 2, "portee": "phase"}],
            },
        )

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "arret_programme_invalide"
        assert "barrage" in reponse.json()["message"]


def test_relancer_un_arret_franchi_rend_200_et_les_phases_reveillees(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le **chemin heureux** de la route de relance — le seul geste que l'US demande à l'admin.

    ⚠️ **Il manquait**, et c'est ce qui rendait la couverture trompeuse : trois tests gardaient les
    refus (401, 401, 404) et aucun le succès. Une route qui refuse correctement tout ce qu'elle doit
    refuser mais ne relance rien passe cette batterie sans broncher. Relevé en revue, axe B.

    Le franchissement est **posé directement en base** plutôt que déclenché par du tir : conduire un
    système suisse jusqu'à une frontière de tour par l'API demanderait un plan de cibles, quatre
    inscriptions et trois manches par rencontre. Le déclenchement a ses propres oracles au
    niveau du service (`test_service_arrets_programmes.py`) ; ce test-ci ne parle que de la
    **frontière API**.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"})
        assert creation.status_code == 201, creation.text

        depot_phases, depot = _depots(app_session)
        phases = [p for p in depot_phases.par_depart(depart_id) if p.id]
        phase_id = phases[0].id
        assert phase_id is not None
        # La phase est **réellement** en pause : la relance doit la rendre à `EN_COURS`, pas
        # seulement marquer le franchissement.
        depot_phases.enregistrer(dataclasses.replace(phases[0], statut=StatutPhase.EN_PAUSE))
        pose = depot.ajouter(
            FranchissementArret(
                phase_id=phase_id,
                apres_tour=2,
                etat=EtatFranchissement.FRANCHI,
                phases_arretees=(phase_id,),
            )
        )
        assert pose.id is not None

        # L'arrêt est bien offert à la relance…
        en_attente = client.get(f"/api/v1/departs/{depart_id}/arrets/en-attente")
        assert en_attente.status_code == 200, en_attente.text
        assert [a["id"] for a in en_attente.json()] == [pose.id]

        # … et le geste rend la salle à la marche, en nommant ce qu'il a réveillé.
        reponse = client.post(f"/api/v1/departs/{depart_id}/arrets/{pose.id}/relancer")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == [phase_id]
        relue = depot_phases.par_id(phase_id)
        assert relue is not None
        assert relue.statut is StatutPhase.EN_COURS
        # Idempotence de fait : l'arrêt levé n'est plus relançable, donc aucun bouton en double.
        assert client.get(f"/api/v1/departs/{depart_id}/arrets/en-attente").json() == []


def test_un_franchissement_fait_l_aller_retour_par_sa_table(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La table `franchissement_arret` : états, photo des tours, phases arrêtées.

    Trois pièges dans un seul aller-retour, et aucun n'était gardé : les clés JSON de
    `tours_a_finir` sont des **chaînes** (par nature du format) et doivent revenir en `int` ; une
    valeur `None` y est porteuse de sens (« cette phase n'avait plus rien en cours ») et ne doit pas
    se perdre ; et `phases_arretees` est ce que la relance rendra — un tableau vide ferait un bouton
    sans effet.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"})
        assert creation.status_code == 201, creation.text

    depot_phases, depot = _depots(app_session)
    phases = [p for p in depot_phases.par_depart(depart_id) if p.id]
    assert phases, "la phase de suisse doit avoir été instanciée dans le créneau"
    phase_id = phases[0].id
    assert phase_id is not None

    pose = depot.ajouter(
        FranchissementArret(
            phase_id=phase_id,
            apres_tour=2,
            etat=EtatFranchissement.ARME,
            tours_a_finir=((phase_id, 3), (PhaseId(phase_id + 1), None)),
        )
    )
    assert pose.id is not None

    relu = depot.par_id(pose.id)
    assert relu is not None
    assert relu.etat is EtatFranchissement.ARME
    assert dict(relu.tours_a_finir) == {phase_id: 3, phase_id + 1: None}

    depot.enregistrer(relu.franchir((phase_id,)))
    apres = depot.par_id(pose.id)
    assert apres is not None
    assert apres.etat is EtatFranchissement.FRANCHI
    assert apres.phases_arretees == (phase_id,)
    # La lecture par créneau passe par la jointure `franchissement_arret → phase` : un `where` faux
    # rendrait relançables les arrêts d'un autre départ.
    assert [f.id for f in depot.par_depart(depart_id)] == [pose.id]


def test_un_arret_ne_se_franchit_pas_deux_fois_dans_le_meme_creneau(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'unicité `(phase_id, apres_tour)` : l'idempotence tenue par le **schéma**, pas le service.

    Ce n'est pas décoratif : le déclencheur tourne après chaque validation de score, et ~30
    tablettes valident. Deux écritures concurrentes du même franchissement doivent être arbitrées
    par la base.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        client.post(f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"})

    depot_phases, depot = _depots(app_session)
    phases = [p for p in depot_phases.par_depart(depart_id) if p.id]
    phase_id = phases[0].id
    assert phase_id is not None

    modele = FranchissementArret(phase_id=phase_id, apres_tour=7, etat=EtatFranchissement.FRANCHI)
    depot.ajouter(modele)

    with pytest.raises(InfrastructureError):
        depot.ajouter(dataclasses.replace(modele))


# ───────────────────────── Les DTO (règle 6) ─────────────────────────


def test_la_portee_d_un_arret_franchi_se_deduit_de_sa_photo() -> None:
    """`ArretFranchiReponse` déduit la portée, elle n'est pas recopiée en base.

    ⚠️ Une déduction non testée sur laquelle l'écran fonde son libellé (« tout le créneau »)
    — relevé par l'axe B. Stocker la portée en double dans la table aurait ouvert une seconde source
    pour ce que la définition dit déjà, avec la divergence qui va avec : seul un arrêt de portée
    départ prend une photo des tours à finir, donc la présence de cette photo **est** le signal.
    """
    from api.v1.phases import ArretFranchiReponse

    de_phase = ArretFranchiReponse.de_agregat(
        FranchissementArret(
            phase_id=PhaseId(41),
            apres_tour=2,
            etat=EtatFranchissement.FRANCHI,
            phases_arretees=(PhaseId(41),),
            id=900,
        )
    )
    de_depart = ArretFranchiReponse.de_agregat(
        FranchissementArret(
            phase_id=PhaseId(41),
            apres_tour=2,
            etat=EtatFranchissement.FRANCHI,
            tours_a_finir=((PhaseId(42), 3),),
            phases_arretees=(PhaseId(41), PhaseId(42)),
            id=901,
        )
    )

    assert de_phase.portee is PorteeArret.PHASE
    assert de_depart.portee is PorteeArret.DEPART
    assert de_depart.phases_arretees == [41, 42]


def test_un_arret_programme_se_lit_et_s_ecrit_par_le_meme_dto() -> None:
    """Aller-retour DTO ↔ agrégat (règle 6) : l'agrégat n'est jamais exposé directement."""
    from api.v1.phases import ArretProgrammeDTO

    agregat = ArretProgramme(apres_tour=5, portee=PorteeArret.DEPART)

    assert ArretProgrammeDTO.de_agregat(agregat).vers_agregat() == agregat


# ══════════════════════ E05US034 — poser une pause le jour J, à la frontière ══════════════════════
#
# Tests écrits **après** l'implémentation (règle 9) : à cette couche il n'y a pas d'oracle métier en
# jeu — la règle « quand couper » vit au domaine et au service, avec ses propres tests dérivés du
# CA. Ce fichier garde la **frontière** : qui a le droit, quel code de retour, et ce que la base
# retient.


def _depot_circonstance(app: FastAPI) -> ArretDeCirconstanceRepositorySQL:
    return ArretDeCirconstanceRepositorySQL(app.state.database.session_factory)


def test_poser_un_arret_relatif_exige_un_admin(app_session: FastAPI) -> None:
    """La route est une **commande de pilotage** : un anonyme ne suspend pas la salle.

    Même garde que les deux routes voisines. Le dire par un test plutôt que de s'en remettre au
    `Depends` : c'est une ligne de décorateur, donc une ligne qui s'oublie en copiant la voisine.
    """
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/departs/1/phases/1/arrets", json={"dans_x_tours": 2})

    assert reponse.status_code == 401, reponse.text


def test_poser_un_arret_sur_une_phase_d_un_autre_creneau_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le créneau de l'URL et celui de la phase doivent concorder — sinon on pilote chez le voisin.

    ⚠️ Le mode de panne visé n'est pas l'attaque mais l'**onglet resté ouvert** : le sélecteur de
    créneau du pilotage a changé, la page pas. Sans ce contrôle, un clic arrêterait le départ du
    matin depuis l'écran de celui de l'après-midi.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        assert (
            client.post(
                f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"}
            ).status_code
            == 201
        )
        autre = client.post(
            f"/api/v1/tournois/{tournoi_id}/departs",
            json={"numero": 2, "tarif_centimes": 800, "horaire": "14:00"},
        )
        assert autre.status_code == 201, autre.text

        depot_phases, _ = _depots(app_session)
        phase_id = depot_phases.par_depart(depart_id)[0].id
        assert phase_id is not None

        reponse = client.post(
            f"/api/v1/departs/{autre.json()['id']}/phases/{phase_id}/arrets",
            json={"dans_x_tours": 1},
        )

    assert reponse.status_code == 404, reponse.text


def test_poser_un_arret_sur_un_type_sans_tour_observable_rend_422(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La **seconde porte d'entrée** applique la règle de l'atelier — c'est le point du test.

    `E05US033` refuse déjà d'enregistrer un arrêt sur une qualification à la composition. Cette
    US ouvre un second chemin ; s'il ne consultait pas la même table de types, l'organisateur
    pourrait poser depuis le pilotage exactement le réglage inerte que l'atelier lui refuse — et le
    découvrir le jour J, ce que le refus existe pour empêcher.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "qualification"}
        )
        assert creation.status_code == 201, creation.text

        depot_phases, _ = _depots(app_session)
        phase_id = depot_phases.par_depart(depart_id)[0].id
        assert phase_id is not None

        reponse = client.post(
            f"/api/v1/departs/{depart_id}/phases/{phase_id}/arrets", json={"dans_x_tours": 1}
        )

    assert reponse.status_code == 422, reponse.text
    assert "tours" in reponse.json()["message"]


def test_poser_zero_tour_est_refuse_par_le_dto(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`ge=1` : le mécanisme coupe à la fin d'un tour, jamais au milieu (ADR-0091).

    Refusé **au DTO** et non au domaine seulement, parce que c'est une borne d'entrée client : la
    faire remonter jusqu'au service coûterait deux lectures pour un refus que la forme suffit à
    prononcer.

    ⚠️ **400 et non 422**, et la nuance n'est pas cosmétique : ce projet range les refus de *forme*
    (`requete_invalide`, Pydantic) en 400 et les refus **métier** en 422. Le domaine refuserait
    aussi ce 0 — avec un message qui dit où aller (« mettez la phase en pause ») —, mais il ne sera
    jamais atteint. C'est un arbitrage de coût assumé : deux lectures en base pour un refus que la
    forme prononce seule.
    """
    with TestClient(app_session) as client:
        _tournoi(client, connecter_admin)
        reponse = client.post("/api/v1/departs/1/phases/1/arrets", json={"dans_x_tours": 0})

    assert reponse.status_code == 400, reponse.text


def test_un_arret_de_circonstance_fait_l_aller_retour_par_sa_table(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La table `arret_de_circonstance` : le créneau, la phase, le tour résolu, la portée.

    ⚠️ **Le `where` sur `depart_id` est l'oracle réel de ce test** — c'est la propriété qui
    distingue un arrêt de circonstance d'un arrêt de déroulé (ADR-0092). Un adapter qui rendrait
    tout le tournoi ferait s'arrêter le créneau du soir pour une décision du matin, et **aucun autre
    test ne le verrait** : le service, lui, reçoit une liste déjà filtrée.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        assert (
            client.post(
                f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"}
            ).status_code
            == 201
        )
        autre = client.post(
            f"/api/v1/tournois/{tournoi_id}/departs",
            json={"numero": 2, "tarif_centimes": 800, "horaire": "14:00"},
        )
        assert autre.status_code == 201, autre.text

    depot_phases, _ = _depots(app_session)
    depot = _depot_circonstance(app_session)
    phase_id = depot_phases.par_depart(depart_id)[0].id
    assert phase_id is not None

    pose = depot.ajouter(
        ArretDeCirconstance(
            depart_id=depart_id,
            phase_id=phase_id,
            apres_tour=4,
            portee=PorteeArret.DEPART,
        )
    )
    assert pose.id is not None

    (relu,) = depot.par_depart(depart_id)
    assert relu.apres_tour == 4
    assert relu.portee is PorteeArret.DEPART
    assert relu.phase_id == phase_id
    assert depot.par_depart(int(autre.json()["id"])) == []


def test_la_meme_pause_ne_se_pose_pas_deux_fois(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'unicité `(depart_id, phase_id, apres_tour)` tenue par le **schéma**, pas par le service.

    Le service refuse déjà le doublon qu'il **voit** ; cette contrainte ferme la course que sa
    lecture ne peut pas fermer — deux postes d'admin qui cliquent dans la même seconde, ou le
    double-clic d'un seul, ce qui est un geste ordinaire du jour J sur une tablette.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        assert (
            client.post(
                f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"}
            ).status_code
            == 201
        )

    depot_phases, _ = _depots(app_session)
    depot = _depot_circonstance(app_session)
    phase_id = depot_phases.par_depart(depart_id)[0].id
    assert phase_id is not None
    arret = ArretDeCirconstance(depart_id=depart_id, phase_id=phase_id, apres_tour=3)
    depot.ajouter(arret)

    # ⚠️ **`ArretProgrammeInvalide`, et le type importe autant que le refus** (correctif de revue,
    # axe A). L'oracle attendait `InfrastructureError`, que la frontière mappe en **500 générique**
    # — l'organisateur qui double-clique dans son écran de pilotage recevait « erreur interne du
    # serveur » pour un geste ordinaire du jour J. Le refus est désormais **métier** (422), avec le
    # même message que celui que le service prononce en amont pour le doublon qu'il voit. Asserter
    # le type, c'est asserter le **code HTTP** que l'organisateur recevra.
    with pytest.raises(ArretProgrammeInvalide):
        depot.ajouter(arret)


def test_l_heure_de_coupe_fait_l_aller_retour_et_remonte_a_l_api(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`arrete_depuis` : ce que la pastille du tableau de bord décompte (« depuis 14 min »).

    Deux choses en un aller-retour, parce qu'elles tombent ensemble ou pas du tout : la colonne
    doit **survivre** à l'écriture (une donnée d'affichage est le genre de champ qu'on oublie de
    recopier dans `enregistrer`) et le DTO doit la **rendre**. Sans le second, la colonne serait
    juste et l'écran resterait muet.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        assert (
            client.post(
                f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "suisse"}
            ).status_code
            == 201
        )

        depot_phases, depot = _depots(app_session)
        phases = [p for p in depot_phases.par_depart(depart_id) if p.id]
        phase_id = phases[0].id
        assert phase_id is not None
        depot_phases.enregistrer(dataclasses.replace(phases[0], statut=StatutPhase.EN_PAUSE))
        coupe = datetime.datetime(2026, 3, 14, 12, 45, tzinfo=datetime.UTC)
        pose = depot.ajouter(
            FranchissementArret(
                phase_id=phase_id,
                apres_tour=2,
                etat=EtatFranchissement.FRANCHI,
                phases_arretees=(phase_id,),
                arrete_depuis=coupe,
            )
        )
        assert pose.id is not None
        assert pose.arrete_depuis is not None

        (rendu,) = client.get(f"/api/v1/departs/{depart_id}/arrets/en-attente").json()

    assert rendu["arrete_depuis"] is not None
    # L'oracle est « le client relit **l'instant** écrit », pas « l'heure murale est 12 ». La
    # nuance décide de tout : SQLite rend un `datetime` *naive*, dont l'heure murale est la seule
    # propriété que la perte de fuseau **conserve**. Une égalité d'instants, elle, exige l'offset
    # dans la charge utile — donc elle retombe si le réattachement UTC saute (revue E05US034).
    assert datetime.datetime.fromisoformat(rendu["arrete_depuis"]) == coupe
    assert datetime.datetime.fromisoformat(rendu["arrete_depuis"]).tzinfo is not None
