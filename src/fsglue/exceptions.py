
class FirestoreGlueException(Exception):
    """BaseException"""
    pass


class FirestoreGlueValidationError(FirestoreGlueException):
    pass


class FirestoreGlueProgrammingError(FirestoreGlueException):
    pass
