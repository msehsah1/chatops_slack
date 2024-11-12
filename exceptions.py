class GcpKeyNotFound(Exception):
    def __init__(self, message='GCP service account not found'):
        super().__init__(message)

class SlackSecretsNotfound(Exception):
    def __init__(self, message='Check your slack configuration'):
        super().__init__(message)
