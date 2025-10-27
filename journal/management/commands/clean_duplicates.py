from django.core.management.base import BaseCommand
from journal.models import MediaAnalysis
from django.conf import settings
from pymongo import MongoClient


class Command(BaseCommand):
    help = 'Nettoie les doublons de MediaAnalysis créés par get_or_create avec Djongo'

    def handle(self, *args, **options):
        self.stdout.write('Nettoyage des doublons MediaAnalysis...')
        
        # Se connecter directement à MongoDB
        db_settings = settings.DATABASES['default']
        client = MongoClient(db_settings['CLIENT']['host'])
        db = client[db_settings['NAME']]
        collection = db['journal_mediaanalysis']
        
        # Trouver les doublons par media_id
        pipeline = [
            {
                '$group': {
                    '_id': '$media_id',
                    'count': {'$sum': 1},
                    'ids': {'$push': '$_id'}
                }
            },
            {
                '$match': {
                    'count': {'$gt': 1}
                }
            }
        ]
        
        duplicates = list(collection.aggregate(pipeline))
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('\n✅ Aucun doublon trouvé!'))
            return
        
        deleted_count = 0
        for dup in duplicates:
            media_id = dup['_id']
            ids = dup['ids']
            count = dup['count']
            
            self.stdout.write(f'  Media {media_id}: {count} analyses trouvées')
            
            # Garder le premier, supprimer les autres
            ids_to_delete = ids[1:]
            for obj_id in ids_to_delete:
                collection.delete_one({'_id': obj_id})
                deleted_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'    ✓ {len(ids_to_delete)} doublon(s) supprimé(s)'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ {deleted_count} doublon(s) supprimé(s) avec succès!'))
