from django.db import migrations

def create_default_subjects(apps, schema_editor):
    Career = apps.get_model("academics", "Career")
    Subject = apps.get_model("academics", "Subject")
    Course = apps.get_model("academics", "Course")

    for career in Career.objects.all():
        subject, _ = Subject.objects.get_or_create(
            career=career,
            name="Sin asignar"
        )
        Course.objects.filter(career=career, subject__isnull=True).update(subject=subject)

class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0003_alter_teammember_student_subject_course_subject_and_more'), 
    ]

    operations = [
        migrations.RunPython(create_default_subjects),
    ]
