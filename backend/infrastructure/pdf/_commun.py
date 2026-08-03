"""Ce que partagent les adapters PDF (socle ADR-0031).

Ne contient que ce qui est **strictement identique** d'un document à l'autre. Chaque adapter garde
sa mise en page, ses styles et ses tableaux : ils n'ont ni le même format ni la même orientation, et
les factoriser reviendrait à inventer un moteur de documents que personne n'a demandé (règle 12 —
l'infra reste simple).
"""

from __future__ import annotations


def echapper(texte: str) -> str:
    """Neutralise les caractères spéciaux du mini-HTML des `Paragraph` ReportLab (`&`, `<`, `>`).

    ⚠️ **Ne vaut que pour les `Paragraph`.** Les cellules de `Table` sont dessinées telles quelles
    (`drawString`), sans parseur : les échapper y afficherait « Dupont &amp; Cie » au lieu de
    « Dupont & Cie ». Chaque adapter applique donc cette fonction aux titres et en-têtes, et
    **jamais** au contenu des tableaux.

    **Factorisée en E06US004** (revue, axe A) : le palmarès en créait la **3ᵉ copie verbatim**
    (`listes_impression`, `documents_salle`, plus une variante dans `feuille_de_marque`). Le seuil
    du projet — 3ᵉ occurrence réelle — est franchi, et il l'est sur un invariant qui neutralise un
    **parseur de balisage** : quatre copies, c'est quatre endroits où l'une peut dériver et
    réintroduire l'injection de markup dans un document. Ce n'est pas « introduire un pattern »
    (donc ni ADR ni US dédiée) : c'est déplacer une fonction pure de trois lignes.
    """
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
