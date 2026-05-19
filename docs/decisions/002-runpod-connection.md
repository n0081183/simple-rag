# ADR 002: RunPod pod connection — SSH primary

## Status

Accepted (Milestone 0)

## Context

Function B orchestrates a remote GPU pod: bootstrap, docs sync, chunk, embed, export snapshot, download. Connection options:

1. **SSH** (RunPod exposes SSH per pod; user adds key)
2. **RunPod REST API** + `runpodctl exec`
3. **Hybrid**: API for lifecycle (start/stop/test), SSH for pipeline execution

## Decision

**Hybrid with SSH as the execution transport** for pipeline steps.

| Operation | Mechanism |
|-----------|-----------|
| Test connection / GPU info | RunPod REST API (`GET /pods/{id}`) |
| Stop pod (optional UI button) | RunPod REST API |
| Bootstrap, sync, embed, export | SSH + `paramiko` (streaming logs over channel) |
| Download snapshot | `scp`/`sftp` over SSH |

## Rationale

1. **Universality**: SSH works on bare PyTorch images without RunPod-specific agents.
2. **Log streaming**: Single long-lived session with stdout/stderr forwarded to SSE → UI.
3. **File transfer**: `rsync`/`scp` for `.tar.zst` snapshot is battle-tested.
4. **API still used** where it shines: credential test, pod metadata, stop pod — no need to parse SSH for GPU model name.

## Consequences

- User must configure SSH key (default `~/.ssh/id_ed25519` or path in settings); RunPod API key in keychain only.
- `backend/app/infra/ssh.py` implements `SSHSession` with retry and host key policy (warn on first connect).
- `runpod/bootstrap.sh` is idempotent; invoked via `ssh exec`.

## Security

- RunPod API key: `keyring` service `siwz-rag-lite/runpod`
- SSH private key: never copied to repo; optional keychain entry for passphrase-less deploy keys
