"""Consultas de lectura de carreras, cursadas e inscripciones.

Los selectors son el unico lugar donde esta app arma querysets para que la lean
otros. La API los llama y devuelve lo que sale; nunca escribe un filter propio.
"""
from django.shortcuts import get_object_or_404

from apps.academics.models import Career,Subject, Course, CourseStudent, Student


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
    return CourseStudent.objects.of_course(course).with_student()


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

def teams_of_course(course):
    """Devuelve todos los equipos de una cursada."""
    return course.teams.all()

def team(course, team_id):
    """Busca un equipo específico asegurando que pertenezca a la cursada."""
    return course.teams.get(id=team_id)

def subjects_for_catalog(career_id=None, institution_id=None):
    """Materias que tienen al menos un proyecto aprobado, filtrables por carrera o institución."""
    from apps.projects.models import Project  # Importación local para evitar dependencia circular
    
    queryset = Subject.objects.filter(
        courses__projects__status__iexact="approved"  # <-- Acá estaba usando Project.Status
    ).distinct()

    if career_id:
        queryset = queryset.filter(career_id=career_id)
    if institution_id:
        queryset = queryset.filter(career__institution_id=institution_id)
    return queryset


def teachers_for_catalog(institution_id=None):
    """Docentes con al menos un proyecto aprobado en la institución."""
    from apps.projects.models import Project
    from apps.accounts.models import User

    queryset = User.objects.filter(
        courses__projects__status__iexact="approved"
    ).distinct()

    if institution_id:
        queryset = queryset.filter(
            courses__career__institution_id=institution_id
        ).distinct()
    return queryset


def courses_for_catalog(institution_id=None, subject_id=None, year=None):
    """Cursadas que tienen al menos un proyecto aprobado."""
    from apps.projects.models import Project

    queryset = Course.objects.filter(
        projects__status__iexact="approved"
    ).distinct().with_related()

    if institution_id:
        queryset = queryset.filter(career__institution_id=institution_id)
    if subject_id:
        queryset = queryset.filter(subject_id=subject_id)
    if year:
        queryset = queryset.filter(year=year)
    return queryset


def years_for_catalog():
    """Años de las cursadas que tienen proyectos aprobados, ordenados de mayor a menor."""
    from apps.projects.models import Project

    return (
        Course.objects.filter(projects__status__iexact="approved")
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )