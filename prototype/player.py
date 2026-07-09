from blason import Blason

class Player:
    def __init__(self, _name:str, _blason:Blason, _jdoe:bool = False):
        self.name = _name
        self.blason = _blason
        self.lettre = ""
        self.idCible = 0
        self.round_score = 0
        self.score = 0
        self.jdoe = _jdoe
        self.rank_round = 0

    @classmethod
    def doe(cls):
        return Player("doe", Blason.fake(), True)

    @classmethod
    def list_doe(cls, n):
        return [Player.doe() for _ in range(n)]
