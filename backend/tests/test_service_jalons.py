"""Tests du service applicatif **Jalons « prêt à… »** (E16US012).

Tests **après** implémentation (règle 9) : il n'y a pas d'oracle en jeu ici — la règle métier vit
dans `domain.jalon`, testée depuis le CA (`test_domain_jalon.py`). Ce qui se vérifie ici est de
l'**agrégation** : le service lit-il les bons ports, et ce qu'il en tire coïncide-t-il avec ce que
les gardes du cycle de vie décideront au clic ?

⚠️ **Le test de cohérence de ce module est le garde-fou de l'US.** Le CA dit « sans doublonner ce
qui existe » : l'écran et la garde doivent dire la même chose. Là où l'effectif est mécaniquement
partagé (`ServiceTournois.exigence_effectif`, appelée par les deux), rien ne peut dériver ; là où le
partage s'arrête — le jalon traduit « aucun créneau » en `EN_ATTENTE`, la garde le traduit en
`TournoiSansDepart` —, seul ce test empêche les deux versants de se séparer en silence. Même patron
que le recoupement `domain.tournoi._TRANSITIONS` ↔ légalité effective du service.
"""

from __future__ import annotations

import pytest

from application.erreurs import (
    EffectifInsuffisantPourDemarrer,
    JalonNonInstruit,
    TournoiIntrouvable,
    TournoiSansDepart,
    TransitionStatutInvalide,
)
from application.jalons import ServiceJalons
from application.tournois import ServiceTournois
from domain.completude import Completude, EtatSection, evaluer_completude
from domain.depart import Depart
from domain.jalon import CLE_CRENEAUX, CLE_DEROULE, CLE_EFFECTIF, Jalon
from domain.tournoi import StatutTournoi, TournoiId
from tests.conftest import (
    DATE_TOURNOI,
    FauxCompteurEngages,
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxTournoiRepository,
    deroule_120,
)


class FauxLecteurCompletude:
    """Port `LecteurCompletude` en mémoire : rend la complétude qu'on lui a réglée.

    Le jalon *terminer* ne fait que **relire** la complétude ; il n'y a donc rien à recalculer dans
    ce faux — lui faire agréger des séries reviendrait à tester `ServiceCompletude` une seconde
    fois, là où l'on veut vérifier le **branchement**.
    """

    def __init__(self, completude: Completude) -> None:
        self.completude = completude

    def pour_tournoi(self, tournoi_id: TournoiId) -> Completude:
        return self.completude


def _attelage(
    *,
    inscrits: int = 0,
    avec_creneau: bool = True,
    avec_deroule: bool = False,
    completude: Completude | None = None,
    creneaux: tuple[int, ...] = (),
) -> tuple[ServiceJalons, ServiceTournois, int]:
    """Un tournoi et les deux services qui le regardent — jalons et cycle de vie.

    Les **mêmes** dépôts alimentent les deux : c'est la condition du test de cohérence. Deux jeux de
    faux distincts le rendraient vert sans rien garantir.

    `creneaux` pose **plusieurs** départs avec leurs effectifs respectifs — ex. `(40, 8)`. Sans lui,
    l'attelage n'avait qu'un créneau, et la règle « l'exigence se juge sur le moins garni »
    (ADR-0075, treize mois de bug) n'était donc **jamais** exercée côté jalon (relevé en revue).
    """
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    deroules = FauxDerouleRepository()
    engages = FauxCompteurEngages(inscrits)
    service_tournois = ServiceTournois(tournois, departs, deroules, engages)

    cree = service_tournois.creer("Trophée", DATE_TOURNOI)
    assert cree.id is not None
    if creneaux:
        for numero, effectif in enumerate(creneaux, start=1):
            pose = departs.ajouter(Depart.creer(cree.id, numero, 810, f"{8 + numero:02d}:00"))
            assert pose.id is not None
            engages.regler(pose.id, effectif)
    elif avec_creneau:
        departs.ajouter(Depart.creer(cree.id, 1, 810, "09:00"))
    if avec_deroule:
        for etape in deroule_120(cree.id):
            deroules.ajouter(etape)

    service_jalons = ServiceJalons(
        tournois,
        departs,
        deroules,
        service_tournois,
        FauxLecteurCompletude(completude or evaluer_completude(qualif=(0, 0), paiements=(0, 0))),
    )
    return service_jalons, service_tournois, cree.id


def _amener_a(tournois: ServiceTournois, tournoi_id: int, statut: StatutTournoi) -> None:
    """Conduit un tournoi jusqu'au statut voulu, par les transitions réelles du service.

    Poser le statut à la main court-circuiterait la machine à états — donc la chose même que le
    test veut confronter au jalon.
    """
    chemins: dict[StatutTournoi, tuple[str, ...]] = {
        StatutTournoi.BROUILLON: (),
        StatutTournoi.PRET: ("vers_pret",),
        StatutTournoi.EN_COURS: ("vers_pret", "demarrer"),
        StatutTournoi.EN_PAUSE: ("vers_pret", "demarrer", "mettre_en_pause"),
        StatutTournoi.TERMINE: ("vers_pret", "demarrer", "terminer"),
        StatutTournoi.ARCHIVE: ("vers_pret", "demarrer", "terminer", "archiver"),
        StatutTournoi.ANNULE: ("annuler",),
    }
    for etape in chemins[statut]:
        getattr(tournois, etape)(tournoi_id)


def _ligne_etat(service: ServiceJalons, tournoi_id: int, cle: str) -> EtatSection:
    """L'état d'une ligne de « prêt à démarrer »."""
    preparation = service.preparation(tournoi_id, Jalon.DEMARRER)
    return next(ligne for ligne in preparation.lignes if ligne.cle == cle).etat


# --- Agrégation : le service lit-il les bons ports ? --------------------------------------------


def test_le_jalon_demarrer_compte_les_creneaux_du_tournoi() -> None:
    jalons, _, tid = _attelage(avec_creneau=False)

    assert _ligne_etat(jalons, tid, CLE_CRENEAUX) is EtatSection.EN_ATTENTE


def test_le_jalon_demarrer_lit_le_deroule_compose_au_tournoi() -> None:
    """ADR-0076 : le déroulé est une **définition** au tournoi, pas N copies par créneau."""
    jalons, _, tid = _attelage(avec_deroule=True, inscrits=40)

    assert _ligne_etat(jalons, tid, CLE_DEROULE) is EtatSection.OK


def test_le_jalon_demarrer_chiffre_l_effectif_depuis_l_exigence_du_service() -> None:
    """Le « 28/34 » de l'écran vient de `exigence_effectif` — la méthode que la garde exécute."""
    jalons, _, tid = _attelage(avec_deroule=True, inscrits=28)

    ligne = next(
        ligne
        for ligne in jalons.preparation(tid, Jalon.DEMARRER).lignes
        if ligne.cle == CLE_EFFECTIF
    )
    assert (ligne.fait, ligne.total) == (28, 34)


def test_le_jalon_terminer_relit_la_completude_sans_la_recalculer() -> None:
    """⚠️ **Sur un tournoi en cours** : c'est la seule fenêtre où la question « prêt à terminer ? »
    se pose, donc la seule où le jalon liste ce qui manque. Ailleurs il rend une liste vide et la
    raison — même règle que *démarrer*.
    """
    completude = evaluer_completude(qualif=(28, 30), paiements=(113, 120))
    jalons, tournois, tid = _attelage(completude=completude, inscrits=40, avec_deroule=True)
    _amener_a(tournois, tid, StatutTournoi.EN_COURS)

    preparation = jalons.preparation(tid, Jalon.TERMINER)
    assert preparation.lignes == completude.sportif
    assert preparation.pret is False


# --- Cohérence jalon ↔ garde : **le garde-fou de l'US** -----------------------------------------


def test_sans_creneau_le_jalon_annonce_ce_que_la_garde_refusera() -> None:
    """`pret is False` **et** `vers_pret` lève : l'écran et le clic disent la même chose.

    ⚠️ « La même chose » au sens **littéral** : on compare la phrase annoncée avant le clic à celle
    que le refus porte. Se contenter des deux verdicts laissait les deux textes diverger en silence
    au premier reformulage (2ᵉ passe de revue, axes A, C2 et D).
    """
    jalons, tournois, tid = _attelage(avec_creneau=False)

    preparation = jalons.preparation(tid, Jalon.DEMARRER)
    assert preparation.pret is False
    # Le refus tombe **dès** « Marquer prêt », pas au démarrage : c'est cette garde-ci.
    assert preparation.moment == "dès le passage en « prêt »"
    with pytest.raises(TournoiSansDepart) as refus:
        tournois.vers_pret(tid)
    assert preparation.detail == str(refus.value)


def test_effectif_insuffisant_le_jalon_annonce_ce_que_la_garde_refusera() -> None:
    """Second versant du même accord, sur l'autre garde (E05US021)."""
    jalons, tournois, tid = _attelage(avec_deroule=True, inscrits=28)

    preparation = jalons.preparation(tid, Jalon.DEMARRER)
    assert preparation.pret is False
    assert preparation.moment == "au démarrage"
    # ⚠️ `vers_pret` **passe** : depuis *brouillon*, la seule garde est « ≥ 1 créneau ». Le jalon
    # répond de l'**étape** (arriver à `en_cours`), pas du prochain clic — c'est tout l'objet de
    # l'US, annoncer l'effectif avant le premier clic plutôt qu'au second. Cette ligne n'avait
    # aucune assertion et laissait donc croire que le refus tombait ici (relevé en revue, axe D) ;
    # c'est ce décalage que l'écran nomme désormais (« sera refusé **au démarrage** »).
    assert tournois.vers_pret(tid).statut is StatutTournoi.PRET
    # ⚠️ On **réinterroge** le jalon : c'est la seule façon de prouver qu'il dit toujours non depuis
    # *prêt*. La 2ᵉ correction avait factorisé cette ligne en relecture d'une variable déjà assertée
    # plus haut — l'appel au service disparaissait, et le statut *prêt* n'était plus couvert du tout
    # (3ᵉ passe de revue, axes B et C1). Une assertion qui ne peut plus échouer n'est pas verte.
    apres = jalons.preparation(tid, Jalon.DEMARRER)
    assert apres.pret is False
    assert apres.moment == "au démarrage"
    with pytest.raises(EffectifInsuffisantPourDemarrer) as refus:
        tournois.demarrer(tid)
    assert apres.detail == str(refus.value)


def test_quand_le_jalon_dit_pret_les_deux_gardes_laissent_passer() -> None:
    """Le sens **inverse**, et c'est celui qui compte le plus : un écran qui annonce « prêt » alors
    que le serveur refuse est le défaut que cette US existe pour supprimer.

    Un écran trop pessimiste fait perdre du temps ; un écran trop optimiste envoie l'organisateur
    au refus, le jour J, devant la salle.
    """
    jalons, tournois, tid = _attelage(avec_deroule=True, inscrits=40)

    assert jalons.preparation(tid, Jalon.DEMARRER).pret is True
    tournois.vers_pret(tid)
    assert tournois.demarrer(tid).id == tid


def test_un_deroule_vide_ne_bloque_ni_le_jalon_ni_la_garde() -> None:
    """`D-15` vérifié **des deux côtés** : le service laisse démarrer sans déroulé, le jalon aussi.

    C'est le cas qui distingue « ce qui manque » de « ce qui bloque » : la ligne du déroulé est en
    attente alors que `pret` reste vrai. Si un jour la garde durcit, ce test tombe — et c'est bien
    ce qu'on veut, la décision est métier.
    """
    jalons, tournois, tid = _attelage(avec_deroule=False, inscrits=0)

    preparation = jalons.preparation(tid, Jalon.DEMARRER)
    assert preparation.pret is True
    assert _ligne_etat(jalons, tid, CLE_DEROULE) is EtatSection.EN_ATTENTE
    tournois.vers_pret(tid)
    assert tournois.demarrer(tid).id == tid


def test_le_jalon_chiffre_l_effectif_du_creneau_le_moins_garni() -> None:
    """ADR-0075/0076 : chaque départ **rejoue le tournoi en entier**, donc l'exigence se juge sur le
    maillon faible — jamais sur la somme.

    Le test manquait, et c'est le trou qui compte le plus : le bug d'origine (deux créneaux à 40 et
    8, tournoi démarré puis bloqué en salle sur le second) a coûté treize mois. Un jalon qui
    sommerait les créneaux annoncerait « 48 inscrits, allez-y » là où la garde refuse.
    """
    jalons, tournois, tid = _attelage(avec_deroule=True, creneaux=(40, 8))

    preparation = jalons.preparation(tid, Jalon.DEMARRER)
    ligne = next(ligne for ligne in preparation.lignes if ligne.cle == CLE_EFFECTIF)
    assert (ligne.fait, ligne.total) == (8, 34)
    assert preparation.pret is False
    # La cause **nomme le créneau** : « 8/34 » seul contredit le total affiché ailleurs.
    assert preparation.detail is not None
    assert "départ 2" in preparation.detail
    tournois.vers_pret(tid)
    with pytest.raises(EffectifInsuffisantPourDemarrer):
        tournois.demarrer(tid)


def test_l_effectif_juste_atteint_passe_des_deux_cotes() -> None:
    """La **borne** d'égalité, `inscrits == minimum` — le point exact où un `>` mis pour un `>=`
    séparerait l'écran de la garde sans qu'aucun autre test ne bouge (relevé en revue, axe B).

    Elle ne peut plus diverger depuis que le verdict est transporté et non recalculé ; ce test
    épingle **que ce soit toujours le cas**.
    """
    jalons, tournois, tid = _attelage(avec_deroule=True, inscrits=34)

    assert jalons.preparation(tid, Jalon.DEMARRER).pret is True
    tournois.vers_pret(tid)
    assert tournois.demarrer(tid).id == tid


def test_un_tournoi_deja_lance_n_annonce_pas_qu_il_peut_demarrer() -> None:
    """La garde de statut, vue depuis le service — le **bloquant** de la revue.

    Sur un tournoi `en_cours`, `demarrer` lève `TransitionStatutInvalide` ; le jalon répondait
    pourtant « prêt, et l'action passera ». Seul le front masquait le mensonge, et `E16US007` /
    `E16US008`, qui consommeront ce contrat, n'auraient pas eu ce garde-fou.
    """
    jalons, tournois, tid = _attelage(avec_deroule=True, inscrits=40)
    tournois.vers_pret(tid)
    tournois.demarrer(tid)

    assert jalons.preparation(tid, Jalon.DEMARRER).pret is False
    with pytest.raises(TransitionStatutInvalide):
        tournois.demarrer(tid)


def test_terminer_hors_du_tournoi_en_cours_annonce_ce_que_la_garde_refusera() -> None:
    """Symétrique, sur l'autre membre : `terminer` n'accepte que `{EN_COURS}`.

    Un tournoi encore en *brouillon* — ou **en pause**, la pause déjeuner du jour J — ne peut pas
    être terminé. Le CA disait « terminer n'a aucune garde dure » : vrai du contenu, faux du statut.
    """
    complet = evaluer_completude(qualif=(30, 30), paiements=(120, 120))
    jalons, tournois, tid = _attelage(completude=complet)

    preparation = jalons.preparation(tid, Jalon.TERMINER)
    assert preparation.pret is False
    assert preparation.bloquant is True
    with pytest.raises(TransitionStatutInvalide) as refus:
        tournois.terminer(tid)
    # Même exigence littérale que pour les créneaux : une seule rédaction pour les deux versants.
    assert preparation.detail == str(refus.value)


def test_le_jalon_terminer_egale_la_completude_sportive_pendant_le_tournoi() -> None:
    """L'équivalence que l'écran « Prêt à terminer ? » consomme **par l'autre route**
    (`/completude`) : tant qu'elle tient, migrer l'écran sur le jalon ne changerait rien à
    ce qu'il affiche.

    Elle vaut **pendant le tournoi**, seule fenêtre où terminer est offert — c'est la précision que
    la garde de statut a rendue nécessaire.
    """
    completude = evaluer_completude(qualif=(28, 30), paiements=(113, 120))
    jalons, tournois, tid = _attelage(completude=completude, inscrits=40, avec_deroule=True)
    tournois.vers_pret(tid)
    tournois.demarrer(tid)

    preparation = jalons.preparation(tid, Jalon.TERMINER)
    assert preparation.lignes == completude.sportif
    assert preparation.pret == completude.sportif_complet


def test_le_jalon_terminer_suit_la_table_des_transitions_sur_tous_les_statuts() -> None:
    """Le jalon **dérive** la garde de statut de `_TRANSITIONS`, il ne la recopie pas.

    Ce test est ce qui rend la dérivation vérifiable : pour **chacun** des sept statuts, « le jalon
    annonce un blocage » doit valoir exactement « le service refuse ». La 1ʳᵉ correction portait
    `(BROUILLON, PRET)` et `EN_COURS` en dur — un second encodage de la table, dans le commit même
    qui érigeait le transport du verdict en doctrine (2ᵉ passe, axes A et C2).

    ⚠️ **Le refus est provoqué, pas déduit.** La 2ᵉ correction comparait `bloquant` à
    `tournois.transitions_possibles(tid)`, qui délègue à la **même** fonction que le jalon : les
    deux membres de l'assertion étaient le même appel, et le test ne pouvait pas échouer (3ᵉ passe,
    quatre axes). On exécute donc `terminer` pour de bon. Le jour où il sera accepté depuis *en
    pause*, ce test dira si les deux versants ont bougé ensemble — ce que l'ancienne forme ne
    pouvait pas faire.
    """
    complet = evaluer_completude(qualif=(30, 30), paiements=(120, 120))

    for statut in StatutTournoi:
        jalons, tournois, tid = _attelage(completude=complet, inscrits=40, avec_deroule=True)
        _amener_a(tournois, tid, statut)

        preparation = jalons.preparation(tid, Jalon.TERMINER)
        try:
            tournois.terminer(tid)
            refuse = False
        except TransitionStatutInvalide:
            refuse = True
        assert preparation.bloquant is refuse, f"désaccord sur {statut.value}"
        # ⚠️ Et la liste, elle, ne suit **pas** le blocage : « où en est le sportif » se lit à tout
        # statut. C'est l'asymétrie avec *démarrer*, dont la liste est la préparation. L'assertion
        # inverse — écrite en 4ᵉ passe — gravait une sur-correction que l'écran avait déjà annulée.
        assert preparation.lignes == complet.sportif, f"lignes perdues sur {statut.value}"


# --- Bornes -------------------------------------------------------------------------------------


@pytest.mark.parametrize("jalon", [Jalon.DEMARRER, Jalon.TERMINER])
def test_un_tournoi_inconnu_rend_404_sur_tous_les_membres(jalon: Jalon) -> None:
    """Un « rien ne manque » sur une ressource inexistante serait un 200 rassurant et faux."""
    jalons, _, _ = _attelage()

    with pytest.raises(TournoiIntrouvable):
        jalons.preparation(9999, jalon)


@pytest.mark.parametrize("jalon", [Jalon.ARCHIVER, Jalon.EXPORTER])
def test_les_membres_pas_encore_instruits_le_disent(jalon: Jalon) -> None:
    """Plutôt qu'une réponse vide, qui se lirait « rien ne manque, allez-y »."""
    jalons, _, tid = _attelage()

    with pytest.raises(JalonNonInstruit):
        jalons.preparation(tid, jalon)


def test_l_existence_du_tournoi_prime_sur_le_membre_non_instruit() -> None:
    """Ordre des contrôles : un tournoi inconnu répond « tournoi inconnu », quel que soit le jalon.

    L'inverse aurait masqué un identifiant faux derrière « cet écran n'existe pas encore ».
    """
    jalons, _, _ = _attelage()

    with pytest.raises(TournoiIntrouvable):
        jalons.preparation(9999, Jalon.EXPORTER)
