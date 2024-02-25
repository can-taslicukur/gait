from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from gait.main import app

from .fixtures.git_history import git_history

runner = CliRunner()

class MockAuthenticationError(Exception):
    pass


class MockNotFoundError(Exception):
    pass


class MockOpenAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.models = MagicMock()

        def models_retrieve_side_effect(model):
            if self.api_key != "test-key":
                raise MockAuthenticationError
            if model not in ["gpt-3.5-turbo", "gpt-4"]:
                raise MockNotFoundError

        self.models.retrieve.side_effect = models_retrieve_side_effect


@pytest.fixture
def mock_openai(monkeypatch):
    monkeypatch.setattr("gait.main.OpenAI", MockOpenAI)
    monkeypatch.setattr("gait.main.AuthenticationError", MockAuthenticationError)
    monkeypatch.setattr("gait.main.NotFoundError", MockNotFoundError)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.mark.usefixtures("git_history")
def test_main(git_history: git_history, mock_openai):
    result = runner.invoke(app, ["--help"])
    assert "OpenAI Parameters" in result.stdout
    assert "Git Parameters" in result.stdout

    # Test with invalid model option
    invalid_model_result = runner.invoke(app, ["--model", "no-gpt"])
    assert invalid_model_result.exit_code != 0
    assert "Only gpt models are supported" in invalid_model_result.stdout

    # Test with non-existent model
    non_existent_model_result = runner.invoke(app, ["--model", "gpt-non-existent"])
    assert non_existent_model_result.exit_code != 0
    assert "gpt-non-existent does not exist" in non_existent_model_result.stdout

    # Test with invalid openai api key
    invalid_api_key_result = runner.invoke(app, ["--openai-api-key", "invalid-key"])
    print(invalid_api_key_result.stdout)
    assert invalid_api_key_result.exit_code != 0
    assert "Invalid OpenAI API key" in invalid_api_key_result.stdout
