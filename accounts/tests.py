"""
accounts app-এর জন্য টেস্ট স্যুট।

কভার করা হয়েছে:
- Registration (সবসময় role='patient' হয়, client role পাঠালেও তা ignore হয়)
- Password validation / mismatch
- Duplicate username
- Login (JWT-তে role/username embed হয় কিনা)
- Profile view/update (role read-only থাকে কিনা -- privilege escalation প্রতিরোধ)
- Custom permission classes (IsPatient/IsRadiologist/IsDoctor/IsAdminRole/IsRadiologistOrDoctor)
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from .models import User
from .permissions import (
    IsPatient,
    IsRadiologist,
    IsDoctor,
    IsAdminRole,
    IsRadiologistOrDoctor,
)


class RegisterTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-register")
        self.valid_payload = {
            "username": "rahim01",
            "email": "rahim@example.com",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
            "first_name": "Rahim",
            "last_name": "Uddin",
            "phone_number": "01700000000",
        }

    def test_register_success_creates_patient_role(self):
        """সফল registration হলে সবসময় role='patient' হবে।"""
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="rahim01")
        self.assertEqual(user.role, "patient")
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_register_ignores_client_supplied_role(self):
        """
        Privilege escalation প্রতিরোধ: client payload-এ role='doctor' পাঠালেও
        serializer-এর fields লিস্টে role নেই বলে সেটা কোনোভাবেই সেট হবে না।
        """
        payload = {**self.valid_payload, "role": "doctor"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="rahim01")
        self.assertEqual(user.role, "patient")

    def test_register_password_mismatch(self):
        payload = {**self.valid_payload, "password2": "DifferentPass456!"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data)

    def test_register_weak_password_rejected(self):
        """Django-এর built-in password validators (validate_password) কাজ করছে কিনা।"""
        payload = {**self.valid_payload, "password": "123", "password2": "123"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username_rejected(self):
        User.objects.create_user(username="rahim01", password="Xyz12345!")
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-login")
        self.user = User.objects.create_user(
            username="doc_karim", password="DocPass123!", role="doctor"
        )

    def test_login_success_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"username": "doc_karim", "password": "DocPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_response_includes_role_and_username(self):
        """
        Custom serializer-এর কারণে login response-এ user.role/username থাকা উচিত,
        যাতে frontend সঠিক dashboard-এ redirect করতে পারে।
        """
        response = self.client.post(
            self.url,
            {"username": "doc_karim", "password": "DocPass123!"},
            format="json",
        )
        self.assertEqual(response.data["user"]["role"], "doctor")
        self.assertEqual(response.data["user"]["username"], "doc_karim")

    def test_login_wrong_password_fails(self):
        response = self.client.post(
            self.url,
            {"username": "doc_karim", "password": "WrongPassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="patient_x", password="PatPass123!", role="patient"
        )
        self.url = reverse("auth-profile")

    def test_profile_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_returns_own_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "patient_x")
        self.assertEqual(response.data["role"], "patient")

    def test_profile_update_allows_editable_fields(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {"phone_number": "01812345678"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "01812345678")

    def test_profile_cannot_change_own_role(self):
        """
        গুরুত্বপূর্ণ security টেস্ট: role read_only_fields-এ থাকায়
        patient নিজেকে PATCH করে 'admin'/'doctor' বানিয়ে ফেলতে পারবে না।
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"role": "admin"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "patient")


class PermissionClassUnitTests(APITestCase):
    """
    accounts/permissions.py-এর প্রতিটা permission class সরাসরি unit-test করা --
    view-এর মধ্য দিয়ে না গিয়ে, যাতে ভবিষ্যতে কোনো view এই permission ভুলভাবে
    ব্যবহার করলেও এই টেস্টগুলো এখনো নিশ্চিত করে যে permission logic নিজে ঠিক আছে।
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.patient = User.objects.create_user(
            username="p1", password="x", role="patient"
        )
        self.radiologist = User.objects.create_user(
            username="r1", password="x", role="radiologist"
        )
        self.doctor = User.objects.create_user(
            username="d1", password="x", role="doctor"
        )
        self.admin = User.objects.create_user(username="a1", password="x", role="admin")
        self.super_admin = User.objects.create_user(
            username="sa1", password="x", role="super_admin"
        )

    def _request_as(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_is_patient_permission(self):
        perm = IsPatient()
        self.assertTrue(perm.has_permission(self._request_as(self.patient), None))
        self.assertFalse(perm.has_permission(self._request_as(self.doctor), None))
        self.assertFalse(perm.has_permission(self._request_as(self.radiologist), None))

    def test_is_radiologist_permission(self):
        perm = IsRadiologist()
        self.assertTrue(perm.has_permission(self._request_as(self.radiologist), None))
        self.assertFalse(perm.has_permission(self._request_as(self.patient), None))

    def test_is_doctor_permission(self):
        perm = IsDoctor()
        self.assertTrue(perm.has_permission(self._request_as(self.doctor), None))
        self.assertFalse(perm.has_permission(self._request_as(self.patient), None))

    def test_is_admin_role_permission_covers_both_admin_and_super_admin(self):
        perm = IsAdminRole()
        self.assertTrue(perm.has_permission(self._request_as(self.admin), None))
        self.assertTrue(perm.has_permission(self._request_as(self.super_admin), None))
        self.assertFalse(perm.has_permission(self._request_as(self.doctor), None))

    def test_is_radiologist_or_doctor_permission(self):
        perm = IsRadiologistOrDoctor()
        self.assertTrue(perm.has_permission(self._request_as(self.radiologist), None))
        self.assertTrue(perm.has_permission(self._request_as(self.doctor), None))
        self.assertFalse(perm.has_permission(self._request_as(self.patient), None))

    def test_unauthenticated_user_denied_everywhere(self):
        request = self.factory.get("/")
        request.user = None
        for perm_cls in (
            IsPatient,
            IsRadiologist,
            IsDoctor,
            IsAdminRole,
            IsRadiologistOrDoctor,
        ):
            self.assertFalse(perm_cls().has_permission(request, None))
