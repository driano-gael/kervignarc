"""Tests du **canal n°2 des quatre canaux de routage** (E07US008) — repositories factices.

Ces cas dérivent du CA d'E07US008 (`stories/E07-affichage-public.md`), écrits **avant**
l'implémentation (règle 9). Le CA énonce quatre choses, et chacune ouvre sa section :

- « chaque archer concerné voit **sa** prochaine affectation (cible, position, tour) » — déjà tenu
  par `ServiceRoutage.routage` (E04US018) ; ce qui est neuf ici, c'est qu'un **archer parti de la
  salle** n'a personne pour lui demander la liste des quatre archers de sa cible ;
- une **vue « toutes les affectations »** alimente l'écran de salle (E07US004) et la table de
  l'organisation — l'appelant ne connaît **aucun** identifiant, c'est le tableau qui les donne ;
- « l'archer **éliminé** voit son **rang final** » ;
- « l'archer **repêché** voit sa **destination** ».

**Le monde est celui d'E04US018** (`test_service_routage._Monde`) : mêmes services composés sur des
repositories en mémoire, classement **vrai** sur des séries semées. On le réemploie plutôt que de
le recopier — c'est le même service qu'on interroge, sous un autre angle.
"""

from __future__ import annotations

from application.routage import (
    REPECHAGE_SANS_DESTINATION,
    IssueRoutage,
    RoutageArcher,
    ServiceRoutage,
)
from domain.bareme import BaremeQualification
from domain.forfait import Forfait, NatureForfait
from domain.grain_validation import GrainValidation
from domain.phase import IssueTour, Phase, SourcePhase, TypePhase
from domain.politiques import PlacementEnCascade, RoutingRepechage
from tests.test_service_routage import _QUAND, _huit, _Monde, _quatre

# --- CA « une vue "toutes les affectations" » ---------------------------------------------------


def test_la_vue_collective_ne_demande_aucun_identifiant() -> None:
    """CA : « une vue *toutes les affectations* alimente l'écran de salle et la table de
    l'organisation ».

    C'est **la** différence avec le panneau de la tablette (E04US018), et elle n'est pas
    cosmétique :
    la tablette sait qui sont ses quatre archers, l'écran de salle ne sait rien du tout. Une méthode
    qui exigerait la liste des identifiants obligerait chaque surface à la reconstituer d'abord —
    donc à connaître le tableau, ce qui est précisément le travail du service.
    """
    monde = _Monde()
    archers = _huit(monde)
    monde.placer()

    affectations = monde.routage.affectations(monde.tournoi_id)

    assert affectations.phase_id == monde.phase_id
    assert sorted(ligne.archer_id for ligne in affectations.archers) == sorted(archers)


def test_la_vue_collective_ordonne_par_cible_puis_position() -> None:
    """L'écran de salle n'a **aucune interaction** (CA E07US004) : il ne peut pas trier, donc
    l'ordre rendu par le serveur est le seul qu'il aura.

    L'ordre du **pas de tir** (cible croissante, puis position A→D) est celui qui se lit de loin :
    c'est la disposition physique de la salle. Un ordre par identifiant d'archer — celui qui sort
    naturellement d'une boucle sur le tableau — n'aurait aucun sens pour quelqu'un qui cherche sa
    butte, et l'écran ne pourrait rien y faire.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()

    affectations = monde.routage.affectations(monde.tournoi_id)

    poses = [
        (ligne.prochain.cible, ligne.prochain.position)
        for ligne in affectations.archers
        if ligne.prochain is not None and ligne.prochain.cible is not None
    ]
    assert poses == sorted(poses)
    assert len(poses) == 8  # tout le monde est posé au tour 1


def test_la_vue_collective_range_a_la_fin_ceux_qui_n_ont_plus_de_pose() -> None:
    """Un archer sorti n'a pas de butte : il ne peut pas s'intercaler dans le pas de tir.

    Le mettre en tête ou au milieu ferait sauter une ligne à qui parcourt les cibles dans l'ordre.
    Ils sont donc rejetés **après** les posés — et entre eux, triés par nom, seul ordre stable dont
    on dispose alors.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()
    monde.gagner(1)  # un quart tranché : son perdant n'a plus de duel

    affectations = monde.routage.affectations(monde.tournoi_id)

    a_une_pose = [
        ligne.prochain is not None and ligne.prochain.cible is not None
        for ligne in affectations.archers
    ]
    assert a_une_pose == sorted(a_une_pose, reverse=True)  # les posés d'abord, sans entrelacement


def test_la_vue_collective_ignore_un_archer_hors_tableau() -> None:
    """Un inscrit **non retenu** pour le tableau n'a pas d'affectation à afficher.

    Contraste voulu avec `routage()` : là, on a *demandé* cet archer, donc on lui doit une ligne
    motivée (« non retenu pour le tableau ») — taire quelqu'un qu'on nous a nommé serait une panne
    apparente. Ici personne ne l'a nommé : l'inscrire au panneau du pas de tir ferait chercher une
    butte à quelqu'un qui n'en a pas.

    Le geste qui sort vraiment quelqu'un du tableau, c'est la **disqualification** (elle le sort du
    classement, ADR-0050) — pas un inscrit de plus, qui ne ferait qu'élargir le tableau au palier
    suivant et l'y placer avec un bye.
    """
    monde = _Monde()
    archers = _huit(monde)
    monde.placer()
    qualif = monde.phases.ajouter(
        Phase.qualification(
            monde.tournoi_id,
            BaremeQualification.creer(1, 2),
            GrainValidation.fin_de_serie(),
        )
    )
    assert qualif.id is not None
    monde.forfaits.semer(
        Forfait.creer(
            monde.tournoi_id,
            archers[0],
            qualif.id,
            NatureForfait.DISQUALIFICATION,
            "DURAND",
            _QUAND,
        )
    )

    affectations = monde.routage.affectations(monde.tournoi_id)

    assert archers[0] not in [ligne.archer_id for ligne in affectations.archers]


def test_la_vue_collective_sans_phase_de_tableau_le_dit() -> None:
    """Pas de phase finale configurée ⇒ `phase_id` à `None` et **aucune** ligne.

    C'est la distinction que l'écran doit pouvoir faire : « il n'y a pas encore de tableau » n'est
    pas « le tableau est vide ». Sans le `phase_id` à `None`, les deux rendraient la même liste
    vide, et l'écran afficherait un pas de tir désert au lieu de dire qu'on n'en est pas là.
    """
    monde = _Monde()
    monde.inscrire_classe(("10", "10"))  # inscrit, mais aucune phase d'élimination

    affectations = monde.routage.affectations(monde.tournoi_id)

    assert affectations.phase_id is None
    assert affectations.archers == ()


def test_la_vue_collective_dit_la_meme_chose_que_le_panneau_de_la_tablette() -> None:
    """Les quatre canaux de routage lisent la **même** projection (docstring de `routage.py`).

    Si la vue collective recalculait sa propre version, la tablette et l'écran de salle pourraient
    annoncer deux buttes différentes pour le même duel — le genre d'écart qu'on ne découvre qu'à
    18 h, quand deux archers se présentent au même endroit.
    """
    monde = _Monde()
    archers = _huit(monde)
    monde.placer()

    collectif = {
        ligne.archer_id: ligne for ligne in monde.routage.affectations(monde.tournoi_id).archers
    }
    individuel = monde.routage.routage(monde.tournoi_id, tuple(archers))

    for ligne in individuel.archers:
        assert collectif[ligne.archer_id] == ligne


# --- CA « l'archer éliminé voit son rang final » ------------------------------------------------


def test_l_elimine_hors_podium_voit_sa_fourchette_de_rangs() -> None:
    """CA : « l'archer **éliminé** voit son **rang final** ».

    Dans un tableau tronqué au podium, le battu d'un quart n'a **pas** de rang exact : aucun match
    n'a été joué pour départager les quatre battus des quarts, donc ils sont 5ᵉ-8ᵉ ex æquo. On rend
    la **fourchette**, qui est l'information complète et vraie, plutôt que « rang publié en fin de
    phase » — qui n'apprenait rien à quelqu'un qui vient précisément de perdre.

    La fourchette n'est pas une règle nouvelle : c'est la **moitié basse** de la plage du match
    perdu (*Règle R*, `Plage.moitie_basse`), déjà portée par le domaine.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()
    monde.gagner(1)
    battu = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, battu)

    assert ligne.issue is IssueRoutage.TERMINE
    assert (ligne.rang_min, ligne.rang_max) == (5, 8)
    assert ligne.motif is None  # plus d'« en attente » : le rang acquis est connu


def test_la_fourchette_ne_depasse_jamais_l_effectif_reel() -> None:
    """**La borne haute est écrêtée à l'effectif** — correctif de revue (axes C1 et adversarial).

    Une plage est bornée par la **taille** du tableau, une puissance de 2, pas par le nombre
    d'archers. À 6 archers le tableau fait 8 : la moitié basse du tour 1 est `[5..8]`, alors que les
    rangs 7 et 8 **n'existent pas**. Sur l'oracle 120 (taille 128) le même défaut annonçait
    « 65ᵉ-128ᵉ » dans un tournoi de 120 — sur le CA central de l'US, affiché en public.

    Le défaut était invisible parce que `_quatre` et `_huit` sont les deux **seuls** effectifs du
    décor où `taille == effectif`. D'où ce cas à 6, qui casse cette coïncidence : sans lui, le
    correctif ne serait gardé par rien.
    """
    monde = _Monde()
    totaux = (("10", "10"), ("10", "9"), ("9", "9"), ("9", "8"), ("8", "8"), ("8", "7"))
    archers = [monde.inscrire_classe(v) for v in totaux]
    monde.creer_phase_tableau()
    monde.placer()
    tableau, _ = monde.saisie.reconstruire(monde.tournoi_id, monde.phase_id or 0)
    assert (tableau.effectif, tableau.taille) == (6, 8)  # la coïncidence est bien rompue
    duel = next(m for m in tableau.matchs if m.tour == 1 and m.est_jouable)
    monde.gagner(duel.numero)
    battu = monde.perd_de(duel.numero)

    ligne = _ligne(monde.routage, monde.tournoi_id, battu)

    # L'issue est assertée explicitement (remarque de revue) : tout le test **dépend** du fait que
    # ce battu n'a plus de match aval. Sans elle, un changement de profondeur le ferait échouer sur
    # `(5, 6) != (None, None)` — un message qui ne désigne pas la cause.
    assert ligne.issue is IssueRoutage.TERMINE
    assert ligne.rang_max == 6, "le rang annoncé ne peut pas dépasser le nombre d'archers"
    assert (ligne.rang_min, ligne.rang_max) == (5, 6)
    assert battu in archers


def test_la_vue_collective_distingue_un_tableau_non_constitue_d_une_phase_absente() -> None:
    """Phase configurée **mais tableau inconstituable** ⇒ `phase_id` **non nul** et liste vide.

    Cas de la matinée : la séquence de phases est composée d'avance (E05US001) alors que la
    qualification n'est pas encore scorée — moins de deux archers en lice, donc pas d'arbre.

    ⚠️ **Branche sans aucun test avant la revue (axe B)**, et le front en tirait une conclusion
    fausse : `phase_id` non nul + zéro ligne lui faisait afficher « Non retenu pour le tableau
    final » à *tous* les archers suivis. Les deux états sont bel et bien distincts — c'est ce que ce
    test fige — et c'est au front de les distinguer, ce qu'il fait désormais.
    """
    monde = _Monde()
    monde.inscrire_classe(("10", "10"))  # un seul archer : pas d'arbre possible
    phase_id = monde.creer_phase_tableau()

    affectations = monde.routage.affectations(monde.tournoi_id)

    assert affectations.phase_id == phase_id  # ...la phase existe (≠ « pas encore de tableau »)
    assert affectations.archers == ()


def test_le_perdant_d_un_match_terminal_voit_un_rang_exact() -> None:
    """Quand le match perdu **décerne** les rangs (`place_en_jeu`), la fourchette se referme.

    C'est le même calcul, pas un cas particulier : la plage d'une finale est `[1..2]`, sa moitié
    basse `[2..2]`. Le rang exact du podium et la fourchette hors podium sont la **même** notion vue
    à deux profondeurs, ce qui est exactement ce qu'il fallait obtenir — deux calculs séparés
    auraient fini par se contredire.
    """
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    monde.gagner(1)
    monde.gagner(2)
    monde.gagner(3)  # la finale
    battu = monde.perd_de(3)

    ligne = _ligne(monde.routage, monde.tournoi_id, battu)

    assert ligne.issue is IssueRoutage.TERMINE
    assert (ligne.rang_min, ligne.rang_max) == (2, 2)
    assert ligne.rang_final == 2  # le podium reste la source du rang exact


def test_le_vainqueur_garde_son_rang_de_podium() -> None:
    """Non-régression : le champion est 1ᵉʳ, pas « 1ᵉʳ-2ᵉ ».

    Il n'a perdu aucun match, donc il n'y a pas de plage de battu à lire pour lui — son rang vient
    du podium, comme avant.
    """
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    monde.gagner(1)
    monde.gagner(2)
    monde.gagner(3)
    champion = monde.gagne_de(3)

    ligne = _ligne(monde.routage, monde.tournoi_id, champion)

    assert ligne.rang_final == 1
    assert (ligne.rang_min, ligne.rang_max) == (1, 1)


def test_l_archer_encore_en_lice_n_a_pas_de_rang() -> None:
    """Un rang annoncé à quelqu'un qui a encore un duel devant lui serait un faux départ.

    Le garde-fou compte : la fourchette se calcule sur « le match que j'ai perdu », et un archer
    qui n'a rien perdu n'en a pas. La confusion serait invisible en lecture de code.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()

    ligne = _ligne(monde.routage, monde.tournoi_id, monde.gagne_de(1))

    assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
    assert (ligne.rang_min, ligne.rang_max) == (None, None)


# --- CA « l'archer repêché voit sa destination » ------------------------------------------------


def test_le_repeche_n_est_pas_annonce_elimine() -> None:
    """CA : « l'archer **repêché** voit sa destination ».

    C'est le vrai trou fonctionnel du canal : `VersRepechage` ne consomme **aucun rang**
    (`domain/politiques.py`), donc le battu sort du tableau sans y être classé — et un service qui
    ne regarde qu'une phase le voyait « terminé ». Annoncer « éliminé » à quelqu'un qui est repêché,
    c'est le faire rentrer chez lui avant son duel.
    """
    monde = _MondeRepechage()
    _huit(monde)
    monde.declarer_phase_de_repechage()
    monde.placer()
    monde.gagner(1)
    repeche = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, repeche)

    assert ligne.issue is IssueRoutage.REPECHE
    assert ligne.rang_final is None  # un repêché n'a pas de rang : il peut encore remonter
    assert (ligne.rang_min, ligne.rang_max) == (None, None)


def test_le_repeche_voit_la_phase_qui_le_reprend() -> None:
    """« Sa destination » = la phase avale qui le **prélève**, nommée.

    La réintégration n'est pas un lien d'arbre mais un prélèvement `issue_de_tour/perdants` de la
    phase suivante (`VersRepechage`, ADR-0062) : la destination se lit donc dans les **sources** de
    la séquence, pas dans le tableau. C'est la seule lecture qui la connaisse.
    """
    monde = _MondeRepechage()
    _huit(monde)
    repechage_id = monde.declarer_phase_de_repechage()
    monde.placer()
    monde.gagner(1)
    repeche = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, repeche)

    assert ligne.destination is not None
    assert ligne.destination.phase_id == repechage_id
    assert ligne.destination.ordre == 3
    assert ligne.destination.type == TypePhase.ELIMINATION_DIRECTE.value


def test_le_repeche_sans_phase_avale_le_dit_au_lieu_de_se_taire() -> None:
    """Le moteur prévient : si la composition **oublie** la phase de repêchage, les battus
    disparaissent sans que rien ne le signale (commentaire de `construire_tableau`).

    Le routage est le premier endroit où ce trou devient **visible par un humain** : l'archer
    demande où il tire, et personne ne peut répondre. On le dit — un panneau muet passerait pour
    une panne réseau, et l'organisateur ne saurait pas que son déroulé est incomplet.
    """
    monde = _MondeRepechage()
    _huit(monde)
    monde.placer()  # aucune phase de repêchage déclarée
    monde.gagner(1)
    repeche = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, repeche)

    assert ligne.issue is IssueRoutage.REPECHE
    assert ligne.destination is None
    assert ligne.motif == REPECHAGE_SANS_DESTINATION


def test_le_battu_d_un_tour_non_repeche_reste_elimine() -> None:
    """Le repêchage n'excepte que **certains tours** (`RoutingRepechage.tours_repeches`).

    Sans ce cas, une implémentation qui déclarerait « repêché » tout battu d'un tableau à repêchage
    passerait les tests précédents et serait fausse pour les autres tours.

    ⚠️ **Réécrit sur remarque de revue (axe B), preuve par mutation à l'appui.** La version d'origine
    faisait jouer les quarts puis une demie et interrogeait le battu de la demie — qui a encore la
    **petite finale** devant lui, donc `PROCHAIN_DUEL` : elle n'atteignait jamais `_est_repeche` et
    survivait au mutant `_est_repeche → True`. On repêche donc ici le **tour 2**, et l'on interroge
    un battu du **tour 1**, qui n'a bien plus aucun duel : lui seul traverse la garde.
    """
    monde = _MondeRepechage(tours_repeches=frozenset({2}))
    _huit(monde)
    monde.declarer_phase_de_repechage(tour=2)
    monde.placer()
    monde.gagner(1)
    battu_du_tour_1 = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, battu_du_tour_1)

    assert ligne.issue is IssueRoutage.TERMINE  # son tour n'est pas repêché
    assert (ligne.rang_min, ligne.rang_max) == (5, 8)


def test_le_battu_repris_par_la_sequence_n_est_pas_encore_annonce() -> None:
    """**Caractérisation de `# DETTE-033`** : la reprise par la *séquence* n'est pas annoncée.

    Un premier correctif de revue posait la `destination` sur les lignes `TERMINE` aussi. Deux
    relecteurs l'ont démoli de deux façons opposées — `dernier` est le dernier match **joué** et non
    le match perdu (le battu des demies redescend en petite finale, on rate donc « perdants du
    tour 2 ») ; et un tour couvre **plusieurs plages** (finale et petite finale sont toutes deux au
    tour 3, on décorerait le 4ᵉ du podium). Leurs correctifs étaient **incompatibles**, ce qui est
    le signal : la sémantique de `par_issue_de_tour` n'est pas tranchée, et `# DETTE-028` acte
    qu'aucun moteur ne la consomme. On ne la devine pas dans un canal d'affichage.

    Ce test **fige la lacune** plutôt que de la laisser muette : le jour où l'US du prélèvement
    tranchera, il échouera — et c'est exactement ce qu'on lui demande.
    """
    monde = _Monde()  # routing de production : cascade, aucun repêchage
    _huit(monde)
    monde.phases.ajouter(
        Phase.creer(
            monde.tournoi_id,
            3,
            TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase.par_issue_de_tour(2, tour=1, issue=IssueTour.PERDANTS),),
        )
    )
    monde.placer()
    monde.gagner(1)
    battu = monde.perd_de(1)

    ligne = _ligne(monde.routage, monde.tournoi_id, battu)

    assert ligne.issue is IssueRoutage.TERMINE
    assert (ligne.rang_min, ligne.rang_max) == (5, 8)  # le rang acquis, lui, est bien annoncé
    assert ligne.destination is None, "cf. DETTE-033 — à lever quand le prélèvement aura un moteur"


# --- décor du repêchage --------------------------------------------------------------------------


class _MondeRepechage(_Monde):
    """Le même décor, avec un **repêchage World Archery** sur le 1ᵉʳ tour.

    Seul le `routing` change : c'est une **politique injectable** (règle 2 du projet), donc changer
    de format est une affaire de câblage, pas de code — le décor d'E04US018 se réemploie tel quel.
    Le tableau construit n'engendre alors aucun sous-tableau pour la moitié basse du tour 1 : ses
    battus en **sortent**, et c'est tout le sujet de cette section.
    """

    def __init__(self, tours_repeches: frozenset[int] = frozenset({1})) -> None:
        super().__init__(
            routing=RoutingRepechage(tours_repeches=tours_repeches, sinon=PlacementEnCascade())
        )

    def declarer_phase_de_repechage(self, tour: int = 1) -> int:
        """La phase avale qui **prélève les perdants du tour** donné de la phase de tableau."""
        phase = self.phases.ajouter(
            Phase.creer(
                self.tournoi_id,
                3,
                TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_issue_de_tour(2, tour=tour, issue=IssueTour.PERDANTS),),
            )
        )
        assert phase.id is not None
        return phase.id


def _ligne(routage: ServiceRoutage, tournoi_id: int, archer_id: int) -> RoutageArcher:
    """La ligne d'un archer dans la **vue collective** — c'est elle que cette US livre."""
    lignes = [
        ligne for ligne in routage.affectations(tournoi_id).archers if ligne.archer_id == archer_id
    ]
    assert len(lignes) == 1, f"L'archer {archer_id} devrait avoir exactement une ligne."
    return lignes[0]
