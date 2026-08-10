from typing import List, Dict

def calculate_fib_levels(start_price: float, end_price: float, levels: List[float]) -> Dict[float, float]:
    """
    Calculates Fibonacci levels based on start and end price.
    For retracement: start=High, end=Low (to find levels between or beyond).
    For strategy wait zones: start=High (before wave 3), end=Low (of wave 3).
    """
    diff = end_price - start_price
    return {level: start_price + (diff * level) for level in levels}
