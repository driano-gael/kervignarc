import random as rnd

class Round:
    """docstring for Round"""
    def __init__(self, _players):
        self.number_round = 0 # numro du round
        self.victory_point = 2 #nombre de point pour le gagnant
        self.draw_point = 1 #nombre de point pour le gagnant
        self.loose_point = 0 #nombre de point pour le gagnant
        self.players = _players # joueurs sur le round
        self.type = ""
        self.len_winners = 0
        self.winners = []
        self.loosers = []
        self.egality_players = []

    def play_round(self):
        #joue le tour (enregistre les point des joueurs)
        for player in self.players:
            player.round_score += rnd.randint(0, 30)
        self.players.sort(key=lambda player: player.round_score, reverse=True)

    def sort_winners(self):
        # definit le score palier du gagnant
        baseScore = self.players[self.len_winners -1].round_score
        # range les joueurs
        for i in range(len(self.players)):
            if self.players[i].round_score > baseScore:
                self.winners.append(self.players[i])
            elif self.players[i].round_score == baseScore:
                self.egality_players.append(self.players[i])
            else:
                self.loosers.append(self.players[i])

class DualRound(Round):
    """docstring for DualRound"""
    def __init__(self, _players):
        super().__init__(_players)
        self.len_winners = 1

    def sort_winners(self):
        if self.players[0].round_score > self.players[1].round_score:
            self.winners.append(self.players[0])
            self.loosers.append(self.players[1])
        else:
            self.egality_players.append(self.players[0])
            self.egality_players.append(self.players[1])
