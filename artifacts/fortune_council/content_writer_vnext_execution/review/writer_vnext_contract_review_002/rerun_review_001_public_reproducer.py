from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
REVIEW_001 = REPO_ROOT / "artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_contract_review_001/public_reproducer.py"
sys.path.insert(0, str(REPO_ROOT))


def load_review_001_module():
    spec = importlib.util.spec_from_file_location("writer_vnext_review_001_public_reproducer", REVIEW_001)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {REVIEW_001}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_review_001_module()
    cases = [module.evaluate(name, payload, valid, findings) for name, payload, valid, findings in module.build_cases()]
    legacy = module.legacy_candidate()
    before = module.deepcopy(legacy)
    legacy_manifest = module.manifest()
    legacy_manifest["legacy_candidate"] = legacy
    legacy_manifest["legacy_candidate_sha256"] = module.contracts.artifact_sha256(legacy)
    module.contracts.validate_manifest(legacy_manifest)
    mutation_check = {
        "name": "legacy_candidate_not_mutated_by_vnext_validation",
        "passed": legacy == before,
        "before_sha256": module.contracts.artifact_sha256(before),
        "after_sha256": module.contracts.artifact_sha256(legacy),
    }
    output = {
        "summary": {
            "total_cases": len(cases) + 1,
            "passed_cases": sum(1 for case in cases if case["passed"]) + int(mutation_check["passed"]),
            "failed_cases": [case["name"] for case in cases if not case["passed"]],
            "mutation_check_passed": mutation_check["passed"],
        },
        "cases": cases,
        "legacy_mutation_check": mutation_check,
    }
    output_path = Path(__file__).with_name("review_001_public_reproducer_rerun_results.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if output["summary"]["passed_cases"] == output["summary"]["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
