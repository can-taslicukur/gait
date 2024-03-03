import pkgutil

import typer
from openai import Stream

from .diff import Diff
from .errors import NoCodeChanges, NoDiffs


def stream_to_console(stream: Stream) -> str:
    """
    Prints the stream to the console and returns the full stream as a string

    Args:
        stream (Stream): Stream of text from OpenAI

    Returns:
        str: Full stream of text from OpenAI
    """
    full_stream = ""
    for chunk in stream:
        chunk_content = chunk.choices[0].delta.content
        if chunk_content is None:
            break
        full_stream += chunk_content
        print(chunk_content, end="", flush=True)
    return full_stream


def read_prompt(prompt: str) -> str:
    """
    Reads a prompt from system_prompts directory

    Args:
        prompt (str): Name of the file to read

    Returns:
        str: Contents of the file
    """
    return pkgutil.get_data(__name__, f"system_prompts/{prompt}").decode("utf-8")


def handle_create_patch_errors(diff_object: Diff) -> None:
    """
    Handles errors raised when creating a patch

    Args:
        diff_object (Diff): The Diff object
    """
    try:
        diff_object.create_patch()
    except NoDiffs as no_diffs:
        print("No differences found to review")
        raise typer.Abort() from no_diffs
    except NoCodeChanges as no_code_changes:
        print("No meaningful code changes found to review")
        raise typer.Abort() from no_code_changes
