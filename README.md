# gait

[![PyPI version](https://badge.fury.io/py/gait.svg)](https://badge.fury.io/py/gait)


`gait` is a command line tool that helps you review code changes in a git repository using an LLM. `gait` commands generates diffs based on `git` commands, and (currently) uses OpenAI's chat completion models to provide code review suggestions.

## Getting Started

### Installation

You can install `gait` using `pip`:

```bash
pip install gait
```

Currently, gait only supports OpenAI chat completion models. To use any of the commands, you can either set the `OPENAI_API_KEY` environment variable 

```bash
export OPENAI_API_KEY='YOUR API KEY HERE'
```

or pass your OpenAI API key manually with `--openai-api-key` option.

### Commands

- **Add**: Review changes between the working tree and the index.
  
  ```bash
  gait add
  ```

- **Commit**: Review changes between the index and the HEAD.
  
  ```bash
  gait commit
  ```

- **Merge**: Review the result of merging a feature branch into the HEAD.
  
  ```bash
  gait merge <feature_branch>
  ```

- **Push**: Review the changes between the HEAD and the remote.
  
  ```bash
  gait push [remote]
  ```

- **Pull Request (PR)**: Review the result of a pull request from HEAD to the target branch in the remote.
  
  ```bash
  gait pr <target_branch> [remote]
  ```

### Options

- `--openai_api_key`: Specify the OpenAI API key. Can also be set via `OPENAI_API_KEY` environment variable.
- `--model`: Choose the OpenAI GPT model for reviews (default: `gpt-4-turbo-preview`).
- `--temperature`: Set the temperature for model responses (range: 0-2) (default: 1).
- `--system_prompt`: Use a custom system prompt for diff patches.
- `--unified`: Context line length on each side of the diff hunk (default: 3).

## Help

To get help, run `gait --help`.

To get help on a specific command, run `gait <command> --help`.
