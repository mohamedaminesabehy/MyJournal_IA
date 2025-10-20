from django import forms
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
