# `gait`

`gait` is a command line tool that helps you review code changes in a git repository using an LLM. `gait` commands generates diffs based on `git` commands, and (currently) uses OpenAI's chat completion models to provide code review suggestions.

## Getting Started

Currently, gait only supports OpenAI chat completion models. To use any of the commands, you can either set the `OPENAI_API_KEY` environment variable or pass your OpenAI API key manually with `--openai-api-key` option.

## Help

To get help, run `gait --help`.

To get help on a specific command, run `gait <command> --help`.
