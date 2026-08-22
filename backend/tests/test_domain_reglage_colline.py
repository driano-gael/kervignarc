"""E05US027 — le réglage d'une phase de **colline**, posé à l'atelier.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US027, puce « réglages à l'atelier ») :
« *nombre de manches et portée du défi (`ConfigurationColline`), avec la portée maximale que
l'effectif autorise affichée en clair* », et du référentiel §10.1 qui pose que la portée **est** ce
qui sépare le King of the Hill (1) du Ladder (2+).

⚠️ **Honnêteté sur l'ordre d'écriture** (règle 9). Ces tests dérivent du CA et de lui seul, mais ils
ont été écrits **après** le réglage — et pire, après la revue : leur absence est le majeur qu'un axe
a relevé. Trois règles métier neuves avaient été livrées sans un seul test unitaire
(`_verifier_portee_de_defi`, le refus d'un réglage porté par un autre type, la traversée
`ModelePhase` ↔ `EtapeDeroule`), alors que le CA jumeau du système suisse a son
`test_domain_reglage_suisse.py` depuis E05US026. La seule couverture existante portait sur le
bornage **à la lecture** (`test_service_colline.py`) — c'est l'autre moitié de la règle : un test
vert sur ce que le service borne ne dit rien de ce que la composition refuse.

**Ce que ces tests ferment.** Le refus d'une portée trop grande existait déjà dans
`defis_de_la_manche`, mais il tombe **au moment d'apparier**, phase déjà lancée : le format y a
perdu son sens et l'organisateur n'a plus de geste de rattrapage. Le porter sur le couple
(réglage, effectif), là où l'effectif est déclaré, c'est le dire à la composition — et c'est ce que
le CA demande en exigeant la borne « affichée en clair ».
"""

from __future__ import annotations

import pytest

from domain.arret_programme import ArretProgramme
from domain.colline import ConfigurationColline, portee_maximale
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import ArretProgrammeInvalide, ConfigurationCollineInvalide
from domain.format_tournoi import ModelePhase
from domain.phase import Phase, StatutPhase, TypePhase

#: Le réglage par défaut du décor — **immuable**, donc partageable entre appels (`frozen`).
_KING_OF_THE_HILL = ConfigurationColline(nb_manches=3, portee_de_defi=1)


def _etape(
    *,
    type: TypePhase = TypePhase.COLLINE,
    colline: ConfigurationColline | None = _KING_OF_THE_HILL,
    effectif: int | None = None,
    arrets: tuple[ArretProgramme, ...] = (),
) -> EtapeDeroule:
    """Une étape de colline, réglée en King of the Hill sur 3 manches sauf mention contraire.

    ⚠️ **Signature nommée, et non `**champs: object` avec un `# type: ignore`** (correctif de 2ᵉ
    passe, trois axes). Le jumeau `test_domain_reglage_suisse.py` emploie le splat, mais le style
    existant n'est pas une justification : ce que l'`ignore` désactivait, c'est la vérification que
    le décor construit une `EtapeDeroule` **valide** — exactement le mécanisme de `DETTE-064`, où
    un décor pose une phase non réglée là où le test croit en poser une réglée, rejoué dans un
    fichier neuf. Le commit qui a créé ce fichier affirmait par ailleurs avoir arbitré « les trois
    `# type: ignore` » : il y en avait quatre, et le quatrième était celui-ci — muet.
    """
    return EtapeDeroule(
        tournoi_id=1, ordre=1, type=type, colline=colline, effectif=effectif, arrets=arrets
    )


def test_le_reglage_se_pose_sur_l_etape_et_descend_dans_chaque_creneau() -> None:
    """CA « réglages à l'atelier » : les deux champs voyagent de l'étape jusqu'à la phase.

    ⚠️ **Porté par l'étape, donc par le tournoi** (ADR-0076) : le choix du format — King of the Hill
    ou Ladder — est une propriété de la *définition*, pas de l'avancement d'un créneau. Deux
    créneaux du même tournoi disputent donc le même format, ce que la question inverse rendrait
    absurde : « la colline du matin est un Ladder, celle de l'après-midi un King of the Hill » n'est
    pas un réglage, c'est deux tournois.
    """
    phase = _etape().instancier(depart_id=7)

    assert phase.colline == ConfigurationColline(nb_manches=3, portee_de_defi=1)
    assert phase.statut is StatutPhase.A_VENIR


def test_une_portee_que_l_effectif_ne_permet_pas_est_refusee_a_la_composition() -> None:
    """CA « la portée maximale que l'effectif autorise » — et le refus tombe **avant** le jour J.

    À 4 archers, un défi porte au plus sur 3 rangs : à 4, le dernier pourrait défier le premier,
    c'est-à-dire « n'importe qui défie n'importe qui ». Ce n'est plus une colline — ni King of the
    Hill, ni Ladder —, c'est un round-robin déguisé, et le classement qu'il produirait n'aurait plus
    la propriété qui fait tout l'intérêt du format (le gagnant monte d'un cran, le perdant descend).
    """
    assert portee_maximale(4) == 3

    _etape(effectif=4, colline=ConfigurationColline(nb_manches=3, portee_de_defi=3))

    with pytest.raises(ConfigurationCollineInvalide, match="au plus sur 3 rang"):
        _etape(effectif=4, colline=ConfigurationColline(nb_manches=3, portee_de_defi=4))


def test_sans_effectif_declare_rien_n_est_refuse() -> None:
    """On ne refuse pas ce qu'on ne peut pas juger — même parti que le suisse.

    L'atelier montre alors la borne atteignable et l'organisateur décide ; le service, lui, **borne
    à la lecture au lieu de lever**, pour qu'un écran s'ouvre toujours. Refuser ici bloquerait la
    composition d'un déroulé dont l'effectif n'est pas encore connu, ce qui est le cas normal.
    """
    etape = _etape(colline=ConfigurationColline(nb_manches=3, portee_de_defi=12))

    assert etape.colline == ConfigurationColline(nb_manches=3, portee_de_defi=12)


def test_le_format_de_bibliotheque_ne_borne_rien() -> None:
    """Un format est réutilisé sur des effectifs qu'il ignore — règle 2, un format est de la config.

    « Portée 5 » est jouable à 12 archers et ne l'est pas à 5. Poser la borne sur `ModelePhase`
    figerait la brique sur un effectif supposé ; elle se juge sur l'**étape**, une fois le tournoi
    connu. Le garde-fou change de porte, il ne disparaît pas.
    """
    modele = ModelePhase(
        ordre=1,
        type=TypePhase.COLLINE,
        colline=ConfigurationColline(nb_manches=4, portee_de_defi=5),
    )

    assert modele.colline == ConfigurationColline(nb_manches=4, portee_de_defi=5)
    with pytest.raises(ConfigurationCollineInvalide):
        ModelePhase(
            ordre=1,
            type=TypePhase.COLLINE,
            effectif=4,
            colline=ConfigurationColline(nb_manches=4, portee_de_defi=5),
        ).pour_tournoi(tournoi_id=1)


def test_un_reglage_de_colline_sur_un_autre_type_est_refuse_des_l_etape() -> None:
    """Un réglage que rien ne lit est invisible et faux — et le refus doit être **précoce**.

    Le cas visé est le **retypage** : on compose une phase en colline, on la repasse en élimination
    directe, et le nombre de manches reste accroché à un type qui ne le lira jamais.

    ⚠️ **Le refus existait, un cran trop tard** (relevé par l'axe adversarial, reproduit par
    exécution). Il ne vivait que sur `Phase`, donc à `instancier()` — après que l'étape a rejoint le
    déroulé. Une requête *invalide* laissait derrière elle une étape sans instance de phase,
    occupant
    un rang que l'ajout suivant ne réutilise pas : le déroulé se retrouvait troué par une entrée
    refusée. D'où la double garde ci-dessous — l'étape **et** la phase.
    """
    with pytest.raises(ConfigurationCollineInvalide, match="type « colline »"):
        _etape(type=TypePhase.ELIMINATION_DIRECTE)

    # Et la garde d'aval reste, elle : `replace()` sur une phase ne repasse pas par l'étape.
    with pytest.raises(ConfigurationCollineInvalide):
        Phase(
            depart_id=1,
            ordre=1,
            type=TypePhase.ELIMINATION_DIRECTE,
            colline=ConfigurationColline(nb_manches=3, portee_de_defi=1),
        )


def test_les_bornes_basses_sont_refusees_par_le_reglage_lui_meme() -> None:
    """Ce qui est vrai du réglage **seul** reste sur le réglage ; le couple monte à l'étape.

    C'est la ligne de partage que le suisse avait déjà tracée, et elle vaut ici pour deux champs au
    lieu d'un : « zéro manche » et « portée nulle » sont faux dans l'absolu, sans qu'aucun effectif
    ait à être connu.
    """
    with pytest.raises(ConfigurationCollineInvalide, match="au moins une manche"):
        ConfigurationColline(nb_manches=0)

    with pytest.raises(ConfigurationCollineInvalide, match="au moins sur la position"):
        ConfigurationColline(nb_manches=3, portee_de_defi=0)


def test_une_pause_posee_apres_la_derniere_manche_est_refusee() -> None:
    """CA « pause programmée » : la borne se connaît **à la composition** pour une colline.

    ⚠️ **C'est le trou que la revue a rouvert deux fois de suite** (deux axes, indépendamment). La
    colline devient arrêtable par la seule bascule d'`avancement_lisible` — `TYPES_ARRETABLES` en
    dérive — sans que rien ne réclame la contrepartie : dire combien de tours elle compte. Sans
    elle,
    `verifier_arrets` ne refuse rien (`nb_tours=None` signifie « inconnu »), et une pause « après la
    manche 7 » sur une phase réglée à 3 manches était **acceptée à l'atelier, puis définitivement
    muette le jour J**. C'est mot pour mot le mode de panne qu'E05US035 avait fermé pour la
    qualification.

    Le raisonnement à rejouer pour tout type ajouté à `TYPES_ARRETABLES` : *son nombre de tours
    est-il un réglage porté par l'étape, ou une conséquence du terrain ?* Pour la colline, c'est un
    réglage — `nb_manches` — au même titre que le découpage d'une qualification.
    """
    # Une pause entre les manches 1 et 2 : légitime, elle coupe quelque chose.
    _etape(arrets=(ArretProgramme(apres_tour=1),))

    with pytest.raises(ArretProgrammeInvalide, match="n'en compte que 3"):
        _etape(arrets=(ArretProgramme(apres_tour=7),))

    # Le refus doit **flécher un geste** (`P-3` : un refus sans issue est un cul-de-sac), et nommer
    # le réglage de CE format — « le nombre de tours du découpage » n'existe pas sur une colline.
    with pytest.raises(ArretProgrammeInvalide, match="nombre de manches"):
        _etape(arrets=(ArretProgramme(apres_tour=3),))


def test_une_colline_non_reglee_ne_borne_aucune_pause() -> None:
    """Le pendant du cas ci-dessus : on ne borne pas ce qu'on ne peut pas juger.

    Une étape de colline sans réglage ne connaît pas son nombre de manches ; refuser une pause y
    serait deviner. Le réglage manquant est déjà refusé ailleurs, au démarrage de la phase — c'est
    une autre porte, et elle reste fermée.
    """
    etape = _etape(colline=None, arrets=(ArretProgramme(apres_tour=99),))

    assert etape.colline is None
