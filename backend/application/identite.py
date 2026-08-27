"""Service de l'**identité visuelle** — un logo ne touche aucun score (`P-3`, ADR-0097).

⚠️ **Le contrôle de contraste est un CALCUL, pas une garde** (`P-4`) : aucun `raise`, on rend le
chiffre et l'organisateur décide. Refuser retirerait sa marque à qui a une charte faible, ce que
`DV-05` interdit. Seul refus : un tournoi **archivé** (ADR-0026 §1) — et l'erreur est celle du
registre applicatif, jamais une classe locale de même nom.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from application.erreurs import TournoiArchiveNonModifiable, TournoiIntrouvable
from domain.identite import (
    FOND_CLAIR,
    FOND_SOMBRE,
    Couleur,
    EmplacementLogo,
    IdentiteVisuelle,
    JetonsDeMarque,
    Logo,
    TypeLogo,
    contraste,
    deriver_marque,
)
from domain.ports import IdentiteVisuelleRepository, TournoiRepository
from domain.tournoi import StatutTournoi, TournoiId


@dataclass(frozen=True)
class AccentDecline:
    """Un accent, décliné sur les deux thèmes, avec le chiffre de son contraste brut.

    Le **chiffre** est ce que `P-4` exige : « une alerte qui ne chiffre pas son impact est un clic
    de plus, pas une protection » (`D-16`). Il porte sur la couleur **telle que fournie** — c'est le
    seul nombre qui dise quelque chose à l'organisateur sur *sa* couleur ; les variantes dérivées,
    elles, sont conformes par construction et leur ratio n'apprendrait rien.
    """

    couleur: Couleur
    sombre: JetonsDeMarque
    clair: JetonsDeMarque
    contraste_sur_sombre: float
    contraste_sur_clair: float


@dataclass(frozen=True)
class IdentiteDeclinee:
    """L'identité d'un tournoi, prête à poser : deux accents déclinés, et les logos présents.

    ⚠️ **La déclinaison est faite ici, pas dans le navigateur.** Le front reçoit des valeurs de
    jetons à appliquer, jamais une couleur à recalculer : la règle de dérivation n'a qu'une
    implémentation, testée sous `mypy --strict` (règle 2). La recopier en TypeScript aurait produit
    une seconde vérité, et le mode de panne aurait été silencieux — un contraste faux ne lève pas
    d'exception, il devient seulement illisible dans un gymnase.
    """

    reglee: bool
    """`False` : rien n'a été choisi, l'identité affichée est **héritée** de celle du club."""

    primaire: AccentDecline
    secondaire: AccentDecline
    empreintes: Mapping[EmplacementLogo, str]
    """Emplacement pourvu → empreinte de son contenu. Les absents n'y sont pas.

    L'empreinte descend jusqu'au DTO parce qu'elle **est** le numéro de version que le front pose
    dans l'URL du logo : sans elle, une image déjà montée ne se redemande jamais, et un logo corrigé
    reste invisible jusqu'au rechargement de la page (relevé en revue, mesuré).
    """


class ServiceIdentite:
    """Cas d'usage de l'identité visuelle d'un tournoi."""

    def __init__(
        self,
        identites: IdentiteVisuelleRepository,
        tournois: TournoiRepository,
    ) -> None:
        self._identites = identites
        self._tournois = tournois

    def pour_tournoi(self, tournoi_id: TournoiId) -> IdentiteDeclinee:
        """Rend l'identité d'un tournoi, déclinée. `TournoiIntrouvable` si le tournoi n'existe pas.

        **Lecture publique** : c'est ce que l'écran de salle et l'appli du spectateur consomment, et
        il n'y a rien de confidentiel dans une couleur projetée sur un mur de gymnase.
        """
        self._exiger_le_tournoi(tournoi_id)
        return decliner(self._identites.reglages(tournoi_id))

    def regler_accents(
        self, tournoi_id: TournoiId, primaire: str, secondaire: str
    ) -> IdentiteDeclinee:
        """Enregistre les deux accents (saisies `#RRGGBB`) et rend l'identité déclinée.

        `CouleurInvalide` (domaine → 422) sur une saisie mal formée ; **aucun refus** sur un
        contraste faible (`P-4`). Part d'une identité vide plutôt que de relire l'existant : les
        deux accents sont écrits **ensemble**, il n'y a pas d'état intermédiaire à préserver. La
        présence des logos n'est pas touchée — c'est le port qui la conserve.
        """
        self._exiger_le_tournoi(tournoi_id, modification=True)
        identite = IdentiteVisuelle().avec_accents(
            Couleur.depuis_hex(primaire), Couleur.depuis_hex(secondaire)
        )
        return decliner(self._identites.enregistrer_accents(tournoi_id, identite))

    def deposer_logo(
        self,
        tournoi_id: TournoiId,
        emplacement: EmplacementLogo,
        contenu: bytes,
        type_logo: TypeLogo,
    ) -> IdentiteDeclinee:
        """Dépose (ou remplace) un logo. `TypeDeLogoRefuse` / `LogoTropVolumineux` → 422.

        La validation du fichier est **entièrement** dans `Logo.deposer` : le service ne regarde pas
        un octet. C'est ce qui fait que le refus d'un SVG porteur de script est testable sans
        serveur, et qu'il ne peut pas diverger d'une route à l'autre.
        """
        self._exiger_le_tournoi(tournoi_id, modification=True)
        logo = Logo.deposer(contenu, type_logo)
        return self._apres_ecriture_de_logo(tournoi_id, emplacement, logo)

    def retirer_logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> IdentiteDeclinee:
        """Vide un emplacement. **Idempotent** : retirer un logo absent n'est pas une erreur.

        Un `404` sur un emplacement déjà vide ferait échouer le second clic d'un organisateur qui
        n'est pas sûr d'avoir cliqué — geste ordinaire sur une tablette, et l'état visé est atteint
        dans les deux cas.
        """
        self._exiger_le_tournoi(tournoi_id, modification=True)
        return self._apres_ecriture_de_logo(tournoi_id, emplacement, None)

    def logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> Logo | None:
        """Rend les octets d'un logo, ou `None` si l'emplacement est vide (l'API en fait un 404).

        Ne vérifie **pas** l'existence du tournoi : une lecture qui n'a rien trouvé rend `None`, et
        distinguer « tournoi inconnu » de « pas de logo » coûterait une requête de plus sur la seule
        route que ~30 tablettes et un vidéoprojecteur appellent ensemble. Les deux cas se répondent
        de la même façon à un navigateur qui affiche une image.
        """
        return self._identites.logo(tournoi_id, emplacement)

    def empreinte_du_logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> str | None:
        """Rend la version d'un logo sans en charger les octets — `None` si l'emplacement est vide.

        Même contrat que `logo` : **ne vérifie pas** l'existence du tournoi. C'est ce qui permet à
        la
        route publique de répondre `304` sans toucher au blob, sur la seule route que trente
        tablettes et un vidéoprojecteur appellent ensemble.
        """
        return self._identites.empreinte_du_logo(tournoi_id, emplacement)

    def _apres_ecriture_de_logo(
        self, tournoi_id: TournoiId, emplacement: EmplacementLogo, logo: Logo | None
    ) -> IdentiteDeclinee:
        """Écrit l'emplacement et rend l'identité relue.

        ⚠️ La ligne d'identité peut naître **ici** (le port la crée au besoin) sans qu'aucune couleur
        n'ait été choisie : `reglee` reste alors `false`, parce qu'il se lit sur les accents et non
        sur l'existence de la ligne. Déposer un logo n'est pas choisir des couleurs.
        """
        return decliner(self._identites.enregistrer_logo(tournoi_id, emplacement, logo))

    def _exiger_le_tournoi(self, tournoi_id: TournoiId, *, modification: bool = False) -> None:
        """Vérifie l'existence, et le verrou d'archive quand on s'apprête à écrire."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Tournoi {tournoi_id} introuvable.")
        if modification and tournoi.statut is StatutTournoi.ARCHIVE:
            raise TournoiArchiveNonModifiable(
                "Ce tournoi est archivé : son identité visuelle ne peut plus changer."
            )


def decliner(identite: IdentiteVisuelle) -> IdentiteDeclinee:
    """Décline une identité sur les deux thèmes — fonction pure, **exposée pour l'aperçu**.

    L'écran d'identité s'en sert **avant** d'enregistrer : l'organisateur voit le rendu et le
    chiffre de contraste pendant qu'il choisit, ce qui est le sens de « contrôle **à la saisie** ».
    Sans cette porte, l'aperçu aurait dû recalculer côté navigateur — donc dupliquer la règle.
    """
    primaire, secondaire = identite.accents
    return IdentiteDeclinee(
        reglee=identite.reglee,
        primaire=_decliner_un_accent(primaire),
        secondaire=_decliner_un_accent(secondaire),
        empreintes=identite.empreintes,
    )


def _decliner_un_accent(accent: Couleur) -> AccentDecline:
    """Décline un accent sur les deux fonds, et mesure son contraste brut sur chacun."""
    return AccentDecline(
        couleur=accent,
        sombre=deriver_marque(accent, FOND_SOMBRE),
        clair=deriver_marque(accent, FOND_CLAIR),
        contraste_sur_sombre=contraste(accent, FOND_SOMBRE),
        contraste_sur_clair=contraste(accent, FOND_CLAIR),
    )
