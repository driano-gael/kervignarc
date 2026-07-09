import random
from blason import Blason
from faker import Faker
from organisation import Organisation
from player import Player
from round import Round
from tableau import Tableau

########################################################################################

DEFAULTBLASON = [
    # Blason(size=1, capacity=4, name="big"),
    # Blason(size=0.5, capacity=2, name="medium"),
    # Blason(size=0.25, capacity=1, name="normal"),
    Blason(size=0.25, capacity=4, name="trispot")
]
fake = Faker()
players = [Player(fake.last_name(), DEFAULTBLASON[random.randint(0, len(DEFAULTBLASON)-1)].clone())
           for _ in range(random.randrange(100, 120))]
           #for _ in range(4)]

print(f"nombre d'inscrit: {len(players)}")
organisation = Organisation(_players=players)
organisation.parsePlayers()
organisation.showTarget()

print(f"#### ORGANISATION DU TABLEAU PRINCIPAL #######")
tableau = Tableau(players)
tableau.parse_player()



# round = Round(players)
# round.play_round()
# round.len_winners = 1
# round.winners_exist()
# print(round.loosers)

