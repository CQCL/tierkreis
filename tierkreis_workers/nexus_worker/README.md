# Nexus worker

## Authentication

The Nexus API requires re-authentication every 30 days.

```bash
uv run python -c "from qnexus.client.auth import login; login()"
```
