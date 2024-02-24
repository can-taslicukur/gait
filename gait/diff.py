from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo
from typer import Exit


class Diff:
    """
    A class to facilitate the generation of diff patches.
    """

    def __init__(self, repo_path: Path, unified: int = 3) -> None:
        """
        The constructor for the Diff class.

        Raises:
            Exit: Raised when no git repository is found.
        """
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError as no_git:
            print("no git repository found.")
            raise Exit(1) from no_git
        self.repo_path = repo_path
        self.unified = unified

    def add(self):
        """
        Diff between the index and the working tree.
        """
        diff = self.repo.index.diff(
            None, create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )
        if len(diff) == 0:
            print("No changes between the index and the working tree")
            raise Exit(0)

        self.diffs = diff
        return self

    def commit(self):
        """
        Diff between the HEAD and the index.
        """
        diff = self.repo.head.commit.diff(
            create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )
        if len(diff) == 0:
            print("No changes between the HEAD and the index.")
            raise Exit(0)

        self.diffs = diff
        return self

    def merge(self, tree: str):
        """
        Diff between the HEAD and the tree.

        Args:
            tree (str): The tree to compare against.

        Raises:
            Exit: Raised when the tree is not found.
        """
        try:
            tree_is_ancestor = self.repo.is_ancestor(tree, self.repo.head.commit)
        except GitCommandError as no_tree:
            print(f"Tree {tree} not found.")
            raise Exit(1) from no_tree

        if tree_is_ancestor:
            print("Tree is an ancestor of the HEAD. No changes to review.")
            raise Exit(0)

        diff = self.repo.head.commit.diff(
            tree, create_patch=True, no_ext_diff=True, R=False, unified=self.unified
        )

        if len(diff) == 0:
            print("No changes between the HEAD and the tree.")
            raise Exit(0)

        self.diffs = diff
        return self

    def get_patch(self):
        """
        Get the patch for the diffs.

        Returns:
            str: The patch for the diffs.
            None: If no diffs are found.
        """
        if self.diffs is None:
            return None
        return "\n".join([diff.diff.decode("utf-8") for diff in self.diffs])
