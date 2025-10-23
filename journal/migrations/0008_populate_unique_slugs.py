from django.db import migrations, models
from django.utils.text import slugify


def generate_unique_slugs(apps, schema_editor):
    goal_model = apps.get_model('journal', 'Goal')
    existing = set()
    for obj in goal_model.objects.all():
        base = slugify(obj.title)[:200] if obj.title else 'goal'
        slug = base
        counter = 1
        while slug in existing or goal_model.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        obj.slug = slug
        obj.save(update_fields=['slug'])
        existing.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0007_add_goal_fields'),
    ]

    operations = [
        migrations.RunPython(generate_unique_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='goal',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]
