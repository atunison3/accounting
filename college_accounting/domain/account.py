class Account:
    def __init__(self, number: int, name: str):

        if not isinstance(number, int):
            raise TypeError('Invalid number type')
        if not isinstance(name, str):
            raise TypeError('Invalid name type')

        if number < 100:
            raise ValueError('Account number must be greater than 99')

        self.number = number
        self.name = name 
        self.type_ = leading_digit(number)

    def __repr__(self):
        return f'''{self.number} {self.name}'''