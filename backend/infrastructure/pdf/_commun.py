"""Ce que partagent les adapters PDF (socle ADR-0031).

Ne contient que ce qui est **strictement identique** d'un document à l'autre. Chaque adapter garde
sa mise en page, ses styles et ses tableaux : ils n'ont ni le même format ni la même orientation, et
les factoriser reviendrait à inventer un moteur de documents que personne n'a demandé (règle 12 —
l'infra reste simple).
"""

from __future__ import annotations


def echapper(texte: str) -> str:
    """Neutralise les caractères spéciaux du mini-HTML des `Paragraph` ReportLab (`&`, `<`, `>`).

    ⚠️ **Ne vaut que pour les `Paragraph`** : les cellules de `Table` sont dessinées telles quelles
    (`drawString`), sans parseur — les échapper afficherait « Dupont &amp; Cie ». Chaque adapter
    l'applique donc aux titres et en-têtes, **jamais** au contenu des tableaux. Factorisée en
    E06US004 sur la **3ᵉ copie verbatim**, et sur un invariant qui neutralise un **parseur de
    balisage** : ce n'est pas introduire un pattern, c'est déplacer trois lignes pures.
    """
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
