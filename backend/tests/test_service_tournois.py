"""Tests du service applicatif Tournois (E00US009, E01US001, E01US002, E01US017, E02US010).

Le service est testé **en isolation** du domaine d'infrastructure : de faux repositories
en mémoire (conformes aux ports `TournoiRepository` et `DepartRepository`) suffisent — ni base ni
serveur. Depuis E02US010, `ServiceTournois` lit aussi les **départs** : le passage à `prêt` exige au
moins un créneau (garde `TournoiSansDepart`), d'où le dépôt de départs injecté.
"""

from __future__ import annotations

import pytest

from application.erreurs import (
    EffectifInsuffisantPourDemarrer,
    TournoiArchiveNonModifiable,
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TournoiSansDepart,
    TransitionStatutInvalide,
)
from application.tournois import OrigineExigence, ServiceTournois
from domain.bareme import BaremeQualification
from domain.depart import Depart
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import NomTournoiInvalide
from domain.grain_validation import GrainValidation
from domain.phase import TypePhase
from domain.tournoi import (
    StatutTournoi,
    TypeTournoi,
    transitions_possibles,
)
from tests.conftest import (
    DATE_TOURNOI,
    FauxCompteurEngages,
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxTournoiRepository,
    deroule_120,
)


def _service_complet() -> (
    tuple[
        ServiceTournois,
        FauxDepartRepository,
        FauxDerouleRepository,
        FauxCompteurEngages,
        FauxTournoiRepository,
    ]
):
    """Le service et **tous** ses dépôts, pour les tests qui garnissent le déroulé et les inscrits.

    ⚠️ Le troisième dépôt est le **déroulé** (`FauxDerouleRepository`) et non les phases
    (E01US025, ADR-0076) : l'exigence d'effectif se déduit de la **définition**, écrite une seule
    fois au tournoi. Elle se lisait sur `PhaseRepository.par_tournoi`, qui concatène les N copies
    d'avancement des créneaux — un plancher faux dès le deuxième départ.
    """
    departs = FauxDepartRepository()
    deroules = FauxDerouleRepository()
    engages = FauxCompteurEngages()
    tournois = FauxTournoiRepository()
    service = ServiceTournois(tournois, departs, deroules, engages)
    return service, departs, deroules, engages, tournois


def _service() -> tuple[ServiceTournois, FauxDepartRepository]:
    """Fabrique le service et son dépôt de départs (à garnir pour les tests de passage à `prêt`).

    Le tournoi obtenu n'a **aucune phase** : la garde d'effectif d'E05US021 ne s'exprime donc pas,
    et les tests de cycle de vie antérieurs restent exactement ce qu'ils étaient.
    """
    service, departs = _service_complet()[:2]
    return service, departs


def _id_cree(service: ServiceTournois, departs: FauxDepartRepository, nom: str = "Trophée") -> int:
    """Crée un tournoi **avec un départ** — condition du passage à `prêt` (E02US010).

    Tous les tests de cycle de vie amènent un tournoi jusqu'à `prêt`/`en_cours`/… : sans départ, la
    garde `TournoiSansDepart` les bloquerait. Le créneau est ici un détail d'attelage, pas le sujet.
    """
    cree = service.creer(nom, DATE_TOURNOI)
    assert cree.id is not None
    departs.ajouter(Depart.creer(cree.id, 1, 810, "09:00"))
    return cree.id


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` délègue au repository, qui attribue l'identifiant."""
    service, _ = _service()
    tournoi = service.creer("Salle 18m", DATE_TOURNOI, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.id == 1
    assert tournoi.nom == "Salle 18m"
    assert tournoi.date == DATE_TOURNOI
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom invalide fait remonter l'erreur du domaine (non persisté)."""
    service, _ = _service()
    with pytest.raises(NomTournoiInvalide):
        service.creer("  ", DATE_TOURNOI)


def test_consulter_relit_un_tournoi_existant() -> None:
    """`consulter` renvoie l'agrégat persisté."""
    service, _ = _service()
    cree = service.creer("Trophée", DATE_TOURNOI)
    assert cree.id is not None
    assert service.consulter(cree.id) == cree


def test_consulter_leve_si_introuvable() -> None:
    """`consulter` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.consulter(404)


def test_lister_renvoie_tous_les_tournois() -> None:
    """`lister` renvoie tous les tournois créés."""
    service, _ = _service()
    assert service.lister() == []
    service.creer("A", DATE_TOURNOI)
    service.creer("B", DATE_TOURNOI)
    assert [t.nom for t in service.lister()] == ["A", "B"]


# --- Édition des métadonnées (E01US002) ---


def test_modifier_persiste_les_metadonnees() -> None:
    """`modifier` met à jour le tournoi et conserve son identifiant."""
    service, _ = _service()
    cree = service.creer("Ancien", DATE_TOURNOI)
    assert cree.id is not None
    modifie = service.modifier(cree.id, "Nouveau", DATE_TOURNOI, "Quimper", TypeTournoi.OFFICIEL)
    assert modifie.id == cree.id
    assert modifie.nom == "Nouveau"
    assert modifie.lieu == "Quimper"
    assert modifie.type_tournoi is TypeTournoi.OFFICIEL
    assert service.consulter(cree.id) == modifie


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.modifier(404, "X", DATE_TOURNOI)


def test_modifier_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service, _ = _service()
    cree = service.creer("Trophée", DATE_TOURNOI)
    assert cree.id is not None
    with pytest.raises(NomTournoiInvalide):
        service.modifier(cree.id, "   ", DATE_TOURNOI)


# --- Cycle de vie enrichi (E01US017, ADR-0026 §2) : graphe des transitions ---
# Depuis E02US010, `vers_pret` exige **au moins un départ** : `_id_cree` en sème un, donc les tests
# de graphe atteignent `prêt`. La garde « ≥ 1 départ » a ses propres tests plus bas ; le reste de la
# complétude de préparation (catégories, blasons, gabarit, barème) viendra d'une tranche ultérieure.


def _amener(service: ServiceTournois, tid: int, statut: StatutTournoi) -> None:
    """Amène un tournoi neuf (brouillon) au statut voulu par le chemin nominal du graphe."""
    if statut is StatutTournoi.BROUILLON:
        return
    service.vers_pret(tid)
    if statut is StatutTournoi.PRET:
        return
    service.demarrer(tid)  # en_cours
    if statut is StatutTournoi.EN_COURS:
        return
    if statut is StatutTournoi.EN_PAUSE:
        service.mettre_en_pause(tid)
        return
    service.terminer(tid)  # termine
    if statut is StatutTournoi.TERMINE:
        return
    if statut is StatutTournoi.ARCHIVE:
        service.archiver(tid)
        return
    raise AssertionError(f"Chemin non couvert pour {statut}.")


def test_chemin_nominal_brouillon_pret_en_cours_termine_archive() -> None:
    """Le chemin de vie complet enchaîne les cinq statuts nominaux dans l'ordre."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    assert service.consulter(tid).statut is StatutTournoi.BROUILLON
    assert service.vers_pret(tid).statut is StatutTournoi.PRET
    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS
    assert service.terminer(tid).statut is StatutTournoi.TERMINE
    assert service.archiver(tid).statut is StatutTournoi.ARCHIVE


def test_pret_peut_revenir_brouillon() -> None:
    """`brouillon ⇄ prêt` : un tournoi prêt peut revenir en brouillon pour rééditer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    service.vers_pret(tid)
    assert service.revenir_brouillon(tid).statut is StatutTournoi.BROUILLON


def test_pause_puis_reprise() -> None:
    """`en_cours ⇄ en_pause` : mise en pause réversible sans terminer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    assert service.mettre_en_pause(tid).statut is StatutTournoi.EN_PAUSE
    assert service.reprendre(tid).statut is StatutTournoi.EN_COURS


# --- Garde « ≥ 1 départ » du passage à prêt (E02US010) ---


def test_vers_pret_refuse_un_tournoi_sans_depart() -> None:
    """Un brouillon **sans départ** ne peut pas passer prêt → `TournoiSansDepart` (→ 409)."""
    service, _ = _service()
    cree = service.creer("Sans créneau", DATE_TOURNOI)
    assert cree.id is not None
    with pytest.raises(TournoiSansDepart):
        service.vers_pret(cree.id)
    assert service.consulter(cree.id).statut is StatutTournoi.BROUILLON


def test_vers_pret_accepte_des_qu_il_y_a_un_depart() -> None:
    """Dès qu'un créneau existe, le passage à prêt est permis (E02US010)."""
    service, departs = _service()
    tid = _id_cree(service, departs)  # sème un départ
    assert service.vers_pret(tid).statut is StatutTournoi.PRET


@pytest.mark.parametrize("depuis", [StatutTournoi.BROUILLON, StatutTournoi.EN_COURS])
def test_vers_pret_refuse_hors_brouillon(depuis: StatutTournoi) -> None:
    """`vers_pret` n'est légal que depuis `brouillon` (en cours → 409)."""
    if depuis is StatutTournoi.BROUILLON:
        return  # cas légal, couvert ailleurs
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.vers_pret(tid)


def test_demarrer_refuse_si_pas_pret() -> None:
    """Démarrer passe désormais par `prêt` : depuis un brouillon → 409."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(tid)  # encore brouillon, pas prêt


# --- Garde d'effectif au démarrage (E05US021) ---
# Écrits **depuis le CA** de `stories/E05-moteur-phases.md` (règle 9), avant l'implémentation :
# « passer un tournoi "en cours" avec un effectif insuffisant est **refusé**, avec un message qui
# nomme la phase et son prélèvement ». Le contrôle que le moteur faisait sur la tablette
# (`EffectifTableauInvalide`, E05US020) remonte là où la décision se prend.


def _pret_avec_deroule(inscrits: int) -> tuple[ServiceTournois, int]:
    """Un tournoi `prêt`, doté du déroulé à 34 minimum et de `inscrits` archers."""
    service, departs, deroules, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    # Le déroulé se pose **sur le tournoi** (ADR-0076) : une définition, pas N copies.
    for _etape in deroule_120(tid):
        deroules.ajouter(_etape)
    engages.nb = inscrits
    service.vers_pret(tid)
    return service, tid


def test_demarrer_refuse_un_effectif_sous_le_minimum_du_deroule() -> None:
    """28 inscrits pour un déroulé qui en exige 34 : refus (→ 409), le tournoi reste `prêt`."""
    service, tid = _pret_avec_deroule(inscrits=28)

    with pytest.raises(EffectifInsuffisantPourDemarrer):
        service.demarrer(tid)

    assert service.consulter(tid).statut is StatutTournoi.PRET


def test_le_refus_nomme_la_phase_et_son_prelevement() -> None:
    """Le CA exige un message actionnable : sans la phase en cause, l'organisateur ne sait pas quoi
    changer dans son format."""
    service, tid = _pret_avec_deroule(inscrits=28)

    with pytest.raises(EffectifInsuffisantPourDemarrer) as leve:
        service.demarrer(tid)

    message = str(leve.value)
    assert "3" in message, "le message doit désigner la phase en cause"
    assert "33" in message, "le message doit citer le prélèvement fautif"
    assert "34" in message and "28" in message, "le message doit dire requis et réel"


def test_demarrer_accepte_des_que_leffectif_atteint_le_minimum() -> None:
    """34 inscrits pile : la borne est **inclusive**, le tournoi démarre."""
    service, tid = _pret_avec_deroule(inscrits=34)

    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS


def test_demarrer_accepte_un_effectif_confortable() -> None:
    service, tid = _pret_avec_deroule(inscrits=120)

    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS


def test_un_tournoi_sans_deroule_compose_demarre_sans_controle() -> None:
    """Aucune phase : aucun format n'est appliqué, il n'y a donc aucun minimum à confronter.

    C'est ce qui garde la garde **silencieuse** tant que l'organisateur n'a rien composé — et ce qui
    laisse intacts les tests de cycle de vie antérieurs à cette US.
    """
    service, departs, _, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    engages.nb = 0
    service.vers_pret(tid)

    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS


def _exiger(
    service: ServiceTournois, tournoi_repository: FauxTournoiRepository, tid: int, minimum: int
) -> None:
    """Pose l'exigence du club sur le tournoi, **comme le fait `ServiceFormats.appliquer`**.

    On passe par l'agrégat et le dépôt plutôt que par une méthode de `ServiceTournois` : aucune
    n'existe, et il ne faut pas en inventer une pour les besoins d'un test — la revue a relevé
    qu'une telle méthode, sans appelant de production, décrivait un chemin qui n'existe pas.
    """
    tournoi = service.consulter(tid)
    tournoi_repository.enregistrer(tournoi.exiger_effectif_minimum(minimum))


def test_lexigence_du_tournoi_prime_quand_elle_depasse_le_minimum_deduit() -> None:
    """Le « minimum exigé » copié du format (« pas sous 40 ») refuse un effectif que le déduit
    accepterait — et le message ne parle **pas** d'un prélèvement, puisqu'aucun n'est en cause."""
    service, departs, deroules, engages, tournois = _service_complet()
    tid = _id_cree(service, departs)
    # Le déroulé se pose **sur le tournoi** (ADR-0076) : une définition, pas N copies.
    for _etape in deroule_120(tid):
        deroules.ajouter(_etape)
    engages.nb = 36
    _exiger(service, tournois, tid, 40)
    service.vers_pret(tid)

    exigence = service.exigence_effectif(tid)
    assert exigence.minimum == 40
    assert exigence.origine is OrigineExigence.CLUB
    assert exigence.ordre_phase is None and exigence.rang_debut is None

    with pytest.raises(EffectifInsuffisantPourDemarrer) as leve:
        service.demarrer(tid)

    message = str(leve.value)
    assert "40" in message and "36" in message
    assert "prélève" not in message, "aucune phase n'est en cause : ne pas en inventer une"


def test_une_exigence_plus_basse_que_le_deduit_ne_labaisse_pas() -> None:
    """Le déduit est un **plancher** : une exigence inférieure ne peut pas autoriser un tournoi que
    le moteur ne saura pas dérouler."""
    service, departs, deroules, engages, tournois = _service_complet()
    tid = _id_cree(service, departs)
    # Le déroulé se pose **sur le tournoi** (ADR-0076) : une définition, pas N copies.
    for _etape in deroule_120(tid):
        deroules.ajouter(_etape)
    engages.nb = 20
    _exiger(service, tournois, tid, 10)
    service.vers_pret(tid)

    assert service.exigence_effectif(tid).minimum == 34

    with pytest.raises(EffectifInsuffisantPourDemarrer):
        service.demarrer(tid)


def test_un_deroule_meme_minimal_exige_au_moins_un_inscrit() -> None:
    """Changement de comportement de l'US, à fixer explicitement : un tournoi **avec** déroulé et
    **zéro** inscrit ne démarre plus, là où il le pouvait avant."""
    service, departs, deroules, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    deroules.ajouter(
        EtapeDeroule(
            tournoi_id=tid,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.preset_ffta_18m(),
            validation=GrainValidation.fin_de_serie(),
        )
    )
    engages.nb = 0
    service.vers_pret(tid)

    with pytest.raises(EffectifInsuffisantPourDemarrer):
        service.demarrer(tid)


# --- CA « visible avant le clic » : la lecture qu'affiche l'écran du tournoi ---


def test_lexigence_se_lit_avant_de_cliquer_et_dit_ce_qui_manque() -> None:
    """« 28 inscrits / 34 requis » — le CA veut le manque visible **sans** cliquer « Démarrer »."""
    service, tid = _pret_avec_deroule(inscrits=28)

    exigence = service.exigence_effectif(tid)

    assert exigence.inscrits == 28
    assert exigence.minimum == 34
    assert exigence.suffisant is False
    assert exigence.ordre_phase == 3


def test_lexigence_est_satisfaite_quand_le_compte_y_est() -> None:
    service, tid = _pret_avec_deroule(inscrits=40)

    exigence = service.exigence_effectif(tid)

    assert exigence.suffisant is True
    assert exigence.minimum == 34


def test_lexigence_dun_tournoi_sans_deroule_est_toujours_satisfaite() -> None:
    """Rien n'est composé : il n'y a rien à exiger, et l'écran n'a rien à signaler."""
    service, departs, _, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    engages.nb = 0

    exigence = service.exigence_effectif(tid)

    assert exigence.suffisant is True
    assert exigence.ordre_phase is None


# --- Portée : l'exigence se juge sur le créneau le moins garni (ADR-0075) ------------------------


def test_lexigence_se_juge_sur_le_creneau_le_moins_garni_pas_sur_la_somme() -> None:
    """**La garde de portée.** Deux créneaux, 40 et 8 inscrits : le tournoi ne démarre pas.

    Un départ **rejoue le tournoi en entier**, donc un déroulé qui prélève à partir du 33ᵉ rang doit
    trouver 34 classés dans *chaque* créneau. L'exigence se lisait sur `nb_engages(tournoi_id)` —
    la somme, 48 — et laissait donc démarrer un tournoi dont la moitié était injouable, l'échec ne
    se manifestant qu'en salle, l'après-midi. Le refus doit en plus **nommer le créneau**, sans quoi
    « 8 inscrits pour 34 requis » contredit le total affiché partout ailleurs.
    """
    service, departs, deroules, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    matin = departs.par_tournoi(tid)[0]
    assert matin.id is not None
    apres_midi = departs.ajouter(Depart.creer(tid, 2, 810, "14:00"))
    assert apres_midi.id is not None
    for _etape in deroule_120(tid):
        deroules.ajouter(_etape)
    engages.regler(matin.id, 40)
    engages.regler(apres_midi.id, 8)
    service.vers_pret(tid)

    exigence = service.exigence_effectif(tid)
    assert exigence.inscrits == 8, "le compte retenu est celui du créneau le plus faible"
    assert exigence.minimum == 34
    assert exigence.suffisant is False
    assert exigence.depart_numero == 2

    with pytest.raises(EffectifInsuffisantPourDemarrer) as leve:
        service.demarrer(tid)
    assert "départ 2" in str(leve.value), "le refus doit nommer le créneau en cause"


def test_lexigence_est_satisfaite_quand_tous_les_creneaux_suivent() -> None:
    """Le miroir : deux créneaux au-dessus du plancher, le tournoi démarre.

    Sans lui, le test ci-dessus serait satisfait par un service qui refuserait *toujours* — c'est le
    couple qui prouve que la garde discrimine.
    """
    service, departs, deroules, engages = _service_complet()[:4]
    tid = _id_cree(service, departs)
    apres_midi = departs.ajouter(Depart.creer(tid, 2, 810, "14:00"))
    assert apres_midi.id is not None
    for _etape in deroule_120(tid):
        deroules.ajouter(_etape)
    engages.nb = 34
    service.vers_pret(tid)

    assert service.exigence_effectif(tid).suffisant is True
    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS


def test_reprendre_refuse_si_pas_en_pause() -> None:
    """Reprendre un tournoi qui n'est pas en pause lève `TransitionStatutInvalide`."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    with pytest.raises(TransitionStatutInvalide):
        service.reprendre(tid)


def test_terminer_refuse_si_pas_en_cours() -> None:
    """Terminer un tournoi non démarré lève `TransitionStatutInvalide` (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    with pytest.raises(TransitionStatutInvalide):
        service.terminer(tid)


def test_archiver_refuse_si_pas_termine() -> None:
    """Archiver un tournoi non terminé lève `TransitionStatutInvalide` (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    with pytest.raises(TransitionStatutInvalide):
        service.archiver(tid)


@pytest.mark.parametrize(
    "depuis",
    [
        StatutTournoi.BROUILLON,
        StatutTournoi.PRET,
        StatutTournoi.EN_COURS,
        StatutTournoi.EN_PAUSE,
    ],
)
def test_annuler_depuis_les_etats_vivants(depuis: StatutTournoi) -> None:
    """`annuler` part de brouillon/prêt/en_cours/en_pause et mène à `annulé` (terminal)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    assert service.annuler(tid).statut is StatutTournoi.ANNULE


@pytest.mark.parametrize("depuis", [StatutTournoi.TERMINE, StatutTournoi.ARCHIVE])
def test_annuler_refuse_depuis_termine_ou_archive(depuis: StatutTournoi) -> None:
    """On n'annule pas un tournoi joué jusqu'au bout (terminé) ni archivé (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.annuler(tid)


# --- Transitions offertes (E14US001) : cohérence topologie ↔ gardes ---
# `transitions_possibles` (topologie du domaine, lue par l'accueil admin) et les gardes `depuis`
# éparpillées dans le service sont **deux encodages** du même graphe : ce test les recoupe pour
# qu'ils ne divergent pas (règle 1, anti-duplication). C'est un test **après** implémentation — la
# règle métier vit dans le domaine (testée depuis le CA dans `test_domain_tournoi`), ici on vérifie
# le **câblage** service ↔ domaine.

# Univers des noms de transition, **dérivé de la topologie** (pas codé en dur) : toute arête ajoutée
# à `_TRANSITIONS` est ainsi automatiquement recoupée contre les gardes du service — sinon un nom
# oublié dans un set manuel échapperait au filet anti-divergence (revue E14US001, axe adversarial).
_TOUS_LES_NOMS = {
    transition.nom for statut in StatutTournoi for transition in transitions_possibles(statut)
}


def _amener_complet(service: ServiceTournois, tid: int, statut: StatutTournoi) -> None:
    """Comme `_amener`, mais couvre aussi `annulé` (annuler depuis brouillon)."""
    if statut is StatutTournoi.ANNULE:
        service.annuler(tid)
        return
    _amener(service, tid, statut)


def _appliquer(service: ServiceTournois, tid: int, nom: str) -> None:
    """Applique la transition d'identifiant `nom` (suffixe d'endpoint) sur le service."""
    getattr(service, nom.replace("-", "_"))(tid)


@pytest.mark.parametrize("statut", list(StatutTournoi))
def test_transitions_possibles_coherentes_avec_les_gardes(statut: StatutTournoi) -> None:
    """Pour chaque statut, les transitions offertes sont exactement celles acceptées par le service.

    Toute arête **offerte** par `transitions_possibles` est acceptée (aucune
    `TransitionStatutInvalide`) ; toute arête **non offerte** est refusée (→ 409). Un départ est
    semé (`_id_cree`), donc `vers-pret` n'est pas bloquée par la garde de complétude `≥ 1 départ`.
    """
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener_complet(service, tid, statut)
    offertes = {transition.nom for transition in service.transitions_possibles(tid)}

    for nom in _TOUS_LES_NOMS:
        # Appliquer une transition mute l'état : on repart d'un tournoi neuf au même statut.
        autre, autres_departs = _service()
        autre_tid = _id_cree(autre, autres_departs)
        _amener_complet(autre, autre_tid, statut)
        if nom in offertes:
            try:
                _appliquer(autre, autre_tid, nom)
            except TransitionStatutInvalide:  # pragma: no cover - filet anti-régression
                pytest.fail(f"{nom} offerte depuis {statut} mais refusée par le service.")
        else:
            with pytest.raises(TransitionStatutInvalide):
                _appliquer(autre, autre_tid, nom)


def test_transitions_possibles_leve_si_introuvable() -> None:
    """`transitions_possibles` relit le tournoi : identifiant inconnu → `TournoiIntrouvable`."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.transitions_possibles(404)


def test_modifier_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.ARCHIVE)
    with pytest.raises(TournoiArchiveNonModifiable):
        service.modifier(tid, "Renommé", DATE_TOURNOI)


# --- Suppression (E01US002, permissions élargies E01US017) ---


@pytest.mark.parametrize(
    "depuis",
    [StatutTournoi.BROUILLON, StatutTournoi.PRET, StatutTournoi.TERMINE],
)
def test_supprimer_autorise_hors_etats_vivants(depuis: StatutTournoi) -> None:
    """Un tournoi brouillon, prêt ou terminé est supprimable."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    service.supprimer(tid)
    assert service.lister() == []


def test_supprimer_un_annule() -> None:
    """Un tournoi annulé (trace) reste supprimable si on veut vraiment l'effacer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    service.annuler(tid)
    service.supprimer(tid)
    assert service.lister() == []


@pytest.mark.parametrize("depuis", [StatutTournoi.EN_COURS, StatutTournoi.EN_PAUSE])
def test_supprimer_refuse_si_vivant(depuis: StatutTournoi) -> None:
    """Un tournoi en cours ou en pause n'est pas supprimable → `TournoiEnCoursNonSupprimable`."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TournoiEnCoursNonSupprimable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is depuis


def test_supprimer_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.ARCHIVE)
    with pytest.raises(TournoiArchiveNonModifiable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is StatutTournoi.ARCHIVE


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.supprimer(404)
