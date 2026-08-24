"""Tests de la politique pure des **jalons « prêt à… »** (E16US012) — dérivés du CA, avant impl.

Source : `stories/E16-retours-maquettes.md`, E16US012, puces « CA » :

- **une forme commune** : chaque écran répond à **une** question binaire (« puis-je passer à
  l'étape suivante ? »), liste **ce qui manque** sous forme d'états (**pas** de barre de
  progression, `D-17`), et porte **l'action** correspondante ;
- **les quatre membres** : démarrer · terminer · archiver · exporter ;
- il **avertit sans bloquer** (`D-15`) ;
- **sans doublonner ce qui existe** : la frise (E14US001) porte déjà les transitions et leurs
  gardes — ces écrans s'y **branchent**.

Arbitrage du commanditaire du 23/08/2026 (reversé à la fiche) : **forme unique paramétrée** par le
jalon, et non quatre écrans jumeaux. D'où le contrat testé ici — un seul type de réponse,
`PreparationJalon`, quel que soit le membre.

Domaine pur : on appelle les politiques sur des décomptes déjà agrégés, comme `evaluer_completude`.
"""

from __future__ import annotations

import pytest

from domain.completude import EtatSection, LigneCompletude, evaluer_completude
from domain.jalon import (
    CLE_CRENEAUX,
    CLE_DEROULE,
    CLE_EFFECTIF,
    Jalon,
    PreparationJalon,
    evaluer_demarrer,
    evaluer_terminer,
    question,
    transition_offerte,
)
from domain.tournoi import (
    MESSAGE_SANS_DEPART,
    MESSAGE_TERMINER_HORS_EN_COURS,
    StatutTournoi,
)


def _ligne(preparation: PreparationJalon, cle: str) -> LigneCompletude:
    """La ligne d'une clé (échoue si absente : le contrat garantit sa présence)."""
    return next(ligne for ligne in preparation.lignes if ligne.cle == cle)


def _demarrer_pret() -> PreparationJalon:
    """Un « prêt à démarrer » dont rien ne manque — base des variations."""
    return evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=2,
        nb_etapes_deroule=3,
        effectif_suffisant=True,
        inscrits=40,
        minimum=34,
        cause_effectif=None,
    )


# --- CA « les quatre membres » -----------------------------------------------------------------


def test_la_famille_compte_exactement_quatre_membres() -> None:
    """Le CA les nomme : démarrer, terminer, archiver, exporter."""
    assert {j.value for j in Jalon} == {"demarrer", "terminer", "archiver", "exporter"}


@pytest.mark.parametrize("jalon", list(Jalon))
def test_chaque_membre_pose_sa_question_sous_la_meme_forme(jalon: Jalon) -> None:
    """CA « forme commune » : la question est la **même phrase**, seul le verbe change.

    C'est ce qui fait une famille plutôt que quatre écrans qui se ressemblent : le libellé n'est
    pas rédigé écran par écran, il se **dérive** du jalon.
    """
    assert question(jalon).startswith("Prêt à ")
    assert question(jalon).endswith(" ?")


# --- CA « une forme commune » : un seul type de réponse -----------------------------------------


def test_les_deux_membres_livres_rendent_la_meme_structure() -> None:
    """Démarrer et terminer sont deux jalons du **même** type — c'est tout l'objet de l'US.

    Si l'un rendait sa propre structure, `E16US007` et `E16US008` figeraient chacune la leur : le
    défaut que la fiche demande précisément d'éviter en instruisant cette US avant elles.
    """
    demarrer = _demarrer_pret()
    terminer = evaluer_terminer(
        completude=evaluer_completude(qualif=(30, 30), paiements=(120, 120)),
        statut=StatutTournoi.EN_COURS,
    )

    assert isinstance(demarrer, PreparationJalon)
    assert isinstance(terminer, PreparationJalon)
    assert demarrer.jalon is Jalon.DEMARRER
    assert terminer.jalon is Jalon.TERMINER


def test_la_reponse_liste_des_etats_et_jamais_une_progression() -> None:
    """`D-17` : pas de barre de progression — chaque ligne porte un **état**, pas un pourcentage.

    Le décompte `fait/total` reste facultatif : il **illustre** l'état (« 28/34 »), il ne le
    remplace pas. Une ligne sans décompte doit donc rester lisible par son seul `etat`.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=0,
        nb_etapes_deroule=0,
        effectif_suffisant=True,
        inscrits=0,
        minimum=0,
        cause_effectif=None,
    )

    assert preparation.lignes  # il y a toujours quelque chose à dire
    for ligne in preparation.lignes:
        assert isinstance(ligne.etat, EtatSection)
    assert _ligne(preparation, CLE_CRENEAUX).fait is None


# --- CA « une question binaire » ----------------------------------------------------------------


def test_pret_a_demarrer_quand_les_creneaux_et_l_effectif_y_sont() -> None:
    """Rien ne manque : la réponse à « puis-je démarrer ? » est **oui**."""
    assert _demarrer_pret().pret is True


def test_sans_aucun_creneau_le_tournoi_n_est_pas_pret_a_demarrer() -> None:
    """Garde existante de `vers_pret` (E02US010) : « aucun départ » interdit le feu vert.

    L'écran doit **le dire avant le clic** — c'est le sujet de l'US : aujourd'hui cette garde ne
    se lit qu'en échouant, et seulement pour le premier manquement rencontré.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=0,
        nb_etapes_deroule=3,
        effectif_suffisant=True,
        inscrits=40,
        minimum=34,
        cause_effectif=None,
    )

    assert preparation.pret is False
    assert _ligne(preparation, CLE_CRENEAUX).etat is EtatSection.EN_ATTENTE


def test_un_effectif_insuffisant_chiffre_le_manque_et_empeche_le_depart() -> None:
    """Garde de `demarrer` (E05US021) : « 28 inscrits / 34 requis », visible **avant** le clic."""
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=2,
        nb_etapes_deroule=3,
        effectif_suffisant=False,
        inscrits=28,
        minimum=34,
        cause_effectif=None,
    )

    ligne = _ligne(preparation, CLE_EFFECTIF)
    assert preparation.pret is False
    assert ligne.etat is EtatSection.ALERTE
    assert (ligne.fait, ligne.total) == (28, 34)


def test_les_deux_manquements_se_lisent_ensemble_et_non_l_un_apres_l_autre() -> None:
    """**Le cœur de l'US.** Les gardes lèvent une exception : on ne découvre la seconde qu'après
    avoir réglé la première. L'écran, lui, les liste **toutes** d'un coup.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=0,
        nb_etapes_deroule=3,
        effectif_suffisant=False,
        inscrits=28,
        minimum=34,
        cause_effectif=None,
    )

    assert preparation.pret is False
    assert _ligne(preparation, CLE_CRENEAUX).etat is EtatSection.EN_ATTENTE
    assert _ligne(preparation, CLE_EFFECTIF).etat is EtatSection.ALERTE


def test_sans_deroule_compose_aucun_effectif_n_est_exige() -> None:
    """`minimum == 0` : rien n'est prélevé, donc rien n'est réclamé (cf. `exigence_effectif`).

    La ligne d'effectif ne doit **pas** s'alarmer sur un plancher qui n'existe pas — c'est le
    piège que `OrigineExigence` avait déjà coûté une fois (un message qui inventait sa cause).

    ⚠️ Mais elle ne doit pas non plus se dire **terminée** : zéro inscrit sans exigence, c'est
    « rien encore d'exploitable », pas « c'est fait ». La première version rendait `OK`, que
    l'écran affiche « Inscrits · Terminé » sur un tournoi qui vient d'être créé (relevé en revue).
    Ce que le CA garde intact, c'est `pret` : sans exigence, le tournoi démarre.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=1,
        nb_etapes_deroule=0,
        effectif_suffisant=True,
        inscrits=0,
        minimum=0,
        cause_effectif=None,
    )

    assert _ligne(preparation, CLE_EFFECTIF).etat is EtatSection.EN_ATTENTE
    assert preparation.pret is True


# --- CA « il avertit sans bloquer » (`D-15`) ----------------------------------------------------


def test_un_deroule_vide_est_signale_mais_ne_retient_pas_le_depart() -> None:
    """`D-15` : l'appli **avertit**, elle n'empêche pas. Le service laisse démarrer sans déroulé.

    C'est la ligne qui distingue *ce qui manque* de *ce qui bloque* : les confondre ferait dire à
    l'écran « vous ne pouvez pas démarrer » là où le serveur, lui, accepte — un écran qui ment.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=1,
        nb_etapes_deroule=0,
        effectif_suffisant=True,
        inscrits=12,
        minimum=0,
        cause_effectif=None,
    )

    assert _ligne(preparation, CLE_DEROULE).etat is EtatSection.EN_ATTENTE
    assert preparation.pret is True
    # ⚠️ Et l'effectif non plus n'est pas « terminé » : sans exigence, **aucun** compte ne clôt la
    # ligne. La 1ʳᵉ correction ne traitait que `inscrits == 0` et laissait « Terminé » sur le cas
    # le plus courant — un tournoi qui se remplit avant que le format soit composé (2ᵉ passe, C1).
    assert _ligne(preparation, CLE_EFFECTIF).etat is EtatSection.EN_ATTENTE


def test_terminer_n_est_jamais_bloquant_meme_incomplet() -> None:
    """`D-15` et le CA d'E12US005 : `sportif_complet` choisit le **libellé** de la confirmation,
    il ne **garde** rien. Une cible abandonnée ne doit pas empêcher de clore le tournoi.

    « Jamais bloquant » vaut **pendant le tournoi** — la garde de statut, elle, existe (cf. plus
    bas) : c'est la précision que le CA d'origine n'avait pas et que la revue a rendue nécessaire.
    """
    preparation = evaluer_terminer(
        completude=evaluer_completude(qualif=(28, 30), paiements=(0, 12)),
        statut=StatutTournoi.EN_COURS,
    )

    assert preparation.pret is False
    assert preparation.bloquant is False


def test_demarrer_est_bloquant_parce_que_le_serveur_refuse_vraiment() -> None:
    """Symétrique du précédent, et c'est **l'asymétrie de la famille** : *démarrer* a des gardes
    dures (`TournoiSansDepart`, `EffectifInsuffisantPourDemarrer`), *terminer* n'en a aucune.

    Sans ce drapeau, la forme unique dirait la même chose des deux — donc serait fausse sur l'un
    des deux.
    """
    assert _demarrer_pret().bloquant is True


# --- CA « sans doublonner ce qui existe » -------------------------------------------------------


def test_le_jalon_terminer_reprend_la_completude_sportive_sans_la_recalculer() -> None:
    """La complétude sportive (E12US005/E16US003) **est** le « prêt à terminer ». On la relit,
    on ne la réécrit pas : deux calculs se contrediraient au premier écart.
    """
    completude = evaluer_completude(qualif=(28, 30), paiements=(113, 120))
    preparation = evaluer_terminer(completude=completude, statut=StatutTournoi.EN_COURS)

    assert preparation.lignes == completude.sportif
    assert preparation.pret is completude.sportif_complet


def test_le_jalon_terminer_ignore_l_administratif() -> None:
    """E16US003, retour A14 : « complétude en déroulé n'est pas complétude administrative ».
    Les paiements ne sont pas une ligne de « prêt à terminer ».
    """
    completude = evaluer_completude(qualif=(30, 30), paiements=(0, 120))
    preparation = evaluer_terminer(completude=completude, statut=StatutTournoi.EN_COURS)

    assert preparation.pret is True
    assert all(ligne not in completude.hors_sportif for ligne in preparation.lignes)


# --- CA « sans doublonner ce qui existe » : la garde de STATUT ----------------------------------
#
# Ajoutée après revue (axe D). Le CA dit que le jalon énumère ce que les gardes vérifient : or
# `ServiceTournois` lève `TransitionStatutInvalide` **avant** toute autre garde, et la première
# version de ce module l'ignorait — elle répondait « prêt » sur un tournoi déjà lancé. C'est aussi
# la seule garde d'`ARCHIVER`, le membre suivant : sans elle, il n'aurait rien à énumérer.


@pytest.mark.parametrize(
    ("statut", "attendu"),
    [
        (StatutTournoi.EN_COURS, "déjà lancé"),
        (StatutTournoi.EN_PAUSE, "déjà lancé"),
        (StatutTournoi.TERMINE, "déjà lancé"),
        (StatutTournoi.ARCHIVE, "archivé"),
        (StatutTournoi.ANNULE, "annulé"),
    ],
)
def test_un_tournoi_qui_n_est_plus_a_lancer_dit_pourquoi_sans_se_tromper(
    statut: StatutTournoi, attendu: str
) -> None:
    """`demarrer` n'est atteignable que depuis *brouillon* ou *prêt*. Tout le reste répond non — et
    **pas avec la même phrase** : un tournoi annulé depuis le brouillon n'a jamais démarré.

    ⚠️ La 1ʳᵉ correction n'assertait ici que `detail is not None`. Elle passait donc sur un contrat
    qui disait « déjà lancé » d'un tournoi annulé — un test écrit pour passer, pas pour vérifier
    (2ᵉ passe de revue, quatre axes). C'est le contrat que liront `E16US007` et `E16US008`.
    """
    preparation = evaluer_demarrer(
        statut=statut,
        nb_creneaux=2,
        nb_etapes_deroule=3,
        effectif_suffisant=True,
        inscrits=40,
        minimum=34,
        cause_effectif=None,
    )

    assert preparation.pret is False
    assert preparation.bloquant is True
    assert preparation.detail is not None
    assert attendu in preparation.detail
    # **Aucune ligne** : « ce qui manque » n'a pas de sens ici, et les rendre obligeait le front à
    # les masquer lui-même — donc à recopier la garde.
    assert preparation.lignes == ()


@pytest.mark.parametrize("statut", [StatutTournoi.BROUILLON, StatutTournoi.PRET])
def test_la_question_se_pose_avant_le_depart_depuis_les_deux_statuts(
    statut: StatutTournoi,
) -> None:
    """Deux transitions mènent au départ (`vers-pret`, `demarrer`) : le jalon répond de l'**étape**,
    donc il répond pareil des deux côtés de `prêt`.
    """
    preparation = evaluer_demarrer(
        statut=statut,
        nb_creneaux=2,
        nb_etapes_deroule=3,
        effectif_suffisant=True,
        inscrits=40,
        minimum=34,
        cause_effectif=None,
    )

    assert preparation.pret is True
    assert preparation.question_posee is True
    assert preparation.detail is None


@pytest.mark.parametrize("jalon", list(Jalon))
def test_la_table_des_transitions_couvre_toute_la_famille(jalon: Jalon) -> None:
    """La table du jalon doit rester **totale** sur `Jalon` — sinon `KeyError`, donc 500.

    La règle ne vivait qu'en commentaire, alors que sa jumelle `_VERBE` est gardée juste au-dessus
    par le même patron (4ᵉ passe de revue, quatre axes). Un 5ᵉ membre ajouté à la famille sans sa
    ligne rouvrirait le 500 en silence : `ARCHIVER` et `EXPORTER` ne sont atteints par aucun autre
    test, le service les arrêtant à `JalonNonInstruit` bien avant le domaine.
    """
    assert transition_offerte(StatutTournoi.BROUILLON, jalon) in (True, False)


def test_exporter_ne_garde_aucune_transition_donc_la_question_se_pose_toujours() -> None:
    """`EXPORTER` garde un **geste répétable**, pas une transition (ADR-0096 §4).

    Le distinguer de « aucune transition offerte » n'est pas cosmétique : un tuple vide aurait rendu
    `False` sur les sept statuts, donc « prêt à exporter ? » bloqué **y compris sur un tournoi
    archivé** — l'état qu'ADR-0026 définit comme le verrou *après export*. C'était le piège tendu à
    `E16US007`, à qui l'ADR promet qu'elle n'a « plus de forme à inventer ».
    """
    for statut in StatutTournoi:
        assert transition_offerte(statut, Jalon.EXPORTER) is True


def test_terminer_hors_du_tournoi_en_cours_annonce_un_refus() -> None:
    """`ServiceTournois.terminer` n'accepte que `{EN_COURS}` : un tournoi **en pause** (la pause
    déjeuner du jour J) ne peut pas être terminé tant qu'on n'a pas repris.

    Le CA disait « terminer n'a aucune garde dure » ; c'est vrai du **contenu**, faux du statut —
    corrigé après revue, et reversé à la fiche.
    """
    complet = evaluer_completude(qualif=(30, 30), paiements=(120, 120))

    preparation = evaluer_terminer(completude=complet, statut=StatutTournoi.EN_PAUSE)

    assert preparation.pret is False
    assert preparation.bloquant is True
    # ⚠️ **Le cas discriminant** : liste **pleine** et question **fermée**. C'est exactement la
    # combinaison que `lignes` ne sait plus exprimer, donc la raison d'être du champ.
    assert preparation.question_posee is False
    # ⚠️ **Mais la liste reste** — asymétrie assumée avec *démarrer*, et corrigée en 5ᵉ passe. Chez
    # *terminer* la liste **est l'état sportif** : « où en est la qualification » a du sens à tout
    # statut, et c'est ce que l'organisateur vient voir pendant la pause. La vider était une
    # sur-correction, et l'assertion inverse écrite ici dérivait du code, pas du CA (règle 9).
    assert preparation.lignes == complet.sportif


# --- CA « sans doublonner ce qui existe » : le verdict d'effectif est REÇU, pas refait -----------


def test_l_effectif_suit_le_verdict_de_la_garde_et_ne_le_recalcule_pas() -> None:
    """Le cas qui distingue « transporter » de « recopier », et qu'aucun test ne pouvait voir tant
    que le domaine refaisait `inscrits >= minimum` : ici les deux chiffres **diraient** insuffisant,
    et pourtant la garde laisse passer.

    C'est exactement ce qui arrivera le jour où `exigence_effectif` gagnera une tolérance ou une
    dérogation. Le jalon doit suivre la garde, pas sa propre arithmétique.
    """
    preparation = evaluer_demarrer(
        statut=StatutTournoi.PRET,
        nb_creneaux=1,
        nb_etapes_deroule=3,
        effectif_suffisant=True,
        inscrits=28,
        minimum=34,
        cause_effectif=None,
    )

    assert preparation.pret is True
    assert _ligne(preparation, CLE_EFFECTIF).etat is EtatSection.OK
    assert (_ligne(preparation, CLE_EFFECTIF).fait, _ligne(preparation, CLE_EFFECTIF).total) == (
        28,
        34,
    )


def test_la_cause_chiffree_du_blocage_est_celle_du_refus_serveur() -> None:
    """`detail` porte la phrase de `message_de_refus()`, telle quelle. Le domaine ne la rédige pas :
    la recomposer ici laisserait l'avertissement d'avant le clic et le 409 d'après dire deux choses
    différentes du même manque (`D-16` / `P-4`).
    """
    cause = (
        "Ce tournoi ne peut pas démarrer : 8 archer(s) inscrit(s) sur le départ 2 pour 34 requis."
    )

    preparation = evaluer_demarrer(
        statut=StatutTournoi.PRET,
        nb_creneaux=2,
        nb_etapes_deroule=3,
        effectif_suffisant=False,
        inscrits=8,
        minimum=34,
        cause_effectif=cause,
    )

    assert preparation.detail == cause


# --- CA « un jalon répond de l'ÉTAPE, pas du prochain clic » ------------------------------------
#
# Ajouté en 2ᵉ passe (axe C1). Les deux gardes de *démarrer* ne tombent pas au même clic : les
# créneaux au passage en *prêt* (`vers_pret`), l'effectif au démarrage. Annoncer « au démarrage »
# dans les deux cas rendait la phrase fausse sur l'état initial de tout tournoi neuf.


def test_sans_creneau_le_refus_est_annonce_pour_le_passage_en_pret() -> None:
    """`vers_pret` lève `TournoiSansDepart` : le refus tombe **dès** « Marquer prêt »."""
    preparation = evaluer_demarrer(
        statut=StatutTournoi.BROUILLON,
        nb_creneaux=0,
        nb_etapes_deroule=3,
        effectif_suffisant=False,
        inscrits=28,
        minimum=34,
        cause_effectif="peu importe : ce n'est pas encore cette garde-là qui refusera",
    )

    assert preparation.moment == "dès le passage en « prêt »"
    # Et la cause affichée est celle de la garde qui refusera **la première**, pas de l'autre.
    assert preparation.detail == MESSAGE_SANS_DEPART


def test_avec_les_creneaux_le_refus_est_annonce_pour_le_demarrage() -> None:
    """Les créneaux sont là : la prochaine garde à refuser est celle de l'effectif."""
    cause = "Ce tournoi ne peut pas démarrer : 28 archer(s) inscrit(s) pour 34 requis."

    preparation = evaluer_demarrer(
        statut=StatutTournoi.PRET,
        nb_creneaux=1,
        nb_etapes_deroule=3,
        effectif_suffisant=False,
        inscrits=28,
        minimum=34,
        cause_effectif=cause,
    )

    assert preparation.moment == "au démarrage"
    assert preparation.detail == cause


def test_rien_ne_bloque_donc_aucun_moment_n_est_annonce() -> None:
    """Pas de refus à venir, pas de moment à nommer — sinon l'écran daterait un événement fictif."""
    preparation = _demarrer_pret()

    assert preparation.moment is None
    assert preparation.detail is None


def test_le_refus_de_terminer_hors_en_cours_est_celui_du_service_mot_pour_mot() -> None:
    """La phrase vient de `domain.tournoi`, que `ServiceTournois.terminer` utilise aussi.

    La 1ʳᵉ correction la recopiait ici en littéral — la duplication que cette US dénonce pour
    l'effectif, reproduite sur la garde de statut (2ᵉ passe, axes A, C2 et D).
    """
    complet = evaluer_completude(qualif=(30, 30), paiements=(120, 120))

    preparation = evaluer_terminer(completude=complet, statut=StatutTournoi.EN_PAUSE)

    assert preparation.detail == MESSAGE_TERMINER_HORS_EN_COURS


def test_pendant_le_tournoi_terminer_liste_bien_ce_qui_reste() -> None:
    """La contrepartie **positive** du cas précédent : sans elle, un `lignes=()` inconditionnel — la
    sur-correction symétrique — ne serait attrapé par aucun test du domaine.
    """
    completude = evaluer_completude(qualif=(28, 30), paiements=(113, 120))

    preparation = evaluer_terminer(completude=completude, statut=StatutTournoi.EN_COURS)

    assert preparation.lignes == completude.sportif
    assert preparation.bloquant is False
    assert preparation.question_posee is True
    assert preparation.detail is None
