from bracket import Bracket
from abc import ABC, abstractmethod


class TournamentTree(ABC):
    def __init__(self, _id, _num_winners):
        self.brackets_tree = {}
        self.id = _id
        self.depth = 0
        self.num_winners = _num_winners
        self.next_brackets = []
        self.child_count = 10
        self.nb_divide = 0

    @abstractmethod
    def create_branch(self, _depth, len_brackets):
        pass

    @abstractmethod
    def create_next_branches(self, _depth, _brackets=None):
        pass

    def display_tree(self, _brackets=None):
        if _brackets is None:
            sorted_brackets = sorted(
                self.brackets_tree.values(),
                key=lambda sorted_bracket: (bracket.depth, len(str(bracket.tree_id)), bracket.tree_id, bracket.id)
            )
        else:
            sorted_brackets = sorted(
                _brackets,
                key=lambda sorted_bracket: (bracket.depth, len(str(bracket.tree_id)), bracket.tree_id, bracket.id)
            )

        for bracket in sorted_brackets:
            bracket.display()

    def get_brackets_tree_by_depth(self, _depth):
        brackets_by_rank = [bracket for bracket in self.brackets_tree.values() if bracket.depth == _depth]
        return brackets_by_rank

    def child_name(self):
        self.child_count -= 1
        string_name = str(self.id) + str(self.child_count)
        return int(string_name)

    def add_secondary_tree(self):
        return TreeLucky(self.child_name(), 1)


class TreePrincipal(TournamentTree):
    def __init__(self, _id, _num_winners):
        super().__init__(_id, _num_winners)

    def create_branch(self, depth, _num_players):
        """utiliser pour la premiere branche
            elle cree des bracket en fonction d'un nombre"""
        next_brackets = []
        for i in range(_num_players):
            bracket_tmp = Bracket()
            bracket_tmp.tree_id = self.id
            bracket_tmp.depth = depth
            bracket_tmp.id = i + 1
            bracket_tmp.player = i + 1
            self.brackets_tree[bracket_tmp.position()] = bracket_tmp
            next_brackets.append(bracket_tmp)
        return next_brackets

    def create_next_branches(self, depth, _brackets=None):
        """
        utilisée a partir de la deuxieme branche, a partir des brackets precedente
        reference les nouvelle bracket sur les precedente
        """
        if _brackets is None:
            brackets = self.next_brackets
        else:
            brackets = _brackets
        next_brackets = []
        bracket_id = 1
        for i in range(0, len(brackets), 2):
            bracket_tmp = Bracket()
            bracket_tmp.tree_id = self.id
            bracket_tmp.depth = depth
            bracket_tmp.id = bracket_id
            bracket_id += 1
            brackets[i].next_bracket_win = bracket_tmp
            brackets[i + 1].next_bracket_win = bracket_tmp
            self.brackets_tree[bracket_tmp.position()] = bracket_tmp
            next_brackets.append(bracket_tmp)
        return next_brackets


class TreeLucky(TournamentTree):
    def __init__(self, _id, _num_winners):
        super().__init__(_id, _num_winners)
        self.secondary_turn = False
        self.secondary_tree = None
        self.nb_divide = 1

    def create_branch(self, _depth, _brackets=None, from_main=False):
        """utiliser pour la premiere branche
            elle cree des la moitie des bracket en fonction d'un nombre"""
        if _brackets is not None:
            brackets = _brackets
        else:
            brackets = self.next_brackets
        next_brackets = []
        bracket_id = 1

        for i in range(0, len(brackets), 2):
            bracket_tmp = Bracket()
            bracket_tmp.tree_id = self.id
            bracket_tmp.depth = _depth
            bracket_tmp.id = bracket_id
            bracket_id += 1
            if from_main:
                brackets[i].next_bracket_loose = bracket_tmp
                brackets[i + 1].next_bracket_loose = bracket_tmp
            else:
                brackets[i].next_bracket_win = bracket_tmp
                brackets[i + 1].next_bracket_win = bracket_tmp

            self.brackets_tree[bracket_tmp.position()] = bracket_tmp
            next_brackets.append(bracket_tmp)
        return next_brackets

    def create_next_branches(self, _depth, main_brackets=None):
        next_brackets = []

        bracket_id = 1
        for i in range(0, len(self.next_brackets), 2):
            bracket_tmp2 = Bracket()
            bracket_tmp2.tree_id = self.id
            bracket_tmp2.depth = _depth
            bracket_tmp2.id = bracket_id
            bracket_id += 1
            main_brackets[i].next_bracket_loose = bracket_tmp2
            main_brackets[i + 1].next_bracket_loose = bracket_tmp2
            self.brackets_tree[bracket_tmp2.position()] = bracket_tmp2
            next_brackets.append(bracket_tmp2)

            bracket_tmp = Bracket()
            bracket_tmp.tree_id = self.id
            bracket_tmp.depth = _depth
            bracket_tmp.id = bracket_id
            bracket_id += 1
            self.next_brackets[i].next_bracket_win = bracket_tmp
            self.next_brackets[i + 1].next_bracket_win = bracket_tmp
            self.brackets_tree[bracket_tmp.position()] = bracket_tmp
            next_brackets.append(bracket_tmp)

        return next_brackets
