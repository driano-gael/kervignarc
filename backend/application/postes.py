"""Service applicatif Postes (E04US001, ADR-0029) — **préparation** des codes de cible &
**session** de poste (rattacher une tablette à sa cible).

Deux volets d'une même capacité, portés par un seul service (même parti que `ServiceScoreurs`) :

- **Préparation** (admin, `D-07` « tout se prépare à l'avance ») : `assurer_codes` garantit **un
  code par cible** du plan de salle du tournoi, de façon **idempotente** (les codes déjà émis ne
  changent pas — les QR sont imprimés). C'est le contrat que E09US008 imprimera.
- **Session** (le poste, `D-13` : identité = le *lieu*) : `rattacher` par code → jeton opaque en
  mémoire lié à la **cible** ; `resoudre_session` le retrouve à la réouverture (« sans rien demander
  à personne ») ; `deconnexion`. Le jeton n'est valide que tant que **son tournoi n'est pas
  terminé** — ancrage de la révocation « nouveau tournoi force le re-rattachement », compatible avec
  **plusieurs tournois non terminés** simultanés (intérieur + extérieur).

Le code est **attribué par le service** (le domaine ne voit qu'un poste, il ne peut garantir
l'unicité). La génération est **injectée** (`generer_code`) pour rester déterministe en test
(règle 9) ; elle **ré-essaie** en cas de collision (pré-contrôle `par_code`), la contrainte
`UNIQUE(code)` en base restant le garde-fou d'intégrité ultime.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import (
    CodePosteInconnu,
    DepartIntrouvable,
    NonAuthentifie,
    PosteIntrouvable,
    PosteNEstPasUnEcran,
    RattachementTournoiTermine,
    SaisieHorsCible,
    TournoiIntrouvable,
)
from domain.depart import Depart, DepartId
from domain.ecran import ReglagePages, SequenceVues
from domain.ports import (
    DepartRepository,
    GabaritSalleRepository,
    PosteRepository,
    RegistreConsignes,
    RegistrePresence,
    TournoiRepository,
)
from domain.poste import Poste, PosteId, TypePoste, normaliser_code
from domain.tournoi import StatutTournoi, TournoiId

_MAX_TENTATIVES_CODE = 100
"""Plafond de ré-essais de génération d'un code libre (cf. `ServiceScoreurs`).

Sur ~10^9 codes pour quelques dizaines de cibles, une collision est quasi impossible ; ce plafond
n'est qu'un garde-fou contre un générateur défectueux. L'atteindre est une **incohérence
technique** (`AssertionError` → 500 générique), jamais rencontrée en exploitation.
"""


def exiger_ecran(poste: Poste) -> Poste:
    """Refuse un poste de cible ; renvoie l'écran sinon (E07US004).

    Garde **réellement partagée** par `ServicePostes` (préparation, réglage) et `ServiceEcrans`
    (affichage, pilotage). Elle vit dans ce module et non dans `application.ecrans` parce que la
    dépendance ne va que dans ce sens : `ecrans.py` importe déjà `StoreSessionsPoste` d'ici, donc
    l'inverse serait circulaire. *(La première version la dupliquait ligne à ligne dans les deux
    services tout en affirmant en docstring qu'elle était partagée — corrigé en revue.)*

    La confusion n'est pas théorique : la console de supervision affiche cibles et écrans **côte à
    côte**, donc l'identifiant d'une tablette est à portée de clic de celui d'un écran.
    """
    if poste.type is not TypePoste.ECRAN:
        raise PosteNEstPasUnEcran(f"Le poste {poste.id} n'est pas un écran de salle.")
    return poste


class StoreSessionsPoste(Protocol):
    """Port : délivrance/validation de jetons de session de poste (en mémoire).

    Un jeton est lié à l'**identité de la cible** (l'`id` du poste). En mémoire, invalidé au
    redémarrage serveur (cohérent ADR-0025) et à la déconnexion ; la révocation « tournoi terminé »
    est appliquée à la **résolution** (le store ignore le cycle de vie du tournoi).
    """

    def ouvrir(self, poste_id: PosteId) -> str:
        """Ouvre une session pour un poste et renvoie son jeton opaque."""

    def poste_de(self, jeton: str | None) -> PosteId | None:
        """Identifiant du poste derrière un jeton valide, ou `None`."""

    def fixer_depart(self, jeton: str, depart_id: DepartId) -> None:
        """Fixe (ou change) le départ courant d'une session (ADR-0034) ; no-op si jeton inconnu."""

    def depart_de(self, jeton: str | None) -> DepartId | None:
        """Départ courant derrière un jeton valide, ou `None` (jeton inconnu ou départ non fixé)."""

    def fermer(self, jeton: str) -> None:
        """Ferme la session (déconnexion) ; sans effet si le jeton est inconnu."""

    def postes_rattaches(self) -> set[PosteId]:
        """Identifiants des postes ayant **au moins une** session ouverte (E12US001).

        Sert à la supervision : un poste sans session est *non rattaché* (code préparé, aucune
        tablette dessus). Deux tablettes sur la même cible ne comptent qu'une fois (un `set`).
        """

    def depart_courant_par_poste(self) -> dict[PosteId, DepartId]:
        """Départ courant **représentatif** de chaque poste rattaché qui en a fixé un (E12US001).

        Sert à la supervision pour situer l'avancement d'une cible. Un poste sans départ fixé est
        absent de la table. Si deux tablettes d'une même cible ont fixé des départs différents (cas
        de bord, `depart_courant` est par jeton, ADR-0034), un seul est retenu — l'avancement reste
        un indicateur de diagnostic, pas une donnée d'autorité.
        """

    def invalider_poste(self, poste_id: PosteId) -> None:
        """Ferme **toutes** les sessions d'un poste (révocation admin, E12US001, `D-07`).

        Modelé sur `invalider_scoreur` : la tablette repasse *non rattachée* et retombe, à la
        prochaine résolution, sur l'écran de rattachement. Sans effet si pas de session.
        """


@dataclass(frozen=True)
class ConnexionPoste:
    """Résultat d'un rattachement : le jeton de session **et** le poste rattaché (sa cible).

    Le `poste` accompagne le jeton pour que le client sache **quelle cible** il sert (tournoi +
    numéro de cible), sans avoir à le redemander.
    """

    jeton: str
    poste: Poste


class ServicePostes:
    """Cas d'usage des postes : préparation des codes (admin) et session (poste)."""

    def __init__(
        self,
        poste_repository: PosteRepository,
        tournoi_repository: TournoiRepository,
        gabarit_repository: GabaritSalleRepository,
        depart_repository: DepartRepository,
        sessions: StoreSessionsPoste,
        consignes: RegistreConsignes,
        presence: RegistrePresence,
        generer_code: Callable[[], str],
    ) -> None:
        self._postes = poste_repository
        self._tournois = tournoi_repository
        self._gabarits = gabarit_repository
        self._departs = depart_repository
        self._sessions = sessions
        self._consignes = consignes
        self._presence = presence
        self._generer_code = generer_code

    # --- Préparation des codes (admin) ---

    def assurer_codes(self, tournoi_id: TournoiId) -> list[Poste]:
        """Garantit **un code par cible** du plan et renvoie tous ses postes (triés par cible).

        **Idempotent** : ne crée que les postes manquants ; les codes déjà émis (QR imprimés) sont
        **préservés**. Un tournoi **sans plan de salle** (aucun gabarit) n'a pas de cible : la liste
        est vide. Lève `TournoiIntrouvable` si le tournoi n'existe pas. Aucune garde de statut : les
        codes se préparent **à l'avance** (`D-07`), y compris sur un brouillon. Lecture du plan,
        pré-contrôle des codes et insertions tiennent dans **une seule commande** en file (règle 7).
        """
        self._verifier_tournoi(tournoi_id)
        existants = {poste.cible(): poste for poste in self._cibles(tournoi_id)}
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is not None:
            for cible in gabarit.cibles:
                if cible.index not in existants:
                    code = self._allouer_code()
                    existants[cible.index] = self._postes.ajouter(
                        Poste.creer(tournoi_id, cible.index, code)
                    )
        return [existants[index] for index in sorted(existants)]

    def lister(self, tournoi_id: TournoiId) -> list[Poste]:
        """Renvoie les postes de **cible** déjà préparés d'un tournoi (triés), **sans rien créer**.

        Lecture pour l'admin (afficher les codes à distribuer/imprimer). Lève `TournoiIntrouvable`
        si le tournoi n'existe pas ; liste vide tant qu'aucun code n'a été préparé. Les **écrans**
        de salle (E07US004) sont exclus : ils ne se préparent pas depuis le plan de salle et se
        listent par `ServiceEcrans.lister`.
        """
        self._verifier_tournoi(tournoi_id)
        return sorted(self._cibles(tournoi_id), key=lambda poste: poste.cible())

    # --- Écrans de salle (E07US004) ---

    def creer_ecran(self, tournoi_id: TournoiId, libelle: str) -> Poste:
        """Crée un écran de salle et lui alloue un code distribuable (QR ou saisie de secours).

        **Création explicite**, à l'inverse des cibles (`assurer_codes`, dérivées du plan) :
        aucun gabarit ne dit combien d'écrans le club branchera ni où. C'est aussi pourquoi le CA
        parle de « plusieurs écrans possibles, chacun son déroulé » — la liste est ouverte.

        Aucune garde de statut, comme pour les codes de cible : un écran se prépare **à l'avance**
        (`D-07`), y compris sur un brouillon.
        """
        self._verifier_tournoi(tournoi_id)
        return self._postes.ajouter(Poste.creer_ecran(tournoi_id, libelle, self._allouer_code()))

    def renommer_ecran(self, tournoi_id: TournoiId, poste_id: PosteId, libelle: str) -> Poste:
        """Renomme un écran (il a déménagé). Le **code reste** : le QR est peut-être imprimé."""
        ecran = self._exiger_ecran(tournoi_id, poste_id)
        return self._postes.enregistrer(ecran.avec_libelle(libelle))

    def regler_deroule_ecran(
        self, tournoi_id: TournoiId, poste_id: PosteId, deroule: SequenceVues
    ) -> Poste:
        """Fixe le déroulé de vues d'un écran — le réglage « à la préparation du tournoi » du CA.

        Persisté (contrairement à la prise de contrôle, volatile) : c'est un réglage de préparation,
        il doit survivre au redémarrage du serveur le matin du jour J.
        """
        ecran = self._exiger_ecran(tournoi_id, poste_id)
        return self._postes.enregistrer(ecran.avec_deroule(deroule))

    def regler_pages_ecran(
        self, tournoi_id: TournoiId, poste_id: PosteId, pages: ReglagePages
    ) -> Poste:
        """Fixe le découpage et la cadence des listes projetées par un écran (E16US009).

        **Un geste distinct du déroulé**, et non un champ de plus sur `regler_deroule_ecran` : le
        déroulé dit *quelles vues et pendant combien de temps*, celui-ci dit *comment une liste se
        lit à dix mètres*. Ils se règlent à des moments différents (l'un à la préparation, l'autre
        une fois le projecteur branché dans la salle) et le second se corrige seul, sans avoir à
        renvoyer la séquence de vues entière — ce qui, à l'inverse, exposait à l'écraser par
        inadvertance.

        Persisté pour la même raison que le déroulé : le réglage doit survivre au redémarrage du
        matin du jour J.
        """
        ecran = self._exiger_ecran(tournoi_id, poste_id)
        return self._postes.enregistrer(ecran.avec_pages(pages))

    def supprimer_ecran(self, tournoi_id: TournoiId, poste_id: PosteId) -> None:
        """Retire un écran : sessions, consigne et présence oubliées, puis ligne supprimée.

        Fermer les sessions **avant** évite qu'un appareil branché sur cet écran continue de
        résoudre un poste disparu. Le reste n'est pas cosmétique : SQLite **réattribue** les
        identifiants libérés, donc **tout** état volatil indexé par ce `poste_id` serait hérité par
        le prochain poste créé — une consigne orpheline figerait un écran neuf sur un podium que
        personne n'a demandé, une présence orpheline le ferait naître « en ligne ». Le nettoyage
        couvre donc les **trois** registres, comme `ServiceSupervision.revoquer_poste` — que la
        version d'origine citait en modèle tout en n'en reprenant que deux tiers (correctif de
        revue).

        La suppression est réservée aux écrans : le code d'une cible est imprimé sous un QR, le
        supprimer invaliderait une affiche déjà posée.
        """
        self._exiger_ecran(tournoi_id, poste_id)
        self._sessions.invalider_poste(poste_id)
        self._consignes.retirer(poste_id)
        self._presence.oublier(poste_id)
        self._postes.supprimer(poste_id)

    # --- Session (poste) ---

    def rattacher(self, code: str) -> ConnexionPoste:
        """Rattache une tablette à la cible dont c'est le code (scan du QR ou code de secours).

        Lève `CodePosteInconnu` (→ 401) si aucun poste ne porte ce code,
        `RattachementTournoiTermine` (→ 409) si le tournoi de la cible est terminé (piège « le jeton
        survit trop bien »). La saisie est **normalisée** (casse, espaces) : « c1 » rattache « C1 ».
        """
        poste = self._postes.par_code(normaliser_code(code))
        if poste is None or poste.id is None:
            raise CodePosteInconnu("Code de cible inconnu.")
        self._refuser_si_termine(poste.tournoi_id)
        jeton = self._sessions.ouvrir(poste.id)
        return ConnexionPoste(jeton=jeton, poste=poste)

    def resoudre_session(self, jeton: str | None) -> Poste | None:
        """Poste derrière un jeton **encore valide**, ou `None` (réouverture « retrouve sa cible »).

        Renvoie `None` si le jeton est inconnu, si le poste a disparu, **ou si son tournoi est
        terminé** (révocation) : le front purge alors le jeton et redemande un rattachement.
        """
        poste_id = self._sessions.poste_de(jeton)
        if poste_id is None:
            return None
        poste = self._postes.par_id(poste_id)
        if poste is None:
            return None
        tournoi = self._tournois.par_id(poste.tournoi_id)
        if tournoi is None or tournoi.statut is StatutTournoi.TERMINE:
            return None
        return poste

    def session_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton correspond à une session de poste encore valide (`exiger_poste`)."""
        return self.resoudre_session(jeton) is not None

    def fixer_depart_courant(self, jeton: str | None, depart_id: DepartId) -> Depart:
        """Met le poste « en mode départ X » : fixe son départ courant (geste manuel, ADR-0034).

        Primitive **un poste, un départ** qu'E12US002 (« lancer un tour ») orchestrera pour *tous*
        les postes d'un coup — même point d'entrée, réutilisé. Auto-gardée pour rester correcte hors
        HTTP (l'orchestrateur l'appellera sans passer par `exiger_poste`) :

        - `NonAuthentifie` (→ 401) si le jeton ne résout **aucune** session de poste valide ;
        - `DepartIntrouvable` (→ 404) si le départ n'existe pas **ou** relève d'un autre tournoi que
          celui du poste (ADR-0034 §4 : le lien est *posé*, jamais deviné ; même parti que partout,
          un départ d'un tournoi voisin n'existe pas plus qu'un identifiant inventé).

        La légalité **fine** de la saisie (l'archer est-il affecté à `(cible, départ)` ?) n'est
        pas vérifiée ici : elle reste au service de saisie (ADR-0033 §3). Renvoie le départ fixé
        pour que le poste confirme *quel* créneau il sert.
        """
        poste = self.resoudre_session(jeton)
        if poste is None:
            raise NonAuthentifie("Session de poste requise.")
        # ⚠️ **Garde de nature, ici et pas seulement à la frontière** (correctif de 2ᵉ passe).
        # La docstring ci-dessus annonce un appelant **hors HTTP** (E12US002, l'orchestrateur de
        # lancement) : la dépendance `exiger_poste_de_cible` ne le couvrirait pas. C'est exactement
        # la leçon tirée dans `ServiceArchers._verifier_poste_sert_l_archer` — une garde posée à un
        # seul niveau se contourne par le chemin qu'on n'avait pas prévu — et elle n'avait pas été
        # rejouée ici.
        if poste.type is not TypePoste.CIBLE:
            raise SaisieHorsCible("Un écran de salle ne fixe pas de départ courant.")
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != poste.tournoi_id:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id} dans ce tournoi.")
        assert jeton is not None  # resoudre_session n'aurait pas rendu de poste sinon
        self._sessions.fixer_depart(jeton, depart_id)
        return depart

    def depart_courant(self, jeton: str | None) -> DepartId | None:
        """Départ courant du poste derrière ce jeton, ou `None` s'il n'en a pas encore fixé.

        `None` **interdit la saisie** (le poste ne sait pas qui afficher) — refus explicite porté
        par le service de saisie, jamais un affichage vide ambigu (ADR-0034 §1).
        """
        return self._sessions.depart_de(jeton)

    def deconnexion(self, jeton: str) -> None:
        """Ferme la session associée au jeton."""
        self._sessions.fermer(jeton)

    # --- Gardes internes ---

    def _cibles(self, tournoi_id: TournoiId) -> list[Poste]:
        """Les postes de **cible** — jamais `par_tournoi`, qui rend aussi les écrans."""
        return self._postes.par_tournoi_et_type(tournoi_id, TypePoste.CIBLE)

    def _exiger_ecran(self, tournoi_id: TournoiId, poste_id: PosteId) -> Poste:
        """L'écran d'identifiant donné dans ce tournoi, ou l'erreur qui convient.

        `PosteIntrouvable` couvre le poste d'un **autre** tournoi (ADR-0034 §4) ; la garde de nature
        est déléguée à `exiger_ecran`, **partagée** avec `ServiceEcrans` (qui importe déjà ce
        module — l'inverse serait circulaire).
        """
        poste = self._postes.par_id(poste_id)
        if poste is None or poste.tournoi_id != tournoi_id:
            raise PosteIntrouvable(f"Aucun poste d'identifiant {poste_id} dans ce tournoi.")
        return exiger_ecran(poste)

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _refuser_si_termine(self, tournoi_id: TournoiId) -> None:
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None or tournoi.statut is StatutTournoi.TERMINE:
            raise RattachementTournoiTermine(
                "Le tournoi de cette cible est terminé : rattachement impossible."
            )

    def _allouer_code(self) -> str:
        """Génère un code libre (ré-essai en cas de collision, cf. `_MAX_TENTATIVES_CODE`)."""
        for _ in range(_MAX_TENTATIVES_CODE):
            code = normaliser_code(self._generer_code())
            if self._postes.par_code(code) is None:
                return code
        raise AssertionError("Impossible de générer un code de poste unique.")
