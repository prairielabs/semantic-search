# Connected local runtime

From the repository root, run `python3 start.py` (Windows: `py -3 start.py`).
The launcher uses only Python's standard library and the current Codex CLI,
signed in with ChatGPT. **GPT-5.6 Terra (`gpt-5.6-terra`)** is the default for
retrieval, ranking, language resolution, and translation. There is no Ollama
dependency and no fallback model. Theme changes do not need a model call.

The startup check verifies CLI capabilities and ChatGPT authentication, then
performs one live Terra web search before opening the browser. `--check` runs
those checks and exits; `--no-open` prints the URL without opening a browser;
`--port 8324` chooses another port. The checks and model calls use Codex allowance.
Account access, connectivity, and available allowance remain prerequisites.

## Data flow and boundaries

The host serves the existing interface and connects its native forms. Each
accepted action returns a complete replacement document. Source files remain
unchanged during use. Page state is per browser session, in memory only, and
resets when the process stops. Refresh preserves the current running session.

Each Codex request is ephemeral and read-only, in an empty temporary working
directory. User configuration and project documents are excluded; shell,
plugins, apps, hooks, browser control, and delegation are disabled. Only live
retrieval enables web search. Codex manages the existing login; the host does
not read or copy credentials. Query and translation data go to OpenAI through
Codex, and retrieval uses its web-search service.

Retrieval requires a completed web-search event and an extracted source table.
It preserves weak provider candidates instead of rejecting unfamiliar input.
Identical same-host title/snippet pairs are collapsed. Ranking selects source
IDs, assesses their relationship to the full query, and assigns relevance
scores. These assessments stay internal. Source snippets become descriptions,
translated when needed. This is snippet-based ranking, not full-page fact
checking. CLI events do not expose the full raw provider table for independent
URL-membership verification; extraction is performed by the retrieval model.
Model judgments can be wrong.

The server binds only loopback and serves explicit routes. It rejects foreign
Host/Origin requests, escapes generated content, caps request sizes, and keeps
queries, cookies, raw model errors, and credentials out of its logs. It is a
personal local app, not a production multi-user web server. True retrieval
failure retains the query and a retry control; expansion failure retains
existing results. Progress uses the existing wordmark wave and an accessible
status, without adding a visible loading label.

## Verification

```sh
python3 -m unittest discover -s local-runtime -p test_runtime.py
python3 start.py --check
```

The test suite runs offline with mocked model calls. The second command is a
real sign-in/model/live-search check and uses account allowance. CI runs the
offline suite on macOS, Linux, and Windows. Browser checks still matter: submit
a normal query and an unfamiliar string, change language, expand results, and
toggle theme. Never claim a successful startup check guarantees provider uptime.

References: [Codex CLI](https://learn.chatgpt.com/docs/codex/cli),
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
