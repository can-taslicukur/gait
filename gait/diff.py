from typing import Union

from git import GitCommandError, InvalidGitRepositoryError, Repo, diff
from typer import Exit, echo


class Diff:
    """
    Diff class to compare changes.
    """

    def __init__(self) -> None:
        try:
            self.repo = Repo(".", search_parent_directories=True)
        except InvalidGitRepositoryError as no_git:
            echo("Current folder is not a git repository!")
            raise Exit(1) from no_git

    def head(
        self,
        against: Union[str, None, diff.Diffable.Index] = diff.Diffable.Index,
        R=False,
        unified: int = 3,
    ) -> str:
        """Compare changes between HEAD and target tree, index or working tree.

        See https://git-scm.com/docs/git-diff for more information on R and unified.

        Args:
            against (Union[str, None, diff.Diffable.Index], optional): What to compare against.
            Defaults to diff.Diffable.Index (index).
            If None, compare against the working tree.
            If a string, compare against the given tree.
            R (bool, optional): Whether to reverse the diff. Defaults to False.
            unified (int, optional): Number of lines of context to show. Defaults to 3.

        Raises:
            Exit: If the target is invalid.

        Returns:
            str: The diff.
        """
        try:
            diffs = self.repo.head.commit.diff(
                against, create_patch=True, no_ext_diff=True, R=R, unified=unified
            )
        except GitCommandError as invalid_target:
            echo(f"Invalid target: {against}")
            raise Exit(1) from invalid_target
        return "\n".join([diff.diff.decode("utf-8") for diff in diffs])
