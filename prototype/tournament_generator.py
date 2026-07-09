from abc import ABC, abstractmethod
from typing import List

from tournament_tree import TreePrincipal, TreeLucky, TournamentTree


class Tournament(ABC):
    def __init__(self, _len_players):
        self.len_players = _len_players
        self.depth = 0
        self.bracket_tree = None
        self.main_tree: [TournamentTree] = None
        self.trees: List[TournamentTree] = []

    @abstractmethod
    def create_tournament(self):
        pass

    def _add_tree(self, _main_tree, _depth, _i=None):
        secondary_tree = _main_tree.add_secondary_tree()
        secondary_tree.nb_divide = _main_tree.nb_divide + 1
        secondary_tree.next_brackets = secondary_tree.create_branch(_depth, _main_tree.next_brackets, True)
        if _i is None:
            self.trees.append(secondary_tree)
        else:
            self.trees.insert(_i, secondary_tree)

    def display_tree(self, _brackets=None):
        if _brackets is None:
            self.bracket_tree = self.combine_tree()
            sorted_brackets = sorted(
                self.bracket_tree.values(),
                key=lambda bracket: (bracket.depth, bracket.tree_id, bracket.id)
            )
        else:
            sorted_brackets = sorted(
                _brackets,
                key=lambda bracket: (bracket.depth, bracket.tree_id, bracket.id)
            )
        for bracket in sorted_brackets:
            bracket.display()

    def combine_tree(self):
        return {key: value for tree in self.trees for key, value in tree.brackets_tree.items()}

    def get_brackets_tree_by_depth(self, _depth):
        if self.bracket_tree is None:
            self.bracket_tree = self.combine_tree()
        brackets_by_rank = [bracket for bracket in self.bracket_tree.values() if bracket.depth == _depth]
        return brackets_by_rank

    def max_depth_in_dict(self):
        max_depth = None
        for key, value in self.bracket_tree.items():
            if hasattr(value, 'depth'):
                if max_depth is None or value.depth > max_depth:
                    max_depth = value.depth

        return max_depth


class TournamentFullElimination(Tournament):
    def __init__(self, _len_players, _num_winners):
        super().__init__(_len_players)
        self.main_tree = TreePrincipal(1, _num_winners)
        self.trees = [self.main_tree]

    def create_tournament(self):
        self.depth += 1
        self.main_tree.next_brackets = self.main_tree.create_branch(self.depth, self.len_players)
        while len(self.main_tree.next_brackets) > self.main_tree.num_winners:
            self.depth += 1
            self.main_tree.next_brackets = self.main_tree.create_next_branches(self.depth)


class TournamentSecondChance(Tournament):
    def __init__(self, _len_players, _nb_winner, _nb_lucky):
        super().__init__(_len_players)
        self.main_tree = TreePrincipal(1, _nb_winner)
        self.luckyTree = TreeLucky(2, _nb_lucky)
        self.trees = [self.main_tree, self.luckyTree]
        self.repechage_round = True

    def create_tournament(self):
        # tour 1 -> uniquement principal
        self.depth += 1
        self.main_tree.next_brackets = self.main_tree.create_branch(self.depth, self.len_players)
        # tour 2
        self.depth += 1
        self.luckyTree.next_brackets = self.luckyTree.create_branch(self.depth, self.main_tree.next_brackets, True)
        self.main_tree.next_brackets = self.main_tree.create_next_branches(self.depth)

        while len(self.luckyTree.next_brackets) > self.luckyTree.num_winners:
            self.depth += 1
            self.luckyTree.secondary_turn = not self.luckyTree.secondary_turn
            if self.repechage_round:
                if self.luckyTree.secondary_turn:
                    if len(self.luckyTree.next_brackets) > self.main_tree.num_winners:
                        self.luckyTree.next_brackets = self.luckyTree.create_next_branches(self.depth,
                                                                                           self.main_tree.next_brackets)
                        self.main_tree.next_brackets = self.main_tree.create_next_branches(self.depth + 1)
                    else:
                        self.repechage_round = False
                        self.luckyTree.next_brackets = self.luckyTree.create_branch(self.depth)
                else:
                    self.luckyTree.next_brackets = self.luckyTree.create_branch(self.depth)
            else:
                self.luckyTree.next_brackets = self.luckyTree.create_branch(self.depth)


class TournamentNoElimination(TournamentSecondChance):
    def __init__(self, _len_players, _nb_winner, _nb_lucky):
        super().__init__(_len_players, _nb_winner, _nb_lucky)

    def create_tournament(self):
        # tour 1 -> uniquement principal
        self.depth += 1
        self.main_tree.next_brackets = self.main_tree.create_branch(self.depth, self.len_players)
        # tour 2 -> principale et premier lucky
        self.depth += 1
        self.luckyTree.next_brackets = self.luckyTree.create_branch(self.depth, self.main_tree.next_brackets, True)
        self.main_tree.next_brackets = self.main_tree.create_next_branches(self.depth)
        # tour 3 et +
        while len(self.luckyTree.next_brackets) > self.luckyTree.num_winners:
            self.depth += 1
            trees = self.trees[:]
            if len(trees[0].next_brackets) > trees[0].num_winners:
                for i in range(len(trees) - 1, 0, -1):
                    if i == len(trees) - 1:
                        self._add_tree(self.trees[i], self.depth + 1)
                    if len(trees[i - 1].next_brackets) > trees[i - 1].num_winners:
                        trees[i].next_brackets = trees[i].create_next_branches(self.depth, trees[i - 1].next_brackets)
                    else:
                        trees[i].create_branch(self.depth)
                self.depth += 1
                trees[0].next_brackets = trees[0].create_next_branches(self.depth)
            offset = 1
            for j in range(1,len(trees)):
                self._add_tree(trees[j], self.depth, j + offset)
                offset += 1
                trees[j].next_brackets = trees[j].create_branch(self.depth)

players = [i for i in range(1, 129)]
# tournament = TournamentFullElimination(len(players), 4)
# tournament = TournamentSecondChance(len(players), 4, 1)
tournament = TournamentNoElimination(len(players), 4, 1)

tournament.create_tournament()
tournament.display_tree()
for i in range(1, tournament.depth + 1):
    print()
    print("tour :",i)
    for tree in tournament.trees:
        count = 0
        brackets = tree.get_brackets_tree_by_depth(i)
        for bracket in brackets:
            count+=1
            print(bracket.tree_id, end=",")
        if count != 0:
            print()
            print(f"nb->{count}")
