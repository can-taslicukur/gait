from unittest.mock import MagicMock

import pytest
import typer

from gait.diff import Diff
from gait.utils import handle_create_patch_errors, read_prompt, stream_to_console


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

def test_read_prompt():
    prompt = read_prompt("default")
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_handle_create_patch_errors(git_history, capsys):
    diff = Diff(git_history["repo_path"])
    repo = diff.repo
    repo.git.add(git_history["gitignore"])
    diff.add()
    with pytest.raises(typer.Abort):
        handle_create_patch_errors(diff)
        assert capsys.readouterr().out == "No differences found to review"

    diff.commit()
    handle_create_patch_errors(diff)
    assert diff.patch is not None
    repo.index.commit("committing changes")

    # add an empty file to the repository
    with open(git_history["repo_path"] / "empty_file", "w") as f:
        f.write("")
    repo.git.add(git_history["repo_path"] / "empty_file")
    diff.commit()
    with pytest.raises(typer.Abort):
        handle_create_patch_errors(diff)
        assert capsys.readouterr().out == "No meaningful code changes found to review"
