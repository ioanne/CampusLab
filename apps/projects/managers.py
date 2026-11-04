"""Filtros reutilizables del catalogo de proyectos."""

from django.db import models

# Donde mira search: los datos del proyecto y los de su cursada. Los de la
# cursada se leen cruzando la relacion, igual que los filtros de abajo, porque
# el proyecto no los guarda.
SEARCH_FIELDS = (
    "title",
    "summary",
    "description",
    "team_name",
    "students__student__first_name",
    "students__student__last_name",
    "course__teacher__first_name",
    "course__teacher__last_name",
    "course__subject__name",
    "course__career__name",
    "course__career__institution__name",
    "technologies__technology__name",
)


def _matches_word(word):
    """Un OR de icontains: la palabra aparece en alguno de los campos."""
    condition = models.Q()
    for field in SEARCH_FIELDS:
        condition |= models.Q(**{f"{field}__icontains": word})
    return condition


class ProjectQuerySet(models.QuerySet):
    """Cada metodo hace una sola cosa y devuelve otro queryset, asi se encadenan:
    Project.objects.approved().of_year(2026).with_student("ana").

    Que vivan aca y no sueltos en la API tiene tres consecuencias practicas:
    "aprobado" se define una sola vez, los mismos filtros sirven para el
    catalogo publico, para la lista del docente y para la bandeja de la
    institucion, y nada de esto se repite el dia que haya que agregar un filtro
    nuevo.

    Casi todos los filtros cruzan la cursada, porque el proyecto no guarda ni la
    carrera ni la institucion ni el docente: los tiene una sola vez, en course.
    El doble guion bajo sigue la relacion hasta donde el dato vive de verdad.
    """

    def approved(self):
        # El import va aca adentro y no arriba: models.py importa este archivo,
        # y que los dos se importen arriba seria un import circular.
        from apps.projects.models import ProjectStatus

        return self.filter(status=ProjectStatus.APPROVED)

    def of_teacher(self, user):
        # Los proyectos de un docente son los de sus cursadas: quien carga el
        # proyecto es siempre el docente que dicta esa comision.
        return self.filter(course__teacher=user)

    def of_course(self, course_id):
        return self.filter(course_id=course_id)

    def search(self, text):
        """Cada palabra tiene que aparecer en algun campo: AND entre palabras,
        OR entre campos. "ana django" deja los proyectos que tienen una Ana en
        algun lado y que ademas usan Django.

        Cada palabra se busca por separado y no todas juntas en un solo
        filter(). Dentro de un mismo filter(), las condiciones sobre una
        relacion de a muchos se cumplen en la MISMA fila: "gomez diaz" pediria
        un alumno que se llame Gomez y Diaz a la vez. Por separado, cada palabra
        cruza la relacion por su cuenta y puede caer en un integrante distinto.

        Y cada palabra va en su propia subconsulta (pk__in), no en un filter()
        encadenado. Encadenados, cada filter() suma sus propios joins a alumnos
        y tecnologias en la misma consulta: las filas se multiplican con cada
        palabra y con 15 palabras SQLite se queda sin joins (admite 64). Con la
        subconsulta, los cruces son de una palabra por vez y la consulta de
        afuera no cruza ninguna relacion de a muchos.

        icontains en SQLite ignora mayusculas solo en las letras ASCII: "MUSEO"
        encuentra "Museo", pero una vocal con tilde o una enie en mayuscula no
        encuentra la misma letra en minuscula. Ignorar acentos queda para
        cuando se pase a PostgreSQL.
        """
        queryset = self
        for word in text.split():
            projects_with_word = self.model._default_manager.filter(
                _matches_word(word)
            ).values("pk")
            queryset = queryset.filter(pk__in=projects_with_word)
        # Con las subconsultas ya no salen repetidos, porque la consulta de
        # afuera no cruza alumnos ni tecnologias. El distinct() lo deja
        # asegurado aunque mas adelante se sume un filtro que si los cruce.
        return queryset.distinct()

    def with_student(self, name):
        # Cruza una relacion de a muchos: sin distinct(), un proyecto de equipo
        # aparece una vez por cada alumno que coincide.
        return self.filter(
            models.Q(students__student__first_name__icontains=name)
            | models.Q(students__student__last_name__icontains=name)
        ).distinct()

    def with_technology(self, technology_id):
        # technologies son las filas de la tabla del medio, asi que el filtro
        # cruza dos relaciones: de proyecto a ProjectTechnology y de ahi a la
        # tecnologia.
        return self.filter(technologies__technology_id=technology_id).distinct()

    def of_institution(self, institution):
        # Acepta la institucion o su id: la bandeja pasa el objeto que ya tiene
        # y el catalogo publico, el id que vino en la URL.
        return self.filter(course__career__institution=institution)

    def of_career(self, career_id):
        return self.filter(course__career_id=career_id)

    def of_year(self, year):
        # El ciclo lectivo es un campo de la cursada: no hay catalogo de anios
        # ni una tabla que mantener al dia.
        return self.filter(course__year=year)

    def of_team(self, text):
        return self.filter(team_name__icontains=text)

    def with_related(self):
        """Trae en pocas consultas todo lo que necesita la ficha completa.

        Sin esto, cada proyecto de la lista dispararia consultas extra: es el
        problema N+1. Como la carrera, la institucion y el docente se responden
        cruzando la cursada, el select_related tiene que traer esa cadena
        entera; si no, preguntar por project.institution en el template o en el
        schema seria una consulta por proyecto.

        select_related sirve para las relaciones de a uno y prefetch_related
        para las de a muchos, sin importar en que app viva cada modelo del
        camino.
        """
        return self.select_related(
            "course",
            "course__career",
            "course__career__institution",
            "course__subject",
            "course__teacher",
            "reviewed_by",
        ).prefetch_related(
            "technologies__technology",
            "students__student",
            "assets",
            "links",
        )
