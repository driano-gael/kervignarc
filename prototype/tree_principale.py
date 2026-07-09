# from typing import Optional, Dict, List
# from bracket import Bracket
# from abc import ABC, abstractmethod
#
#
# class TournamentTree(ABC):
#     def __init__(self):
#         self.brackets_tree = {}
#         self.players = None
#         self.name = None
#         self.depth = 0
#         self.num_winners = None
#         self.next_brackets = []
#
#     def display_tree(self, _brackets=None):
#         if _brackets is None:
#             sorted_brackets = sorted(
#                 self.brackets_tree.values(),
#                 key=lambda bracket: (bracket.depth, bracket.id)
#             )
#         else:
#             sorted_brackets = sorted(
#                 _brackets,
#                 key=lambda bracket: (bracket.depth, bracket.id)
#             )
#
#         for bracket in sorted_brackets:
#             bracket.display()
#
#     def get_brackets_tree_by_depth(self, _depth):
#         brackets_by_rank = [bracket for bracket in self.brackets_tree.values() if bracket.depth == _depth]
#         return brackets_by_rank
#
#
# class TreePrincipal(TournamentTree):
#     def __init__(self):
#         super().__init__()
#         self.name = "Main"
#
#     def create_tree(self):
#         self.depth += 1
#         self.next_brackets = self.create_main_branch(self.players)
#         while len(self.next_brackets) > self.num_winners:
#             self.depth += 1
#             self.next_brackets = self.create_next_branches()
#
#     def create_main_branch(self, depth):
#         next_brackets = []
#         bracket_id = 1
#         for player in self.players:
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             bracket_tmp.player = player
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#         return next_brackets
#
#     def create_next_branches(self, depth):
#         next_brackets = []
#         bracket_id = 1
#         for i in range(0, len(self.next_brackets), 2):
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             self.next_brackets[i].next_bracket_win = bracket_tmp
#             self.next_brackets[i + 1].next_bracket_win = bracket_tmp
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#         return next_brackets
#
#
# class TreeLucky(TournamentTree):
#     def __init__(self):
#         super().__init__()
#         self.name = "Lucky"
#         self.main_tree: Optional['TreePrincipal'] = None
#         self.main_depth = 1
#         self.secondary_turn = False
#         self.secondary_tree = None
#
#     def create_branch(self, _depth, _brackets=None, from_main=False):
#         if _brackets is not None:
#             brackets = _brackets
#         else:
#             brackets = self.next_brackets
#         next_brackets = []
#         bracket_id = 1
#
#         for i in range(0, len(brackets), 2):
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = _depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             if from_main:
#                 brackets[i].next_bracket_loose = bracket_tmp
#                 brackets[i + 1].next_bracket_loose = bracket_tmp
#             else:
#                 brackets[i].next_bracket_win = bracket_tmp
#                 brackets[i + 1].next_bracket_win = bracket_tmp
#
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#         return next_brackets
#
#     def create_branches_with_main(self, _depth, main_brackets):
#         next_brackets = []
#
#         bracket_id = 1
#         for i in range(0, len(self.next_brackets), 2):
#             bracket_tmp2 = Bracket()
#             bracket_tmp2.tree = self.name
#             bracket_tmp2.depth = _depth
#             bracket_tmp2.id = bracket_id
#             bracket_id += 1
#             main_brackets[i].next_bracket_loose = bracket_tmp2
#             main_brackets[i + 1].next_bracket_loose = bracket_tmp2
#             self.brackets_tree[bracket_tmp2.position()] = bracket_tmp2
#             next_brackets.append(bracket_tmp2)
#
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = _depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             self.next_brackets[i].next_bracket_win = bracket_tmp
#             self.next_brackets[i + 1].next_bracket_win = bracket_tmp
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#
#         return next_brackets
#
#
# class TreeSecondary(TournamentTree):
#     def __init__(self):
#         super().__init__()
#         self.name = "Secondary_"
#         self.parent_tree = None
#         self.child_tree = None
#
#     def create_branch(self, _depth, _brackets=None, from_main=False):
#         if _brackets is not None:
#             brackets = _brackets
#         else:
#             brackets = self.next_brackets
#         next_brackets = []
#         bracket_id = 1
#
#         for i in range(0, len(brackets), 2):
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = _depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             if from_main:
#                 brackets[i].next_bracket_loose = bracket_tmp
#                 brackets[i + 1].next_bracket_loose = bracket_tmp
#             else:
#                 brackets[i].next_bracket_win = bracket_tmp
#                 brackets[i + 1].next_bracket_win = bracket_tmp
#
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#         return next_brackets
#
#     def create_branches_with_main(self, _depth, main_brackets):
#         next_brackets = []
#
#         bracket_id = 1
#         for i in range(0, len(self.next_brackets), 2):
#             bracket_tmp2 = Bracket()
#             bracket_tmp2.tree = self.name
#             bracket_tmp2.depth = _depth
#             bracket_tmp2.id = bracket_id
#             bracket_id += 1
#             main_brackets[i].next_bracket_loose = bracket_tmp2
#             main_brackets[i + 1].next_bracket_loose = bracket_tmp2
#             self.brackets_tree[bracket_tmp2.position()] = bracket_tmp2
#             next_brackets.append(bracket_tmp2)
#
#             bracket_tmp = Bracket()
#             bracket_tmp.tree = self.name
#             bracket_tmp.depth = _depth
#             bracket_tmp.id = bracket_id
#             bracket_id += 1
#             self.next_brackets[i].next_bracket_win = bracket_tmp
#             self.next_brackets[i + 1].next_bracket_win = bracket_tmp
#             self.brackets_tree[bracket_tmp.position()] = bracket_tmp
#             next_brackets.append(bracket_tmp)
#
#         return next_brackets
