"""Context-rich infrastructure failures."""


class ContractValidationError(ValueError):
    """Raised when external data violates a versioned JSON contract."""
