"""Service applicatif Departs — orchestre les créneaux d'un tournoi (E02US004, ADR-0017).

Use cases de configuration des **départs** (créneaux horaires) d'un tournoi : créer, lister, éditer
(tarif/horaire), supprimer. Il ne connaît ni HTTP, ni SQL, ni la file d'écriture (sérialisation
assurée en amont, côté API) ; il reste synchrone et pur d'infrastructure.

Il arbitre l'**existence** — du tournoi (`TournoiIntrouvable`) et du départ dans ce tournoi
(`DepartIntrouvable`) — et **attribue le numéro** d'un nouveau créneau : le domaine ne voit qu'un
départ à la fois, il ne peut donc pas savoir quel numéro est libre. Le numéro est toujours **le plus
grand existant + 1** (1 pour le premier) — jamais un rang recalculé. Supprimer un créneau
**intermédiaire** laisse donc un trou définitif ; supprimer **le dernier** (le plus grand numéro)
libère son numéro, que la création suivante reprendra (le max a baissé). Les inscriptions et le
placement référencent l'`id` technique, pas le `numero`, donc cette réutilisation est sans effet.

Le lien archer↔départ (inscription) et le suivi `payé` sont E02US009 : ce service ne gère que la
**définition** des créneaux.
"""

from __future__ import annotations

from typing import Protocol

from application.erreurs import (
    DepartAvecInscriptions,
    DepartEnCoursNonConfirme,
    DepartIntrouvable,
    DernierDepartNonSupprimable,
    TournoiIntrouvable,
)
from domain.cycle_depart import AvancementDepart, EtatDepart
from domain.depart import Depart, DepartId
from domain.ports import (
    ArcherRepository,
    DepartRepository,
    DerouleRepository,
    Horloge,
    InscriptionRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.remboursement import MotifRemboursement, Remboursement
from domain.tournoi import StatutTournoi, TournoiId

_LIBELLE_ETAT = {EtatDepart.LANCE: "lancé", EtatDepart.CLOS: "clos"}
"""Libellé humain de l'état protégé, pour le message de signalement (jamais *ouvert* : il ne lève
pas)."""


class LecteurAvancementDepart(Protocol):
    """Port étroit : lire l'**avancement** d'un créneau (réalisé par `ServiceCompletude`).

    Le service des départs n'a pas besoin de toute la complétude ni de savoir *comment* l'état se
    calcule (placements · séries · forfaits · barème) : juste du **verdict** chiffré par créneau,
    d'où l'on dérive `EtatDepart`. Même patron que `LecteurPaiements` (application/completude.py) :
    un port étroit découple le consommateur du service porteur et se falsifie trivialement en test.
    """

    def avancement_depart(self, tournoi_id: TournoiId, depart_id: DepartId) -> AvancementDepart:
        """L'avancement du créneau (nb placés / ayant tiré / séries closes) à cet instant."""
        ...


class ServiceDeparts:
    """Cas d'usage des départs d'un tournoi : créer, lister, éditer, supprimer."""

    def __init__(
        self,
        depart_repository: DepartRepository,
        tournoi_repository: TournoiRepository,
        inscription_repository: InscriptionRepository,
        lecteur_avancement: LecteurAvancementDepart,
        archer_repository: ArcherRepository,
        horloge: Horloge,
        deroule_repository: DerouleRepository,
        phase_repository: PhaseRepository,
    ) -> None:
        self._departs = depart_repository
        self._tournois = tournoi_repository
        self._inscriptions = inscription_repository
        self._avancement = lecteur_avancement
        self._archers = archer_repository
        self._horloge = horloge
        # ⚠️ **Un créneau neuf doit rejouer le déroulé déjà composé** (ADR-0076, relevé en revue).
        # L'ADR n'énonçait la synchronisation que dans un sens — « ajouter une étape crée son
        # instance dans chaque créneau » — et le sens inverse manquait : un départ ouvert après
        # coup n'avait **aucune** phase, donc rien à piloter et pas de qualification d'où tirer un
        # barème. Le seul remède aurait été de réappliquer le format, ce qui détruit les phases
        # déjà engagées des autres créneaux.
        self._deroules = deroule_repository
        self._phases = phase_repository

    def creer(
        self,
        tournoi_id: TournoiId,
        tarif_centimes: int,
        horaire: str,
        quota: int | None = None,
    ) -> Depart:
        """Crée et persiste un départ dans un tournoi, avec un numéro attribué automatiquement.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si le tarif, l'horaire
        (`HH:MM` obligatoire, E02US010) ou le quota sont invalides. Le numéro est le plus grand
        existant + 1 (1 pour le premier créneau) ; le `quota` est facultatif (`None` = créneau sans
        plafond, E02US006).

        Lecture (`par_tournoi`) puis écriture (`ajouter`) tiennent dans **une seule commande** en
        file (règle 7, ADR-0005) : aucune création concurrente ne peut se glisser entre le calcul du
        numéro et l'insertion. La contrainte `UNIQUE(tournoi_id, numero)` reste le garde-fou ultime.
        """
        self._verifier_tournoi(tournoi_id)
        existants = self._departs.par_tournoi(tournoi_id)
        numero = existants[-1].numero + 1 if existants else 1
        depart = Depart.creer(tournoi_id, numero, tarif_centimes, horaire, quota)
        pose = self._departs.ajouter(depart)
        assert pose.id is not None, "Un départ persisté porte toujours son identifiant."
        # Le créneau rejoue le déroulé **déjà** défini pour ce tournoi : une instance par étape, au
        # statut « à venir ». Sur un tournoi non encore composé, la boucle est vide — et les étapes
        # ajoutées ensuite s'instancieront dans ce créneau comme dans les autres.
        for etape in self._deroules.par_tournoi(tournoi_id):
            self._phases.ajouter(etape.instancier(pose.id))
        return pose

    def lister(self, tournoi_id: TournoiId) -> list[Depart]:
        """Renvoie les départs d'un tournoi, triés par numéro (liste éventuellement vide).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._verifier_tournoi(tournoi_id)
        return self._departs.par_tournoi(tournoi_id)

    def lister_avec_etat(self, tournoi_id: TournoiId) -> list[tuple[Depart, EtatDepart]]:
        """Les départs du tournoi, chacun avec son **état de cycle de vie** dérivé (E12US008).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas. Lecture seule : l'état est **calculé**
        (jamais stocké) à partir de l'avancement lu au vol — le front en fait un badge par créneau.
        Simplicité assumée (règle 12) : un appel d'avancement par départ ; les créneaux d'un tournoi
        se comptent sur les doigts, la relecture n'est pas un goulot.
        """
        self._verifier_tournoi(tournoi_id)
        departs = self._departs.par_tournoi(tournoi_id)
        return [(depart, self._etat_de(depart)) for depart in departs]

    def modifier(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        tarif_centimes: int,
        horaire: str,
        quota: int | None = None,
        confirme_cycle: bool = False,
    ) -> Depart:
        """Édite le tarif, l'horaire et le quota d'un départ (le numéro est fixe).

        **Remplacement complet** : tarif, horaire et quota sont réécrits ; un `quota` omis (`None`)
        **retire** le plafond (E02US006). L'horaire reste **obligatoire** (`HH:MM`, E02US010). Lève
        `DepartIntrouvable` si le départ n'existe pas dans ce tournoi, `DomainError` si le tarif,
        l'horaire ou le quota sont invalides.

        **Garde-fou de cycle (E12US008)** : si le créneau est *lancé* ou *clos* (une session de tir
        y a eu lieu), lève `DepartEnCoursNonConfirme` tant que `confirme_cycle` n'est pas vrai — on
        ne réécrit pas les paramètres d'un créneau en cours de tir par mégarde.
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        self._exiger_confirmation_cycle(depart, confirme_cycle)
        return self._departs.enregistrer(depart.modifier(tarif_centimes, horaire, quota))

    def supprimer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        autoriser_suppression_inscrits: bool = False,
        confirme_cycle: bool = False,
    ) -> None:
        """Supprime un départ d'un tournoi (E02US004, garde-fous E02US009 + E12US008).

        Lève `DepartIntrouvable` si le départ n'existe pas dans ce tournoi. Trois garde-fous.

        D'abord, un **refus dur** : c'est le **dernier** départ d'un tournoi **non-brouillon**
        (`DernierDepartNonSupprimable`, E02US010). Aucun drapeau ne le lève — un tournoi engagé a
        été validé avec ≥ 1 créneau ; pour repartir de zéro, l'admin **revient en brouillon**. Ce
        refus **précède** les deux confirmations ci-dessous : les proposer n'aurait pas de sens
        puisque la suppression est de toute façon interdite.

        Ensuite, deux garde-fous selon l'**état de cycle** du créneau :

        - *lancé* / *clos* (une session de tir a eu lieu) : lève `DepartEnCoursNonConfirme` tant que
          `confirme_cycle` n'est pas vrai. Cette confirmation **subsume** le signalement
          d'inscriptions — un créneau lancé porte forcément des inscriptions, et confirmer
          qu'on détruit une session de tir couvre *a fortiori* ses inscriptions (pas de double
          dialogue, E12US008) ;
        - *ouvert* (aucun score) : comportement E02US009 strictement inchangé — si le créneau porte
          des **inscriptions**, lève `DepartAvecInscriptions` (signalement, pas refus, ADR-0018),
          que l'admin lève via `autoriser_suppression_inscrits=True`.

        Le message d'inscriptions **décompte les inscriptions, dont les payées**, pour exposer
        l'effet de bord monétaire (remboursement déporté en E08US005).
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        assert depart.id is not None, "Un départ relu est persisté."
        self._refuser_suppression_du_dernier_depart(tournoi_id)
        etat = self._exiger_confirmation_cycle(depart, confirme_cycle)
        # DETTE-007 : la confirmation d'inscriptions est **aveugle**. Le décompte annoncé n'est pas
        # revérifié au rejeu — entre le 409 et la confirmation, d'autres tablettes peuvent inscrire
        # ou marquer payé, et l'on effacerait plus que le message n'a annoncé. Ne joue que sur un
        # créneau *ouvert* : sur *lancé*/*clos*, la confirmation de cycle a déjà tranché plus haut.
        if etat is EtatDepart.OUVERT and not autoriser_suppression_inscrits:
            self._signaler_inscriptions(depart)
        self._supprimer_en_remboursant(depart)

    def _supprimer_en_remboursant(self, depart: Depart) -> None:
        """Supprime le départ en **ouvrant les remboursements** de ses inscriptions payées
        (E08US005).

        Sur un créneau **tarifé**, chaque inscription **payée** effacée devient un remboursement à
        traiter (ADR-0057) : on les construit (instantané archer + créneau, montant = tarif) et on
        confie leur ouverture **atomique** avec les `DELETE` à l'adapter
        (`supprimer_avec_remboursements`). Sans payée à rembourser (créneau gratuit, aucune payée),
        on retombe sur la suppression simple. La confirmation de l'admin a déjà été obtenue en
        amont.
        """
        assert depart.id is not None, "Un départ relu est persisté."
        remboursements = (
            self._remboursements_des_payees(depart) if depart.tarif_centimes > 0 else []
        )
        if remboursements:
            self._departs.supprimer_avec_remboursements(depart.id, remboursements)
        else:
            self._departs.supprimer(depart.id)

    def _remboursements_des_payees(self, depart: Depart) -> list[Remboursement]:
        """Un `Remboursement` par inscription **payée** du créneau (tarif > 0 garanti par
        l'appelant).

        L'instantané (prénom/nom de l'archer, libellé du créneau) est figé maintenant — il doit
        survivre à l'effacement du départ. Une inscription payée dont l'archer aurait disparu (cas
        défensif quasi impossible : la suppression d'archer purge ses inscriptions) est **ignorée**
        faute de nom à figer — plutôt qu'un remboursement anonyme.
        """
        assert depart.id is not None, "Un départ relu est persisté."
        instant = self._horloge.maintenant()
        creneau = f"Départ n°{depart.numero} — {depart.horaire}"
        remboursements: list[Remboursement] = []
        for inscription in self._inscriptions.par_depart(depart.id):
            if not inscription.paye:
                continue
            archer = self._archers.par_id(inscription.archer_id)
            if archer is None:
                continue
            remboursements.append(
                Remboursement.creer(
                    depart.tournoi_id,
                    archer_prenom=archer.prenom,
                    archer_nom=archer.nom,
                    creneau=creneau,
                    # DETTE-016 : le montant remboursé est le **tarif courant**, pas la somme
                    # réellement encaissée (le modèle ne stocke que le booléen `paye`) — faux si le
                    # tarif a été édité après le paiement. Résorption : figer la somme encaissée.
                    montant_centimes=depart.tarif_centimes,
                    motif=MotifRemboursement.DEPART_SUPPRIME,
                    cree_le=instant,
                )
            )
        return remboursements

    def _refuser_suppression_du_dernier_depart(self, tournoi_id: TournoiId) -> None:
        """Lève `DernierDepartNonSupprimable` si retirer ce départ laisserait un tournoi engagé sans
        aucun créneau (E02US010).

        « Engagé » = tout statut **hors brouillon** : dès `prêt`, la garde `TournoiSansDepart`
        (`ServiceTournois.vers_pret`) a exigé ≥ 1 départ ; cette garde-ci **maintient** l'invariant
        en aval. Le compte (`par_tournoi`) inclut le départ qu'on s'apprête à retirer, d'où le test
        « ≤ 1 » : s'il n'en reste qu'un, c'est celui-là. Sur un `brouillon`, aucune borne — le
        tournoi n'est pas encore engagé. La lecture du tournoi et celle des départs tiennent dans la
        même commande de file que la suppression (règle 7) : pas de course avec un autre créneau.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if tournoi.statut is StatutTournoi.BROUILLON:
            return
        if len(self._departs.par_tournoi(tournoi_id)) <= 1:
            raise DernierDepartNonSupprimable(
                "C'est le dernier départ de ce tournoi, qui n'est plus en brouillon : un tournoi "
                "engagé doit garder au moins un créneau, son dernier départ ne peut pas être "
                "supprimé."
            )

    def _exiger_confirmation_cycle(self, depart: Depart, confirme_cycle: bool) -> EtatDepart:
        """Renvoie l'`EtatDepart` du créneau, ou lève `DepartEnCoursNonConfirme` si nécessaire.

        Sur un créneau *lancé* ou *clos* non confirmé, lève un **signalement chiffré** (famille de
        `ReplacementNonConfirme`, E12US007) : `details` porte l'état et le nombre d'archers ayant
        tiré, calculés au moment d'agir — jamais crus sur parole. Sur un créneau *ouvert*, renvoie
        simplement `OUVERT` (rien à confirmer côté cycle).
        """
        avancement = self._avancement_de(depart)
        etat = avancement.etat
        if etat is not EtatDepart.OUVERT and not confirme_cycle:
            libelle = _LIBELLE_ETAT[etat]
            tireurs = avancement.nb_ayant_tire
            accord = "archer y a déjà tiré" if tireurs == 1 else "archers y ont déjà tiré"
            message = (
                f"Le départ n° {depart.numero} est {libelle} : {tireurs} {accord}. Le modifier ou "
                "le supprimer touche une session de tir ; confirmez seulement si c'est voulu."
            )
            raise DepartEnCoursNonConfirme(message, etat=etat.value, archers_ayant_tire=tireurs)
        return etat

    def etat(self, tournoi_id: TournoiId, depart_id: DepartId) -> EtatDepart:
        """État de cycle de vie d'un créneau donné (E12US008), pour le rafraîchir après édition.

        Lève `DepartIntrouvable` si le départ n'existe pas dans ce tournoi.
        """
        return self._etat_de(self._depart_du_tournoi(tournoi_id, depart_id))

    def _etat_de(self, depart: Depart) -> EtatDepart:
        """État de cycle dérivé d'un créneau (pour l'affichage : liste, badge)."""
        return self._avancement_de(depart).etat

    def _avancement_de(self, depart: Depart) -> AvancementDepart:
        """Lit l'avancement d'un créneau via le port étroit (placements · séries · forfaits)."""
        assert depart.id is not None, "Un départ relu est persisté."
        return self._avancement.avancement_depart(depart.tournoi_id, depart.id)

    def _signaler_inscriptions(self, depart: Depart) -> None:
        """Lève `DepartAvecInscriptions` si le créneau porte des inscriptions (E02US009).

        Le message énumère ce qui sera détruit — nombre d'inscriptions **et** de payées — plutôt que
        d'inviter à confirmer : les payées sont une somme encaissée qui deviendra un remboursement
        (E08US005), l'admin doit le voir avant de trancher.
        """
        assert depart.id is not None, "Un départ relu est persisté."
        inscriptions = self._inscriptions.par_depart(depart.id)
        if not inscriptions:
            return
        nombre = len(inscriptions)
        payees = sum(1 for inscription in inscriptions if inscription.paye)
        accord = "inscription" if nombre == 1 else "inscriptions"
        detail = f"{nombre} {accord}"
        if payees:
            detail += f", dont {payees} déjà payée" + ("s" if payees > 1 else "")
        message = (
            f"Le départ n° {depart.numero} porte {detail}. Le supprimer les effacera définitivement"
        )
        # La clause de remboursement ne s'affiche **que** s'il y a des payées **sur un créneau
        # tarifé** : sinon elle évoquerait un remboursement fictif (créneau gratuit — rien encaissé
        # —
        # ou aucune inscription réglée). Depuis E08US005, cette promesse est **tenue** (le
        # remboursement est réellement ouvert à la suppression), d'où l'alignement sur `tarif > 0`.
        if payees and depart.tarif_centimes > 0:
            message += " ; les sommes déjà payées seront à rembourser (E08US005)"
        message += ". Confirmez seulement si ce créneau est bien annulé."
        raise DepartAvecInscriptions(message)

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        """Lève `TournoiIntrouvable` si le tournoi n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _depart_du_tournoi(self, tournoi_id: TournoiId, depart_id: DepartId) -> Depart:
        """Relit un départ et vérifie qu'il appartient au tournoi ; sinon `DepartIntrouvable`."""
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )
        return depart
