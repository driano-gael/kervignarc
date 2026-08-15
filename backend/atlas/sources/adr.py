"""Lecture des ADR — le registre des décisions et le graphe qu'il forme déjà sans le savoir.

Les 83 ADR portent un en-tête à puces très régulier (`Statut`, `Date`, puis des relations) et,
pour 25 d'entre eux, une section « Porté dans le code par ». Le premier fait un graphe daté ; la
seconde fait une promesse **vérifiable**. Le vrai apport de ce module n'est pas de dessiner le
registre, c'est de confronter ce qu'il promet à ce que le dépôt contient.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from atlas import markdown
from atlas.modele import (
    AtlasSourceInvalide,
    Decision,
    Lien,
    Portage,
    Sens,
    TypeLien,
)
from atlas.normalisation import est_metadonnee, normaliser_statut, relation

FICHIER_ADR = re.compile(r"^(?P<numero>\d{4})-.+\.md$")
_ADR_CITE = re.compile(r"ADR-(\d{4})")
_US_CITEE = re.compile(r"E\d{2}US\d{3}")
_DATE_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
# 11 ADR sur 83 datent en `JJ/MM/AAAA` au lieu de l'ISO du reste du registre — dérive apparue
# vers ADR-0064. On accepte les deux et on normalise, mais l'écart est **signalé** (cf.
# `controles.py`) : le masquer reviendrait à laisser l'atlas cautionner l'incohérence qu'il
# est censé rendre visible.
_DATE_FR = re.compile(r"(?P<jour>\d{2})/(?P<mois>\d{2})/(?P<annee>\d{4})")


def _date_iso(brut: str, *, fichier: str) -> str:
    iso = _DATE_ISO.search(brut)
    if iso:
        return iso.group(0)
    francaise = _DATE_FR.search(brut)
    if francaise:
        return "-".join(francaise.group("annee", "mois", "jour"))
    raise AtlasSourceInvalide(
        f"{fichier} : date « {brut} » non reconnue (attendu AAAA-MM-JJ, ou JJ/MM/AAAA toléré)."
    )


_RACINES_DE_CODE = ("backend/", "frontend/", "docs/", "stories/", "epics/", ".github/", "atlas/")
# Fichiers de premier niveau qu'un ADR peut légitimement déclarer porter sa décision. Énumérés
# plutôt que devinés : un motif large attraperait de la prose (« le fichier `machin.md` »), et un
# faux chemin produit un « chemin disparu » **bloquant**. Liste à élargir au besoin.
_FICHIERS_RACINE = (
    ".pre-commit-config.yaml",
    ".gitattributes",
    "CLAUDE.md",
    "guide-architecture.md",
    "pyproject.toml",
)
_EXTENSIONS_VERIFIABLES = (".py", ".ts", ".tsx")

# Les sections « Porté dans le code par » citent un chemin puis, en prose, les symboles qu'il
# porte — sous des formes libres, et sous **deux structures** :
#     - `backend/domain/participant.py` — `Participant` (`genre` + `ref_id`, `frozen`) et…
#     | `backend/domain/phase.py` | le contrat de phase |
# D'où la lecture **par entrée** (puce OU ligne de tableau) : le premier accent grave qui
# ressemble à un chemin est la cible, les autres identifiants de la même entrée sont ses symboles.
_TOKEN = re.compile(r"`(?P<valeur>[^`\n]+)`")
_IDENTIFIANT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
# Notation compacte employée par ADR-0083 : `backend/domain/{phase,deroule_etape}.py`. La lire
# telle quelle fabriquerait des « chemins disparus » bloquants sur des modules qui existent.
_ACCOLADE = re.compile(r"^(?P<avant>[^{]*)\{(?P<liste>[^}]*)\}(?P<apres>.*)$")


def _est_chemin(token: str) -> bool:
    return token.startswith(_RACINES_DE_CODE) or token in _FICHIERS_RACINE


def _developper(chemin: str) -> list[str]:
    """Développe `a/{x,y}.py` en `a/x.py` et `a/y.py` ; rend `[chemin]` s'il n'y a rien à faire."""
    accolade = _ACCOLADE.match(chemin)
    if not accolade:
        return [chemin]
    avant, apres = accolade.group("avant"), accolade.group("apres")
    return [
        developpe
        for morceau in accolade.group("liste").split(",")
        if morceau.strip()
        for developpe in _developper(f"{avant}{morceau.strip()}{apres}")
    ]


def _cibles_adr(valeur: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_ADR_CITE.findall(valeur)))


def _liens(champs: list[tuple[str, str]], *, fichier: str) -> tuple[Lien, ...]:
    """Traduit l'en-tête en arêtes normalisées.

    Un champ de relation dont la valeur ne cite aucun ADR n'est pas une anomalie : plusieurs ADR
    amendent une *story* ou un document (`Amende : stories/E02-inscriptions.md`). Ces valeurs ne
    portent simplement pas d'arête dans le graphe des décisions.
    """
    trouves: list[Lien] = []
    for libelle, valeur in champs:
        if est_metadonnee(libelle):
            continue
        type_lien, sens = relation(libelle, fichier=fichier)
        if type_lien is TypeLien.CODE:
            continue
        cibles = (
            tuple(dict.fromkeys(_US_CITEE.findall(valeur)))
            if type_lien is TypeLien.US
            else _cibles_adr(valeur)
        )
        trouves.extend(
            Lien(type=type_lien, sens=sens, cible=cible, libelle=libelle) for cible in cibles
        )
    return tuple(trouves)


def _portage(texte: str, champs: list[tuple[str, str]], racine: Path) -> tuple[Portage, ...]:
    """Les modules qu'un ADR déclare porter sa décision, et l'état réel de chacun.

    Deux formes coexistent dans le registre : une section `## Porté dans le code par` (24 ADR) et
    un champ d'en-tête du même nom (1 ADR). On lit les deux — préférer l'une reviendrait à ne pas
    voir un quart des promesses.
    """
    brut = markdown.section(texte, "Porté dans le code par")
    brut += "\n" + "\n".join(f"- {v}" for libelle, v in champs if "code par" in libelle.lower())

    # Un même module peut être cité par plusieurs entrées (ADR-0083 nomme `poule.py` quatre fois,
    # à chaque fois pour un rôle différent) : on **fusionne** les symboles au lieu d'ignorer les
    # entrées suivantes, sinon les promesses des puces 2 à 4 disparaissaient sans bruit.
    promesses: dict[str, list[str]] = {}
    for entree in _entrees(brut):
        tokens = _TOKEN.findall(entree)
        cites = [t for t in tokens if _est_chemin(t)]
        if not cites:
            continue
        chemins = _developper(cites[0])
        # Les identifiants d'US cités dans la même entrée (« …, E13US002 ») ne sont pas des
        # symboles : les garder ferait dire au contrôle qu'un module « ne contient pas E13US002 »,
        # ce qui est vrai et sans intérêt. Du bruit dans un signal finit par le rendre inaudible.
        promis = [
            t
            for t in tokens
            if t not in cites and _IDENTIFIANT.match(t) and not _US_CITEE.fullmatch(t)
        ]
        for chemin in chemins:
            promesses.setdefault(chemin, []).extend(promis)

    portes: list[Portage] = []
    for chemin in sorted(promesses):
        cible = _cible_sure(racine, chemin)
        symboles = tuple(dict.fromkeys(promesses[chemin]))
        existe = cible is not None and cible.exists()
        verifiable = existe and cible is not None and _lisible(cible)
        portes.append(
            Portage(
                chemin=chemin,
                existe=existe,
                symboles=symboles,
                symboles_absents=(
                    _symboles_absents(cible, symboles)
                    if verifiable and cible is not None
                    else (() if existe else symboles)
                ),
                verifiable=verifiable or not symboles,
            )
        )
    return tuple(portes)


def _cible_sure(racine: Path, chemin: str) -> Path | None:
    """Le chemin absolu, ou `None` s'il sort de l'arbre du dépôt.

    Le chemin vient d'un ADR — donc d'une source versionnée et relue —, mais rien n'empêche
    `backend/../../secrets.py` de franchir le filtre de préfixe. Une borne coûte deux lignes ;
    l'absence de borne fait de l'atlas un oracle « telle chaîne figure-t-elle dans tel fichier
    de la machine ».
    """
    cible = (racine / chemin).resolve()
    return cible if cible.is_relative_to(racine.resolve()) else None


def _lisible(cible: Path) -> bool:
    return cible.is_file() and cible.suffix in _EXTENSIONS_VERIFIABLES


def _entrees(section: str) -> list[str]:
    """Découpe une section en entrées : puces Markdown **et** lignes de tableau.

    Le registre a adopté le tableau en cours de route (ADR-0079, 0081, 0083) sans que personne
    ne le décide : ne lire que les puces perdait **un tiers des promesses**, en silence, et la
    fiche affichait « cette décision ne nomme aucun module » sur les trois ADR les plus rigoureux
    du dépôt. C'est précisément le « parseur qui devine et finit par affirmer » que ce module
    s'interdit ailleurs.
    """
    entrees: list[list[str]] = []
    tableau: list[str] = []

    def vider_tableau() -> None:
        # Une ligne de séparation (`|---|---|`) marque la ligne précédente comme en-tête : les
        # deux se jettent, le reste est du contenu.
        lignes = tableau[2:] if len(tableau) >= 2 and _est_separateur(tableau[1]) else tableau
        entrees.extend([ligne] for ligne in lignes)
        tableau.clear()

    for ligne in section.split("\n"):
        nue = ligne.strip()
        if nue.startswith("|"):
            tableau.append(nue)
            continue
        vider_tableau()
        if nue.startswith(("- ", "* ")) and not ligne.startswith((" ", "\t")):
            entrees.append([nue])
        elif entrees and nue:
            entrees[-1].append(nue)
    vider_tableau()
    return [" ".join(morceaux) for morceaux in entrees]


def _est_separateur(ligne: str) -> bool:
    return set(ligne) <= set("|-: ")


def _symboles_absents(cible: Path, symboles: tuple[str, ...]) -> tuple[str, ...]:
    """Parmi les symboles promis, ceux qui ne figurent pas dans le fichier.

    Contrôle volontairement grossier — une recherche de nom, pas une analyse. Il attrape le cas
    qui compte (un ADR promettant une classe qui n'existe pas) sans prétendre vérifier que le
    module **fait** ce que l'ADR annonce. Cette limite est assumée, affichée, et c'est pourquoi
    le résultat est un signal et non un blocage.
    """
    source = markdown.lire(cible)
    return tuple(s for s in symboles if s.rsplit(".", 1)[-1] not in source)


def _champ(champs: list[tuple[str, str]], nom: str, *, fichier: str) -> str:
    for libelle, valeur in champs:
        if libelle.strip().lower() == nom:
            return valeur
    raise AtlasSourceInvalide(
        f"{fichier} : champ d'en-tête « {nom.capitalize()} » absent. "
        f"Tout ADR porte au minimum « Statut » et « Date » dans son en-tête à puces."
    )


def lire_decision(chemin: Path, racine: Path) -> Decision:
    texte = markdown.lire(chemin)
    fichier = chemin.relative_to(racine).as_posix()
    champs = markdown.entete_a_puces(texte)

    statut_brut = _champ(champs, "statut", fichier=fichier)
    statut, remplace_par = normaliser_statut(statut_brut, fichier=fichier)

    brut_date = _champ(champs, "date", fichier=fichier)
    numero = chemin.name[:4]
    titre_brut = markdown.titre(texte)
    # Les titres d'ADR séparent le numéro par un tiret cadratin, parfois demi-cadratin : les deux
    # sont voulus ici, d'où la levée de l'avertissement « caractère ambigu ».
    titre_court = re.sub(r"^ADR-\d{4}\s*[—–-]\s*", "", titre_brut).strip()  # noqa: RUF001

    return Decision(
        identifiant=numero,
        titre=titre_court or titre_brut,
        statut=statut,
        statut_brut=statut_brut,
        remplace_par=remplace_par,
        date=_date_iso(brut_date, fichier=fichier),
        date_brute=brut_date,
        fichier=fichier,
        liens=_liens(champs, fichier=fichier),
        portage=_portage(texte, champs, racine),
        us=tuple(sorted(set(_US_CITEE.findall(texte)))),
        extrait=markdown.tronquer(markdown.en_clair(markdown.section(texte, "Décision")), 700),
    )


def lire_decisions(racine: Path) -> tuple[Decision, ...]:
    """Toutes les décisions, triées par identifiant — l'ordre de sortie ne doit rien au disque."""
    dossier = racine / "docs" / "adr"
    fichiers = sorted(f for f in dossier.iterdir() if FICHIER_ADR.match(f.name))
    decisions = [lire_decision(f, racine) for f in fichiers]
    return tuple(_avec_amendements_entrants(decisions))


def _avec_amendements_entrants(decisions: list[Decision]) -> list[Decision]:
    """Retourne le graphe : chaque décision apprend qui l'amende.

    C'est le calcul qui répond à la question posée — « cette décision tient-elle encore ? ». Le
    champ `Statut` ne le dit pas : **82 ADR sur 83 sont `Accepté`** et un seul est marqué
    `Remplacé`. La péremption réelle est partielle et implicite, portée par les 42 arêtes
    « Amende », et elle n'est écrite **sur aucune des deux fiches concernées**.
    """
    entrants: dict[str, set[str]] = {d.identifiant: set() for d in decisions}
    for decision in decisions:
        for lien in decision.liens:
            if lien.type not in (TypeLien.AMENDE, TypeLien.REMPLACE):
                continue
            if lien.sens is Sens.SORTANT and lien.cible in entrants:
                entrants[lien.cible].add(decision.identifiant)
            elif lien.sens is Sens.ENTRANT and decision.identifiant in entrants:
                entrants[decision.identifiant].add(lien.cible)
    return [
        dataclasses.replace(d, amende_par=tuple(sorted(entrants[d.identifiant]))) for d in decisions
    ]
