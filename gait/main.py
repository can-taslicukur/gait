from pathlib import Path
from types import SimpleNamespace

import typer
from openai import AuthenticationError, NotFoundError, OpenAI
from typing_extensions import Annotated

from .diff import Diff
from .errors import NotARepo

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    openai_api_key: Annotated[
        str,
        typer.Option(
            help="OpenAI API key", envvar="OPENAI_API_KEY", rich_help_panel="OpenAI Parameters"
        ),
    ],
    model: Annotated[
        str, typer.Option(help="OpenAI GPT model", rich_help_panel="OpenAI Parameters")
    ] = "gpt-3.5-turbo",
    temperature: Annotated[
        int,
        typer.Option(
            min=0, max=2, help="Temperature for the model", rich_help_panel="OpenAI Parameters"
        ),
    ] = 1,
    unified: Annotated[
        int,
        typer.Option(
            help="Context lines to show before and after the change",
            rich_help_panel="Git Parameters",
        ),
    ] = 3,
):
    try:
        diff = Diff(Path("."))
    except NotARepo as not_a_repo:
        print("Not a git repository")
        raise typer.Abort() from not_a_repo

    if not model.startswith("gpt"):
        raise typer.BadParameter(
            "Only gpt models are supported", ctx=ctx, param=model, param_hint="model"
        )

    client = OpenAI(api_key=openai_api_key)
    try:
        client.models.retrieve(model=model)
    except AuthenticationError as auth_error:
        raise typer.BadParameter(
            "Invalid OpenAI API key", ctx=ctx, param=openai_api_key, param_hint="openai_api_key"
        ) from auth_error
    except NotFoundError as no_model:
        raise typer.BadParameter(
            f"{model} does not exist", ctx=ctx, param=model, param_hint="model"
        ) from no_model

    ctx.obj = SimpleNamespace(
        diff=diff,
        client=client,
        openai_api_key=openai_api_key,
        model=model,
        temperature=temperature,
        unified=unified,
    )

    if ctx.invoked_subcommand is None:
        ctx.get_help()

@app.command()
def add(ctx: typer.Context):
    pass


if __name__ == "__main__":
    app()
