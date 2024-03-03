import pkgutil

from openai import Stream


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
