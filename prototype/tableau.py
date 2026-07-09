import math
import random
from player import Player

'''
ok 1 - savoir comment se deroule la finale (quel type de match)
'''
class Tableau:
    def __init__(self, _players):
        self.players = _players
        self.duel = {}

    def parse_player(self):
        self.__fake_scored_players()
        self.__sorted_players()
        self.__create_duel()

    # -----  PRIVATE  ------------------------------------#

    def __create_duel(self):
        # pour gerer le tableau initial j'ai besoin de connaitre le nombre a puissance 2 le plus proche
        closest = self.__closest_power_of_2()
        nb_duel = closest // 2
        self.players.extend(Player.list_doe(closest - len(self.players)))
        switch = True
        start_numduel = 0
        end_numduel = nb_duel + 1

        for i in range(nb_duel):
            switch = not switch
            if switch:
                start_numduel += 1
                id_duel = start_numduel
            else:
                end_numduel -= 1
                id_duel = end_numduel
            self.duel[id_duel] = (self.players[i], self.players[-(i+1)])

        self.duel = dict(sorted(self.duel.items(), key=lambda item: item[0]))
        for k, v in self.duel.items():
            print(f"Duel {k}: \t{v[0].id}, {v[0].round_score} VS {v[1].id}, {v[1].round_score} ")

    def __sorted_players(self):
        self.players = sorted(self.players, key=lambda player: player.round_score, reverse=True)

    def __fake_scored_players(self):
        eligible_players = [player for player in self.players if not player.jdoe]
        unique_scores = random.sample(range(1, 301), len(eligible_players))
        for player, score in zip(eligible_players, unique_scores):
            player.round_score = score

    def __closest_power_of_2(self):
        if len(self.players) <= 0:
            raise ValueError("Le nombre doit être positif.")
        return 2 ** math.ceil(math.log2(len(self.players)))  # Plus proche au-dessus

    def play_matchs(self):
        # for match in self.matchs:
        #     match.play_match()
        pass
