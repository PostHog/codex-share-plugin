# Codex Session Sharing Plugin

A Codex plugin that saves and shares coding sessions to GitHub as readable Markdown.

## Features

- Converts Codex JSONL session logs into clean, readable Markdown
- Includes user and Codex messages with collapsible tool calls
- Excludes system and developer instructions
- Creates a local preview for review before anything is published
- Commits and pushes approved sessions to any GitHub repository
- Organizes exports by GitHub username under `sessions/codex/`
- Supports optional descriptions for clearer titles and filenames

## Prerequisites

- Python 3.10+
- Codex
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated
- A GitHub repository for session exports (public or private)

## Installation

### Quick install (recommended)

For PostHog, run:

```bash
curl -fsSL https://raw.githubusercontent.com/PostHog/codex-share-plugin/main/install.sh | bash
```

This installs the plugin and configures the private `PostHog/agent-sessions` repository. Restart Codex and start a new thread after installation.

To publish somewhere else:

```bash
curl -fsSL https://raw.githubusercontent.com/PostHog/codex-share-plugin/main/install.sh | \
  bash -s -- --codex-share-repo owner/repository
```

Replace `owner/repository` with the repository where sessions should be stored. The installer detects your GitHub username with `gh` and saves the repository to `${CODEX_HOME:-~/.codex}/share-plugin-config.json`.

### Install from GitHub

```bash
codex plugin marketplace add PostHog/codex-share-plugin
codex plugin add codex-share-plugin@codex-share-plugin
```

### Install locally

From a local checkout, run:

```bash
codex plugin marketplace add /absolute/path/to/codex-share-plugin
codex plugin add codex-share-plugin@codex-share-plugin
```

Restart Codex and start a new thread after installing.

## Usage

Ask Codex to share the current session:

> Share this session.

Add a description to create a more useful title and filename:

> Share this session as “fixing authentication”.

Codex writes a local Markdown preview first. Review it, then approve publishing when prompted. You can also invoke the installed `share-session` skill explicitly.

### Output structure

Published sessions are organized like this:

```text
your-sessions-repo/
└── sessions/
    └── codex/
        └── github-username/
            ├── 20260721-142530-fixing-authentication.md
            ├── 20260721-153245-adding-tests.md
            └── ...
```

The same repository can hold exports from multiple agents by giving each one its own namespace, such as `sessions/claude/` and `sessions/codex/`.

### Example Markdown output

````markdown
# Fixing authentication

**Exported:** 2026-07-21 14:25:30 UTC

## User

Can you help me fix the authentication bug?

## Codex

I'll investigate the authentication flow and start with the relevant files.

<details>
<summary><code>exec_command</code></summary>

```json
{
  "cmd": "rg -n authentication src"
}
```
</details>
````

## Configuration

The quick installer writes the target repository to `${CODEX_HOME:-~/.codex}/share-plugin-config.json`.

To change it later, ask Codex:

> Configure session sharing to use `owner/repository`.

Or run the bundled script directly from this repository:

```bash
python3 plugins/codex-share-plugin/scripts/share_session.py \
  --configure-repo owner/repository
```

`CODEX_SHARE_REPO` overrides the configured repository. The publishing script also supports `--repo`, `--branch`, and `--base-path` overrides when run directly.

## How it works

1. Finds the latest Codex session associated with the current working directory.
2. Converts user messages, Codex responses, and tool calls to Markdown.
3. Writes a local preview and waits for explicit approval.
4. Clones the configured repository into a temporary directory.
5. Commits the session under `sessions/codex/{github-username}/` and pushes it.
6. Returns a direct GitHub link to the published transcript.

## Privacy and security

Session transcripts may contain prompts, source code, tool inputs, local paths, or secrets. Review every preview before publishing and prefer a private repository for sensitive work.

The plugin uses your existing GitHub CLI authentication and never publishes without a preview and explicit approval.

## Troubleshooting

### Repository is not configured

Re-run the installer with a repository:

```bash
curl -fsSL https://raw.githubusercontent.com/PostHog/codex-share-plugin/main/install.sh | \
  bash -s -- --codex-share-repo owner/repository
```

Or use the configuration command shown above.

### GitHub authentication fails

Check that the GitHub CLI is installed and authenticated:

```bash
gh --version
gh auth status
```

If needed, run `gh auth login` and confirm that your account has write access to the target repository.

### The repository cannot be cloned or pushed

Confirm that:

1. The repository exists and uses the `owner/repository` format.
2. Your GitHub account can access and write to it.
3. The configured branch exists. The default is `main`.
4. Your authentication has not expired. Run `gh auth refresh` if necessary.

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

After changing an installed local plugin, upgrade the marketplace and reinstall the plugin before testing it in a new Codex thread.

## License

MIT
