import random

class DataSimulator:

    @staticmethod
    def simulate_voltage() -> float:
        # 230Volts ± 10%
        return round(random.uniform(207, 253), 2) # Simulates volage within EU / Swiss Standard
    
    @staticmethod
    def simulate_frequency() -> float:
        # 50Hz ± 0.5Hz
        return round(random.uniform(49.5, 50.5), 2) # Simulates frequency within EU / Swiss Standard
    
    @staticmethod
    def simulate_current(lowerRange: int, upperRange: int) -> float:
        # Simulate current. Example 0-16A
        return round(random.uniform(lowerRange, upperRange), 2)
    
    @staticmethod
    def simulate_power(lowerRange: int, upperRange: int) -> float:
        # Simulates power
        return round(random.uniform(lowerRange, upperRange), 2)