from typing import List, Dict

def calculate_fib_extension(point_a: float, point_b: float, point_c: float, levels: List[float] = [0.618, 1.0, 1.618]) -> Dict[float, float]:
    """
    Standard 3-point Fibonacci Extension.
    point_a: Start of wave (Low)
    point_b: End of wave (High)
    point_c: End of retracement (Low)
    """
    diff = point_b - point_a
    return {level: point_c + (diff * level) for level in levels}
