"""Service applicatif Clubs — CRUD du référentiel des clubs (E02US001).

Orchestre le domaine derrière le port `ClubRepository`. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le référentiel est **global** (aucun tournoi en paramètre) : les clubs sont réutilisés d'une
compétition à l'autre.

**Unicité du nom.** Le domaine ne voit qu'un club à la fois, jamais la collection : c'est donc
ici qu'on refuse un doublon (`NomClubDejaPris`), avec une contrainte `UNIQUE` en base comme
garde-fou d'intégrité. Le contrôle « le nom est-il libre ? » puis l'insertion ne peuvent pas
s'entrelacer : toutes les écritures passent par la **file du writer unique** (ADR-0005), qui
les sérialise — le classique problème de concurrence entre la vérification et l'écriture ne se
pose donc pas ici.

**Suppression d'un club utilisé.** Refusée (`ClubReference` → 409), sur le patron de
`ServiceBlasons.supprimer` / `BlasonReference` (E01US006) : on refuse plutôt que de cascader
silencieusement sur des inscriptions. La règle est **exerçable** parce que la même US pose
`archer.club_id` — sans ce lien, elle n'aurait pu se vérifier que contre le vide.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from application.erreurs import ClubIntrouvable, ClubReference, NomClubDejaPris
from domain.club import Club, ClubId, cle_nom
from domain.erreurs import NomClubInvalide
from domain.ports import ArcherRepository, ClubRepository


@dataclass(frozen=True)
class RapportImportClubs:
    """Compte-rendu d'un import en masse (E01US023) — **aucun import partiel silencieux**.

    Trois issues par ligne, et elles doivent rester distinctes à l'écran : un club **créé**, un
    **doublon** ignoré (déjà au référentiel, ou répété dans le collage lui-même) et une ligne
    **rejetée** (vide après normalisation). Un import qui ne rendrait qu'un total laisserait
    l'organisateur croire à un échec là où il n'y a que du déjà-connu.
    """

    crees: list[str] = field(default_factory=list)
    doublons: list[str] = field(default_factory=list)
    lignes_ignorees: int = 0


class ServiceClubs:
    """Cas d'usage du référentiel des clubs : créer, lister, renommer, supprimer, importer."""

    def __init__(self, clubs: ClubRepository, archers: ArcherRepository) -> None:
        self._clubs = clubs
        self._archers = archers

    def creer(self, nom: str) -> Club:
        """Ajoute un club au référentiel.

        Lève `NomClubInvalide` (domaine) si le nom est vide, `NomClubDejaPris` si un club porte
        déjà ce nom au sens de `cle_nom` (espaces de bord, casse **et accents** repliés).
        """
        club = Club.creer(nom)
        self._exiger_nom_libre(club.nom)
        return self._clubs.ajouter(club)

    def lister(self) -> list[Club]:
        """Renvoie tout le référentiel, trié par nom (ordre d'affichage attendu à l'écran).

        Trie sur `cle_nom`, la clé qui sert aussi à refuser les homonymes : casse **et** accents
        repliés. Un tri sur le nom brut classerait par code point, donc « Élan » après « Zénith »
        — les clubs accentués s'entasseraient en fin de liste, dans l'écran même où l'utilisateur
        cherche le sien à l'œil.
        """
        return sorted(self._clubs.lister(), key=lambda club: cle_nom(club.nom))

    def importer(self, lignes: str) -> RapportImportClubs:
        """Alimente le référentiel **en masse** depuis une liste collée — une ligne, un club.

        Sert le patrimoine du club (E01US023) : les clubs voisins reviennent d'une compétition à
        l'autre, et les saisir un à un est la corvée que le référentiel existe pour supprimer.

        **Ne pas confondre avec E02US007**, l'import des *inscrits* depuis un fichier fédéral :
        celui-là crée archers, clubs et départs **d'un tournoi**, avec ses propres pièges (quota
        d'un départ, homonymes, licence). Ici il n'y a qu'un référentiel global à peupler.

        Le doublon s'entend au sens de `domain.club.cle_nom` — casse, accents et espaces de bord
        repliés — **comme la saisie unitaire** : un import ne doit pas ouvrir une porte que le
        formulaire ferme, sinon c'est par lui qu'entreront les « Élan de Fougères » / « elan de
        fougeres » que `creer` refuse. La déduplication couvre aussi les répétitions **internes** au
        collage, qui sont le cas le plus fréquent quand on colle deux listes bout à bout.

        Ne lève pas sur une ligne fautive : une ligne vide est **comptée**, pas fatale. C'est la
        promesse « aucun import partiel silencieux » — on va au bout et on rend le compte-rendu.
        """
        crees: list[str] = []
        doublons: list[str] = []
        ignorees = 0
        vus = {cle_nom(club.nom) for club in self._clubs.lister()}
        for ligne in lignes.splitlines():
            try:
                club = Club.creer(ligne)
            except NomClubInvalide:
                # Ligne vide ou blanche : le cas normal d'un collage (ligne de séparation, retour
                # final). On la compte pour que le total du rapport se raccorde au texte fourni.
                ignorees += 1
                continue
            if cle_nom(club.nom) in vus:
                doublons.append(club.nom)
                continue
            vus.add(cle_nom(club.nom))
            crees.append(self._clubs.ajouter(club).nom)
        return RapportImportClubs(crees=crees, doublons=doublons, lignes_ignorees=ignorees)

    def modifier(self, club_id: ClubId, nom: str) -> Club:
        """Renomme un club.

        Lève `ClubIntrouvable` si l'identifiant est inconnu, `NomClubInvalide` (domaine) si le
        nom est vide, `NomClubDejaPris` si un **autre** club porte déjà ce nom.
        """
        club = self._club_existant(club_id)
        renomme = club.modifier(nom)
        self._exiger_nom_libre(renomme.nom, sauf=club_id)
        return self._clubs.enregistrer(renomme)

    def supprimer(self, club_id: ClubId) -> None:
        """Retire un club du référentiel.

        Lève `ClubIntrouvable` si l'identifiant est inconnu, `ClubReference` si au moins un
        archer y est rattaché — **tous tournois confondus** : le référentiel étant global, un
        club utilisé par une compétition passée est utilisé tout court, et le supprimer
        laisserait une référence pendante dans l'historique.
        """
        club = self._club_existant(club_id)
        references = self._archers.par_club(club_id)
        if references:
            # Le **nom**, pas l'identifiant : ce message est lu par un bénévole, pas par un
            # développeur — et `_exiger_nom_libre` nomme déjà le club dans son propre refus.
            raise ClubReference(
                f"Le club « {club.nom} » est utilisé par {len(references)} archer(s) ; "
                "réaffectez-les avant de le supprimer."
            )
        self._clubs.supprimer(club_id)

    def _club_existant(self, club_id: ClubId) -> Club:
        club = self._clubs.par_id(club_id)
        if club is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        return club

    def _exiger_nom_libre(self, nom: str, sauf: ClubId | None = None) -> None:
        """Refuse un nom déjà porté par un autre club (`sauf` : le club en cours de renommage)."""
        homonyme = self._clubs.par_nom(nom)
        if homonyme is not None and homonyme.id != sauf:
            raise NomClubDejaPris(f"Un club nommé « {homonyme.nom} » existe déjà.")
