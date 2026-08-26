"""Endpoints REST de l'**identité visuelle du tournoi** (`/api/v1`) — E16US006, ADR-0097.

Suit le patron de bout en bout : DTO Pydantic distincts du domaine (règle 6), **écritures** par la
file (writer unique, ADR-0005) sous `exiger_admin`, **lectures** hors boucle (threadpool), erreurs
typées traduites à la frontière.

**Deux lectures sont PUBLIQUES, et c'est délibéré** : l'identité déclinée et les octets d'un logo.
L'écran de salle et l'appli du spectateur en vivent, et il n'y a rien à protéger dans une couleur
projetée sur le mur d'un gymnase. Les écritures, elles, restent admin.

**Un logo monte en corps brut, pas en `multipart/form-data`.** `UploadFile` exigerait
`python-multipart`, qui n'est ni installé ni déclaré au manifeste — l'ajouter serait un arbitrage de
dépendance (règle 11), pour un gain nul ici : on téléverse **un** fichier sans aucun champ à côté.
Le corps est donc le fichier, et le `Content-Type` dit son format. Bonus non négligeable sur un
réseau de gymnase : pas les ~33 % d'inflation d'un encodage base64.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.erreurs import CorpsHorsDeProportion, LogoIntrouvable
from application.identite import AccentDecline, IdentiteDeclinee, ServiceIdentite, decliner
from domain.identite import (
    POIDS_LOGO_MAX_OCTETS,
    SEUIL_CONTOUR,
    SEUIL_TEXTE,
    Couleur,
    EmplacementLogo,
    IdentiteVisuelle,
    JetonsDeMarque,
    TypeLogo,
)
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["identite"])

# Le corps est lu **avant** toute validation de contenu : il faut donc une borne qui ne dépende pas
# du domaine, sinon un client hostile ferait grossir la mémoire du serveur en amont du refus. La
# marge sur `POIDS_LOGO_MAX_OCTETS` est volontaire — c'est le domaine qui rend le message utile («
# ce logo pèse 900 Ko, la limite est 512 Ko »), pas cette coupure de sécurité, qui doit rester
# muette et large. Elle est appliquée **pendant** la lecture, pas après : cf.
# `_lire_le_corps_borne`.
_PLAFOND_DE_LECTURE_OCTETS = 4 * 1024 * 1024


class JetonsReponse(BaseModel):
    """Les quatre jetons de marque d'un accent sur un thème — valeurs `#rrggbb` prêtes à poser.

    Les noms sont ceux de `frontend/src/index.css` (`--brand-surface`, `--brand-border`,
    `--brand-text`, `--sur-brand`) : le front transcrit, il ne traduit pas.
    """

    surface: str
    contour: str
    texte: str
    encre: str

    @staticmethod
    def de_jetons(jetons: JetonsDeMarque) -> JetonsReponse:
        """Traduit les jetons du domaine en DTO."""
        return JetonsReponse(
            surface=jetons.surface.hex,
            contour=jetons.contour.hex,
            texte=jetons.texte.hex,
            encre=jetons.encre.hex,
        )


class AccentReponse(BaseModel):
    """Un accent : la couleur choisie, ses deux déclinaisons, et ses deux contrastes **mesurés**.

    `contraste_sur_sombre` / `contraste_sur_clair` portent sur la couleur **brute**. C'est le
    chiffre de `P-4` — « une alerte qui ne chiffre pas son impact est un clic de plus, pas une
    protection » (`D-16`) : il dit à l'organisateur que *sa* couleur ne tiendrait pas en texte,
    pendant que les variantes livrées, elles, tiennent.
    """

    couleur: str
    sombre: JetonsReponse
    clair: JetonsReponse
    contraste_sur_sombre: float
    contraste_sur_clair: float

    @staticmethod
    def de_accent(accent: AccentDecline) -> AccentReponse:
        """Traduit un accent décliné en DTO. Les ratios sont arrondis au centième — c'est la
        précision publiée par la charte (« 2,55:1 »), et trois décimales de plus n'apprendraient
        rien à qui lit l'écran."""
        return AccentReponse(
            couleur=accent.couleur.hex,
            sombre=JetonsReponse.de_jetons(accent.sombre),
            clair=JetonsReponse.de_jetons(accent.clair),
            contraste_sur_sombre=round(accent.contraste_sur_sombre, 2),
            contraste_sur_clair=round(accent.contraste_sur_clair, 2),
        )


class LogoPresentReponse(BaseModel):
    """Un emplacement pourvu, et l'**empreinte** de ce qu'il contient.

    ⚠️ L'empreinte n'est pas décorative : c'est le segment de version que le front pose dans l'URL
    du logo. Une URL stable ne provoque aucune requête sur une image déjà montée — le navigateur ne
    consulte même pas son cache, donc `Cache-Control: no-cache` ne s'applique à rien — et un
    organisateur qui corrige son fichier ne le voyait jamais (relevé en revue, mesuré). Versionner
    par l'horloge de la requête, à l'inverse, retéléchargeait 512 Ko à chaque événement WebSocket.
    L'empreinte du **contenu** est la seule valeur qui tienne les deux bouts.
    """

    emplacement: str
    empreinte: str


class IdentiteReponse(BaseModel):
    """L'identité d'un tournoi, prête à appliquer.

    `reglee` à `false` **n'est pas un vide** : les accents rendus sont ceux du club, et l'écran doit
    dire « hérité de l'identité du club » plutôt que d'afficher un formulaire vierge.

    `seuil_contour` / `seuil_texte` voyagent avec la réponse plutôt que d'être recopiés côté front :
    ce sont les deux critères WCAG contre lesquels les ratios ci-dessus se lisent, et un front qui
    porterait sa propre copie pourrait annoncer « conforme » sur un seuil que le serveur n'applique
    plus.
    """

    reglee: bool
    primaire: AccentReponse
    secondaire: AccentReponse
    logos: list[LogoPresentReponse]
    seuil_contour: float
    seuil_texte: float
    poids_logo_max_octets: int
    """La limite de poids, servie plutôt que recopiée — même argument que les deux seuils.

    Le front s'en sert pour refuser un fichier hors limite **avant** de le faire traverser le Wi-Fi
    du gymnase. Une copie en dur y aurait annoncé une limite que le serveur n'applique plus, et dans
    le mauvais sens (copie trop petite) elle aurait interdit un dépôt que le serveur acceptait.
    """

    @staticmethod
    def de_identite(identite: IdentiteDeclinee) -> IdentiteReponse:
        """Traduit l'identité déclinée en DTO de réponse."""
        return IdentiteReponse(
            reglee=identite.reglee,
            primaire=AccentReponse.de_accent(identite.primaire),
            secondaire=AccentReponse.de_accent(identite.secondaire),
            # Trié pour que la réponse soit **stable** : un mappage n'a pas d'ordre garanti, et
            # deux requêtes identiques rendant deux ordres différents casseraient le cache
            # du client.
            logos=[
                LogoPresentReponse(emplacement=emplacement.value, empreinte=empreinte)
                for emplacement, empreinte in sorted(
                    identite.empreintes.items(), key=lambda paire: paire[0].value
                )
            ],
            seuil_contour=SEUIL_CONTOUR,
            seuil_texte=SEUIL_TEXTE,
            poids_logo_max_octets=POIDS_LOGO_MAX_OCTETS,
        )


class ReglerAccentsRequete(BaseModel):
    """Corps de réglage des deux accents — des saisies, validées par le domaine (`#RRGGBB`).

    `str` et non un type contraint par Pydantic : la règle de format appartient à
    `Couleur.depuis_hex` (règle 1), et la dupliquer en contrainte de DTO créerait deux définitions
    du mot « couleur » — dont une seule serait testée.
    """

    primaire: str
    secondaire: str


@router.get("/tournois/{tournoi_id}/identite", response_model=IdentiteReponse)
async def identite_du_tournoi(tournoi_id: int, request: Request) -> IdentiteReponse:
    """Identité déclinée d'un tournoi (**public**). `404` si le tournoi n'existe pas.

    Lecture pure, hors file d'écriture : threadpool.
    """
    service: ServiceIdentite = request.app.state.service_identite
    identite = await run_in_threadpool(service.pour_tournoi, tournoi_id)
    return IdentiteReponse.de_identite(identite)


@router.get("/identite/apercu", response_model=IdentiteReponse)
async def apercu_d_une_identite(
    primaire: str, secondaire: str, _: None = Depends(exiger_admin)
) -> IdentiteReponse:
    """Décline deux couleurs **sans les enregistrer** (**admin**) — le contrôle « à la saisie ».

    C'est ce qui permet à l'écran d'identité de montrer le rendu et le chiffre de contraste pendant
    que l'organisateur choisit, **sans** que le navigateur recalcule la dérivation. Route de calcul
    pur : aucun accès à la base, donc ni file d'écriture ni threadpool.

    ⚠️ `reglee` vaut `true` dans la réponse : les deux accents **sont** posés sur l'identité qu'on
    décline — c'est un aperçu de ce que donnerait l'enregistrement, pas un état persisté. La route
    ne cite aucun tournoi, ce qui suffit à dire que rien n'a été écrit.
    """
    identite = IdentiteVisuelle().avec_accents(
        Couleur.depuis_hex(primaire), Couleur.depuis_hex(secondaire)
    )
    return IdentiteReponse.de_identite(decliner(identite))


@router.put(
    "/tournois/{tournoi_id}/identite",
    response_model=IdentiteReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regler_les_accents(
    tournoi_id: int, requete: ReglerAccentsRequete, request: Request
) -> IdentiteReponse:
    """Enregistre les deux accents (**action admin**) : écriture via la file (ADR-0005).

    `422` sur une couleur mal formée, `409` sur un tournoi archivé, `404` sur un tournoi inconnu.
    **Aucun refus sur un contraste faible** (`P-4`) : le chiffre est rendu, pas opposé.
    """
    service: ServiceIdentite = request.app.state.service_identite
    write_queue: WriteQueue = request.app.state.write_queue
    identite = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.regler_accents(tournoi_id, requete.primaire, requete.secondaire)
        )
    )
    return IdentiteReponse.de_identite(identite)


@router.put(
    "/tournois/{tournoi_id}/identite/logos/{emplacement}",
    response_model=IdentiteReponse,
    dependencies=[Depends(exiger_admin)],
)
async def deposer_un_logo(
    tournoi_id: int, emplacement: EmplacementLogo, request: Request
) -> IdentiteReponse:
    """Dépose ou remplace un logo (**action admin**) : le **corps est le fichier**.

    Le format est lu dans l'en-tête `Content-Type` (`image/png` ou `image/svg+xml`). `422` sur un
    format non reconnu, un contenu qui dément le format annoncé, un SVG porteur de script, ou un
    fichier trop lourd — tous les refus viennent du **domaine** (`TypeLogo.depuis_entete`,
    `Logo.deposer`), aucun n'est réécrit ici. `413` si le corps dépasse la coupure de sécurité de la
    frontière, qui est une autre affaire que la limite métier (cf. `_lire_le_corps_borne`).
    """
    # ⚠️ Le **type d'abord**, le corps ensuite. L'ordre inverse — celui de la rédaction
    # précédente — accumulait jusqu'à 4 Mo en mémoire pour refuser sur un en-tête qui était lisible
    # gratuitement. C'est la même famille de défaut que celle qu'on venait de corriger un cran plus
    # haut (« la borne s'appliquait après l'ingestion »), appliquée à moitié. Effet voulu : un gros
    # corps de format non reconnu rend 422 (le format *est* invalide, on l'a su sans rien lire) au
    # lieu de 413.
    type_logo = TypeLogo.depuis_entete(request.headers.get("content-type"))
    contenu = await _lire_le_corps_borne(request)
    service: ServiceIdentite = request.app.state.service_identite
    write_queue: WriteQueue = request.app.state.write_queue
    identite = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.deposer_logo(tournoi_id, emplacement, contenu, type_logo)
        )
    )
    return IdentiteReponse.de_identite(identite)


@router.delete(
    "/tournois/{tournoi_id}/identite/logos/{emplacement}",
    response_model=IdentiteReponse,
    dependencies=[Depends(exiger_admin)],
)
async def retirer_un_logo(
    tournoi_id: int, emplacement: EmplacementLogo, request: Request
) -> IdentiteReponse:
    """Vide un emplacement de logo (**action admin**). **Idempotent** : `200` même s'il était
    vide."""
    service: ServiceIdentite = request.app.state.service_identite
    write_queue: WriteQueue = request.app.state.write_queue
    identite = await asyncio.wrap_future(
        write_queue.submit(lambda: service.retirer_logo(tournoi_id, emplacement))
    )
    return IdentiteReponse.de_identite(identite)


@router.get("/tournois/{tournoi_id}/identite/logos/{emplacement}")
async def logo_du_tournoi(
    tournoi_id: int, emplacement: EmplacementLogo, request: Request
) -> Response:
    """Sert les octets d'un logo (**public**). `404` si l'emplacement est vide.

    ⚠️ **Les trois en-têtes de sûreté ne sont pas décoratifs.** Un SVG est un document : servi
    depuis l'origine de l'application — celle qui sert aussi la SPA d'administration —, il
    partagerait sa session. Le domaine refuse déjà ce qui exécute (`Logo.deposer`) ; ces en-têtes
    sont la **seconde barrière**, celle qui tient si un fichier est entré par une version antérieure
    des règles :

    - `Content-Security-Policy: default-src 'none'` — le document ne peut charger ni exécuter rien ;
    - `X-Content-Type-Options: nosniff` — le navigateur ne réinterprète pas le type annoncé ;
    - `Content-Disposition: inline` sans nom de fichier — rien de ce qu'a saisi l'organisateur ne se
      retrouve dans un en-tête.

    L'`ETag` évite de renvoyer 512 Ko à chaque rafraîchissement de l'écran de salle. Il est calculé
    sur le contenu (SHA-256 tronqué), donc il **change** dès qu'on remplace le logo : un
    organisateur qui corrige son fichier le voit sans vider son cache.
    """
    service: ServiceIdentite = request.app.state.service_identite
    logo = await run_in_threadpool(service.logo, tournoi_id, emplacement)
    if logo is None:
        # Le contrat `{code, message}` (règle 5) vaut aussi ici : c'est une route **publique**, et
        # un 404 nu était la seule réponse du module hors format. Le consommateur prévu est une
        # balise `<img>`, qui n'en lit pas le corps — mais rien ne garantit qu'il restera le seul.
        raise LogoIntrouvable("Aucun logo à cet emplacement.")

    # L'empreinte est celle du domaine, la même que celle servie dans `/identite` : les deux
    # bouts de la chaîne de cache parlent donc de la même valeur, et le front peut construire une
    # URL qui change exactement quand l'`ETag` change.
    etag = f'"{logo.empreinte}"'
    if _etag_deja_connu(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=_entetes_du_logo(etag))
    return Response(
        content=logo.contenu,
        media_type=logo.type_logo.value,
        headers=_entetes_du_logo(etag),
    )


def _entetes_du_logo(etag: str) -> dict[str, str]:
    """Les gardes posées sur **toute** réponse de la route, 304 compris.

    Écrites d'un seul endroit plutôt que sur la seule réponse complète : le 304 en sortait nu, et si
    la RFC 9111 §4.3.4 fait bien conserver au cache les champs qu'un 304 ne remplace pas — donc pas
    de fenêtre réelle —, le raisonnement n'était écrit nulle part et la seule réponse du module à
    sortir sans le trio était justement celle que sa docstring déclare « pas décoratif ».
    """
    return {
        "ETag": etag,
        "Cache-Control": "no-cache",
        "Content-Security-Policy": "default-src 'none'",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
    }


def _etag_deja_connu(entete: str | None, etag: str) -> bool:
    """`If-None-Match` porte une **liste**, et ses entrées peuvent être faibles (`W/"…"`).

    Une égalité stricte sur la chaîne entière — la rédaction précédente — retombait en 200 complet
    dès qu'un intermédiaire ajoutait une entrée ou préfixait la validation : jusqu'à 512 Ko de plus
    par tablette, pour un fichier que le client avait déjà.
    """
    if entete is None:
        return False
    proposees = {valeur.strip().removeprefix("W/") for valeur in entete.split(",")}
    return etag in proposees or "*" in proposees


async def _lire_le_corps_borne(request: Request) -> bytes:
    """Lit le corps de la requête **en s'arrêtant** au plafond, au lieu de le borner après coup.

    ⚠️ La première rédaction écrivait `contenu = await request.body()` *puis* comparait la longueur
    au plafond. Or `Request.body()` accumule **tout** le flux avant de rendre la main : la borne
    était évaluée sur un tampon déjà constitué, et un dépôt de 20 Mo était bel et bien mis en
    mémoire avant d'être refusé (mesuré en revue adversariale). Le commentaire, lui, promettait
    l'inverse — une fausse garantie coûte plus cher qu'une garantie absente, parce qu'elle empêche
    le lecteur suivant de poser la vraie.

    Deux contrôles et non un : `Content-Length` refuse sans lire une seule fois qu'il est annoncé,
    et le cumul en flux couvre le transfert **chunké**, où l'en-tête est absent. La route est
    derrière `exiger_admin`, donc seul un poste d'organisateur peut déclencher le cas — mais c'est
    le serveur **unique** du gymnase, écrans de salle compris, qui en paierait la mémoire.
    """
    annonce = request.headers.get("content-length")
    if annonce is not None and annonce.isdigit() and int(annonce) > _PLAFOND_DE_LECTURE_OCTETS:
        raise CorpsHorsDeProportion("Corps de requête hors de proportion.")
    morceaux = bytearray()
    async for morceau in request.stream():
        morceaux.extend(morceau)
        if len(morceaux) > _PLAFOND_DE_LECTURE_OCTETS:
            raise CorpsHorsDeProportion("Corps de requête hors de proportion.")
    return bytes(morceaux)
