from datetime import datetime
from pydantic import BaseModel


def format_amount(value: float, print_day: bool = False) -> str:
    """Return formatted amount or blanks if zero."""
    return f"{value:9.2f}" if value else " " * 9


class JournalEntry(BaseModel):
    entry_id: int
    date: datetime
    description: str
    debits: list[tuple[str, int, float]]
    credits: list[tuple[str, int, float]]

    def print_to_terminal(self):

        debits = self.debits.copy()
        credits = self.credits.copy()

        def print_line(transaction: tuple, debit: bool, day: str = '  '):

            title = transaction[0]
            pr = transaction[1]
            if debit:
                dr = format_amount(transaction[2])
                cr = format_amount(0)
                line = f'    | {day:02} | {title:<79.79} | {pr} | {dr} | {cr}'
            else:
                cr = format_amount(transaction[2])
                dr = format_amount(0)
                line = f'    | {day:02} |   {title:<77.77} | {pr} | {dr} | {cr}'

            print(line)

        transaction = debits.pop(0)
        print_line(transaction, debit=True, day=self.date.day)
        while debits:
            transaction = debits.pop(0)
            print_line(transaction, debit=True)

        while credits:
            transaction = credits.pop(0)
            print_line(transaction, debit=False)

        dr = format_amount(0)
        cr = format_amount(0)
        print(f'    |    |    {self.description[:73]:<76.76} |     | {dr} | {cr}')
        print(f'''    |    |{' ' * 81}|     |           |          ''')

    def print_trial_balances(self, from_: datetime, to_: datetime, accounts: list = None):
        '''Prints the trial balance of selected accounts'''

        if not accounts:
            accounts = None
