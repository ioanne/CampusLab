from datetime import datetime

from typing import Literal, Optional #literal con esto le decimos a ninja 'este campo solo puede tener exacto estos valores' (LINKEDIN, GITHUB, ETC)
                                     #optional dice 'puede venir o no' (para el PATCH, [edicion parcial el cliente puede cambiar el email y no el nombre])
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


class CourseIn(Schema):
    """Lo que manda el docente para abrir una cursada.

    El ciclo lectivo son dos campos sueltos y no el id de otra tabla: year es el
    ano y term una de las opciones de CourseTerm.
    """

    career_id: int
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
    teacher_name: str

    @staticmethod
    def resolve_term_label(obj):
        """El texto legible sale del modelo y no se reescribe en el front."""
        return obj.get_term_display()

    @staticmethod
    def resolve_teacher_name(obj):
        return obj.teacher.full_name

#schemas de links de ALUMNO (primero por studentOut los usa)

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

#EL schema para actualizar un alumno (PATCH)

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
    links: list[StudentLinkOut] = []  # el corchete por que si el student o alumno no tiene links la API devuelve "links":[] en lugar de null. (Para frontend)


class EnrollStudentIn(Schema):
    """Lo que carga el docente para sumar un alumno a su cursada.

    No hay contrasena ni cuenta: el alumno no entra a la plataforma. El email es
    opcional, pero es lo unico que permite reconocerlo si ya fue cargado en otra
    cursada de la misma institucion.
    """

    first_name: str
    last_name: str
    email: str = ""
    links: list[StudentLinkIn] = [] #cuando teacher inscriba a alumno el json puede incluir un campo links con una lista de links.

class EnrollmentOut(Schema):
    id: int
    student: StudentOut
    created_at: datetime










