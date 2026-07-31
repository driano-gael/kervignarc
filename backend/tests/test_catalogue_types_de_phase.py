"""Test de recette du **catalogue de types de phase** (E05US015).

**Dérivé du CA** (règle 9), et du plus englobant d'entre eux : « **Vérifier que le catalogue livré
couvre bien la séquence d'exemple d'EF-3.1** : qualification → barrage → tableau principal →
repêchage → tournoi des perdants → tableaux de placement → finale → Big Shoot Off → podium ».

C'est le seul test de l'US qui ne regarde **aucun** moteur en particulier : il vérifie que les
briques livrées **s'assemblent** en le déroulé que le cahier des charges cite en exemple. Un
catalogue dont chaque pièce marche isolément mais qui ne sait pas composer la séquence de référence
n'aurait pas rempli son objet.

Trois points que ce fichier fige au passage, parce qu'ils sont la **thèse** de l'US :

- la **finale** n'est pas un type — c'est une élimination directe à 2 participants alimentée par
  « les gagnants des demies », ce que les sources multiples d'E05US010 rendent exprimable ;
- le **repêchage** n'est pas un type non plus — c'est une phase alimentée par un prélèvement
  `issue_de_tour/perdants`, plus une politique `routing` sur la phase amont ;
- le **podium** n'est pas une phase du tout : c'est la **sortie** de la phase terminale.
"""

from __future__ import annotations

from domain.bareme import BaremeQualification
from domain.duel import BaremeDuel, ModeDuel
from domain.grain_validation import GrainValidation
from domain.phase import (
    IssueTour,
    Phase,
    SequencePhases,
    SourcePhase,
    TypePhase,
)
from domain.politiques import (
    AucunClassement,
    RoutingRepechage,
    ScoreAvecHandicap,
    TiebreakPoules,
    assembler_politiques,
    registre_par_defaut,
)

TOURNOI = 1


def _sequence_ef31() -> SequencePhases:
    """La séquence d'exemple d'EF-3.1, composée avec les briques livrées.

    Aucun effectif n'est déclaré sur les phases à prélèvement relatif : c'est ce que les plages
    relatives d'E05US010 permettent, et ce qui rend le déroulé indépendant de l'effectif réel.
    """
    return SequencePhases(
        (
            # 1 — qualification : le classement de départ.
            Phase(
                tournoi_id=TOURNOI,
                ordre=1,
                type=TypePhase.QUALIFICATION,
                bareme=BaremeQualification(nb_volees=5, nb_fleches_par_volee=3),
                validation=GrainValidation.fin_de_serie(),
            ),
            # 2 — barrage : départage les ex æquo **avant** de monter le tableau (§8.2).
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=2,
                type=TypePhase.BARRAGE,
                sources=(SourcePhase.par_rangs(1, rang_debut=1, rang_fin=32),),
            ),
            # 3 — tableau principal : les 32 rescapés du barrage.
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=3,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_rangs(2, rang_debut=1, rang_fin=32),),
            ),
            # 4 — repêchage : les perdants du 1ᵉʳ tour du tableau principal reviennent.
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=4,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_issue_de_tour(3, tour=1, issue=IssueTour.PERDANTS),),
            ),
            # 5 — tournoi des perdants : les battus du 2ᵉ tour, qui ne reviennent pas, eux.
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=5,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_issue_de_tour(3, tour=2, issue=IssueTour.PERDANTS),),
            ),
            # 6 — tableaux de placement : tout le reste se classe.
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=6,
                type=TypePhase.PLACEMENT,
                sources=(SourcePhase.le_reste(3),),
            ),
            # 7 — finale : **pas un type**, une élimination directe à 2 alimentée par les gagnants
            # des demies (tour 4 d'un tableau de 32). Elle ne devient une phase distincte que pour
            # lui donner un barème propre — ce que les sources multiples rendent exprimable.
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=7,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_issue_de_tour(3, tour=4, issue=IssueTour.GAGNANTS),),
                effectif=2,
            ),
            # 8 — Big Shoot Off : la grande finale spectacle, alimentée par **deux** sources — les
            # finalistes et le repêché. C'est le cas réel du classeur (`Tableaux.xlsx`).
            Phase.creer(
                tournoi_id=TOURNOI,
                ordre=8,
                type=TypePhase.BIG_SHOOT_OFF,
                sources=(
                    SourcePhase.par_rangs(7, rang_debut=1, rang_fin=2),
                    SourcePhase.par_rangs(4, rang_debut=1, rang_fin=1),
                ),
            ),
        )
    )


def test_la_sequence_d_exemple_du_cahier_des_charges_est_composable() -> None:
    """Le CA de l'US, mot pour mot : le catalogue couvre-t-il EF-3.1 ?

    `SequencePhases` **rejette** à la construction toute séquence incohérente (ordres non contigus,
    source postérieure, prélèvement impossible) : que celle-ci se construise *est* l'assertion.
    """
    sequence = _sequence_ef31()
    assert [phase.type for phase in sequence.phases] == [
        TypePhase.QUALIFICATION,
        TypePhase.BARRAGE,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.PLACEMENT,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.BIG_SHOOT_OFF,
    ]


def test_le_podium_n_est_pas_une_phase() -> None:
    """Dernier terme de la séquence EF-3.1, et le seul qui ne se compose pas : le podium est la
    **sortie** de la phase terminale (les rangs qu'elle produit), pas une étape de plus.

    La preuve par le catalogue : aucun `TypePhase` ne s'appelle « podium », et c'est délibéré.
    """
    assert "podium" not in {type_phase.value for type_phase in TypePhase}


def test_la_finale_spectacle_s_obtient_par_configuration() -> None:
    """CA « trois types obtenus par configuration, sans code », et règle du commanditaire :
    « en arc classique les duels se jouent au système de sets (premier à 6) ; en arc à poulies au
    score cumulé sur 15 flèches ; en cas d'égalité un tir de barrage départage ».

    Les deux barèmes **existaient déjà** (E04US013). La finale spectacle est donc un tableau à 8
    plus un barème, pas un moteur : sa part réellement neuve — musique, écran géant, commentateur,
    compte à rebours — est de la **mise en scène**, donc de l'écran de salle (E07US004).
    """
    classique = BaremeDuel.preset_ffta_classique()
    poulies = BaremeDuel.preset_ffta_poulies()
    assert (classique.mode, classique.points_pour_gagner) == (ModeDuel.SETS, 6)
    assert poulies.mode is ModeDuel.CUMUL
    # « Score cumulé sur 15 flèches » de la règle = 5 volées de 3.
    assert poulies.nb_manches * poulies.nb_fleches_par_volee == 15


def test_chaque_type_neuf_a_un_jeu_de_politiques_resoluble() -> None:
    """ADR-0045 §2 : on n'offre pas un type qu'aucun moteur ne sait dérouler.

    Le pendant côté configuration : les politiques que ces types réclament doivent se **résoudre**
    depuis une `config.policies`. Un nom absent du registre lèverait `PolitiqueInconnue` au premier
    chargement de la phase — c'est-à-dire le jour J.
    """
    registre = registre_par_defaut()
    politiques = assembler_politiques(
        {
            "routing": {"nom": "repechage", "tours": [1]},
            "scoring": {"nom": "handicap"},
            "tiebreak": {"nom": "poules"},
            "depth": {"nom": "aucun"},
        },
        registre,
    )
    assert isinstance(politiques.routing, RoutingRepechage)
    assert isinstance(politiques.scoring, ScoreAvecHandicap)
    assert isinstance(politiques.tiebreak, TiebreakPoules)
    assert isinstance(politiques.depth, AucunClassement)


def test_un_echauffement_s_insere_en_tete_du_deroule() -> None:
    """L'échauffement « occupe du temps et des cibles » : il doit pouvoir précéder la qualification
    sans casser la séquence — et celle-ci reprend « le reste » de ses participants, seule succession
    licite à une phase qui ne classe pas."""
    sequence = SequencePhases(
        (
            Phase.creer(tournoi_id=TOURNOI, ordre=1, type=TypePhase.ECHAUFFEMENT),
            Phase(
                tournoi_id=TOURNOI,
                ordre=2,
                type=TypePhase.QUALIFICATION,
                sources=(SourcePhase.le_reste(1),),
                bareme=BaremeQualification(nb_volees=5, nb_fleches_par_volee=3),
                validation=GrainValidation.fin_de_serie(),
            ),
        )
    )
    assert sequence.phases[0].type is TypePhase.ECHAUFFEMENT
