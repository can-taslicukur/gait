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
