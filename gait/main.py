from pathlib import Path
from types import SimpleNamespace

import typer
from openai import AuthenticationError, NotFoundError, OpenAI
from typing_extensions import Annotated

from .diff import Diff
from .errors import (
    DirtyRepo,
    InvalidRemote,
    InvalidTree,
    IsAncestor,
    NotAncestor,
    NotARepo,
)
from .utils import handle_create_patch_errors, read_prompt, stream_to_console

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
    ] = "gpt-4-turbo-preview",
    temperature: Annotated[
        int,
        typer.Option(
            min=0, max=2, help="Temperature for the model", rich_help_panel="OpenAI Parameters"
        ),
    ] = 1,
    system_prompt: Annotated[
        str,
        typer.Option(
            help="Custom system prompt to use for the diff patches",
            rich_help_panel="OpenAI Parameters",
        ),
    ] = None,
    unified: Annotated[
        int,
        typer.Option(
            help="Context line length on each side of the diff hunk",
            rich_help_panel="Git Parameters",
        ),
    ] = 3,
):
    if ctx.invoked_subcommand is None:
        ctx.get_help()
    try:
        diff = Diff(Path("."), unified=unified)
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

    if system_prompt is None:
        system_prompt = read_prompt("default")

    ctx.obj = SimpleNamespace(
        diff=diff,
        client=client,
        openai_api_key=openai_api_key,
        model=model,
        temperature=temperature,
        system_prompt=system_prompt,
        unified=unified,
    )

@app.command()
def add(ctx: typer.Context):
    ctx.obj.diff.add()
    handle_create_patch_errors(ctx.obj.diff)
    review = ctx.obj.diff.review_patch(
        ctx.obj.client, ctx.obj.model, ctx.obj.temperature, ctx.obj.system_prompt
    )
    stream_to_console(review)


@app.command()
def commit(ctx: typer.Context):
    ctx.obj.diff.commit()
    handle_create_patch_errors(ctx.obj.diff)
    review = ctx.obj.diff.review_patch(
        ctx.obj.client, ctx.obj.model, ctx.obj.temperature, ctx.obj.system_prompt
    )
    stream_to_console(review)


@app.command()
def merge(
    ctx: typer.Context, tree: Annotated[str, typer.Argument(help="tree to merge into the HEAD")]
):
    try:
        ctx.obj.diff.merge(tree)
    except InvalidTree as invalid_tree:
        print(f"{tree} is not a valid tree to merge into the HEAD")
        raise typer.Abort() from invalid_tree
    except IsAncestor as ancestor_tree:
        print(f"{tree} is an ancestor of the HEAD, no code changes to review")
        raise typer.Abort() from ancestor_tree
    except DirtyRepo as dirty_repo:
        print(
            "Working tree has uncommitted changes, please commit or stash them to review the merge"
        )
        raise typer.Abort() from dirty_repo
    handle_create_patch_errors(ctx.obj.diff)
    review = ctx.obj.diff.review_patch(
        ctx.obj.client, ctx.obj.model, ctx.obj.temperature, ctx.obj.system_prompt
    )
    stream_to_console(review)

@app.command()
def push(
    ctx: typer.Context, remote: Annotated[str, typer.Argument(help="remote to push to")] = "origin"
):
    remote_head = f"{remote}/{ctx.obj.diff.repo.active_branch.name}"
    try:
        ctx.obj.diff.push(remote)
    except InvalidRemote as invalid_remote:
        print(f"{remote} is not a valid remote")
        raise typer.BadParameter(
            f"{remote} is not a valid remote", ctx=ctx, param=remote, param_hint="remote"
        ) from invalid_remote
    except InvalidTree as no_upstream:
        print(f"Active branch has no upstream {remote_head}, please set it to review the push")
        raise typer.Abort() from no_upstream
    except NotAncestor as not_ancestor:
        print(
            "Remote is ahead of the local branch, please pull the changes before reviewing the push"
        )
        raise typer.Abort() from not_ancestor
    handle_create_patch_errors(ctx.obj.diff)
    review = ctx.obj.diff.review_patch(
        ctx.obj.client, ctx.obj.model, ctx.obj.temperature, ctx.obj.system_prompt
    )
    stream_to_console(review)

@app.command()
def pr(
    ctx: typer.Context,
    target_branch: Annotated[str, typer.Argument(help="target branch to compare")],
    remote: Annotated[str, typer.Argument(help="remote of the target branch")] = "origin",
):
    remote_target_ref = f"{remote}/{target_branch}"
    try:
        ctx.obj.diff.pr(target_branch, remote)
    except InvalidRemote as invalid_remote:
        raise typer.BadParameter(
            f"{remote} is not a valid remote", ctx=ctx, param=remote, param_hint="remote"
        ) from invalid_remote
    except InvalidTree as invalid_tree:
        raise typer.BadParameter(
            f"{remote_target_ref} is not a valid tree",
            ctx=ctx,
            param_hint="remote/target_branch",
        ) from invalid_tree
    except IsAncestor as ancestor_tree:
        print(f"HEAD is an ancestor of {remote_target_ref}, no code changes to review")
        raise typer.Abort() from ancestor_tree
    except DirtyRepo as dirty_repo:
        print(
            "Working tree has uncommitted changes, please commit or stash them to review the pull request"  # noqa: E501
        )
        raise typer.Abort() from dirty_repo
    handle_create_patch_errors(ctx.obj.diff)
    review = ctx.obj.diff.review_patch(
        ctx.obj.client, ctx.obj.model, ctx.obj.temperature, ctx.obj.system_prompt
    )
    stream_to_console(review)


if __name__ == "__main__":
    app()
