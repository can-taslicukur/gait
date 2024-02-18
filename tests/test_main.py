from typer.testing import CliRunner

from gait.main import app

runner = CliRunner()


def test_app():
    result = runner.invoke(
        app,
        ["--help"],
    )
    assert result.exit_code == 0
