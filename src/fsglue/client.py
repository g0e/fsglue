from google.cloud import firestore

_client = None


def get_client():
    """
    Returns:
        firestore.Client instance used in fsglue.
    """
    global _client
    if not _client:
        _client = firestore.Client()
    return _client


def initialize(**kwargs):
    """initialize firestore.Client() manually

    Args:
        **kwargs: arguments passed to firestore.Client(**kwargs).
    """
    global _client
    _client = firestore.Client(**kwargs)
