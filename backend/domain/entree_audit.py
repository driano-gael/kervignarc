"""Agrégat `EntreeAudit` — une entrée du **journal d'audit métier** (E10US005).

Le jour J, des actes **sensibles** sont posés : un scoreur **valide** une série (elle se
verrouille), un rôle habilité **corrige** un score verrouillé, un archer est déclaré en **forfait**.
En cas
de litige (« qui a validé ma série à 8, pas à 9 ? »), il faut pouvoir répondre. Chaque entrée fige
donc les quatre invariants d'une trace utile — **qui / quand / avant-après** (CDC UX `D-04`) —, plus
l'**objet** sur lequel l'action a porté et sa **nature** (`ActionAuditee`).

Trace en **ajout seul** (cf. port `AuditRepository`) : une entrée ne se modifie pas — la corriger la
viderait de sa valeur de preuve. D'où un agrégat **immuable** (`frozen`).

L'`auteur` est le **nom** de qui a agi (un scoreur, l'admin), **pas une clé étrangère** : la trace
d'une validation doit survivre à la **suppression** du scoreur (E10US003) — un scoreur qui ne vient
plus est retiré, ses validations passées restent lisibles. Stocker son `id` casserait à sa
suppression ; on fige donc le nom au moment de l'acte.

**Socle E10US005** : cet agrégat et son service (`ServiceAudit.consigner`) sont la primitive
d'écriture. Les **producteurs** — la validation et la correction (E04US002), le forfait (E12US004) —
appelleront `consigner` depuis leur propre commande d'écriture ; ils n'existent pas encore. La
surface de **consultation** admin livrée ici (`lister` + endpoint `GET`) rend le journal exploitable
dès qu'il se remplira.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.erreurs import AuteurAuditInvalide, HorodatageAuditInvalide, ObjetAuditInvalide
from domain.tournoi import TournoiId

EntreeAuditId = int
"""Identifiant technique d'une entrée d'audit, attribué par la persistance."""


class ActionAuditee(str, Enum):
    """Nature de l'acte sensible tracé — l'ensemble **fermé** des actions du CA E10US005.

    `(str, Enum)` : la valeur est un slug stable, stocké tel quel en base (comme `StatutTournoi`).
    Producteurs : `VALIDATION`/`CORRECTION_SCORE` (E04US002), `FORFAIT` (E12US004, à venir),
    `REPLACEMENT` (E12US007 — régénération **massive** du plan de cibles, quand des scores existent
    déjà, [ADR-0040]). Les nommer ici n'anticipe pas leur code : c'est le **vocabulaire** du CA.

    [ADR-0040]: ../../docs/adr/0040-alerte-par-calcul-d-impact.md
    """

    VALIDATION = "validation"
    CORRECTION_SCORE = "correction_score"
    FORFAIT = "forfait"
    REPLACEMENT = "replacement"


@dataclass(frozen=True)
class EntreeAudit:
    """Une entrée du journal d'audit. `id` vaut `None` tant qu'elle n'est pas persistée.

    `avant`/`apres` sont **optionnels** : une **validation** est un évènement sans état antérieur
    (l'objet dit *quelle* série a été verrouillée, il n'y a pas d'« avant » à opposer à un
    « après ») ; une **correction**, elle, les renseigne (l'ancienne et la nouvelle valeur). Ce sont
    des
    représentations **textuelles** libres, laissées au producteur — le socle ne présume pas de leur
    forme.
    """

    tournoi_id: TournoiId
    action: ActionAuditee
    auteur: str
    horodatage: datetime.datetime
    objet: str
    avant: str | None = None
    apres: str | None = None
    id: EntreeAuditId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        action: ActionAuditee,
        auteur: str,
        horodatage: datetime.datetime,
        objet: str,
        avant: str | None = None,
        apres: str | None = None,
    ) -> EntreeAudit:
        """Construit une entrée valide.

        `auteur` et `objet` sont normalisés (espaces de bord retirés) et ne peuvent être vides
        (`AuteurAuditInvalide`, `ObjetAuditInvalide`) — sans eux, la trace ne dit pas *qui* ni *sur
        quoi*. `horodatage` (« quand ») est fourni par l'appelant via le port `Horloge` (jamais lu
        ici : le domaine reste pur et déterministe) et doit être un instant **UTC** *aware*
        (`HorodatageAuditInvalide` sinon) : la persistance réattache UTC en aveugle à la relecture,
        ce qui n'est fidèle que si l'écrit était déjà UTC. `avant`/`apres` restent **verbatim**.
        """
        return EntreeAudit(
            tournoi_id=tournoi_id,
            action=action,
            auteur=_auteur_valide(auteur),
            horodatage=_horodatage_valide(horodatage),
            objet=_objet_valide(objet),
            avant=avant,
            apres=apres,
        )


def _auteur_valide(auteur: str) -> str:
    """Normalise l'auteur ; lève `AuteurAuditInvalide` s'il est vide."""
    auteur_normalise = auteur.strip()
    if not auteur_normalise:
        raise AuteurAuditInvalide("L'auteur d'une entrée d'audit ne peut pas être vide.")
    return auteur_normalise


def _objet_valide(objet: str) -> str:
    """Normalise l'objet ; lève `ObjetAuditInvalide` s'il est vide."""
    objet_normalise = objet.strip()
    if not objet_normalise:
        raise ObjetAuditInvalide("L'objet d'une entrée d'audit ne peut pas être vide.")
    return objet_normalise


def _horodatage_valide(horodatage: datetime.datetime) -> datetime.datetime:
    """Vérifie que l'horodatage est un instant UTC *aware* ; lève `HorodatageAuditInvalide` sinon.

    `utcoffset()` vaut `None` pour un datetime **naïf** et un `timedelta` non nul pour un fuseau
    **non-UTC** : un unique test `!= timedelta(0)` couvre les deux cas fautifs. On ne convertit pas
    en UTC en douce — un horodatage mal fuseauté est un **bug de l'appelant** (une horloge non
    conforme au contrat du port `Horloge`), pas une entrée à corriger silencieusement.
    """
    if horodatage.utcoffset() != datetime.timedelta(0):
        raise HorodatageAuditInvalide(
            "L'horodatage d'une entrée d'audit doit être un instant UTC (datetime aware)."
        )
    return horodatage
