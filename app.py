import base64
import html
import json
import os
from io import BytesIO
from datetime import datetime
from uuid import UUID, uuid4
import streamlit as st
from models import CareerRoadmap
from ai_service import generate_roadmap, review_roadmap, evaluate_answer, error_message
from services import (ROOT, TZ, SESSION_TYPES, load_workspace, save_workspace, load_mentors,
    match_mentor, available_slots, book_session, bookings_for, cancel_booking, calendar_event)
from PIL import Image
from progress_ui import render_task_charts, performance_chart

st.set_page_config(page_title='ZEIL CareerConnect', page_icon='✳️', layout='wide')
if not os.getenv('GEMINI_API_KEY'):
    try:
        if st.secrets.get('GEMINI_API_KEY'):
            os.environ['GEMINI_API_KEY'] = str(st.secrets['GEMINI_API_KEY'])
        if st.secrets.get('GEMINI_MODEL'):
            os.environ['GEMINI_MODEL'] = str(st.secrets['GEMINI_MODEL'])
    except FileNotFoundError:
        pass
st.markdown('''<style>
.stApp{background:#f8f9fc;color:#172337}.block-container{max-width:1250px;padding-top:5.5rem}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:1rem}
h1,h2,h3{letter-spacing:-.035em}[data-testid="stSidebar"]{background:white;border-right:1px solid #e8ebf2}
[data-testid="stMetric"]{background:white;border:1px solid #e5eaf2;border-radius:16px;padding:18px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px;background:white}
.stButton>button,.stDownloadButton>button{border-radius:10px}
[data-testid="InputInstructions"]{display:none!important}
.hero{background:#162438;border-radius:22px;padding:36px 40px;color:white;margin:12px 0 24px}
.hero h1{color:white;font-size:2.7rem;line-height:1.15;margin:10px 0}.hero p{color:#cbd7e7;max-width:650px}
.eyebrow{font-size:.73rem;letter-spacing:.16em;color:#96ebd4;font-weight:700}
.brand{font-size:1.35rem;font-weight:800;letter-spacing:-.05em}.brand span{color:#0c9a77}
.portrait{width:100%;height:180px;object-fit:cover;object-position:center 35%;border-radius:12px;margin-bottom:14px}
.tag{display:inline-block;background:#edf7f4;color:#08795e;font-size:.75rem;padding:4px 9px;border-radius:6px;margin:2px}
.stTabs [data-baseweb="tab-list"]{gap:22px}.stTabs [data-baseweb="tab"]{font-weight:600}
@media(max-width:640px){.hero{padding:24px}.hero h1{font-size:2rem}}
</style>''', unsafe_allow_html=True)


def empty_workspace():
    return dict(plan=None, profile=None, initial_plan=None, review=None, revision_review=None,
        completed=[], followups=[], attempts=[], activity=[], sample=False, plan_id=str(uuid4()))


if 'owner' not in st.session_state:
    try:
        owner = str(UUID(st.query_params.get('workspace', '')))
    except (ValueError, TypeError):
        owner = str(uuid4())
    st.session_state.owner = owner
    st.query_params['workspace'] = owner
    st.session_state.work = load_workspace(owner) or empty_workspace()
work = st.session_state.work
work.setdefault('activity', [])
st.session_state.setdefault('opportunity_form_revision', 0)


@st.cache_data
def portrait(photo):
    with Image.open(ROOT / photo) as im:
        im.thumbnail((800, 600))
        out = BytesIO()
        im.convert('RGB').save(out, format='JPEG', quality=85)
    return base64.b64encode(out.getvalue()).decode()


def persist():
    save_workspace(st.session_state.owner, work)


def record_activity(kind, label):
    work['activity'].append(dict(id=str(uuid4()), kind=kind, label=label,
        timestamp=datetime.now(TZ).isoformat()))


def install_plan(plan, profile, initial=None, review=None, revision_review=None, sample=False):
    profile = profile.copy()
    activity = work.get('activity', []).copy()
    work.update(empty_workspace())
    work.update(plan=plan.model_dump(), profile=profile, initial_plan=initial,
        review=review, revision_review=revision_review, sample=sample, activity=activity)
    record_activity('Roadmap', ('Sample plan loaded: ' if sample else 'Roadmap saved: ') + plan.detected_job_title)
    persist()


def fail(error):
    st.error(error_message(error))


with st.sidebar:
    st.markdown('<div class="brand">ZEIL<span> / </span>CareerConnect</div>', unsafe_allow_html=True)
    st.caption('Your next role. Your own path.')
    st.divider()
    st.subheader('Your target opportunity')
    form_revision = st.session_state.opportunity_form_revision
    with st.form(f'profile_form_{form_revision}'):
        title = st.text_input('Target job title', placeholder='e.g. Data Engineer', key=f'opportunity_title_{form_revision}', max_chars=150)
        description = st.text_area('Job description', key=f'opportunity_description_{form_revision}', height=170, placeholder='Paste the actual job advertisement…', max_chars=15000)
        skills = st.text_area('Your skills & experience', key=f'opportunity_skills_{form_revision}', placeholder='Python, SQL, a university project…', max_chars=5000)
        weeks = st.selectbox('Preparation time (weeks)', [1, 2, 3, 4], index=2, key=f'opportunity_weeks_{form_revision}')
        reviewer = st.checkbox('Review & refine with a second AI role', value=True, key=f'opportunity_reviewer_{form_revision}')
        submitted = st.form_submit_button('Generate my roadmap', type='primary', use_container_width=True)
    if submitted:
        profile = dict(job_title=title, job_description=description, candidate_skills=skills, weeks=weeks)
        if not title.strip() or not description.strip() or not skills.strip():
            st.warning('Enter a target title, job description and your existing skills.')
        else:
            with st.spinner('Planning your preparation…'):
                try:
                    initial = generate_roadmap(profile)
                    plan, review, second = initial, None, None
                    if reviewer:
                        try:
                            review = review_roadmap(profile, initial)
                            if review.needs_revision:
                                plan = generate_roadmap(profile, initial.model_dump(), review.model_dump())
                                second = review_roadmap(profile, plan)
                        except Exception as review_error:
                            st.session_state.review_notice = 'Independent review could not finish. Your valid plan was saved. ' + error_message(review_error)
                    install_plan(plan, profile, initial.model_dump(), review.model_dump() if review else None, second.model_dump() if second else None)
                    st.session_state.opportunity_form_revision += 1
                    st.rerun()
                except Exception as error:
                    fail(error)

st.markdown('<div class="brand">ZEIL<span> / </span>CareerConnect</div>', unsafe_allow_html=True)
st.markdown('''<div class="hero"><div class="eyebrow">FROM OPPORTUNITY TO CONFIDENCE</div>
<h1>Your next chapter<br>starts with a plan.</h1><p>Prepare for the role you want. Build the right skills, learn from industry mentors, and turn interview feedback into your next step.</p></div>''', unsafe_allow_html=True)
if 'review_notice' in st.session_state:
    st.warning(st.session_state.pop('review_notice'))
plan = CareerRoadmap.model_validate(work['plan']) if work['plan'] else None
bookings = bookings_for(st.session_state.owner)
tasks = [(f'{w.week}:{i}', t) for w in plan.weeks for i, t in enumerate(w.tasks)] if plan else []
done = sum(key in work['completed'] for key, _ in tasks)
for col, label, value in zip(st.columns(4), ['Learning tasks', 'Plan completed', 'Practice attempts', 'Mentor sessions'],
    [f'{done} / {len(tasks)}', f'{round(100*done/len(tasks)) if tasks else 0}%', len(work['attempts']), len(bookings)]):
    col.metric(label, value)
st.write('')
tabs = st.tabs(['My Roadmap', 'Find Mentors', 'My Sessions', 'AI Interview', 'My Progress'])


def followup_checkboxes(prefix):
    for item in work['followups']:
        checked = st.checkbox(item['task'], value=item['done'], key=f'{prefix}_{item["id"]}')
        if checked != item['done']:
            item['done'] = checked
            record_activity('Follow-up', ('Completed: ' if checked else 'Reopened: ') + item['task'])
            persist()
            st.rerun()


with tabs[0]:
    if not plan:
        st.subheader('A roadmap built around your opportunity')
        st.write('Add a job description and your experience in the sidebar. Turn the gap between where you are and where you want to be into a practical weekly plan.')
        for col, number, heading, body in zip(st.columns(3), ['01', '02', '03'], ['Prepare with purpose', 'Connect with a mentor', 'Practise and improve'], ['Measurable tasks for your actual job requirements.', 'Industry expertise matched to your preparation needs.', 'Constructive feedback that becomes your next task.']):
            with col, st.container(border=True):
                st.caption(number)
                st.subheader(heading)
                st.write(body)
    else:
        if work['sample']:
            st.info('Sample roadmap for exploring the app. Interview evaluation uses live Gemini; this sample is not AI-generated.')
        st.subheader(plan.detected_job_title)
        st.caption(f'{len(plan.weeks)} weeks · Personalised to your saved profile')
        with st.expander('Saved opportunity & candidate profile'):
            st.write('**Target title:** ' + work['profile']['job_title'])
            st.write('**Job description**')
            st.write(work['profile']['job_description'])
            st.write('**Your stated experience**')
            st.write(work['profile']['candidate_skills'])
        if plan.role_mismatch_note:
            st.info(plan.role_mismatch_note)
        a, b = st.columns(2)
        with a, st.container(border=True):
            st.subheader('Your starting strengths')
            for strength in plan.strengths:
                st.write('✓ ' + strength)
            if not plan.strengths:
                st.caption('No relevant strengths demonstrated yet. Start with the foundations.')
        with b, st.container(border=True):
            st.subheader('Where to focus next')
            for priority in plan.preparation_priorities:
                st.write('↗ ' + priority)
        st.subheader('Your preparation plan')
        st.progress(done / len(tasks), text=f'{done} of {len(tasks)} learning tasks completed')
        for week in plan.weeks:
            with st.expander(f'Week {week.week} · {week.focus}', expanded=True):
                for i, task in enumerate(week.tasks):
                    key = f'{week.week}:{i}'
                    checked = st.checkbox(task.title, value=key in work['completed'], key=f'task_{work["plan_id"]}_{key}')
                    if checked != (key in work['completed']):
                        if checked:
                            work['completed'].append(key)
                        else:
                            work['completed'].remove(key)
                        record_activity('Learning task', ('Completed: ' if checked else 'Reopened: ') + task.title)
                        persist()
                        st.rerun()
                    st.caption(f'{task.skill} · {task.duration_minutes} minutes')
                    st.write(task.description)
                    st.caption('Deliverable: ' + task.deliverable)
        if work['followups']:
            st.subheader('Feedback-driven next steps')
            followup_checkboxes('roadmap_follow')
        with st.expander('Interview topics to practise'):
            for question in plan.interview_questions:
                st.write(f'**{question.category}** · {question.question}')
        with st.expander('Independent AI quality review'):
            if work['review']:
                st.write(work['review']['summary'])
                for issue in work['review']['issues']:
                    st.write('• ' + issue)
                for recommendation in work['review']['recommendations']:
                    st.caption('Recommendation: ' + recommendation)
                if work['revision_review']:
                    st.write('**Review after revision:** ' + work['revision_review']['summary'])
                    if work['revision_review']['needs_revision']:
                        st.warning('The reviewer still identified gaps. Consider refining your profile and regenerating.')
                st.download_button('Download original plan & review evidence', json.dumps(dict(initial_plan=work['initial_plan'], review=work['review'], final_plan=work['plan'], revision_review=work['revision_review']), indent=2), 'plan-review.json', 'application/json')
            else:
                st.caption('No independent review recorded for this plan.')
            if st.button('Review current plan'):
                try:
                    with st.spinner('Reviewing relevance and realism…'):
                        result = review_roadmap(work['profile'], plan)
                        work['review'] = result.model_dump()
                        work['initial_plan'] = work['plan']
                        work['revision_review'] = None
                        persist()
                        st.rerun()
                except Exception as error:
                    fail(error)
            if work['review'] and work['review']['needs_revision'] and st.button('Apply reviewer recommendations'):
                try:
                    with st.spinner('Refining your preparation plan…'):
                        revised = generate_roadmap(work['profile'], work['plan'], work['review'])
                        recheck = review_roadmap(work['profile'], revised)
                        install_plan(revised, work['profile'], work['initial_plan'], work['review'], recheck.model_dump())
                        st.rerun()
                except Exception as error:
                    fail(error)
        st.download_button('Download preparation plan', json.dumps(work, indent=2), 'careerconnect-plan.json', 'application/json')

mentors = load_mentors()
with tabs[1]:
    st.subheader('The right conversation can change your direction.')
    st.caption('Fictional mentor profiles with supplied demo portraits. All prices and bookings are simulated.')
    search = st.text_input('Search mentors by name, skill or specialisation', placeholder='Try Python, PLM, or data engineering')
    show_all = st.checkbox('Browse all mentors', value=not bool(plan))
    ranked = sorted(mentors, key=lambda m: match_mentor(m, plan.preparation_priorities)[0] if plan else 0, reverse=True)
    visible = [m for m in ranked if (show_all or (plan and match_mentor(m, plan.preparation_priorities)[0])) and search.lower() in ' '.join([m['name'], m['role'], m['specialisation'], *m['skills']]).lower()]
    if not visible:
        st.info('No mentors match these preparation needs or search terms. Clear your search or browse all mentors for career guidance.')
    grid = st.columns(3)
    for i, mentor in enumerate(visible):
        with grid[i % 3], st.container(border=True):
            encoded = portrait(mentor['photo'])
            st.markdown(f'<img class="portrait" src="data:image/jpeg;base64,{encoded}" alt="Demo portrait for {html.escape(mentor["name"])}">', unsafe_allow_html=True)
            st.subheader(mentor['name'])
            st.write(mentor['role'])
            st.caption(f'{mentor["experience"]} years experience · {mentor["specialisation"]}')
            st.markdown(' '.join(f'<span class="tag">{html.escape(s)}</span>' for s in mentor['skills'][:5]), unsafe_allow_html=True)
            matches = match_mentor(mentor, plan.preparation_priorities)[1] if plan else []
            st.write('**Why this mentor?**')
            st.caption('Relevant expertise: ' + ', '.join(matches) if matches else 'Explore their expertise for general career guidance. No direct preparation match yet.')
            st.write(f'**NZ${mentor["price_nzd"]}** / 30 minutes')
            with st.expander('Book a demo session'):
                slots = available_slots(mentor)
                if not slots:
                    st.info('No upcoming slots. Check another mentor.')
                else:
                    with st.form(f'book_{mentor["id"]}'):
                        kind = st.selectbox('Session type', SESSION_TYPES, key=f'kind_{mentor["id"]}')
                        slot = st.selectbox('Available time · Pacific/Auckland', slots, format_func=lambda s: datetime.fromisoformat(s).strftime('%a %d %b, %I:%M %p %Z'), key=f'slot_{mentor["id"]}')
                        st.caption('30 minutes · Demo reservation · No charge')
                        confirm = st.form_submit_button('Confirm demo booking', type='primary')
                    if confirm:
                        try:
                            book_session(st.session_state.owner, mentor, slot, kind, plan.detected_job_title if plan else 'Career exploration')
                            record_activity('Booking', 'Demo session reserved with ' + mentor['name'])
                            persist()
                            st.session_state.booking_notice = f'Session with {mentor["name"]} confirmed. Open My Sessions for details.'
                            st.rerun()
                        except ValueError as error:
                            st.warning(str(error))

with tabs[2]:
    st.subheader('Make space for your next step')
    st.caption('Your simulated mentor appointments · Times shown in Pacific/Auckland')
    if 'booking_notice' in st.session_state:
        st.success(st.session_state.pop('booking_notice'))
    if not bookings:
        st.info('No sessions booked yet. Find a mentor and reserve a demo session to get started.')
    for booking in bookings:
        with st.container(border=True):
            a, b = st.columns([3, 1])
            with a:
                st.subheader(booking['mentor_name'])
                st.write(booking['session_type'] + ' · ' + booking['role'])
                st.write(datetime.fromisoformat(booking['slot']).strftime('%A %d %B %Y · %I:%M %p %Z'))
                st.caption(f'30 minutes · NZ${booking["price_nzd"]} demo price · No payment collected')
                st.caption('Demo confirmation ' + booking['id'][:8].upper() + ' · No actual call is scheduled')
            with b:
                st.download_button('Add to calendar', calendar_event(booking), 'demo-session.ics', 'text/calendar', key=f'ics_{booking["id"]}')
                if st.button('Cancel demo session', key=f'cancel_{booking["id"]}'):
                    cancel_booking(st.session_state.owner, booking['id'])
                    record_activity('Booking', 'Demo session cancelled with ' + booking['mentor_name'])
                    persist()
                    st.rerun()


def show_feedback(attempt, prefix):
    feedback = attempt['feedback']
    with st.container(border=True):
        st.subheader('Your practice feedback')
        st.caption(feedback['assessment'] + ' answer · AI coaching scores, not a hiring assessment')
        for col, field in zip(st.columns(4), ['accuracy', 'completeness', 'clarity', 'relevance']):
            col.metric(field.title(), f'{feedback[field]} / 10')
        a, b = st.columns(2)
        with a:
            st.write('**What went well**')
            for item in feedback['strengths']:
                st.write('✓ ' + item)
        with b:
            st.write('**What to improve**')
            for item in feedback['improvements']:
                st.write('↗ ' + item)
        with st.expander('A stronger example answer'):
            st.write(feedback['suggested_answer'])
            st.caption('An illustrative answer. Adapt it to your own real experience.')
        st.write('**Recommended next task**')
        st.write(feedback['next_practice_task'])
        added = any(t['source'] == attempt['id'] for t in work['followups'])
        if st.button('Added to your plan' if added else 'Add to my preparation plan', disabled=added, key=f'{prefix}_{attempt["id"]}'):
            work['followups'].append(dict(id=str(uuid4()), task=feedback['next_practice_task'], source=attempt['id'], done=False))
            record_activity('Follow-up', 'Added preparation task: ' + feedback['next_practice_task'])
            persist()
            st.rerun()


with tabs[3]:
    st.subheader('Practise here. Show up with confidence.')
    st.caption('Written, job-specific AI practice · Feedback feeds back into your preparation plan')
    if not plan:
        st.info('Generate a roadmap to unlock interview questions.')
    else:
        category = st.radio('Practice focus', ['Technical', 'Behavioural'], horizontal=True)
        questions = [q.question for q in plan.interview_questions if q.category == category]
        question = st.selectbox('Choose a question', questions)
        st.info(question)
        with st.form(f'answer_{work["plan_id"]}_{category}_{questions.index(question)}'):
            answer = st.text_area('Your answer', height=190, placeholder='Explain your approach with concrete examples. For behavioural questions, try situation → task → action → result.', max_chars=10000)
            evaluate = st.form_submit_button('Get AI feedback', type='primary')
        if evaluate:
            if not answer.strip():
                st.warning('Write your answer before requesting feedback.')
            else:
                try:
                    with st.spinner('Reviewing your answer against this opportunity…'):
                        feedback = evaluate_answer(work['profile'], dict(category=category, question=question), answer)
                        work['attempts'].append(dict(id=str(uuid4()), question=question, category=category, answer=answer, timestamp=datetime.now(TZ).isoformat(), feedback=feedback.model_dump()))
                        record_activity('Interview', category + ' answer evaluated: ' + question)
                        persist()
                        st.rerun()
                except Exception as error:
                    fail(error)
        if work['attempts']:
            latest = work['attempts'][-1]
            st.caption('Latest evaluated question: ' + latest['question'])
            show_feedback(latest, 'latest')
        with st.expander(f'Your practice history ({len(work["attempts"])})'):
            for attempt in reversed(work['attempts']):
                st.write('**' + attempt['question'] + '**')
                st.caption(attempt['timestamp'][:16].replace('T', ' ') + ' · ' + attempt['category'])
                st.write(attempt['answer'])
                show_feedback(attempt, 'history')

with tabs[4]:
    st.subheader('Small steps. Visible progress.')
    st.caption('Preparation activity and practice feedback, not a prediction of getting hired.')
    if not plan:
        st.info('Your progress starts with a preparation roadmap.')
    else:
        minutes = sum(t.duration_minutes for key, t in tasks if key in work['completed'])
        st.caption('Target role: ' + plan.detected_job_title)
        for column, label, value in zip(st.columns(3), ['Estimated learning covered', 'Follow-up tasks completed', 'Practice attempts'],
                [f'{minutes // 60}h {minutes % 60}m', f"{sum(t['done'] for t in work['followups'])} / {len(work['followups'])}", len(work['attempts'])]):
            column.metric(label, value)
        st.write('')
        render_task_charts(plan, work['completed'])
        if done < len(tasks):
            st.write('**Next recommended action:** ' + next(t.title for key, t in tasks if key not in work['completed']))
        else:
            st.success('Your roadmap tasks are complete. Practise an interview and review your follow-up tasks.')
        if work['followups']:
            st.subheader('Your improvement checklist')
            followup_checkboxes('progress_follow')
        if work['attempts']:
            st.subheader('Interview performance')
            st.altair_chart(performance_chart(work['attempts']), use_container_width=True)
            st.caption('Scores are AI coaching estimates; question difficulty can vary across attempts.')
            st.write('**Latest improvement areas**')
            for item in work['attempts'][-1]['feedback']['improvements']:
                st.write('• ' + item)
        else:
            st.info('Try your first AI interview question to discover what to work on next.')
        if work['activity']:
            with st.expander('Your activity timeline', expanded=True):
                st.caption('Recorded activity in this workspace · Pacific/Auckland')
                for event in reversed(work['activity'][-20:]):
                    stamp = datetime.fromisoformat(event['timestamp']).astimezone(TZ).strftime('%d %b · %I:%M %p')
                    st.caption(stamp + ' · ' + event['kind'])
                    st.write(event['label'])
        st.download_button('Export my progress & feedback', json.dumps(work, indent=2), 'careerconnect-progress.json', 'application/json')
st.divider()
st.caption('ZEIL CareerConnect · Prepare → Practise → Receive feedback → Improve · Hackathon prototype')
