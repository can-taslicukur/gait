import pytest
from git import Repo

from gait.diff import Diff, check_ancestry, fetch_remote
from gait.errors import (
    DirtyRepo,
    InvalidRemote,
    InvalidTree,
    IsAncestor,
    NoDiffs,
    NotAncestor,
    NotARepo,
)


def test_fetch_remote(git_history):
    repo = Repo(git_history["repo_path"])
    with pytest.raises(InvalidRemote):
        fetch_remote(repo, "nonexistent_remote")
    assert fetch_remote(repo, "origin") is None

def test_check_ancestry(git_history):
    repo = Repo(git_history["repo_path"])
    with pytest.raises(InvalidTree):
        check_ancestry(repo, "nonexistent_tree")
    assert check_ancestry(repo, "master") is True
    assert check_ancestry(repo, "feature", "master") is True

    # Make master ahead of feature
    repo.heads.master.checkout()
    repo.git.add(git_history["gitignore"])
    repo.index.commit("second commit")

    repo.heads.feature.checkout()
    assert check_ancestry(repo, "master") is False
    assert check_ancestry(repo, "feature", "master") is True


def test_init(git_history):
    no_repo_path = git_history["no_repo_path"]
    repo_path = git_history["repo_path"]
    with pytest.raises(NotARepo):
        Diff(no_repo_path)
    repo = Repo.init(repo_path)
    diff = Diff(repo_path)
    assert diff.repo == repo
    assert diff.unified == 3
    assert diff.diffs is None
    assert diff.patch is None


def test_create_tmp_branch(git_history):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    tmp_branch = diff._create_tmp_branch()

    assert tmp_branch.startswith("tmp-")
    assert tmp_branch in diff.repo.heads
    assert diff.repo.heads[tmp_branch].commit.hexsha == diff.repo.head.commit.hexsha
    diff.repo.git.add(git_history["gitignore"])
    diff.repo.index.commit("second commit")
    assert diff.repo.heads.master.commit.hexsha != diff.repo.heads.feature.commit.hexsha

    tmp_branch_from_master = diff._create_tmp_branch("master")

    assert tmp_branch_from_master.startswith("tmp-")
    assert tmp_branch_from_master in diff.repo.heads
    assert (
        diff.repo.heads[tmp_branch_from_master].commit.hexsha
        == diff.repo.heads.master.commit.hexsha
    )


def test_create_patch(git_history, snapshot):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    with pytest.raises(Exception, match="No diffs generated"):
        diff.create_patch()

    patch = diff.add().create_patch()
    assert diff.patch == patch
    snapshot.assert_match(patch, "add_patch")

    diff_negative_unified = Diff(repo_path, unified=-11)
    patch = diff_negative_unified.add().create_patch()
    snapshot.assert_match(patch, "add_patch_diff_negative_unified")

    repo = Repo(repo_path)
    repo.git.add(git_history["gitignore"])
    with pytest.raises(NoDiffs):
        diff.add().create_patch()


def test_merge_on_temp_branch(git_history, snapshot):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    with pytest.raises(DirtyRepo):
        diff._merge_on_temp_branch("feature", "master")

    # Commit all changes
    repo = Repo(repo_path)
    repo.git.add(git_history["gitignore"])
    repo.index.commit("second commit")

    # Checkout to master
    repo.heads.master.checkout()

    sha_before_merge = repo.head.commit.hexsha
    branches_before_merge = repo.heads
    diffs = diff._merge_on_temp_branch("feature", "master")
    assert isinstance(diffs, list)
    assert len(diffs) == 1
    snapshot.assert_match(diff.create_patch(), "feature_merge_on_master_patch")
    assert sha_before_merge == repo.head.commit.hexsha
    assert branches_before_merge == repo.heads

    # make master ahead of feature
    with open(git_history["gitignore"], "a") as f:
        f.write("conflict\n")
    repo.git.add(git_history["gitignore"])
    repo.index.commit("I want to see the world burn!")
    diffs = diff._merge_on_temp_branch("feature", "master")
    assert isinstance(diffs, list)
    assert len(diffs) == 1
    snapshot.assert_match(diff.create_patch(), "feature_conflict_merge_on_master_patch")


def test_add(git_history, snapshot):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    patch = diff.add().create_patch()
    snapshot.assert_match(patch, "add_patch")

    diff.repo.git.add(git_history["gitignore"])
    diff.add()
    assert len(diff.diffs) == 0


def test_commit(git_history, snapshot):
    repo_path = git_history["repo_path"]
    diff = Diff(repo_path)
    patch = diff.commit().create_patch()
    snapshot.assert_match(patch, "commit_patch")

    diff.repo.git.add(git_history["gitignore"])
    diff.repo.index.commit("second commit")
    diff.commit()
    assert len(diff.diffs) == 0


def test_merge(git_history, snapshot):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)
    with pytest.raises(IsAncestor):
        diff.merge("master")
    repo.git.add(git_history["gitignore"])
    repo.index.commit("second commit")
    repo.heads.master.checkout()
    patch = diff.merge("feature").create_patch()
    snapshot.assert_match(patch, "merge_patch")

    # create conflict
    with open(git_history["gitignore"], "a") as f:
        f.write("conflict\n")
    repo.git.add(git_history["gitignore"])
    repo.index.commit("conflict")
    patch = diff.merge("feature").create_patch()
    snapshot.assert_match(patch, "merge_conflict_patch")


def test_push(git_history, snapshot):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)

    diff.push()
    assert len(diff.diffs) == 0

    repo.index.commit("added second line")
    patch = diff.push().create_patch()
    snapshot.assert_match(patch, "push_patch")

    # Make remote ahead of local
    repo.git.push()
    repo.git.reset("HEAD^")
    # Commit working tree
    repo.git.add(git_history["gitignore"])
    repo.index.commit("added second and third line")
    with pytest.raises(NotAncestor):
        diff.push()

def test_pr(git_history, snapshot):
    repo_path = git_history["repo_path"]
    repo = Repo(repo_path)
    diff = Diff(repo_path)
    with pytest.raises(InvalidTree):
        # master has not been pushed to origin
        diff.pr("master")
    repo.remotes.origin.push("master", set_upstream=True)

    repo.git.add(git_history["gitignore"])
    repo.index.commit("added second and third line")
    patch = diff.pr("master").create_patch()
    snapshot.assert_match(patch, "pr_patch")

    # Make remote master ahead of local feature
    repo.heads.master.checkout()
    with open(git_history["gitignore"], "a") as f:
        f.write("adding a line in master\n")
    repo.git.add(git_history["gitignore"])
    repo.index.commit("adding a line in master")
    repo.remotes.origin.push("master")
    repo.heads.feature.checkout()
    patch = diff.pr("master").create_patch()
    snapshot.assert_match(patch, "pr_conflict_patch")

    # Make local feature ancestor of remote master
    repo.git.reset("HEAD^", hard=True)
    with pytest.raises(IsAncestor):
        diff.pr("master")


def test_review_patch(mock_openai, git_history):
    openai_client = mock_openai["MockOpenAI"]("test-key")
    diff = Diff(git_history["repo_path"])
    with pytest.raises(Exception, match="No patch to review"):
        diff.review_patch(openai_client, "gpt-3", 0.7, "system_prompt")

    openai_client.chat.completions.create.return_value = "test completion"
    diff.add().create_patch()
    diff.review_patch(openai_client, "gpt-3", 0.7, "system prompt")
    assert diff.review == "test completion"
