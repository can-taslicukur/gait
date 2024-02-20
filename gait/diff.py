from typing import Callable, Union

from git import GitCommandError, InvalidGitRepositoryError, Repo, diff
from typer import Exit, echo


class Diff:
    """
    A class to facilitate the generation of diffs.
    """

    def __init__(self) -> None:
        """
        The constructor for the Diff class.

        Raises:
            Exit: Raised when no git repository is found.
        """
        try:
            self.repo = Repo(".", search_parent_directories=True)
        except InvalidGitRepositoryError as no_git:
            echo("no git repository found.")
            raise Exit(1) from no_git

    def get_repo(self) -> Repo:
        """
        Get the repository object.

        Returns:
            Repo: The repository object.
        """
        return self.repo

    def generate_diffs(
        self,
        diffMethod: Callable[..., diff.Diff],
        against: Union[str, None, diff.Diffable.Index] = diff.Diffable.Index,
        R: bool = False,
        unified: int = 3,
    ):
        """
        Generate diffs with a diffMethod against a target.

        Args:
            diffMethod (Callable[..., diff.Diff]): The diff method to use.
            against (Union[str, None, diff.Diffable.Index], optional): Target to compare against
            Defaults to diff.Diffable.Index.
            If None, compare against the working tree.
            If str, compare against the given tree.
            R (bool, optional): Whether to reverse the diff. Defaults to False.
            unified (int, optional): Number of lines of context. Defaults to 3.

        Raises:
            Exit: Raised when an invalid target is provided.
        """
        try:
            diffs = diffMethod(against, create_patch=True, no_ext_diff=True, R=R, unified=unified)
            self.diffs = diffs
        except GitCommandError as invalid_target:
            echo(f"Invalid target: {against}")
            raise Exit(1) from invalid_target

    def get_patch(self) -> str:
        """
        Get the patch for the diffs.

        Raises:
            ValueError: Raised when no diffs are generated with generate_diffs method.

        Returns:
            str: The patch for the diffs.
        """
        if self.diffs is None:
            raise ValueError("No diffs generated.")
        return "\n".join([diff.diff.decode("utf-8") for diff in self.diffs])
