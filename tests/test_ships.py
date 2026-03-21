import unittest

from game.ships import get_classic_fleet, get_placement_fleet


class PlacementFleetTests(unittest.TestCase):
    def test_classic_fleet_keeps_standard_order(self):
        fleet = get_classic_fleet(5)

        self.assertEqual(
            [(ship.name, ship.length) for ship in fleet],
            [
                ("Patrol Boat", 2),
                ("Submarine", 3),
                ("Destroyer", 3),
                ("Battleship", 4),
                ("Carrier", 5),
            ],
        )

    def test_placement_fleet_starts_with_largest_boats(self):
        fleet = get_placement_fleet(5)

        self.assertEqual(
            [(ship.name, ship.length) for ship in fleet],
            [
                ("Carrier", 5),
                ("Battleship", 4),
                ("Destroyer", 3),
                ("Submarine", 3),
                ("Patrol Boat", 2),
            ],
        )


if __name__ == "__main__":
    unittest.main()
