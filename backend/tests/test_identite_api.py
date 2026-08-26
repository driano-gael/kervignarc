"""Test bout-en-bout de l'API **identité visuelle du tournoi** (E16US006, ADR-0097).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — et
vérifie ce que seul un test d'API peut voir : le **câblage** (composition root), le **mapping** des
erreurs typées à la frontière, la **portée des autorisations** (lectures publiques, écritures admin)
et les **en-têtes de sûreté** posés sur les octets d'un logo.

Écrit **après** l'implémentation, conformément à la règle 9 : il n'y a pas d'oracle métier en jeu
ici. L'oracle de la dérivation, lui, est dans `test_domain_identite.py`, écrit avant.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.identite import POIDS_LOGO_MAX_OCTETS
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    # Bloc de données puis marque de fin : un **vrai** PNG, pas seulement une signature. Depuis la
    # revue, `Logo.deposer` exige la structure (`IHDR` en douzième position, `IEND` présente) — la
    # signature seule laissait passer un polyglotte PNG/SVG porteur de script, déposé pour de vrai
    # par le relecteur adversarial et accepté en 200.
    b"\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB\x60\x82"
)
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


@pytest.fixture
def app_identite(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _emplacements(identite: dict[str, Any]) -> list[str]:
    """Les emplacements pourvus d'une réponse d'identité, triés.

    Le DTO porte, pour chaque logo, l'emplacement **et** l'empreinte de son contenu (le numéro de
    version que le front pose dans l'URL). La plupart des tests ne s'intéressent qu'aux
    emplacements : les lire d'ici évite de recopier la forme du DTO sept fois, et laisse
    `test_l_empreinte_servie_change_avec_le_contenu` être le seul à regarder l'empreinte.
    """
    return [logo["emplacement"] for logo in identite["logos"]]


def _creer_tournoi(client: TestClient, nom: str = "Challenge des Champions") -> int:
    """Crée un tournoi et rend son identifiant (l'admin doit déjà être connecté)."""
    reponse = client.post(
        "/api/v1/tournois", json={"nom": nom, "date": "2026-11-14", "type_tournoi": "officiel"}
    )
    assert reponse.status_code == 201, reponse.text
    identifiant = reponse.json()["id"]
    assert isinstance(identifiant, int)
    return identifiant


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Lecture : le défaut hérité, et la déclinaison servie prête à poser


def test_un_tournoi_neuf_herite_de_l_identite_du_club(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « défaut = identité du club si rien n'est fourni ».

    `reglee: false` est la donnée qui permet à l'écran de dire *hérité* plutôt que d'afficher un
    formulaire vierge — la migration `0050` ne sème aucune ligne précisément pour que la distinction
    existe.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/identite")

        assert reponse.status_code == 200, reponse.text
        identite = reponse.json()
        assert identite["reglee"] is False
        assert identite["primaire"]["couleur"] == "#b71918", "le rouge du club"
        assert identite["secondaire"]["couleur"] == "#1d1d1b", "l'anthracite du club"
        assert _emplacements(identite) == []


def test_la_reponse_porte_les_jetons_derives_des_deux_themes(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le front reçoit des **valeurs à poser**, pas une couleur à recalculer.

    C'est le point qui justifie que la dérivation vive côté serveur (règle 2) : si la réponse ne
    portait que la couleur brute, le navigateur devrait refaire le calcul — donc en détenir une
    seconde copie, non testée et silencieusement divergente.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        primaire = client.get(f"/api/v1/tournois/{tournoi_id}/identite").json()["primaire"]

        # Thème sombre : le rouge du club échoue en texte, ses variantes sont dérivées.
        assert primaire["sombre"]["surface"] == "#b71918", "l'aplat garde la couleur exacte"
        assert primaire["sombre"]["contour"] == "#cc1c1b"
        assert primaire["sombre"]["texte"] != "#b71918"
        assert primaire["sombre"]["encre"] == "#ffffff"
        # Thème clair : il tient tel quel, les trois jetons se confondent (cf. `index.css`).
        assert primaire["clair"]["texte"] == "#b71918"


def test_le_contraste_est_chiffre_et_accompagne_de_ses_seuils(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`P-4` : l'alerte est **chiffrée**. `D-16` : « une alerte qui ne chiffre pas son impact est un
    clic de plus, pas une protection ».

    Les seuils voyagent avec la réponse pour que le front n'en tienne pas sa propre copie : il
    pourrait sinon annoncer « conforme » sur un critère que le serveur n'applique plus.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        identite = client.get(f"/api/v1/tournois/{tournoi_id}/identite").json()

        assert identite["primaire"]["contraste_sur_sombre"] == 2.55, "le chiffre publié par DV-04"
        assert identite["primaire"]["contraste_sur_clair"] == 6.63
        assert identite["seuil_contour"] == 3.0
        assert identite["seuil_texte"] == 4.5


def test_l_identite_d_un_tournoi_inconnu_est_un_404(app_identite: FastAPI) -> None:
    with TestClient(app_identite) as client:
        assert client.get("/api/v1/tournois/9999/identite").status_code == 404


def test_lire_l_identite_ne_demande_aucune_session(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Lecture **publique** : l'écran de salle et l'appli du spectateur n'ont pas de session admin.

    Le second client n'a jamais d'en-tête d'autorisation — c'est tout l'oracle. Un
    `Depends(exiger_admin)` ajouté par distraction sur cette route éteindrait l'identité sur le
    vidéoprojecteur, et aucun test d'admin ne le verrait.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

    with TestClient(app_identite) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/identite")

    assert "Authorization" not in anonyme.headers
    assert reponse.status_code == 200, reponse.text


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Écriture des accents


def test_regler_les_accents_les_persiste_et_bascule_reglee(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        ecriture = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite",
            json={"primaire": "#0B6E9E", "secondaire": "#FFD400"},
        )

        assert ecriture.status_code == 200, ecriture.text
        assert ecriture.json()["reglee"] is True
        relecture = client.get(f"/api/v1/tournois/{tournoi_id}/identite").json()
        assert relecture["primaire"]["couleur"] == "#0b6e9e", "normalisé en minuscules"
        assert relecture["secondaire"]["couleur"] == "#ffd400"
        assert relecture["reglee"] is True


def test_une_couleur_mal_formee_est_refusee_en_422(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`CouleurInvalide` est une erreur de **domaine** → 422 (règle 5), pas un 400 de validation
    Pydantic : la règle de format appartient à `Couleur.depuis_hex`, pas au DTO."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite",
            json={"primaire": "bleu ciel", "secondaire": "#ffd400"},
        )

        assert refus.status_code == 422, refus.text
        assert refus.json()["code"] == "couleur_invalide"


def test_un_contraste_faible_n_est_jamais_refuse(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`P-4` : « alerte chiffrée et **non bloquante** ».

    Le cas extrême : un accent identique au fond sombre (contraste 1:1). Il est **accepté**, ses
    variantes sont dérivées, et le chiffre dit la vérité. Un refus ici retirerait sa marque à un
    club dont la charte est faible — ce que `DV-05` interdit en toutes lettres.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        ecriture = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite",
            json={"primaire": "#1d1d1b", "secondaire": "#1d1d1b"},
        )

        assert ecriture.status_code == 200, ecriture.text
        rendu = ecriture.json()["primaire"]
        assert rendu["contraste_sur_sombre"] == 1.0, "le chiffre ne ment pas"
        assert rendu["sombre"]["texte"] != "#1d1d1b", "mais la variante de texte, elle, est lisible"


def test_regler_les_accents_sans_session_est_refuse(app_identite: FastAPI) -> None:
    with TestClient(app_identite) as client:
        refus = client.put(
            "/api/v1/tournois/1/identite", json={"primaire": "#000000", "secondaire": "#ffffff"}
        )
        assert refus.status_code == 401


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Les logos


def test_deposer_puis_servir_un_png(app_identite: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        depot = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement",
            content=PNG,
            headers={"Content-Type": "image/png"},
        )

        assert depot.status_code == 200, depot.text
        assert _emplacements(depot.json()) == ["evenement"]

        servi = client.get(f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement")
        assert servi.status_code == 200
        assert servi.content == PNG
        assert servi.headers["content-type"] == "image/png"


def test_les_deux_emplacements_sont_independants(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA d'E16US006 : « un champ **de plus** pour le logo du club, en plus du logo du tournoi ».

    Déposer l'un ne remplace pas l'autre, et en retirer un laisse le second en place. C'est
    l'invariant que l'adapter tient colonne par colonne — un `UPDATE` trop large le casserait sans
    qu'aucun test unitaire ne bouge.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/identite/logos"

        client.put(f"{base}/evenement", content=PNG, headers={"Content-Type": "image/png"})
        apres_second = client.put(
            f"{base}/club", content=SVG, headers={"Content-Type": "image/svg+xml"}
        )
        assert _emplacements(apres_second.json()) == ["club", "evenement"]

        apres_retrait = client.delete(f"{base}/evenement")
        assert _emplacements(apres_retrait.json()) == ["club"], "le logo du club a survécu"
        assert client.get(f"{base}/club").content == SVG


def test_deposer_un_logo_ne_pretend_pas_que_les_couleurs_sont_reglees(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le piège que l'adapter crée en fabriquant une ligne à la volée : la ligne existe désormais,
    mais **personne n'a choisi de couleur**. L'écran doit continuer à dire *hérité*."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
            content=PNG,
            headers={"Content-Type": "image/png"},
        )

        relecture = client.get(f"/api/v1/tournois/{tournoi_id}/identite").json()
        assert _emplacements(relecture) == ["club"]
        assert relecture["reglee"] is False, "un logo n'est pas un choix de couleurs"
        assert relecture["primaire"]["couleur"] == "#b71918"


def test_regler_les_accents_n_efface_pas_un_logo_deja_depose(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Symétrique du précédent : les deux gestes sont indépendants dans les deux sens."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
            content=PNG,
            headers={"Content-Type": "image/png"},
        )

        apres = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite",
            json={"primaire": "#0b6e9e", "secondaire": "#ffd400"},
        )

        assert _emplacements(apres.json()) == ["club"]
        assert apres.json()["reglee"] is True


def test_un_emplacement_vide_est_un_404(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        assert client.get(f"/api/v1/tournois/{tournoi_id}/identite/logos/club").status_code == 404


def test_retirer_un_logo_absent_est_idempotent(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le second clic d'un organisateur qui n'est pas sûr d'avoir cliqué — geste ordinaire sur une
    tablette. L'état visé est atteint dans les deux cas."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        retrait = client.delete(f"/api/v1/tournois/{tournoi_id}/identite/logos/club")

        assert retrait.status_code == 200, retrait.text
        assert _emplacements(retrait.json()) == []


def test_un_svg_porteur_de_script_est_refuse_par_l_api(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le refus vient du domaine ; ce test prouve qu'il **atteint la frontière** en 422, et n'est
    pas avalé quelque part entre la route et l'agrégat."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement",
            content=b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            headers={"Content-Type": "image/svg+xml"},
        )

        assert refus.status_code == 422, refus.text
        assert refus.json()["code"] == "type_de_logo_refuse"


def test_un_format_non_accepte_est_refuse_en_422(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement",
            content=b"GIF89a",
            headers={"Content-Type": "image/gif"},
        )

        assert refus.status_code == 422, refus.text
        assert refus.json()["code"] == "type_de_logo_refuse"


def test_un_logo_trop_lourd_est_refuse_en_disant_la_limite(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement",
            content=PNG + b"\x00" * POIDS_LOGO_MAX_OCTETS,
            headers={"Content-Type": "image/png"},
        )

        assert refus.status_code == 422, refus.text
        assert refus.json()["code"] == "logo_trop_volumineux"
        assert "512 Ko" in refus.json()["message"], "le refus chiffre la limite"


def test_les_octets_d_un_logo_sont_servis_avec_leurs_gardes(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ La **seconde barrière** contre un SVG exécutable : le domaine refuse ce qui exécute, ces
    en-têtes tiennent si un fichier est entré sous une version antérieure des règles.

    Un test explicite parce que ce sont trois chaînes qu'aucun autre test ne regarde : les retirer
    ne casserait rien de visible, et la faille ne se révélerait que le jour où quelqu'un ouvre le
    lien du logo dans l'onglet où il est connecté en admin.

    Le `Content-Type` servi est asserté **avec** elles : `nosniff` ne veut rien dire sans le type
    qu'il interdit de réinterpréter, et le trio ne tient qu'ensemble (relevé en revue).
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
            content=SVG,
            headers={"Content-Type": "image/svg+xml"},
        )

        servi = client.get(f"/api/v1/tournois/{tournoi_id}/identite/logos/club")

        assert servi.headers["content-security-policy"] == "default-src 'none'"
        assert servi.headers["x-content-type-options"] == "nosniff"
        assert servi.headers["content-disposition"] == "inline"
        assert servi.headers["content-type"] == "image/svg+xml", "le type que nosniff verrouille"
        # ⚠️ `Cache-Control` porte désormais la correction du cache : l'URL d'un logo ne change
        # qu'avec son **contenu** (l'empreinte), et c'est cet en-tête qui impose la revalidation.
        # Le retirer rendrait un logo corrigé invisible jusqu'au vidage du cache, sans rougir.
        assert servi.headers["cache-control"] == "no-cache"


def test_la_reponse_sert_la_borne_de_poids_au_lieu_de_la_faire_recopier(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ Un champ de contrat que **rien** n'assertait, et dont l'absence s'éteint en silence.

    Le front a perdu sa copie en dur de la limite dans le même commit qui a ajouté ce champ : il lit
    `identite.poids_logo_max_octets` pour refuser un fichier hors limite **avant** de le faire
    traverser le Wi-Fi du gymnase. Si le champ est renommé ou disparaît, `fichier.size > undefined`
    vaut `false` — le pré-contrôle s'éteint, la fiche de recette ment (« immédiat, sans attente »),
    et aucun test ne rougit nulle part."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        identite = client.get(f"/api/v1/tournois/{tournoi_id}/identite").json()

        assert identite["poids_logo_max_octets"] == POIDS_LOGO_MAX_OCTETS
        assert identite["seuil_contour"] == 3.0
        assert identite["seuil_texte"] == 4.5


@pytest.mark.parametrize(
    ("entete", "attendu"),
    [
        ("exact", 304),
        ("faible", 304),
        ("liste", 304),
        ("joker", 304),
        ("autre", 200),
    ],
)
def test_la_revalidation_accepte_les_formes_conformes_d_if_none_match(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin, entete: str, attendu: int
) -> None:
    """⚠️ `_etag_deja_connu` est un durcissement dont **rien** n'exerçait la partie neuve.

    `If-None-Match` porte une **liste**, et ses entrées peuvent être faibles (`W/"…"`) ou valoir
    `*` — trois formes conformes que l'égalité stricte d'avant faisait retomber en 200 complet, soit
    jusqu'à 512 Ko de plus par tablette pour un fichier déjà en cache. Le seul test 304 renvoyait
    l'`ETag` exact, qui passait déjà : supprimer la fonction laissait la suite verte.

    Le cas `autre` est celui qui compte autant que les quatre premiers : il interdit à la fonction
    de
    dégénérer en « toujours 304 »."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        chemin = f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement"
        client.put(chemin, content=PNG, headers={"Content-Type": "image/png"})
        etag = client.get(chemin).headers["etag"]
        propose = {
            "exact": etag,
            "faible": f"W/{etag}",
            "liste": f'"deja-vu", {etag}',
            "joker": "*",
            "autre": '"deja-vu"',
        }[entete]

        reponse = client.get(chemin, headers={"If-None-Match": propose})

        assert reponse.status_code == attendu


def test_un_logo_inchange_se_revalide_en_304(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'écran de salle rafraîchit en boucle : sans `ETag`, chaque cycle renverrait le fichier."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        chemin = f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement"
        client.put(chemin, content=PNG, headers={"Content-Type": "image/png"})

        premiere = client.get(chemin)
        etag = premiere.headers["etag"]
        seconde = client.get(chemin, headers={"If-None-Match": etag})

        assert seconde.status_code == 304


def test_remplacer_un_logo_change_son_etag(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le pendant du test précédent, et le plus important des deux : un `ETag` qui ne changerait pas
    ferait qu'un organisateur corrigeant son fichier continuerait de voir l'ancien."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        chemin = f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement"

        client.put(chemin, content=PNG, headers={"Content-Type": "image/png"})
        avant = client.get(chemin).headers["etag"]
        client.put(chemin, content=SVG, headers={"Content-Type": "image/svg+xml"})
        apres = client.get(chemin).headers["etag"]

        assert avant != apres


def test_deposer_un_logo_sans_session_est_refuse(app_identite: FastAPI) -> None:
    with TestClient(app_identite) as client:
        refus = client.put(
            "/api/v1/tournois/1/identite/logos/club",
            content=PNG,
            headers={"Content-Type": "image/png"},
        )
        assert refus.status_code == 401


def test_retirer_un_logo_sans_session_est_refuse(app_identite: FastAPI) -> None:
    """La symétrie du test précédent. Le dépôt et le retrait sont les **deux seules routes du
    dépôt** qui écrivent des octets arbitraires en base ; le garde-fou dynamique de
    `test_acces_public.py` les couvre déjà par énumération, mais c'est ici que le refus se lit."""
    with TestClient(app_identite) as client:
        assert client.delete("/api/v1/tournois/1/identite/logos/club").status_code == 401


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Non-régression : régler l'identité ne rend pas le tournoi indéracinable


def test_un_tournoi_dont_l_identite_est_reglee_reste_supprimable(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Ce test garde un bloquant trouvé en revue adversariale, à l'exécution.**

    La ligne `identite_tournoi` naît au **premier réglage** — accents ou logo, indifféremment — et
    rien ne la supprime jamais (`retirer_logo` vide les colonnes, il ne retire pas la ligne). Sa
    clé étrangère ayant d'abord été posée **sans `ON DELETE`**, et `PRAGMA foreign_keys` étant à
    `ON`, supprimer le tournoi levait une `IntegrityError` → **500**. Effleurer l'écran d'identité
    rendait donc le tournoi *définitivement* indéracinable, alors qu'un brouillon vide se supprimait
    jusque-là (DETTE-001 note que le 500 était déjà systématique ailleurs — c'était le dernier
    chemin qui marchait, et cette US le fermait depuis l'écran qu'elle ajoute).

    La FK porte désormais `ON DELETE CASCADE` : l'identité est un **composant strict** de l'agrégat
    tournoi, comme `volee` l'est de la série. Ce test tient les deux moitiés — la suppression passe,
    et la ligne d'identité part avec.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        # Les deux gestes, parce que chacun crée la ligne à lui seul.
        assert (
            client.put(
                f"/api/v1/tournois/{tournoi_id}/identite",
                json={"primaire": "#b71918", "secondaire": "#1d1d1b"},
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
                content=PNG,
                headers={"Content-Type": "image/png"},
            ).status_code
            == 200
        )

        suppression = client.delete(f"/api/v1/tournois/{tournoi_id}")

        assert suppression.status_code == 204, suppression.text
        assert client.get(f"/api/v1/tournois/{tournoi_id}").status_code == 404

        # ⚠️ **C'est cette assertion-ci qui prouve la cascade, et la précédente rédaction ne
        # l'avait pas.** Elle interrogeait `/identite`, qui rend 404 parce que le *tournoi* a
        # disparu — que la ligne d'identité ait survécu ou non : une tautologie présentée comme une
        # preuve. La route des **octets**, elle, ne vérifie pas l'existence du tournoi (c'est écrit
        # dans `ServiceIdentite.logo` : distinguer coûterait une requête sur la seule route que
        # trente tablettes appellent ensemble). Elle sert donc encore le logo d'un tournoi supprimé
        # si la ligne est restée orpheline — démontré en revue, `PRAGMA foreign_keys=OFF` à
        # l'appui. C'est la seule porte qui voie la différence.
        orphelin = client.get(f"/api/v1/tournois/{tournoi_id}/identite/logos/club")
        assert orphelin.status_code == 404, "la ligne d'identité doit être partie avec le tournoi"


def test_un_logo_absent_repond_au_contrat_d_erreur(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le 404 d'un emplacement vide portait un corps **nu** — la seule réponse du module hors du
    format `{code, message}` (règle 5), sur une route **publique**. Le consommateur prévu est une
    balise `<img>`, qui n'en lit pas le corps ; rien ne garantit qu'il restera le seul."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        vide = client.get(f"/api/v1/tournois/{tournoi_id}/identite/logos/evenement")

        assert vide.status_code == 404
        assert vide.json()["code"] == "logo_introuvable"


def test_un_corps_hors_de_proportion_est_refuse_sans_etre_ingere(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La coupure de sécurité de la frontière, **distincte** de la limite métier.

    Un fichier entre 512 Ko et 4 Mo est refusé par le domaine, qui sait dire « ce logo pèse 900 Ko,
    la limite est de 512 Ko » (422). Au-delà de 4 Mo, la frontière coupe avant de savoir de quoi il
    s'agit : 413, message muet. La première rédaction bufferisait **tout** le corps avant de
    comparer — 20 Mo mis en mémoire puis jetés, mesuré en revue."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        chemin = f"/api/v1/tournois/{tournoi_id}/identite/logos/club"

        metier = client.put(
            chemin, content=PNG + b"\x00" * (700 * 1024), headers={"Content-Type": "image/png"}
        )
        frontiere = client.put(
            chemin, content=b"\x00" * (5 * 1024 * 1024), headers={"Content-Type": "image/png"}
        )

        assert metier.status_code == 422, "la limite métier explique la limite"
        assert metier.json()["code"] == "logo_trop_volumineux"
        assert frontiere.status_code == 413, "la coupure de frontière ne regarde pas le contenu"
        assert frontiere.json()["code"] == "corps_hors_de_proportion"


def test_un_corps_chunke_hors_de_proportion_est_refuse_sans_content_length(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **La moitié de la garde que le test précédent n'exerce pas.**

    Envoyer des octets fait poser un `Content-Length` par le client : seule la première branche
    joue. Or `_lire_le_corps_borne` en a **deux**, et la seconde — le cumul en flux — existe
    précisément parce qu'un transfert **chunké** n'a pas d'en-tête de longueur. Mutation faite en
    revue : en retirant entièrement le cumul, la suite restait verte.

    Passer un itérateur fait basculer httpx en `Transfer-Encoding: chunked`.

    ⚠️ **Ce que ce test ne prouve PAS**, et le nom a été corrigé pour cesser de le promettre : le
    harnais de `TestClient` joint le générateur avant que l'application n'en voie un octet, donc la
    coupure n'a pas lieu « en cours de lecture ». Il prouve la **branche**, pas la propriété de
    mémoire bornée — laquelle demanderait une `Request` fabriquée à la main comptant ses appels à
    `receive`.
    """

    def flux() -> Iterator[bytes]:
        for _ in range(80):
            yield b"\x00" * 65536

    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
            content=flux(),
            headers={"Content-Type": "image/png"},
        )

        assert refus.status_code == 413, "sans Content-Length, c'est le cumul en flux qui coupe"
        assert refus.json()["code"] == "corps_hors_de_proportion"


def test_un_format_non_reconnu_est_refuse_sans_lire_le_corps(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le `Content-Type` se lit gratuitement : un corps hors de proportion **et** de format inconnu
    doit sortir en 422 (le format), pas en 413 (la taille) — preuve que le refus est arrivé avant
    l'ingestion."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/identite/logos/club",
            content=b"\x00" * (5 * 1024 * 1024),
            headers={"Content-Type": "image/jpeg"},
        )

        assert refus.status_code == 422, "le format décide avant que la taille n'ait à décider"
        assert refus.json()["code"] == "type_de_logo_refuse"


def test_l_empreinte_servie_change_avec_le_contenu(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Le bout de chaîne qui rend un logo remplacé visible.**

    Le front pose l'empreinte dans l'URL du logo : elle doit donc être **la même** que l'`ETag`
    servi par la route des octets (sinon les deux moitiés du cache parlent de valeurs différentes)
    et changer **exactement** quand le fichier change."""
    with TestClient(app_identite) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        chemin = f"/api/v1/tournois/{tournoi_id}/identite/logos/club"

        premier = client.put(chemin, content=PNG, headers={"Content-Type": "image/png"})
        empreinte_premier = premier.json()["logos"][0]["empreinte"]
        etag = client.get(chemin).headers["etag"]

        remplace = client.put(chemin, content=SVG, headers={"Content-Type": "image/svg+xml"})
        empreinte_remplace = remplace.json()["logos"][0]["empreinte"]

        assert etag == f'"{empreinte_premier}"', "l'ETag et l'URL disent la même version"
        assert empreinte_remplace != empreinte_premier, "remplacer le fichier change la version"


# ————————————————————————————————————————————————————————————————————————————————————————————————
# L'aperçu — le contrôle « à la saisie »


def test_l_apercu_decline_sans_rien_enregistrer(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """C'est ce qui permet le contrôle « à la saisie » sans dupliquer la dérivation côté navigateur.

    L'oracle du « sans rien enregistrer » : aucun tournoi n'est cité dans l'URL, donc il n'y a
    rien à écrire.
    """
    with TestClient(app_identite) as client:
        connecter_admin(client)

        apercu = client.get(
            "/api/v1/identite/apercu", params={"primaire": "#b71918", "secondaire": "#1d1d1b"}
        )

        assert apercu.status_code == 200, apercu.text
        rendu = apercu.json()
        assert rendu["primaire"]["sombre"]["contour"] == "#cc1c1b"
        assert rendu["primaire"]["contraste_sur_sombre"] == 2.55


def test_l_apercu_refuse_une_couleur_mal_formee(
    app_identite: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_identite) as client:
        connecter_admin(client)
        refus = client.get(
            "/api/v1/identite/apercu", params={"primaire": "#zzz", "secondaire": "#1d1d1b"}
        )
        assert refus.status_code == 422
        assert refus.json()["code"] == "couleur_invalide"


def test_l_apercu_demande_une_session(app_identite: FastAPI) -> None:
    """Contrairement à la lecture d'identité, l'aperçu est un outil de préparation : il n'a aucune
    raison d'être ouvert au public."""
    with TestClient(app_identite) as client:
        refus = client.get(
            "/api/v1/identite/apercu", params={"primaire": "#b71918", "secondaire": "#1d1d1b"}
        )
        assert refus.status_code == 401
