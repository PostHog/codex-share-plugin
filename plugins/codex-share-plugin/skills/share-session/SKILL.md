---
name: share-session
description: Preview or publish the current Codex coding session as readable Markdown in a configured GitHub repository. Use when the user asks to share, export, publish, or save a Codex session or transcript.
---

# Share a Codex session

Use the bundled script at `../../scripts/share_session.py`.

1. Verify `gh auth status` succeeds.
2. Run the script without `--push`, passing the user's description after `--description`. This creates a local Markdown preview and prints its path.
3. Tell the user that transcripts can contain source code, prompts, tool inputs, local paths, or secrets. Ask them to approve publishing after they review the preview.
4. Only after explicit approval, rerun with the same description and `--push`.
5. Return the GitHub URL printed by the script.

If no repository is configured, ask for `owner/repo`, then run:

```bash
python3 ../../scripts/share_session.py --configure-repo owner/repo
```

Configuration is stored in `${CODEX_HOME:-~/.codex}/share-plugin-config.json`. `CODEX_SHARE_REPO` overrides the file.

Never publish without the preview and explicit approval. Do not expose transcript contents in chat unless the user asks.
