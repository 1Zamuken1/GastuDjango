import pytest


@pytest.fixture(autouse=True)
def _sin_ia_real(settings):
    """Los tests nunca llaman a Groq; los que prueban la IA simulan la respuesta."""
    settings.CAPTURA_USAR_IA = False
