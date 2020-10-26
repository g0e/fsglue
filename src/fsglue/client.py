from google.cloud import firestore

_client = None


def get_client():
    """
    Returns:
        obj: firestore.Client instance used in fsglue.
    """
    global _client
    if not _client:
        _client = firestore.Client()
    return _client


def initialize(**kwargs):
    """initialize firestore.Client() manually

    Args:
        **kwargs: arguments passed to `firestore.Client(**kwargs) <https://googleapis.dev/python/firestore/latest/client.html#module-google.cloud.firestore_v1.client>`_
    """
    global _client
    _client = firestore.Client(**kwargs)
