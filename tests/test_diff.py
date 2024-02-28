import re

import pytest
from git import Repo

from gait.diff import Diff, check_head_ancestry, fetch_remote
from gait.errors import (
    DirtyRepo,
    InvalidRemote,
    InvalidTree,
    IsAncestor,
    NoDiffs,
    NotAncestor,
    NotARepo,
)

added_lines_pattern = re.compile(r"(?<=^\+)\w+(?=\n)", re.M)
removed_lines_pattern = re.compile(r"(?<=^-)\w+(?=\n)", re.M)
conflict_ours_pattern = re.compile(r"(?<=^\+\<{7} HEAD\n\s).+(?=\n\+\={7}\n)", re.M)


def test_fetch_remote(git_history):
    repo = Repo(git_history["repo_path"])
    with pytest.raises(InvalidRemote):
        fetch_remote(repo, "nonexistent_remote")
    assert fetch_remote(repo, "origin") is None

def test_check_head_ancestry(git_history):
    repo = Repo(git_history["repo_path"])
    with pytest.raises(InvalidTree):
        check_head_ancestry(repo, "nonexistent_tree")
    assert check_head_ancestry(repo, "master") is True

    # Make master ahead of feature
    repo.heads.master.checkout()
    repo.git.add(".gitignore")
    repo.index.commit("second commit")

    repo.heads.feature.checkout()
    assert check_head_ancestry(repo, "master") is False


def test_init(git_history):
    no_repo_path = git_history["no_repo_path"]
    repo_path = git_history["repo_path"]
    with pytest.raises(NotARepo):
        Diff(no_repo_path)
    repo = Repo.init(repo_path)
    diff = Diff(repo_path)
    assert diff.repo == repo
    assert diff.unified == 3

def test_get_patch(git_history, snapshot):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    with pytest.raises(Exception, match="No diffs generated"):
        diff.get_patch()

    patch = diff.add().get_patch()
    snapshot.assert_match(patch, "add_patch")

    diff_negative_unified = Diff(repo_path, unified=-11)
    patch = diff_negative_unified.add().get_patch()
    snapshot.assert_match(patch, "add_patch_diff_negative_unified")

    repo = Repo(repo_path)
    repo.git.add(".gitignore")
    with pytest.raises(NoDiffs):
        diff.add().get_patch()

def test_add(git_history):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    patch = diff.add().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["third_line"]

def test_commit(git_history):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    patch = diff.commit().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line"]

def test_merge(git_history):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)
    with pytest.raises(IsAncestor):
        diff.merge("master")
    repo.git.add(".gitignore")
    repo.index.commit("second commit")
    repo.heads.master.checkout()
    sha_before_merge = repo.head.commit.hexsha
    patch = diff.merge("feature").get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line", "third_line"]
    assert sha_before_merge == repo.head.commit.hexsha

    # make repo dirty
    with open(repo_path / ".gitignore", "a") as f:
        f.write("conflict\n")
    with pytest.raises(DirtyRepo):
        diff.merge("feature")
    repo.git.add(".gitignore")
    with pytest.raises(DirtyRepo):
        diff.merge("feature")

    # create conflict
    repo.index.commit("conflict")
    sha_before_merge = repo.head.commit.hexsha
    patch = diff.merge("feature").get_patch()
    print(patch)
    assert conflict_ours_pattern.findall(patch) == ["conflict"]
    assert sha_before_merge == repo.head.commit.hexsha


def test_push(git_history):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)
    repo.index.commit("added second line")
    patch = diff.push().get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line"]

    # Make remote ahead of local
    repo.git.push()
    repo.git.reset("HEAD^")
    # Commit working tree
    repo.git.add(".gitignore")
    repo.index.commit("added second and third line")
    with pytest.raises(NotAncestor):
        diff.push()

def test_pr(git_history):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)
    with pytest.raises(InvalidTree):
        diff.pr("nonexistent_branch")
        # master has not been pushed to origin
        diff.pr("master")
    repo.remotes.origin.push("master", set_upstream=True)
    assert len(diff.pr("master").diffs) == 0

    repo.git.add(".gitignore")
    repo.index.commit("added second and third line")
    patch = diff.pr("master").get_patch()
    assert removed_lines_pattern.search(patch) is None
    assert added_lines_pattern.findall(patch) == ["second_line", "third_line"]

    # Make remote master ahead of local feature
    repo.heads.master.checkout()
    with open(repo_path / "gitignore", "a") as f:
        f.write("adding a line in master\n")
    repo.git.add(".gitignore")
    repo.index.commit("adding a line in master")
    repo.remotes.origin.push("master")
    repo.heads.feature.checkout()
    with pytest.raises(NotAncestor):
        diff.pr("master")
