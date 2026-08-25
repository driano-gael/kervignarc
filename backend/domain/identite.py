"""Identité visuelle d'un tournoi — deux accents, deux logos (E16US006, absorbe E01US016).

Le club a **deux marques** : *Les Archers de Kervignac*, permanente, et l'événement — *Challenge des
Champions* — qui change à chaque édition. L'organisateur fournit **un logo par marque et deux
couleurs d'accent, rien d'autre** ; tout le reste du chrome est **dérivé** ici (`DV-06`).

**Pourquoi la dérivation vit dans le domaine.** « Teinte et saturation conservées, clarté ajustée
jusqu'au seuil AA » (`DV-05`) est une **règle reproductible**, pas un goût de graphiste : elle a une
entrée, une sortie, aucune horloge et aucun aléa. C'est donc du domaine pur (règle 1), testable sans
navigateur — et non un calcul recopié dans le front, où il aurait échappé à `mypy --strict` et
n'aurait été vérifié par personne.

**Ce que la dérivation ne touche PAS.** Les deux accents pilotent les **jetons de marque**, jamais
le fond de page ni les couleurs sémantiques. Le CDC design §3.6 le pose en verrous : *« les neutres,
l'échelle typographique, les espacements et les composants ne bougent pas — seul le chrome de marque
change »* (verrou 2) et *« alerte, succès, info appartiennent au produit, pas au tournoi »* (verrou
1, `DV-03`). Ce n'est pas de la prudence : `frontend/src/index.css` mesure **chaque** couleur contre
`--surface-0`. Repeindre le fond par tournoi invaliderait d'un coup les vingt ratios de la charte,
sans qu'aucun test ne bouge — le « bug de contraste silencieux » que `charte.test.ts` dit exister.

**La déclinaison du club est l'oracle de ce module.** `index.css` (E17US001, ADR-0074) décline le
rouge `#B71918` **à la main** en `#CC1C1B` (contour, 3,01:1) et `#E84E4D` (texte, 4,52:1). Ces trois
valeurs partagent teinte et saturation à moins d'un demi-degré près : la charte avait déjà appliqué
la règle que ce module automatise. `test_domain_identite.py` exige qu'il la reproduise.
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, replace
from enum import Enum

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
    **inutilisable en texte** sur le même fond. Les noms sont ceux de `index.css`, pour que la
    traduction en `--brand-*` reste une transcription et non une correspondance à retenir.
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
    l'organisateur sont sa marque, les changer serait la lui prendre. C'est aussi ce qui empêche la
    solution paresseuse : « atteindre 4,5:1 » se satisfait de renvoyer du blanc.

    Le contrôle est **non bloquant** (`P-4`) : rien ici ne refuse une couleur. L'accent trop faible
    est accepté, décliné, et le chiffre de son échec est rendu à l'écran pour que l'organisateur
    décide en connaissance de cause.
    """
    return JetonsDeMarque(
        surface=accent,
        contour=_ajuster_clarte(accent, fond, SEUIL_CONTOUR),
        texte=_ajuster_clarte(accent, fond, SEUIL_TEXTE),
        encre=_BLANC if contraste(_BLANC, accent) >= contraste(_NOIR, accent) else _NOIR,
    )


def _ajuster_clarte(couleur: Couleur, fond: Couleur, seuil: float) -> Couleur:
    """Éloigne `couleur` de `fond` **en clarté seulement**, jusqu'au premier pas qui tient `seuil`.

    Trois choses qui ont l'air de détails et n'en sont pas :

    1. **Une couleur déjà conforme n'est pas touchée.** En thème clair le rouge du club atteint
       6,63:1 et `index.css` donne bien la **même** valeur à ses trois jetons de marque. Ajuster
       systématiquement contredirait la charte livrée.
    2. **Le sens se décide par les extrêmes, pas par une heuristique.** On compare ce que donnent le
       blanc et le noir sur ce fond : celui qui gagne indique la direction. Sur l'anthracite c'est
       le blanc (16,88:1 contre 1,19:1) — descendre vers le noir n'atteindrait **jamais** 3:1, une
       recherche qui aurait « choisi » cette direction bouclerait sur un échec silencieux.
    3. **Le seuil est vérifié sur la couleur ARRONDIE.** La clarté est un flottant, le CSS reçoit
       trois octets : un seuil atteint à 4,502 en flottant peut retomber à 4,497 une fois arrondi.
       C'est la couleur livrée qui doit tenir la promesse, pas celle qu'on a calculée.
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

# Ce qui, dans un SVG, **exécute**. Cherché sur le fichier replié en minuscules, et volontairement
# large : `<script`, un gestionnaire `on…=`, une URL `javascript:`, et `<foreignObject>` qui
# réintroduit du HTML — donc tout HTML — à l'intérieur du SVG.
_MOTIF_SVG_EXECUTABLE = re.compile(
    rb"<\s*script|<\s*foreignobject|\son[a-z]+\s*=|javascript\s*:", re.IGNORECASE
)


@dataclass(frozen=True)
class Logo:
    """Un fichier de logo déposé, avec son format. Value object immuable.

    ⚠️ **Un SVG est un document, pas une image.** Servi depuis l'origine de l'application — qui sert
    aussi sa propre SPA —, un SVG porteur de script s'exécuterait avec la session de qui l'ouvre, y
    compris celle d'un admin. `<img src>` neutralise bien les scripts, mais la route qui sert le
    logo reste atteignable en navigation directe : on **refuse le fichier**, plutôt que de faire
    reposer la sûreté sur la façon dont il sera affiché.
    """

    contenu: bytes
    type_logo: TypeLogo

    @staticmethod
    def deposer(contenu: bytes, type_logo: TypeLogo) -> Logo:
        """Valide puis emballe un fichier déposé.

        Lève `TypeDeLogoRefuse` si le contenu est vide, dément le format annoncé, ou — pour un SVG —
        contient de quoi exécuter ; `LogoTropVolumineux` au-delà de la borne.

        **Le type annoncé ne fait pas foi** : c'est le contenu qui décide. Un fichier déclaré PNG
        mais contenant du balisage serait renvoyé avec `Content-Type: image/png`, ce qu'un
        navigateur indulgent pourrait ne pas respecter.
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


def _verifier_le_contenu(contenu: bytes, type_logo: TypeLogo) -> None:
    """Confronte les premiers octets au format annoncé ; lève `TypeDeLogoRefuse` en cas d'écart."""
    if type_logo is TypeLogo.PNG:
        if not contenu.startswith(_SIGNATURE_PNG):
            raise TypeDeLogoRefuse(
                "Ce fichier est annoncé PNG mais n'en porte pas la signature. "
                "Déposez un PNG ou un SVG."
            )
        return

    # SVG : le document peut commencer par une déclaration XML, un DOCTYPE ou des commentaires —
    # c'est même la forme la plus courante d'un export d'outil de dessin. On exige seulement qu'une
    # balise `<svg` apparaisse dans l'en-tête, avant de chercher ce qui exécute.
    entete = contenu[:1024].lower()
    if b"<svg" not in entete:
        raise TypeDeLogoRefuse(
            "Ce fichier est annoncé SVG mais ne contient pas de balise <svg>. "
            "Déposez un SVG ou un PNG."
        )
    if _MOTIF_SVG_EXECUTABLE.search(contenu):
        raise TypeDeLogoRefuse(
            "Ce SVG contient du script (balise <script>, attribut on…, lien javascript: ou "
            "<foreignObject>). Exportez-le sans interactivité, ou déposez un PNG."
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

    ⚠️ **Les accents sont `None` tant que personne n'a choisi, et ce n'est pas un détail de
    stockage.** Le CA dit « défaut = identité du club **si rien n'est fourni** » : il faut donc
    pouvoir distinguer *l'organisateur a choisi le rouge du club* de *il n'a rien choisi*, sinon
    l'écran ne peut plus dire « hérité ». `reglee` se **dérive** de cette absence.

    La première rédaction faisait circuler un booléen `reglee` de la persistance jusqu'au DTO, à
    côté d'une identité toujours concrète. Un test d'API l'a démentie : déposer un logo crée la
    ligne, et la relecture annonçait alors « réglée » sans qu'aucune couleur ait été choisie. Le
    défaut venait du drapeau lui-même — deux sources pour un même fait, l'une écrite à la main à
    chaque appel. Ici, il n'y a plus de drapeau, seulement une valeur absente.

    ⚠️ **Les octets des logos ne sont pas ici non plus.** Un blob traîné dans l'agrégat serait relu
    à chaque fois qu'on veut connaître les accents — soit à chaque affichage public. Le port lit les
    deux séparément : les réglages d'un côté (quelques octets), un logo à la fois de l'autre, sur sa
    propre route et son propre cache.
    """

    accent_primaire: Couleur | None = None
    accent_secondaire: Couleur | None = None
    logos_presents: frozenset[EmplacementLogo] = frozenset()

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

    def avec_logo(self, emplacement: EmplacementLogo) -> IdentiteVisuelle:
        """Renvoie une copie marquant `emplacement` comme pourvu — l'autre est inchangé."""
        return replace(self, logos_presents=self.logos_presents | {emplacement})

    def sans_logo(self, emplacement: EmplacementLogo) -> IdentiteVisuelle:
        """Renvoie une copie marquant `emplacement` comme vide — l'autre est inchangé."""
        return replace(self, logos_presents=self.logos_presents - {emplacement})

    def marque(self, fond: Couleur) -> tuple[JetonsDeMarque, JetonsDeMarque]:
        """Décline les deux accents effectifs sur un fond — dans l'ordre (primaire, secondaire)."""
        primaire, secondaire = self.accents
        return deriver_marque(primaire, fond), deriver_marque(secondaire, fond)
