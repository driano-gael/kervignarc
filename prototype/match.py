'''

'''
from round import DualRound


class Match:
    def __init__(self, _players):
        self.players = _players
        self.winners = []
        self.loosers = []
        self.rounds = [DualRound(self.players),
                       DualRound(self.players),
                       DualRound(self.players)
                       ]
        self.point_to_win = 4

    def get_rounds(self):
        self.rounds.append(DualRound(self.players))
        self.rounds.append(DualRound(self.players))
        self.rounds.append(DualRound(self.players))

    def play_rounds(self):
        # for round in self.rounds:
        #     round.play_round()
        # self.get_winners()
        pass

    def get_winners(self):
        pass