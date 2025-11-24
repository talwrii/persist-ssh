# persist-ssh
Persist ssh connections without breaking terminal scrollback.

## Motivation
I use tmux locally but sometimes ssh into a server to do work. It gets annoying when ssh connectios fail so I want to persist shells on remote machines. The standard approach is to use a multiplexer like tmux, zellij or screen. However, these tools tends to break scrollback and it's a bit weird have a terminal multiplexer within another terminal multiplexer. I want something simpler which does not break scrollback. 
`dtach` is such a tool. It is a lightweight detacheable connection to a running process.

This tool wraps up dtach and a tool called mosh - which creates more robust ssh connections to kill you a persistent connection to a remote machine.


