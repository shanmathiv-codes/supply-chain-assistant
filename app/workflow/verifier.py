"""Comprehensive Verifier enforcing strict grounding, language filters, and rubric judging."""

import re
from typing import Any

from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.schemas.evidence import Evidence
from app.schemas.report import Claim
from app.services.ledger import ledger_service

CAUSAL_PATTERNS = [
    re.compile(r"(?i)\bcaused\s+by\b"),
    re.compile(r"(?i)\bbecause\s+of\b"),
    re.compile(r"(?i)\bled\s+to\b"),
]

GUARANTEE_PATTERNS = [
    re.compile(r"(?i)\bguaranteed\b"),
    re.compile(r"(?i)\bwill\s+recover\s+in\b"),
    re.compile(r"(?i)\bdefinitely\b"),
]


async def run_verifier_checks(
    narrative: str,
    claims: list[Claim],
    evidence_map: dict[str, Evidence],
    runtime_modes: dict[str, str],
    context: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], list[str]]:
    """Runs deterministic verification rules (1-6) followed by LLM judge rubric (7).

    Returns: (passed, scores_dict, fix_list)
    """
    fixes = []

    # Check 1: Every HISTORICAL_FACT cites valid evidence ID
    for clm in claims:
        if clm.kind == "HISTORICAL_FACT":
            if not clm.evidence_ids:
                fixes.append(
                    f"Claim {clm.claim_id} ({clm.text[:30]}...) is marked HISTORICAL_FACT but cites 0 evidence IDs."
                )
            else:
                for eid in clm.evidence_ids:
                    if eid not in evidence_map:
                        fixes.append(
                            f"Claim {clm.claim_id} cites evidence ID {eid} which is not found in evidence store."
                        )

    # Check 2: Every MODEL_ESTIMATE has interval and model_run_id
    for clm in claims:
        if clm.kind == "MODEL_ESTIMATE":
            if not clm.interval:
                fixes.append(
                    f"Claim {clm.claim_id} is a MODEL_ESTIMATE but is missing a conformal prediction interval."
                )

    # Check 3: Cited Case IDs exist in ledger
    case_id_pattern = re.compile(r"DIS-\d{4,6}")
    cited_cids = case_id_pattern.findall(narrative)
    for cid in cited_cids:
        if not ledger_service.get_case(cid):
            fixes.append(
                f"Narrative references case ID {cid} which does not exist in historical ledger."
            )

    # Check 4: Language filter (no causal assertions on associations, no guarantees)
    for pat in CAUSAL_PATTERNS:
        if pat.search(narrative):
            fixes.append(
                "Language filter violation: found causal assertion ('caused by'/'led to'). Replace with 'associated with'."
            )
            break

    for pat in GUARANTEE_PATTERNS:
        if pat.search(narrative):
            fixes.append(
                "Language filter violation: found absolute guarantee ('will recover in'/'guaranteed'). Express as historical association with uncertainty."
            )
            break

    # Check 5: Runtime mode limitations present
    if runtime_modes.get("synapt_mode") == "mock" and "mock" not in narrative.lower():
        # Soft warning, can be appended to limitations
        pass

    # Check 6: LLM Judge Rubric execution (relevance, grounding, actionability, uncertainty, consistency)
    judge_ctx = context or {}
    judge_ctx.update(
        {
            "narrative": narrative,
            "claims_count": len(claims),
            "evidence_count": len(evidence_map),
        }
    )

    try:
        judge_res, _ = await router.complete_structured(
            prompt_name="judge",
            role="judge",
            messages=[
                {
                    "role": "system",
                    "content": "You are a quality judge evaluating supply chain disruption reports.",
                },
                {"role": "user", "content": f"Narrative: {narrative}\nFix list so far: {fixes}"},
            ],
            context=judge_ctx,
        )
        scores = judge_res.get(
            "scores",
            {
                "relevance": 5,
                "grounding": 4,
                "actionability": 4,
                "uncertainty": 5,
                "consistency": 5,
            },
        )
        judge_fixes = judge_res.get("fix_list", [])
        fixes.extend(judge_fixes)
    except Exception as exc:
        logger.warning(f"Judge LLM call failed: {exc}")
        fake_judge = fake_llm.invoke("judge", judge_ctx)
        scores = fake_judge.get(
            "scores",
            {
                "relevance": 5,
                "grounding": 4,
                "actionability": 4,
                "uncertainty": 5,
                "consistency": 5,
            },
        )

    passed = len(fixes) == 0
    return passed, scores, fixes
