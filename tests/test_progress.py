import unittest
from progress_ui import progress_summary, completion_chart, weekly_chart, performance_chart
from sample import sample_roadmap


class ProgressTests(unittest.TestCase):
    def test_progress_handles_zero_partial_full_and_stale_tasks(self):
        plan = sample_roadmap()
        for completed, count in [([], 0), (['1:0', '1:0', 'stale'], 1),
                ([f'{week.week}:{i}' for week in plan.weeks for i in range(len(week.tasks))], 6)]:
            with self.subTest(count=count):
                summary = progress_summary(plan, completed)
                self.assertEqual(summary['completed'], count)
                self.assertEqual(summary['remaining'], 6-count)
                self.assertEqual(sum(w['completed'] for w in summary['weeks']), count)
                self.assertEqual(sum(s['completed'] for s in summary['skills']), count)
                completion_chart(summary).to_dict(validate=True)
                weekly_chart(summary).to_dict(validate=True)

    def test_week_and_skill_aggregation_use_real_task_completion(self):
        plan = sample_roadmap()
        plan.weeks[1].tasks[0].skill = '  plm  '
        summary = progress_summary(plan, ['1:0', '2:1'])
        self.assertEqual(summary['percentage'], 33)
        self.assertEqual([w['completed'] for w in summary['weeks']], [1, 1, 0])
        plm = next(s for s in summary['skills'] if s['skill'] == 'PLM')
        self.assertEqual((plm['completed'], plm['total']), (1, 2))

    def test_one_interview_attempt_is_visible_with_score_bounds(self):
        chart = performance_chart([dict(question='Example', category='Technical',
            feedback=dict(accuracy=4, completeness=3, clarity=7, relevance=8))])
        spec = chart.to_dict(validate=True)
        self.assertEqual(spec['encoding']['y']['scale']['domain'], [0, 10])
        self.assertTrue(spec['mark']['point'])


if __name__ == '__main__':
    unittest.main()
