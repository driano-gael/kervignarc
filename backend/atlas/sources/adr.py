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
_EXTENSIONS_VERIFIABLES = (".py", ".ts", ".tsx")

# Les sections « Porté dans le code par » sont des listes à puces dont chaque entrée cite un
# chemin puis, en prose, les symboles qu'il porte — sous des formes libres :
#     - `backend/domain/participant.py` — `Participant` (`genre` + `ref_id`, `frozen`) et…
#     - `backend/domain/deroule_etape.py` (`EtapeDeroule`)
# D'où la lecture **par puce** : le premier accent grave qui ressemble à un chemin est la cible,
# les autres identifiants entre accents graves de la même puce en sont les symboles promis.
_TOKEN = re.compile(r"`(?P<valeur>[^`\n]+)`")
_IDENTIFIANT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


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

    portes: list[Portage] = []
    vus: set[str] = set()
    for puce in _puces(brut):
        tokens = _TOKEN.findall(puce)
        chemins = [t for t in tokens if t.startswith(_RACINES_DE_CODE)]
        if not chemins or chemins[0] in vus:
            continue
        chemin = chemins[0]
        vus.add(chemin)
        cible = racine / chemin
        existe = cible.exists()
        # Les identifiants d'US cités dans la même puce (« …, E13US002 ») ne sont pas des
        # symboles : les garder ferait dire au contrôle qu'un module « ne contient pas E13US002 »,
        # ce qui est vrai et sans intérêt. Du bruit dans un signal finit par le rendre inaudible.
        symboles = tuple(
            dict.fromkeys(
                t
                for t in tokens
                if t != chemin and _IDENTIFIANT.match(t) and not _US_CITEE.fullmatch(t)
            )
        )
        portes.append(
            Portage(
                chemin=chemin,
                existe=existe,
                symboles=symboles,
                symboles_absents=_symboles_absents(cible, symboles) if existe else symboles,
            )
        )
    return tuple(portes)


def _puces(section: str) -> list[str]:
    """Découpe une liste Markdown en puces, continuations indentées recollées."""
    puces: list[list[str]] = []
    for ligne in section.split("\n"):
        if ligne.lstrip().startswith(("- ", "* ")) and not ligne.startswith((" ", "\t")):
            puces.append([ligne.strip()])
        elif puces and ligne.strip():
            puces[-1].append(ligne.strip())
    return [" ".join(morceaux) for morceaux in puces]


def _symboles_absents(cible: Path, symboles: tuple[str, ...]) -> tuple[str, ...]:
    """Parmi les symboles promis, ceux qui ne figurent pas dans le fichier.

    Contrôle volontairement grossier — une recherche de nom, pas une analyse. Il attrape le cas
    qui compte (un ADR promettant une classe qui n'existe pas) sans prétendre vérifier que le
    module **fait** ce que l'ADR annonce. Cette limite est assumée, affichée, et c'est pourquoi
    le résultat est un signal et non un blocage.
    """
    if not cible.is_file() or cible.suffix not in _EXTENSIONS_VERIFIABLES:
        return ()
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
