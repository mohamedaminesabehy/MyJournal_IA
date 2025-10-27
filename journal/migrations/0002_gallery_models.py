# Generated manually for gallery intelligent models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import journal.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('journal', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=200, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Vidéo'), ('audio', 'Audio')], max_length=10)),
                ('file', models.FileField(upload_to=journal.models.media_upload_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav'])])),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='gallery/thumbnails/')),
                ('file_size', models.BigIntegerField(default=0)),
                ('width', models.IntegerField(blank=True, null=True)),
                ('height', models.IntegerField(blank=True, null=True)),
                ('duration', models.FloatField(blank=True, null=True)),
                ('album', models.CharField(blank=True, max_length=100, null=True)),
                ('is_favorite', models.BooleanField(default=False)),
                ('is_analyzed', models.BooleanField(default=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='media', to='journal.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Média',
                'verbose_name_plural': 'Médias',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='SmartAlbum',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('album_type', models.CharField(choices=[('auto', 'Automatique'), ('manual', 'Manuel')], default='manual', max_length=10)),
                ('filter_criteria', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cover_image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='album_covers', to='journal.media')),
                ('media', models.ManyToManyField(blank=True, related_name='smart_albums', to='journal.Media')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='smart_albums', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Album Intelligent',
                'verbose_name_plural': 'Albums Intelligents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MediaAnalysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detected_objects', models.JSONField(blank=True, default=list)),
                ('detected_locations', models.JSONField(blank=True, default=list)),
                ('detected_faces', models.IntegerField(default=0)),
                ('dominant_colors', models.JSONField(blank=True, default=list)),
                ('color_palette', models.JSONField(blank=True, default=list)),
                ('detected_emotions', models.JSONField(blank=True, default=list)),
                ('mood', models.CharField(blank=True, max_length=50, null=True)),
                ('extracted_text', models.TextField(blank=True, null=True)),
                ('ai_title', models.CharField(blank=True, max_length=200, null=True)),
                ('ai_description', models.TextField(blank=True, null=True)),
                ('ai_summary', models.TextField(blank=True, null=True)),
                ('suggested_tags', models.JSONField(blank=True, default=list)),
                ('suggested_filters', models.JSONField(blank=True, default=list)),
                ('creative_suggestions', models.TextField(blank=True, null=True)),
                ('vision_api_used', models.CharField(blank=True, max_length=50, null=True)),
                ('generative_api_used', models.CharField(blank=True, max_length=50, null=True)),
                ('confidence_score', models.FloatField(default=0.0)),
                ('analyzed_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('media', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='journal.media')),
            ],
            options={
                'verbose_name': 'Analyse IA',
                'verbose_name_plural': 'Analyses IA',
            },
        ),
        migrations.CreateModel(
            name='MediaTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('source', models.CharField(choices=[('manual', 'Manuel'), ('ai', 'IA'), ('system', 'Système')], default='manual', max_length=10)),
                ('confidence', models.FloatField(default=1.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('media', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='journal.media')),
            ],
            options={
                'verbose_name': 'Tag Média',
                'verbose_name_plural': 'Tags Média',
                'ordering': ['-confidence', 'name'],
                'unique_together': {('media', 'name')},
            },
        ),
    ]
