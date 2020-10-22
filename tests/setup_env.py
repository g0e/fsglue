import fsglue
from unittest import mock
import google.auth.credentials
import os


os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8001"
credentials = mock.Mock(spec=google.auth.credentials.Credentials)
fsglue.initialize(project="test", credentials=credentials)
