from django.test import TestCase, Client
from django.urls import reverse
import factory

from talent.models import Skill, Expertise, PersonSkill
from .factories import (
    SkillFactory,
    ExpertiseFactory,
    PersonFactory,
    StatusFactory,
    PersonSkillFactory,
)


class TalentAppLoginRequiredTest(TestCase):
    def setUp(self):
        self.url_names = [
            "get_skills",
            "get_current_skills",
            "get_expertise",
            "get_current_expertise",
            "list-skill-and-expertise",
        ]
        self.url_list = [reverse(url_name) for url_name in self.url_names]

    def test_as_anonymous(self):
        login_url = reverse("sign_in")
        client = Client()

        for url in self.url_list:
            response = client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, f"{login_url}?next={url}")

    def test_as_logged_in(self):
        person = PersonFactory()
        client = Client()
        client.force_login(person.user)

        for url in self.url_list:
            response = client.get(url)
            self.assertEqual(response.status_code, 200)


class TalentAppFunctionBasedViewsTest(TestCase):
    def setUp(self):
        self.person = PersonFactory()
        self.client = Client()
        self.client.force_login(self.person.user)

        self.another_person = PersonFactory()
        self.client_for_none = Client()
        self.client_for_none.force_login(self.another_person.user)

        self.skills = SkillFactory.create_batch(10)
        self.skill_ids = [s.id for s in self.skills]
        self.skill_data = [{"id": s.id, "name": s.name} for s in self.skills]

        self.expertise = ExpertiseFactory.create_batch(
            10, skill=factory.Iterator(self.skills)
        )
        self.expertise_ids = [exp.id for exp in self.expertise]
        self.expertise_queryset = Expertise.objects.filter(
            id__in=self.expertise_ids
        ).values()
        self.expertise_data = [
            {"id": exp.id, "name": exp.name} for exp in self.expertise
        ]

        _ = PersonSkillFactory(
            person=self.person, skill=self.skill_data, expertise=self.expertise_data
        )

    def tearDown(self):
        Skill.objects.filter(id__in=self.skill_ids).delete()
        Expertise.objects.filter(id__in=self.expertise_ids).delete()

    def test_get_skills(self):
        skills_url = reverse("get_skills")
        actual_response = self.client.get(skills_url).json()

        expected_json_data = list(
            Skill.objects.filter(id__in=self.skill_ids, active=True)
            .order_by("-display_boost_factor")
            .values()
        )
        self.assertCountEqual(actual_response, expected_json_data)

    def test_current_skills(self):
        url = reverse("get_current_skills")

        actual_response = self.client.get(url).json()
        self.assertEqual(actual_response, self.skill_ids)

        actual_response = self.client_for_none.get(url).json()
        expected_response = []

        self.assertEqual(actual_response, expected_response)

    def test_get_expertise(self):
        url = reverse("get_expertise")

        response = self.client.get(url, data={"selected_skills": f"{self.skill_ids}"})
        actual_data = response.json()
        expected_data = {
            "expertiseList": list(self.expertise_queryset),
            "expertiseIDList": self.expertise_ids,
        }
        self.assertEqual(actual_data, expected_data)

        response = self.client.get(url)
        actual_data = response.json()
        expected_data = {
            "expertiseList": [],
            "expertiseIDList": [],
        }
        self.assertEqual(actual_data, expected_data)

    def test_get_current_expertise(self):
        url = reverse("get_current_expertise")

        response = self.client.get(url)
        actual_data = response.json()
        expected_data = {
            "expertiseList": list(self.expertise_queryset),
            "expertiseIDList": self.expertise_ids,
        }

        self.assertEqual(actual_data, expected_data)

        response = self.client_for_none.get(url)
        actual_data = response.json()
        expected_data = {
            "expertiseList": [],
            "expertiseIDList": [],
        }

        self.assertEqual(actual_data, expected_data)

    def test_list_skill_and_expertise(self):
        url = reverse("list-skill-and-expertise")

        response = self.client.get(url)

        actual_data = response.json()
        expected_data = []

        self.assertEqual(actual_data, expected_data)

        response = self.client.get(
            url,
            data={"skills": f"{self.skill_ids}", "expertise": f"{self.expertise_ids}"},
        )

        actual_data = response.json()
        expected_data = []
        for exp in self.expertise:
            expected_data.append(
                {
                    "skill": exp.skill.name,
                    "expertise": exp.name,
                }
            )

        self.assertEqual(actual_data, expected_data)


class SubmitFeedbackViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("submit-feedback")

    def test_submit_feedback_get(self):
        response = self.client.get(self.url)

        actual = response.content.decode("utf-8")
        expected = "Something went wrong"

        self.assertEqual(actual, expected)

    def test_submit_feedback_invalid_post(self):
        response = self.client.post(self.url, data={"message": "test message"})

        actual = response.content.decode("utf-8")
        expected = "Something went wrong"

        self.assertEqual(actual, expected)

    def test_submit_feedback_valid_post(self):
        person = PersonFactory()
        _ = StatusFactory(person=person)
        _ = PersonSkillFactory(person=person)
        auth_person = PersonFactory()

        self.client.force_login(auth_person.user)
        response = self.client.post(
            self.url,
            data={
                "message": "test message",
                "stars": 5,
                "feedback-recipient-username": person.user.username,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("portfolio", args=(person.user.username,))
        )


class TalentPortfolioViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        person_auth = PersonFactory()
        self.client.force_login(person_auth.user)

        self.person = PersonFactory()
        _ = StatusFactory(person=self.person)
        self.person_skill = PersonSkillFactory(person=self.person)
        self.url = reverse("portfolio", args=(self.person.user.username,))

    def test_get_request(self):
        from talent.forms import FeedbackForm
        from talent.services import FeedbackService

        response = self.client.get(self.url)

        actual = response.context_data
        expected = {
            "user": self.person.user,
            "photo_url": "/media/avatars/profile-empty.png",
            "person": self.person,
            "person_linkedin_link": "",
            "person_twitter_link": "",
            "status": self.person.status,
            "skills": self.person_skill.skill,
            "expertise": self.person_skill.expertise,
            "FeedbackService": FeedbackService,
            "can_leave_feedback": True,
        }

        # we dont' need to check form
        actual.pop("form")

        bounty_claims = actual.pop("bounty_claims")
        self.assertEqual(bounty_claims.count(), 0)

        received_feedbacks = actual.pop("received_feedbacks")
        self.assertEqual(received_feedbacks.count(), 0)

        self.assertEqual(actual, expected)


# TODO: write tests for _remove_picture method. It is not written since it was not urgent
class UpdateProfileViewTest(TestCase):
    def setUp(self):
        self.person = PersonFactory()
        self.client = Client()
        self.client.force_login(self.person.user)
        self.url = reverse("profile", args=(self.person.user.pk,))

    def test_get_context_data(self):
        response = self.client.get(self.url)

        actual = response.context_data
        expected = {
            "person": self.person,
            "pk": self.person.pk,
            "photo_url": "/media/avatars/profile-empty.png",
            "requires_upload": True,
        }

        for key in expected.keys():
            self.assertEqual(actual.get(key), expected.get(key))

    def test_post_valid(self):
        skills = SkillFactory.create_batch(3)
        skill_ids = [skill.id for skill in skills]

        expertise = ExpertiseFactory.create_batch(5)
        expertise_ids = [exp.id for exp in expertise]

        data = {
            "full_name": "test user",
            "preferred_name": "test",
            "current_position": "xyz company",
            "headline": "dummy headline",
            "overview": "dummy overview",
            "location": "somewhere",
            "github_link": "www.github.com/testuser",
            "twitter_link": "www.twitter.com/testuser",
            "linkedin_link": "www.linkedin.com/in/testuser",
            "website_link": "www.example.com",
            "send_me_bounties": True,
            "selected_skill_ids": f"{skill_ids}",
            "selected_expertise_ids": f"{expertise_ids}",
        }

        _ = self.client.post(self.url, data=data)

        person_skill = PersonSkill.objects.get(person=self.person)
        self.assertIsNotNone(person_skill)
        self.assertEqual(
            person_skill.skill,
            list(Skill.objects.filter(id__in=skill_ids).values("id", "name")),
        )
        self.assertEqual(
            person_skill.expertise,
            list(Expertise.objects.filter(id__in=expertise_ids).values("id", "name")),
        )

        Skill.objects.filter(id__in=skill_ids).delete()
        Expertise.objects.filter(id__in=expertise_ids).delete()
