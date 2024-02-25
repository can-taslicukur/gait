import pytest
from git import Repo


@pytest.fixture
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
