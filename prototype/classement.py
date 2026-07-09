import random as rnd

class Joueur:
    def __init__(self, _id):
        self.id = _id
        self.score = {}  # Les scores par round

def jouer_un_round(joueurs, round_num):
    """
    Génère un score aléatoire pour chaque joueur pour le round donné.
    """
    for joueur in joueurs:
        joueur.score[str(round_num)] = rnd.randint(0, 30)

def trier_joueurs(joueurs, round_num):
    """
    Trie les joueurs par score décroissant pour le round donné.
    """
    joueurs.sort(key=lambda joueur: joueur.score[str(round_num)], reverse=True)

def classer_joueurs(joueurs, round_num):
    """
    Classe les joueurs en fonction de leurs scores et gère les égalités.
    Retourne un dictionnaire où les clés sont les positions et les valeurs
    sont des listes de joueurs.
    """
    sorted_players = {}
    score = joueurs[0].score[str(round_num)]
    place = 1

    for i, joueur in enumerate(joueurs):
        if joueur.score[str(round_num)] != score:
            score = joueur.score[str(round_num)]
            place = i + 1

        if str(place) not in sorted_players:
            sorted_players[str(place)] = []
        sorted_players[str(place)].append(joueur)

    return sorted_players

def gerer_egalites(sorted_players, round_num):
    """
    Gère les égalités en rejouant des manches pour les joueurs à égalité.
    Met à jour le classement avec de nouvelles positions.
    """
    egalites = False
    for k, v in list(sorted_players.items()):
        if len(v) > 1:  # Si plusieurs joueurs sont à égalité
            egalites = True
            jouer_un_round(v, round_num)  # Rejouer pour les joueurs concernés
            trier_joueurs(v, round_num)  # Trier les joueurs après le départage

            # Supprimer l'ancienne position
            del sorted_players[k]

            # Réattribuer les places après le départage
            sub_score = v[0].score[str(round_num)]
            sub_place = int(k)
            for i, joueur in enumerate(v):
                if joueur.score[str(round_num)] != sub_score:
                    sub_score = joueur.score[str(round_num)]
                    sub_place += 1

                if str(sub_place) not in sorted_players:
                    sorted_players[str(sub_place)] = []
                sorted_players[str(sub_place)].append(joueur)

    return sorted_players, egalites

def afficher_classement(sorted_players, round_num):
    """
    Affiche le classement des joueurs.
    """
    print(f"\n(Round {round_num}):")
    for place, joueurs in sorted(sorted_players.items(), key=lambda x: int(x[0])):
        print(f"Place {place}: " + ", ".join(
            f"Joueur {joueur.id} (Scores: {joueur.score})" for joueur in joueurs
        ))

def tournoi(joueurs):
    """
    Gère le déroulement complet du tournoi.
    """
    round_num = 1
    jouer_un_round(joueurs, round_num)
    trier_joueurs(joueurs, round_num)

    # Premier classement
    sorted_players = classer_joueurs(joueurs, round_num)
    afficher_classement(sorted_players, round_num)

    # Gérer les égalités jusqu'à ce que tout le monde soit bien classé
    egalites = True
    while egalites:
        round_num += 1
        sorted_players, egalites = gerer_egalites(sorted_players, round_num)
        afficher_classement(sorted_players, round_num)
    print(f"\nTournoi terminé après {round_num} rounds.")

# Initialisation des joueurs
joueurs = [Joueur(i + 1) for i in range(128)]

# Lancer le tournoi
tournoi(joueurs)
