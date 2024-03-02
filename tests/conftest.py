from unittest.mock import MagicMock

import pytest
from git import Repo


@pytest.fixture
def git_history(tmp_path_factory):
    no_repo_path = tmp_path_factory.mktemp("no_repo")
    repo_path = tmp_path_factory.mktemp("repo")
    repo = Repo.init(repo_path)
    gitignore = repo_path / ".gitignore"

    # First commit
    with open(gitignore, "w") as f:
        f.write("first_line\n")
    repo.git.add(gitignore)
    repo.index.commit("first commit")

    # Create a feature branch and checkout
    repo.create_head("feature")
    repo.heads.feature.checkout()

    # Adding second line and staging
    with open(gitignore, "a") as f:
        f.write("second_line\n")
    repo.git.add(gitignore)

    # Adding third line
    with open(gitignore, "a") as f:
        f.write("third_line\n")

    remote_repo_path = tmp_path_factory.mktemp("remote_repo")
    Repo.init(remote_repo_path, bare=True)

    repo.create_remote("origin", remote_repo_path.as_uri())
    repo.remotes.origin.push("feature", set_upstream=True)

    return {
        "repo_path": repo_path,
        "gitignore": gitignore,
        "remote_repo_path": remote_repo_path,
        "no_repo_path": no_repo_path,
    }


@pytest.fixture
def mock_openai():
    class MockAuthenticationError(Exception):
        pass

    class MockNotFoundError(Exception):
        pass

    class MockOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = MagicMock()

            def models_retrieve_side_effect(model):
                if self.api_key != "test-key":
                    raise MockAuthenticationError
                if model not in ["gpt-3.5-turbo", "gpt-4"]:
                    raise MockNotFoundError

            self.models.retrieve.side_effect = models_retrieve_side_effect

    return {
        "MockAuthenticationError": MockAuthenticationError,
        "MockNotFoundError": MockNotFoundError,
        "MockOpenAI": MockOpenAI,
    }
