"""Tests du domaine de l'**identité visuelle du tournoi** (E16US006, absorbe E01US016).

⚠️ **Écrits depuis le CA, avant l'implémentation** (`CLAUDE.md` règle 9). La source est la puce « CA
» d'`E01US016` dans [`stories/E01-configuration.md`](../../stories/E01-configuration.md), complétée
de [`cahier-des-charges-design.md`](../../cahier-des-charges-design.md) §3.5/§3.6 (`DV-04`, `DV-05`,
`DV-06`) — jamais `docs/fonctionnel/`, qui n'existe pas encore et serait un produit de
l'implémentation.

**L'oracle de la dérivation ne vient pas de moi.** La charte du club a été déclinée **à la main**
dans `frontend/src/index.css` (E17US001, ADR-0074) : `#B71918` mesuré à 2,55:1 sur l'anthracite, ses
variantes `#CC1C1B` (contour, 3,01:1) et `#E84E4D` (texte, 4,52:1). Vérification faite en écrivant
ces tests, ces trois valeurs **conservent teinte et saturation** (0,38° / 0,34° / 0,39° de teinte,
saturation 0,768 / 0,766 / 0,771) et ne diffèrent que par la **clarté** — c'est exactement la règle
que `DV-05` énonce en français. Le calcul de cette US doit donc **reproduire une déclinaison écrite
avant elle**, ce qui en fait un oracle externe et non une description de mon propre code.
"""

from __future__ import annotations

import colorsys

import pytest

from domain.erreurs import CouleurInvalide, LogoTropVolumineux, TypeDeLogoRefuse
from domain.identite import (
    ACCENT_PRIMAIRE_CLUB,
    ACCENT_SECONDAIRE_CLUB,
    FOND_CLAIR,
    FOND_SOMBRE,
    POIDS_LOGO_MAX_OCTETS,
    SEUIL_CONTOUR,
    SEUIL_TEXTE,
    Couleur,
    EmplacementLogo,
    IdentiteVisuelle,
    Logo,
    TypeLogo,
    contraste,
    deriver_marque,
)

# Les trois valeurs que la charte a calculées à la main (E17US001) — l'oracle de ce fichier.
ROUGE_CLUB = "#b71918"
CONTOUR_ATTENDU_SOMBRE = "#cc1c1b"
TEXTE_ATTENDU_SOMBRE = "#e84e4d"


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA — « l'organisateur fournit un logo et deux couleurs d'accent, RIEN D'AUTRE »


class TestCouleur:
    """Une couleur d'accent se saisit, donc elle se valide."""

    @pytest.mark.parametrize(
        "saisie",
        ["#B71918", "#b71918", "b71918", "  #B71918  ", "#B71918\n"],
    )
    def test_les_formes_usuelles_d_une_saisie_sont_acceptees(self, saisie: str) -> None:
        """Un organisateur colle une valeur depuis sa charte : dièse ou non, casse quelconque,
        espaces de bord. Refuser sur la casse serait une chicane, pas une règle."""
        assert Couleur.depuis_hex(saisie).hex == ROUGE_CLUB

    def test_la_forme_normalisee_est_minuscule_et_prefixee(self) -> None:
        """Une seule écriture en sortie : la comparaison des jetons et le CSS émis en dépendent."""
        assert Couleur.depuis_hex("B71918").hex == "#b71918"

    @pytest.mark.parametrize(
        "saisie",
        [
            "",
            "#",
            "#B7191",  # cinq chiffres
            "#B719188",  # sept
            "#GG1918",  # hors hexadécimal
            "rouge",
            "rgb(183,25,24)",
        ],
    )
    def test_toute_autre_forme_est_refusee_avec_une_erreur_de_domaine(self, saisie: str) -> None:
        """« Rien d'autre » : le domaine n'accepte pas les notations CSS, ni les noms. Une seule
        forme admise, sinon on rouvre la porte que `charte.test.ts` a fermée côté front."""
        with pytest.raises(CouleurInvalide):
            Couleur.depuis_hex(saisie)

    def test_la_forme_courte_a_trois_chiffres_est_refusee(self) -> None:
        """`#F00` n'est pas accepté : l'accepter obligerait à décider si `#F00` et `#FF0000` sont
        la même couleur au moment de comparer deux identités. Une forme, une valeur."""
        with pytest.raises(CouleurInvalide):
            Couleur.depuis_hex("#F00")


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA — « contrôle de contraste à la saisie, en alerte CHIFFRÉE et non bloquante » (P-4)


class TestContraste:
    """Le ratio WCAG 2.1 — c'est lui qui est *chiffré* à l'écran, donc il doit être juste."""

    def test_le_blanc_sur_le_noir_atteint_le_maximum_theorique(self) -> None:
        assert contraste(
            Couleur.depuis_hex("#ffffff"), Couleur.depuis_hex("#000000")
        ) == pytest.approx(21.0, abs=0.01)

    def test_une_couleur_sur_elle_meme_ne_contraste_pas(self) -> None:
        rouge = Couleur.depuis_hex(ROUGE_CLUB)
        assert contraste(rouge, rouge) == pytest.approx(1.0, abs=0.001)

    def test_le_ratio_est_symetrique(self) -> None:
        """WCAG définit (L1+0,05)/(L2+0,05) avec L1 la plus claire : l'ordre des arguments ne doit
        donc rien changer. Une implémentation naïve qui ne trierait pas les deux luminances
        renverrait l'inverse du ratio dans un sens sur deux."""
        a, b = Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE
        assert contraste(a, b) == pytest.approx(contraste(b, a), abs=1e-9)

    def test_le_rouge_du_club_echoue_sur_l_anthracite_au_ratio_mesure_par_la_charte(self) -> None:
        """`DV-04`, chiffre publié : 2,55:1. C'est le cas d'école du CDC — et le seul point du
        calcul que je peux confronter à une valeur écrite par quelqu'un d'autre."""
        mesure = contraste(Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE)
        assert mesure == pytest.approx(2.55, abs=0.01)
        assert mesure < SEUIL_CONTOUR, "il échoue même au seuil le plus bas (WCAG 1.4.11)"

    def test_le_rouge_du_club_passe_en_texte_sur_le_blanc(self) -> None:
        """Même chiffre publié, autre fond : 6,63:1 (`index.css`, thème clair). C'est ce qui fait
        que les trois jetons de marque se confondent en thème clair — un test qui ne vérifierait
        que le thème sombre laisserait passer une dérivation qui assombrit toujours."""
        mesure = contraste(Couleur.depuis_hex(ROUGE_CLUB), FOND_CLAIR)
        assert mesure == pytest.approx(6.63, abs=0.01)
        assert mesure >= SEUIL_TEXTE


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA — « la couleur exacte est ACCEPTÉE pour les aplats, une variante AA est DÉRIVÉE pour le texte
# et les bordures » (DV-05) · « le système dérive […] en thème sombre ET clair »


class TestDerivationDeLaMarque:
    def test_l_aplat_porte_la_couleur_exacte_meme_quand_elle_echoue(self) -> None:
        """Le cœur de `DV-05` : on n'améliore pas la couleur de l'organisateur, on l'accepte telle
        quelle en surface. La corriger serait lui prendre sa marque — c'est le contrôle qui est
        « non bloquant » (`P-4`), pas la couleur qui est réécrite."""
        jetons = deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE)
        assert jetons.surface.hex == ROUGE_CLUB

    def test_le_contour_derive_reproduit_la_valeur_calculee_a_la_main_par_la_charte(self) -> None:
        """L'oracle externe. `index.css` porte `--brand-border: #cc1c1b` avec le commentaire
        « 3,01:1 dérivée DV-05 », écrit en E17US001, avant cette US."""
        jetons = deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE)
        assert jetons.contour.hex == CONTOUR_ATTENDU_SOMBRE

    def test_le_texte_derive_tombe_un_cran_sous_la_valeur_calculee_a_la_main(self) -> None:
        """⚠️ **Le seul point où le calcul et la charte divergent, et l'écart a été instruit.**

        `index.css` porte `--brand-text: #e84e4d`, « 4,52:1 ». La dérivation rend `#e84d4d` : un
        cran plus bas sur le canal vert, à 4,50:1. Les deux sont conformes ; la différence est que
        la charte, calculée à la main, s'est arrêtée **un pas après** le franchissement, là où
        `DV-05` demande d'ajuster la clarté **jusqu'au** seuil — donc de toucher la marque le moins
        possible.

        Ce test dit les deux choses : la valeur rendue est bien celle de la charte **à un cran
        près** (la règle est la même, il n'y a pas de dérive de teinte), et c'est bien la valeur
        **minimale** qui franchit le seuil (le cran précédent échoue). Sans cette seconde assertion,
        « à un cran près » excuserait n'importe quelle imprécision.
        """
        obtenu = deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE).texte
        charte = Couleur.depuis_hex(TEXTE_ATTENDU_SOMBRE)

        for canal_obtenu, canal_charte in (
            (obtenu.r, charte.r),
            (obtenu.g, charte.g),
            (obtenu.b, charte.b),
        ):
            assert abs(canal_obtenu - canal_charte) <= 1

        assert contraste(obtenu, FOND_SOMBRE) >= SEUIL_TEXTE
        assert contraste(charte, FOND_SOMBRE) >= SEUIL_TEXTE, "la charte est conforme elle aussi"

    def test_la_variante_de_texte_est_la_plus_proche_qui_franchisse_le_seuil(self) -> None:
        """La propriété que la divergence ci-dessus a rendue nécessaire d'écrire : la dérivation ne
        « monte pas jusqu'à ce que ce soit bien », elle s'arrête au premier pas conforme.

        Se vérifie sans connaître le résultat : on redescend d'un cran la clarté de la valeur
        obtenue et on exige que ce cran-là **échoue**. Une dérivation qui prendrait une marge de
        confort — ou qui renverrait du blanc — tomberait ici."""
        obtenu = deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), FOND_SOMBRE).texte
        un_cran_plus_sombre = Couleur(
            r=max(0, obtenu.r - 1), g=max(0, obtenu.g - 1), b=max(0, obtenu.b - 1)
        )

        assert contraste(un_cran_plus_sombre, FOND_SOMBRE) < SEUIL_TEXTE

    @pytest.mark.parametrize(
        "accent",
        [
            "#b71918",  # le rouge du club
            "#1d1d1b",  # l'anthracite : l'accent SE CONFOND avec le fond sombre (contraste 1:1)
            "#000000",  # plus sombre que le fond : la dérivation doit ÉCLAIRCIR
            "#ffffff",  # déjà au maximum
            "#ffd400",  # un jaune vif
            "#0b6e9e",  # un bleu sombre
            "#808080",  # un gris sans saturation — la teinte n'existe pas
            "#00ff00",  # saturation maximale
        ],
    )
    @pytest.mark.parametrize("fond", ["sombre", "clair"])
    def test_les_variantes_derivees_atteignent_toujours_leur_seuil(
        self, accent: str, fond: str
    ) -> None:
        """La propriété qui compte, sur les deux thèmes : quelle que soit la couleur fournie —
        y compris celle qui se confond avec le fond, celle qui est déjà noire, celle qui n'a pas de
        teinte — le contour atteint 3:1 (WCAG 1.4.11) et le texte 4,5:1 (WCAG 1.4.3).

        C'est un test de **propriété**, pas de valeur : il ne dit pas quelle couleur sortir, il dit
        que la promesse « la conformité AA n'est pas à la main de l'organisateur » (§3.6, verrou 3)
        tient sur tous les cas que je sais construire. Un seuil atteint en flottant puis **perdu à
        l'arrondi 8 bits** est le mode de panne exact que la valeur livrée doit éviter : le ratio
        est donc mesuré sur la couleur arrondie, celle qui part vraiment dans le CSS.
        """
        surface = FOND_SOMBRE if fond == "sombre" else FOND_CLAIR
        depart = Couleur.depuis_hex(accent)
        jetons = deriver_marque(depart, surface)

        assert contraste(jetons.contour, surface) >= SEUIL_CONTOUR
        assert contraste(jetons.texte, surface) >= SEUIL_TEXTE

        # Et **pas davantage** : `DV-05` dit « ajustée **jusqu'au** seuil », et non
        # « jusqu'à confort ».
        # Sans cette moitié, une dérivation qui prendrait dix crans de marge sur toutes les couleurs
        # resterait verte partout — la conservation de teinte ne l'attraperait pas, un
        # éclaircissement en HLS conserve la teinte. Seul le rouge du club était pincé par le bas,
        # via l'oracle d'`index.css` ; la propriété, elle, ne l'était nulle part (relevé en revue).
        _exiger_la_minimalite(depart, jetons.contour, surface, SEUIL_CONTOUR)
        _exiger_la_minimalite(depart, jetons.texte, surface, SEUIL_TEXTE)

    @pytest.mark.parametrize("accent", ["#b71918", "#ffd400", "#0b6e9e", "#00ff00"])
    @pytest.mark.parametrize("fond", ["sombre", "clair"])
    def test_la_derivation_conserve_la_teinte(self, accent: str, fond: str) -> None:
        """`DV-05` dit « teinte et saturation conservées, clarté ajustée ». Sans cette contrainte,
        « atteindre 4,5:1 » se satisferait de renvoyer du blanc — techniquement conforme, et la
        marque de l'organisateur aurait disparu. La tolérance couvre l'arrondi 8 bits, pas un
        changement de couleur.

        Le gris (`#808080`) et les achromatiques sont exclus du cas : une couleur sans saturation
        n'a pas de teinte à conserver, exiger la sienne n'aurait aucun sens."""
        surface = FOND_SOMBRE if fond == "sombre" else FOND_CLAIR
        depart = Couleur.depuis_hex(accent)
        jetons = deriver_marque(depart, surface)

        for derivee in (jetons.contour, jetons.texte):
            assert derivee.teinte == pytest.approx(
                depart.teinte, abs=1.5
            ), f"{derivee.hex} n'a plus la teinte de {depart.hex}"

    def test_une_couleur_deja_conforme_n_est_pas_touchee(self) -> None:
        """En thème clair le rouge du club atteint 6,63:1 : `index.css` y donne bien la **même**
        valeur aux trois jetons de marque. Une dérivation qui ajusterait systématiquement
        renverrait un rouge plus sombre et **contredirait la charte livrée**."""
        jetons = deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), FOND_CLAIR)

        assert jetons.surface.hex == ROUGE_CLUB
        assert jetons.contour.hex == ROUGE_CLUB
        assert jetons.texte.hex == ROUGE_CLUB

    def test_l_encre_posee_sur_l_aplat_est_celle_qui_contraste_le_plus(self) -> None:
        """`DV-04` : « on écrit **en blanc dessus** (6,63:1) ». L'encre n'est pas une variante de la
        marque — c'est le noir ou le blanc, selon lequel des deux tient sur l'aplat. La charte pose
        `--sur-brand: #ffffff` dans les deux thèmes ; c'est une propriété de l'aplat, pas du fond de
        page, donc elle ne dépend pas du thème."""
        for fond in (FOND_SOMBRE, FOND_CLAIR):
            assert deriver_marque(Couleur.depuis_hex(ROUGE_CLUB), fond).encre.hex == "#ffffff"

        # Un jaune vif : c'est le noir qui tient dessus. Sans ce cas, « renvoyer toujours blanc »
        # passerait — et blanc sur `#ffd400` vaut 1,32:1, l'effondrement que `charte.test.ts` décrit
        # déjà (« blanc sur ambre, 1,9:1 »).
        assert deriver_marque(Couleur.depuis_hex("#ffd400"), FOND_SOMBRE).encre.hex == "#000000"

    def test_l_encre_de_l_aplat_est_elle_aussi_lisible(self) -> None:
        """La propriété derrière le cas d'école : quoi qu'on fournisse, le texte posé sur l'aplat
        atteint le seuil de **texte**. Le pire cas théorique est un gris moyen, où ni le noir ni le
        blanc ne brillent — d'où sa présence explicite dans la liste.

        ⚠️ L'assertion comparait à `SEUIL_CONTOUR` (3,0) alors que la docstring promettait le seuil
        de texte, et la promesse forte est bien tenue : au pire, `max(blanc, noir)` sur un ton moyen
        rend 4,58:1. À 3,0 le test laissait passer une comparaison d'encre **inversée** sur les tons
        moyens, où le mauvais choix rend exactement 3,0:1 (relevé en revue).
        """
        for accent in ("#b71918", "#ffd400", "#00ff00", "#767676", "#1d1d1b", "#ffffff"):
            jetons = deriver_marque(Couleur.depuis_hex(accent), FOND_SOMBRE)
            assert (
                contraste(jetons.encre, jetons.surface) >= SEUIL_TEXTE
            ), f"rien ne s'écrit lisiblement sur {accent}"


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA — « défaut = identité du club si rien n'est fourni » CA (E16US006) — « un second logo,
# FACULTATIF, distinct du logo d'événement »


class TestIdentiteVisuelle:
    def test_a_defaut_les_accents_effectifs_sont_ceux_du_club(self) -> None:
        """CDC design §3.6, tableau des deux accents : « Rouge club `#B71918` + anthracite ».

        Un tournoi neuf n'affiche donc pas une identité *vide* : il **hérite** de celle du club.
        C'est `accents` qui applique ce défaut — et lui seul, pour qu'aucun appelant ne puisse
        l'oublier."""
        identite = IdentiteVisuelle()

        primaire, secondaire = identite.accents
        assert primaire == ACCENT_PRIMAIRE_CLUB
        assert secondaire == ACCENT_SECONDAIRE_CLUB
        assert ACCENT_PRIMAIRE_CLUB.hex == ROUGE_CLUB
        assert ACCENT_SECONDAIRE_CLUB.hex == "#1d1d1b"

    def test_heriter_et_avoir_choisi_le_rouge_du_club_ne_sont_pas_le_meme_etat(self) -> None:
        """⚠️ Le CA dit « défaut = identité du club **si rien n'est fourni** » : il faut donc que
        « je n'ai rien choisi » se distingue de « j'ai choisi exactement les couleurs du club ».

        Les deux identités rendent les **mêmes** couleurs — et doivent pourtant se lire
        différemment, l'écran devant dire *hérité* dans un cas et *réglé* dans l'autre. Sans cette
        distinction, un tournoi paraîtrait configuré parce qu'il ne l'est pas."""
        heritee = IdentiteVisuelle()
        choisie = IdentiteVisuelle().avec_accents(ACCENT_PRIMAIRE_CLUB, ACCENT_SECONDAIRE_CLUB)

        assert heritee.accents == choisie.accents, "mêmes couleurs à l'écran"
        assert heritee.reglee is False
        assert choisie.reglee is True

    def test_deposer_un_logo_ne_regle_pas_les_couleurs(self) -> None:
        """⚠️ **Ce test vient d'un défaut réel, trouvé par le test d'API de cette même US.**

        Déposer un logo fait exister la ligne d'identité en base. Une première rédaction en
        déduisait « réglée », si bien qu'un tournoi dont on avait seulement déposé le logo se
        présentait comme configuré. `reglee` se lit sur les **accents**, jamais sur l'existence
        d'un enregistrement."""
        identite = IdentiteVisuelle().avec_logo(EmplacementLogo.CLUB)

        assert identite.logos_presents == frozenset({EmplacementLogo.CLUB})
        assert identite.reglee is False

    def test_les_deux_logos_sont_facultatifs_et_absents_par_defaut(self) -> None:
        """« bien sûr cela reste optionnel » (questionnaire A05). Un tournoi sans logo est un état
        normal, pas une configuration incomplète : rien dans le CA n'en fait une garde de
        démarrage."""
        assert IdentiteVisuelle().logos_presents == frozenset()

    def test_les_deux_emplacements_sont_distincts(self) -> None:
        """Le CA d'E16US006 dit « un champ **de plus** » : déposer le logo du club ne remplace pas
        celui de l'événement. Deux emplacements nommés, pas une liste."""
        identite = IdentiteVisuelle().avec_logo(EmplacementLogo.CLUB)

        assert identite.logos_presents == frozenset({EmplacementLogo.CLUB})
        assert EmplacementLogo.EVENEMENT not in identite.logos_presents

    def test_deposer_puis_retirer_un_logo_ne_touche_pas_l_autre(self) -> None:
        identite = (
            IdentiteVisuelle()
            .avec_logo(EmplacementLogo.CLUB)
            .avec_logo(EmplacementLogo.EVENEMENT)
            .sans_logo(EmplacementLogo.EVENEMENT)
        )

        assert identite.logos_presents == frozenset({EmplacementLogo.CLUB})

    def test_regler_les_accents_ne_touche_pas_aux_logos(self) -> None:
        """Symétrique du précédent : les deux gestes sont indépendants **dans les deux sens**."""
        identite = IdentiteVisuelle().avec_logo(EmplacementLogo.EVENEMENT)

        apres = identite.avec_accents(Couleur.depuis_hex("#0b6e9e"), Couleur.depuis_hex("#ffd400"))

        assert apres.logos_presents == frozenset({EmplacementLogo.EVENEMENT})

    def test_changer_un_accent_renvoie_une_copie(self) -> None:
        """Agrégat **immuable** (règle 4) : `P-3` dit « modifiable à tout moment, y compris tournoi
        en cours » — c'est le service qui réécrit, pas l'objet qui mute."""
        depart = IdentiteVisuelle()
        modifiee = depart.avec_accents(Couleur.depuis_hex("#0b6e9e"), Couleur.depuis_hex("#ffd400"))

        assert depart.reglee is False, "l'original n'est pas touché"
        assert modifiee.accents[0].hex == "#0b6e9e"
        assert modifiee.accents[1].hex == "#ffd400"

    def test_l_identite_decline_ses_deux_accents_sur_un_fond(self) -> None:
        """`marque()` est la porte que le service emprunte : elle applique le défaut du club **et**
        la dérivation, pour que personne n'ait à enchaîner les deux à la main."""
        primaire, secondaire = IdentiteVisuelle().marque(FOND_SOMBRE)

        assert primaire.surface.hex == ROUGE_CLUB
        assert primaire.contour.hex == CONTOUR_ATTENDU_SOMBRE
        assert secondaire.surface.hex == "#1d1d1b", "l'anthracite, tel quel, en aplat"
        assert (
            contraste(secondaire.texte, FOND_SOMBRE) >= SEUIL_TEXTE
        ), "même un accent confondu avec le fond rend un texte lisible"


# ————————————————————————————————————————————————————————————————————————————————————————————————
# CA — « l'organisateur fournit un logo (SVG/PNG) » Arbitrage du 25/08/2026 (Q-UX10) : le fichier
# est fourni **déjà calibré**. L'application ne recadre, ne détoure et ne redimensionne rien — elle
# **refuse explicitement** ce qu'elle n'accepte pas, plutôt que de laisser croire qu'elle a traité
# le fichier.

PNG_MINIMAL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    # Bloc de données puis marque de fin : un **vrai** PNG, pas seulement une signature. Depuis la
    # revue, `Logo.deposer` exige la structure (`IHDR` en douzième position, `IEND` présente) — la
    # signature seule laissait passer un polyglotte PNG/SVG porteur de script, déposé pour de vrai
    # par le relecteur adversarial et accepté en 200.
    b"\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB\x60\x82"
)
SVG_MINIMAL = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _exiger_la_minimalite(depart: Couleur, derivee: Couleur, fond: Couleur, seuil: float) -> None:
    """Vérifie qu'aucune clarté **entre** l'accent d'origine et la variante ne tenait déjà le seuil.

    Formulée en boîte noire : on ne relit pas le pas de recherche du module, on prend la clarté
    **médiane** entre le départ et la variante et on exige qu'elle échoue. Si la dérivation prenait
    de la marge, cette médiane la tiendrait — c'est exactement ce qu'on veut voir rougir.

    Deux échappatoires légitimes, et elles sont nommées plutôt que tolérées en silence :
    l'accent déjà conforme (la variante **est** l'accent, il n'y a rien à minimiser) et la médiane
    qui, arrondie sur huit bits, retombe sur la variante elle-même (il n'existait alors aucune
    couleur intermédiaire à tester).
    """
    if derivee == depart:
        return
    h_depart, l_depart, s_depart = colorsys.rgb_to_hls(
        depart.r / 255, depart.g / 255, depart.b / 255
    )
    _, l_derivee, _ = colorsys.rgb_to_hls(derivee.r / 255, derivee.g / 255, derivee.b / 255)
    r, g, b = colorsys.hls_to_rgb(h_depart, (l_depart + l_derivee) / 2, s_depart)
    mediane = Couleur(r=round(r * 255), g=round(g * 255), b=round(b * 255))
    if mediane == derivee:
        return
    assert contraste(mediane, fond) < seuil, (
        f"la dérivation de {depart.hex} vers {derivee.hex} prend de la marge : "
        f"{mediane.hex} tenait déjà {seuil}:1"
    )


class TestLogo:
    def test_un_png_est_accepte(self) -> None:
        logo = Logo.deposer(PNG_MINIMAL, TypeLogo.PNG)
        assert logo.type_logo is TypeLogo.PNG
        assert logo.contenu == PNG_MINIMAL

    def test_un_svg_est_accepte(self) -> None:
        assert Logo.deposer(SVG_MINIMAL, TypeLogo.SVG).type_logo is TypeLogo.SVG

    def test_un_svg_precede_d_une_declaration_xml_est_accepte(self) -> None:
        """Un export d'Illustrator ou d'Inkscape commence par `<?xml …?>`, souvent suivi d'un
        `<!DOCTYPE>` et de commentaires. Refuser ce cas rendrait le format inutilisable en
        pratique, alors que c'est la forme la plus courante d'un SVG « propre »."""
        entete = b'<?xml version="1.0" encoding="UTF-8"?>\n<!-- Generator -->\n'
        assert Logo.deposer(entete + SVG_MINIMAL, TypeLogo.SVG).type_logo is TypeLogo.SVG

    def test_un_contenu_qui_dement_le_type_annonce_est_refuse(self) -> None:
        """Le type ne se croit pas sur parole : c'est le **contenu** qui décide. Un fichier annoncé
        PNG mais contenant du balisage serait servi avec `Content-Type: image/png` tout en étant
        interprété autrement par un navigateur indulgent — le sniffing est neutralisé côté API, mais
        l'invariant vaut mieux d'être tenu ici, où il est testable."""
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(SVG_MINIMAL, TypeLogo.PNG)
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(PNG_MINIMAL, TypeLogo.SVG)

    def test_un_svg_porteur_de_script_est_refuse(self) -> None:
        """⚠️ Un SVG est un **document**, pas une image : servi depuis la même origine que
        l'application, un `<script>` qu'il contiendrait s'exécuterait avec la session de qui
        l'ouvre. L'appli sert sa propre SPA — c'est donc la session **admin** qui est en jeu. On
        refuse le fichier plutôt que de compter sur le fait que `<img>` neutralise les scripts : la
        route qui
        sert le logo est atteignable directement."""
        hostile = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(hostile, TypeLogo.SVG)

    @pytest.mark.parametrize(
        "hostile",
        [
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)">x</a></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject></foreignObject></svg>',
        ],
    )
    def test_les_autres_vecteurs_d_execution_d_un_svg_sont_refuses_aussi(
        self, hostile: bytes
    ) -> None:
        """`<script>` n'est pas le seul : un gestionnaire `on…`, une URL `javascript:` et
        `<foreignObject>` (qui réintroduit du HTML dans le SVG) exécutent tout autant. Ne bloquer
        que la balise donnerait un garde-fou qui **rassure sans protéger**."""
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(hostile, TypeLogo.SVG)

    @pytest.mark.parametrize(
        ("vecteur", "hostile"),
        [
            (
                "référence de caractère dans un lien",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<a xlink:href="&#106;avascript:alert(1)">x</a></svg>',
            ),
            (
                "référence hexadécimale",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<a href="&#x6a;avascript:alert(1)">x</a></svg>',
            ),
            (
                "entité déclarée (XXE)",
                b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
                b'<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>',
            ),
            (
                "gestionnaire posé par SMIL",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<set attributeName="onload" to="alert(1)"/></svg>',
            ),
            (
                "animation d'un lien",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<animate attributeName="href" values="javascript:alert(1)"/></svg>',
            ),
            (
                "document tiers par <use>",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<use href="data:image/svg+xml;base64,AAAA"/></svg>',
            ),
            (
                "document tiers par <image>",
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<image href="https://exemple.test/x.svg"/></svg>',
            ),
        ],
    )
    def test_le_corpus_d_attaques_reelles_est_refuse(self, vecteur: str, hostile: bytes) -> None:
        """⚠️ **Ce corpus ne dérive pas du filtre, il dérive de l'attaque.** Le test précédent
        n'exerçait que les trois formes littérales que la regex reconnaissait déjà : il décrivait
        l'implémentation au lieu de l'éprouver. Les sept cas ci-dessous ont été **déposés pour de
        vrai** par le relecteur adversarial et **acceptés en 200** par la première rédaction.

        Deux familles, deux raisons :

        - **l'encodage** — le parseur XML décode les références de caractère *avant* d'interpréter
          un attribut, donc une recherche sur les octets bruts arrive toujours trop tard. On refuse
          la famille entière plutôt que de la poursuivre encodage par encodage ;
        - **l'indirection** — SMIL (`<set>`, `<animate>`) *écrit* un attribut sans jamais en porter
          la syntaxe, et `<use>`/`<image>` chargent un document tiers. Aucun logo n'en a besoin.

        Honnêteté sur la portée : ce refus reste une **denylist**, la barrière porteuse est la CSP
        de la route de service (cf. `Logo`). Ce corpus rend la première barrière non vide, il ne la
        rend pas exhaustive.
        """
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(hostile, TypeLogo.SVG)

    def test_un_doctype_nu_reste_accepte(self) -> None:
        """La contrepartie du cas « entité déclarée » ci-dessus : c'est `<!ENTITY` qui est refusée,
        pas la ligne `<!DOCTYPE>`. Illustrator en produit une depuis toujours ; la refuser aurait
        rendu le format inutilisable pour la moitié des logos de club, sans rien fermer."""
        doctype = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
        doctype += b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
        assert Logo.deposer(doctype + SVG_MINIMAL, TypeLogo.SVG).type_logo is TypeLogo.SVG

    def test_un_polyglotte_png_svg_est_refuse(self) -> None:
        """La signature PNG fait huit octets, et huit octets se recopient. Le relecteur adversarial
        a fait accepter — puis **servir** — un fichier annoncé `image/png` qui commençait par
        `\x89PNG` et continuait en SVG porteur de script.

        On exige donc la **structure** : `IHDR` en douzième position. Un document XML analysable
        depuis son premier octet ne peut pas porter ces quatre lettres à cet endroit."""
        polyglotte = (
            b"\x89PNG\r\n\x1a\n"
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        )
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(polyglotte, TypeLogo.PNG)

    def test_un_svg_dont_l_entete_depasse_mille_octets_est_accepte(self) -> None:
        """La balise `<svg` n'était cherchée que dans les 1 024 premiers octets : un export licite
        précédé d'une longue bannière de licence était refusé, avec un message qui **mentait** («
        ne contient pas de balise <svg> »). Elle est désormais cherchée sur tout le fichier."""
        banniere = b"<!-- " + b"licence " * 200 + b"-->"
        assert Logo.deposer(banniere + SVG_MINIMAL, TypeLogo.SVG).type_logo is TypeLogo.SVG

    def test_un_fichier_vide_est_refuse(self) -> None:
        with pytest.raises(TypeDeLogoRefuse):
            Logo.deposer(b"", TypeLogo.PNG)

    def test_un_fichier_trop_lourd_est_refuse_en_le_disant(self) -> None:
        """Arbitrage du 25/08/2026 : le fichier est stocké **en base** (blob), donc son poids passe
        par la file d'écriture unique (règle 7) et voyage dans chaque sauvegarde. Le borner n'est
        pas une coquetterie ; le refus **dit** la limite, il ne tronque pas en silence."""
        with pytest.raises(LogoTropVolumineux):
            Logo.deposer(PNG_MINIMAL + b"\x00" * POIDS_LOGO_MAX_OCTETS, TypeLogo.PNG)

    def test_un_fichier_juste_sous_la_limite_passe(self) -> None:
        """La borne est **inclusive** : sans ce test, une comparaison stricte d'un côté ou de
        l'autre passerait inaperçue, et l'écran annoncerait une limite que le serveur refuse."""
        bourrage = POIDS_LOGO_MAX_OCTETS - len(PNG_MINIMAL)
        assert Logo.deposer(PNG_MINIMAL + b"\x00" * bourrage, TypeLogo.PNG).poids_octets == (
            POIDS_LOGO_MAX_OCTETS
        )
