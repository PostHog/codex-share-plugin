# Codex session sharing plugin

A Codex plugin that previews and publishes coding sessions to GitHub as readable Markdown.

## Features

- Finds the latest Codex session for the current working directory
- Exports user and Codex messages plus collapsible tool calls
- Excludes developer and system instructions
- Requires a local preview before Codex asks to publish
- Organizes sessions under `sessions/codex/{github-username}/`, so the repository can hold exports from multiple agents

## Prerequisites

- Python 3.10+
- Codex
- An authenticated [GitHub CLI](https://cli.github.com/)
- A GitHub repository for agent session exports

## Install locally

```bash
codex plugin marketplace add /absolute/path/to/codex-share-plugin
```

Restart the Codex app, install **Codex Share Plugin** from Plugins, then start a new thread.

To distribute this repository from GitHub, push it and use:

```bash
codex plugin marketplace add owner/codex-share-plugin
```

## Configure

Ask Codex:

> Configure session sharing to use `owner/repository`.

Or run the bundled script directly:

```bash
python3 plugins/codex-share-plugin/scripts/share_session.py --configure-repo owner/repository
```

For PostHog's shared private agent-session repository, use `PostHog/agent-sessions`.

## Use

Ask Codex:

> Share this session as “fixing authentication”.

Codex creates a local preview and asks for confirmation before pushing it. You can also invoke the installed `share-session` skill explicitly.

## Privacy

Session transcripts may contain prompts, source code, tool inputs, local paths, or secrets. Review every preview before publishing, and prefer a private repository.

The repository can be shared with other agent-session exporters by giving each agent its own namespace, for example `sessions/claude/` and `sessions/codex/`.

## Test

```bash
python3 -m unittest discover -s tests
```

## License

MIT
