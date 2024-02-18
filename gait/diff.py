from git import GitCommandError, InvalidGitRepositoryError, Repo
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

    # TODO: Right now, because of a bug in gitPython, we can't include index or working tree in diff
    # to generate patch reliably. That is why `target_tree` is not optional.
    # Issue: https://github.com/gitpython-developers/GitPython/issues/1828
    # It would be nice to have a way to get diff HEAD against working tree or index.
    # Or index against tree or working tree.
    def head(self, target_tree: str) -> str:
        """
        Compare HEAD against target tree.

        Args:
            target_tree (str): Target tree to compare changes.

        Raises:
            Exit: If target tree is invalid.

        Returns:
            str: Diff between HEAD and target tree.
        """
        try:
            diffs = self.repo.head.commit.diff(target_tree, create_patch=True, R=True)
        except GitCommandError as invalid_target:
            echo(f"Invalid target: {target_tree}")
            raise Exit(1) from invalid_target
        return "\n".join(
            [
                f"a_path:{diff.a_path}\nb_path:{diff.b_path}\n{diff.diff.decode('utf-8')}"
                for diff in diffs
            ]
        )
