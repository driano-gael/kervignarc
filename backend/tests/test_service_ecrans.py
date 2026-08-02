"""Tests du service des écrans de salle (E07US004) — **dérivés du CA**, avant impl (règle 9).

Source : `stories/E07-affichage-public.md`, E07US004, puces « CA — poste rattaché & déroulé » et
« CA — pilotage admin », plus l'arbitrage **Q-UX7** du 01/08/2026 (durée **et** retour explicite).

On isole le service : **vrais** store de sessions et registre de consignes (en mémoire,
déterministes — ce qui couvre aussi l'adapter), faux repositories, **horloge réglable**. Le temps
est le sujet même de la moitié de ces tests : une prise de contrôle se termine « toute seule »
*parce que le temps passe*, sans qu'aucun événement ne survienne.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.ecrans import ServiceEcrans
from application.erreurs import PosteIntrouvable, PosteNEstPasUnEcran, SaisieHorsCible
from application.postes import ServicePostes
from domain.ecran import Consigne, SequenceVues, VueEcran, VueProgrammee
from domain.poste import Poste, PosteId, TypePoste
from domain.tournoi import StatutTournoi, Tournoi, TournoiId
from infrastructure.postes.consignes import RegistreConsignesMemoire
from infrastructure.postes.presence import RegistrePresenceMemoire
from infrastructure.postes.sessions import PosteSessionStore

_DATE = datetime.date(2026, 3, 14)
_T0 = datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.UTC)


class HorlogeReglable:
    """Horloge conforme au port `Horloge`, avançable à la main (déterminisme, règle 9)."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant

    def avancer(self, secondes: float) -> None:
        self._instant += datetime.timedelta(seconds=secondes)


class FauxPosteRepository:
    """Repository de postes en mémoire conforme au port `PosteRepository`."""

    def __init__(self) -> None:
        self._postes: dict[int, Poste] = {}
        self._sequence = 0

    def ajouter(self, poste: Poste) -> Poste:
        self._sequence += 1
        persiste = dataclasses.replace(poste, id=self._sequence)
        self._postes[self._sequence] = persiste
        return persiste

    def enregistrer(self, poste: Poste) -> Poste:
        assert poste.id is not None
        self._postes[poste.id] = poste
        return poste

    def supprimer(self, poste_id: PosteId) -> None:
        self._postes.pop(poste_id, None)

    def par_id(self, poste_id: PosteId) -> Poste | None:
        return self._postes.get(poste_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        return [p for p in self._postes.values() if p.tournoi_id == tournoi_id]

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_poste: TypePoste) -> list[Poste]:
        return [p for p in self.par_tournoi(tournoi_id) if p.type is type_poste]

    def par_code(self, code: str) -> Poste | None:
        return next((p for p in self._postes.values() if p.code == code), None)


class FauxTournoiRepository:
    """Repository de tournois en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        self._tournois.pop(tournoi_id, None)


class FauxGabaritRepository:
    """Assez de port pour `ServicePostes` : aucun plan de salle (les écrans n'en dépendent pas)."""

    def par_tournoi(self, tournoi_id: TournoiId) -> None:
        return None


class FauxDepartRepository:
    """Assez de port pour `ServicePostes` : aucun départ (hors sujet ici)."""

    def par_id(self, depart_id: int) -> None:
        return None


class Contexte:
    """Le montage complet : un tournoi en cours, un service de postes, un service d'écrans."""

    def __init__(self) -> None:
        self.horloge = HorlogeReglable(_T0)
        self.postes_repo = FauxPosteRepository()
        self.tournois = FauxTournoiRepository()
        self.sessions = PosteSessionStore()
        self.consignes = RegistreConsignesMemoire()
        self.presence = RegistrePresenceMemoire()
        self._codes = iter(f"CODE{n:02d}" for n in range(1, 100))
        self.tournoi = self.tournois.ajouter(
            dataclasses.replace(Tournoi.creer("Tournoi", _DATE), statut=StatutTournoi.EN_COURS)
        )
        assert self.tournoi.id is not None
        self.tournoi_id: TournoiId = self.tournoi.id
        self.service_postes = ServicePostes(
            poste_repository=self.postes_repo,
            tournoi_repository=self.tournois,
            gabarit_repository=FauxGabaritRepository(),  # type: ignore[arg-type]
            depart_repository=FauxDepartRepository(),  # type: ignore[arg-type]
            sessions=self.sessions,
            consignes=self.consignes,
            presence=self.presence,
            generer_code=lambda: next(self._codes),
        )
        self.service = ServiceEcrans(
            poste_repository=self.postes_repo,
            tournoi_repository=self.tournois,
            sessions=self.sessions,
            consignes=self.consignes,
            horloge=self.horloge,
        )

    def ecran(self, libelle: str = "Près du pas de tir") -> Poste:
        return self.service_postes.creer_ecran(self.tournoi_id, libelle)


@pytest.fixture
def ctx() -> Contexte:
    return Contexte()


# --- CA « poste rattaché & déroulé » --------------------------------------------------------------


def test_un_ecran_se_cree_avec_un_code_distribuable(ctx: Contexte) -> None:
    """« l'écran est un poste rattaché par **jeton** (même mécanisme que la tablette) » : il lui
    faut donc, comme à une cible, un **code** à scanner ou retaper."""
    ecran = ctx.ecran()

    assert ecran.type is TypePoste.ECRAN
    assert ecran.code
    assert ecran.libelle == "Près du pas de tir"
    assert ctx.service.lister(ctx.tournoi_id) == [ecran]


def test_un_ecran_neuf_joue_le_deroule_par_defaut(ctx: Contexte) -> None:
    """« déroulé de vues **par défaut** » : on branche l'écran, il informe, sans rien régler."""
    ecran = ctx.ecran()

    assert ecran.deroule is None
    assert ecran.deroule_effectif == SequenceVues.par_defaut()


def test_plusieurs_ecrans_ont_chacun_leur_deroule(ctx: Contexte) -> None:
    """« **plusieurs écrans possibles, chacun son déroulé** » (affectations près du pas de tir,
    classements côté public) : régler l'un ne touche pas l'autre."""
    pas_de_tir = ctx.ecran("Pas de tir")
    public = ctx.ecran("Côté public")
    assert pas_de_tir.id is not None and public.id is not None

    plans = SequenceVues((VueProgrammee(VueEcran.PLAN_CIBLES, 20),))
    regle = ctx.service_postes.regler_deroule_ecran(ctx.tournoi_id, pas_de_tir.id, plans)

    assert regle.deroule_effectif == plans
    relu = ctx.postes_repo.par_id(public.id)
    assert relu is not None
    assert relu.deroule_effectif == SequenceVues.par_defaut()


def test_un_ecran_se_rattache_par_son_code_comme_une_tablette(ctx: Contexte) -> None:
    """Le **même** point d'entrée que la tablette de cible : aucun mécanisme parallèle."""
    ecran = ctx.ecran()

    connexion = ctx.service_postes.rattacher(ecran.code)

    assert connexion.poste.id == ecran.id
    assert ctx.service_postes.session_valide(connexion.jeton)


def test_regler_le_deroule_d_une_cible_est_refuse(ctx: Contexte) -> None:
    """Une cible n'affiche pas de déroulé : elle saisit des scores."""
    cible = ctx.postes_repo.ajouter(Poste.creer(ctx.tournoi_id, 1, "CIB001"))
    assert cible.id is not None

    with pytest.raises(PosteNEstPasUnEcran):
        ctx.service_postes.regler_deroule_ecran(ctx.tournoi_id, cible.id, SequenceVues.par_defaut())


def test_un_ecran_d_un_autre_tournoi_n_existe_pas(ctx: Contexte) -> None:
    """Même parti que partout (ADR-0034 §4) : un poste d'un tournoi voisin n'existe pas ici."""
    ecran = ctx.ecran()
    autre = ctx.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert ecran.id is not None and autre.id is not None

    with pytest.raises(PosteIntrouvable):
        ctx.service.prendre_le_controle(
            autre.id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
        )


def test_un_ecran_se_supprime(ctx: Contexte) -> None:
    """L'écran se débranche et se retire ; sa consigne éventuelle part avec lui."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
    )

    ctx.service_postes.supprimer_ecran(ctx.tournoi_id, ecran.id)

    assert ctx.service.lister(ctx.tournoi_id) == []
    assert ctx.consignes.prise_de(ecran.id) is None


# --- CA « pilotage admin » ------------------------------------------------------------------------


def test_sans_consigne_l_ecran_joue_son_deroule(ctx: Contexte) -> None:
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton

    affichage = ctx.service.affichage(jeton)

    assert affichage.sequence == SequenceVues.par_defaut()
    assert affichage.vue_figee is None
    assert affichage.reste_s is None
    assert not affichage.sous_controle


def test_une_vue_figee_remplace_le_deroule_en_direct(ctx: Contexte) -> None:
    """« l'admin **impose** […] une **vue figée** (ex. podium) ; l'écran bascule **en direct** ».

    « En direct » se lit ici comme : la prochaine lecture de l'écran rend déjà la consigne — aucune
    latence de propagation, aucun ordre à acquitter.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton

    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)
    )

    affichage = ctx.service.affichage(jeton)
    assert affichage.sous_controle
    assert affichage.vue_figee is VueEcran.CLASSEMENT
    # ⚠️ La séquence accompagne **toujours** la vue figée (correctif de revue) : c'est le repli sur
    # lequel l'écran retombera tout seul à l'échéance, sans rien redemander au serveur. La sortir de
    # la réponse — ce que faisait la première version — rendait impossible la reprise « insensible
    # au réseau » que promettent l'ADR, la story et la recette.
    assert affichage.sequence == SequenceVues.par_defaut()


def test_une_autre_sequence_peut_etre_imposee(ctx: Contexte) -> None:
    """« soit une **autre séquence** » — l'écran tourne, mais sur ce que l'admin a choisi."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    imposee = SequenceVues((VueProgrammee(VueEcran.PLAN_CIBLES, 15),))

    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=None, sequence=imposee, duree_s=None)
    )

    affichage = ctx.service.affichage(jeton)
    assert affichage.sous_controle
    assert affichage.sequence == imposee
    assert affichage.vue_figee is None


def test_une_prise_a_duree_se_termine_toute_seule(ctx: Contexte) -> None:
    """CA « **durée** » : « podium 10 min **puis reprise du déroulé** ».

    C'est le test central d'ADR-0064 : entre les deux appels, **aucun événement** n'est survenu —
    seul le temps a passé. Un pilotage par ordre poussé n'aurait rien eu à envoyer ici.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)
    )

    ctx.horloge.avancer(599)
    assert ctx.service.affichage(jeton).sous_controle

    ctx.horloge.avancer(2)
    reprise = ctx.service.affichage(jeton)
    assert not reprise.sous_controle
    assert reprise.sequence == SequenceVues.par_defaut()


def test_une_prise_a_duree_affiche_son_compte_a_rebours(ctx: Contexte) -> None:
    """« podium 10 min puis reprise » ne vaut que si l'échéance est **visible** des deux côtés."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)
    )

    ctx.horloge.avancer(120)

    assert ctx.service.affichage(jeton).reste_s == 480


def test_rendre_la_main_ramene_le_deroule_immediatement(ctx: Contexte) -> None:
    """CA « **ou** retour explicite très visible » — le second terme de l'arbitrage Q-UX7."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=None)
    )

    ctx.service.rendre_la_main(ctx.tournoi_id, ecran.id)

    assert not ctx.service.affichage(jeton).sous_controle


def test_rendre_la_main_sur_un_ecran_libre_est_sans_effet(ctx: Contexte) -> None:
    """Idempotent, comme la révocation d'un poste : un double clic n'est pas une erreur."""
    ecran = ctx.ecran()
    assert ecran.id is not None

    ctx.service.rendre_la_main(ctx.tournoi_id, ecran.id)

    assert not ctx.service.prises(ctx.tournoi_id)


def test_une_prise_sans_duree_est_signalee_a_la_console(ctx: Contexte) -> None:
    """CA « **jamais un état forcé qu'on oublie** ».

    Le service ne peut pas empêcher l'oubli ; il doit le **remonter** — c'est ce que la console
    transforme en rappel très visible. Sans ce drapeau, l'écran resterait figé en silence.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=None)
    )

    prises = ctx.service.prises(ctx.tournoi_id)

    assert prises[ecran.id].exige_rappel
    assert prises[ecran.id].reste_s is None


def test_une_prise_echue_disparait_de_la_console(ctx: Contexte) -> None:
    """La console ne doit pas proposer de « rendre la main » sur une prise déjà terminée."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
    )

    ctx.horloge.avancer(61)

    assert ctx.service.prises(ctx.tournoi_id) == {}


def test_une_seconde_prise_remplace_la_premiere(ctx: Contexte) -> None:
    """« impose le podium » après « impose le plan » est une correction, pas une file d'attente."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.PLAN_CIBLES, sequence=None, duree_s=600)
    )

    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
    )

    assert ctx.service.affichage(jeton).vue_figee is VueEcran.CLASSEMENT


def test_prendre_le_controle_d_une_cible_est_refuse(ctx: Contexte) -> None:
    """Le pilotage s'adresse aux écrans : imposer une vue à une tablette de saisie n'a pas de sens
    — et la console les affiche côte à côte, donc la garde n'est pas théorique."""
    cible = ctx.postes_repo.ajouter(Poste.creer(ctx.tournoi_id, 1, "CIB001"))
    assert cible.id is not None

    with pytest.raises(PosteNEstPasUnEcran):
        ctx.service.prendre_le_controle(
            ctx.tournoi_id, cible.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
        )


def test_l_affichage_exige_une_session_d_ecran(ctx: Contexte) -> None:
    """Un jeton de **cible** ne donne pas accès à l'affichage d'un écran (portées distinctes)."""
    cible = ctx.postes_repo.ajouter(Poste.creer(ctx.tournoi_id, 1, "CIB001"))
    assert cible.id is not None
    jeton = ctx.service_postes.rattacher("CIB001").jeton

    with pytest.raises(PosteNEstPasUnEcran):
        ctx.service.affichage(jeton)


def test_rendre_la_main_sur_une_prise_echue_est_sans_effet(ctx: Contexte) -> None:
    """Cas adverse proposé en revue : la fenêtre où le nettoyage automatique a déjà eu lieu.

    L'idempotence était prouvée sur un écran **libre**, jamais sur celui dont la prise vient
    d'expirer et d'être retirée par `_retirer_si_echue`. C'est pourtant l'enchaînement réel : la
    console poll, découvre l'expiration, nettoie — puis l'organisateur clique « rendre la main »
    sur une ligne qu'il voyait encore.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
    )
    ctx.horloge.avancer(61)
    assert ctx.service.prises(ctx.tournoi_id) == {}  # le nettoyage a déjà eu lieu

    ctx.service.rendre_la_main(ctx.tournoi_id, ecran.id)

    assert not ctx.service.affichage(jeton).sous_controle


def test_une_prise_reposee_survit_au_nettoyage_de_la_precedente(ctx: Contexte) -> None:
    """**Non-régression** (revue, axe A) : le nettoyage d'une prise échue ne doit pas emporter la
    suivante.

    Le retrait d'une prise expirée est un effet de bord de la **lecture**. S'il retirait par simple
    identifiant, la séquence « je lis une prise expirée → l'organisateur en repose une → je
    retire » effacerait **la neuve**. Fenêtre étroite, mais c'est exactement l'instant « le podium
    expire, l'organisateur le remet » — et la console poll en continu.

    On la reproduit à la main : on capture la prise expirée, on en pose une neuve, puis on demande
    le retrait conditionnel de l'ancienne.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=60)
    )
    echue = ctx.consignes.prise_de(ecran.id)
    assert echue is not None
    ctx.horloge.avancer(61)
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=VueEcran.PLAN_CIBLES, sequence=None, duree_s=600)
    )

    ctx.consignes.retirer_si(ecran.id, echue)

    prises = ctx.service.prises(ctx.tournoi_id)
    assert prises[ecran.id].vue_figee is VueEcran.PLAN_CIBLES


def test_supprimer_un_ecran_oublie_aussi_sa_presence(ctx: Contexte) -> None:
    """SQLite **réattribue** les identifiants : tout état volatil indexé par ce `poste_id` doit
    partir, sinon un écran neuf naîtrait « en ligne » avec l'IP de son prédécesseur (revue)."""
    ecran = ctx.ecran()
    assert ecran.id is not None
    ctx.presence.enregistrer(ecran.id, _T0, "192.168.1.42")

    ctx.service_postes.supprimer_ecran(ctx.tournoi_id, ecran.id)

    assert ctx.presence.derniere_activite(ecran.id) is None


def test_un_ecran_ne_fixe_pas_de_depart_courant(ctx: Contexte) -> None:
    """Garde de nature **au service**, pas seulement à la frontière (2ᵉ passe de revue).

    `fixer_depart_courant` annonce dans sa propre docstring un appelant **hors HTTP** (E12US002,
    « l'orchestrateur l'appellera sans passer par `exiger_poste` ») : une garde posée uniquement à
    la dépendance API ne le couvrirait pas. C'est exactement le raisonnement tiré du bloquant de la
    1ʳᵉ passe, qui n'avait pas été rejoué ici.
    """
    ecran = ctx.ecran()
    jeton = ctx.service_postes.rattacher(ecran.code).jeton

    with pytest.raises(SaisieHorsCible):
        ctx.service_postes.fixer_depart_courant(jeton, 1)


def test_une_sequence_imposee_laisse_le_deroule_propre_en_repli(ctx: Contexte) -> None:
    """**Non-régression** (3ᵉ passe) : le repli local doit exister **aussi** sous séquence imposée.

    Un correctif intermédiaire repliait `sequence` sur le déroulé propre. Cela marchait pour une
    **vue figée** — où `sequence` était libre — mais pas pour une **séquence imposée**, où elle
    porte déjà la consigne : à l'échéance, un écran isolé continuait de jouer la séquence de l'admin
    **en affirmant au bandeau avoir repris son déroulé**. D'où un champ distinct.

    Le test tient les deux à la fois : `sequence` porte bien la consigne, `deroule_repli` bien le
    déroulé propre, et les deux **diffèrent**.
    """
    ecran = ctx.ecran()
    assert ecran.id is not None
    jeton = ctx.service_postes.rattacher(ecran.code).jeton
    imposee = SequenceVues((VueProgrammee(VueEcran.PLAN_CIBLES, 15),))
    ctx.service.prendre_le_controle(
        ctx.tournoi_id, ecran.id, Consigne(vue=None, sequence=imposee, duree_s=600)
    )

    affichage = ctx.service.affichage(jeton)

    assert affichage.sequence == imposee
    assert affichage.deroule_repli == SequenceVues.par_defaut()
    assert affichage.sequence != affichage.deroule_repli
