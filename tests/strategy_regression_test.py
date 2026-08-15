import unittest
import pandas as pd
import numpy as np
from app.strategies.bullish_divergence import BullishDivergenceStrategy
from app.confirmation.candle import check_bullish_candle

class TestStrategyRegression(unittest.TestCase):
    def test_doji_no_entry(self):
        """Test that a doji candle does not produce a READY signal."""
        # Create a doji candle (Open=100, High=105, Low=95, Close=100.1)
        df = pd.DataFrame([{
            "Open": 100, "High": 105, "Low": 95, "Close": 100.1, "Volume": 1000
        }])
        self.assertFalse(check_bullish_candle(df))

    def test_green_candle_entry(self):
        """Test that a solid green candle is accepted."""
        df = pd.DataFrame([{
            "Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1000
        }])
        self.assertTrue(check_bullish_candle(df))

    def test_bullish_divergence_logic(self):
        # This would need a more complex setup with pivots and indicators
        pass

if __name__ == "__main__":
    unittest.main()
