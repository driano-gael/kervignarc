"""Documents de salle (QR des postes, cartes scoreurs) — **lecture pure**, ports seuls.

⚠️ **L'URL du QR est composée depuis l'origine de la requête admin** : générer depuis `localhost`
produit des QR inutilisables sur les tablettes du réseau. Limite assumée — `DETTE-012` — acceptable
parce que le jour J l'admin accède au serveur par son IP réseau. ADR-0031
"""

from __future__ import annotations

from application.erreurs import PosteIntrouvable, ScoreurIntrouvable, TournoiIntrouvable
from domain.documents_salle import CarteScoreur, CartesScoreurs, EtiquetteCible, EtiquettesCibles
from domain.ports import (
    GenerateurDocumentsSalle,
    PosteRepository,
    ScoreurRepository,
    TournoiRepository,
)
from domain.poste import TypePoste
from domain.scoreur import ScoreurId
from domain.tournoi import Tournoi, TournoiId


class ServiceDocumentsSalle:
    """Cas d'usage : composer et rendre les supports d'identité à imprimer avant le jour J."""

    def __init__(
        self,
        tournois: TournoiRepository,
        postes: PosteRepository,
        scoreurs: ScoreurRepository,
        generateur: GenerateurDocumentsSalle,
    ) -> None:
        self._tournois = tournois
        self._postes = postes
        self._scoreurs = scoreurs
        self._generateur = generateur

    def etiquettes_cibles(self, tournoi_id: TournoiId, origine: str) -> bytes:
        """Rend en PDF les étiquettes de cible (un QR par cible : URL de rattachement + code clair).

        `origine` est l'origine réseau du serveur (p. ex. `str(request.base_url)`) : l'URL encodée
        est `{origine}/?poste=<code>`. Lève `TournoiIntrouvable` si le tournoi n'existe pas ;
        document **vide** (aucune étiquette) tant qu'aucune cible n'a été préparée. Étiquettes
        triées par numéro de cible (ordre physique de la salle).
        """
        tournoi = self._verifier_tournoi(tournoi_id)
        # `par_tournoi_et_type` et non `par_tournoi` : depuis E07US004, ce dernier rend aussi les
        # écrans de salle, qui n'ont pas de cible à étiqueter (leur code se distribue autrement).
        postes = sorted(
            self._postes.par_tournoi_et_type(tournoi_id, TypePoste.CIBLE),
            key=lambda poste: poste.cible(),
        )
        etiquettes = tuple(
            EtiquetteCible(
                cible_index=poste.cible(),
                code=poste.code,
                url=_url_rattachement(origine, poste.code),
            )
            for poste in postes
        )
        return self._generateur.etiquettes_cibles(
            EtiquettesCibles(nom_tournoi=tournoi.nom, etiquettes=etiquettes)
        )

    def qr_rattachement(self, tournoi_id: TournoiId, cible_index: int, origine: str) -> bytes:
        """Rend en **SVG** le seul QR de rattachement de la cible `cible_index` (E11US008).

        Pendant **à l'écran** de l'étiquette imprimée : même URL encodée (`{origine}/?poste=<code>`)
        que `etiquettes_cibles`, pour rattacher une tablette sans passer par le PDF (admin « Postes
        de cible »). Lève `TournoiIntrouvable` si le tournoi n'existe pas, `PosteIntrouvable` si
        aucune cible ne porte ce numéro dans ce tournoi (même parti « hors-tournoi = inexistant »
        que les autres gardes 404).
        """
        self._verifier_tournoi(tournoi_id)
        # `par_tournoi_et_type` et non `par_tournoi` : le port réserve ce dernier à qui veut
        # vraiment l'ensemble (la console de supervision). Sans effet observable ici — un écran a
        # `cible_index` nul, donc ne matche jamais — mais c'est le contrat que cette US vient
        # d'écrire, et le laisser violé dans le même diff est le meilleur moyen qu'il ne tienne pas.
        poste = next(
            (
                p
                for p in self._postes.par_tournoi_et_type(tournoi_id, TypePoste.CIBLE)
                if p.cible_index == cible_index
            ),
            None,
        )
        if poste is None:
            raise PosteIntrouvable(
                f"Aucune cible {cible_index} préparée dans le tournoi {tournoi_id}."
            )
        # Même # DETTE-012 que l'étiquette PDF : `origine` = origine de la requête admin, faute de
        # base URL publique configurée — d'où l'intérêt d'ouvrir l'admin par l'IP LAN (E11US008).
        return self._generateur.qr_rattachement(_url_rattachement(origine, poste.code))

    def qr_scoreur(self, tournoi_id: TournoiId, scoreur_id: ScoreurId, origine: str) -> bytes:
        """Rend en **SVG** le QR de rattachement d'un scoreur (E16US015), jumeau du QR de cible.

        Même port, même forme d'URL — `{origine}/?scoreur=<code>` — que `qr_rattachement`, à ceci
        près que le code encodé est un secret **personnel** : d'où la garde d'appartenance
        ci-dessous, plus stricte que celle d'une cible. Lève `TournoiIntrouvable` si le tournoi
        n'existe pas, `ScoreurIntrouvable` sinon.
        """
        self._verifier_tournoi(tournoi_id)
        scoreur = self._scoreurs.par_id(scoreur_id)
        # ⚠️ `par_id` ne filtre PAS par tournoi (le code est unique dans toute la base, cf. le port
        # `ScoreurRepository`) : sans ce test d'appartenance, l'admin d'un tournoi obtiendrait le
        # QR — donc le code personnel — d'un scoreur d'un AUTRE tournoi. Le jumeau cible n'a pas
        # ce risque, il interroge un repository déjà borné au tournoi.
        if scoreur is None or scoreur.tournoi_id != tournoi_id:
            raise ScoreurIntrouvable(
                f"Aucun scoreur d'identifiant {scoreur_id} dans le tournoi {tournoi_id}."
            )
        return self._generateur.qr_rattachement(_url_scoreur(origine, scoreur.code))

    def cartes_scoreurs(self, tournoi_id: TournoiId) -> bytes:
        """Rend en PDF les cartes de scoreur (un papier par scoreur : nom + code personnel).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas ; document **vide** tant qu'aucun
        scoreur n'est défini. Cartes triées par nom (comme `ServiceScoreurs.lister`).
        """
        tournoi = self._verifier_tournoi(tournoi_id)
        scoreurs = sorted(self._scoreurs.par_tournoi(tournoi_id), key=lambda s: s.nom.casefold())
        cartes = tuple(CarteScoreur(nom=scoreur.nom, code=scoreur.code) for scoreur in scoreurs)
        return self._generateur.cartes_scoreurs(
            CartesScoreurs(nom_tournoi=tournoi.nom, cartes=cartes)
        )

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> Tournoi:
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi


def _url_rattachement(origine: str, code: str) -> str:
    """URL de rattachement d'un poste : `{origine}/?poste=<code>`, sans `//` parasite.

    Le front lit le paramètre de query `poste` à la racine (`frontend/src/features/poste/url.ts`).
    Les codes sont tirés d'un alphabet URL-safe (sans confondables) : aucun échappement nécessaire.
    """
    # DETTE-012 : `origine` est l'origine de la requête admin (`request.base_url`), faute de base
    # URL publique configurée. Correct dans le flux réel (IP réseau le jour J), faux depuis
    # `localhost`. Résorption : base URL configurable en E11US001 (mise en réseau).
    return f"{origine.rstrip('/')}/?poste={code}"


def _url_scoreur(origine: str, code: str) -> str:
    """URL de session d'un scoreur : `{origine}/scoreur?code=<code>` (E16US015).

    ⚠️ **Forme volontairement différente** de `_url_rattachement`, qui vise la racine : celle-ci
    nomme le **monde** dans le chemin (`/scoreur`, ADR-0059), si bien que le routeur d'adresses
    aiguille seul — aucune règle à ajouter à `resoudreRole`, le cœur risqué de l'entrée (ADR-0042).
    Le code reste en query, lu par `frontend/src/features/scoreur-session/url.ts`.
    """
    # Même DETTE-012 que l'URL de poste : `origine` est l'origine de la requête admin.
    return f"{origine.rstrip('/')}/scoreur?code={code}"
