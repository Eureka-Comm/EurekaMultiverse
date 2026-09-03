# Package initialization for EMPredictor
# Register the EMPredictorEngine with the EMRegistry upon import

from src.eureka.foundation.cognitive.orchestration.em_registry import EMRegistry
from .engine import EMPredictorEngine

# Instantiate a registry instance for registration (if a global registry exists elsewhere, this will register a new instance; however, per constraints, we register explicitly here)
# In typical usage, the application creates a registry and registers EMs; here we provide a helper registration function.

def register_empredictor(registry: EMRegistry) -> None:
    """Register EMPredictorEngine with the provided EMRegistry."""
    registry.register(EMPredictorEngine())
