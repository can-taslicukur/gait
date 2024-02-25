import re

import pytest
import typer
from git import Repo

from gait.diff import Diff, fetch_remote

added_lines_pattern = re.compile(r"(?<=^\+)\w+(?=\s)", re.M)
removed_lines_pattern = re.compile(r"(?<=^-)\w+(?=\s)", re.M)


@pytest.fixture(scope="function")
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

    remote_repo_path = tmp_path_factory.mktemp("remote_repo")
    Repo.init(remote_repo_path, bare=True)

    repo.create_remote("origin", remote_repo_path.as_uri())
    repo.remotes.origin.push("feature", set_upstream=True)

    return {"repo_path": repo_path, "remote_repo_path": remote_repo_path}

def test_fetch_remote(git_history):
    repo = Repo(git_history["repo_path"])
    with pytest.raises(typer.Exit):
        fetch_remote(repo, "nonexistent_remote")
    assert fetch_remote(repo, "origin") is None


def test_init(tmp_path):
    with pytest.raises(typer.Exit):
        Diff(tmp_path)
    repo = Repo.init(tmp_path)
    diff = Diff(tmp_path)
    assert diff.repo == repo
    assert diff.unified == 3


def test_add(git_history):
    repo_path = git_history["repo_path"]
    patch = Diff(repo_path).add().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["third_line"]


def test_commit(git_history):
    repo_path = git_history["repo_path"]
    patch = Diff(repo_path).commit().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line"]


def test_merge(git_history):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    with pytest.raises(typer.Exit):
        Diff(repo_path).merge("master")
    with pytest.raises(typer.Exit):
        Diff(repo_path).merge("nonexistent_tree")
    repo.git.add(".gitignore")
    repo.index.commit("second commit")
    repo.heads.master.checkout()
    patch = Diff(repo_path).merge("feature").get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line", "third_line"]


def test_push(git_history):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    with pytest.raises(typer.Exit):
        Diff(repo_path).push("nonexistent_remote")
    repo.index.commit("added second line")
    patch = Diff(repo_path).push().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line"]

    # Make remote ahead of local
    repo.git.push()
    repo.git.reset("HEAD^")
    # Commit working tree
    repo.git.add(".gitignore")
    repo.index.commit("added second and third line")
    with pytest.raises(typer.Exit):
        Diff(repo_path).push()
