# persist-ssh
**@readwithai** - [X](https://x.com/readwithai) - [blog](https://readwithai.substack.com/) - [machine-aided reading](https://www.reddit.com/r/machineAidedReading/) - [📖](https://readwithai.substack.com/p/what-is-reading-broadly-defined
)[⚡️](https://readwithai.substack.com/s/technical-miscellany)[🖋️](https://readwithai.substack.com/p/note-taking-with-obsidian-much-of)

Persist ssh connections without breaking terminal scrollback.

## Motivation
I use tmux locally but sometimes ssh into a server to do work. It gets annoying when ssh connectios fail so I want to persist shells on remote machines. The standard approach is to use a multiplexer like tmux, zellij or screen. However, these tools tends to break scrollback and it's a bit weird have a terminal multiplexer within another terminal multiplexer. I want something simpler which does not break scrollback.
`dtach` is such a tool. It is a lightweight detacheable connection to a running process.

## Installation
You can install persist-ssh using [pipx](https://github.com/pypa/pipx).

```
pipx install persist-ssh
```

## Usage
`persist-ssh server`

This will install mosh and dtach remotely. You can press Ctrl+t to detach. `persist-ssh` wil then reattach to the session by default.

I use persist-ssh with `tmux` so like to use the name of my tmux window for the remote session. For tis you can use the `--tmux` option or by adding `session_from_tmux_pane = false` to `~/.config/persist-ssh.toml`.


## About me
I am **@readwithai**. I create tools for reading, research and agency sometimes using the markdown editor [Obsidian](https://readwithai.substack.com/p/what-exactly-is-obsidian).

I also create a [stream of tools](https://readwithai.substack.com/p/my-productivity-tools) that are related to carrying out my work.

I write about lots of things - including tools like this - on [X](https://x.com/readwithai).
My [blog](https://readwithai.substack.com/) is more about reading and research and agency.
