"""La **cascade de poules** — une phase de niveau nourrie par une phase de poules (E05US029).

⚠️ **Ces tests sont écrits depuis le CA, avant l'implémentation du chaînage** (règle 9). L'oracle
est le format décrit verbatim par le commanditaire au cadrage d'`E05US026`, le 15/08/2026 :

> 36 archers. **Phase 1** : 6 poules de 6, disputant les rangs 1-36. **Phase 2** : 6 poules de 6,
> mais composées **par niveau** — les rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36. Le classement de
> la phase 2 est alors le **classement final** du tournoi, exact de 1 à 36. Variante : 3 qualifiés
> par poule, plusieurs phases enchaînées, et le palmarès se resserre de cran en cran.

complété de l'arbitrage du cadrage du 21/08/2026, qui a fait entrer **la variante à resserrement**
dans le périmètre : il ne suffit pas que le mode existe, il faut que la cascade tienne de bout en
bout — prélèvement, composition, classement de phase, espace de rangs.

**L'échelle est réduite, la propriété non.** Le format du commanditaire (36 archers, 90 rencontres
par phase) ne prouverait rien de plus que 8 ou 16 archers : ce qui est éprouvé ici est la
**chaîne** — le classement de la phase 1 arrive-t-il en ordre dans la phase 2, la tranche de rangs
est-elle la bonne, le décalage est-il posé — et aucun de ces maillons ne dépend de l'effectif. On
paie en revanche 24 rencontres jouées pour de vrai plutôt qu'un décor simulé, parce que c'est
justement le passage par le vrai classement qu'on veut éprouver.

⚠️ **Ce que ces tests ne couvrent pas** : le palmarès lui-même (`application/palmares.py`), qui
consomme le `ResultatPhase` produit ici par le **même** `rang_premier`. La chaîne est vérifiée
jusqu'à ce résultat inclus ; l'assemblage du palmarès a ses propres tests.
"""

from __future__ import annotations

from application.poules import ServicePoules
from domain.blason import ZoneScore
from domain.phase import Phase, SourcePhase, TypePhase
from domain.poule import ModeDeComposition, ReglageDePoules
from tests.test_service_poules import _Monde


def _service_en_cascade(monde: _Monde) -> ServicePoules:
    """Le service de poules, **avec son lecteur de classement branché** (ADR-0084).

    ⚠️ Sans ce branchement, un prélèvement visant une phase de poules est **inerte** : le résolveur
    ne sait pas lire le classement de ce type, et la phase avale reçoit tous les archers en lice au
    lieu de la tranche demandée. C'est le défaut exact qu'E05US026 a fermé, et c'est ce que fait le
    composition root (`bootstrap/composition.py`, « le port casse le cycle de construction »). Le
    décor de test doit donc le refaire, sans quoi la cascade se testerait sur une chaîne débranchée
    — et passerait pour de mauvaises raisons.
    """
    service = monde.service()
    service._saisie_duels.brancher_lecteur(TypePhase.POULES, service)
    return service


def _phase_avale(
    monde: _Monde,
    *,
    rang_debut: int,
    rang_fin: int,
    taille_visee: int,
    mode: ModeDeComposition = ModeDeComposition.PAR_NIVEAU,
) -> int:
    """Pose la phase 2 : des poules qui prélèvent une tranche du classement de la phase 1.

    `SourcePhase.par_rangs` désigne la phase source par son **ordre** dans le déroulé (2, celle que
    `_Monde.regler` pose), pas par son identifiant — c'est le prélèvement d'ADR-0068/ADR-0080.
    """
    phase = monde.phases.ajouter(
        Phase(
            depart_id=monde.depart_id,
            ordre=3,
            type=TypePhase.POULES,
            poules=ReglageDePoules(taille_visee=taille_visee, mode=mode),
            sources=(SourcePhase.par_rangs(2, rang_debut, rang_fin),),
        )
    )
    assert phase.id is not None
    return phase.id


def _jouer_selon_le_rang(service: ServicePoules, monde: _Monde, phase_id: int) -> None:
    """Fait gagner **le mieux classé** de chaque rencontre, puis valide.

    Les archers sont créés par scores décroissants (`_Monde.inscrire`), donc le plus petit
    `archer_id` est le mieux classé. Le classement de chaque poule est alors l'ordre scratch de ses
    membres — ce qui rend le classement de la phase 1 prévisible sans le recopier depuis le code
    qui le calcule.
    """
    for poule in service.etat(monde.tournoi_id, phase_id).poules:
        for rencontre in poule.rencontres:
            assert rencontre.haut is not None and rencontre.bas is not None
            gagne_en_haut = rencontre.haut.archer_id < rencontre.bas.archer_id
            haut = ("10", "10", "10") if gagne_en_haut else ("6", "6", "6")
            bas = ("6", "6", "6") if gagne_en_haut else ("10", "10", "10")
            for manche in (1, 2, 3):
                service.saisir_manche(
                    monde.tournoi_id,
                    phase_id,
                    rencontre.numero,
                    manche,
                    tuple(ZoneScore(v) for v in haut),
                    tuple(ZoneScore(v) for v in bas),
                )
            service.valider(monde.tournoi_id, phase_id, rencontre.numero, "DURAND")


def _membres(service: ServicePoules, monde: _Monde, phase_id: int) -> list[list[int]]:
    """Les archers de chaque groupe d'une phase, dans l'ordre des groupes.

    `PouleAffichee.membres` porte des `Duelliste` — l'archer **résolu** pour l'affichage — et non
    des `Participant` : c'est l'écran de saisie que ce service sert d'abord.
    """
    return [
        [membre.archer_id for membre in poule.membres]
        for poule in service.etat(monde.tournoi_id, phase_id).poules
    ]


def _classement_de_phase(service: ServicePoules, monde: _Monde, phase_id: int) -> list[int]:
    """Le classement que la phase **produit**, dans l'ordre des rangs.

    Le résolveur est celui que le service ouvre lui-même quand l'appel vient d'en haut : on le lui
    demande plutôt que d'en fabriquer un second, qui résoudrait la même chaîne dans un autre cache
    et pourrait situer la population dans un autre espace de rangs (`DETTE-034`).
    """
    resolveur = service._saisie_duels.resolveur_de_classement(monde.tournoi_id, monde.depart_id)
    source = service.classement_de_phase(monde.tournoi_id, phase_id, resolveur)
    return [ligne.archer_id for ligne in source.classement.lignes]


def test_une_phase_de_niveau_reprend_le_classement_de_la_phase_amont_dans_l_ordre() -> None:
    """Le cœur de la cascade : la poule A de la phase 2 réunit **les premiers** de la phase 1.

    8 archers, 2 poules de 4 au serpent → le classement de phase 1 les range par rang de poule
    d'abord (les deux vainqueurs, puis les deux deuxièmes…). La phase 2 prélève ce classement
    entier et le découpe par niveau : sa poule A doit donc porter les rangs 1 à 4 **de ce
    classement-là**, et non les quatre plus petits identifiants ni l'ordre d'inscription.
    """
    monde = _Monde(nb_cibles=16)
    archers = monde.inscrire(8)
    phase_1 = monde.regler(ReglageDePoules(taille_visee=4))
    service = _service_en_cascade(monde)
    _jouer_selon_le_rang(service, monde, phase_1)

    ordre_phase_1 = _classement_de_phase(service, monde, phase_1)
    phase_2 = _phase_avale(monde, rang_debut=1, rang_fin=8, taille_visee=4)

    assert _membres(service, monde, phase_2) == [ordre_phase_1[:4], ordre_phase_1[4:]]
    # Et ce classement n'est pas l'ordre d'inscription : le serpent l'a bien rebattu en phase 1.
    assert ordre_phase_1 != archers


def test_le_vainqueur_du_groupe_du_bas_garde_son_rang_dans_la_phase_de_niveau() -> None:
    """Le CA « chaque groupe dispute son propre espace de rangs », éprouvé **par le service**.

    Le test de domaine le prouve sur des classements fabriqués ; ici la chaîne entière est en jeu —
    prélèvement, composition, classement de poule, classement de phase. Le premier du groupe des
    rangs 5-8 doit ressortir **5ᵉ** de la phase 2, jamais 1ᵉʳ.
    """
    monde = _Monde(nb_cibles=16)
    monde.inscrire(8)
    phase_1 = monde.regler(ReglageDePoules(taille_visee=4))
    service = _service_en_cascade(monde)
    _jouer_selon_le_rang(service, monde, phase_1)
    phase_2 = _phase_avale(monde, rang_debut=1, rang_fin=8, taille_visee=4)
    _jouer_selon_le_rang(service, monde, phase_2)

    groupe_du_haut, groupe_du_bas = _membres(service, monde, phase_2)
    classement = _classement_de_phase(service, monde, phase_2)

    assert classement.index(groupe_du_bas[0]) == 4, "le 1ᵉʳ du groupe bas occupe le 5ᵉ rang"
    # ⚠️ On compare des **ensembles** : le groupe occupe la tranche, il ne la remplit pas dans son
    # ordre d'entrée — c'est le tir de la phase 2 qui range ses membres à l'intérieur, et c'est
    # tout l'objet d'une phase de niveau. Comparer les listes reviendrait à exiger que la phase 2
    # ne change rien, donc à tester l'inverse du CA.
    assert set(classement[:4]) == set(groupe_du_haut)
    assert set(classement[4:]) == set(groupe_du_bas)


def test_une_cascade_a_resserrement_ne_reprend_que_les_qualifies() -> None:
    """La variante du commanditaire, entrée au périmètre par le cadrage du 21/08/2026.

    16 archers, 4 poules de 4 en phase 1 ; la phase 2 ne reprend que les **rangs 1 à 8**, découpés
    en deux poules de niveau. Le palmarès se resserre : huit archers continuent, huit s'arrêtent là.

    ⚠️ **Ce prélèvement ne coupe aucun bloc, et c'est ce qui le rend possible sans départage
    inter-poules** (ADR-0081). Sur 4 poules, le classement de phase range les 4 vainqueurs aux
    rangs 1-4 et les 4 deuxièmes aux rangs 5-8 : « les rangs 1 à 8 » prend donc **deux blocs
    entiers**. C'est exactement la propriété qui fait marcher la variante « 3 qualifiés par poule »
    du commanditaire — 3 x 6 poules = 18 = trois blocs pleins — et elle tient parce que le nombre
    de qualifiés est **uniforme**. Un resserrement qui couperait un bloc (« les rangs 1 à 6 » sur 4
    poules) serait refusé et annoncé, ce qui est le comportement voulu et non une limite de cette
    US.
    """
    monde = _Monde(nb_cibles=32)
    monde.inscrire(16)
    phase_1 = monde.regler(ReglageDePoules(taille_visee=4))
    service = _service_en_cascade(monde)
    _jouer_selon_le_rang(service, monde, phase_1)

    ordre_phase_1 = _classement_de_phase(service, monde, phase_1)
    phase_2 = _phase_avale(monde, rang_debut=1, rang_fin=8, taille_visee=4)

    groupes = _membres(service, monde, phase_2)
    assert groupes == [ordre_phase_1[:4], ordre_phase_1[4:8]]
    assert not set(ordre_phase_1[8:]) & {archer for groupe in groupes for archer in groupe}


def test_une_phase_de_niveau_au_serpent_composerait_l_inverse() -> None:
    """Le contre-exemple qui justifie le refus posé au déroulé — **et il n'est pas théorique**.

    Même décor, même prélèvement, seul le mode change. Au serpent, les deux premiers du classement
    de la phase 1 partent dans **deux groupes différents** ; par niveau, ils se retrouvent dans le
    même. C'est cette différence, et elle seule, que l'organisateur croit régler en enchaînant deux
    phases de poules — d'où le garde-fou bloquant de `domain/deroule.py`.
    """
    monde = _Monde(nb_cibles=16)
    monde.inscrire(8)
    phase_1 = monde.regler(ReglageDePoules(taille_visee=4))
    service = _service_en_cascade(monde)
    _jouer_selon_le_rang(service, monde, phase_1)
    ordre_phase_1 = _classement_de_phase(service, monde, phase_1)

    au_serpent = _phase_avale(
        monde, rang_debut=1, rang_fin=8, taille_visee=4, mode=ModeDeComposition.SERPENT
    )
    groupes = _membres(service, monde, au_serpent)

    premier, second = ordre_phase_1[0], ordre_phase_1[1]
    assert premier in groupes[0] and second in groupes[1]
