"""Charts reflect saved task completion, not inferred skill proficiency."""
from collections import OrderedDict
import altair as alt
import pandas as pd
import streamlit as st

GREEN = '#0c9876'
REMAINING = '#dde5ef'
STATUS_SCALE = alt.Scale(domain=['Completed', 'Remaining'], range=[GREEN, REMAINING])


def progress_summary(plan, completed):
    checked = set(completed)
    weeks, skills = [], OrderedDict()
    for week in plan.weeks:
        finished = 0
        for index, task in enumerate(week.tasks):
            done = int(f'{week.week}:{index}' in checked)
            finished += done
            key = ' '.join(task.skill.split()).casefold()
            area = skills.setdefault(key, dict(skill=task.skill.strip(), completed=0, total=0))
            area['completed'] += done
            area['total'] += 1
        weeks.append(dict(week=f'Week {week.week}', focus=week.focus,
            completed=finished, remaining=len(week.tasks)-finished, total=len(week.tasks)))
    total = sum(w['total'] for w in weeks)
    done = sum(w['completed'] for w in weeks)
    return dict(total=total, completed=done, remaining=total-done,
        percentage=round(100*done/total) if total else 0, weeks=weeks, skills=list(skills.values()))


def completion_chart(summary):
    data = pd.DataFrame([dict(status='Completed', tasks=summary['completed'], order=0),
        dict(status='Remaining', tasks=summary['remaining'], order=1)])
    arcs = alt.Chart(data).mark_arc(innerRadius=90, outerRadius=120, cornerRadius=3).encode(
        theta=alt.Theta('tasks:Q'), color=alt.Color('status:N', scale=STATUS_SCALE,
            legend=alt.Legend(title=None, orient='bottom')),
        order=alt.Order('order:Q'), tooltip=['status:N', alt.Tooltip('tasks:Q', title='Tasks')])
    center = alt.Chart(pd.DataFrame([{'label': f"{summary['percentage']}%"}])).mark_text(
        fontSize=40, fontWeight=700, color='#172337').encode(text='label:N')
    return (arcs + center).properties(height=285).configure_view(stroke=None)


def weekly_chart(summary):
    rows = [dict(week=w['week'], focus=w['focus'], status=status, tasks=w[key], order=order)
        for w in summary['weeks']
        for status, key, order in [('Completed', 'completed', 0), ('Remaining', 'remaining', 1)]]
    return alt.Chart(pd.DataFrame(rows)).mark_bar(size=44, cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5).encode(
        x=alt.X('week:N', sort=[w['week'] for w in summary['weeks']], axis=alt.Axis(title=None, labelAngle=0)),
        y=alt.Y('tasks:Q', stack='zero', axis=alt.Axis(title='Learning tasks', tickMinStep=1)),
        color=alt.Color('status:N', scale=STATUS_SCALE, legend=alt.Legend(title=None, orient='bottom')),
        order=alt.Order('order:Q'), tooltip=['week:N', 'focus:N', 'status:N', alt.Tooltip('tasks:Q', title='Tasks')]
    ).properties(height=285).configure_view(stroke=None)


def performance_chart(attempts):
    rows = [dict(attempt=i+1, criterion=field.title(), score=a['feedback'][field],
        question=a['question'], category=a['category'])
        for i, a in enumerate(attempts)
        for field in ['accuracy', 'completeness', 'clarity', 'relevance']]
    return alt.Chart(pd.DataFrame(rows)).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X('attempt:Q', axis=alt.Axis(title='Practice attempt', tickMinStep=1)),
        y=alt.Y('score:Q', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='Practice score', tickMinStep=1)),
        color=alt.Color('criterion:N', scale=alt.Scale(range=[GREEN, '#4263b8', '#e3a135', '#8b63b8']),
            legend=alt.Legend(title=None, orient='bottom')),
        tooltip=['attempt:Q', 'criterion:N', 'score:Q', 'category:N', 'question:N']
    ).properties(height=280).configure_view(stroke=None)


def render_task_charts(plan, completed):
    summary = progress_summary(plan, completed)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader('Learning completion')
        st.altair_chart(completion_chart(summary), use_container_width=True)
        st.caption(f"{summary['completed']} of {summary['total']} roadmap tasks finished")
    with right, st.container(border=True):
        st.subheader('Weekly preparation')
        st.altair_chart(weekly_chart(summary), use_container_width=True)
        st.caption('Hover over a bar to see its focus and task counts.')
    with st.container(border=True):
        st.subheader('Skill preparation by area')
        st.caption('Completed learning tasks in each area. These percentages describe preparation activity, not skill proficiency.')
        for area in summary['skills']:
            fraction = area['completed'] / area['total']
            label, bar, percentage = st.columns([2, 4, 1])
            label.write(area['skill'])
            bar.progress(fraction, text=f"{area['completed']} / {area['total']} tasks")
            percentage.write(f'**{round(100*fraction)}%**')
