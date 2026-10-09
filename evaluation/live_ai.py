"""Optional paid API smoke test; saves actual structured outputs as review evidence."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_service import generate_roadmap, review_roadmap, evaluate_answer
from sample import PROFILE


def main():
    plan = generate_roadmap(PROFILE)
    print('Live roadmap: valid 3-week plan', flush=True)
    review = review_roadmap(PROFILE, plan)
    print('Live review: validated', flush=True)
    final = generate_roadmap(PROFILE, plan.model_dump(), review.model_dump()) if review.needs_revision else plan
    recheck = review_roadmap(PROFILE, final) if review.needs_revision else review
    question = {'category': 'Technical', 'question': 'How would you validate engineering metadata during a migration?'}
    weak = evaluate_answer(PROFILE, question, 'I would compare record counts and use Python to find missing values.')
    strong = evaluate_answer(PROFILE, question, 'I would baseline source counts by part and revision, define ID mappings and check referential integrity of parent-child assemblies. I would validate mandatory attributes and types, detect duplicates and orphan references, and compare file checksums for CAD assets. I would reconcile source and destination counts and content by migration batch using Python and SQL, retain audit logs and quarantine exceptions for review with the CAD administrator. I would test rollback and sample records in Teamcenter before approval.')
    result = dict(profile=PROFILE, initial_plan=plan.model_dump(), review=review.model_dump(),
        final_plan=final.model_dump(), revision_review=recheck.model_dump(),
        weak_feedback=weak.model_dump(), strong_feedback=strong.model_dump())
    (Path(__file__).parent / 'live_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Weak completeness:', weak.completeness, 'Strong completeness:', strong.completeness, flush=True)


if __name__ == '__main__':
    main()
