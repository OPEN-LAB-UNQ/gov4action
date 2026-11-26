import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from config import Settings


def options(**extra):
    return dict(
        _env_file=None,
        database_url="sqlite://",
        secret_key="s" * 32,
        gobernanza_password="p" * 12,
        admin_password=None,
        **extra,
    )


@pytest.mark.parametrize("field", ["secret_key", "gobernanza_password", "admin_password"])
@pytest.mark.parametrize("value", ["", "CAMBIAR", " cambiar ", "password", "short"])
def test_rejects_invalid_credentials(field, value):
    data = options()
    data[field] = value
    with pytest.raises(ValidationError):
        Settings(**data)


@pytest.mark.parametrize("field,minimum", [("secret_key", 32), ("gobernanza_password", 12), ("admin_password", 12)])
def test_length_boundary_and_error_does_not_disclose_value(field, minimum):
    data = options()
    data[field] = "Z" * (minimum - 1)
    with pytest.raises(ValidationError) as error:
        Settings(**data)
    assert data[field] not in str(error.value)
    data[field] = "Z" * minimum
    assert getattr(Settings(**data), field) == data[field]


def test_optional_admin_password_and_valid_settings():
    assert Settings(**options()).admin_password is None


def test_import_fails_before_app_start_with_example_secret(tmp_path):
    env = dict(
        os.environ,
        DATABASE_URL="sqlite://",
        SECRET_KEY="CAMBIAR",
        GOBERNANZA_PASSWORD="test-only-password",
        PYTHONPATH=os.getcwd(),
    )
    result = subprocess.run(
        [sys.executable, "-c", "import config"], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr
    assert "input_value=" not in result.stderr
