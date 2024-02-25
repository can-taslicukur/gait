from pathlib import Path
from types import SimpleNamespace

import typer
from openai import AuthenticationError, NotFoundError, OpenAI, Stream
from typing_extensions import Annotated

from .diff import Diff
from .errors import InvalidRemote, InvalidTree, IsAncestor, NoDiffs, NotAncestor, NotARepo


# TODO: Move system_prompt to a file and make it configurable
def review_patch(openai_client: OpenAI, patch: str, model: str, temperature: float) -> Stream:
    system_prompt = """Act as a senior developer who reviews code changes to the codebase. As a senior developer, your task is to provide constructive feedback and guidance on the quality of changes based on the given diff patch.

Review the individual files and modules. Ignore the changes to automatically generated files in the diff such as .lock, manifest.json, .min.css, snaps, etc.

Assess the clarity of variable and function names and consistent coding style. Evaluate the code's structure, ensuring it follows modular design principles and separates concerns appropriately. Next, analyze the code's efficiency and performance. Look for any potential bottlenecks, unnecessary computations, or inefficient algorithms. Suggest optimizations or alternative approaches that can enhance the code's speed and resource usage. Take into account factors such as the potential impact on the overall system, the likelihood of introducing new bugs or security vulnerabilities, code readability, maintainability, test coverage, efficiency, adherence to best practices, security, and overall design patterns. Your review should focus on identifying potential issues and suggesting improvements. If the PR lacks robust tests, provide suggestions for additional tests.

If any issues are spotted, highlight them, explain the problem, and provide code suggestions. When you suggest new code, keep it simple and adhere to the principles mentioned above. Do not suggest commenting on the code, except adding docstring.

Remember to approach the code review process with a constructive and helpful mindset, aiming to assist the developer in creating a higher-quality codebase.

Conclude your review by deciding whether you request changes or approve."""  # noqa: E501
    return openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": patch}],
        temperature=temperature,
        stream=True,
    )


# TODO: Open a pager at the end of the stream and display the review as markdown
def stream_to_console(review: Stream) -> None:
    """
    Stream the review to the console and open a pager at the end of the stream

    Args:
        review (Stream): _description_
    """
    full_review = ""
    for chunk in review:
        chunk_content = chunk.choices[0].delta.content
        if chunk_content is None:
            break
        full_review += chunk_content
        print(chunk_content, end="", flush=True)


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
            help="Context line length on each side of the diff hunk",
            rich_help_panel="Git Parameters",
        ),
    ] = 3,
):
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
    try:
        patch = ctx.obj.diff.add().get_patch()
    except NoDiffs as no_diffs:
        print("No diffs to review")
        raise typer.Abort() from no_diffs
    review = review_patch(ctx.obj.client, patch, ctx.obj.model, ctx.obj.temperature)
    stream_to_console(review)


@app.command()
def commit(ctx: typer.Context):
    try:
        patch = ctx.obj.diff.commit().get_patch()
    except NoDiffs as no_diffs:
        print("No diffs to review")
        raise typer.Abort() from no_diffs
    review = review_patch(ctx.obj.client, patch, ctx.obj.model, ctx.obj.temperature)
    stream_to_console(review)


@app.command()
def merge(
    ctx: typer.Context, tree: Annotated[str, typer.Argument(help="tree to merge into the HEAD")]
):
    try:
        patch = ctx.obj.diff.merge(tree).get_patch()
    except InvalidTree as invalid_tree:
        print(f"{tree} is not a valid tree")
        raise typer.Abort() from invalid_tree
    except IsAncestor as ancestor_tree:
        print(f"{tree} is an ancestor of the HEAD")
        raise typer.Abort() from ancestor_tree
    except NoDiffs as no_diffs:
        print("No diffs to review")
        raise typer.Abort() from no_diffs
    review = review_patch(ctx.obj.client, patch, ctx.obj.model, ctx.obj.temperature)
    stream_to_console(review)


@app.command()
def push(
    ctx: typer.Context, remote: Annotated[str, typer.Argument(help="remote to push to")] = "origin"
):
    try:
        patch = ctx.obj.diff.push(remote).get_patch()
    except InvalidRemote as invalid_remote:
        print(f"{remote} is not a valid remote")
        raise typer.Abort() from invalid_remote
    except InvalidTree as invalid_tree:
        print(f"{remote} is not a valid tree")
        raise typer.Abort() from invalid_tree
    except NotAncestor as not_ancestor:
        print(f"{remote} is not an ancestor of the HEAD")
        raise typer.Abort() from not_ancestor
    except NoDiffs as no_diffs:
        print("No diffs to review")
        raise typer.Abort() from no_diffs
    review = review_patch(ctx.obj.client, patch, ctx.obj.model, ctx.obj.temperature)
    stream_to_console(review)


@app.command()
def pr(
    ctx: typer.Context,
    target_branch: Annotated[str, typer.Argument(help="target branch to compare")],
    remote: Annotated[str, typer.Argument(help="remote of the target branch")] = "origin",
):
    try:
        patch = ctx.obj.diff.pr(target_branch, remote).get_patch()
    except InvalidRemote as invalid_remote:
        print(f"{remote} is not a valid remote")
        raise typer.Abort() from invalid_remote
    except InvalidTree as invalid_tree:
        print(f"{target_branch} is not a valid tree")
        raise typer.Abort() from invalid_tree
    except NotAncestor as not_ancestor:
        print(f"{remote}/{target_branch} is not an ancestor of the HEAD")
        raise typer.Abort() from not_ancestor
    except NoDiffs as no_diffs:
        print("No diffs to review")
        raise typer.Abort() from no_diffs
    review = review_patch(ctx.obj.client, patch, ctx.obj.model, ctx.obj.temperature)
    stream_to_console(review)


if __name__ == "__main__":
    app()
