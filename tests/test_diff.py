import re

import pytest
import typer
from git import Repo

from gait.diff import Diff

added_lines_pattern = re.compile(r"(?<=^\+)\w+(?=\s)", re.M)
removed_lines_pattern = re.compile(r"(?<=^-)\w+(?=\s)", re.M)


@pytest.fixture(scope="module")
def git_history(tmp_path_factory):
    repo_path = tmp_path_factory.mktemp("repo")
    repo = Repo.init(repo_path)
    gitignore = repo_path / ".gitignore"

    # First commit
    with open(gitignore, "w") as f:
        f.write("first_line\n")
    repo.git.add(".gitignore")
    repo.index.commit("first commit")

    # Create a feature branch and checkout
    repo.create_head("feature")
    repo.heads.feature.checkout()

    # Adding second line and staging
    with open(gitignore, "a") as f:
        f.write("second_line\n")
    repo.git.add(".gitignore")

    # Adding third line
    with open(gitignore, "a") as f:
        f.write("third_line\n")

    return repo_path


def test_init(tmp_path):
    with pytest.raises(typer.Exit):
        Diff(tmp_path)
    repo = Repo.init(tmp_path)
    diff = Diff(tmp_path)
    assert diff.repo == repo
    assert diff.unified == 3


def test_add(git_history):
    repo_path = git_history
    patch = Diff(repo_path).add().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["third_line"]


def test_commit(git_history):
    repo_path = git_history
    patch = Diff(repo_path).commit().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line"]


def test_merge(git_history):
    repo_path = git_history
    with pytest.raises(typer.Exit):
        Diff(repo_path).merge("master")
    repo = Repo(repo_path)
    repo.git.add(".gitignore")
    repo.index.commit("second commit")
    repo.heads.master.checkout()
    patch = Diff(repo_path).merge("feature").get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line", "third_line"]
