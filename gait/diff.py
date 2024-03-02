import uuid
from pathlib import Path
from typing import List

from git import GitCommandError, InvalidGitRepositoryError, Repo, diff
from openai import OpenAI, Stream

from .errors import (
    DirtyRepo,
    InvalidRemote,
    InvalidTree,
    IsAncestor,
    NoCodeChanges,
    NoDiffs,
    NotAncestor,
    NotARepo,
)


def fetch_remote(repo: Repo, remote: str) -> None:
    """Fetch the remote.

    Args:
        repo (Repo): The git repository.
        remote (str): The remote to fetch.

    Raises:
        InvalidRemote: Raised when the remote is not found.
    """
    try:
        repo.git.fetch(remote)
    except GitCommandError as no_remote:
        raise InvalidRemote from no_remote


def check_head_ancestry(repo: Repo, tree: str) -> bool:
    """Check if the tree is an ancestor of the HEAD.

    Args:
        repo (Repo): The git repository.
        tree (str): The tree to compare against.

    Raises:
        InvalidTree: Raised when the tree is not found.

    Returns:
        bool: True if the tree is an ancestor of the HEAD, False otherwise.
    """
    try:
        return repo.is_ancestor(tree, repo.head.commit)
    except GitCommandError as no_tree:
        raise InvalidTree from no_tree


class Diff:
    """
    The Diff class for generating diffs and patches.
    """

    def __init__(self, repo_path: Path, unified: int = 3) -> None:
        """
        Initialize the Diff class.

        Args:
            repo_path (Path): The path to the git repository.
            unified (int, optional): The number of lines of context to include in the patch.
            Defaults to 3.

        Raises:
            NotARepo: Raised when the path is not a git repository.
        """
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError as no_git:
            raise NotARepo from no_git
        self.diffs = None
        self.patch = None
        self.repo_path = repo_path
        self.unified = unified

    def add(self) -> "Diff":
        """
        Diff between the index and the working tree.

        Returns:
            Diff: The Diff object.
        """
        self.diffs = self.repo.index.diff(
            None, create_patch=True, no_ext_diff=True, unified=self.unified
        )
        return self

    def commit(self) -> "Diff":
        """
        Diff between the HEAD and the index.

        Returns:
            Diff: The Diff object.
        """
        self.diffs = self.repo.head.commit.diff(
            create_patch=True, no_ext_diff=True, unified=self.unified
        )
        return self

    def _create_tmp_branch(self, from_commit: str = "HEAD") -> str:
        tmp_branch = f"tmp-{uuid.uuid4()}"
        self.repo.create_head(tmp_branch, from_commit)
        return tmp_branch

    def _merge_on_temp_branch(self, feature_commit: str, base_commit: str) -> List[diff.Diff]:
        if self.repo.is_dirty():
            raise DirtyRepo
        # Save current branch to get back to it later
        active_branch = self.repo.active_branch.name

        tmp_branch = self._create_tmp_branch(base_commit)
        self.repo.heads[tmp_branch].checkout()

        has_conflict = False
        try:
            self.repo.git.merge(feature_commit, no_commit=True, no_ff=True)
        except GitCommandError:
            has_conflict = True
        finally:
            diffs = self.repo.head.commit.diff(
                None, create_patch=True, no_ext_diff=True, unified=self.unified
            )
        if has_conflict:
            self.repo.git.merge(abort=True)
        else:
            self.repo.git.reset(hard=True)

        # Go back to original branch
        self.repo.heads[active_branch].checkout()
        # Clean up the temporary branch
        self.repo.delete_head(tmp_branch, force=True)

        self.diffs = diffs
        return diffs

    def merge(self, tree: str) -> "Diff":
        """
        Diff between the HEAD and the tree.

        Args:
            tree (str): The tree to compare against.

        Raises:
            IsAncestor: When the tree is an ancestor of the HEAD.
            DirtyRepo: When the repository has uncommitted changes.
            GitCommandError: When the merge fails, except conflicts.

        Returns:
            Diff: The Diff object.
        """
        tree_is_ancestor = check_head_ancestry(self.repo, tree)
        if tree_is_ancestor:
            raise IsAncestor

        self.diffs = self._merge_on_temp_branch(tree, self.repo.active_branch.name)

        return self

    def push(self, remote: str = "origin") -> "Diff":
        """
        Diff between the HEAD and the remote HEAD.

        Args:
            remote (str, optional): The remote to compare against. Defaults to "origin".

        Raises:
            NotAncestor: When the remote HEAD is not an ancestor of the HEAD.

        Returns:
            Diff: The Diff object.
        """
        remote_head = f"{remote}/{self.repo.active_branch.name}"

        fetch_remote(self.repo, remote)
        remote_is_ancestor = check_head_ancestry(self.repo, remote_head)
        if not remote_is_ancestor:
            raise NotAncestor

        self.diffs = self.repo.head.commit.diff(
            remote_head, create_patch=True, no_ext_diff=True, R=True, unified=self.unified
        )
        return self

    def pr(self, target_branch: str, remote: str = "origin") -> "Diff":
        """
        Diff between the HEAD and the target branch on the remote.

        Args:
            target_branch (str): The target branch on the remote.
            remote (str, optional): The remote to compare against. Defaults to "origin".

        Raises:
            NotAncestor: When the remote HEAD is not an ancestor of the HEAD.

        Returns:
            Diff: The Diff object.
        """
        remote_head = f"{remote}/{target_branch}"
        fetch_remote(self.repo, remote)

        # To trigger InvalidTree if the remote_head is not found
        check_head_ancestry(self.repo, remote_head)

        self.diffs = self._merge_on_temp_branch(self.repo.active_branch.name, remote_head)

        return self

    def create_patch(self) -> str:
        """
        Get the patch from the diffs.

        Raises:
            Exception: No diffs generated.
            NoDiffs: When there are no diffs to review.

        Returns:
            str: All the diffs in the patch.
        """
        if self.diffs is None:
            raise Exception("No diffs generated.")
        elif len(self.diffs) == 0:
            raise NoDiffs
        patch = "\n".join([diff.diff.decode("utf-8") for diff in self.diffs])
        if patch.strip() == "":
            raise NoCodeChanges
        self.patch = patch
        return patch

    def review_patch(
        self, openai_client: OpenAI, model: str, temperature: float, system_prompt: str
    ) -> Stream:
        if self.patch is None:
            raise Exception("No patch to review.")

        self.review = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.patch},
            ],
            temperature=temperature,
            stream=True,
        )

        return self.review
