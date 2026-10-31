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
    Career,
    Course,
    CourseStudent,
    CourseTerm,
    Student,
    StudentLink,
    Subject,
)
from apps.accounts.models import UserRole
from apps.institutions import selectors as institutions_selectors


def create_career(institution, *, name):
    """Alta de una carrera."""
    name = name.strip()
    if Career.objects.of_institution(institution).filter(name__iexact=name).exists():
        raise ValidationError({"name": "La institucion ya tiene una carrera con ese nombre."})
    return Career.objects.create(institution=institution, name=name)


def create_subject(career, *, name):
    """Alta de una materia de la carrera.

    Mismo criterio que create_career: el nombre se compara sin distinguir
    mayusculas, porque "Programacion I" y "programacion i" son la misma materia
    y la restriccion de la base, que compara tal cual, no lo notaria.
    """
    name = name.strip()
    if not name:
        raise ValidationError({"name": "La materia necesita un nombre."})
    if Subject.objects.of_career(career).filter(name__iexact=name).exists():
        raise ValidationError({"name": "La carrera ya tiene una materia con ese nombre."})
    return Subject.objects.create(career=career, name=name)


def create_course(teacher, *, career_id, subject_id, name, year, term):
    """Alta de una cursada, hecha por el docente que la va a dictar.

    Aca aparece la regla de permisos del docente: no alcanza con tener el rol
    TEACHER (eso solo abre la puerta del router), hay que tener la membresia
    aceptada en la institucion duena de la carrera. El administrador queda
    afuera de la regla porque no representa a ninguna institucion: destraba.

    La cursada guarda su carrera y su materia, y la materia ya sabe de que
    carrera es: que las dos coincidan no lo puede garantizar la base, asi que
    se pregunta aca.

    El periodo llega como texto desde la API, asi que se valida contra las
    opciones antes de guardar: el choices del modelo no valida solo en un
    create(), solo arma el formulario y el admin.

    La comision repetida se busca antes de crearla: la restriccion de la base
    la rechazaria igual, pero como IntegrityError, y la API devolveria un 500
    en vez de explicar el problema.
    """
    career = selectors.career(career_id)
    membership = institutions_selectors.accepted_membership(teacher, career.institution)
    if membership is None and teacher.role != UserRole.ADMIN:
        raise ValidationError(
            {"career_id": "El docente no forma parte de la institucion de esa carrera."}
        )

    subject = selectors.subject(subject_id)
    if subject.career_id != career.id:
        raise ValidationError(
            {"subject_id": "La materia no pertenece a la carrera de la cursada."}
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
        subject=subject,
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
        if (
            email
            and Student.objects.of_institution(student.institution)
            .with_email(email)
            .exclude(pk=student.pk)
            .exists()
        ):
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
    url = url.strip()
    if student.links.filter(url=url).exists():
        raise ValidationError({"url": "Ese link ya esta cargado para el alumno."})

    link = StudentLink(
        student=student,
        link_type=link_type,
        title=title.strip(),
        url=url,
    )
    link.full_clean()
    link.save()
    return link


def remove_student_link(link):
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

    existing_urls = set(student.links.values_list("url", flat=True))
    for link_data in links or []:
        if link_data["url"].strip() in existing_urls:
            continue
        link = create_student_link(student, **link_data)
        existing_urls.add(link.url)

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
