from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.academics.managers import (
    CareerQuerySet,
    CourseQuerySet,
    CourseStudentQuerySet,
    StudentQuerySet,
    SubjectQuerySet,
)


class Career(models.Model):
    """Carrera de una institucion.

    No existe suelta: cada carrera pertenece a una institucion, y por eso el
    nombre es unico por institucion y no global (dos institutos pueden dictar
    "Desarrollo de Software" cada uno con la suya).

    Antes la carrera tambien guardaba la familia profesional. Ese campo se fue:
    servia para clasificar el banco de proyectos viejo, que tenia cinco
    catalogos, y aca no queda nadie que lo consulte. Un campo que nadie lee es
    un campo que hay que seguir completando sin ganar nada a cambio.
    """

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="careers",
    )
    name = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CareerQuerySet.as_manager()

    class Meta:
        verbose_name = "carrera"
        verbose_name_plural = "carreras"
        ordering = ["institution__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="carrera_unica_por_institucion",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.institution.name})"


class Subject(models.Model):
    """Materia de una carrera: lo que se dicta en una cursada.

    Cuelga de la carrera y no de la institucion por la misma razon que la
    carrera cuelga de la institucion: "Programacion I" de Desarrollo de Software
    y la de Analisis de Sistemas son materias distintas, cada una de su plan.

    El nombre es unico por carrera. La restriccion de la base compara tal cual;
    el service compara sin distinguir mayusculas, igual que con las carreras.
    """

    career = models.ForeignKey(
        Career,
        on_delete=models.CASCADE,
        related_name="subjects",
        verbose_name="carrera",
    )
    name = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SubjectQuerySet.as_manager()

    class Meta:
        verbose_name = "materia"
        verbose_name_plural = "materias"
        ordering = ["career__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["career", "name"],
                name="materia_unica_por_carrera",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.career.name})"


class CourseTerm(models.TextChoices):
    """Cuando se dicta la cursada dentro del ano."""

    FIRST = "FIRST", "Primer cuatrimestre"
    SECOND = "SECOND", "Segundo cuatrimestre"
    FULL_YEAR = "FULL_YEAR", "Anual"


class Course(models.Model):
    """Cursada: la comision concreta donde un docente organiza a sus alumnos.

    Pertenece a una carrera y esta asociada al docente que la dicta. Es la
    unidad de trabajo del docente: carga aca a sus alumnos y despues cuelga de
    ella los proyectos que esos alumnos hicieron.

    El ciclo lectivo vive en dos campos propios (year y term) y no en una tabla
    aparte. Antes habia una app entera para eso, con un modelo AcademicYear al
    que la cursada apuntaba. El criterio para sacarla: un ciclo lectivo no es
    una entidad con vida propia en este sistema. Nadie lo consulta suelto, no
    tiene datos colgando ni comportamiento propio, y su unico uso era escribir
    "2026" al lado del nombre de la comision. Una tabla que solo guarda el ano
    obliga a darla de alta antes de poder crear una cursada, y a un JOIN cada
    vez que se lee: dos costos a cambio de nada.
    """

    career = models.ForeignKey(
        Career,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name="materia",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name="docente",
    )
    name = models.CharField(max_length=120, verbose_name="comision")
    year = models.PositiveSmallIntegerField(
        verbose_name="ciclo lectivo",
        help_text="El ano en que se dicta la cursada, por ejemplo 2026.",
    )
    term = models.CharField(
        max_length=10,
        choices=CourseTerm.choices,
        verbose_name="periodo",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CourseQuerySet.as_manager()

    class Meta:
        verbose_name = "cursada"
        verbose_name_plural = "cursadas"
        ordering = ["-year", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["career", "year", "term", "name"],
                name="cursada_unica_por_carrera_ciclo_y_periodo",
            )
        ]

    def __str__(self):
        return (
            f"{self.career.name} - {self.name} ({self.year} {self.get_term_display()})"
        )

    @property
    def institution(self):
        """La institucion se responde desde la carrera: no se guarda dos veces.

        Guardar aca un segundo ForeignKey a la institucion seria mas comodo de
        consultar y una fuente segura de datos contradictorios: bastaria mover
        la carrera de institucion para que la cursada quedara mintiendo.
        """
        return self.career.institution


class Student(models.Model):
    """Alumno: un dato que carga el docente, no una cuenta de la plataforma.

    En la version anterior el alumno era un User con rol STUDENT: entraba con
    su contrasena y cargaba sus propios proyectos. Aca los actores son dos, la
    institucion y el docente, asi que el alumno no inicia sesion. Se lo carga
    para poder decir quien hizo cada proyecto, y eso es todo lo que necesita
    ser: nombre, apellido y (si se sabe) email.

    Cuelga de la institucion y no de la cursada a proposito. Si colgara de la
    cursada habria un Ana Gomez distinto por cada materia que cursa, y no habria
    forma de saber que son la misma persona. Colgando de la institucion, la
    segunda vez que un docente la carga se reusa la fila que ya existe y todos
    sus proyectos quedan atados al mismo alumno.
    """

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="students",
    )
    first_name = models.CharField(max_length=150, verbose_name="nombre")
    last_name = models.CharField(max_length=150, verbose_name="apellido")
    email = models.EmailField(
        max_length=255,
        blank=True,
        help_text="Opcional: el docente puede cargar un alumno sin conocer su email.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StudentQuerySet.as_manager()

    class Meta:
        verbose_name = "alumno"
        verbose_name_plural = "alumnos"
        ordering = ["last_name", "first_name"]
        constraints = [
            # El email es opcional pero unico cuando esta. Un unique comun no
            # alcanza: con dos alumnos sin email los dos guardan "" y el segundo
            # seria rechazado por repetido. La condicion deja afuera de la regla
            # a las filas con el email vacio, que son justamente las que no se
            # pueden comparar entre si.
            models.UniqueConstraint(
                fields=["institution", "email"],
                condition=~models.Q(email=""),
                name="alumno_unico_por_email_en_institucion",
            )
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class CourseStudent(models.Model):
    """Inscripcion: este alumno cursa esta comision.

    Es la tabla intermedia entre Course y Student, escrita a mano como todas
    las de este proyecto. Que sea un modelo propio es lo que permite guardarle
    datos a la inscripcion (hoy la fecha) y borrar una sola inscripcion sin
    tocar al alumno, que sigue existiendo en la institucion.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="alumno",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CourseStudentQuerySet.as_manager()

    class Meta:
        verbose_name = "alumno de cursada"
        verbose_name_plural = "alumnos de cursadas"
        ordering = ["student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"],
                name="alumno_unico_por_cursada",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} en {self.course}"


class StudentLinkType(models.TextChoices):
    """Son 4: lo que se pide siempre el Linkedin y gitHub; PORTFOLIO es para su pagina personal/portfolio, y OTHER para
    cualquier otra cosa (un blog, etc,etc)"""

    LINKEDIN = "LINKEDIN", "LinkedIn"
    GITHUB = "GITHUB", "Github"
    PORTFOLIO = "PORTFOLIO", "Portfolio"
    OTHER = "OTHER", "Otro"


class StudentLink(models.Model):
    """La URL es unica por alumno para no cargar el link dos veces.
    Si el tipo es LINKEDIN, la URL tiene que ser linkedin.com. Si es GITHUB, tiene que ser github.com.
    Para PORTFOLIO Y OTHER, cualquier URL válida sirve."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="links",
        verbose_name="alumno",
    )
    link_type = models.CharField(
        max_length=12,
        choices=StudentLinkType.choices,
        verbose_name="tipo de link",
    )

    title = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="titulo",
    )
    url = models.URLField(verbose_name="direccion")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "link del alumno"
        verbose_name_plural = "links del alumno"
        ordering = ["link_type", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "url"],
                name="link_unico_por_alumno",
            )
        ]

    def __str__(self):
        return self.title or self.url

    def clean(self):
        super().clean()

        if not self.url:
            return

        parsed = urlparse(self.url)
        hostname = parsed.hostname or ""

        if parsed.scheme not in {"http", "https"}:
            raise ValidationError(
                {"url": "La URL tiene que empezar con http:// o https://."}
            )

        if self.link_type == StudentLinkType.LINKEDIN:
            if not (hostname == "linkedin.com" or hostname.endswith(".linkedin.com")):
                raise ValidationError(
                    {"url": "Si el tipo es LinkedIn, la URL debe ser de linkedin.com."}
                )

        if self.link_type == StudentLinkType.GITHUB:
            if not (hostname == "github.com" or hostname.endswith(".github.com")):
                raise ValidationError(
                    {"url": "Si el tipo es GitHub, la URL debe ser de github.com."}
                )
