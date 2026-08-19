"""L'**arrêt programmé** — couper le déroulé sans le piloter tour par tour (E05US033, [ADR-0091]).

Tests écrits **depuis le CA** de l'US, avant l'implémentation (règle 9). L'oracle est la fiche
`stories/E05-moteur-phases.md` § E05US033, telle que le commanditaire l'a arbitrée les 18 et
19/08/2026 — pas ce que le code sait déjà faire. La distinction n'est pas théorique ici : le code
**ne savait rien faire du tout**, `StatutPhase.EN_PAUSE` ne gelant rien (constat vérifié au cadrage
du 19/08/2026, cf. `DETTE-073`). Un test dérivé de l'implémentation aurait donc consacré une pause
cosmétique.

Deux gardes portent l'essentiel et méritent d'être lues avant les autres :

- `test_un_arret_leve_ne_rearrete_pas_la_phase` garde le CA *« après reprise, la phase repart en
  automatique jusqu'au prochain arrêt »*. C'est **le** piège du mécanisme, et il est structurel :
  l'avancement est **dérivé à la lecture** (ADR-0090 §5) — après la reprise, « le tour 2 est achevé
  et un arrêt est posé après le tour 2 » reste **vrai pour toujours**. Un déclencheur qui relit la
  condition sans mémoire remet la phase en pause à la seconde suivante, et l'organisateur ne peut
  plus rien relancer. C'est ce qui impose de persister le **franchissement**, et non de le dériver.
- `test_un_arret_de_portee_depart_laisse_chaque_phase_finir_son_tour` garde l'arbitrage du
  commanditaire du 18/08/2026 : un arrêt de départ n'est **pas simultané**. C'est la raison d'être
  de l'état `ARME`, que rien d'autre ne justifierait.

⚠️ **Ce fichier ne teste pas le libellé du tour** (`test_domain_tour_de_phase.py` le fait déjà),
sauf pour le seul point qu'E05US033 y ajoute : une qualification **découpée** cesse d'être une phase
entière, donc elle annonce enfin un numéro de tour.

⚠️ **Il ne teste pas non plus le gel lui-même** — ce que `EN_PAUSE` refuse et ce qu'il laisse passer
(la correction d'un score déjà saisi, CA du 19/08/2026) n'est pas une règle de ce module mais une
garde de service : l'oracle vit dans `test_service_saisie.py` (section E05US033), là où le montage
de saisie existe déjà. Le dire ici parce que la frontière n'est pas devinable : ce module décide
**quand** couper, pas **ce que** couper interdit.

[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

import pytest

from domain.arret_programme import (
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    arrets_atteints,
    phases_a_arreter,
    verifier_arrets,
)
from domain.contrat_phase import TypePhase, UniteDeTour
from domain.erreurs import ArretProgrammeInvalide, DecoupageEnToursInvalide
from domain.phase import PhaseId
from domain.tour_de_phase import (
    DecoupageEnTours,
    libelle_de_tour,
    nb_tours_regles,
    unite_de_tour_effective,
)

# ─────────────────────────── CA : l'automatique reste le défaut ───────────────────────────


def test_une_phase_sans_arret_programme_ne_declenche_jamais_rien() -> None:
    """CA — *« une phase sans arrêt programmé se comporte exactement comme aujourd'hui »*.

    Le test le plus important de la livraison, et le moins spectaculaire : c'est lui qui garantit
    qu'aucune phase déjà en cours le jour du déploiement ne change de comportement. Il doit rester
    vrai pour **tout** tour achevé, y compris le dernier.
    """
    for tour_acheve in range(1, 12):
        assert arrets_atteints((), tour_acheve=tour_acheve, deja_traites=()) == ()


def test_un_arret_ne_se_declenche_pas_avant_son_tour() -> None:
    """CA — un arrêt posé *après le tour 5* ne coupe rien aux tours 1 à 4."""
    arret = ArretProgramme(apres_tour=5)

    for tour_acheve in range(1, 5):
        assert arrets_atteints((arret,), tour_acheve=tour_acheve, deja_traites=()) == ()

    assert arrets_atteints((arret,), tour_acheve=5, deja_traites=()) == (arret,)


# ─────────────────────────── CA : une liste, pas un arrêt unique ───────────────────────────


def test_une_phase_porte_plusieurs_arrets_et_chacun_attend_son_tour() -> None:
    """CA — *« plusieurs par phase : c'est une liste, pas un arrêt unique »*.

    L'organisateur prépare sa journée (« pause après le tour 2, pause après le tour 5 »). Les deux
    arrêts coexistent sur la même phase et se déclenchent **chacun à son tour**, pas ensemble.
    """
    apres_2 = ArretProgramme(apres_tour=2)
    apres_5 = ArretProgramme(apres_tour=5)
    arrets = (apres_2, apres_5)

    assert arrets_atteints(arrets, tour_acheve=2, deja_traites=()) == (apres_2,)
    assert arrets_atteints(arrets, tour_acheve=5, deja_traites=(2,)) == (apres_5,)


def test_un_arret_deja_traite_ne_se_redeclenche_pas() -> None:
    """CA — corollaire de la liste : un arrêt consommé sort du jeu.

    Sans quoi le deuxième passage du déclencheur re-couperait la même phase au même endroit.
    """
    arret = ArretProgramme(apres_tour=2)

    assert arrets_atteints((arret,), tour_acheve=2, deja_traites=(2,)) == ()


def test_aucun_arret_n_est_saute_quand_plusieurs_tours_s_achevent_d_un_coup() -> None:
    """Cas limite **non écrit au CA**, et tranché ici : le déclencheur regarde en arrière.

    L'avancement étant dérivé à la lecture, rien ne garantit que le déclencheur soit évalué à chaque
    frontière de tour — une correction en cascade, un lot de validations, une phase reprise après un
    incident peuvent faire passer `tour_courant` de 2 à 5 entre deux évaluations. Comparer par
    égalité (`apres_tour == tour_acheve`) perdrait alors silencieusement les arrêts intermédiaires :
    l'organisateur aurait programmé trois pauses et n'en verrait aucune.

    On rend donc **tous** les arrêts dus, du plus ancien au plus récent. Le service n'en applique
    qu'un (la phase ne peut être mise en pause qu'une fois) mais marque les autres traités, ce qui
    est la seule lecture honnête : ces pauses-là ont été **manquées**, pas annulées.
    """
    arrets = (
        ArretProgramme(apres_tour=2),
        ArretProgramme(apres_tour=3),
        ArretProgramme(apres_tour=4),
    )

    dus = arrets_atteints(arrets, tour_acheve=4, deja_traites=())

    assert [arret.apres_tour for arret in dus] == [2, 3, 4]


# ─────────────────────────────── CA : la portée de l'arrêt ───────────────────────────────


def test_un_arret_porte_sur_sa_phase_seule_par_defaut() -> None:
    """CA — *« cette phase seule, ou toutes les phases du même départ »*.

    Le défaut est le moins intrusif des deux : couper une phase n'éteint pas la salle. C'est le
    sens de lecture de la règle 12 appliqué à une valeur par défaut — le geste large se demande.
    """
    assert ArretProgramme(apres_tour=3).portee is PorteeArret.PHASE
    assert set(PorteeArret) == {PorteeArret.PHASE, PorteeArret.DEPART}


def test_un_arret_de_portee_depart_laisse_chaque_phase_finir_son_tour() -> None:
    """CA — *« un arrêt de portée départ laisse chaque phase finir son tour en cours »*.

    Arbitrage du commanditaire du 18/08/2026 : l'arrêt n'est **pas simultané**. Si la coupe tombe à
    la fin du tour 3 des poules, la qualification finit ses volées et le duel engagé va à son terme.

    Le modèle en découle : au moment où l'arrêt est **armé**, on note le tour que chaque phase a en
    cours ; une phase s'arrête quand ce tour-là est fini, c'est-à-dire quand son tour courant a
    **changé**. Comparer à un tour noté, plutôt que d'attendre un événement « tour fini », est ce
    qui rend le mécanisme compatible avec un avancement dérivé à la lecture (ADR-0090 §5).
    """
    poules, qualif, tableau = PhaseId(1), PhaseId(2), PhaseId(3)
    tours_a_finir = {poules: 3, qualif: 1, tableau: 2}

    # Instant de l'armement : personne n'a encore fini, donc personne ne s'arrête.
    assert phases_a_arreter(tours_a_finir, {poules: 3, qualif: 1, tableau: 2}) == ()

    # Les poules passent au tour 4 : leur tour 3 est fini, elles seules s'arrêtent.
    assert phases_a_arreter(tours_a_finir, {poules: 4, qualif: 1, tableau: 2}) == (poules,)

    # Plus tard, la qualification et le tableau finissent à leur tour.
    assert phases_a_arreter(tours_a_finir, {poules: 4, qualif: 2, tableau: 3}) == (
        poules,
        qualif,
        tableau,
    )


def test_une_phase_qui_n_a_plus_rien_en_cours_s_arrete_tout_de_suite() -> None:
    """Cas limite du même CA : `tour_courant is None` signifie *« plus rien ne tourne »*.

    C'est la convention d'`AvancementDePhase` (ADR-0090) — tout est joué, même si la phase n'est pas
    clôturée. Une telle phase n'a aucun tour à finir : la faire attendre un changement qui ne
    viendra jamais la laisserait `EN_COURS` pour l'éternité, et l'arrêt de départ resterait `ARME`
    sans jamais devenir `FRANCHI`. L'organisateur relancerait alors une pause qui n'a jamais eu
    lieu.
    """
    dormante = PhaseId(7)

    assert phases_a_arreter({dormante: None}, {dormante: None}) == (dormante,)


def test_une_phase_disparue_de_l_avancement_ne_bloque_pas_l_arret() -> None:
    """Cas limite : une phase clôturée à la main pendant que l'arrêt est armé (E12US008).

    Elle n'a plus d'avancement à lire. Elle ne doit ni être mise en pause (elle est terminée) ni
    empêcher l'arrêt d'aboutir — sans quoi un geste de clôture légitime gèlerait la reprise.
    """
    partie, restante = PhaseId(1), PhaseId(2)

    assert phases_a_arreter({partie: 2, restante: 1}, {restante: 1}) == (partie,)


# ────────────────────── CA : la pause s'atteint seule, se lève à la main ──────────────────────


def test_un_arret_franchi_retient_les_phases_qu_il_a_arretees() -> None:
    """CA — *« un arrêt de portée départ se relance d'un seul geste »*.

    Il faut donc savoir **lesquelles** il a arrêtées. Les déduire à la reprise (« toutes les phases
    en pause du départ ») relancerait aussi une phase que l'organisateur avait suspendue à la main
    pour une autre raison — un effet de bord qu'aucun écran ne lui expliquerait.
    """
    franchissement = FranchissementArret(
        phase_id=PhaseId(1), apres_tour=3, etat=EtatFranchissement.ARME
    )

    franchi = franchissement.franchir((PhaseId(1), PhaseId(2)))

    assert franchi.etat is EtatFranchissement.FRANCHI
    assert franchi.phases_arretees == (PhaseId(1), PhaseId(2))


def test_lever_un_arret_rend_toutes_ses_phases_d_un_seul_geste() -> None:
    """CA — *« la reprise est un geste manuel d'un admin »*, et un seul pour tout l'arrêt.

    *« Quatre boutons pour un seul arrêt créerait exactement le piège qu'on cherche à éviter — en
    oublier une. »*
    """
    franchi = FranchissementArret(
        phase_id=PhaseId(1),
        apres_tour=3,
        etat=EtatFranchissement.FRANCHI,
        phases_arretees=(PhaseId(1), PhaseId(2), PhaseId(3)),
    )

    leve = franchi.lever()

    assert leve.etat is EtatFranchissement.LEVE
    assert leve.phases_arretees == (PhaseId(1), PhaseId(2), PhaseId(3))


def test_un_arret_leve_ne_rearrete_pas_la_phase() -> None:
    """CA — *« après reprise, la phase repart en automatique jusqu'au prochain arrêt »*.

    ⚠️ **Le piège central de l'US.** L'avancement est dérivé à la lecture : une fois le tour 2
    achevé, la condition « tour 2 achevé **et** arrêt posé après le tour 2 » reste vraie
    indéfiniment. Un déclencheur sans mémoire remet donc la phase en pause aussitôt relancée, et
    l'organisateur perd la main **définitivement** — la salle ne repart jamais.

    Ce que ce test garde, c'est que le franchissement est une **trace persistée** et non une
    dérivation : un arrêt levé compte parmi les `deja_traites`, au même titre qu'un arrêt franchi.
    """
    apres_2 = ArretProgramme(apres_tour=2)
    apres_5 = ArretProgramme(apres_tour=5)

    # Le tour 2 est achevé depuis longtemps, l'arrêt a été franchi puis levé.
    assert arrets_atteints((apres_2, apres_5), tour_acheve=2, deja_traites=(2,)) == ()
    assert arrets_atteints((apres_2, apres_5), tour_acheve=4, deja_traites=(2,)) == ()

    # ... et l'arrêt suivant fonctionne toujours : la phase est repartie en automatique.
    assert arrets_atteints((apres_2, apres_5), tour_acheve=5, deja_traites=(2,)) == (apres_5,)


def test_un_franchissement_ne_recule_jamais() -> None:
    """Un arrêt **levé** ne se re-franchit pas et ne se relève pas deux fois.

    Le cycle de vie est monotone (`ARME → FRANCHI → LEVE`), comme celui d'une phase (ADR-0045) :
    c'est ce qui rend le déclencheur rejouable sans effet cumulatif. Un franchissement réversible
    ferait de chaque évaluation un tirage au sort.

    ⚠️ **Portée exacte de cette garde** : elle ne couvre que les refus depuis `LEVE`. Le retour
    `FRANCHI → ARME` n'est pas testé parce qu'il n'est pas *exprimable* — il n'existe aucune méthode
    `armer()`, l'état `ARME` étant posé à la construction par le service. Le dire ici plutôt que de
    laisser croire que le cycle entier est gardé : c'est le second oracle qui manquerait si l'on
    ajoutait un jour ce geste.
    """
    leve = FranchissementArret(phase_id=PhaseId(1), apres_tour=3, etat=EtatFranchissement.LEVE)

    with pytest.raises(ArretProgrammeInvalide):
        leve.franchir((PhaseId(1),))

    with pytest.raises(ArretProgrammeInvalide):
        leve.lever()


# ─────────────────────────────── Invariants de définition ───────────────────────────────


def test_un_arret_se_pose_apres_un_tour_qui_existe() -> None:
    """*« après un tour donné »* : le tour 0 n'existe pas, et un tour négatif encore moins.

    Un arrêt « après le tour 0 » couperait la phase avant son premier tir — ce n'est pas une pause,
    c'est un refus de démarrer, qui a déjà son geste (ne pas démarrer la phase).
    """
    for apres_tour in (0, -1, -7):
        with pytest.raises(ArretProgrammeInvalide):
            ArretProgramme(apres_tour=apres_tour)


def test_deux_arrets_ne_se_posent_pas_apres_le_meme_tour() -> None:
    """Deux arrêts au même endroit : le second est inapplicable, la phase étant déjà en pause.

    Refusé à la **composition** plutôt que toléré et ignoré en salle : l'organisateur qui a saisi
    deux fois « après le tour 3 » a fait une erreur de saisie, et le lui dire à l'atelier lui coûte
    un clic là où le découvrir le jour J ne lui coûte qu'une incompréhension.
    """
    with pytest.raises(ArretProgrammeInvalide):
        verifier_arrets((ArretProgramme(apres_tour=3), ArretProgramme(apres_tour=3)))


def test_deux_arrets_de_portees_differentes_au_meme_tour_sont_refuses_aussi() -> None:
    """Même refus, et il faut le dire : la portée ne désambiguïse pas.

    Un arrêt « phase » et un arrêt « départ » après le même tour poseraient la question de savoir
    lequel l'emporte — question sans réponse utile, puisque le geste large contient le geste étroit.
    """
    with pytest.raises(ArretProgrammeInvalide):
        verifier_arrets(
            (
                ArretProgramme(apres_tour=3, portee=PorteeArret.PHASE),
                ArretProgramme(apres_tour=3, portee=PorteeArret.DEPART),
            )
        )


def test_un_arret_apres_le_dernier_tour_est_refuse_quand_le_nombre_de_tours_est_connu() -> None:
    """Un arrêt après le dernier tour est **inerte** : la phase est finie, il n'y a rien à couper.

    Refusé seulement **quand le nombre de tours est connu** — un système suisse réglé à 7 rondes
    n'en joue que 5 si l'effectif ne le permet pas (`AvancementDePhase`), et l'atelier ne connaît
    pas toujours l'effectif. On ne refuse pas ce qu'on ne peut pas juger : c'est la doctrine déjà
    suivie par `EtapeDeroule._verifier_rondes_appariables`, et la reprendre évite d'inventer une
    seconde règle de silence.
    """
    verifier_arrets((ArretProgramme(apres_tour=9),), nb_tours=None)
    verifier_arrets((ArretProgramme(apres_tour=4),), nb_tours=5)

    with pytest.raises(ArretProgrammeInvalide):
        verifier_arrets((ArretProgramme(apres_tour=5),), nb_tours=5)


# ─────────────────── CA : la qualification et l'échauffement divisibles ───────────────────


def test_une_qualification_non_decoupee_reste_une_phase_entiere() -> None:
    """CA — le défaut ne change pas : *« 1 tour est vrai, pas un trou »* (E05US032).

    Garde la compatibilité avec l'US précédente : sans réglage, rien ne bouge.
    """
    assert unite_de_tour_effective(TypePhase.QUALIFICATION, None) is UniteDeTour.PHASE_ENTIERE
    assert nb_tours_regles(TypePhase.QUALIFICATION, None) == 1


def test_une_qualification_decoupee_avance_par_tours() -> None:
    """CA — *« la qualification et l'échauffement deviennent divisibles en tours »*.

    C'est le réglage reporté d'`E05US032`, qui n'avait pas d'emploi avant celui-ci : sans lui, ces
    deux types n'ont qu'un tour, et un arrêt « après le tour n » n'a nulle part où se poser.

    ⚠️ Le découpage **précise** le contrat, il ne le contredit pas : `PHASE_ENTIERE` signifie
    littéralement « rien dans la structure du format ne dit combien de tours » (ADR-0090). Quand
    l'organisateur le dit, la source existe enfin — et elle est de la configuration, pas du code
    (règle 2).
    """
    decoupage = DecoupageEnTours(nb_tours=2)

    assert unite_de_tour_effective(TypePhase.QUALIFICATION, decoupage) is UniteDeTour.TOUR
    assert nb_tours_regles(TypePhase.QUALIFICATION, decoupage) == 2
    assert unite_de_tour_effective(TypePhase.ECHAUFFEMENT, decoupage) is UniteDeTour.TOUR


def test_une_qualification_decoupee_annonce_enfin_un_numero_de_tour() -> None:
    """CA d'E05US032 — *« le libellé affiché est le mot du métier »* — appliqué au cas neuf.

    Une qualification entière ne dit rien (« Qualification », jamais « Qualification — tour 1 sur
    1 ») ; découpée en deux, elle dit « Tour 2 ». C'est le seul point où E05US033 touche au libellé,
    et il passe par la fonction **existante** : ouvrir un domicile de plus au libellé de tour est ce
    que `DETTE-020` interdit.
    """
    assert libelle_de_tour(UniteDeTour.PHASE_ENTIERE, tour=1, nb_tours=1) is None
    assert libelle_de_tour(UniteDeTour.TOUR, tour=2, nb_tours=2) == "Tour 2"


def test_un_decoupage_en_un_seul_tour_reste_une_phase_entiere() -> None:
    """Cas limite : « découpée en 1 tour » est le défaut écrit en clair, pas un découpage.

    Sans cette clause, une qualification réglée à 1 tour annoncerait « Tour 1 » — exactement le
    « Qualification — tour 1 sur 1 » que le CA d'E05US032 refuse, réintroduit par la porte du
    réglage.
    """
    decoupage = DecoupageEnTours(nb_tours=1)

    assert unite_de_tour_effective(TypePhase.QUALIFICATION, decoupage) is UniteDeTour.PHASE_ENTIERE
    assert nb_tours_regles(TypePhase.QUALIFICATION, decoupage) == 1


def test_un_decoupage_ne_se_regle_pas_a_zero_tour() -> None:
    """Invariant : une phase compte au moins un tour (CA d'E05US032, « aucun type exclu »)."""
    for nb_tours in (0, -3):
        with pytest.raises(DecoupageEnToursInvalide):
            DecoupageEnTours(nb_tours=nb_tours)


def test_un_decoupage_ne_change_rien_a_un_format_qui_compte_deja_ses_tours() -> None:
    """Le découpage ne s'applique qu'aux types dont la structure ne détermine pas les tours.

    Un système suisse tire son nombre de rondes de son réglage, une poule de son round-robin, un
    tableau de ses braquets : leur imposer un découpage d'organisateur créerait **deux** sources
    pour le même nombre, soit la divergence silencieuse qu'ADR-0076 a rendue impossible ailleurs.

    ⚠️ **Deux niveaux, et il faut les distinguer pour lire ce test.** L'**agrégat** (`Phase`,
    `EtapeDeroule`) *refuse* un découpage sur un tel type — c'est le patron déjà suivi par `poules`,
    `big_shoot_off` et `suisse`, dont la justification tient : « un réglage que rien ne lit est
    invisible et faux ». Le **résolveur** testé ici reste au contraire **total** : il ignore le
    réglage plutôt que de lever. Ce n'est pas une redondance molle mais la division du travail
    habituelle du domaine — l'agrégat garde la cohérence de la donnée, la fonction pure garde la
    propriété de rendre toujours une réponse. Un résolveur qui lèverait obligerait chaque écran de
    lecture à gérer une exception sur une donnée déjà validée à l'écriture.
    """
    decoupage = DecoupageEnTours(nb_tours=4)

    assert unite_de_tour_effective(TypePhase.SUISSE, decoupage) is UniteDeTour.RONDE
    assert unite_de_tour_effective(TypePhase.POULES, decoupage) is UniteDeTour.TOUR
    assert (
        unite_de_tour_effective(TypePhase.ELIMINATION_DIRECTE, decoupage)
        is UniteDeTour.TOUR_DE_TABLEAU
    )
