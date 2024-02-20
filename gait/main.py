import os

import typer
from typing_extensions import Annotated

from .diff import Diff
from .reviewer import Reviewer

app = typer.Typer(no_args_is_help=True)

@app.command()
def add():
    """
    Review changes between the working tree and index.
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.index.diff, None)
    patch = diff.get_patch()
    Reviewer(api_key=os.environ.get("OPENAI_API_KEY")).review(patch)


@app.command()
def commit():
    """
    Review changes between the index and HEAD.
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff)
    patch = diff.get_patch()
    Reviewer(api_key=os.environ.get("OPENAI_API_KEY")).review(patch)


@app.command()
def merge(tree: Annotated[str, typer.Argument(help="The tree to compare against.")]):
    """
    Review merge changes
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff, tree)
    patch = diff.get_patch()
    Reviewer(api_key=os.environ.get("OPENAI_API_KEY")).review(patch)


@app.command()
def pr(tree: Annotated[str, typer.Argument(help="The tree to send a pull request.")]):
    """
    Review a Pull Request
    """
    diff = Diff()
    repo = diff.get_repo()
    diff.generate_diffs(repo.head.commit.diff, tree, R=True)
    patch = diff.get_patch()
    Reviewer(api_key=os.environ.get("OPENAI_API_KEY")).review(patch)


if __name__ == "__main__":
    app()
