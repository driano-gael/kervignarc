"""Service applicatif Documents de salle (E09US008) — étiquettes de cible & cartes de scoreur.

Compose deux documents imprimables à partir de données **déjà préparées** (les codes existent : ils
sont émis par `ServicePostes.assurer_codes` pour les cibles, `ServiceScoreurs` pour les scoreurs) :

- `etiquettes_cibles` : un QR par cible du tournoi, encodant l'**URL de rattachement** du poste
  (E04US001) et portant le code en clair ;
- `cartes_scoreurs` : un papier par scoreur, avec son nom et son code personnel (E10US003).

Comme la feuille de marque, c'est une **lecture pure** (aucune écriture DB) : le service lit les
postes/scoreurs persistés via des **ports seuls** (jamais service→service — même parti que
`ServiceFeuilleDeMarque`) et délègue le rendu au port `GenerateurDocumentsSalle` (adapter ReportLab,
ADR-0031). Le service reste synchrone et pur d'infrastructure : il ne connaît ni HTTP, ni SQL, ni
ReportLab. Seule garde 404 : `TournoiIntrouvable`.

**Construction de l'URL** : le domaine ne sait pas construire une URL réseau ; c'est ici qu'on la
compose, à partir de l'**origine** de la requête admin (`request.base_url`, passée par l'API) et du
code — forme `…/?poste=<code>`, lue par le front (`frontend/src/features/poste/url.ts`). Générer
depuis `localhost` produit donc des QR pointant sur localhost, inutilisables sur les tablettes du
réseau local : c'est une limite assumée (# DETTE-012), acceptable car le jour J l'admin accède au
serveur par son IP réseau ; une base URL configurable relèvera de la mise en réseau (E11US001).
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.documents_salle import CarteScoreur, CartesScoreurs, EtiquetteCible, EtiquettesCibles
from domain.ports import (
    GenerateurDocumentsSalle,
    PosteRepository,
    ScoreurRepository,
    TournoiRepository,
)
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
        postes = sorted(self._postes.par_tournoi(tournoi_id), key=lambda poste: poste.cible_index)
        etiquettes = tuple(
            EtiquetteCible(
                cible_index=poste.cible_index,
                code=poste.code,
                url=_url_rattachement(origine, poste.code),
            )
            for poste in postes
        )
        return self._generateur.etiquettes_cibles(
            EtiquettesCibles(nom_tournoi=tournoi.nom, etiquettes=etiquettes)
        )

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
