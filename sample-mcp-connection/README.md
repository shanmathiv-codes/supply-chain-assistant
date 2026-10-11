# Trident MCP Query Agent

A registered-agent client for the **Trident MCP server**. It exchanges a
`client_id` / `client_secret` for a short-lived **session token**, then presents
that token as a Bearer credential on every MCP tool call against a context
provider (knowledge base).

Implements the *Registered Agent Integration Guide* (client_id / client_secret
flow). Registration itself is done by the platform team; by the time you run
this, the credential exists and its grant is approved.

The agent holds no domain knowledge — every answer comes back from the
substrate. Its job is authentication plus transport.

## Flow

```
  client_id + client_secret
            │  POST (JSON)
            ▼
  <mcp base>/generate_token  ──►  { token, expires_at, scope[...] }
            │                          the grant, resolved at issue time
            │ Bearer token
            ▼
  POST <mcp base>              (MCP JSON-RPC 2.0, tools/call)
   provider_id + arguments  ──►  grounded answer
```

The token's `scope` is authoritative: it lists exactly which tools this agent
may call on which providers. `--whoami` prints it.

## Layout

| File | Role |
|---|---|
| [query_agent/config.py](query_agent/config.py) | Settings from `.env`; derives the token URL from the MCP base |
| [query_agent/s2s.py](query_agent/s2s.py) | Token sources: `SecretTokenSource` (the flow), `StaticTokenSource` |
| [query_agent/mcp_client.py](query_agent/mcp_client.py) | MCP session, tool calls, auth-retry, diagnostics |
| [query_agent/agent.py](query_agent/agent.py) | `QueryAgent` — one method per granted tool |
| [query.py](query.py) | CLI |

## Setup

```bash
pip install -r requirements.txt
```

Fill in [.env](.env): `SYNAPT_PROVIDER_ID`, `SYNAPT_AGENT_CLIENT_ID`,
`SYNAPT_AGENT_CLIENT_SECRET`. The endpoint defaults to the beta MCP base.

## Use

```bash
python query.py --whoami                    # token + granted scope + live tool list
python query.py --stats                     # the provider's graph stats
python query.py "what is the retry policy?"
python query.py "..." --mode chunks         # raw document text
python query.py "..." --mode search         # graph nodes by meaning
python query.py "..." --mode procedures     # structured SOPs
python query.py "..." --raw --sources --top-k 8
python query.py "..." --provider-id other   # override the provider for one call
```

From Python:

```python
from query_agent import QueryAgent

async with QueryAgent.from_env() as agent:
    print(await agent.answer("what are the escalation rules?"))
    print(await agent.chunks("escalation", top_k=3))
```

`QueryAgent` has one method per granted tool: `ask`/`answer`, `search`,
`traverse`, `chunks`, `procedures`, `stats`, `feedback`, plus `tools` and
`whoami`. `trident_get_schema` is **not** in the registered-agent tool set — use
`stats`.

## Gotchas worth knowing

- **`SYNAPT_MCP_URL` must NOT have a trailing slash.** `/api/mcp/` 307-redirects;
  the URL is used verbatim.
- **`provider_id` is required on every call** — the agent injects it. Never send
  `client_id` or `agent_id` as a tool argument: their absence is what tells the
  server to use your Bearer token's identity (sending `agent_id` switches to the
  federated flow and is rejected).
- **Auth succeeds but every tool call is denied?** That's a grant not yet
  approved (`client '<id>' has no access to '<tool>' on '<provider>'`), or a
  stale token issued before a grant change — re-run (a fresh token is minted
  automatically). If it persists, ask the platform team to confirm the grant.
- **`SYNAPT_VERIFY_SSL=false`** for a self-signed or TLS-inspecting chain; point
  it at the CA bundle to validate properly.
- **Auth failures reach the MCP transport as `CancelledError`, not a 401** (the
  HTTP happens inside a task group). `SynaptMCP` re-probes the endpoint on the
  failure path and reports what the server actually said.
- **Console encoding.** `query.py` forces UTF-8 on stdout so substrate content
  (em-dashes, arrows) doesn't crash `print()` on a Windows codepage.
- **The client_secret is shown once at registration and cannot be recovered.**
  If lost, the platform issues a new one and the old stops working immediately.
