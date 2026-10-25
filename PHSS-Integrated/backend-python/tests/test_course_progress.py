import unittest
from app.agents.learning.course_progress import annotate_plan,lesson_key
class CourseProgressTests(unittest.TestCase):
    def setUp(self):self.plan={'topic':'Arrays','steps':[{'order':1,'concept':'Indexing'},{'order':2,'concept':'Two pointers'}]}
    def test_reading_and_video_share_one_lesson_quiz(self):
        attempts=[{'courseTopic':'Arrays','lessonKey':'1:Indexing','passed':True,'score':.9,'resourceUrl':'https://youtube.com/watch?v=abc','createdAt':'2026-10-25'}]
        p=annotate_plan(self.plan,attempts)['quizProgress'];self.assertEqual(p['completed'],1);self.assertEqual(p['percentage'],50)
    def test_other_courses_do_not_change_completion(self):
        p=annotate_plan(self.plan,[{'courseTopic':'Trees','lessonKey':'1:Indexing','passed':True}])['quizProgress'];self.assertEqual(p['completed'],0)
    def test_duplicate_attempts_do_not_inflate_course_count(self):
        a={'courseTopic':'Arrays','lessonKey':'1:Indexing','passed':True,'createdAt':'2026-10-25'};self.assertEqual(annotate_plan(self.plan,[a,a])['quizProgress']['completed'],1)
    def test_latest_graded_result_drives_completion(self):
        attempts=[{'courseTopic':'Arrays','lessonKey':'1:Indexing','passed':True,'createdAt':'2026-10-24'},{'courseTopic':'Arrays','lessonKey':'1:Indexing','passed':False,'createdAt':'2026-10-25'}];self.assertFalse(annotate_plan(self.plan,attempts)['quizProgress']['lessons']['1:Indexing']['passed'])
    def test_viewing_is_not_quiz_completion(self):
        self.assertEqual(annotate_plan(self.plan,[])['quizProgress']['completed'],0)
    def test_failed_quiz_counts_as_attempted_but_not_passed(self):
        progress=annotate_plan(self.plan,[{'courseTopic':'Arrays','lessonKey':'1:Indexing','score':.4,'passed':False}])['quizProgress']
        self.assertEqual(progress['attempted'],1)
        self.assertEqual(progress['attemptPercentage'],50)
        self.assertEqual(progress['completed'],0)
    def test_module_reordering_keeps_exact_concept_progress(self):
        progress=annotate_plan(self.plan,[{'courseTopic':'Arrays','lessonKey':'7:Indexing','score':.8,'passed':True}])['quizProgress']
        self.assertEqual(progress['completed'],1)
if __name__=='__main__':unittest.main()
