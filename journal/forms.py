from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import Media, MediaTag, SmartAlbum
import mimetypes
from django.contrib.auth.forms import UserCreationForm
from .models import Note, Category
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'date_of_birth', 'location',)


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
            self.fields['category'].queryset = Category.objects.filter(user=user)
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
            self.fields['category'].queryset = Category.objects.filter(user=user)
    
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
            self.fields['category'].queryset = Category.objects.filter(user=user)

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'date_of_birth', 'location',)
class NoteForm(forms.ModelForm):
    # Redéfinir le champ category comme ChoiceField pour éviter la validation de ForeignKey
    category = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Note
        fields = ['title', 'content', 'location']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Donnez un titre à votre note...', 'required': 'required'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Écrivez votre note ici...', 'rows': 10}),
            'location': forms.TextInput(attrs={'class': 'form-control mb-3', 'placeholder': 'Entrez un lieu ou utilisez votre position actuelle'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(NoteForm, self).__init__(*args, **kwargs)
        if user:
            # Charger les catégories sans validation de ForeignKey
            try:
                categories = [(cat.id, cat.name) for cat in Category.objects.filter(user=user)]
                categories.insert(0, ('', 'Aucune catégorie (optionnel)'))
                self.fields['category'].choices = categories
            except:
                self.fields['category'].choices = [('', 'Aucune catégorie (optionnel)')]
    
    def save(self, commit=True):
        instance = super(NoteForm, self).save(commit=False)
        # Gérer manuellement la catégorie
        category_id = self.cleaned_data.get('category')
        if category_id:
            try:
                instance.category = Category.objects.get(id=category_id)
            except:
                instance.category = None
        else:
            instance.category = None
        
        if commit:
            instance.save()
        return instance
            
            
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
            self.fields['category'].queryset = Category.objects.filter(user=user)
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
            self.fields['category'].queryset = Category.objects.filter(user=user)
    
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
            self.fields['category'].queryset = Category.objects.filter(user=user)



from .models import Affirmation

class AffirmationForm(forms.ModelForm):
    class Meta:
        model = Affirmation
        fields = ["text", "tone", "topic"]
        widgets = {
            "text": forms.Textarea(attrs={"rows":2, "placeholder":"I am calm and focused..."}),
        }