from unittest.mock import MagicMock

from gait.utils import stream_to_console


def test_stream_to_console(capsys):
    mock_openai_stream = MagicMock()
    mock_openai_stream.__iter__.return_value = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="mock"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" "))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="content"))]),
    ]
    full_stream = stream_to_console(mock_openai_stream)
    out, err = capsys.readouterr()
    assert out == "mock content"
    assert full_stream == "mock content"
