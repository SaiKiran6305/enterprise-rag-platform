"""Run a curated JSONL evaluation against one workspace; never invent labels."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.ai import OpenAIProvider
from app.services.answer import FALLBACK, format_context, validate_answer
from app.services.retrieval import search


def run(dataset: Path, workspace_id: UUID, output: Path, top_k: int):
    settings = get_settings()
    provider = OpenAIProvider(settings, workspace_id)
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    results = []
    with SessionLocal() as db:
        for case in cases:
            hits = search(db, workspace_id, case["question"], top_k, settings, provider)
            answer, citations = validate_answer(provider.answer(case["question"], format_context(hits)), hits) if hits else (FALLBACK, [])
            expected = case.get("expected_document")
            page = case.get("expected_page")
            retrieved = any(h.document.original_filename == expected and (page is None or h.chunk.page_number == page) for h in hits) if expected else None
            should_refuse = case.get("answerable") is False
            results.append({"question": case["question"], "expected_document": expected, "expected_page": page, "retrieval_hit": retrieved, "expected_refusal": should_refuse, "refused": answer == FALLBACK, "answer": answer, "citations": citations, "manual_faithfulness_review": None})
    labeled = [r for r in results if r["retrieval_hit"] is not None]
    refusal = [r for r in results if r["expected_refusal"]]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "workspace_id": str(workspace_id), "top_k": top_k, "case_count": len(results), "retrieval_recall_at_k": sum(r["retrieval_hit"] for r in labeled) / len(labeled) if labeled else None, "refusal_accuracy": sum(r["refused"] for r in refusal) / len(refusal) if refusal else None, "note": "Citation support and answer faithfulness require human review of the evidence; they are not inferred from the model's own output.", "cases": results}
    output.write_text(json.dumps(report, indent=2, default=str))
    print(f"Wrote {output} ({len(results)} cases)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation-report.json"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    run(args.dataset, args.workspace_id, args.output, args.top_k)
