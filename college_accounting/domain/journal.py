__all__ = [
    'Journal'
]

class Journal():
    def __init__(self, name: str):

        self.name = name
        self.lines = []