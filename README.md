# Semantic Search

**A production application whose source code is a text file.**

Semantic Search is one of Prairie Labs' two founding programs (alongside Prairie Engine), and it is built prompt-native: the entire application — identity, behavior, screens, rules, product contract — lives in [`context.md`](context.md), a program written in [Scissortail](https://github.com/prairielabs/scissortail), our prompt-native programming language. The [`index.html`](index.html) shell renders it; a language model runs it.

Two files. That's the application.

## Why this matters

Most AI products hide their behavior inside weights and server code. A prompt-native application is the opposite: **the program surface is readable.** You can open the source, read what the software is and does in plain language, change a line, and run your changed program — anywhere a capable model can read text.

- **Inspectable** — the behavior contract is the document you're looking at
- **Portable** — no build step, no backend lock-in; the program travels as text
- **Controllable** — editing the software is editing prose with structure

## Install

There is no binary. Tell your coding agent (Claude Code, Codex, or similar):

> **read this: https://github.com/prairielabs/semantic-search/blob/main/READTHIS.txt**

The installer is written in [Scissortail](https://github.com/prairielabs/scissortail) and is addressed to the model. It will acquire the two files, read the program, serve the page, and become the runtime. Then you search.

## Reading order

1. [`context.md`](context.md) — the program. Written in Scissortail; meant to be read top-to-bottom by people and models alike.
2. [`index.html`](index.html) — the shell that gives it a screen.
3. [The Scissortail specification](https://github.com/prairielabs/scissortail) — the language this is written in.

## Provenance

Extracted from the private Prairie Labs platform, where Semantic Search has shipped as a product (web, and a standalone macOS desktop build). Created by [Prairie Labs, Inc](https://prairielabs.ai) — the General Simulation Company.

MIT licensed.
