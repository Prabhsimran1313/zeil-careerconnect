"""Reproduce exact-overlap baseline vs phrase/alias matching. No AI calls required."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import load_mentors, match_mentor


def main():
    root = Path(__file__).parent
    cases = json.loads((root / 'matching_cases.json').read_text())
    mentors = {m['id']: m for m in load_mentors()}
    rows = []
    for case in cases:
        mentor = mentors[case['mentor_id']]
        before = case['input'].lower() in {s.lower() for s in mentor['skills']}
        after = match_mentor(mentor, [case['input']])[0] > 0
        rows.append(dict(**case, baseline_match=before, improved_match=after,
            baseline_pass=before == case['expected_match'], improved_pass=after == case['expected_match']))
    report = dict(scope='Deterministic mentor matching, not LLM quality', count=len(rows),
        baseline_correct=sum(r['baseline_pass'] for r in rows),
        improved_correct=sum(r['improved_pass'] for r in rows), cases=rows)
    (root / 'matching_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"Baseline: {report['baseline_correct']}/{len(rows)}; improved: {report['improved_correct']}/{len(rows)}")
    return 0 if report['improved_correct'] == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
