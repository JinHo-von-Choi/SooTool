class SooToolError(Exception):
    pass


class InvalidInputError(SooToolError):
    pass


class DomainConstraintError(SooToolError):
    pass


class PrecisionLossError(SooToolError):
    pass
