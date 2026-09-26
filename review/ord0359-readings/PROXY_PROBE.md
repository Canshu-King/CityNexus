# Transport probe behind the failed pushes

Command: `netstat -ano`, output 5252 lines, read on 2026-09-26 at 18:0x.
Declared by the shell: `HTTP_PROXY=http://127.0.0.1:7892` and `HTTPS_PROXY=http://127.0.0.1:7892`.

## Listening entries for the port the shell names

- rows matching `127.0.0.1:7892`: 0
  (none - so nothing was bound there when git tried to use it)

## Listening entries for the port that actually answers

- netstat line 138: `TCP    127.0.0.1:7897         0.0.0.0:0              LISTENING       35752`

Four pushes failed with `Failed to connect to 127.0.0.1 port 7892`; the same push with a
per-command override to `http://127.0.0.1:7897` returned `[new branch]` and `git ls-remote`
read the ref back. Direct 443 to github.com times out on this link, so that proxy is the only
egress. No configuration file was modified - the next lane inherits the same broken default.
