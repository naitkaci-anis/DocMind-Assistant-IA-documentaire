from config import settings


def test_settings_paths_exist():
    assert settings.BASE_DIR.exists()
    assert settings.DATA_DIR.exists()
    assert settings.UPLOADS_DIR.exists()
    assert settings.CHROMA_DIR.exists()


def test_allowed_extensions():
    assert ".pdf" in settings.ALLOWED_EXTENSIONS
    assert ".docx" in settings.ALLOWED_EXTENSIONS
