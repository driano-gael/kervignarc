"""Identité visuelle — la dérivation des accents est **reproductible** (`DV-05`, ADR-0097).
Teinte et saturation conservées, clarté ajustée jusqu'au seuil AA : donc du domaine, testable
sans navigateur.

⚠️ **Les accents pilotent les jetons de MARQUE, jamais le fond ni le sémantique.** `index.css`
mesure chaque couleur contre `--surface-0` : repeindre le fond par tournoi invaliderait d'un coup
les vingt ratios de la charte, sans qu'aucun test ne bouge.
"""

from __future__ import annotations

import colorsys
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType

from domain.erreurs import CouleurInvalide, LogoTropVolumineux, TypeDeLogoRefuse

# Seuils WCAG 2.1, cités par leur critère parce que ce sont deux exigences **différentes** et non
# deux niveaux du même : 1.4.11 (Non-text Contrast) régit ce qui se contourne, 1.4.3 (Contrast
# Minimum) ce qui se lit. `charte.test.ts` fait déjà cette distinction entre `--border` (4,04:1,
# actionnable) et `--border-subtle` (1,55:1, décoratif, sans exigence).
SEUIL_CONTOUR = 3.0
"""Contraste minimal d'un contour d'élément d'interface (WCAG 1.4.11)."""

SEUIL_TEXTE = 4.5
"""Contraste minimal d'un texte de corps (WCAG 1.4.3, niveau AA)."""

_MOTIF_HEX = re.compile(r"\A#?([0-9a-fA-F]{6})\Z")


@dataclass(frozen=True)
class Couleur:
    """Une couleur sRGB opaque, sur trois octets. Value object pur et immuable.

    Pas de forme courte (`#F00`) ni de notation CSS : **une écriture, une valeur**. Accepter
    plusieurs formes obligerait à décider si `#F00` et `#FF0000` désignent la même identité au
    moment de comparer deux tournois, et rouvrirait côté serveur la porte que `charte.test.ts` a
    fermée côté front (les notations `rgb()`, `hsl()`, `oklch()` y sont traquées).
    """

    r: int
    g: int
    b: int

    @staticmethod
    def depuis_hex(saisie: str) -> Couleur:
        """Lit `#RRGGBB` (dièse facultatif, casse et espaces de bord indifférents).

        Lève `CouleurInvalide` sur toute autre forme — c'est une saisie d'organisateur, elle se
        valide à la frontière du domaine et pas dans un `<input type="color">` qu'un client peut
        contourner.
        """
        trouve = _MOTIF_HEX.match(saisie.strip())
        if trouve is None:
            raise CouleurInvalide(
                f"« {saisie.strip()} » n'est pas une couleur : attendu six chiffres hexadécimaux, "
                "par exemple #B71918."
            )
        chiffres = trouve.group(1)
        return Couleur(r=int(chiffres[0:2], 16), g=int(chiffres[2:4], 16), b=int(chiffres[4:6], 16))

    @property
    def hex(self) -> str:
        """Forme normalisée `#rrggbb`, minuscule — la seule qui sorte d'ici."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    @property
    def teinte(self) -> float:
        """Teinte HSL en degrés `[0, 360[`. Sert au garde-fou « la dérivation garde la marque »."""
        h, _, _ = colorsys.rgb_to_hls(self.r / 255, self.g / 255, self.b / 255)
        return h * 360

    @property
    def luminance_relative(self) -> float:
        """Luminance relative WCAG 2.1 (§ *relative luminance*), dans `[0, 1]`.

        La linéarisation par canal (`/12,92` sous le coude, puissance 2,4 au-dessus) n'est pas
        décorative : sans elle, le ratio d'un rouge saturé sort faux d'un facteur deux, et l'écran
        annoncerait un chiffre rassurant à un organisateur qui n'a aucun moyen de le recouper.
        """
        return sum(
            coefficient * _linearise(canal / 255)
            for coefficient, canal in ((0.2126, self.r), (0.7152, self.g), (0.0722, self.b))
        )


def _linearise(canal: float) -> float:
    """Convertit un canal sRGB `[0, 1]` en valeur linéaire (WCAG 2.1)."""
    return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4


def contraste(a: Couleur, b: Couleur) -> float:
    """Ratio de contraste WCAG 2.1 entre deux couleurs, dans `[1, 21]`.

    **Symétrique** : la formule `(L1 + 0,05) / (L2 + 0,05)` veut L1 la plus claire. Ne pas trier
    renverrait l'inverse du ratio une fois sur deux — une couleur illisible passerait alors pour
    conforme selon l'ordre des arguments.
    """
    claire, sombre = sorted((a.luminance_relative, b.luminance_relative), reverse=True)
    return (claire + 0.05) / (sombre + 0.05)


@dataclass(frozen=True)
class JetonsDeMarque:
    """Ce qu'un accent devient, une fois posé sur un fond donné — la strate « marque » de `DV-06`.

    Quatre jetons et non un, parce que `DV-04` a montré qu'un seul ne peut pas tenir trois usages :
    le rouge du club est **utilisable en aplat** (2,55:1 suffit à voir une surface) et
    **inutilisable en texte** sur le même fond. ⚠️ La correspondance vers `index.css` est écrite
    ici, une seule fois — `surface`→`--brand-surface`, `contour`→`--brand-border`,
    `texte`→`--brand-text`, `encre`→`--sur-brand` : deux des quatre changent de mot.
    """

    surface: Couleur
    """L'aplat : la couleur **exacte** de l'organisateur (`DV-05`). Jamais corrigée."""

    contour: Couleur
    """Variante atteignant `SEUIL_CONTOUR` sur le fond — `--brand-border`."""

    texte: Couleur
    """Variante atteignant `SEUIL_TEXTE` sur le fond — `--brand-text`."""

    encre: Couleur
    """Ce qui s'écrit **sur** l'aplat : noir ou blanc — `--sur-brand`."""


# Fonds de référence : les `--surface-0` des deux thèmes de `index.css`. La dérivation dépend du
# fond, donc elle se fait **deux fois** — « en thème sombre et clair », dit le CA. Un accent qui ne
# serait décliné que sur le sombre s'effondrerait sur le poste d'un bénévole ayant choisi le clair.
FOND_SOMBRE = Couleur(r=0x1D, g=0x1D, b=0x1B)
"""Anthracite de la banderole du club (`DV-02`) — fond du thème par défaut."""

FOND_CLAIR = Couleur(r=0xFF, g=0xFF, b=0xFF)
"""Blanc — fond du thème clair."""

_NOIR = Couleur(r=0, g=0, b=0)
_BLANC = Couleur(r=0xFF, g=0xFF, b=0xFF)

# Pas assez fin, la recherche saute la valeur juste ; trop fin, elle ne change rien (la sortie est
# quantifiée sur 8 bits de toute façon). 1/1024 garantit qu'aucune couleur 8 bits atteignable n'est
# enjambée : deux clartés distinctes d'un même octet sont plus éloignées que ce pas.
_PAS_DE_CLARTE = 1 / 1024


def deriver_marque(accent: Couleur, fond: Couleur) -> JetonsDeMarque:
    """Décline un accent en ses quatre jetons de marque sur un fond donné.

    Applique `DV-05` à la lettre : **l'aplat garde la couleur exacte**, seules les variantes de
    contour et de texte sont ajustées, et uniquement en **clarté** — la teinte et la saturation de
    l'organisateur sont sa marque. C'est aussi ce qui empêche la solution paresseuse : « atteindre
    4,5:1 » se satisfait de renvoyer du blanc. Le contrôle est **non bloquant** (`P-4`) : l'accent
    trop faible est accepté, décliné, et le chiffre de son échec rendu à l'écran.
    """
    return JetonsDeMarque(
        surface=accent,
        contour=_ajuster_clarte(accent, fond, SEUIL_CONTOUR),
        texte=_ajuster_clarte(accent, fond, SEUIL_TEXTE),
        encre=_BLANC if contraste(_BLANC, accent) >= contraste(_NOIR, accent) else _NOIR,
    )


def _ajuster_clarte(couleur: Couleur, fond: Couleur, seuil: float) -> Couleur:
    """Éloigne `couleur` de `fond` **en clarté seulement**, jusqu'au premier pas qui tient `seuil`.

    1. **Une couleur déjà conforme n'est pas touchée** : en thème clair le rouge du club atteint
       6,63:1, et la charte livrée donne bien la même valeur à ses trois jetons de marque.
    2. **Le sens se décide par les extrêmes** — on compare ce que donnent le blanc et le noir sur
       ce fond. Sur l'anthracite, descendre vers le noir n'atteindrait jamais 3:1.
    3. **Le seuil est vérifié sur la couleur ARRONDIE** : c'est celle qui est livrée.
    """
    if contraste(couleur, fond) >= seuil:
        return couleur

    vers_le_clair = contraste(_BLANC, fond) >= contraste(_NOIR, fond)
    teinte, clarte, saturation = colorsys.rgb_to_hls(
        couleur.r / 255, couleur.g / 255, couleur.b / 255
    )

    pas = _PAS_DE_CLARTE if vers_le_clair else -_PAS_DE_CLARTE
    for indice in range(1, int(1 / _PAS_DE_CLARTE) + 1):
        candidate = _depuis_hls(teinte, min(1.0, max(0.0, clarte + indice * pas)), saturation)
        if contraste(candidate, fond) >= seuil:
            return candidate

    # Inatteignable : à clarté 1 (blanc) ou 0 (noir), la direction retenue est par construction
    # celle qui maximise le contraste sur ce fond, et `#ffffff` sur `#1d1d1b` vaut 16,88:1 comme
    # `#000000` sur `#ffffff` vaut 21:1 — les deux dépassent 4,5. Le repli est là pour que la
    # fonction reste totale, pas parce qu'un cas y mène.
    return _BLANC if vers_le_clair else _NOIR


def _depuis_hls(teinte: float, clarte: float, saturation: float) -> Couleur:
    """Reconstruit une couleur 8 bits depuis un triplet HLS."""
    r, g, b = colorsys.hls_to_rgb(teinte, clarte, saturation)
    return Couleur(r=round(r * 255), g=round(g * 255), b=round(b * 255))


# ————————————————————————————————————————————————————————————————————————————————————————————————
# Les logos


class TypeLogo(str, Enum):
    """Les deux seuls formats acceptés — la valeur **est** le type MIME servi par l'API."""

    SVG = "image/svg+xml"
    PNG = "image/png"

    @staticmethod
    def depuis_entete(entete: str | None) -> TypeLogo:
        """Lit le format dans un `Content-Type` ; lève `TypeDeLogoRefuse` (→ 422) sur tout autre.

        Le paramétrage éventuel (`; charset=utf-8`) est coupé : c'est le type médiatique seul qui
        décide. ⚠️ **Ici et non dans le routeur** : « quels formats de logo le tournoi accepte »
        est une règle du domaine, pas une convention HTTP — et l'API qui la portait levait une
        `DomainError` de sa propre initiative, ce que la règle 5 proscrit.
        """
        type_medium = (entete or "").split(";")[0].strip().lower()
        for type_logo in TypeLogo:
            if type_logo.value == type_medium:
                return type_logo
        raise TypeDeLogoRefuse(
            f"Format « {type_medium or 'non précisé'} » non accepté : déposez un PNG ou un SVG."
        )


class EmplacementLogo(str, Enum):
    """Les deux marques d'un tournoi (questionnaire A05 : « un champ **de plus** »).

    Deux emplacements **nommés** et non une liste : déposer le logo du club ne remplace pas celui de
    l'événement, et chacun a sa place à l'écran. La valeur sert de segment d'URL.
    """

    EVENEMENT = "evenement"
    CLUB = "club"


POIDS_LOGO_MAX_OCTETS = 512 * 1024
"""Borne **inclusive** du poids d'un logo.

Le fichier est stocké en base (arbitrage du 25/08/2026, ADR-0097) : son poids passe donc par la file
d'écriture unique (règle 7) et voyage dans chaque sauvegarde du `.db`. 512 Ko laissent passer très
largement un SVG de charte et un PNG raisonnable, et arrêtent la photo de téléphone que l'arbitrage
`Q-UX10` a mise hors périmètre.
"""

_SIGNATURE_PNG = b"\x89PNG\r\n\x1a\n"
# Le bloc de fin d'un PNG : longueur nulle, type `IEND`, CRC constant (le bloc est vide).
_FIN_PNG = b"\x00\x00\x00\x00IEND\xaeB\x60\x82"

# ————————————————————————————————————————————————————————————————————————————————————————————————
# Ce qui, dans un SVG, **exécute** — ou permet d'y amener quelque chose qui exécute.
#
# ⚠️ **Une denylist perd par défaut, et celle-ci l'a perdu deux fois.** Les motifs ci-dessous sont
# la TROISIÈME rédaction : la deuxième était écrite sur des balises **non préfixées**, si bien que
# `<svg:script>` franchissait l'ensemble. Sept charges ont été déposées ET servies en 200 par le
# relecteur adversarial. La leçon vaut plus que les motifs : **un durcissement qui n'est pas
# attaqué déplace le trou au lieu de le fermer.**

# La barrière **porteuse** reste ailleurs : les en-têtes de la route de service
# (`Content-Security-Policy: default-src 'none'`, `nosniff`) et le rendu en `<img>`. Ces motifs
# sont la première des trois, jamais la seule — et ils ne doivent pas refuser un logo honnête :
# chaque clause ci-dessous a son contre-exemple **accepté** dans `test_domain_identite.py` (texte
# accentué échappé, `&copy;`, `<use href="#symbole">`, le `<!ENTITY>` d'Illustrator).

# Un nom d'élément peut porter n'importe quel préfixe de namespace : c'est le nom **local** qui
# décide. La borne est « tout ce qui n'est pas un délimiteur, suivi de `:` » et non une classe de
# caractères énumérée — la 3ᵉ rédaction exigeait `[a-z]` en tête, ce qui laissait passer
# `<_x:script>`
# et `<é:script>`, deux préfixes que XML autorise (`NCNameStartChar`). Réénumérer la grammaire,
# c'est
# se tromper une fois de plus ; ne rien exiger avant le `:` ne coûte aucun faux positif, puisque le
# nom local, lui, reste vérifié.
_PREFIXE_XML = rb"(?:[^\s<>/=\"']{1,64}:)?"

_MOTIF_SVG_EXECUTABLE = re.compile(
    # Exécution directe, retour au HTML, et animation SMIL qui **écrit** un attribut sans jamais en
    # porter la syntaxe (`<set attributeName="onload" to="…">`). `animate[a-z]*` plutôt que trois
    # noms : `<animateMotion>` échappait au `\b` qui suivait `animate`.
    rb"<\s*" + _PREFIXE_XML + rb"(?:script|foreignobject|set|handler|animate[a-z]*)\b"
    # Un gestionnaire d'événement. Borne gauche « tout caractère non identifiant » et non une liste
    # de trois : `<svg/onload="…">` est valide en XML et passait la liste.
    rb"|[^\w-]on[a-z]+\s*="
    rb"|attributename\s*="
    # `@import` dans un `<style>` charge une feuille tierce sans balise suspecte.
    rb"|@\s*import"
    # `javascript:` — les caractères de contrôle intercalés sont retirés par l'analyseur d'URL du
    # navigateur, donc `java\nscript:` s'exécute et `javascript\s*:` ne le voyait pas.
    rb"|j[\s\x00-\x20]*a[\s\x00-\x20]*v[\s\x00-\x20]*a[\s\x00-\x20]*s"
    rb"[\s\x00-\x20]*c[\s\x00-\x20]*r[\s\x00-\x20]*i[\s\x00-\x20]*p[\s\x00-\x20]*t[\s\x00-\x20]*:",
    re.IGNORECASE,
)

# **Toute** référence qui sort du fichier, quel que soit l'élément qui la porte.
#
# ⚠️ Ancrer le contrôle sur `<use …>` / `<image …>` avec un `[^>]*?` laissait passer un `>`
# **littéral** dans une valeur d'attribut (`<use aria-label="a>b" href="http://…">`, déposé et
# servi en revue). Chercher la **valeur** plutôt que l'élément est plus simple et strictement plus
# fort — cela couvre aussi `<a href>`, `<feImage>`, `<textPath>`.

# Deux formes restent admises, celles d'un export vectoriel honnête : le **fragment local**
# (`#symbole`) et le **raster embarqué** (`data:image/png;base64,…`). `data:image/svg+xml` n'en fait
# pas partie : c'est un document, pas une image. Le `\s*` vit **dans** le lookahead — consommé, il
# laissait le moteur reculer et faire matcher `href=" #symbole"`, un faux refus.
_MOTIF_REFERENCE_EXTERNE = re.compile(
    rb"(?:xlink:)?href\s*=\s*[\"']"
    rb"(?!\s*#)(?!\s*data:image/(?:png|jpe?g|gif|webp|bmp)[;,])"
    rb"|url\(\s*[\"']?\s*(?!#)(?!data:image/(?:png|jpe?g|gif|webp|bmp)[;,])(?=\w+:)",
    re.IGNORECASE,
)

# Une **référence de caractère** numérique. On ne les refuse pas — un projet français en produit
# légitimement — on les DÉCODE avant de rechercher ce qui exécute : le parseur XML fait exactement
# cela, et une recherche sur les octets bruts arrivait donc toujours trop tard.
_MOTIF_REFERENCE_NUMERIQUE = re.compile(rb"&#(x[0-9a-f]+|[0-9]+);", re.IGNORECASE)

# Une **entité générale interne**, déclarée avec une valeur littérale. Illustrator en produit
# (`<!ENTITY ns_extend "http://ns.adobe.com/…">`) : on ne les refuse donc pas, on les **développe**
# avant de chercher ce qui exécute, comme les références numériques.
#
# ⚠️ Refuser toute entité puis cesser de le faire **sans ajouter le développement** laissait passer
# une charge répartie sur deux entités (`&a;&b;`) : `javascript:` n'apparaît alors nulle part dans
# les octets, et le parseur la reconstitue à l'affichage. Une seule passe, jamais récursive —
# développer des entités qui se référencent rouvrirait *billion laughs*.
_MOTIF_ENTITE_INTERNE = re.compile(rb"<!\s*ENTITY\s+([^\s<>]+)\s+[\"']([^\"']*)[\"']\s*>")
_MOTIF_APPEL_D_ENTITE = re.compile(rb"&([^\s;&<>]{1,64});")

# Le vecteur XXE est l'identifiant **externe** : `<!ENTITY xxe SYSTEM "file:///etc/passwd">` fait
# lire un fichier du serveur. Une entité déclarée avec une valeur littérale, elle, est développée
# ci-dessus plutôt que refusée — c'est celle qu'Illustrator écrit.
_MOTIF_ENTITE_EXTERNE = re.compile(rb"<!\s*ENTITY\b[^>]*\b(?:SYSTEM|PUBLIC)\b", re.IGNORECASE)

# Un `<!DOCTYPE … SYSTEM "http://…">` fait charger une DTD tierce. Le `PUBLIC "-//W3C//DTD SVG
# 1.1//EN" "…"` d'Illustrator, lui, reste accepté : c'est la forme normalisée, et son identifiant
# système n'est utilisé qu'à défaut du public.
_MOTIF_DOCTYPE_EXTERNE = re.compile(rb"<!\s*DOCTYPE\b[^>\[]*\bSYSTEM\b", re.IGNORECASE)


@dataclass(frozen=True)
class Logo:
    """Un fichier de logo déposé, avec son format. Value object immuable.

    ⚠️ **Un SVG est un document, pas une image.** Servi depuis l'origine de l'application, un SVG
    porteur de script s'exécuterait avec la session de qui l'ouvre — on **refuse le fichier**. ⚠️
    Ce refus est une **denylist** : elle attrape ce qu'elle connaît. La barrière **porteuse** est
    la CSP et le `nosniff` de la route qui sert les octets — c'est elle qu'il faudra reporter le
    jour où un logo sera rendu autrement.
    """

    contenu: bytes
    type_logo: TypeLogo

    @staticmethod
    def deposer(contenu: bytes, type_logo: TypeLogo) -> Logo:
        """Valide puis emballe un fichier déposé.

        Lève `TypeDeLogoRefuse` si le contenu est vide, dément le format annoncé, ou — pour un SVG
        — contient de quoi exécuter ; `LogoTropVolumineux` au-delà de la borne. **Le type annoncé
        ne fait pas foi** : un fichier déclaré PNG mais contenant du balisage serait renvoyé avec
        `Content-Type: image/png`, ce qu'un navigateur indulgent pourrait ne pas respecter.
        """
        if not contenu:
            raise TypeDeLogoRefuse("Le fichier déposé est vide.")
        if len(contenu) > POIDS_LOGO_MAX_OCTETS:
            raise LogoTropVolumineux(
                f"Ce logo pèse {len(contenu) // 1024} Ko ; la limite est de "
                f"{POIDS_LOGO_MAX_OCTETS // 1024} Ko. Réduisez le fichier avant de le déposer."
            )
        _verifier_le_contenu(contenu, type_logo)
        return Logo(contenu=contenu, type_logo=type_logo)

    @property
    def poids_octets(self) -> int:
        """Taille du fichier — ce que l'écran annonce, et ce que la borne compare."""
        return len(self.contenu)

    @property
    def empreinte(self) -> str:
        """Empreinte du **contenu** — l'identité des octets, pas celle de l'emplacement.

        Elle sert l'`ETag` de la route qui sert les octets **et** le segment de version de l'URL.
        ⚠️ **C'est ce qui rend un logo remplacé visible** : une URL stable ne provoque aucune
        requête sur une image déjà montée, donc `Cache-Control: no-cache` ne s'applique à rien.
        Versionner par l'horloge faisait l'inverse — 512 Ko retéléchargés à chaque événement
        WebSocket. Tronquée à 32 caractères : 128 bits suffisent à distinguer deux versions.
        """
        return hashlib.sha256(self.contenu).hexdigest()[:32]


def _decoder_les_references_numeriques(contenu: bytes) -> bytes:
    """Remplace `&#106;` / `&#x6a;` par le caractère correspondant, comme le ferait un parseur XML.

    Sert à chercher ce qui exécute **sur le texte tel que le navigateur le lira**, plutôt qu'à
    refuser toute référence — ce que faisait la rédaction précédente, au prix d'un refus des textes
    accentués échappés. Une référence hors plage ou mal formée est laissée telle quelle : le but
    est de révéler une dissimulation, pas de valider du XML.
    """

    def _remplacer(trouve: re.Match[bytes]) -> bytes:
        chiffres = trouve.group(1)
        try:
            point = int(chiffres[1:], 16) if chiffres[:1] in (b"x", b"X") else int(chiffres)
        except ValueError:  # pragma: no cover — le motif n'admet que des chiffres
            return trouve.group(0)
        if point > 0x10FFFF:
            return trouve.group(0)
        return chr(point).encode("utf-8", "replace")

    return _MOTIF_REFERENCE_NUMERIQUE.sub(_remplacer, contenu)


def _developper_les_entites_internes(contenu: bytes) -> bytes:
    """Substitue les entités générales **internes** par leur valeur littérale, une seule fois.

    Le parseur XML les développe ; une recherche sur les octets bruts arrive donc trop tard, tout
    comme pour les références numériques. Une seule passe, délibérément : la substitution récursive
    est ce qui rend *billion laughs* possible, et un logo n'a aucun usage d'une entité imbriquée.

    Rend le contenu inchangé si le document n'en déclare aucune — le cas de l'écrasante majorité.
    """
    declarees = dict(_MOTIF_ENTITE_INTERNE.findall(contenu))
    if not declarees:
        return contenu
    return _MOTIF_APPEL_D_ENTITE.sub(
        lambda trouve: declarees.get(trouve.group(1), trouve.group(0)), contenu
    )


def _lectures_possibles(contenu: bytes) -> list[bytes]:
    """Le fichier tel qu'il est écrit, **et** tel qu'un parseur le lira.

    Un octet cherché dans la seule forme brute est un octet cherché au mauvais endroit : entités et
    références de caractère sont deux façons d'écrire la même chaîne, et les deux se combinent.
    On rend donc les variantes distinctes, et le contrôle les balaie toutes.
    """
    lectures = [contenu]
    developpe = _developper_les_entites_internes(contenu)
    if developpe != contenu:
        lectures.append(developpe)
    for texte in list(lectures):
        decode = _decoder_les_references_numeriques(texte)
        if decode != texte:
            lectures.append(decode)
    return lectures


def _verifier_le_contenu(contenu: bytes, type_logo: TypeLogo) -> None:
    """Confronte les premiers octets au format annoncé ; lève `TypeDeLogoRefuse` en cas d'écart."""
    if type_logo is TypeLogo.PNG:
        # ⚠️ La signature seule ne prouve rien : la revue adversariale a fait accepter — puis
        # **servir** — un `\x89PNG…` suivi d'un SVG à script. On encadre donc le fichier par ses
        # deux extrémités obligatoires : `IHDR` (octets 12 à 16) et `IEND`, qui **termine** toujours
        # le fichier, CRC compris. N'exiger `IEND` que « quelque part » — relâché pour ne pas casser
        # un test de poids qui bourrait après la fin — laissait vingt octets suffire à reconstruire
        # un polyglotte. Le test bourre désormais avant `IEND`.
        if not contenu.startswith(_SIGNATURE_PNG):
            raise TypeDeLogoRefuse(
                "Ce fichier est annoncé PNG mais n'en porte pas la signature. "
                "Déposez un PNG ou un SVG."
            )
        if contenu[12:16] != b"IHDR" or not contenu.endswith(_FIN_PNG):
            raise TypeDeLogoRefuse(
                "Ce fichier porte la signature PNG mais n'en a pas la structure "
                "(en-tête IHDR, bloc de fin IEND). Ré-exportez-le depuis votre outil de dessin."
            )
        return

    # SVG : le document peut commencer par une déclaration XML, un DOCTYPE ou des commentaires —
    # c'est même la forme la plus courante d'un export d'outil de dessin. On cherche la balise sur
    # **tout** le fichier : la borner à l'en-tête faisait refuser un export licite dont la bannière
    # de licence dépassait mille octets, avec un message qui mentait.
    replie = contenu.lower()
    if b"<svg" not in replie:
        raise TypeDeLogoRefuse(
            "Ce fichier est annoncé SVG mais ne contient pas de balise <svg>. "
            "Déposez un SVG ou un PNG."
        )
    if _MOTIF_ENTITE_EXTERNE.search(contenu) or _MOTIF_DOCTYPE_EXTERNE.search(contenu):
        raise TypeDeLogoRefuse(
            "Ce SVG déclare une entité ou une DTD externe, qui sert à faire lire des fichiers "
            "du serveur et dont un logo n'a aucun usage. Ré-exportez-le en SVG simple."
        )
    # Le parseur développe les entités et décode les références **avant** d'interpréter quoi que ce
    # soit : on cherche donc sur toutes les lectures possibles du fichier, pas seulement sur ses
    # octets. C'est ce qui laisse passer `&#233;` et les entités d'Illustrator tout en fermant les
    # charges qui s'écrivent en morceaux.
    for texte in _lectures_possibles(contenu):
        if _MOTIF_REFERENCE_EXTERNE.search(texte):
            raise TypeDeLogoRefuse(
                "Ce SVG va chercher un document, une image ou une feuille de style ailleurs. Un "
                "logo doit se suffire à lui-même : aplatissez-le à l'export, ou déposez un PNG."
            )
        if _MOTIF_SVG_EXECUTABLE.search(texte):
            raise TypeDeLogoRefuse(
                "Ce SVG contient de quoi exécuter (balise <script>, attribut on…, lien "
                "javascript:, <foreignObject>, animation SMIL ou @import). Exportez-le en formes "
                "simples, ou déposez un PNG."
            )


# ————————————————————————————————————————————————————————————————————————————————————————————————
# L'agrégat

ACCENT_PRIMAIRE_CLUB = Couleur(r=0xB7, g=0x19, b=0x18)
"""Rouge des Archers de Kervignac (CDC design §3.3, `DV-04`)."""

ACCENT_SECONDAIRE_CLUB = Couleur(r=0x1D, g=0x1D, b=0x1B)
"""Anthracite du club — l'`accent-2` du tableau des deux accents (CDC design §3.6).

⚠️ Il **ne repeint pas le fond**, malgré son homonymie avec `--surface-0` : c'est un second accent
de marque, la strate structure étant figée (verrou 2). Que le club ait choisi son propre anthracite
comme couleur secondaire est une propriété de sa charte, pas une règle du système.
"""


@dataclass(frozen=True)
class IdentiteVisuelle:
    """L'identité visuelle d'un tournoi : deux accents **facultatifs**, et la présence des logos.

    ⚠️ **Les accents sont `None` tant que personne n'a choisi** : le CA veut distinguer *l'a choisi
    le rouge du club* de *n'a rien choisi*, sinon l'écran ne peut plus dire « hérité ». `reglee` se
    **dérive** de cette absence — le drapeau porté à la main annonçait « réglée » dès qu'un logo
    créait la ligne. ⚠️ Les **octets** des logos ne sont pas ici non plus : un blob traîné dans
    l'agrégat serait relu à chaque affichage public.
    """

    accent_primaire: Couleur | None = None
    accent_secondaire: Couleur | None = None
    empreintes: Mapping[EmplacementLogo, str] = MappingProxyType({})
    """Empreinte du contenu de chaque logo **présent** — les absents n'y figurent pas.

    ⚠️ **Une seule source pour deux faits** : « quels emplacements sont pourvus » se lit des clés,
    « quelle version » des valeurs. Les porter séparément rejouerait le défaut de `reglee`. ⚠️ **Le
    champ est gelé à la construction** : un `dict` derrière une annotation `Mapping` laissait
    l'agrégat `frozen` garder la référence de l'appelant, donc mutable de l'extérieur, et perdre sa
    hachabilité. `MappingProxyType` sur une copie ferme les deux (règle 4).
    """

    def __post_init__(self) -> None:
        """Fige la table d'empreintes — cf. la note du champ. `frozen` ne gèle que la liaison."""
        object.__setattr__(self, "empreintes", MappingProxyType(dict(self.empreintes)))

    def __hash__(self) -> int:
        """Hachable comme avant l'arrivée des empreintes : sur le contenu, table comprise."""
        return hash(
            (self.accent_primaire, self.accent_secondaire, tuple(sorted(self.empreintes.items())))
        )

    @property
    def logos_presents(self) -> frozenset[EmplacementLogo]:
        """Les emplacements pourvus — **dérivés** des empreintes, jamais stockés à côté."""
        return frozenset(self.empreintes)

    @property
    def reglee(self) -> bool:
        """`True` si l'organisateur a choisi ses couleurs ; `False` s'il hérite de celles du club.

        Ne regarde que l'accent **primaire** : les deux sont écrits ensemble (`avec_accents`), il
        n'existe aucun état où l'un serait posé sans l'autre.
        """
        return self.accent_primaire is not None

    @property
    def accents(self) -> tuple[Couleur, Couleur]:
        """Les deux accents **effectifs** — ceux du club si rien n'a été choisi.

        C'est le seul point où le défaut s'applique. Le mettre ici plutôt que dans le service
        garantit qu'aucun appelant ne peut l'oublier : lire `accent_primaire` directement rend
        `None`, ce que `mypy --strict` refuse de laisser passer sans traitement.
        """
        return (
            self.accent_primaire if self.accent_primaire is not None else ACCENT_PRIMAIRE_CLUB,
            self.accent_secondaire
            if self.accent_secondaire is not None
            else ACCENT_SECONDAIRE_CLUB,
        )

    def avec_accents(self, primaire: Couleur, secondaire: Couleur) -> IdentiteVisuelle:
        """Renvoie une copie aux deux accents posés (`P-3` : à tout moment, tournoi en cours
        compris — la garde de statut, s'il en fallait une, serait au service, pas ici)."""
        return replace(self, accent_primaire=primaire, accent_secondaire=secondaire)

    def avec_logo(self, emplacement: EmplacementLogo, empreinte: str) -> IdentiteVisuelle:
        """Renvoie une copie où `emplacement` porte ce contenu — l'autre est inchangé."""
        return replace(self, empreintes={**self.empreintes, emplacement: empreinte})

    def sans_logo(self, emplacement: EmplacementLogo) -> IdentiteVisuelle:
        """Renvoie une copie marquant `emplacement` comme vide — l'autre est inchangé."""
        return replace(
            self, empreintes={lieu: c for lieu, c in self.empreintes.items() if lieu != emplacement}
        )

    def marque(self, fond: Couleur) -> tuple[JetonsDeMarque, JetonsDeMarque]:
        """Décline les deux accents effectifs sur un fond — dans l'ordre (primaire, secondaire)."""
        primaire, secondaire = self.accents
        return deriver_marque(primaire, fond), deriver_marque(secondaire, fond)
