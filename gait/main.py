import typer
from typing_extensions import Annotated

from .diff import Diff

app = typer.Typer(no_args_is_help=True)


@app.command()
def review(
    target_tree: Annotated[
        str,
        typer.Argument(help="Target tree to compare changes."),
    ] = "origin/main",
):
    """
    Review changes between HEAD and target tree.
    """
    print(Diff().head(target_tree))


if __name__ == "__main__":
    app()
