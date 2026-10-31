"""Pruebas del circuito del docente: su cursada y los alumnos que carga.

El escenario es caro de armar (institucion, cuenta institucional, docente,
membresia aceptada y carrera), asi que se arma una vez en una clase base sin
pruebas y las demas heredan de ella.
"""
import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.academics import selectors
from apps.academics.models import (
    Career,
    Course,
    CourseStudent,
    CourseTerm,
    Student,
    StudentLink,
    Subject,
)
from apps.accounts.models import UserRole
from apps.institutions.models import (
    Institution,
    InstitutionEmailRule,
    InstitutionTeacher,
    MembershipOrigin,
    MembershipStatus,
)

class AcademicsTestCase(TestCase):
    """Escenario compartido: una institucion, su cuenta, un docente y una carrera."""

    def setUp(self):
        self.user_model = get_user_model()
        # Los datos de las otras apps se crean aca: esta app depende de ellas,
        # asi que sus tests tambien.
        self.institution = Institution.objects.create(name="IFTS 18", city="CABA")
        self.institution_user = self.user_model.objects.create_user(
            email="rectoria@ifts18.edu.ar",
            password="Rectoria12345!",
            first_name="Rectoria",
            last_name="IFTS",
            role=UserRole.INSTITUTION,
        )
        InstitutionEmailRule.objects.create(
            institution=self.institution,
            email="rectoria@ifts18.edu.ar",
            user=self.institution_user,
        )
        self.teacher = self.user_model.objects.create_user(
            email="diana@docentes.edu.ar",
            password="Docente12345!",
            first_name="Diana",
            last_name="Docente",
            role=UserRole.TEACHER,
        )
        self.membership = InstitutionTeacher.objects.create(
            institution=self.institution,
            teacher=self.teacher,
            origin=MembershipOrigin.INVITATION,
            status=MembershipStatus.ACCEPTED,
        )
        self.career = Career.objects.create(
            institution=self.institution,
            name="Desarrollo de Software",
        )
        self.subject = Subject.objects.create(career=self.career, name="Programacion I")

    def _login(self, email, password):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access"]

    def _post(self, url, payload, access):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

    def _patch(self, url, payload, access):
        return self.client.patch(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

    def _delete(self, url, access):
        return self.client.delete(
            url,
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

    def _create_course(self, name="1C - Noche", teacher=None, year=2026):
        return Course.objects.create(
            career=self.career,
            subject=self.subject,
            teacher=teacher or self.teacher,
            name=name,
            year=year,
            term=CourseTerm.FIRST,
        )


class CareerApiTests(AcademicsTestCase):
    def test_public_careers_need_no_token(self):
        response = self.client.get(f"/api/careers?institution_id={self.institution.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Desarrollo de Software")

    def test_institution_creates_career(self):
        access = self._login("rectoria@ifts18.edu.ar", "Rectoria12345!")

        response = self._post("/api/institution/careers", {"name": "Ciencia de Datos"}, access)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Career.objects.filter(institution=self.institution, name="Ciencia de Datos").exists()
        )

    def test_career_name_cannot_repeat_in_the_same_institution(self):
        """La comparacion no distingue mayusculas: es la misma carrera."""
        access = self._login("rectoria@ifts18.edu.ar", "Rectoria12345!")

        response = self._post(
            "/api/institution/careers", {"name": "desarrollo de software"}, access
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Career.objects.filter(institution=self.institution).count(), 1)


class SubjectModelTests(AcademicsTestCase):
    def test_subject_name_is_unique_within_its_career(self):
        """La base sostiene la regla aunque alguien saltee el service."""
        with self.assertRaises(IntegrityError):
            Subject.objects.create(career=self.career, name="Programacion I")


class SubjectApiTests(AcademicsTestCase):
    def setUp(self):
        super().setUp()
        self.access = self._login("rectoria@ifts18.edu.ar", "Rectoria12345!")

    def _url(self, career):
        return f"/api/institution/careers/{career.id}/subjects"

    def _get(self, url):
        return self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_institution_creates_a_subject_in_its_career(self):
        response = self._post(self._url(self.career), {"name": "  Base de Datos "}, self.access)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Base de Datos")
        self.assertEqual(response.json()["career_id"], self.career.id)
        self.assertTrue(
            Subject.objects.filter(career=self.career, name="Base de Datos").exists()
        )

    def test_subject_name_cannot_repeat_in_the_same_career(self):
        """Mismo criterio que la carrera: no distingue mayusculas ni espacios de mas."""
        response = self._post(self._url(self.career), {"name": " programacion i "}, self.access)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Subject.objects.filter(career=self.career).count(), 1)

    def test_the_same_subject_name_is_fine_in_another_career(self):
        """Cada carrera tiene su plan: las dos pueden dictar Programacion I."""
        other_career = Career.objects.create(
            institution=self.institution, name="Analisis de Sistemas"
        )

        response = self._post(self._url(other_career), {"name": "Programacion I"}, self.access)

        self.assertEqual(response.status_code, 200)

    def test_a_blank_name_is_rejected(self):
        response = self._post(self._url(self.career), {"name": "   "}, self.access)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Subject.objects.filter(career=self.career).count(), 1)

    def test_institution_lists_only_the_subjects_of_that_career(self):
        other_career = Career.objects.create(
            institution=self.institution, name="Analisis de Sistemas"
        )
        Subject.objects.create(career=other_career, name="Base de Datos")

        response = self._get(self._url(self.career))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["name"] for s in response.json()], ["Programacion I"])

    def test_a_career_of_another_institution_is_forbidden(self):
        other_institution = Institution.objects.create(name="IFTS 24", city="CABA")
        foreign_career = Career.objects.create(
            institution=other_institution, name="Desarrollo de Software"
        )

        listing = self._get(self._url(foreign_career))
        creation = self._post(self._url(foreign_career), {"name": "Programacion I"}, self.access)

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(creation.status_code, 403)
        self.assertFalse(Subject.objects.filter(career=foreign_career).exists())

    def test_admin_manages_the_subjects_of_any_career(self):
        """El administrador no representa a ninguna institucion: destraba."""
        self.user_model.objects.create_user(
            email="admin@campuslab.edu.ar",
            password="Admin12345!",
            first_name="Ada",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        self.access = self._login("admin@campuslab.edu.ar", "Admin12345!")

        response = self._post(self._url(self.career), {"name": "Base de Datos"}, self.access)

        self.assertEqual(response.status_code, 200)


class CourseApiTests(AcademicsTestCase):
    def test_member_teacher_creates_course(self):
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": self.subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["career"]["name"], "Desarrollo de Software")
        self.assertEqual(response.json()["term_label"], "Primer cuatrimestre")

    def test_non_member_teacher_cannot_create_course(self):
        """Ser TEACHER no alcanza: la membresia aceptada es el permiso real."""
        self.user_model.objects.create_user(
            email="externo@docentes.edu.ar",
            password="Docente12345!",
            first_name="Elias",
            last_name="Externo",
            role=UserRole.TEACHER,
        )
        access = self._login("externo@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": self.subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Course.objects.exists())

    def test_a_pending_membership_is_not_enough(self):
        self.membership.status = MembershipStatus.PENDING
        self.membership.save(update_fields=["status"])
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": self.subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_term_is_rejected(self):
        """El periodo llega como texto: si no es una opcion, no se guarda nada."""
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": self.subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": "VERANO",
            },
            access,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Course.objects.exists())

    def test_course_comes_back_with_its_subject(self):
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": self.subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["subject"],
            {"id": self.subject.id, "name": "Programacion I", "career_id": self.career.id},
        )
        self.assertEqual(Course.objects.get().subject, self.subject)

    def test_subject_of_another_career_is_rejected(self):
        """La materia y la cursada tienen que ser de la misma carrera."""
        other_career = Career.objects.create(
            institution=self.institution, name="Analisis de Sistemas"
        )
        foreign_subject = Subject.objects.create(career=other_career, name="Base de Datos")
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "subject_id": foreign_subject.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("subject_id", response.json()["detail"])
        self.assertFalse(Course.objects.exists())

    def test_subject_is_required(self):
        access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._post(
            "/api/teacher/courses",
            {
                "career_id": self.career.id,
                "name": "1C - Noche",
                "year": 2026,
                "term": CourseTerm.FIRST.value,
            },
            access,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(Course.objects.exists())

    def test_course_answers_its_institution_through_the_career(self):
        """La cursada no guarda la institucion y sin embargo la sabe."""
        course = self._create_course()

        self.assertEqual(course.institution, self.institution)


class EnrollmentApiTests(AcademicsTestCase):
    def setUp(self):
        super().setUp()
        self.course = self._create_course()
        self.access = self._login("diana@docentes.edu.ar", "Docente12345!")

    def _enroll(self, course, first_name="Ana", last_name="Gomez", email=""):
        return self._post(
            f"/api/teacher/courses/{course.id}/students",
            {"first_name": first_name, "last_name": last_name, "email": email},
            self.access,
        )

    def test_teacher_loads_a_student_and_no_account_is_created(self):
        """El alumno es un dato del docente: ya no nace una cuenta con el."""
        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"]["full_name"], "Ana Gomez")
        student = Student.objects.get(email="ana@alumnos.edu.ar")
        self.assertEqual(student.institution, self.institution)
        self.assertFalse(self.user_model.objects.filter(email="ana@alumnos.edu.ar").exists())

    def test_the_same_email_reuses_the_student_of_the_institution(self):
        """Ana cursa dos materias: es una sola alumna con dos inscripciones."""
        other_course = self._create_course(name="2C - Manana")

        self._enroll(self.course, email="ana@alumnos.edu.ar")
        self._enroll(other_course, email="ANA@alumnos.edu.ar")

        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(CourseStudent.objects.count(), 2)

    def test_students_without_email_are_not_mixed_up(self):
        """Sin email no hay con que compararlos: son dos alumnos distintos."""
        self._enroll(self.course, first_name="Ana", last_name="Gomez")
        self._enroll(self.course, first_name="Luis", last_name="Perez")

        self.assertEqual(Student.objects.count(), 2)

    def test_student_cannot_be_enrolled_twice_in_the_same_course(self):
        self._enroll(self.course, email="ana@alumnos.edu.ar")

        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CourseStudent.objects.filter(course=self.course).count(), 1)

    def test_teacher_cannot_touch_another_teachers_course(self):
        other_teacher = self.user_model.objects.create_user(
            email="otro@docentes.edu.ar",
            password="Docente12345!",
            first_name="Omar",
            last_name="Otro",
            role=UserRole.TEACHER,
        )
        InstitutionTeacher.objects.create(
            institution=self.institution,
            teacher=other_teacher,
            origin=MembershipOrigin.REQUEST,
            status=MembershipStatus.ACCEPTED,
        )
        self.access = self._login("otro@docentes.edu.ar", "Docente12345!")

        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 403)

    def test_removing_an_enrollment_keeps_the_student(self):
        """Se da de baja la inscripcion, no al alumno: sigue en la institucion."""
        self._enroll(self.course, email="ana@alumnos.edu.ar")
        enrollment = CourseStudent.objects.get(course=self.course)

        response = self.client.delete(
            f"/api/teacher/courses/{self.course.id}/students/{enrollment.id}",
            HTTP_AUTHORIZATION=f"Bearer {self.access}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CourseStudent.objects.filter(pk=enrollment.pk).exists())
        self.assertTrue(Student.objects.filter(email="ana@alumnos.edu.ar").exists())

    def test_an_enrollment_of_another_course_is_not_found(self):
        """El id se busca dentro de la cursada, asi no se borra lo ajeno."""
        other_course = self._create_course(name="2C - Manana")
        self._enroll(other_course, email="ana@alumnos.edu.ar")
        enrollment = CourseStudent.objects.get(course=other_course)

        response = self.client.delete(
            f"/api/teacher/courses/{self.course.id}/students/{enrollment.id}",
            HTTP_AUTHORIZATION=f"Bearer {self.access}",
        )

        self.assertEqual(response.status_code, 404)

    def test_only_students_enrolled_in_the_course_come_back(self):
        """Es la pregunta que hace projects para validar los participantes."""
        self._enroll(self.course, email="ana@alumnos.edu.ar")
        outsider = Student.objects.create(
            institution=self.institution,
            first_name="Luis",
            last_name="Perez",
            email="luis@alumnos.edu.ar",
        )
        enrolled = Student.objects.get(email="ana@alumnos.edu.ar")

        found = selectors.students_enrolled_in_course(
            self.course, [enrolled.id, outsider.id]
        )

        self.assertEqual(list(found), [enrolled])


class InstitutionEnrollmentApiTests(AcademicsTestCase):
    def setUp(self):
        super().setUp()
        self.course = self._create_course()
        self.access = self._login("rectoria@ifts18.edu.ar", "Rectoria12345!")

        other_institution = Institution.objects.create(name="IFTS 11", city="CABA")
        other_career = Career.objects.create(
            institution=other_institution, name="Analisis de Sistemas"
        )
        other_teacher = self.user_model.objects.create_user(
            email="otro@docentes.edu.ar",
            password="Docente12345!",
            first_name="Omar",
            last_name="Otro",
            role=UserRole.TEACHER,
        )
        self.foreign_course = Course.objects.create(
            career=other_career,
            subject=Subject.objects.create(career=other_career, name="Base de Datos"),
            teacher=other_teacher,
            name="1C - Manana",
            year=2026,
            term=CourseTerm.FIRST,
        )

    def _url(self, course):
        return f"/api/institution/courses/{course.id}/students"

    def _enroll(self, course, first_name="Ana", last_name="Gomez", email=""):
        return self._post(
            self._url(course),
            {"first_name": first_name, "last_name": last_name, "email": email},
            self.access,
        )

    def _get(self, course):
        return self.client.get(
            self._url(course), HTTP_AUTHORIZATION=f"Bearer {self.access}"
        )

    def _delete(self, course, enrollment):
        return self.client.delete(
            f"{self._url(course)}/{enrollment.id}",
            HTTP_AUTHORIZATION=f"Bearer {self.access}",
        )

    def test_institution_enrolls_a_student_in_its_course(self):
        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"]["full_name"], "Ana Gomez")
        student = Student.objects.get(email="ana@alumnos.edu.ar")
        self.assertEqual(student.institution, self.institution)
        self.assertTrue(
            CourseStudent.objects.filter(course=self.course, student=student).exists()
        )

    def test_institution_cannot_enroll_in_a_course_of_another_institution(self):
        response = self._enroll(self.foreign_course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseStudent.objects.exists())

    def test_the_same_email_reuses_the_student_of_the_institution(self):
        other_course = self._create_course(name="2C - Manana")

        self._enroll(self.course, email="ana@alumnos.edu.ar")
        response = self._enroll(other_course, email="ANA@alumnos.edu.ar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(CourseStudent.objects.count(), 2)

    def test_student_cannot_be_enrolled_twice_in_the_same_course(self):
        self._enroll(self.course, email="ana@alumnos.edu.ar")

        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CourseStudent.objects.filter(course=self.course).count(), 1)

    def test_institution_lists_the_students_of_its_course(self):
        self._enroll(self.course, email="ana@alumnos.edu.ar")

        response = self._get(self.course)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [e["student"]["email"] for e in response.json()], ["ana@alumnos.edu.ar"]
        )

    def test_institution_cannot_list_the_students_of_another_institution(self):
        response = self._get(self.foreign_course)

        self.assertEqual(response.status_code, 403)

    def test_institution_removes_an_enrollment_and_keeps_the_student(self):
        self._enroll(self.course, email="ana@alumnos.edu.ar")
        enrollment = CourseStudent.objects.get(course=self.course)

        response = self._delete(self.course, enrollment)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CourseStudent.objects.filter(pk=enrollment.pk).exists())
        self.assertTrue(Student.objects.filter(email="ana@alumnos.edu.ar").exists())

    def test_institution_cannot_remove_an_enrollment_of_another_institution(self):
        student = Student.objects.create(
            institution=self.foreign_course.institution,
            first_name="Luis",
            last_name="Perez",
        )
        enrollment = CourseStudent.objects.create(
            course=self.foreign_course, student=student
        )

        response = self._delete(self.foreign_course, enrollment)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CourseStudent.objects.filter(pk=enrollment.pk).exists())

    def test_teacher_cannot_use_the_institution_endpoints(self):
        self.access = self._login("diana@docentes.edu.ar", "Docente12345!")

        response = self._enroll(self.course, email="ana@alumnos.edu.ar")

        self.assertEqual(response.status_code, 403)


class StudentLinkApiTests(AcademicsTestCase):
    """HU-12: editar alumnos y sus links (docente e institucion)."""

    def setUp(self):
        super().setUp()
        self.course = self._create_course()
        # Inscribimos a Ana en la cursada del docente Diana
        self.ana = Student.objects.create(
            institution=self.institution,
            first_name="Ana",
            last_name="Gomez",
            email="ana@alumnos.edu.ar",
        )
        CourseStudent.objects.create(course=self.course, student=self.ana)

        self.teacher_access = self._login("diana@docentes.edu.ar", "Docente12345!")
        self.institution_access = self._login("rectoria@ifts18.edu.ar", "Rectoria12345!")

    # --- Helpers ---

    def _create_other_teacher(self):
        other_teacher = self.user_model.objects.create_user(
            email="otro@docentes.edu.ar",
            password="Docente12345!",
            first_name="Omar",
            last_name="Otro",
            role=UserRole.TEACHER,
        )
        InstitutionTeacher.objects.create(
            institution=self.institution,
            teacher=other_teacher,
            origin=MembershipOrigin.REQUEST,
            status=MembershipStatus.ACCEPTED,
        )
        return other_teacher

    # --- Tests que pide el ticket ---

    def test_teacher_edits_student_of_his_course(self):
        """El docente edita un alumno de su cursada: 200."""
        response = self._patch(
            f"/api/teacher/students/{self.ana.id}",
            {"first_name": "Ana Maria"},
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 200)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Ana Maria")

    def test_teacher_cannot_edit_student_of_another_course(self):
        """Un docente que NO tiene al alumno en sus cursadas: 403."""
        self._create_other_teacher()
        other_access = self._login("otro@docentes.edu.ar", "Docente12345!")

        response = self._patch(
            f"/api/teacher/students/{self.ana.id}",
            {"first_name": "Hackeado"},
            other_access,
        )

        self.assertEqual(response.status_code, 403)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Ana")

    def test_linkedin_with_invalid_domain_returns_400(self):
        """LinkedIn con URL de GitHub: 400."""
        response = self._post(
            f"/api/teacher/students/{self.ana.id}/links",
            {
                "link_type": "LINKEDIN",
                "url": "https://github.com/ana-gomez",
            },
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StudentLink.objects.exists())

    # --- Tests extra para cubrir los 5 criterios de aceptacion ---

    def test_github_link_with_valid_domain_is_created(self):
        """Criterio 2: GitHub con URL de github.com se crea bien."""
        response = self._post(
            f"/api/teacher/students/{self.ana.id}/links",
            {
                "link_type": "GITHUB",
                "title": "Mi repo",
                "url": "https://github.com/ana-gomez",
            },
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["link_type"], "GITHUB")

    def test_portfolio_accepts_any_valid_url(self):
        """Criterio 2: PORTFOLIO acepta cualquier URL valida."""
        response = self._post(
            f"/api/teacher/students/{self.ana.id}/links",
            {
                "link_type": "PORTFOLIO",
                "url": "https://anamaria.dev",
            },
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 200)

    def test_duplicate_link_is_rejected(self):
        """Criterio 1: la URL es unica por alumno."""
        url = f"/api/teacher/students/{self.ana.id}/links"
        payload = {"link_type": "GITHUB", "url": "https://github.com/ana-gomez"}

        primera = self._post(url, payload, self.teacher_access)
        self.assertEqual(primera.status_code, 200)

        repetida = self._post(url, payload, self.teacher_access)
        self.assertEqual(repetida.status_code, 400)
        self.assertEqual(StudentLink.objects.filter(student=self.ana).count(), 1)

    def test_changing_email_to_one_already_used_returns_400(self):
        """Criterio 4: el email es unico por institucion."""
        Student.objects.create(
            institution=self.institution,
            first_name="Bruno",
            last_name="Diaz",
            email="bruno@alumnos.edu.ar",
        )

        response = self._patch(
            f"/api/teacher/students/{self.ana.id}",
            {"email": "bruno@alumnos.edu.ar"},
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 400)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.email, "ana@alumnos.edu.ar")

    def test_enroll_student_with_optional_links(self):
        """Criterio 5: al inscribir, se pueden mandar links opcionales."""
        response = self._post(
            f"/api/teacher/courses/{self.course.id}/students",
            {
                "first_name": "Carla",
                "last_name": "Ruiz",
                "email": "carla@alumnos.edu.ar",
                "links": [
                    {
                        "link_type": "GITHUB",
                        "url": "https://github.com/carla-ruiz",
                    },
                    {
                        "link_type": "LINKEDIN",
                        "url": "https://linkedin.com/in/carla-ruiz",
                    },
                ],
            },
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 200)
        carla = Student.objects.get(email="carla@alumnos.edu.ar")
        self.assertEqual(carla.links.count(), 2)

    def test_institution_can_edit_student_of_its_institution(self):
        """Criterio 3: la institucion tambien puede editar."""
        response = self._patch(
            f"/api/institution/students/{self.ana.id}",
            {"first_name": "Ana Maria"},
            self.institution_access,
        )

        self.assertEqual(response.status_code, 200)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Ana Maria")

    def test_institution_cannot_edit_student_of_another_institution(self):
        """Criterio 3: la institucion solo toca alumnos propios."""
        otra_institucion = Institution.objects.create(name="IFTS 24", city="CABA")
        otro_alumno = Student.objects.create(
            institution=otra_institucion,
            first_name="Delia",
            last_name="Vera",
            email="delia@alumnos.edu.ar",
        )

        response = self._patch(
            f"/api/institution/students/{otro_alumno.id}",
            {"first_name": "Hackeado"},
            self.institution_access,
        )

        self.assertEqual(response.status_code, 403)

    def test_delete_link_of_another_student_returns_400(self):
        """El service verifica que el link sea del alumno, no solo que exista."""
        otro_alumno = Student.objects.create(
            institution=self.institution,
            first_name="Bruno",
            last_name="Diaz",
            email="bruno@alumnos.edu.ar",
        )
        link_ajeno = StudentLink.objects.create(
            student=otro_alumno,
            link_type="GITHUB",
            url="https://github.com/bruno",
        )

        response = self._delete(
            f"/api/teacher/students/{self.ana.id}/links/{link_ajeno.id}",
            self.teacher_access,
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(StudentLink.objects.filter(pk=link_ajeno.id).exists())


class UnassignedSubjectMigrationTests(TransactionTestCase):
    """La migracion en dos pasos, sobre una base que ya tenia cursadas.

    Corre las migraciones de verdad: vuelve academics a la 0002 (la columna
    nullable), carga cursadas sin materia con los modelos de ese momento y
    avanza hasta la 0004. Una migracion de datos no se puede probar de otra
    forma: con los modelos de hoy la cursada sin materia ni siquiera se puede
    crear.
    """

    before = [("academics", "0002_subject_course_subject")]
    after = [("academics", "0004_alter_course_subject")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old_apps = executor.loader.project_state(self.before).apps

        Institution = old_apps.get_model("institutions", "Institution")
        User = old_apps.get_model("accounts", "User")
        Career = old_apps.get_model("academics", "Career")
        Course = old_apps.get_model("academics", "Course")

        institution = Institution.objects.create(name="IFTS 18")
        teacher = User.objects.create(
            email="diana@docentes.edu.ar",
            first_name="Diana",
            last_name="Docente",
            role="TEACHER",
        )
        self.career_id = Career.objects.create(
            institution=institution, name="Desarrollo de Software"
        ).id
        self.empty_career_id = Career.objects.create(
            institution=institution, name="Analisis de Sistemas"
        ).id
        # Dos cursadas en la misma carrera: tienen que compartir una sola
        # "Sin asignar", no una cada una.
        for name in ["1C - Noche", "2C - Manana"]:
            Course.objects.create(
                career_id=self.career_id,
                teacher=teacher,
                name=name,
                year=2025,
                term="FIRST",
            )

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        self.apps = executor.loader.project_state(self.after).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_each_career_with_courses_gets_one_unassigned_subject(self):
        Subject = self.apps.get_model("academics", "Subject")
        Course = self.apps.get_model("academics", "Course")

        subjects = list(Subject.objects.filter(career_id=self.career_id))

        self.assertEqual([subject.name for subject in subjects], ["Sin asignar"])
        self.assertEqual(Course.objects.filter(subject=subjects[0]).count(), 2)
        self.assertFalse(Course.objects.filter(subject__isnull=True).exists())

    def test_a_career_without_courses_gets_no_filler_subject(self):
        Subject = self.apps.get_model("academics", "Subject")

        self.assertFalse(Subject.objects.filter(career_id=self.empty_career_id).exists())
