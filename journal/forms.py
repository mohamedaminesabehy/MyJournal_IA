from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import mimetypes

from .models import (
    Note,
    Category,
    Goal,
    Media,
    MediaTag,
    SmartAlbum,
    Affirmation,
)

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'date_of_birth', 'location',)


class NoteForm(forms.ModelForm):
    """Formulaire pour créer/éditer une Note.

    Comportement compatible avec les deux variantes:
    - Utilise un ModelChoiceField pour `category` et filtre par utilisateur si fourni.
    - Sauvegarde tolérante: accepte soit une instance Category, soit un id/string venant d'un choix.
    """

    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Note
        fields = ['title', 'content', 'location', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Donnez un titre à votre note...', 'required': 'required'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Écrivez votre note ici...', 'rows': 10}),
            'location': forms.TextInput(attrs={'class': 'form-control mb-3', 'placeholder': 'Entrez un lieu ou utilisez votre position actuelle'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Support passing `user` from views (e.g. NoteForm(user=request.user))
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Ensure the category queryset is filtered by the provided user
        try:
            if user:
                qs = Category.objects.filter(users=user)
                if qs.exists():
                    # Normal case: ORM has Category objects linked to the user
                    self.fields['category'].queryset = qs
                else:
                    # Fallback: categories may be stored directly in MongoDB and not
                    # reflected as ORM objects. In that case, replace the field
                    # with a ChoiceField populated from the Mongo collection so the
                    # template shows options and the form still returns a PK value.
                    try:
                        from pymongo import MongoClient
                        from django.conf import settings
                        mongo_uri = settings.DATABASES['default']['CLIENT']['host']
                        client = MongoClient(mongo_uri)
                        db = client['journalDB']
                        collection = db['journal_category']
                        docs = list(collection.find({'$or': [{'user_id': user.id}, {'users': user.id}]}))
                        client.close()
                        choices = [('', '---------')]
                        for d in docs:
                            # prefer numeric 'id' (Djongo style) otherwise use _id
                            cid = d.get('id') or d.get('_id')
                            # ensure string/int stable representation
                            choices.append((str(cid), d.get('name', '')))
                        # replace ModelChoiceField with a ChoiceField
                        self.fields['category'] = forms.ChoiceField(choices=choices, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
                    except Exception:
                        # final defensive fallback
                        self.fields['category'].queryset = Category.objects.none()
            else:
                self.fields['category'].queryset = Category.objects.none()
        except Exception:
            # Be defensive: if Category model/query fails, default to empty queryset
            self.fields['category'].queryset = Category.objects.none()

    def clean_category(self):
        """Normalize category cleaned value:

        - If the field returned a Category instance, keep it.
        - If it returned a PK (string/int) from the ChoiceField fallback, return the PK
          so assigning to a ForeignKey (category_id) will work when saving the model.
        """
        val = self.cleaned_data.get('category')
        if val is None or val == '':
            return None
        # If it's already a Category instance, return it
        if isinstance(val, Category):
            return val

        # If the fallback ChoiceField returned a PK (string/int), try to
        # resolve it to a Category instance; if not present in ORM, create a
        # lightweight Category with that PK so Django can assign the FK.
        try:
            cid = int(val)
        except Exception:
            # Not an int-like value; return as-is and let validation fail later
            return val

        try:
            cat = Category.objects.filter(pk=cid).first()
            if cat:
                return cat
        except Exception:
            # ORM lookup failed; fall through to create lightweight instance
            pass

        # Create a transient Category instance with the given PK so the
        # ModelForm can assign the FK (Django will store category_id on save).
        try:
            tmp = Category()
            tmp.pk = cid
            return tmp
        except Exception:
            return None
# ==================== GALERIE INTELLIGENTE ====================

class MediaUploadForm(forms.ModelForm):
    """Formulaire pour uploader un seul média"""
    
    class Meta:
        model = Media
        fields = ['file', 'title', 'description', 'category', 'album']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du média (optionnel - l\'IA peut le générer)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description (optionnel - l\'IA peut la générer)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'album': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'album (optionnel)'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png',
                'required': 'required'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Rendre le fichier et la catégorie obligatoires
        self.fields['file'].required = True
        self.fields['category'].required = True
        self.fields['category'].empty_label = "Sélectionnez une catégorie *"
        
        # Filtrer les catégories par utilisateur
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)
        else:
            from .models import Category
            self.fields['category'].queryset = Category.objects.none()
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError('❌ Vous devez sélectionner un fichier à uploader.')
        
        # Vérifier la taille du fichier (50MB max)
        if file.size > 52428800:  # 50MB
            raise forms.ValidationError('❌ Le fichier ne doit pas dépasser 50MB.')
        
        # Vérifier l'extension (seulement JPG et PNG)
        filename = file.name.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        # Bloquer EXPLICITEMENT les extensions non autorisées (incluant JFIF)
        blocked_extensions = ['jfif', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        
        if ext in blocked_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non autorisée!\n\n'
                f'📋 Seules ces extensions sont acceptées: JPG, JPEG, PNG\n'
                f'Votre fichier: {file.name}'
            )
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non reconnue!\n\n'
                f'📋 Extensions acceptées: JPG, JPEG, PNG uniquement.\n'
                f'Votre fichier: {file.name}'
            )
        
        # Vérifier le type MIME pour plus de sécurité
        allowed_mime_types = ['image/jpeg', 'image/jpg', 'image/png']
        
        # Vérifier aussi le content_type si disponible
        if hasattr(file, 'content_type'):
            actual_mime = file.content_type.lower()
            if actual_mime not in allowed_mime_types:
                raise forms.ValidationError(
                    f'❌ Type de fichier non autorisé!\n\n'
                    f'📋 Formats acceptés: Images JPG et PNG uniquement.\n'
                    f'Type détecté: {actual_mime}\n'
                    f'Votre fichier: {file.name}'
                )
        
        return file


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget pour supporter l'upload multiple"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field pour gérer plusieurs fichiers"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class MultipleMediaUploadForm(forms.Form):
    """Formulaire pour uploader plusieurs médias en même temps (max 3 images JPG/PNG)"""
    
    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/jpg,image/png',
            'id': 'multipleFileInput',
            'required': 'required'
        })
    )
    category = forms.ModelChoiceField(
        queryset=None,  # Sera défini dans la vue
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Sélectionnez une catégorie *"
    )
    album = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de l\'album (optionnel)'
        })
    )
    auto_analyze = forms.BooleanField(
        required=False,
        initial=True,
        label='Analyser automatiquement avec l\'IA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)
    
    def clean_files(self):
        files = self.cleaned_data.get('files')
        
        if not files:
            raise forms.ValidationError('❌ Vous devez sélectionner au moins un fichier.')
        
        # Vérifier le nombre maximum de fichiers (3 max)
        if isinstance(files, list) and len(files) > 3:
            raise forms.ValidationError(
                f'❌ Trop de fichiers sélectionnés!\n\n'
                f'📋 Maximum autorisé: 3 images\n'
                f'Nombre sélectionné: {len(files)}'
            )
        
        # Valider chaque fichier
        if isinstance(files, list):
            for file in files:
                self._validate_single_file(file)
        else:
            self._validate_single_file(files)
        
        return files
    
    def _validate_single_file(self, file):
        """Valide un seul fichier"""
        # Vérifier la taille du fichier (50MB max)
        if file.size > 52428800:  # 50MB
            raise forms.ValidationError(
                f'❌ Fichier trop volumineux: "{file.name}"\n\n'
                f'📋 Taille maximum: 50MB\n'
                f'Taille du fichier: {file.size / (1024*1024):.2f}MB'
            )
        
        # Vérifier l'extension (seulement JPG et PNG)
        filename = file.name.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        # Bloquer EXPLICITEMENT les extensions non autorisées (incluant JFIF)
        blocked_extensions = ['jfif', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        
        if ext in blocked_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non autorisée!\n\n'
                f'📋 Seules ces extensions sont acceptées: JPG, JPEG, PNG\n'
                f'Fichier rejeté: {file.name}'
            )
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non reconnue!\n\n'
                f'📋 Extensions acceptées: JPG, JPEG, PNG uniquement.\n'
                f'Fichier rejeté: {file.name}'
            )
        
        # Vérifier le type MIME pour plus de sécurité
        allowed_mime_types = ['image/jpeg', 'image/jpg', 'image/png']
        
        # Vérifier le content_type si disponible
        if hasattr(file, 'content_type'):
            actual_mime = file.content_type.lower()
            if actual_mime not in allowed_mime_types:
                raise forms.ValidationError(
                    f'❌ Type de fichier non autorisé: "{file.name}"\n\n'
                    f'📋 Formats acceptés: Images JPG et PNG uniquement.\n'
                    f'Type détecté: {actual_mime}'
                )



class MediaTagForm(forms.ModelForm):
    """Formulaire pour ajouter des tags manuellement"""
    
    class Meta:
        model = MediaTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ajouter un tag...'
            })
        }


class SmartAlbumForm(forms.ModelForm):
    """Formulaire pour créer un album intelligent"""
    
    class Meta:
        model = SmartAlbum
        fields = ['name', 'description', 'album_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'album'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description de l\'album'
            }),
            'album_type': forms.Select(attrs={
                'class': 'form-control'
            })
        }


class GalleryFilterForm(forms.Form):
    """Formulaire pour filtrer la galerie"""
    
    MEDIA_TYPE_CHOICES = [
        ('', 'Tous les types'),
        ('image', 'Images'),
        ('video', 'Vidéos'),
        ('audio', 'Audio'),
    ]
    
    SORT_CHOICES = [
        ('-uploaded_at', 'Plus récent'),
        ('uploaded_at', 'Plus ancien'),
        ('title', 'Titre (A-Z)'),
        ('-title', 'Titre (Z-A)'),
        ('-file_size', 'Taille (plus grand)'),
        ('file_size', 'Taille (plus petit)'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '🔍 Rechercher...'
        })
    )
    media_type = forms.ChoiceField(
        choices=MEDIA_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_favorite = forms.BooleanField(
        required=False,
        label='Favoris uniquement',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_analyzed = forms.BooleanField(
        required=False,
        label='Analysés par IA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-uploaded_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'date_of_birth', 'location',)



class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        # Removed 'visibility' from the form fields intentionally (kept at model level)
        fields = ['title', 'description', 'start_date', 'end_date', 'status', 'motivation_level', 'priority', 'difficulty', 'reward', 'recurrence', 'milestones']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Titre de l\'objectif'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Décris ton objectif...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'motivation_level': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '10', 'class': 'form-range', 'step': '1'}),
            'priority': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'difficulty': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '5', 'class': 'form-range', 'step': '1'}),
            'reward': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Récompense prévue (optionnel)'}),
            'recurrence': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex : quotidien, hebdomadaire, mensuel (optionnel)'}),
            'milestones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Entrez les jalons en JSON simple: [{"title": "Étape 1", "due": "2025-10-31"}]'}),
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'start_date': 'Date de début',
            'end_date': 'Date de fin',
            'status': 'Statut',
            'motivation_level': 'Niveau de motivation',
            'priority': 'Priorité',
            'difficulty': 'Difficulté',
            'reward': 'Récompense',
            'recurrence': 'Récurrence',
            'milestones': 'Jalons',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Provide a friendly placeholder for milestones when none
        if not self.instance or not self.instance.milestones:
            example = '[{"title": "Étape 1", "due": "2025-11-01", "done": false}]'
            self.fields['milestones'].initial = example

    def clean_motivation_level(self):
        val = self.cleaned_data.get('motivation_level')
        if val is None:
            return 5
        if val < 1 or val > 10:
            raise forms.ValidationError('La motivation doit être entre 1 et 10.')
        return val

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and start > end:
            raise forms.ValidationError('La date de début doit être antérieure ou égale à la date de fin.')

        # validate & normalize milestones JSON structure
        milestones = cleaned.get('milestones')
        if milestones:
            cleaned['milestones'] = self._parse_milestones(milestones)

        return cleaned

    def _parse_milestones(self, val):
        """Parse milestones which may be provided as JSON string or a Python list.

        Returns a validated list of milestone dicts.
        """
        import json
        # Accept either a JSON string/list of dicts OR a plain newline-separated string
        if isinstance(val, str):
            val = val.strip()
            # try JSON first
            try:
                parsed = json.loads(val) if val else []
            except Exception:
                # fallback: interpret as plain text lines (one milestone per line)
                lines = [l.strip() for l in val.splitlines() if l.strip()]
                parsed = []
                for line in lines:
                    parsed.append({'title': line, 'done': False})
        else:
            parsed = val or []

        if not isinstance(parsed, list):
            raise forms.ValidationError('Les jalons doivent être une liste.')

        for m in parsed:
            if not isinstance(m, dict) or 'title' not in m:
                raise forms.ValidationError('Chaque jalon doit être un objet avec au moins une clé "title".')

        return parsed
        
        
        
        
            
class MediaUploadForm(forms.ModelForm):
    """Formulaire pour uploader un seul média"""
    
    class Meta:
        model = Media
        fields = ['file', 'title', 'description', 'category', 'album']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du média (optionnel - l\'IA peut le générer)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description (optionnel - l\'IA peut la générer)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'album': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'album (optionnel)'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png',
                'required': 'required'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Rendre le fichier et la catégorie obligatoires
        self.fields['file'].required = True
        self.fields['category'].required = True
        self.fields['category'].empty_label = "Sélectionnez une catégorie *"
        
        # Filtrer les catégories par utilisateur
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)
        else:
            from .models import Category
            self.fields['category'].queryset = Category.objects.none()
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError('❌ Vous devez sélectionner un fichier à uploader.')
        
        # Vérifier la taille du fichier (50MB max)
        if file.size > 52428800:  # 50MB
            raise forms.ValidationError('❌ Le fichier ne doit pas dépasser 50MB.')
        
        # Vérifier l'extension (seulement JPG et PNG)
        filename = file.name.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        # Bloquer EXPLICITEMENT les extensions non autorisées (incluant JFIF)
        blocked_extensions = ['jfif', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        
        if ext in blocked_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non autorisée!\n\n'
                f'📋 Seules ces extensions sont acceptées: JPG, JPEG, PNG\n'
                f'Votre fichier: {file.name}'
            )
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non reconnue!\n\n'
                f'📋 Extensions acceptées: JPG, JPEG, PNG uniquement.\n'
                f'Votre fichier: {file.name}'
            )
        
        # Vérifier le type MIME pour plus de sécurité
        allowed_mime_types = ['image/jpeg', 'image/jpg', 'image/png']
        
        # Vérifier aussi le content_type si disponible
        if hasattr(file, 'content_type'):
            actual_mime = file.content_type.lower()
            if actual_mime not in allowed_mime_types:
                raise forms.ValidationError(
                    f'❌ Type de fichier non autorisé!\n\n'
                    f'📋 Formats acceptés: Images JPG et PNG uniquement.\n'
                    f'Type détecté: {actual_mime}\n'
                    f'Votre fichier: {file.name}'
                )
        
        return file


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget pour supporter l'upload multiple"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field pour gérer plusieurs fichiers"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class MultipleMediaUploadForm(forms.Form):
    """Formulaire pour uploader plusieurs médias en même temps (max 3 images JPG/PNG)"""
    
    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/jpg,image/png',
            'id': 'multipleFileInput',
            'required': 'required'
        })
    )
    category = forms.ModelChoiceField(
        queryset=None,  # Sera défini dans la vue
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Sélectionnez une catégorie *"
    )
    album = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de l\'album (optionnel)'
        })
    )
    auto_analyze = forms.BooleanField(
        required=False,
        initial=True,
        label='Analyser automatiquement avec l\'IA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)
    
    def clean_files(self):
        files = self.cleaned_data.get('files')
        
        if not files:
            raise forms.ValidationError('❌ Vous devez sélectionner au moins un fichier.')
        
        # Vérifier le nombre maximum de fichiers (3 max)
        if isinstance(files, list) and len(files) > 3:
            raise forms.ValidationError(
                f'❌ Trop de fichiers sélectionnés!\n\n'
                f'📋 Maximum autorisé: 3 images\n'
                f'Nombre sélectionné: {len(files)}'
            )
        
        # Valider chaque fichier
        if isinstance(files, list):
            for file in files:
                self._validate_single_file(file)
        else:
            self._validate_single_file(files)
        
        return files
    
    def _validate_single_file(self, file):
        """Valide un seul fichier"""
        # Vérifier la taille du fichier (50MB max)
        if file.size > 52428800:  # 50MB
            raise forms.ValidationError(
                f'❌ Fichier trop volumineux: "{file.name}"\n\n'
                f'📋 Taille maximum: 50MB\n'
                f'Taille du fichier: {file.size / (1024*1024):.2f}MB'
            )
        
        # Vérifier l'extension (seulement JPG et PNG)
        filename = file.name.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        # Bloquer EXPLICITEMENT les extensions non autorisées (incluant JFIF)
        blocked_extensions = ['jfif', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        
        if ext in blocked_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non autorisée!\n\n'
                f'📋 Seules ces extensions sont acceptées: JPG, JPEG, PNG\n'
                f'Fichier rejeté: {file.name}'
            )
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non reconnue!\n\n'
                f'📋 Extensions acceptées: JPG, JPEG, PNG uniquement.\n'
                f'Fichier rejeté: {file.name}'
            )
        
        # Vérifier le type MIME pour plus de sécurité
        allowed_mime_types = ['image/jpeg', 'image/jpg', 'image/png']
        
        # Vérifier le content_type si disponible
        if hasattr(file, 'content_type'):
            actual_mime = file.content_type.lower()
            if actual_mime not in allowed_mime_types:
                raise forms.ValidationError(
                    f'❌ Type de fichier non autorisé: "{file.name}"\n\n'
                    f'📋 Formats acceptés: Images JPG et PNG uniquement.\n'
                    f'Type détecté: {actual_mime}'
                )


class MediaEditForm(forms.ModelForm):
    """Formulaire pour éditer les informations d'un média"""
    
    class Meta:
        model = Media
        fields = ['file', 'title', 'description', 'category', 'album', 'is_favorite']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du média'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'album': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'album'
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le fichier est optionnel en édition (on garde l'ancien si non fourni)
        self.fields['file'].required = False
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        # Si aucun nouveau fichier, retourner None (on garde l'ancien)
        if not file:
            return None
        
        # Sinon, valider le nouveau fichier
        # Vérifier la taille du fichier (50MB max)
        if file.size > 52428800:  # 50MB
            raise forms.ValidationError('❌ Le fichier ne doit pas dépasser 50MB.')
        
        # Vérifier l'extension (seulement JPG et PNG)
        filename = file.name.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        # Bloquer EXPLICITEMENT les extensions non autorisées (incluant JFIF)
        blocked_extensions = ['jfif', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        
        if ext in blocked_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non autorisée!\n\n'
                f'📋 Seules ces extensions sont acceptées: JPG, JPEG, PNG\n'
                f'Votre fichier: {file.name}'
            )
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'❌ Extension ".{ext.upper()}" non reconnue!\n\n'
                f'📋 Extensions acceptées: JPG, JPEG, PNG uniquement.\n'
                f'Votre fichier: {file.name}'
            )
        
        # Vérifier le type MIME pour plus de sécurité
        allowed_mime_types = ['image/jpeg', 'image/jpg', 'image/png']
        
        # Vérifier aussi le content_type si disponible
        if hasattr(file, 'content_type'):
            actual_mime = file.content_type.lower()
            if actual_mime not in allowed_mime_types:
                raise forms.ValidationError(
                    f'❌ Type de fichier non autorisé!\n\n'
                    f'📋 Formats acceptés: Images JPG et PNG uniquement.\n'
                    f'Type détecté: {actual_mime}\n'
                    f'Votre fichier: {file.name}'
                )
        
        return file


class MediaTagForm(forms.ModelForm):
    """Formulaire pour ajouter des tags manuellement"""
    
    class Meta:
        model = MediaTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ajouter un tag...'
            })
        }

class SmartAlbumForm(forms.ModelForm):
    """Formulaire pour créer un album intelligent"""
    
    class Meta:
        model = SmartAlbum
        fields = ['name', 'description', 'album_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'album'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description de l\'album'
            }),
            'album_type': forms.Select(attrs={
                'class': 'form-control'
            })
        }

class GalleryFilterForm(forms.Form):
    """Formulaire pour filtrer la galerie"""
    
    MEDIA_TYPE_CHOICES = [
        ('', 'Tous les types'),
        ('image', 'Images'),
        ('video', 'Vidéos'),
        ('audio', 'Audio'),
    ]
    
    SORT_CHOICES = [
        ('-uploaded_at', 'Plus récent'),
        ('uploaded_at', 'Plus ancien'),
        ('title', 'Titre (A-Z)'),
        ('-title', 'Titre (Z-A)'),
        ('-file_size', 'Taille (plus grand)'),
        ('file_size', 'Taille (plus petit)'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '🔍 Rechercher...'
        })
    )
    media_type = forms.ChoiceField(
        choices=MEDIA_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_favorite = forms.BooleanField(
        required=False,
        label='Favoris uniquement',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_analyzed = forms.BooleanField(
        required=False,
        label='Analysés par IA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-uploaded_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from .models import Category
            self.fields['category'].queryset = Category.objects.filter(users=user)



from .models import Affirmation

class AffirmationForm(forms.ModelForm):
    class Meta:
        model = Affirmation
        fields = ["text", "tone", "topic"]
        widgets = {
            "text": forms.Textarea(attrs={"rows":2, "placeholder":"I am calm and focused..."}),
        }