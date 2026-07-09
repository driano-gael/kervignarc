
class Blason:
    def __init__(self,size, capacity, name):
        self.size = size
        self.capacity = capacity
        self.name = name

    def clone(self):
        return Blason(size=self.size, capacity=self.capacity, name=self.name)

    @classmethod
    def fake(cls):
        return Blason(size=0, capacity=1,name="fake")


