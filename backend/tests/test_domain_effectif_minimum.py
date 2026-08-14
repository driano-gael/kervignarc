"""Tests unitaires de l'**effectif minimum d'un format** (E05US021) — domaine pur, sans base.

Écrits **depuis le CA** de `stories/E05-moteur-phases.md` (règle 9), avant l'implémentation. Les
puces couvertes, dans l'ordre :

- « **effectif minimum déduit** » — l'application dérive des prélèvements le nombre d'inscrits en
  dessous duquel le format ne peut pas se dérouler ; « les rangs 33 et suivants » exige 34 classés
  pour produire un tableau de 2 ;
- « **minimum exigé, facultatif** » — un format peut exiger davantage que son minimum technique,
  jamais moins ; l'énoncer plus bas rend le format inapplicable ;
- « **visible à la composition** » — la projection annonce le minimum, effectif simulé ou non ;
- « **portée du calcul** » — un rang se lit dans le classement de sa phase source, et la chaîne se
  **remonte** jusqu'à la phase alimentée par les inscriptions (E05US024). Seules les phases dont le
  moteur sait lire le classement (`_TYPES_CLASSANTS_LUS`) comptent ; une fenêtre amont **bornée**
  ne fixe aucun plancher.
  ⚠️ Cet en-tête a affirmé jusqu'au 08/08/2026 que « seuls les prélèvements visant la **première**
  phase se traduisent en nombre d'inscrits » — vrai avant E05US024, faux depuis, et non corrigé par
  le commit qui ajoutait pourtant cinq tests le contredisant. C'est l'oracle local que lira le
  prochain auteur de test : le laisser périmé, c'est le piège de la règle 9 un cran plus bas.

Le raisonnement du chiffre, une fois pour toutes : une phase en tableau a besoin de **deux**
participants ; un prélèvement « à partir du rang d » n'en a deux que lorsque la phase source en
classe `d + 1`. D'où `d - 1 + 2` inscrits, soit 34 pour d = 33.
"""

from __future__ import annotations

import datetime

import pytest

from domain.anomalie import Anomalie, Gravite
from domain.bareme import BaremeQualification
from domain.deroule import effectif_minimum, projeter
from domain.erreurs import EffectifMinimumIncoherent, ExigenceEffectifInvalide
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.phase import IssueTour, SourcePhase, TypePhase
from domain.tournoi import Tournoi


def _qualification(ordre: int = 1) -> ModelePhase:
    return ModelePhase.qualification(BaremeQualification.preset_ffta_18m(), ordre=ordre)


def _tableau(ordre: int, *sources: SourcePhase) -> ModelePhase:
    return ModelePhase(ordre=ordre, type=TypePhase.ELIMINATION_DIRECTE, sources=tuple(sources))


def _echauffement(ordre: int) -> ModelePhase:
    return ModelePhase(ordre=ordre, type=TypePhase.ECHAUFFEMENT)


def _codes(anomalies: tuple[Anomalie, ...]) -> list[str]:
    return [anomalie.code for anomalie in anomalies]


# --- CA « effectif minimum déduit » --------------------------------------------------------------


def test_une_qualification_seule_nexige_quun_archer() -> None:
    """Rien dans une qualification ne réclame un effectif : elle accueille qui se présente."""
    assert effectif_minimum([_qualification()]) == 1


def test_un_tableau_exige_deux_archers_pour_avoir_un_duel() -> None:
    assert effectif_minimum([_qualification(), _tableau(2, SourcePhase.par_rangs(1, 1, 32))]) == 2


def test_les_rangs_33_et_suivants_exigent_34_inscrits() -> None:
    """L'exemple même du CA — un tableau de 2 ne se monte qu'à partir du 34ᵉ classé."""
    etapes = [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]

    assert effectif_minimum(etapes) == 34


def test_une_plage_fermee_haute_exige_autant_quune_plage_ouverte() -> None:
    """« Les rangs 33 à 64 » ne prend deux archers qu'au 34ᵉ, comme « 33 et suivants »."""
    etapes = [_qualification(), _tableau(2, SourcePhase.par_rangs(1, 33, 64))]

    assert effectif_minimum(etapes) == 34


def test_cest_la_phase_la_plus_exigeante_qui_fixe_le_minimum() -> None:
    """Le déroulé d'ADR-0068 : un tableau principal 1-32, un classement « 33 et suivants »."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_rangs(1, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_plusieurs_prelevements_sur_une_phase_se_cumulent_donc_le_plus_bas_decide() -> None:
    """Une phase nourrie par « 1 à 8 » **et** « 33 à 40 » a ses deux archers dès le 2ᵉ inscrit."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 8), SourcePhase.par_rangs(1, 33, 40)),
    ]

    assert effectif_minimum(etapes) == 2


def test_un_format_sans_etape_nexige_rien() -> None:
    assert effectif_minimum([]) == 1


# --- Notes « portée du calcul » : un rang se lit dans sa phase source ----------------------------


def test_un_prelevement_par_issue_de_tour_ne_fixe_aucun_minimum() -> None:
    """« Les perdants du tour 2 » ne se traduit pas en nombre d'inscrits — le déroulé en décide.

    Le plancher **structurel** subsiste : un tableau reste un tableau, il lui faut deux tireurs.
    """
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_issue_de_tour(2, tour=2, issue=IssueTour.PERDANTS)),
    ]

    assert effectif_minimum(etapes) == 2


def test_le_reste_ne_chiffre_rien_mais_un_tableau_reste_un_tableau() -> None:
    """« Le reste » ne dit pas *combien* d'inscrits il faut, mais la phase qu'il alimente **oppose**
    toujours deux tireurs — le plancher structurel ne se perd pas en route.

    ⚠️ Un premier jet rendait `1` ici, et son test l'entérinait : à 1 inscrit, le moteur levait
    `EffectifTableauInvalide` **en salle**, soit le défaut même que l'US retire.
    """
    etapes = [_qualification(), _tableau(2, SourcePhase.le_reste(1))]

    assert effectif_minimum(etapes) == 2


def test_un_prelevement_dans_une_phase_intermediaire_ne_se_lit_pas_en_inscrits() -> None:
    """Le rang 33 **du tableau** n'est pas le 33ᵉ inscrit : ce cas relève du diagnostic, pas du
    minimum. L'annoncer comme un besoin de 34 inscrits serait annoncer un chiffre faux."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_rangs(2, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 2


# --- Le classement traduisible est celui d'une phase CLASSANTE, où qu'elle soit dans le déroulé ---
# L'oracle de cette section est le **moteur** : `ServiceSaisieDuels._classement_de_l_ordre` sait
# lire une qualification **et** un tableau, et rend `None` pour tout autre type. Un plancher qui
# viserait autre chose mentirait — et il a menti dans les deux sens avant d'être corrigé.
#
# ⚠️ **Élargi par E05US024.** La section s'intitulait « celui de la QUALIFICATION, pas celui de la
# première phase », et son oracle était `_ordre_de_la_qualification` — méthode qui n'existe plus.
# Ce qui a changé n'est pas la règle (« le plancher vise exactement ce que le moteur lira ») mais
# **ce que le moteur sait lire**. Les deux tests de refus abusif ci-dessous restent donc valables
# tels quels : ils portent sur des types que rien n'exécute, ce que cette US ne touche pas.


def test_un_echauffement_en_tete_ne_desactive_pas_le_controle() -> None:
    """Le déroulé d'ADR-0068, précédé d'un échauffement : le plancher ne bouge pas d'un cran.

    ⚠️ Le défaut que ce test verrouille était **bloquant** : viser la première phase au lieu de la
    qualification rendait un plancher de 1, l'écran n'affichait rien, le tournoi démarrait, et la
    consolante cassait sur la tablette. `echauffement` est l'un des types offerts par l'écran de
    composition — le déroulé n'a rien d'exotique.
    """
    etapes = [
        _echauffement(1),
        _qualification(ordre=2),
        _tableau(3, SourcePhase.par_rangs(2, 1, 32)),
        _tableau(4, SourcePhase.par_rangs(2, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_le_plancher_remonte_la_chaine_des_prelevements() -> None:
    """**CA E05US024 — l'effectif minimum suit la chaîne.**

    « Les rangs 5 et suivants d'un tableau qui prend lui-même les rangs 17 à 32 de la
    qualification » : pour que ce tableau classe 6 archers (5ᵉ et 6ᵉ, soit les deux tireurs que le
    tableau aval exige), la qualification doit en classer `17 - 1 + 6 = 22`. Le décalage se
    **cumule** le long de la chaîne.

    Avant cette US, seule une source visant la qualification comptait : ce déroulé n'annonçait que
    son plancher structurel, 2. L'organisateur démarrait à 12 inscrits et la phase manquait de monde
    en salle — le mode de défaillance que le plancher existe pour éviter.
    """
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 17, 32)),
        _tableau(3, SourcePhase.par_rangs(2, rang_debut=5)),
    ]

    assert effectif_minimum(etapes) == 22


def test_un_tableau_en_tete_se_traduit_en_inscrits_comme_une_qualification() -> None:
    """Une phase **en tête** est alimentée par les inscriptions, quel qu'en soit le type (E05US024).

    ⚠️ **Ce test remplace `test_sans_qualification_aucun_rang_ne_se_traduit_en_inscrits`**, dont la
    prémisse est tombée avec E05US024 : « sans qualification, il n'y a aucun classement à lire ». Ce
    n'est plus vrai — le moteur lit désormais le classement de **toute** phase classante, et un
    tableau en tête en est une. « Les rangs 33 et suivants » de ce tableau réclament donc bien 34
    inscrits : le tableau les classe tous, puisque rien ne l'a filtré en amont.

    Ce que l'ancien test protégeait reste protégé ailleurs, et c'est ce qui permet de le remplacer
    sans perte : `test_un_type_sans_consommateur_ne_bloque_pas_le_lancement` couvre le refus abusif
    (le vrai risque), et `test_une_fenetre_dun_seul_rang_ne_fixe_pas_de_plancher` la fenêtre trop
    étroite.
    """
    etapes = [
        _tableau(1),
        _tableau(2, SourcePhase.par_rangs(1, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_une_phase_sans_opposition_se_contente_dun_participant() -> None:
    """Qualification et échauffement font tirer l'archer **seul** ; les six autres opposent."""
    assert effectif_minimum([_echauffement(1)]) == 1
    assert effectif_minimum([_qualification()]) == 1


def _avec_prelevement_haut(type_phase: TypePhase) -> list[ModelePhase]:
    """Une qualification, puis une phase de `type_phase` prélevant « les rangs 33 et suivants »."""
    return [
        _qualification(),
        ModelePhase(ordre=2, type=type_phase, sources=(SourcePhase.par_rangs(1, rang_debut=33),)),
    ]


@pytest.mark.parametrize("type_deroule", [TypePhase.ELIMINATION_DIRECTE, TypePhase.POULES])
def test_un_type_que_le_moteur_deroule_reclame_ses_34_inscrits(type_deroule: TypePhase) -> None:
    """Le plancher n'a de sens que si le moteur va réellement monter la phase — c'est le cas ici.

    ⚠️ **Les poules y entrent en E05US023, `placement` en sort** — les deux mouvements viennent du
    registre de contrat ([ADR-0083]), qui ne laisse plus écrire « déroulé » à côté de « aucun
    service ne le monte ». Le cas `placement` est traité par
    `test_un_type_au_decor_darbre_mais_sans_service_ne_bloque_pas_le_lancement` ci-dessous.

    [ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
    """
    assert effectif_minimum(_avec_prelevement_haut(type_deroule)) == 34


@pytest.mark.parametrize(
    "type_sans_moteur",
    [
        TypePhase.PLACEMENT,
        TypePhase.SUISSE,
        TypePhase.COLLINE,
        TypePhase.BARRAGE,
    ],
)
def test_un_type_sans_consommateur_ne_bloque_pas_le_lancement(type_sans_moteur: TypePhase) -> None:
    """Ces types ont un moteur de domaine — ou un décor — mais **aucun service ne les déroule**.

    Leur prélèvement ne sera pas honoré : rien ne cassera en salle, donc rien ne justifie de refuser
    le démarrage. ⚠️ Un premier jet leur réclamait 34 inscrits — un déroulé « qualification →
    poules » cessait donc de démarrer à 28, pour une phase que rien n'exécute. **Refuser à tort est
    le pire mode de défaillance de cette US** : il ne se répare que le jour J, en éditant le
    déroulé. Le plancher structurel (deux tireurs) subsiste, lui.

    ⚠️ **`placement` a rejoint cette liste en E05US023, et les poules l'ont quittée.** Le cas
    `placement` est le plus instructif : il n'a jamais eu de service pour monter son tableau, mais
    `_TYPES_DEROULES` l'y comptait — E06US006 l'avait constaté et laissé, « corriger la table
    changerait le plancher, donc le comportement d'une autre US ». Le registre de contrat
    (`domain/contrat_phase.py`, ADR-0083) a tranché : ce test-ci est donc, littéralement, la
    disparition du refus abusif qu'E05US021 nommait comme sa pire défaillance.

    Le jour où l'un de ces types gagne son service, il entre dans `TYPES_DEROULES` et ce test change
    de camp — c'est le signal attendu, pas une régression. **C'est arrivé au Big Shoot Off le
    14/08/2026** (E05US028) : il a quitté cette liste pour celle du test précédent, et le plancher
    de 34 lui est désormais réclamé — légitimement, puisque son prélèvement est réellement honoré.
    """
    assert effectif_minimum(_avec_prelevement_haut(type_sans_moteur)) == 2


# --- Fenêtres de rangs trop étroites : un défaut de composition, pas un plancher -----------------


def test_une_fenetre_dun_seul_rang_ne_fixe_pas_de_plancher() -> None:
    """« Les rangs 33 à 33 » ne donnera **jamais** deux tireurs, à aucun effectif.

    Annoncer 34 laisserait croire qu'un effectif répare le format ; c'est faux — c'est le déroulé
    qu'il faut corriger. On n'invente donc pas de plancher pour un prélèvement impossible.
    """
    etapes = [_qualification(), _tableau(2, SourcePhase.par_rangs(1, 33, 33))]

    assert effectif_minimum(etapes) == 2


def test_une_fenetre_etroite_ne_masque_pas_la_vraie_exigence_de_sa_voisine() -> None:
    """Le piège du `min` : « rangs 1 à 1 » **et** « rangs 33 et suivants » sur la même phase.

    La fenêtre étroite a le plus petit rang de départ, donc elle gagnait le `min` et faisait
    annoncer 2 — alors qu'elle n'apporte qu'un archer et que la seconde en exige 34.
    """
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 1), SourcePhase.par_rangs(1, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_une_phase_sans_prelevement_est_peuplee_par_les_inscrits() -> None:
    """Une phase en tableau que rien n'alimente reçoit tout le monde (`# DETTE-028`) : deux archers
    lui suffisent, mais il en faut deux."""
    assert effectif_minimum([_tableau(1)]) == 2


# --- CA « minimum exigé, facultatif » ------------------------------------------------------------


def test_un_format_peut_exiger_plus_que_son_minimum_technique() -> None:
    """« Pas de tournoi de ce type sous 40 archers » — une règle de club, au-dessus du déduit."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=40,
    )

    assert format_tournoi.effectif_minimum == 40


def test_sans_exigence_le_minimum_du_format_est_celui_quil_deduit() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.effectif_minimum == 34
    assert format_tournoi.anomalies() == ()


def test_exiger_exactement_le_minimum_deduit_est_licite() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=34,
    )

    assert format_tournoi.effectif_minimum == 34
    assert format_tournoi.anomalies() == ()


def test_exiger_moins_que_le_minimum_deduit_rend_le_format_inapplicable() -> None:
    """Un chiffre saisi sous le plancher technique est un mensonge : il laisserait lancer un tournoi
    que le moteur ne saura pas dérouler — le défaut même que l'US corrige."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=20,
    )

    anomalies = format_tournoi.anomalies()

    assert _codes(anomalies) == ["effectif_minimum_incoherent"]
    assert anomalies[0].gravite is Gravite.BLOQUANTE
    assert not format_tournoi.projeter().est_applicable


def test_un_format_au_minimum_incoherent_refuse_de_sappliquer() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=20,
    )

    with pytest.raises(EffectifMinimumIncoherent):
        format_tournoi.appliquer(1)


@pytest.mark.parametrize("absurde", [0, -1])
def test_une_exigence_absurde_est_refusee_des_la_saisie(absurde: int) -> None:
    """Zéro ou négatif ne veut rien dire : « aucune exigence » se dit en ne réglant rien."""
    with pytest.raises(ExigenceEffectifInvalide):
        FormatTournoi.creer("Salle 120", [_qualification()], effectif_minimum_exige=absurde)


@pytest.mark.parametrize("absurde", [0, -1])
def test_un_tournoi_refuse_la_meme_exigence_absurde_a_la_construction(absurde: int) -> None:
    """L'invariant est sur `__post_init__`, **pas** sur la méthode qui le règle — et ce test le
    prouve par la porte que le correctif visait.

    Le repository reconstruit `Tournoi(...)` directement depuis la colonne : un contrôle logé dans
    la seule `exiger_effectif_minimum` laissait entrer une valeur absurde par cette porte-là. Un
    test qui passerait par la méthode serait vert avec **l'ancienne** implémentation, donc ne
    prouverait rien.
    """
    with pytest.raises(ExigenceEffectifInvalide):
        Tournoi(
            nom="Trophée",
            date=datetime.date(2026, 3, 14),
            effectif_minimum_exige=absurde,
        )


# --- CA « visible à la composition » -------------------------------------------------------------


def test_la_projection_annonce_le_minimum_sans_effectif_simule() -> None:
    """Le minimum est une propriété du **format**, pas de l'effectif : il s'affiche d'emblée."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.projeter().effectif_minimum == 34


def test_la_projection_annonce_le_minimum_avec_un_effectif_simule() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.projeter(effectif=28).effectif_minimum == 34


def test_la_projection_dun_format_exigeant_annonce_lexigence() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=40,
    )

    assert format_tournoi.projeter(effectif=28).effectif_minimum == 40


def test_la_projection_generique_annonce_le_minimum_deduit() -> None:
    """`projeter` ne connaît que des étapes : il annonce le déduit, que le format relève ensuite."""
    projection = projeter([_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))])

    assert projection.effectif_minimum == 34


def test_un_deroule_qui_boucle_ne_part_pas_en_recursion() -> None:
    """Le plancher d'un brouillon cyclique se calcule, il ne fait pas tomber l'écran.

    Bloquant de revue, reproduit par deux axes. `_inscrits_pour_classer` fondait sa terminaison sur
    l'antériorité des sources, « vérifiée par `verifier_sequence` ». L'argument vaut pour les
    chemins d'**écriture** — pas pour `projeter`, dont la docstring dit l'inverse (« une séquence
    incohérente ne fait pas échouer le calcul, elle le **décrit** »), et pas depuis
    E01US024/ADR-0063, où un format s'enregistre incomplet **sans** passer par `verifier_sequence`.

    Un brouillon dont une étape se désigne elle-même en source partait donc en `RecursionError`,
    donc en **500** — sur l'écran de diagnostic dont le métier est justement de dire à
    l'organisateur que sa composition boucle.
    """
    etapes = [
        _qualification(1),
        _tableau(2, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=8)),
    ]

    # Le plancher structurel subsiste (un tableau veut deux tireurs) ; aucun rang n'est chiffrable.
    assert effectif_minimum(etapes) == 2


def test_un_cycle_entre_deux_etapes_ne_part_pas_en_recursion() -> None:
    """Même garde, sur un cycle de longueur 2 — l'auto-source n'est pas le seul cas."""
    etapes = [
        _qualification(1),
        _tableau(2, SourcePhase.par_rangs(ordre_source=3, rang_debut=1, rang_fin=8)),
        _tableau(3, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=8)),
    ]

    assert effectif_minimum(etapes) == 2


def test_le_plancher_est_le_minimum_des_exigences_pas_celui_des_rangs() -> None:
    """Deux sources de **profondeurs différentes** : la plus basse en rang n'est pas la moins chère.

    Correctif de revue (axe C1). Le code prenait d'abord la source au plus petit `rang_debut`, ce
    qui supposait que toutes visaient la **même** phase — vrai tant que seule la qualification était
    lisible, faux depuis cette US.

    Ici la phase 3 est nourrie par « les rangs 5 et suivants de la phase 2 » — un tableau qui prend
    lui-même les places 17 à 32, donc une source **chère** : 22 inscrits — **et** par « les rangs 6
    et suivants de la qualification », qui n'en réclame que 7. La première a pourtant le
    `rang_debut`
    le plus bas (5 < 6) : l'ancien code la choisissait pour ce seul motif et annonçait **22**, alors
    que 18 suffisent (ce que réclame la phase 2 pour elle-même). Un refus abusif au démarrage.
    """
    etapes = [
        _qualification(1),
        _tableau(2, SourcePhase.par_rangs(ordre_source=1, rang_debut=17, rang_fin=32)),
        _tableau(
            3,
            SourcePhase.par_rangs(ordre_source=2, rang_debut=5, rang_fin=None),
            SourcePhase.par_rangs(ordre_source=1, rang_debut=6, rang_fin=None),
        ),
    ]

    # 18 = ce que la phase 2 exige d'elle-même (17 - 1 + 2). La phase 3, elle, se contente de 7.
    assert effectif_minimum(etapes) == 18


def test_une_source_infaisable_n_eteint_pas_l_exigence_de_sa_voisine() -> None:
    """Le sens inverse du précédent : un `None` ne doit pas ramener le plancher au structurel.

    La phase 3 prélève « les rangs 33 et suivants » d'un tableau qui n'en prend que 32 — infaisable
    à tout effectif, donc `None` — **et** « les rangs 60 et suivants » de la qualification, qui
    réclame 61 inscrits. Le premier `None` faisait retomber tout le calcul sur le plancher
    structurel (2) : le tournoi démarrait, puis manquait de monde en salle.
    """
    etapes = [
        _qualification(1),
        _tableau(2, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=32)),
        _tableau(
            3,
            SourcePhase.par_rangs(ordre_source=2, rang_debut=33, rang_fin=None),
            SourcePhase.par_rangs(ordre_source=1, rang_debut=60, rang_fin=None),
        ),
    ]

    assert effectif_minimum(etapes) == 61


def test_un_prelevement_dans_un_type_non_lisible_ne_fixe_pas_de_plancher() -> None:
    """Le verrou de `_TYPES_CLASSANTS_LUS` dans le sens **dangereux** (correctif de revue, axe B/D).

    La table est présentée comme le miroir de `ServiceSaisieDuels._classement_de_l_ordre`, et sa
    divergence est censée rouvrir le défaut d'E05US021. Or seul le sens « retirer un type » était
    gardé : y **ajouter** un type que le moteur ne lit pas produit un plancher réclamé pour un
    prélèvement que rien n'honorera, soit le « refus abusif le jour J » que la docstring nomme
    elle-même comme l'un des deux pires modes de défaillance.

    Vérifié par mutation en revue : élargir la table laissait **99 tests verts**. Ce test-ci passe
    à 34 si on l'élargit, et c'est tout son objet.

    ⚠️ **Le cas portait sur les poules jusqu'à E05US023**, qui les a rendues lisibles — la garde
    vise donc désormais le **système suisse**, non lu et sans service. Le déplacement n'affaiblit
    rien : ce qui est testé est le mécanisme (un type non lisible ne fixe pas de plancher), pas
    l'identité du type. `test_un_type_que_le_moteur_deroule_reclame_ses_34_inscrits` couvre le sens
    opposé pour les poules.
    """
    etapes = [
        _qualification(1),
        ModelePhase(ordre=2, type=TypePhase.SUISSE),
        _tableau(3, SourcePhase.par_rangs(ordre_source=2, rang_debut=33, rang_fin=None)),
    ]

    assert effectif_minimum(etapes) == 2
