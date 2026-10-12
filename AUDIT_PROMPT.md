Perform a read-only architecture audit of the LLM provider flow in my project at D:\supply-chain-project. Do not modify any files.

Inspect:

app/llm/router.py

app/core/config.py

config/models.yaml

config/models.resolved.yaml

scripts/probe_models.py

The LLM call sites in workflow/nodes/intake.py, app/services/classification.py, workflow/nodes/recovery.py, app/services/recommendations.py, workflow/nodes/synthesize.py, and workflow/verifier.py

Verify these claims against the implementation:

The application uses Gemini and OpenRouter as alternative providers through a shared LLM router, rather than assigning a provider to each application feature.

fast, reason, and judge have the described responsibilities, and the listed call sites actually invoke those roles.

Candidate models are attempted in configured order. Identify the exact conditions under which the router moves to the next candidate.

Determine whether the router tries a candidate from the other provider after a failure, and whether authentication errors, rate limits, timeouts, and model errors are handled differently.

Identify the exact conditions under which FakeLLM is returned. Does this happen only after all live candidates fail, or can it happen in other modes?

Explain how llm_mode is determined and whether having at least one API key is sufficient to activate live mode.

Explain how models.yaml becomes models.resolved.yaml, which file the runtime actually loads, and whether stale generated configuration can affect execution.

Verify how provider-specific rate limiters, cache, concurrency, call budgets, token budgets, and repair retries interact with the router.

Check whether the existing model probe reports actual exception details and whether its results reliably reflect runtime behavior.

Return a concise report with:

Confirmed claims

Incorrect or partially correct claims

Exact file and function names supporting each finding

Any important differences between intended behavior and actual implementation

The smallest safe changes recommended for the model update

Do not expose secrets. Do not modify files, install packages, or run destructive commands.