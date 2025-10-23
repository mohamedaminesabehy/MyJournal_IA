from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0006_auto_20251022_1718'),
    ]

    operations = [
        migrations.AddField(
            model_name='goal',
            name='priority',
            field=models.IntegerField(choices=[(1, 'Faible'), (2, 'Moyenne'), (3, 'Haute')], default=2),
        ),
        migrations.AddField(
            model_name='goal',
            name='visibility',
            field=models.CharField(choices=[('private', 'Privé'), ('public', 'Public')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='goal',
            name='reward',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='goal',
            name='difficulty',
            field=models.IntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)]),
        ),
        migrations.AddField(
            model_name='goal',
            name='recurrence',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='goal',
            name='milestones',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='slug',
            field=models.SlugField(blank=True, max_length=220),
        ),
        migrations.AddField(
            model_name='goal',
            name='progress_cached',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
