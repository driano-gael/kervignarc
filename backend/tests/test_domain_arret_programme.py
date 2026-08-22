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

⚠️ **Ce fichier ne teste pas le libellé du tour** — `test_domain_tour_de_phase.py` le fait déjà, et
E05US033 n'y touche pas : le périmètre final ne change rien à la résolution du libellé.

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
    ArretDeCirconstance,
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    arrets_applicables,
    arrets_atteints,
    phases_a_arreter,
    tour_d_un_arret_relatif,
    verifier_arrets,
)
from domain.bareme import BaremeQualification
from domain.contrat_phase import TypePhase
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import ArretProgrammeInvalide
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import PhaseId


def _etape(type_phase: TypePhase, arrets: tuple[ArretProgramme, ...] = ()) -> EtapeDeroule:
    """Une étape de déroulé **valide** du type demandé — le décor des invariants de définition.

    ⚠️ **Barème et grain ne sont donnés qu'à la qualification**, et il faut les deux moitiés de
    cette clause. Sans eux, `PhaseQualificationIncomplete` tombe **avant** la garde des arrêts et
    masque ce qu'on veut lire ; avec eux partout, c'est `GrainIncompatibleAvecTypePhase` qui tombe
    sur les autres types. Les deux vérifications sont voisines de celle qu'on exerce, et
    aucune n'est l'objet de ce fichier : le décor les satisfait, il ne les teste pas.

    Les réglages propres à un format (poules, Big Shoot Off, suisse) restent à `None` : aucun n'est
    exigé pour composer.
    """
    qualification = type_phase is TypePhase.QUALIFICATION
    return EtapeDeroule(
        tournoi_id=1,
        ordre=1,
        type=type_phase,
        bareme=BaremeQualification.creer(10, 3) if qualification else None,
        validation=GrainValidation(type=TypeGrain.FIN_DE_SERIE) if qualification else None,
        arrets=arrets,
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

    Le défaut est le moins intrusif des deux : couper une phase n'éteint pas la salle. C'est le sens
    de lecture de la règle 12 appliqué à une valeur par défaut — le geste large se demande.
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


# ──────────────── CA : un arrêt ne se pose que là où l'application lit le tour ────────────────


def test_un_arret_se_pose_sur_les_types_qui_annoncent_leurs_tours() -> None:
    """CA — *« l'organisateur programme les pauses du déroulé »*, sur les formats qui les admettent.

    Le déclencheur ne coupe qu'à une frontière de tour **observée** : il demande le tour courant au
    service qui déroule la phase. Les quatre types que `TYPES_DEROULES` recense en ont un ; c'est
    exactement le périmètre où une pause est autre chose qu'une intention.
    """
    for type_phase in (
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.POULES,
        TypePhase.SUISSE,
        TypePhase.BIG_SHOOT_OFF,
        # E05US027 : la colline rejoint les formats arrêtables, par la seule bascule
        # d'`avancement_lisible` au registre de contrat — `TYPES_ARRETABLES` en dérive (ADR-0093).
        TypePhase.COLLINE,
    ):
        etape = _etape(type_phase, arrets=(ArretProgramme(apres_tour=2),))

        assert etape.arrets == (ArretProgramme(apres_tour=2, portee=PorteeArret.PHASE),)


def test_un_arret_est_refuse_sur_un_type_qui_n_annonce_pas_ses_tours() -> None:
    """Le refus, plutôt qu'un réglage inerte — arbitrage du commanditaire du 19/08/2026.

    Ces trois types n'ont **aucun** tour observable : l'échauffement, le barrage, le placement. Un
    arrêt posé dessus serait accepté à l'atelier et définitivement inerte le jour J —
    l'organisateur découvrirait le jour de la compétition que sa pause repas n'a jamais eu lieu.
    C'est le mode de panne que `DETTE-028` nomme, et le refus est le seul verdict honnête.

    ⚠️ **La qualification en faisait partie jusqu'à E05US035**, qui l'en a sortie en lui donnant un
    découpage en tours et un lecteur d'avancement (ADR-0093) ; **la colline jusqu'à E05US027**, qui
    l'en a sortie en lui donnant `ServiceColline.avancement_de_phase`. Les trois qui restent ne sont
    pas un reste de plomberie et n'attendent aucune US : l'échauffement n'a ni barème ni feuille de
    marque — aucune donnée existante ne dit où il en est —, le placement n'a pas de service pour
    monter son arbre, et le barrage est un **départage**. Leur ouvrir la table demanderait de
    **décider** de quoi ils tirent leur avancement, pas seulement de brancher un lecteur.
    """
    for type_phase in (
        TypePhase.ECHAUFFEMENT,
        TypePhase.BARRAGE,
        TypePhase.PLACEMENT,
    ):
        with pytest.raises(ArretProgrammeInvalide):
            _etape(type_phase, arrets=(ArretProgramme(apres_tour=2),))


def test_le_refus_nomme_le_type_et_dit_ou_les_pauses_se_posent() -> None:
    """Un refus qui ne dit pas quoi faire à la place est un cul-de-sac (`P-3`).

    Le message part au client tel quel (`ArretProgrammeInvalide` → 422, règle 5 : c'est un message
    **écrit pour l'utilisateur**, pas un détail interne qui fuit). L'organisateur doit y lire les
    deux choses qui lui manquent : pourquoi ici non, et où oui.
    """
    with pytest.raises(ArretProgrammeInvalide) as refus:
        _etape(TypePhase.ECHAUFFEMENT, arrets=(ArretProgramme(apres_tour=2),))

    message = str(refus.value)
    assert "echauffement" in message
    assert "poules" in message
    # E05US035 : le message dit désormais aussi la qualification, qui est devenue le cas le plus
    # probable — c'est le format que tout le monde tire.
    assert "qualification" in message


def test_une_etape_sans_arret_reste_composable_sur_tout_type() -> None:
    """Le refus vise l'**arrêt**, pas le type : composer une qualification n'a pas changé d'un iota.

    Sans cette garde, la vérification aurait fait échouer toute composition de qualification — un
    refus qui déborde de son objet est pire qu'un réglage inerte : il casse ce qui marchait.
    """
    for type_phase in TypePhase:
        etape = _etape(type_phase)

        assert etape.arrets == ()


# ══════════════════════ E05US034 — l'arrêt posé le jour J ══════════════════════
#
# Tests écrits **depuis le CA** d'`E05US034`, avant l'implémentation (règle 9). L'oracle est la
# fiche `stories/E05-moteur-phases.md` § E05US034, puce *« le jour J, l'organisateur pose un arrêt
# relatif depuis le pilotage : "bloquer dans x tours". Il s'ajoute aux arrêts programmés, il ne les
# remplace pas »*.
#
# ⚠️ **Pourquoi un concept de plus et non un `ArretProgramme` de plus.** Un arrêt posé à l'atelier
# est de la **composition** : ADR-0076 §4 le place au tournoi, et *tous* les créneaux le rejouent.
# Un arrêt posé à 14 h parce que le chauffage est tombé est de la **conduite** : ADR-0076 §5 place
# le geste au départ, et le créneau de l'après-midi n'a aucune raison de le rejouer. Les deux
# natures ne peuvent donc pas partager un rangement — d'où [ADR-0092].
#
# [ADR-0092]: ../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md


def _circonstance(apres_tour: int, portee: PorteeArret = PorteeArret.PHASE) -> ArretDeCirconstance:
    """Un arrêt de circonstance du créneau 7 sur la phase 3 — le décor par défaut de la section."""
    return ArretDeCirconstance(
        depart_id=7, phase_id=PhaseId(3), apres_tour=apres_tour, portee=portee
    )


# ────────────── CA : « bloquer dans x tours » se traduit en « après le tour n » ──────────────


def test_bloquer_dans_un_tour_coupe_a_la_fin_du_tour_en_cours() -> None:
    """CA — *« bloquer dans x tours »*, cas x = 1 : le tour en cours finit, puis la salle s'arrête.

    C'est la valeur la plus demandée le jour J (« on s'arrête après celui-là ») et c'est aussi la
    borne basse : il n'existe pas d'arrêt « tout de suite », le mécanisme coupe **à la fin d'un
    tour** (ADR-0091) et jamais au milieu.
    """
    assert tour_d_un_arret_relatif(tour_courant=3, dans_x_tours=1) == 3


def test_bloquer_dans_deux_tours_laisse_jouer_le_tour_en_cours_et_le_suivant() -> None:
    """CA — cas x = 2 : *deux* tours se jouent encore, donc la coupe tombe après le second.

    ⚠️ **C'est ici que se joue l'erreur de décalage d'une unité**, et elle n'est pas rattrapable en
    aval : `tour_courant + x` couperait après un tour de trop, soit — sur un système suisse de cinq
    rondes — une pause qui tombe une demi-heure après le repas. Le tour courant **compte** dans les
    « x tours », parce que c'est ce que l'organisateur voit à l'écran au moment où il clique.
    """
    assert tour_d_un_arret_relatif(tour_courant=3, dans_x_tours=2) == 4


def test_bloquer_dans_zero_tour_est_refuse() -> None:
    """Un arrêt qui ne laisse finir aucun tour n'existe pas : ce serait couper en plein tir.

    Le refus est **explicite** plutôt qu'un repli silencieux sur 1 : l'organisateur qui a tapé 0
    voulait probablement « maintenant », et lui répondre « d'accord, après ce tour » sans le dire
    lui ferait croire que le geste « arrêter tout de suite » existe.
    """
    with pytest.raises(ArretProgrammeInvalide):
        tour_d_un_arret_relatif(tour_courant=3, dans_x_tours=0)


def test_un_arret_relatif_ne_se_pose_pas_sur_une_phase_dont_le_tour_est_inconnu() -> None:
    """Sans tour courant lisible, « dans x tours » n'a pas d'origine — donc pas de sens.

    `tour_courant is None` a au moins cinq provenances (cf. `ServiceArretsProgrammes._tour_acheve`),
    dont « tout est joué » et « aucun lecteur pour ce type ». Aucune n'autorise à deviner un point
    de départ : poser l'arrêt après le tour 1 « par défaut » couperait une phase déjà finie, ou
    couperait la salle au premier tour d'une phase qu'on croyait à son cinquième.
    """
    with pytest.raises(ArretProgrammeInvalide):
        tour_d_un_arret_relatif(tour_courant=None, dans_x_tours=2)


# ────────── CA : « il s'ajoute aux arrêts programmés, il ne les remplace pas » ──────────


def test_les_deux_natures_d_arret_sont_appliquees_ensemble() -> None:
    """CA — l'arrêt du jour J **s'ajoute** : le déclencheur voit les deux sources en un seul jeu.

    L'organisateur a programmé le repas après le tour 2 à l'atelier ; il ajoute « dans un tour »
    à 14 h alors que le tour 4 tourne. Les deux coupes doivent tomber.
    """
    applicables = arrets_applicables(
        arrets_de_l_etape=(ArretProgramme(apres_tour=2),),
        arrets_de_circonstance=(_circonstance(apres_tour=4),),
    )

    assert tuple(arret.apres_tour for arret in applicables) == (2, 4)


def test_les_arrets_applicables_sont_rendus_du_plus_ancien_au_plus_recent() -> None:
    """L'ordre est celui du déroulé, quelle que soit la source — l'aval en dépend.

    `arrets_atteints` rend les arrêts triés et `_appliquer` n'applique que le **plus ancien** dû ;
    lui livrer un jeu désordonné ferait consommer la mauvaise pause quand deux tours ont été
    franchis entre deux évaluations.
    """
    applicables = arrets_applicables(
        arrets_de_l_etape=(ArretProgramme(apres_tour=5), ArretProgramme(apres_tour=1)),
        arrets_de_circonstance=(_circonstance(apres_tour=3),),
    )

    assert tuple(arret.apres_tour for arret in applicables) == (1, 3, 5)


def test_deux_arrets_sur_le_meme_tour_fusionnent_au_lieu_de_couper_deux_fois() -> None:
    """Le déclencheur est **tolérant** là où la pose est stricte : ce n'est pas une inconséquence.

    Poser un arrêt de circonstance sur un tour déjà pris est refusé à l'organisateur, qui a l'écran
    devant lui. Mais la collision peut naître **après coup**, sans que personne ne mente : l'atelier
    ajoute un arrêt après le tour 4 au déroulé du tournoi pendant qu'un créneau porte déjà un arrêt
    de circonstance après le tour 4. L'atelier ne connaît pas les arrêts de circonstance — ADR-0076
    lui interdit même de les voir. Lever une exception à l'évaluation gèlerait alors le déclencheur
    du créneau : plus aucune pause ne tomberait, pour aucune phase.

    ⚠️ Fusionner est aussi ce qui garde l'unicité `(phase_id, apres_tour)` du franchissement vraie :
    une seule coupe, une seule trace, un seul bouton de relance.
    """
    applicables = arrets_applicables(
        arrets_de_l_etape=(ArretProgramme(apres_tour=4),),
        arrets_de_circonstance=(_circonstance(apres_tour=4),),
    )

    assert tuple(arret.apres_tour for arret in applicables) == (4,)


def test_la_fusion_retient_la_portee_la_plus_large() -> None:
    """Quand les deux natures se rencontrent sur un tour, c'est la **plus large** qui l'emporte.

    Arbitrer dans l'autre sens laisserait tirer une salle que l'un des deux arrêts voulait éteindre
    entièrement — un arrêt de créneau *contient* un arrêt de phase, donc l'appliquer honore les
    deux. L'inverse n'est pas vrai.
    """
    applicables = arrets_applicables(
        arrets_de_l_etape=(ArretProgramme(apres_tour=4, portee=PorteeArret.PHASE),),
        arrets_de_circonstance=(_circonstance(apres_tour=4, portee=PorteeArret.DEPART),),
    )

    assert applicables[0].portee is PorteeArret.DEPART


def test_sans_arret_de_circonstance_le_jeu_applicable_est_celui_de_l_etape() -> None:
    """Non-régression d'`E05US033` : un créneau où personne n'a rien posé se comporte à l'identique.

    C'est le pendant de `test_une_phase_sans_arret_programme_ne_declenche_jamais_rien` pour cette
    tranche — la garantie que la capacité neuve ne change rien tant qu'on ne s'en sert pas.
    """
    etape = (ArretProgramme(apres_tour=2), ArretProgramme(apres_tour=5))

    assert arrets_applicables(etape, ()) == etape


# ────────────── Invariants de l'arrêt de circonstance lui-même ──────────────


def test_un_arret_de_circonstance_se_pose_apres_un_tour_existant() -> None:
    """Même invariant qu'`ArretProgramme`, tenu à la construction — `replace()` compris.

    Le redire ici plutôt que de s'en remettre à la conversion : les deux types sont construits par
    des chemins différents (l'un par le JSON d'étape, l'autre par une route de pilotage), et un
    invariant qui ne vaut que sur l'une des deux portes n'est pas un invariant.
    """
    with pytest.raises(ArretProgrammeInvalide):
        _circonstance(apres_tour=0)


def test_un_arret_de_circonstance_appartient_a_un_creneau() -> None:
    """Le `depart_id` est ce qui distingue les deux natures — il n'est pas décoratif (ADR-0092).

    Sans lui, l'arrêt serait rejoué par tous les créneaux du tournoi, ce qui est exactement la
    propriété qu'on refuse : la panne de chauffage du matin n'arrête pas l'après-midi.
    """
    arret = _circonstance(apres_tour=2)

    assert arret.depart_id == 7
    assert arret.definition() == ArretProgramme(apres_tour=2, portee=PorteeArret.PHASE)
