from django.test import TestCase

# Create your tests here.
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import UserRole


class AccountsApiTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_superuser(
            email="admin@plataforma.edu.ar",
            password="Admin12345!",
            first_name="Ada",
            last_name="Admin",
        )
        self.teacher = self.user_model.objects.create_user(
            email="diana@docentes.edu.ar",
            password="Docente12345!",
            first_name="Diana",
            last_name="Docente",
            role=UserRole.TEACHER,
        )

    def _login(self, email, password):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access"]

    def test_login_returns_token_pair(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "diana@docentes.edu.ar", "password": "Docente12345!"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "diana@docentes.edu.ar", "password": "otra"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_returns_a_new_token_pair(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "diana@docentes.edu.ar", "password": "Docente12345!"}),
            content_type="application/json",
        )
        refresh = response.json()["refresh"]

        response = self.client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": refresh}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_refresh_rejects_an_access_token(self):
        """Los dos tokens se firman igual: lo que los distingue es el campo
        type, y por eso el refresh no acepta un access."""
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self.client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": access}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_admin_role_becomes_staff_on_save(self):
        user = self.user_model.objects.create_user(
            email="jefa@plataforma.edu.ar",
            password="Clave12345!",
            first_name="Julia",
            last_name="Jefa",
            role=UserRole.ADMIN,
        )
        self.assertTrue(user.is_staff)

    def test_new_account_defaults_to_teacher(self):
        """El unico alta abierta es la del docente, asi que es el default."""
        user = self.user_model.objects.create_user(
            email="sin.rol@docentes.edu.ar",
            password="Clave12345!",
            first_name="Sin",
            last_name="Rol",
        )
        self.assertEqual(user.role, UserRole.TEACHER)

    def test_teacher_can_register_without_token(self):
        """El registro del docente es publico: la cuenta sola no habilita nada."""
        response = self.client.post(
            "/api/auth/register/teacher",
            data=json.dumps(
                {
                    "email": "dario@docentes.edu.ar",
                    "first_name": "Dario",
                    "last_name": "Docente",
                    "password": "Pizarron2026!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], UserRole.TEACHER)

    def test_teacher_registration_rejects_duplicated_email(self):
        response = self.client.post(
            "/api/auth/register/teacher",
            data=json.dumps(
                {
                    "email": "diana@docentes.edu.ar",
                    "first_name": "Diana",
                    "last_name": "Repetida",
                    "password": "Pizarron2026!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(response.json()["errors"]), ["email"])

    def test_admin_manages_users_and_others_cannot(self):
        access = self._login("admin@plataforma.edu.ar", "Admin12345!")
        response = self.client.post(
            "/api/admin/users",
            data=json.dumps(
                {
                    "email": "rectorado@iftsX.edu.ar",
                    "first_name": "Ines",
                    "last_name": "Instituto",
                    "password": "Pizarron2026!",
                    "role": UserRole.INSTITUTION,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], UserRole.INSTITUTION)

        teacher_access = self._login("diana@docentes.edu.ar", "Docente12345!")
        response = self.client.get(
            "/api/admin/users",
            HTTP_AUTHORIZATION=f"Bearer {teacher_access}",
        )
        # 403 y no 401: la API sabe quien es, pero el rol no alcanza.
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_assign_a_role_that_no_longer_exists(self):
        """STUDENT y COMPANY se fueron con el recorte: el service valida contra
        UserRole y no deja entrar un rol viejo por la API."""
        access = self._login("admin@plataforma.edu.ar", "Admin12345!")

        response = self.client.post(
            "/api/admin/users",
            data=json.dumps(
                {
                    "email": "ana@alumnos.edu.ar",
                    "first_name": "Ana",
                    "last_name": "Gomez",
                    "password": "Alumna12345!",
                    "role": "STUDENT",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.user_model.objects.filter(email="ana@alumnos.edu.ar").exists())

    def test_me_returns_the_user_of_the_token(self):
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self.client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "diana@docentes.edu.ar")

    def test_me_requires_token(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


class StrongPasswordTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_superuser(
            email="admin@plataforma.edu.ar",
            password="Admin12345!",
            first_name="Ada",
            last_name="Admin",
        )
        self.teacher = self.user_model.objects.create_user(
            email="diana@docentes.edu.ar",
            password="Docente12345!",
            first_name="Diana",
            last_name="Docente",
            role=UserRole.TEACHER,
        )

    def _post(self, url, payload, **extra):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json", **extra)

    def _admin_headers(self):
        response = self._post("/api/auth/login", {"email": "admin@plataforma.edu.ar", "password": "Admin12345!"})
        return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}

    def _register(self, password, **overrides):
        payload = {
            "email": "dario@docentes.edu.ar",
            "first_name": "Dario",
            "last_name": "Perez",
            "password": password,
            **overrides,
        }
        return self._post("/api/auth/register/teacher", payload)

    def test_registration_rejects_a_one_character_password(self):
        response = self._register("a")

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])
        self.assertFalse(self.user_model.objects.filter(email="dario@docentes.edu.ar").exists())

    def test_each_rule_rejects_its_own_case(self):
        candidate = self.user_model(email="dario@docentes.edu.ar", first_name="Dario", last_name="Perez")
        cases = {
            "password_too_short": "Ab1",
            "password_too_common": "password123",
            "password_no_letter_and_digit": "PizarronVerde",
            "password_too_similar": "dariodocentes1",
        }
        for code, password in cases.items():
            with self.subTest(code=code):
                with self.assertRaises(ValidationError) as ctx:
                    validate_password(password, user=candidate)
                self.assertIn(code, [error.code for error in ctx.exception.error_list])

    def test_entirely_numeric_password_gets_a_single_message(self):
        response = self._register("48213957601")

        self.assertEqual(len(response.json()["errors"]["password"]), 1)

    def test_errors_of_every_field_come_together(self):
        response = self._register("1", email="diana@docentes.edu.ar")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["errors"]), {"email", "password"})

    def test_registration_accepts_a_strong_password(self):
        response = self._register("Pizarron2026!")

        self.assertEqual(response.status_code, 200)

    def test_errors_are_grouped_by_field_and_keep_the_detail_text(self):
        response = self._register("123")

        body = response.json()
        self.assertEqual(list(body["errors"]), ["password"])
        self.assertGreaterEqual(len(body["errors"]["password"]), 2)
        self.assertTrue(body["detail"].startswith("password:"))

    def test_admin_cannot_create_a_user_with_a_weak_password(self):
        response = self._post(
            "/api/admin/users",
            {
                "email": "ines@instituto.edu.ar",
                "first_name": "Ines",
                "last_name": "Instituto",
                "password": "1234",
                "role": UserRole.INSTITUTION,
            },
            **self._admin_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])
        self.assertFalse(self.user_model.objects.filter(email="ines@instituto.edu.ar").exists())

    def test_admin_cannot_set_a_weak_password_when_editing(self):
        response = self.client.patch(
            f"/api/admin/users/{self.teacher.id}",
            data=json.dumps({"password": "x", "first_name": "Otra"}),
            content_type="application/json",
            **self._admin_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("Docente12345!"))
        self.assertEqual(self.teacher.first_name, "Diana")

    def test_admin_cannot_blank_the_password_when_editing(self):
        response = self.client.patch(
            f"/api/admin/users/{self.teacher.id}",
            data=json.dumps({"password": ""}),
            content_type="application/json",
            **self._admin_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("Docente12345!"))

    def test_admin_can_set_a_strong_password_when_editing(self):
        response = self.client.patch(
            f"/api/admin/users/{self.teacher.id}",
            data=json.dumps({"password": "Pizarron2026!"}),
            content_type="application/json",
            **self._admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("Pizarron2026!"))
