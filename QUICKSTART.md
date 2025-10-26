# 🚀 Guide de Démarrage Rapide - MyJournal IA

## Installation en 5 minutes

### 1️⃣ Cloner et préparer l'environnement
```powershell
# Cloner le projet
git clone https://github.com/votre-repo/MyJournal_IA.git
cd MyJournal_IA-amineBranch

# Créer l'environnement virtuel
python -m venv venv

# Activer (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

### 2️⃣ Configuration
```powershell
# Copier le fichier d'exemple
Copy-Item .env.example .env

# Éditer .env et ajouter votre SECRET_KEY
# Vous pouvez en générer une avec:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3️⃣ Base de données
```powershell
# Créer les tables
python manage.py migrate

# Créer un compte admin
python manage.py createsuperuser
# Suivez les instructions (username, email, password)
```

### 4️⃣ Lancer l'application
```powershell
# Démarrer le serveur
python manage.py runserver

# Ouvrir dans votre navigateur
# http://127.0.0.1:8000/
```

## 🎯 Premiers pas

### Créer votre première entrée
1. Connectez-vous avec votre compte
2. Cliquez sur "Dashboard"
3. Cliquez sur "Nouvelle entrée"
4. Écrivez quelques phrases
5. Ajoutez une image (optionnel)
6. Sauvegardez

✨ **L'IA analyse automatiquement votre humeur !**

### Tester la galerie intelligente
1. Allez dans "Galerie"
2. Cliquez sur "Uploader"
3. Ajoutez une photo (ex: Tour Eiffel, paysage, etc.)
4. Attendez quelques secondes
5. Cliquez sur "Analyser avec l'IA"

🤖 **L'IA détecte objets, lieux, couleurs automatiquement !**

### Voir vos statistiques
1. Retournez au "Dashboard"
2. Consultez vos graphiques d'humeur
3. Voyez votre séquence d'écriture (streak)
4. Découvrez vos insights personnalisés

## 🛠️ Commandes utiles

```powershell
# Créer une nouvelle migration
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic

# Lancer les tests
python manage.py test

# Accéder au shell Django
python manage.py shell

# Créer une sauvegarde de la DB
python manage.py dumpdata > backup.json

# Restaurer une sauvegarde
python manage.py loaddata backup.json
```

## 🐛 Résolution de problèmes

### Erreur de migration
```powershell
# Supprimer la DB et recommencer
Remove-Item db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Module non trouvé
```powershell
# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Port 8000 déjà utilisé
```powershell
# Utiliser un autre port
python manage.py runserver 8080
```

### Erreur CLIP/Transformers
```powershell
# Installer torch avec CPU uniquement (plus léger)
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## 📚 Ressources

- **Documentation Django**: https://docs.djangoproject.com/
- **Hugging Face Transformers**: https://huggingface.co/docs/transformers/
- **CLIP Model**: https://github.com/openai/CLIP

## 💡 Conseils

### Pour développement
- Gardez `DEBUG=True` dans `.env`
- Utilisez SQLite (par défaut)
- Les médias sont dans `media/gallery/`

### Pour production
- Changez `DEBUG=False`
- Utilisez PostgreSQL
- Configurez un serveur web (Nginx + Gunicorn)
- Activez HTTPS

## 🎉 C'est tout !

Vous êtes prêt à utiliser votre journal intelligent ! 

**Besoin d'aide ?** Ouvrez une issue sur GitHub ou consultez le README.md complet.
