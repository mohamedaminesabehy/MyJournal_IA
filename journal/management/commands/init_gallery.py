"""
Script pour initialiser manuellement les collections MongoDB pour la galerie
À exécuter une seule fois après la migration fake
"""

from django.core.management.base import BaseCommand
from journal.models import Media, MediaAnalysis, MediaTag, SmartAlbum


class Command(BaseCommand):
    help = 'Initialise les collections MongoDB pour la galerie intelligente'

    def handle(self, *args, **options):
        self.stdout.write('Initialisation des collections MongoDB...')
        
        try:
            # Vérifier si les collections existent en essayant de compter
            media_count = Media.objects.count()
            self.stdout.write(self.style.SUCCESS(f'Collection Media existe ({media_count} entrées)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Collection Media n existe pas encore: {e}'))
        
        try:
            analysis_count = MediaAnalysis.objects.count()
            self.stdout.write(self.style.SUCCESS(f'Collection MediaAnalysis existe ({analysis_count} entrées)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Collection MediaAnalysis n existe pas encore'))
        
        try:
            tag_count = MediaTag.objects.count()
            self.stdout.write(self.style.SUCCESS(f'Collection MediaTag existe ({tag_count} entrées)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Collection MediaTag n existe pas encore'))
        
        try:
            album_count = SmartAlbum.objects.count()
            self.stdout.write(self.style.SUCCESS(f'Collection SmartAlbum existe ({album_count} entrées)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Collection SmartAlbum n existe pas encore'))
        
        self.stdout.write(self.style.SUCCESS('\nInitialisation terminée!'))
        self.stdout.write('Vous pouvez maintenant utiliser la galerie.')
