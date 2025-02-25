from typer.testing import CliRunner

from gait.main import app

runner = CliRunner()

def test_main(monkeypatch, git_history):
    monkeypatch.chdir(git_history["repo_path"])

    result = runner.invoke(app, ["--help"])
    assert "OpenAI Parameters" in result.stdout
    assert "Git Parameters" in result.stdout

    # Test in a non-git directory
    monkeypatch.chdir(git_history["no_repo_path"])
    not_a_repo_result = runner.invoke(app)
    assert not_a_repo_result.exit_code != 0
    print(not_a_repo_result.exit_code)
    print(not_a_repo_result.stdout)
    assert not_a_repo_result.stdout.endswith(
        "\nCurrent directory is not a git repository\nAborted.\n"
    )
