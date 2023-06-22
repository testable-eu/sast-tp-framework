from pathlib import Path

class A:
    def __init__(self) -> None:
        self.path = Path(".")
        self.my_path = self.make_path('abc')
    
    def make_path(self, arg):
        yield self.path / arg


a = A()
print(a.path)
print(a.my_path)
a.path = Path('/')
print(a.path)
print(a.my_path.is_file())