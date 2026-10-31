from django.contrib import admin

from apps.academics.models import Career, Course, CourseStudent, Student, Subject


class CourseStudentInline(admin.TabularInline):
    """Los alumnos de la cursada se ven y se cargan desde la cursada misma."""

    model = CourseStudent
    extra = 0
    autocomplete_fields = ["student"]


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "created_at"]
    search_fields = ["name", "institution__name"]
    list_filter = ["institution"]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "career", "created_at"]
    # search_fields es lo que hace funcionar el autocomplete de la cursada.
    search_fields = ["name", "career__name"]
    list_filter = ["career__institution"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "career", "teacher", "year", "term", "created_at"]
    search_fields = ["name", "subject__name", "career__name", "teacher__email"]
    list_filter = ["year", "term", "career__institution"]
    autocomplete_fields = ["subject"]
    inlines = [CourseStudentInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "email", "institution", "created_at"]
    # search_fields es lo que hace funcionar el autocomplete del inline.
    search_fields = ["last_name", "first_name", "email"]
    list_filter = ["institution"]


@admin.register(CourseStudent)
class CourseStudentAdmin(admin.ModelAdmin):
    list_display = ["student", "course", "created_at"]
    search_fields = ["student__last_name", "student__email", "course__name"]
