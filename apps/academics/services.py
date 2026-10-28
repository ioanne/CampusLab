"""Operaciones que modifican carreras, cursadas y alumnos.

El circuito se lee en los nombres: la institucion crea carreras, el docente que
forma parte de ella abre cursadas, y en esas cursadas carga a sus alumnos.

Las reglas viven aca y no en la API: son verdades del negocio y valen igual si
manana el alta se hace desde el admin, desde un comando o desde un test.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.academics import selectors
from apps.academics.models import (
    Career, Course, CourseStudent, CourseTerm, Student, StudentLink,
)
from apps.accounts.models import UserRole
from apps.institutions import selectors as institutions_selectors


def create_career(institution, *, name):
    """Alta de una carrera."""
    name = name.strip()
    if Career.objects.of_institution(institution).filter(name__iexact=name).exists():
        raise ValidationError({"name": "La institucion ya tiene una carrera con ese nombre."})
    return Career.objects.create(institution=institution, name=name)


def create_course(teacher, *, career_id, name, year, term):
    """Alta de una cursada, hecha por el docente que la va a dictar."""
    career = selectors.career(career_id)
    membership = institutions_selectors.accepted_membership(teacher, career.institution)
    if membership is None and teacher.role != UserRole.ADMIN:
        raise ValidationError(
            {"career_id": "El docente no forma parte de la institucion de esa carrera."}
        )

    if term not in CourseTerm.values:
        raise ValidationError(
            {"term": f"Periodo invalido. Opciones: {', '.join(CourseTerm.values)}."}
        )

    name = name.strip()
    if Course.objects.filter(career=career, year=year, term=term, name=name).exists():
        raise ValidationError(
            {"name": "Ya existe esa comision en esa carrera, ano y periodo."}
        )

    return Course.objects.create(
        career=career,
        teacher=teacher,
        name=name,
        year=year,
        term=term,
    )


def update_student(student, *, first_name=None, last_name=None, email=None):
    """Edita los datos basicos de un alumno ya creado.

    Todos los parametros son opcionales (None) porque es un PATCH: el cliente
    puede mandar solo el email, o solo el nombre. Los que no vienen, no se tocan.

    El email es unico por institucion (lo dice el UniqueConstraint del modelo),
    pero la base de datos lanzaria un IntegrityError (500) si se repite. Aca lo
    detectamos antes y devolvemos un ValidationError (400) con un mensaje claro.
    """
    if first_name is not None:
        student.first_name = first_name.strip()
    if last_name is not None:
        student.last_name = last_name.strip()
    if email is not None:
        email = email.strip().lower()
        otro = (
            Student.objects.of_institution(student.institution)
            .with_email(email)
            .exclude(pk=student.pk)
            .first()
        )
        if otro is not None:
            raise ValidationError(
                {"email": "Ya hay otro alumno en esta institucion con ese email."}
            )
        student.email = email

    if not student.first_name or not student.last_name:
        raise ValidationError({"last_name": "El alumno necesita nombre y apellido."})

    student.full_clean()
    student.save()
    return student


def create_student_link(student, *, link_type, title="", url):
    """Crea un link para un alumno.

    La validacion del dominio (LinkedIn -> linkedin.com, GitHub -> github.com)
    vive en el clean() del modelo. Aca la disparamos con full_clean().
    Tambien valida el UniqueConstraint (student, url): no se puede cargar el
    mismo link dos veces para el mismo alumno.
    """
    link = StudentLink(
        student=student,
        link_type=link_type,
        title=title.strip(),
        url=url.strip(),
    )
    link.full_clean()
    link.save()
    return link


def remove_student_link(student, link_id):
    """Borra un link del alumno.

    Busca el link por id Y por alumno: si el link es de otro alumno, no lo
    encuentra y devuelve un error. Asi nadie puede borrar links ajenos pasando
    un id que no le corresponde.
    """
    link = StudentLink.objects.filter(pk=link_id, student=student).first()
    if link is None:
        raise ValidationError(
            {"link_id": "El link no existe o no pertenece a este alumno."}
        )
    link.delete()


@transaction.atomic
def enroll_student(course, *, first_name, last_name, email="", links=None):
    """Carga un alumno en una cursada, reusando el que ya existe en la institucion.

    NUEVO: si se mandan links opcionales, se crean para el alumno en la misma
    transaccion. Si un link falla (ej: LinkedIn con URL de GitHub), se revierte
    todo: ni el alumno ni la inscripcion quedan.
    """
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()

    if not first_name or not last_name:
        raise ValidationError({"last_name": "El alumno necesita nombre y apellido."})

    institution = course.institution
    student = None
    if email:
        student = Student.objects.of_institution(institution).with_email(email).first()

    if student is None:
        student = Student.objects.create(
            institution=institution,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    if CourseStudent.objects.of_course(course).filter(student=student).exists():
        raise ValidationError({"student": "El alumno ya esta inscripto en esta cursada."})

    # NUEVO: crear los links si vinieron en el pedido
    for link_data in (links or []):
        create_student_link(student, **link_data)

    return CourseStudent.objects.create(course=course, student=student)


def remove_enrollment(enrollment):
    """Saca a un alumno de una cursada."""
    participations = getattr(enrollment.student, "project_participations", None)
    if participations is not None and participations.filter(project__course=enrollment.course).exists():
        raise ValidationError(
            {
                "enrollment_id": (
                    "El alumno figura en un proyecto de esta cursada: primero hay que "
                    "sacarlo del proyecto."
                )
            }
        )
    enrollment.delete()