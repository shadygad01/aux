"""Observable application errors."""


class DecisionEvaluationError(RuntimeError):
    """Raised when the use case cannot evaluate an observation safely."""
