from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo
from typer import Exit


def fetch_remote(repo: Repo, remote: str) -> None:
    """
    Fetch the remote.

    Args:
        repo (Repo): The git repository.
        remote (str): The remote to fetch.

    Raises:
        typer.Exit: Raised when the remote is not found.
    """
    try:
        repo.git.fetch(remote)
    except GitCommandError as no_remote:
        print(f"remote {remote} not found.")
        raise Exit(1) from no_remote

def check_head_ancestry(repo: Repo, tree: str) -> bool:
    """
    Check if the tree is an ancestor of the HEAD.

    Args:
        repo (Repo): The git repository.
        tree (str): The tree to compare against.

    Raises:
        typer.Exit: Raised when the tree is not found.

    Returns:
        bool: True if the tree is an ancestor of the HEAD, False otherwise.
    """
    try:
        return repo.is_ancestor(tree, repo.head.commit)
    except GitCommandError as no_tree:
        print(f"{tree} not found.")
        raise Exit(1) from no_tree


class Diff:
    """
    A class to facilitate the generation of diff patches.
    """

    def __init__(self, repo_path: Path, unified: int = 3) -> None:
        """
        The constructor for the Diff class.

        Raises:
            typer.Exit: Raised when no git repository is found.
        """
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError as no_git:
            print("no git repository found.")
            raise Exit(1) from no_git
        self.diffs = None
        self.repo_path = repo_path
        self.unified = unified

    def add(self) -> "Diff":
        """
        Diff between the index and the working tree.
        """
        self.diffs = self.repo.index.diff(
            None, create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )
        return self

    def commit(self) -> "Diff":
        """
        Diff between the HEAD and the index.
        """
        self.diffs = self.repo.head.commit.diff(
            create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )
        return self

    def merge(self, tree: str) -> "Diff":
        """
        Diff between the HEAD and the tree.

        Args:
            tree (str): The tree to compare against.

        Raises:
            Exit: Raised when the tree is not found.
        """
        tree_is_ancestor = check_head_ancestry(self.repo, tree)
        if tree_is_ancestor:
            print("Tree is an ancestor of the HEAD. No changes to review.")
            raise Exit(0)

        self.diffs = self.repo.head.commit.diff(
            tree, create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )
        return self

    def push(self, remote: str = "origin") -> "Diff":
        """
        Diff between the HEAD and remote.

        Args:
            remote (str): The remote to compare against. Defaults to "origin".
        """
        remote_head = f"{remote}/{self.repo.active_branch.name}"

        fetch_remote(self.repo, remote)
        remote_is_ancestor = check_head_ancestry(self.repo, remote_head)
        if not remote_is_ancestor:
            print("Remote is not an ancestor of the HEAD, cannot push without merging.")
            raise Exit(1)

        self.diffs = self.repo.head.commit.diff(
            remote_head, create_patch=True, no_ext_diff=True, R=True, unified=self.unified
        )
        return self

    def pr(self, target_branch: str, remote: str = "origin"):
        """
        Diff between the HEAD and the remote target branch.

        Args:
            target_branch (str): The branch to compare HEAD against.
            remote (str): Remote name
        """
        remote_head = f"{remote}/{target_branch}"
        fetch_remote(self.repo, remote)
        remote_head_is_ancestor = check_head_ancestry(self.repo, remote_head)
        if not remote_head_is_ancestor:
            print(f"{remote_head} is not an ancestor of the HEAD, consider merging or rebasing.")
            raise Exit(1)
        self.diffs = self.repo.head.commit.diff(
            remote_head, create_patch=True, no_ext_diff=True, R=True, unified=self.unified
        )
        return self

    def get_patch(self) -> str:
        """
        Get the patch for the diffs.

        Returns:
            str: The patch for the diffs.
            None: If no diffs are found.
        """
        if self.diffs is None:
            raise Exception("No diffs generated.")
        elif len(self.diffs) == 0:
            print("No changes found.")
            raise Exit(0)
        return "\n".join([diff.diff.decode("utf-8") for diff in self.diffs])
