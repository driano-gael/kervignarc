class Bracket:
    def __init__(self):
        self.tree_id = None
        self.id = None
        self.depth = None
        self.last_bracket = None
        self.next_bracket_win = None
        self.next_bracket_loose = None
        self.player = None
        self.cible = None
        self.letter = None

    def display(self):
        print(f"TreeNode(id={self.id},"
              f" depth={self.depth},"
              f" tree={self.tree_id},"
              f" last_bracket={self.last_bracket},"
              f" next_bracket_win={self.next_bracket_win},"
              f" next_bracket_loose={self.next_bracket_loose},"
              f" player={self.player},"
              f" cible={self.cible},"
              f" letter={self.letter})")


    def position(self):
        return str(self.tree_id) + "_" + str(self.depth) + "_" +str(self.id)


    def __repr__(self):
        return f"node {str(self.tree_id)}_{self.depth}_{self.id}"


