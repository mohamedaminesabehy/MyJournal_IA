from django.core.management.base import BaseCommand
from journal.models import Note
from journal.utils import predict_emotion as predict_func, lr_model

class Command(BaseCommand):
    help = 'Update existing notes with emotion predictions'

    def handle(self, *args, **options):
        if not lr_model:
            self.stdout.write(
                self.style.ERROR('Emotion prediction model not loaded. Check model file.')
            )
            return

        notes_without_emotion = Note.objects.filter(emotion__isnull=True)
        total_notes = notes_without_emotion.count()
        
        if total_notes == 0:
            self.stdout.write(
                self.style.SUCCESS('All notes already have emotion predictions.')
            )
            return

        self.stdout.write(f'Updating emotions for {total_notes} notes...')
        
        updated_count = 0
        for note in notes_without_emotion:
            try:
                if note.content:
                    emotion, confidence = predict_func(note.content, lr_model)
                    if emotion:
                        note.emotion = emotion
                        note.emotion_confidence = float(confidence * 100)
                        note.save()
                        updated_count += 1
                        self.stdout.write(f'Updated note "{note.title}" - Emotion: {emotion} ({confidence:.1%})')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error updating note "{note.title}": {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated emotions for {updated_count} notes.')
        )