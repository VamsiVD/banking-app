"""Shared value types for the banking schemas.

Both the account and transaction domains need these. Kept in one place so a
new schema file imports a type instead of re-declaring it — re-declaring is
how `Money`/`AccountNumber`/`Currency` ended up defined twice before this
split.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

# Money is Decimal, never float. 0.1 + 0.2 does not equal 0.3 in binary floating
# point, and a balance that drifts by a cent is a balance nobody can reconcile.
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]

AccountNumber = Annotated[str, Field(min_length=1, max_length=34)]
Currency = Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]

# Matches UserRow.id: the owning user's email, which doubles as their id.
UserId = Annotated[str, Field(min_length=1, max_length=255)]

# Amounts on a movement are strictly positive; direction is carried by type,
# never by a negative number. A "deposit of -50" should be impossible to express.
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
