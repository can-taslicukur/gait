from typer.testing import CliRunner

from gait.main import app

runner = CliRunner()

def test_main(mock_openai, monkeypatch, git_history):
    monkeypatch.chdir(git_history["repo_path"])
    monkeypatch.setattr("gait.main.OpenAI", mock_openai["MockOpenAI"])
    monkeypatch.setattr("gait.main.AuthenticationError", mock_openai["MockAuthenticationError"])
    monkeypatch.setattr("gait.main.NotFoundError", mock_openai["MockNotFoundError"])
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

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

    # Test in a non-git directory
    monkeypatch.chdir(git_history["no_repo_path"])
    not_a_repo_result = runner.invoke(app)
    assert not_a_repo_result.exit_code != 0
    assert "Current directory is not a git repository" in not_a_repo_result.stdout
