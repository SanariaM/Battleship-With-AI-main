'''
This file defines simple ship configuration helpers.

The current game uses a classic Battleship-style fleet:
- Patrol Boat (2)
- Submarine (3)
- Destroyer (3)
- Battleship (4)
- Carrier (5)

The welcome screen still lets players choose 1 to 5 boats, but that choice now
selects the first N boats from the classic fleet instead of generating lengths
1 through N.
'''

# game/ships.py
# Battleship Project - ship configuration helpers
# Created: 2026-02-06

from dataclasses import dataclass
from typing import List


@dataclass
class Ship:
    """
    A ship is defined mainly by its length.
    We'll track its cells/hits later during gameplay.
    """
    length: int


@dataclass(frozen=True)
class ShipSpec:
    name: str
    length: int


CLASSIC_FLEET: List[ShipSpec] = [
    ShipSpec(name="Patrol Boat", length=2),
    ShipSpec(name="Submarine", length=3),
    ShipSpec(name="Destroyer", length=3),
    ShipSpec(name="Battleship", length=4),
    ShipSpec(name="Carrier", length=5),
]


def get_classic_fleet(num_ships: int) -> List[ShipSpec]:
    """
    Return the first `num_ships` boats from the classic Battleship fleet.
    """
    if num_ships <= 0:
        raise ValueError("num_ships must be positive")
    if num_ships > len(CLASSIC_FLEET):
        raise ValueError("num_ships exceeds the classic fleet size")
    return CLASSIC_FLEET[:num_ships]


def get_classic_lengths(num_ships: int) -> List[int]:
    """Convenience helper for code paths that only need the classic ship lengths."""
    return [ship.length for ship in get_classic_fleet(num_ships)]


def get_placement_fleet(num_ships: int) -> List[ShipSpec]:
    """
    Return the placement order used by the UI: largest boats first.
    """
    return list(reversed(get_classic_fleet(num_ships)))


def build_ship_set(num_ships: int) -> List[Ship]:
    """
    Convert the welcome-screen selection into a ship set.
    Example:
    3 -> [2,3,3]
    """
    return [Ship(length=ship.length) for ship in get_classic_fleet(num_ships)]
