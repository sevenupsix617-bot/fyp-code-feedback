"""Student-level class evidence and directory regressions; no LLM/API calls."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .analytics import build_class_analytics, build_class_evidence
from .models import CodeFeedbackRecord, Question
from .taxonomy import TOPIC_TAXONOMY


class ClassEvidenceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(username="teacher", is_staff=True)
        self.first = User.objects.create_user(username="first")
        self.second = User.objects.create_user(username="second")
        self.unpractised = User.objects.create_user(username="no_practice")
        self.question = Question.objects.create(title="Loop", problem_statement="Sum", topic_tags="iteration_range")

    def attempt(self, user, **kwargs):
        defaults = dict(user=user, question=self.question, problem_statement="Sum",
                        student_code="print(1)", execution_status="success",
                        output_comparison_status="mismatch", classification_outcome="peci_error",
                        peci_error_code="N", peci_error_label="Misspelled names or keywords",
                        error_category="Misspelled names or keywords", concept_reference="Unknown")
        defaults.update(kwargs)
        return CodeFeedbackRecord.objects.create(**defaults)

    def topic(self, context):
        return next(t for t in context["topic_evidence"] if t["id"] == "iteration_range")

    def test_ten_attempts_by_one_student_count_as_one_person(self):
        for _ in range(10):
            self.attempt(self.first)
        context = build_class_evidence()
        self.assertEqual(context["common_errors"][0]["student_count"], 1)
        self.assertEqual(context["common_errors"][0]["attempt_count"], 10)
        topic = self.topic(context)
        self.assertEqual((topic["affected_students"], topic["practising_students"]), (1, 1))
        self.assertEqual(topic["attempt_count"], 10)

    def test_two_students_once_each_count_as_two_people(self):
        self.attempt(self.first)
        self.attempt(self.second)
        context = build_class_evidence()
        self.assertEqual(context["common_errors"][0]["student_count"], 2)
        self.assertEqual(context["common_errors"][0]["attempt_count"], 2)
        self.assertEqual(self.topic(context)["affected_students"], 2)

    def test_latest_topic_attempt_and_unpractised_denominator(self):
        self.attempt(self.first)
        self.attempt(self.first, solved=True, classification_outcome="no_error", error_category="No Error", peci_error_code="")
        self.attempt(self.second)
        context = build_class_analytics()
        topic = self.topic(context)
        self.assertEqual((topic["affected_students"], topic["practising_students"]), (1, 2))
        self.assertEqual(context["follow_up_student_count"], 1)
        self.assertEqual(context["practising_student_count"], 2)
        self.assertEqual(context["student_count"], 3)
        self.assertEqual(len(context["topic_evidence"]), 8)
        unpractised = next(t for t in context["topic_evidence"] if t["id"] == "functions_returns")
        self.assertFalse(unpractised["has_evidence"])
        self.assertEqual(unpractised["affected_students"], 0)
        self.assertEqual(unpractised["practising_students"], 0)

    def test_fixed_tags_not_model_topic_mentions_define_topic_evidence(self):
        self.attempt(self.first, concept_reference="Functions and Return Values")
        context = build_class_evidence()
        self.assertEqual(self.topic(context)["practising_students"], 1)
        functions = next(t for t in context["topic_evidence"] if t["id"] == "functions_returns")
        self.assertFalse(functions["has_evidence"])

    def test_staff_anonymous_inactive_and_manual_experiments_are_excluded(self):
        self.attempt(self.teacher)
        self.attempt(None)
        self.attempt(self.first, question=None)
        self.second.is_active = False
        self.second.save()
        self.attempt(self.second)
        context = build_class_evidence()
        self.assertEqual(context["practice_submission_count"], 0)
        self.assertFalse(context["common_errors"])

    def test_modern_project_and_legacy_sources_remain_distinct_and_unchanged(self):
        peci = self.attempt(self.first)
        project = self.attempt(self.first, classification_outcome="runtime_error", peci_error_code="",
                               error_category="Runtime error", execution_status="index_error")
        legacy = self.attempt(self.second, classification_outcome="", peci_error_code="",
                              error_category="Logical Error", legacy_error_category="Logical Error",
                              feedback_schema_version="feedback_schema_v2")
        before = list(CodeFeedbackRecord.objects.values("id", "classification_outcome", "peci_error_code", "error_category", "legacy_error_category"))
        context = build_class_evidence()
        self.assertEqual({r["source"] for r in context["common_errors"]}, {"peci", "project", "legacy"})
        self.assertEqual(before, list(CodeFeedbackRecord.objects.values("id", "classification_outcome", "peci_error_code", "error_category", "legacy_error_category")))
        for record, source in ((peci, "peci"), (project, "project"), (legacy, "legacy")):
            row = next(r for r in context["common_errors"] if r["source"] == source)
            self.client.force_login(self.teacher)
            response = self.client.get(row["evidence_url"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual({r.pk for r in response.context["records"]}, {record.pk})

    def test_evidence_links_match_topic_and_student_permissions(self):
        first = self.attempt(self.first)
        second = self.attempt(self.second)
        topic_url = self.topic(build_class_evidence())["evidence_url"]
        self.client.force_login(self.teacher)
        self.assertEqual({r.pk for r in self.client.get(topic_url).context["records"]}, {first.pk, second.pk})
        self.client.force_login(self.first)
        self.assertEqual({r.pk for r in self.client.get(topic_url).context["records"]}, {first.pk})
        self.assertEqual(self.client.get(f"/history/{second.pk}/").status_code, 403)

    def test_recommendations_use_people_and_have_record_links(self):
        for _ in range(10):
            self.attempt(self.first)
        context = build_class_analytics()
        advice = context["instructional_recommendations"]
        self.assertIn("1 of 1 practising students", advice[0]["body"])
        self.assertIn("1 distinct student(s), across 10 submissions", advice[1]["body"])
        self.assertTrue(all(a["evidence_url"].startswith("/history/?") for a in advice))

    def test_unknown_topic_filter_is_404_for_teacher(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/history/?topic=not_a_topic").status_code, 404)


class DirectoryAndPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user(username="teacher", is_staff=True)
        cls.students = [User.objects.create_user(username=f"demo_student_{i:02d}") for i in range(1, 31)]
        User.objects.create_user(username="inactive_student", is_active=False)

    def test_search_and_pagination_for_thirty_students(self):
        self.client.force_login(self.teacher)
        response = self.client.get("/analytics/students/")
        page = response.context["student_page"]
        self.assertEqual(page.paginator.count, 30)
        self.assertEqual(len(page), 5)
        self.assertEqual(page.paginator.num_pages, 6)
        self.assertContains(response, "demo_student_01")
        self.assertNotContains(response, "demo_student_06")
        second = self.client.get("/analytics/students/?page=2")
        self.assertContains(second, "demo_student_06")
        self.assertContains(second, "demo_student_10")
        self.assertNotContains(second, "demo_student_11")
        self.assertNotContains(second, "demo_student_01")
        last = self.client.get("/analytics/students/?page=6")
        self.assertEqual(len(last.context["student_page"]), 5)
        self.assertContains(last, "demo_student_26")
        self.assertContains(last, "demo_student_30")
        found = self.client.get("/analytics/students/?q=DEMO_STUDENT_27")
        self.assertEqual(found.context["student_page"].paginator.count, 1)
        self.assertContains(found, "demo_student_27")
        self.assertContains(found, f'/analytics/students/{self.students[26].pk}/')

    def test_pagination_preserves_search_query(self):
        self.client.force_login(self.teacher)
        response = self.client.get("/analytics/students/?q=demo_student&page=2")
        self.assertContains(response, '?q=demo_student&amp;page=3')
        self.assertContains(response, '?q=demo_student&amp;page=1')

    def test_invalid_pages_empty_results_and_escaped_query(self):
        self.client.force_login(self.teacher)
        for page in ("bogus", "999", "-1"):
            self.assertEqual(self.client.get("/analytics/students/", {"page": page}).status_code, 200)
        response = self.client.get("/analytics/students/", {"q": '<script>alert(1)</script>'})
        self.assertContains(response, "No students match this search.")
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_directory_permissions(self):
        self.assertEqual(self.client.get("/analytics/students/").status_code, 302)
        self.client.force_login(self.students[0])
        self.assertEqual(self.client.get("/analytics/students/").status_code, 403)
        self.assertEqual(self.client.get(f"/analytics/students/{self.students[1].pk}/").status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/analytics/students/").status_code, 200)

    def test_current_status_contains_all_eight_topics_without_duplicate_actions(self):
        self.client.force_login(self.students[0])
        response = self.client.get("/profile/current/")
        for topic in TOPIC_TAXONOMY:
            self.assertContains(response, f'data-topic="{topic}"')
        self.assertContains(response, "No evidence", count=9)
        self.assertNotContains(response, "Practice next")
        self.assertContains(response, 'class="btn btn-primary text-nowrap"', count=1)
        self.assertContains(response, "not a standardised assessment")

    def test_result_and_archive_share_topic_label_without_changing_stored_field(self):
        question = Question.objects.create(title="Loop", problem_statement="Count", topic_tags="iteration_range")
        record = CodeFeedbackRecord.objects.create(user=self.students[0], question=question,
            problem_statement="Count", student_code="print(1)", error_category="Logical error",
            classification_outcome="logical_error", concept_reference="Iteration and Range", feedback_text="Check the loop.")
        self.client.force_login(self.students[0])
        response = self.client.get(f"/history/{record.pk}/")
        self.assertContains(response, '>Topic</span>')
        self.assertNotContains(response, '>Concept</span>')
        record.refresh_from_db()
        self.assertEqual(record.concept_reference, "Iteration and Range")
