from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Note, Category
from django.contrib.auth.models import User
from .models import Goal

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'date_of_birth', 'location',)

class NoteForm(forms.ModelForm):
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
        user = kwargs.pop('user', None)
        super(NoteForm, self).__init__(*args, **kwargs)
        if user:
            # Adapter à ManyToMany: seules les catégories associées à l'utilisateur
            # doivent être sélectionnables
            self.fields['category'].queryset = Category.objects.filter(users=user)


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
            'recurrence': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: daily, weekly, monthly (optionnel)'}),
            'milestones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Entrez les jalons en JSON simple: [{"title": "Étape 1", "due": "2025-10-31"}]'}),
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
