from cible import Cible


class Organisation:
    def __init__(self, _players):
        self.players = _players
        self.Target = 30
        self.cible_placement = {}  # {"cible_id": Cible}
        self.unplaced_players = []

    def organiseCible(self):
        self.sortPlayers()
        self.parsePlayers()

    def sortPlayers(self):
        self.players = sorted(self.players, key=lambda joueur: (joueur.blason.size, joueur.blason.id, joueur.id), reverse=True)

    def parsePlayers(self):
        self.sortPlayers()
        if not self.players or self.Target <= 0:
            return

        i_current_player = 0
        for i in range(1, self.Target+1):
            #  s'il n'y a plus de joueur a placer on sort de la boucle
            if i_current_player >= len(self.players):
                break
            # instancie la cible avec son id
            cible = Cible(i)
            # place les joueur sur la cible
            i_current_player += cible.placePlayer(self.players[i_current_player:])
            # range le placement de la cible dans le dictionnaire
            self.cible_placement[str(i)] = cible
        print(f"i_current_player: {i_current_player}, nbplayer: {len(self.players)}")

    def showTarget(self):
        for k,v in self.cible_placement.items():
            print(f"cible : {k}")
            v.showplacement()

