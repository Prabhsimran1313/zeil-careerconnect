# ZEIL CareerConnect

CareerConnect helps job seekers prepare for a specific opportunity with personalised learning roadmaps, industry mentor discovery, and interview feedback that becomes the next preparation task. Hackathon pack: **14**.

## Finished prototype

The core feature is a job-specific AI preparation roadmap. Two companion features are mentor discovery/booking and AI practice interviews. The complete journey is **Prepare → Book → Practise → Receive feedback → Improve**.

- **My Roadmap:** role mismatch detection, demonstrated strengths, preparation priorities, 1–4 weekly sections, measurable deliverables and estimated task time. Technical and behavioural question banks.
- **Find Mentors:** ranked, explainable phrase/alias matching; searchable profiles; interviewer portraits from `pic/`; a PLM mentor for CAD migration opportunities; a helpful unmatched state.
- **My Sessions:** 30-minute simulated technical interviews, behavioural interviews or career guidance. Real dates over the next two weeks, Auckland timezone, NZD demo pricing, confirmations, cancellation and `.ics` calendar export. SQLite prevents simultaneous duplicate reservations of the same mentor/time.
- **AI Interview:** typed practice, structured 0–10 accuracy/completeness/clarity/relevance feedback, incorrect vs incomplete answers, stronger example answers and persistent practice history.
- **My Progress:** a completion donut, completed/remaining weekly stacked bars, skill preparation bars, interview score lines when history exists, estimated completed learning time, next actions, a dated activity timeline, follow-up tasks and JSON export. Percentages reflect completed tasks rather than inferred proficiency. Follow-up additions are idempotent.
- **Independent reviewer:** a separate Gemini coaching role checks relevance, missed requirements, unsupported candidate claims and time realism. When enabled during generation, concrete findings trigger revision and another review. Original/final plans and review findings can be exported. Existing plans can also be reviewed and refined manually.

The supplied `zeil_pic/` screenshots were used to understand the original app. The finished interface uses a sidebar profile form, five navigation tabs, a dark hero panel, mint accents, mentor portrait cards and dashboard metrics.

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set GEMINI_API_KEY. Never commit the key.
.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://localhost:8501** and generate a roadmap using the opportunity form. Planning, interview feedback and review require live Gemini. Existing `.env` files should be kept rather than overwritten. Synthetic sample data remains available to automated tests and evaluation scripts, without a sample-loading button in the app.

After successful roadmap generation, the opportunity form clears and returns to its default preparation duration. Failed requests retain the entered fields for correction or retry. The generated plan keeps its original profile, visible under **Saved opportunity & candidate profile**, for all subsequent review and interview feedback. Activity recording starts with new actions; historical events without timestamps are not fabricated.

`GEMINI_MODEL` defaults to `gemini-flash-latest`, preserving the original prototype's model choice. Change it in `.env` if your Google account uses a different available model. `CAREERCONNECT_DB` optionally overrides the SQLite file location.

## Architecture and state

`app.py` provides the Streamlit interface. `models.py` defines strict Pydantic schemas; `ai_service.py` implements planning, independent review and interview coaching. `services.py` handles matching, persistence, dated availability, atomic bookings and calendar exports. `sample.py` contains explicitly synthetic demo content. `mentors.json` contains fictional profiles and photo paths.

Gemini receives a system instruction plus JSON-encoded untrusted source data. All responses are parsed and validated before use, including score limits and exact sequential week numbering. Empty input fails locally. Evaluation uses the profile saved with the plan, so editing an unsubmitted job description cannot change the context of existing interview questions. AI failures preserve existing saved work and do not expose raw provider errors or credentials.

SQLite stores roadmaps, completion, follow-ups, interview answers and feedback. Each browser workspace has an unguessable identifier in the page URL; returning to the same URL restores it. **This is a demo access link, not account authentication.** Anyone with the link can access that workspace. Do not use sensitive personal information in a publicly hosted demo. Different tabs editing the same workspace can overwrite one another; this is not a collaborative editor.

## Verification and bonus evidence

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe evaluation\score_matching.py
# Optional: uses the external Gemini service and may incur API charges
.venv\Scripts\python.exe evaluation\live_ai.py
```

The automated suite covers input validation, invalid JSON and UI recovery, score bounds, week count/numbering, alias matching, database isolation, duplicate booking across workspaces, cancellation ownership, calendar generation, UI empty states, refresh persistence, progress reset, booking UI, feedback-to-plan updates, reviewer revision, stored job context, untrusted-data prompt separation and error recovery. SDK serialization regression tests exercise the real request conversion for all three AI schemas. AI UI tests use explicit mocks rather than pretending to measure live model quality.

**Prove It Works evidence:** [12 fixed matching cases](evaluation/matching_cases.json), [scoring script](evaluation/score_matching.py), and [measured before/after results](evaluation/matching_results.json). The original exact-overlap baseline gets **2/12**; phrase/alias matching gets **12/12** on these cases. This measures a deterministic matching change on a small curated set, not broad AI accuracy or hackathon eligibility.

[AI evaluation scenarios](evaluation/ai_cases.json) document expected outcomes for varied roles, 1/4 week plans, absent skills, role mismatches, prompt injection and weak/strong answers. These are additional scenarios, not measured live results. `live_ai.py` saves actual roadmap/reviewer/weak-vs-strong feedback evidence to `evaluation/live_results.json` only after successful external calls. Live verification was blocked by this environment's network permissions/automatic approval review; no live result is claimed unless that file is generated successfully.

**Gemini request compatibility:** requests use `response_json_schema` with Pydantic's `model_json_schema()`, then validate the response locally. Using `response_schema` with the strict models caused Gemini HTTP 400 (`additional_properties` is not a valid field in the legacy schema format). The corrected format was verified with a live fictional schema diagnostic, without sending candidate data. Authentication, quota, model availability, connectivity and timeout errors now have specific messages without raw provider payloads.

**Schedule reliability:** the requested 1–4 week duration is enforced in the response schema with equal minimum/maximum weekly item counts. Display numbering is normalised without discarding tasks. An incomplete or invalid plan gets one automatic repair request before an error is shown; authentication, quota and network errors do not trigger additional generation calls. If repair fails, the form retains the entered details and the previous saved plan remains intact.

**Strict Shapes:** Pydantic-constrained output plus invalid-output tests. **Two Brains:** separate planner/reviewer roles with retained review/revision evidence; demonstrate a real useful correction before claiming the bonus. These labels describe implemented mechanisms; bonus points are awarded by the hackathon reviewers.

## Deployment and submission

The app is ready to run locally. For a hosted Streamlit deployment, use `app.py` as the entrypoint and `requirements.txt` for installation. Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL` as server environment variables (or Streamlit secrets). For persistent bookings/workspaces, host SQLite on a persistent volume or migrate to a managed database; temporary hosting disks can lose data on restarts. No public deployment or repository push has been performed.

See [DEMO.md](DEMO.md) for the three-minute recording script and submission checklist. The actual video, repository sharing and submission require the project owner. Do not upload `.env` or runtime databases.

## Scope, attribution and future work

The original project supplied the Streamlit/Gemini roadmap prototype, mentor data and reference images. This completion adds the structured planning fields, AI reviewer/interviewer, SQLite services, full user flow, refreshed UI, tests and evaluation scripts with Codex assistance. Libraries: Streamlit, Google GenAI SDK, Pydantic, python-dotenv, pandas, Pillow (through Streamlit) and tzdata. Portraits are user-supplied demo assets; they do not establish the pictured people's identities or mentor participation.

Human mentors, prices and bookings are fictional simulations. AI practice feedback is live when Gemini is available and is coaching guidance, never a hiring decision. Real payments, video calls, verified mentors, authentication, real mentor availability, notifications and voice interviews remain future production features as specified in the roadmap. Model scores may vary and are not a calibrated readiness probability.
