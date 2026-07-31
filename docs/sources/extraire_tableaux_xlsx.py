"""Extrait de `Tableaux.xlsx` la fixture de l'**oracle 120** (E05US010).

Le classeur est le **tournoi réel à 120 archers** dont `moteur-placement-lucky-loser.md` est la
rétro-ingénierie : c'est le seul oracle indépendant du moteur de placement (risque R1 du cahier des
charges technique). Le test `backend/tests/test_oracle_120_placement.py` compare ce que le moteur
produit à la fixture que ce script écrit — il ne lit **jamais** le classeur lui-même.

**Pourquoi une fixture dérivée plutôt qu'une lecture directe du `.xlsx` en test.** Lire un classeur
dans la suite demanderait `openpyxl` : une dépendance de production ajoutée pour un seul test, alors
que la règle 11 (parcimonie) l'interdit sans arbitrage. Le format `.xlsx` étant une archive ZIP de
documents XML, la stdlib suffit — mais ce décodage n'a pas sa place dans un test, où il ferait
dépendre le vert de la suite d'un binaire d'un mégaoctet. On l'extrait donc **une fois**, on
commite le résultat lisible, et on garde ce script pour pouvoir le refaire.

**Usage** (depuis la racine du dépôt, aucun paquet à installer) :

    python docs/sources/extraire_tableaux_xlsx.py

Écrit `backend/tests/donnees/oracle_120.json`. Le script est **idempotent** et n'est exécuté ni par
la suite de tests, ni par la CI : il ne tourne que lorsqu'on veut régénérer la fixture.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RACINE = Path(__file__).resolve().parents[2]
CLASSEUR = RACINE / "Tableaux.xlsx"
SORTIE = RACINE / "backend" / "tests" / "donnees" / "oracle_120.json"

# Onglets du classeur, désignés par leur **nom** et non par leur fichier : le mapping
# `nom d'onglet → sheetN.xml` passe par les relations du classeur et n'a rien d'intuitif (« TABLEAU
# 1 OK » porte `sheetId=2` et vit dans `sheet3.xml`). Un simple ré-enregistrement du fichier peut le
# permuter — et l'on extrairait alors la mauvaise feuille en silence.
ONGLET_PRINCIPAL = "TABLEAU 1 OK"
ONGLET_PLACEMENT = "TABLEAU 2 OK"

# Colonne des étiquettes de match du premier tour, et décalage de la colonne des occupants.
COLONNE_PREMIER_TOUR = 3
DECALAGE_OCCUPANT = 2

RE_MATCH = re.compile(r"^M\s*(\d+)$")
# ⚠️ La tolérance sur la fin de « Perdant »/« Gagnant » n'est pas de la coquetterie : le classeur
# porte une **coquille** — `Perdan443` au lieu de `Perdant M443` (onglet « TABLEAU 2 OK »), qui
# décrit la provenance du rang 38. Sans elle, ce rang disparaît de la fixture sans un mot.
RE_SOURCE = re.compile(r"^(Perdan|Gagnan)t?\s*M?\s*(\d+)$", re.IGNORECASE)
RE_ARCHER = re.compile(r"^Archer\s*(\d+)$")

# Comptes attendus, vérifiés à la main sur le classeur du 31/07/2026. Ce sont des **garde-fous
# d'extraction** : si l'un tombe, c'est le script (ou le classeur) qu'il faut regarder, pas le
# moteur. Sans eux, une mauvaise feuille produirait une fixture appauvrie en silence.
ATTENDU_MATCHS_PREMIER_TOUR = 64
ATTENDU_RANGS_TERMINAUX = 115  # rangs 6 à 120 : les rangs 1 à 5 sortent du Big Shoot Off
ATTENDU_MATCHS_TOTAL = 484
ATTENDU_DESCENTES = 32  # les 32 matchs du 1er niveau de placement (M97-M128)

# Colonne des étiquettes du 1er niveau de placement, et décalage de la colonne des entrants.
COLONNE_PLACEMENT = 5
DECALAGE_ENTRANT = 2


def _fichier_de_l_onglet(archive: zipfile.ZipFile, nom: str) -> str:
    """Résout `nom d'onglet` → `sheetN.xml` par les relations du classeur (jamais en dur)."""
    classeur = ET.fromstring(archive.read("xl/workbook.xml"))
    relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    cibles = {
        relation.get("Id"): relation.get("Target", "")
        for relation in relations
    }
    for feuille in classeur.iter(f"{NS}sheet"):
        if feuille.get("name") == nom:
            identifiant = feuille.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            return "xl/" + cibles.get(identifiant, "").lstrip("/")
    raise SystemExit(f"Onglet introuvable dans le classeur : « {nom} »")


def _cellules(archive: zipfile.ZipFile, feuille: str) -> dict[tuple[int, int], str]:
    """La feuille (chemin dans l'archive) sous forme `{(ligne, colonne): texte}`, colonnes dès 1."""
    chaines = [
        "".join(t.text or "" for t in si.iter(f"{NS}t"))
        for si in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(f"{NS}si")
    ]
    grille: dict[tuple[int, int], str] = {}
    for ligne in ET.fromstring(archive.read(feuille)).iter(f"{NS}row"):
        for cellule in ligne.findall(f"{NS}c"):
            reference = re.match(r"([A-Z]+)(\d+)", cellule.get("r", ""))
            if reference is None:
                continue
            colonne = 0
            for lettre in reference.group(1):
                colonne = colonne * 26 + (ord(lettre) - 64)
            valeur = cellule.find(f"{NS}v")
            if cellule.get("t") == "s" and valeur is not None and valeur.text is not None:
                texte = chaines[int(valeur.text)]
            elif cellule.get("t") == "inlineStr":
                texte = "".join(t.text or "" for t in cellule.iter(f"{NS}t"))
            elif valeur is not None:
                texte = valeur.text or ""
            else:
                continue
            texte = texte.strip().replace("\n", " ")
            if texte:
                grille[(int(reference.group(2)), colonne)] = texte
    return grille


def premier_tour(grille: dict[tuple[int, int], str]) -> list[list[int | None]]:
    """Les 64 appariements du premier tour, en **rangs d'ensemencement**.

    Chaque étiquette `Mxx` de la colonne du premier tour est suivie, deux colonnes à droite, des
    occupants (« Archer 65 » = le 65ᵉ du classement de qualification). La fenêtre de lecture d'un
    match est bornée par la ligne du match **suivant** : sans cette borne, un match adjacent est
    happé et un archer apparaît deux fois. Un seul occupant = un **bye** (le second est `None`).
    """
    etiquettes = sorted(
        (ligne, int(m.group(1)))
        for (ligne, colonne), texte in grille.items()
        if colonne == COLONNE_PREMIER_TOUR and (m := RE_MATCH.match(texte))
    )
    appariements: list[list[int | None]] = []
    for index, (ligne, _numero) in enumerate(etiquettes):
        fin = etiquettes[index + 1][0] if index + 1 < len(etiquettes) else ligne + 4
        occupants = [
            int(m.group(1))
            for l in range(ligne, fin)
            if (texte := grille.get((l, COLONNE_PREMIER_TOUR + DECALAGE_OCCUPANT)))
            and (m := RE_ARCHER.match(texte))
        ]
        if not occupants:
            raise SystemExit(f"Match M{_numero} sans occupant lisible — extraction à revoir.")
        appariements.append([occupants[0], occupants[1] if len(occupants) > 1 else None])
    return appariements


def descentes(grille: dict[tuple[int, int], str]) -> list[list[int]]:
    """Le **câblage de descente** : quels perdants du 1ᵉʳ tour s'affrontent dans chaque match du
    premier niveau de placement (`M97`-`M128`).

    C'est la *Règle R* écrite noir sur blanc dans le classeur — « Perdant M 62 » / « Perdant M 61 »
    en regard de `M98`. Sans cette extraction, l'oracle ne vérifie que la **partition** des rangs et
    reste **aveugle aux appariements** : permuter les entrants d'un sous-tableau ne déplace aucun
    rang quand le mieux classé gagne toujours. C'est ce qu'un relecteur adversarial a démontré par
    mutation testing sur la première version de l'oracle — trois mutants survivaient.

    Rend, pour chaque match de placement et dans l'ordre du classeur, les **numéros des matchs du
    1ᵉʳ tour** dont il reçoit les perdants. Un seul numéro = l'autre camp vient d'un match gagné
    d'office, qui n'a pas de perdant.
    """
    etiquettes = sorted(
        (ligne, int(m.group(1)))
        for (ligne, colonne), texte in grille.items()
        if colonne == COLONNE_PLACEMENT and (m := RE_MATCH.match(texte))
    )
    cablage: list[list[int]] = []
    for index, (ligne, _numero) in enumerate(etiquettes):
        fin = etiquettes[index + 1][0] if index + 1 < len(etiquettes) else ligne + 4
        amont = [
            int(m.group(2))
            for l in range(ligne, fin)
            if (texte := grille.get((l, COLONNE_PLACEMENT + DECALAGE_ENTRANT)))
            and (m := RE_SOURCE.match(texte))
            and m.group(1).lower().startswith("perdan")
        ]
        cablage.append(amont)
    return cablage


def rangs_terminaux(grilles: list[dict[tuple[int, int], str]]) -> dict[str, list[object]]:
    """La table `rang → (issue, match terminal)` — l'énoncé de la *Règle T* dans les données.

    Le classeur écrit, en tête de chaque colonne de finales de placement, le rang obtenu et sa
    provenance (`8` ← `Perdant M428`). Le nombre est à gauche de la provenance, sur la même ligne.
    """
    table: dict[str, list[object]] = {}
    for grille in grilles:
        for (ligne, colonne), texte in grille.items():
            source = RE_SOURCE.match(texte)
            if source is None:
                continue
            for decalage in (1, 2, 3):
                voisin = grille.get((ligne, colonne - decalage))
                if voisin is None:
                    continue
                if re.fullmatch(r"\d+", voisin) and 1 <= int(voisin) <= 120:
                    # `group(1)` vaut « Perdan »/« Gagnan » : la regex tolère la coquille du
                    # classeur, on recompose donc le mot entier.
                    issue = source.group(1).lower() + "t"
                    table[voisin] = [issue, int(source.group(2))]
                break
    return dict(sorted(table.items(), key=lambda kv: int(kv[0])))


def main() -> None:
    if not CLASSEUR.exists():
        raise SystemExit(f"Classeur introuvable : {CLASSEUR}")
    with zipfile.ZipFile(CLASSEUR) as archive:
        principal = _cellules(archive, _fichier_de_l_onglet(archive, ONGLET_PRINCIPAL))
        placement = _cellules(archive, _fichier_de_l_onglet(archive, ONGLET_PLACEMENT))

    appariements = premier_tour(principal)
    table = rangs_terminaux([principal, placement])
    cablage = descentes(placement)
    total = len(
        {
            int(m.group(1))
            for grille in (principal, placement)
            for texte in grille.values()
            if (m := RE_MATCH.match(texte))
        }
    )
    cites = [rang for paire in appariements for rang in paire if rang is not None]
    if sorted(cites) != list(range(1, 121)):
        raise SystemExit("Le premier tour extrait ne cite pas exactement les 120 archers.")
    for constate, attendu, quoi in (
        (len(appariements), ATTENDU_MATCHS_PREMIER_TOUR, "matchs de premier tour"),
        (len(table), ATTENDU_RANGS_TERMINAUX, "rangs terminaux"),
        (total, ATTENDU_MATCHS_TOTAL, "matchs au total"),
        (len(cablage), ATTENDU_DESCENTES, "matchs de premier niveau de placement"),
    ):
        if constate != attendu:
            raise SystemExit(f"Extraction douteuse : {constate} {quoi} au lieu de {attendu}.")

    fixture = {
        "_source": (
            "Tableaux.xlsx, onglets « TABLEAU 1 OK » et « TABLEAU 2 OK » (tournoi réel à 120 "
            "archers). Régénérer avec docs/sources/extraire_tableaux_xlsx.py — ne pas éditer à "
            "la main."
        ),
        "effectif": 120,
        "taille": 128,
        "matchs_du_classeur": total,
        "premier_tour": appariements,
        "descentes_premier_niveau": cablage,
        "rangs_terminaux": table,
    }
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(fixture, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    byes = [paire[0] for paire in appariements if paire[1] is None]
    print(f"{SORTIE.relative_to(RACINE)} : {len(appariements)} matchs, {len(byes)} byes "
          f"(seeds {sorted(byes)}), {len(table)} rangs terminaux", file=sys.stderr)


if __name__ == "__main__":
    main()
