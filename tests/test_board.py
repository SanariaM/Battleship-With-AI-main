import random
import unittest

from game.board import GRID_SIZE, generate_random_fleet


class GenerateRandomFleetTests(unittest.TestCase):
    def test_generate_random_fleet_places_expected_ship_lengths_without_overlap(self):
        board, ships = generate_random_fleet(5, rng=random.Random(123))

        self.assertEqual(len(ships), 5)
        self.assertEqual([len(ship) for ship in ships], [2, 3, 3, 4, 5])

        occupied = [coord for ship in ships for coord in ship]
        self.assertEqual(len(occupied), len(set(occupied)))

        for row, col in occupied:
            self.assertTrue(0 <= row < GRID_SIZE)
            self.assertTrue(0 <= col < GRID_SIZE)
            self.assertEqual(board[row][col], 1)

        marked_cells = {
            (row, col)
            for row in range(GRID_SIZE)
            for col in range(GRID_SIZE)
            if board[row][col] == 1
        }
        self.assertEqual(marked_cells, set(occupied))

    def test_generate_random_fleet_rejects_non_positive_ship_count(self):
        with self.assertRaises(ValueError):
            generate_random_fleet(0)


if __name__ == "__main__":
    unittest.main()
