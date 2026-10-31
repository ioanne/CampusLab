"""Consultas de lectura de carreras, cursadas e inscripciones.

Los selectors son el unico lugar donde esta app arma querysets para que la lean
otros. La API los llama y devuelve lo que sale; nunca escribe un filter propio.
"""
from django.shortcuts import get_object_or_404

from apps.academics.models import (
    Career,
    Course,
    CourseStudent,
    Student,
    StudentLink,
    Subject,
)


def careers(institution_id=None, search=None):
    """Lista publica: sirve para navegar y para el filtro del catalogo."""
    queryset = Career.objects.with_institution()
    if institution_id:
        queryset = queryset.filter(institution_id=institution_id)
    if search:
        queryset = queryset.search(search)
    return queryset


def career(career_id):
    return get_object_or_404(Career.objects.with_institution(), pk=career_id)


def subjects_of_career(career):
    """Las materias de una carrera: lo que la institucion gestiona."""
    return Subject.objects.of_career(career).with_career()


def subject(subject_id):
    return get_object_or_404(Subject.objects.with_career(), pk=subject_id)


def courses_of_teacher(teacher):
    """Las cursadas que dicta ese docente: lo que ve al entrar."""
    return Course.objects.of_teacher(teacher).with_related()


def courses_of_institution(institution):
    """Todas las cursadas de la institucion, sin importar el docente."""
    return Course.objects.of_institution(institution).with_related()


def course(course_id):
    return get_object_or_404(Course.objects.with_related(), pk=course_id)


def enrollments_of_course(course):
    """Los alumnos inscriptos en una cursada, con el alumno ya cargado."""
    return CourseStudent.objects.of_course(course).with_student_links()


def enrollment(course, enrollment_id):
    """Una inscripcion, buscada DENTRO de la cursada.

    La cursada no es un adorno del filtro: es lo que impide que un docente
    borre la inscripcion de otra comision pasando un id ajeno. Si el id no
    pertenece a esta cursada la respuesta es 404, no un borrado.
    """
    return get_object_or_404(
        CourseStudent.objects.of_course(course).with_student(), pk=enrollment_id
    )


def students_enrolled_in_course(course, student_ids):
    """De esos ids, los alumnos que de verdad estan inscriptos en la cursada.

    Vive en academics y no en projects porque la inscripcion es un dato de esta
    app: quien cursa que comision lo sabe la tabla CourseStudent. La app de
    proyectos necesita esa respuesta para validar los participantes que carga
    el docente, asi que la pregunta; no arma un queryset sobre una tabla ajena.
    Comparar la cantidad que devuelve contra la cantidad de ids pedidos alcanza
    para saber si alguno se colo.
    """
    return Student.objects.filter(
        enrollments__course=course, id__in=student_ids
    ).distinct()


def student(student_id):
    """Busca un alumno por id, con sus links precargados.

    El prefetch_related evita el problema N+1: en lugar de hacer 1 consulta
    para el alumno y N para sus links, hace 2 en total.
    """
    return get_object_or_404(
        Student.objects.prefetch_related("links"),
        pk=student_id,
    )


def student_link(student, link_id):
    return get_object_or_404(StudentLink.objects.filter(student=student), pk=link_id)


def teacher_has_student(teacher, student):
    return CourseStudent.objects.filter(student=student, course__teacher=teacher).exists()
