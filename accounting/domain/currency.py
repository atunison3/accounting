"""Currency conversion rules used by accounting analytics."""

from decimal import Decimal, ROUND_HALF_UP

# The application currently supports a deliberately small, explicit rate table.
THB_PER_USD = Decimal("33")


def convert_currency(amount_cents: int, from_currency: str, to_currency: str = "USD") -> int:
    """Convert an integer-cent amount between supported currencies.

    The current fixed rate is 33 Thai baht to one US dollar.  Results are
    rounded to the nearest cent so analytics never use floating point money.
    """
    source = from_currency.upper()
    target = to_currency.upper()
    # TBH was used by an earlier website form; retain it as a legacy alias.
    source = "THB" if source == "TBH" else source
    target = "THB" if target == "TBH" else target
    if source == target:
        return amount_cents
    if {source, target} != {"USD", "THB"}:
        raise ValueError(f"Unsupported currency conversion: {source} to {target}")

    amount = Decimal(amount_cents)
    converted = amount / THB_PER_USD if source == "THB" else amount * THB_PER_USD
    return int(converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
