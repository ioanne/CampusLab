from datetime import datetime
from typing import Literal, Optional

from ninja import Schema


class CareerIn(Schema):
    name: str


class CareerOut(Schema):
    id: int
    name: str
    institution_id: int
    institution_name: str

    @staticmethod
    def resolve_institution_name(obj):
        return obj.institution.name


class SubjectIn(Schema):
    name: str


class SubjectOut(Schema):
    id: int
    name: str
    career_id: int


class CourseIn(Schema):
    """Lo que manda el docente para abrir una cursada.

    El ciclo lectivo son dos campos sueltos y no el id de otra tabla: year es el
    ano y term una de las opciones de CourseTerm. La materia tiene que ser de esa
    misma carrera: lo controla el service.
    """

    career_id: int
    subject_id: int
    name: str
    year: int
    term: str


class CourseOut(Schema):
    id: int
    name: str
    year: int
    term: str
    term_label: str
    career: CareerOut
    subject: SubjectOut
    teacher_name: str

    @staticmethod
    def resolve_term_label(obj):
        """El texto legible sale del modelo y no se reescribe en el front."""
        return obj.get_term_display()

    @staticmethod
    def resolve_teacher_name(obj):
        return obj.teacher.full_name


class StudentLinkIn(Schema):
    """Lo que el cliente manda para crear un link de alumno.

    - link_type: solo acepta los 4 valores exactos (LINKEDIN, GITHUB, PORTFOLIO, OTHER).
      Si mandan "TWITTER", Ninja devuelve un error 422 automatico.
    - title: opcional, por defecto vacio.
    - url: obligatorio, tiene que ser un string (Django valida que sea URL valida mas adelante).
    """
    link_type: Literal["LINKEDIN", "GITHUB", "PORTFOLIO", "OTHER"]
    title: str = ""
    url: str


class StudentLinkOut(Schema):
    """Lo que la API devuelve al leer un link.

    No incluimos 'student_id' ni 'created_at' porque el front no los necesita
    para mostrar el link en la ficha del alumno.
    """
    id: int
    link_type: str
    title: str
    url: str


class StudentUpdateIn(Schema):
    """Lo que se puede editar de un alumno ya creado.

    Todos los campos son Optional porque es un PATCH (edicion parcial):
    el cliente puede mandar solo el email, o solo el nombre, o todo junto.
    Si un campo no viene, queda como None y el service no lo toca.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None


class StudentOut(Schema):
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    links: list[StudentLinkOut] = []


class EnrollStudentIn(Schema):
    """Lo que carga el docente para sumar un alumno a su cursada.

    No hay contrasena ni cuenta: el alumno no entra a la plataforma. El email es
    opcional, pero es lo unico que permite reconocerlo si ya fue cargado en otra
    cursada de la misma institucion.
    """

    first_name: str
    last_name: str
    email: str = ""
    links: list[StudentLinkIn] = []


class EnrollmentOut(Schema):
    id: int
    student: StudentOut
    created_at: datetime
