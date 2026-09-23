# Semantic Search

A source-first web search app from Prairie Labs. Enter a query, get real links
ranked for relevance, and search in the language you choose.

Its behavior is written in [`context.md`](context.md), a readable program in
[Scissortail](https://github.com/prairielabs/scissortail). [`index.html`](index.html)
is the interface; the included local runtime connects its controls to live search.

## Get started

You need **Python 3.10+**, the current **[Codex CLI](https://learn.chatgpt.com/docs/codex/cli)**,
and a **ChatGPT account with Codex and GPT-5.6 Terra access**. Searches and
translations use your account's Codex allowance. No API key, Ollama, local
model download, or Python package installation is required.

Install Codex once using the official guide, or with npm if Node.js is installed:

```sh
npm install -g @openai/codex
codex login
```

Choose ChatGPT sign-in. Then download this repository (Code → Download ZIP and
extract it), or clone it:

```sh
git clone https://github.com/prairielabs/semantic-search.git
cd semantic-search
python3 start.py
```

On Windows, use `py -3 start.py` instead of `python3 start.py`.

The launcher checks your setup, verifies **ChatGPT Terra** (`gpt-5.6-terra`)
with a real web search, and opens the connected app at
[localhost:8323](http://localhost:8323/). That startup check uses Codex allowance.
Keep the terminal open while using the app; press Ctrl+C to stop.

**Do not open `index.html` directly or use a plain static server to run searches.**
Those show the interface without connecting its controls. Use `start.py`.

## Having trouble?

- **Codex missing or too old:** install/update it with `npm install -g @openai/codex@latest`.
- **Sign-in or model access:** run `codex login`, choose ChatGPT, and confirm your account has Terra access and remaining Codex allowance.
- **Port already in use:** stop the previous server, or run `python3 start.py --port 8324`.
- **Browser did not open:** use the URL printed in the terminal. For remote/headless use, pass `--no-open`; the server stays bound to loopback.
- **Check setup without starting:** run `python3 start.py --check`. It performs one live search and reports success or the setup problem.
- **Search fails after startup:** your query stays in the field and Try again retries it. Check connectivity and account allowance. Searches take time to retrieve and rank sources; the wordmark animates while a request runs.

The launcher stops with a setup message instead of opening an inert app when a
prerequisite is missing. Account outages and exhausted allowances can still
interrupt searches after a successful startup check.

## Use with a coding agent

Ask your agent to follow [`HARNESSED_AGENT_READ_THIS.md`](HARNESSED_AGENT_READ_THIS.md).
It must launch the included runtime and verify an actual search, rather than
claiming that reading the prompt or serving static HTML has installed the app.
The supported local runtime uses Codex even when another agent helps set it up.

## How it works

- Live search retrieves source candidates; Terra then ranks the retrieved source IDs.
- URLs must come from the retrieved candidate table. Ranking cannot invent destinations.
- Weak matches are ranked honestly instead of rejecting unfamiliar input before retrieval.
- Terra translates the interface and summaries when you enter a language name.
- The language hint cycles through sixteen native language names, five seconds each.
- Light/dark switching is immediate. Query and preferences remain in the current browser session until the server stops.

This is a personal local app, not a public multi-user server. Queries and
translation payloads are sent through Codex to OpenAI; retrieved web text is
processed as untrusted input. There is no query history written by this host.
See [`local-runtime/README.md`](local-runtime/README.md) for boundaries and tests.

## Source and provenance

1. [`context.md`](context.md) — application behavior and product contract.
2. [`index.html`](index.html) — the interface shell.
3. [`local-runtime/`](local-runtime/README.md) — the working open-source browser bridge.
4. [Scissortail specification](https://github.com/prairielabs/scissortail) — the prompt language.

Semantic Search is one of Prairie Labs' founding programs alongside Prairie
Engine. Its desktop and hosted lineage are separate from this local distribution.
The September 22 update supersedes the earlier Luna default with
[GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra).

Created by [Prairie Labs, Inc](https://prairielabs.ai), the General Simulation Company.
MIT licensed.

## Hosted alternative

[`FREE-CODES.md`](FREE-CODES.md) records the earlier first-come hosted-code offer
at [gensim.co](https://gensim.co). Remaining code availability is not guaranteed.
Those codes are separate from this local app and its ChatGPT sign-in.
