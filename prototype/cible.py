
class Cible:
    key_blasons = "blasons"
    key_joueurs = "joueurs"
    def __init__(self, _id):
        self.id = _id
        self.len_players = 2 # nombre de joueur admis sur la cible
        self.letters = ["A", "C", "B", "D"]
        self.len_place = 1 # ratio de place pour les blasons
        self.player_placement = {}  # {"blasons" : Blason[], "joueurs": Joueur[]}

    def placePlayer(self, players):
        # place le premier blason
        all_placed = True
        i_joueur = 0
        blason = players[i_joueur].blason.clone()
        self.len_place -= blason.size
        players[i_joueur].lettre = self.letters[i_joueur]
        blason.capacity -= 1
        joueurs = [players[i_joueur]]
        blasons = [blason]

        # et on passe au deuxieme joueur
        for i in range(1, self.len_players):
            i_joueur = i
            if i_joueur >= len(players):
                break
            # verifie la dispnibilité du blason et si le joueur a le meme blason
            if blason.capacity > 0 and players[i_joueur].blason.id == blason.id :
                # s'il y a de la place sur le blason, on enregistre le joueur
                players[i_joueur].lettre = players[i_joueur].lettre = self.letters[i_joueur]
                joueurs.append(players[i_joueur])
                blason.capacity -= 1
                # et on passe au suivant
                continue
            else:
                # sinon on teste le blason du nouveau joueur
                blason = players[i_joueur].blason.clone()
                self.len_place -= blason.size
                # si le blason passe dans la cible
                if self.len_place >= 0:
                    # on enregistre le blason et le joueur
                    blasons.append(blason)
                    players[i_joueur].lettre = players[i_joueur].lettre = self.letters[i_joueur]
                    joueurs.append(players[i_joueur])
                    # et on passe au suivant
                    continue
                else:
                    all_placed = False
                    break
        # avant de quitter la fonction on enregistre dans le dictionnaire et on renvoie la valeur de i
        self.player_placement[self.key_blasons] = blasons
        self.player_placement[self.key_joueurs] = joueurs
        if all_placed:
            i_joueur += 1
        return i_joueur

    def showplacement(self):
        ordered_list = sorted(self.player_placement[self.key_joueurs], key=lambda joueur: (joueur.blason.size, joueur.blason.id))
        for player in ordered_list:
            print(f"\t{player.lettre}: {player.id} -- {player.blason.id}/{player.blason.capacity}")

