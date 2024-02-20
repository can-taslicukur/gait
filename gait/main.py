import typer
from typing_extensions import Annotated

from .diff import Diff

app = typer.Typer(no_args_is_help=True)


@app.command()
def add():
    """
    Review changes between the working tree and index.
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.index.diff, None)
    print(diff.get_patch())


@app.command()
def commit():
    """
    Review changes between the index and HEAD.
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff)
    print(diff.get_patch())


@app.command()
def merge(tree: Annotated[str, typer.Argument(help="The tree to compare against.")]):
    """
    Review merge changes
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff, tree)
    print(diff.get_patch())


@app.command()
def pr(tree: Annotated[str, typer.Argument(help="The tree to send a pull request.")]):
    """
    Review a Pull Request
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff, tree, R=True)
    print(diff.get_patch())


if __name__ == "__main__":
    app()
