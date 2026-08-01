"""Service applicatif des **écrans de salle** (E07US004, ADR-0064) — que montre cet écran, et
qui décide.

Deux cas d'usage, deux publics :

- **l'écran** demande `affichage(jeton)` : ce qu'il doit montrer *maintenant* — son déroulé, ou la
  consigne que l'admin lui a imposée, avec le temps restant ;
- **l'admin** pose (`prendre_le_controle`) et retire (`rendre_la_main`) des consignes, et lit
  `prises` pour sa console.

**Le pilotage est un état lu, pas un ordre poussé** — la décision centrale d'ADR-0064. Deux raisons,
la seconde suffirait :

1. Le hub temps réel est **mono-canal** (`infrastructure.realtime.broadcaster`) : il diffuse à tous
   les abonnés, sans ciblage par destinataire. Pousser un ordre à *un* écran demanderait
   l'abonnement par sujet, qui n'existe pas.
2. Surtout, la **fin** d'une prise de contrôle naît du **temps qui passe** — et aucun événement
   serveur ne peut pousser le temps qui passe. C'est mot pour mot le raisonnement d'ADR-0038 §4 sur
   le passage hors-ligne d'un poste, qui a valu à la supervision d'être en *poll* plutôt qu'en
   WebSocket. Une prise « podium 10 min » se termine donc **sans que rien ne soit envoyé**.

Conséquence pratique : la reprise du déroulé ne dépend d'aucun message. Un écran qui perd le réseau
pendant la prise reprend quand même à l'heure — il connaît le début et la durée, il décompte en
local (`domain.ecran.reste_secondes`).

Lecture synchrone hors boucle événementielle (règle 7) : le registre de consignes est en mémoire,
les postes en base (lectures courtes). Aucune écriture en file — poser une consigne ne touche que
de l'état volatil.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import (
    NonAuthentifie,
    PosteIntrouvable,
    PosteNEstPasUnEcran,
    TournoiIntrouvable,
)
from application.postes import StoreSessionsPoste
from domain.ecran import Consigne, PriseDeControle, SequenceVues, VueEcran, reste_secondes
from domain.ports import Horloge, PosteRepository, RegistreConsignes, TournoiRepository
from domain.poste import Poste, PosteId, TypePoste
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class AffichageEcran:
    """Ce qu'un écran doit montrer à cet instant.

    **Exactement l'un** de `sequence` (il tourne) ou `vue_figee` (il est figé) est renseigné —
    l'écran n'a donc jamais à arbitrer. `reste_s` alimente son propre compte à rebours ; `None`
    signifie soit « pas sous contrôle », soit « sous contrôle sans échéance », que `sous_controle`
    permet de distinguer.
    """

    sequence: SequenceVues | None
    vue_figee: VueEcran | None
    sous_controle: bool
    reste_s: float | None


@dataclass(frozen=True)
class PriseActive:
    """Une prise de contrôle en vigueur, vue de la console de supervision.

    `exige_rappel` porte le CA « jamais un état forcé qu'on oublie » jusqu'à l'UI : c'est lui qui
    déclenche le rappel très visible sur les prises sans échéance.
    """

    poste_id: PosteId
    vue_figee: VueEcran | None
    reste_s: float | None
    exige_rappel: bool


class ServiceEcrans:
    """Cas d'usage des écrans de salle : affichage courant et prise de contrôle admin."""

    def __init__(
        self,
        poste_repository: PosteRepository,
        tournoi_repository: TournoiRepository,
        sessions: StoreSessionsPoste,
        consignes: RegistreConsignes,
        horloge: Horloge,
    ) -> None:
        self._postes = poste_repository
        self._tournois = tournoi_repository
        self._sessions = sessions
        self._consignes = consignes
        self._horloge = horloge

    # --- Côté écran ---

    def affichage(self, jeton: str | None) -> AffichageEcran:
        """Ce que l'écran derrière ce jeton doit montrer maintenant.

        `NonAuthentifie` (→ 401) si le jeton ne résout aucune session valide,
        `PosteNEstPasUnEcran` (→ 409) s'il résout une **cible** : la portée « poste » est commune
        aux deux natures (même en-tête, même store), donc la garde de nature est ici — un jeton de
        tablette ne doit pas ouvrir l'affichage d'un écran.
        """
        poste_id = self._sessions.poste_de(jeton)
        if poste_id is None:
            raise NonAuthentifie("Session de poste requise.")
        poste = self._postes.par_id(poste_id)
        if poste is None:
            raise NonAuthentifie("Session de poste requise.")
        ecran = _exiger_ecran(poste)
        prise = self._prise_en_vigueur(poste_id)
        if prise is None:
            return AffichageEcran(
                sequence=ecran.deroule_effectif,
                vue_figee=None,
                sous_controle=False,
                reste_s=None,
            )
        return AffichageEcran(
            sequence=prise.consigne.sequence,
            vue_figee=prise.consigne.vue,
            sous_controle=True,
            reste_s=self._reste(prise),
        )

    # --- Côté admin ---

    def lister(self, tournoi_id: TournoiId) -> list[Poste]:
        """Les écrans de salle d'un tournoi. `TournoiIntrouvable` si le tournoi n'existe pas."""
        self._verifier_tournoi(tournoi_id)
        return self._postes.par_tournoi_et_type(tournoi_id, TypePoste.ECRAN)

    def prendre_le_controle(
        self, tournoi_id: TournoiId, poste_id: PosteId, consigne: Consigne
    ) -> PriseActive:
        """Impose une vue figée ou une autre séquence à un écran, à partir de maintenant.

        Une prise **remplace** la précédente (dernière volonté de l'organisateur). L'instant de pose
        vient du port `Horloge` : c'est le service qui lit l'heure, jamais le domaine.
        """
        self._exiger_ecran_du_tournoi(tournoi_id, poste_id)
        prise = PriseDeControle(consigne=consigne, debut=self._horloge.maintenant())
        self._consignes.poser(poste_id, prise)
        return PriseActive(
            poste_id=poste_id,
            vue_figee=consigne.vue,
            reste_s=self._reste(prise),
            exige_rappel=consigne.exige_rappel,
        )

    def rendre_la_main(self, tournoi_id: TournoiId, poste_id: PosteId) -> None:
        """Retire la consigne : l'écran reprend son déroulé à sa prochaine lecture.

        **Idempotent** (comme la révocation d'un poste) : rendre la main sur un écran libre est sans
        effet. Un double clic depuis la console n'est pas une erreur à signaler à l'organisateur.
        """
        self._exiger_ecran_du_tournoi(tournoi_id, poste_id)
        self._consignes.retirer(poste_id)

    def prises(self, tournoi_id: TournoiId) -> dict[PosteId, PriseActive]:
        """Les prises **encore en vigueur** sur les écrans de ce tournoi, pour la console.

        Les prises échues sont **retirées au passage** plutôt que filtrées : sans cela, le registre
        garderait des consignes mortes que « rendre la main » proposerait encore d'annuler. C'est le
        même parti que la supervision, où l'état se dérive à la lecture.
        """
        ecrans = {p.id for p in self._postes.par_tournoi_et_type(tournoi_id, TypePoste.ECRAN)}
        actives: dict[PosteId, PriseActive] = {}
        for poste_id, prise in self._consignes.toutes().items():
            if poste_id not in ecrans:
                continue
            if self._retirer_si_echue(poste_id, prise):
                continue
            actives[poste_id] = PriseActive(
                poste_id=poste_id,
                vue_figee=prise.consigne.vue,
                reste_s=self._reste(prise),
                exige_rappel=prise.consigne.exige_rappel,
            )
        return actives

    # --- Gardes et calculs internes ---

    def _prise_en_vigueur(self, poste_id: PosteId) -> PriseDeControle | None:
        """La prise de cet écran si elle n'est pas échue, sinon `None` (et elle est retirée)."""
        prise = self._consignes.prise_de(poste_id)
        if prise is None or self._retirer_si_echue(poste_id, prise):
            return None
        return prise

    def _retirer_si_echue(self, poste_id: PosteId, prise: PriseDeControle) -> bool:
        """Vrai si la prise était échue — auquel cas elle vient d'être retirée du registre."""
        if not prise.consigne.expiree(secondes_ecoulees=self._ecoulees(prise)):
            return False
        self._consignes.retirer(poste_id)
        return True

    def _ecoulees(self, prise: PriseDeControle) -> float:
        return (self._horloge.maintenant() - prise.debut).total_seconds()

    def _reste(self, prise: PriseDeControle) -> float | None:
        return reste_secondes(prise.consigne, secondes_ecoulees=self._ecoulees(prise))

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_ecran_du_tournoi(self, tournoi_id: TournoiId, poste_id: PosteId) -> Poste:
        """L'écran d'identifiant donné **dans ce tournoi**, ou l'erreur qui va bien.

        `PosteIntrouvable` couvre aussi le poste d'un **autre** tournoi : même parti que partout
        (ADR-0034 §4), un poste d'un tournoi voisin n'existe pas plus qu'un identifiant inventé.
        """
        poste = self._postes.par_id(poste_id)
        if poste is None or poste.tournoi_id != tournoi_id:
            raise PosteIntrouvable(f"Aucun poste d'identifiant {poste_id} dans ce tournoi.")
        return _exiger_ecran(poste)


def _exiger_ecran(poste: Poste) -> Poste:
    """Refuse un poste de cible ; renvoie l'écran sinon.

    Garde partagée par le service des écrans et `ServicePostes` (réglage du déroulé) : la console
    affiche cibles et écrans **côte à côte**, donc l'identifiant d'une tablette est à portée de clic
    de celui d'un écran. La confusion n'est pas théorique.
    """
    if poste.type is not TypePoste.ECRAN:
        raise PosteNEstPasUnEcran(f"Le poste {poste.id} n'est pas un écran de salle.")
    return poste
