from unittest import TestCase

from timestream.util import (
    layouts,  # module
)


class TestTrayPosToChamberIndex(TestCase):
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_tray_pos_to_chamber_idx(self):
        """Tests for ts.util.traypos_to_chamber_index"""
        self.assertEqual(layouts.traypos_to_chamber_index("1A1"), 1)
        self.assertEqual(layouts.traypos_to_chamber_index("01A1"), 1)
        self.assertEqual(layouts.traypos_to_chamber_index("1a1"), 1)
        self.assertEqual(layouts.traypos_to_chamber_index("01a1"), 1)
        self.assertEqual(layouts.traypos_to_chamber_index("09A1"), 161)
        self.assertEqual(layouts.traypos_to_chamber_index("16D4"), 319)
        with self.assertRaises(TypeError):
            layouts.traypos_to_chamber_index(321)
        with self.assertRaises(ValueError):
            layouts.traypos_to_chamber_index("234A3")
        with self.assertRaises(ValueError):
            layouts.traypos_to_chamber_index("24A33")
        with self.assertRaises(ValueError):
            layouts.traypos_to_chamber_index("24A")
        with self.assertRaises(ValueError):
            layouts.traypos_to_chamber_index("A2")
