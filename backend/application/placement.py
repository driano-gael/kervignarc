"""Service applicatif Placement — plan de cibles d'un départ (E03US001).

Orchestre le moteur de placement **pur** (`domain/placement.py`) derrière les ports repository :
il reconstitue, pour un départ, la liste des archers inscrits et **joint** chacun à sa catégorie
puis à son blason par défaut (`Archer.categorie_id → Categorie.blason_id → Blason`), construit les
`ArcherAPlacer` et appelle `placer`. Aucune écriture : le plan est **recalculé à la demande**
(périmètre d'E03US001 ; la persistance et l'ajustement manuel sont E03US004).

Un archer dont la catégorie n'a **pas** de blason par défaut ne peut pas être placé — on ignore sa
fraction de place : il ressort en conflit `SANS_BLASON`. Ces conflits « de données » sont fusionnés
avec les conflits « de faisabilité » que renvoie le moteur (`NON_PLACE`), pour un **rapport unique**
(CA « conflits »). Lecture synchrone, hors file d'écriture (règle 7).
"""

from __future__ import annotations

from application.erreurs import DepartIntrouvable, GabaritDuTournoiAbsent, TournoiIntrouvable
from domain.archer import ArcherId
from domain.depart import DepartId
from domain.placement import (
    ArcherAPlacer,
    Conflit,
    PlanDeCibles,
    RaisonConflit,
    placer,
)
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    DepartRepository,
    GabaritSalleRepository,
    InscriptionRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServicePlacement:
    """Cas d'usage du placement : produire le plan de cibles d'un départ."""

    def __init__(
        self,
        tournois: TournoiRepository,
        departs: DepartRepository,
        gabarits: GabaritSalleRepository,
        inscriptions: InscriptionRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._gabarits = gabarits
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._blasons = blasons

    def plan_de_cibles(self, tournoi_id: TournoiId, depart_id: DepartId) -> PlanDeCibles:
        """Calcule le plan de cibles des archers inscrits à un départ.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DepartIntrouvable` si le départ
        n'existe pas ou n'appartient pas à ce tournoi, `GabaritDuTournoiAbsent` si aucun gabarit
        n'est appliqué au tournoi (il n'y a alors pas de cible à remplir).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )

        a_placer: list[ArcherAPlacer] = []
        conflits_donnees: list[Conflit] = []
        for inscription in self._inscriptions.par_depart(depart_id):
            entree = self._archer_a_placer(inscription.archer_id)
            if entree is None:
                conflits_donnees.append(
                    Conflit(archer_id=inscription.archer_id, raison=RaisonConflit.SANS_BLASON)
                )
            else:
                a_placer.append(entree)

        plan = placer(gabarit.cibles, tuple(a_placer))
        # Les conflits « de données » (sans blason) d'abord, puis ceux « de faisabilité » du moteur.
        return PlanDeCibles(cibles=plan.cibles, conflits=tuple(conflits_donnees) + plan.conflits)

    def _archer_a_placer(self, archer_id: ArcherId) -> ArcherAPlacer | None:
        """Reconstruit l'entrée du moteur pour un archer, ou `None` si sa fraction est inconnue.

        `None` = pas de blason exploitable (catégorie sans blason par défaut, ou incohérence de
        données) : l'appelant en fait un conflit `SANS_BLASON`. Chaîne : archer → catégorie →
        blason par défaut, d'où l'on tire fraction (`taille`), capacité de carton et hauteur.
        """
        archer = self._archers.par_id(archer_id)
        if archer is None:
            return None
        categorie = self._categories.par_id(archer.categorie_id)
        if categorie is None:
            return None
        blason_id = categorie.blason_id
        if blason_id is None:
            return None
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            return None
        return ArcherAPlacer(
            archer_id=archer_id,
            blason_id=blason_id,
            taille=blason.taille,
            capacite_blason=blason.capacite,
            hauteur_cm=categorie.hauteur_cm,
        )
