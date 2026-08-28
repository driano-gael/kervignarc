"""Le corpus de recherche — des résumés, pas les textes entiers.

Choix assumé : **pas d'index inversé.** Le corpus fait ~300 documents ; un `indexOf` sur une copie
normalisée coûte quelques millisecondes. Un index pèserait autant, demanderait une tokenisation
française et **interdirait la recherche par expression** (« portée sportive », `E05US028`) —
précisément ce qu'on cherche ici. La normalisation (minuscules, sans accents) est faite **ici**,
une fois, et non dans le navigateur à chaque frappe.
"""

from __future__ import annotations

from typing import TypedDict

from atlas import markdown
from atlas.modele import Decision, Regle
from atlas.normalisation import sans_accent


class Document(TypedDict):
    genre: str
    identifiant: str
    titre: str
    texte: str
    recherche: str
    lien: str


def _normaliser(texte: str) -> str:
    return sans_accent(texte).lower()


def construire(regles: tuple[Regle, ...], decisions: tuple[Decision, ...]) -> list[Document]:
    documents: list[Document] = []

    for regle in regles:
        texte = markdown.tronquer(markdown.en_clair(regle.corps), 1200)
        documents.append(
            Document(
                genre="regle",
                identifiant=regle.identifiant,
                titre=regle.titre,
                texte=texte,
                recherche=_normaliser(f"{regle.titre} {regle.section} {texte}"),
                lien=f"regle.html?id={regle.identifiant}",
            )
        )

    for decision in decisions:
        entete = " ".join(f"{lien.libelle} ADR-{lien.cible}" for lien in decision.liens)
        texte = markdown.tronquer(decision.extrait, 1200)
        documents.append(
            Document(
                genre="decision",
                identifiant=decision.identifiant,
                titre=f"ADR-{decision.identifiant} — {decision.titre}",
                texte=texte,
                recherche=_normaliser(
                    f"ADR-{decision.identifiant} {decision.titre} {entete} "
                    f"{' '.join(decision.us)} {texte}"
                ),
                lien=f"adr.html?id={decision.identifiant}",
            )
        )

    return documents
