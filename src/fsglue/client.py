from google.cloud import firestore


_client = None


def get_client():
    global _client
    if not _client:
        _client = firestore.Client()
    return _client


def initialize(**kwargs):
    global _client
    _client = firestore.Client(**kwargs)
