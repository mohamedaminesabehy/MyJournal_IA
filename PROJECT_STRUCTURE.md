# 📂 Structure du Projet MyJournal IA

```
MyJournal_IA-amineBranch/
│
├── 📄 manage.py                    # Script principal Django
├── 📄 README.md                    # Documentation complète
├── 📄 QUICKSTART.md                # Guide de démarrage rapide
├── 📄 LICENSE                      # Licence MIT
├── 📄 requirements.txt             # Dépendances Python
├── 📄 .env.example                 # Template de configuration
├── 📄 .gitignore                   # Règles Git
├── 📄 db.sqlite3                   # Base de données SQLite
│
├── 📁 journal/                     # 🎯 Application principale
│   ├── 📄 __init__.py
│   ├── 📄 models.py               # Modèles de données
│   ├── 📄 views.py                # Vues principales
│   ├── 📄 views_albums.py         # Vues albums intelligents
│   ├── 📄 views_training.py       # Vues analytics
│   ├── 📄 forms.py                # Formulaires Django
│   ├── 📄 urls.py                 # Routes URL
│   ├── 📄 admin.py                # Interface admin
│   ├── 📄 signals.py              # Signals Django
│   ├── 📄 tests.py                # Tests unitaires
│   │
│   ├── 📁 ai_services/            # 🤖 Services IA
│   │   ├── 📄 __init__.py
│   │   └── 📄 config.py           # Configuration APIs
│   │
│   ├── 📁 services/               # 💼 Services métier
│   │   ├── 📄 __init__.py
│   │   └── 📄 vision_service.py   # Analyse d'images (CLIP)
│   │
│   ├── 📁 management/             # ⚙️ Commandes Django
│   │   └── 📁 commands/
│   │
│   └── 📁 migrations/             # 🗄️ Migrations DB
│       ├── 📄 __init__.py
│       └── 📄 0001_initial.py
│
├── 📁 my_journal_intime/          # ⚙️ Configuration Django
│   ├── 📄 __init__.py
│   ├── 📄 settings.py             # Paramètres du projet
│   ├── 📄 urls.py                 # URLs principales
│   ├── 📄 wsgi.py                 # Configuration WSGI
│   └── 📄 asgi.py                 # Configuration ASGI
│
├── 📁 template/                   # 🎨 Templates HTML
│   ├── 📄 base.html               # Template de base
│   ├── 📄 home.html               # Page d'accueil
│   ├── 📄 dashboard.html          # Tableau de bord
│   ├── 📄 signin.html             # Connexion
│   ├── 📄 signup.html             # Inscription
│   ├── 📄 profile.html            # Profil utilisateur
│   ├── 📄 create_note.html        # Créer une entrée
│   ├── 📄 modern_notes.html       # Liste des entrées
│   ├── 📄 gallery.html            # Galerie de médias
│   ├── 📄 media_upload.html       # Upload de médias
│   ├── 📄 media_detail.html       # Détail d'un média
│   ├── 📄 media_edit.html         # Édition d'un média
│   ├── 📄 media_delete_confirm.html
│   ├── 📄 album_detail.html       # Détail d'un album
│   ├── 📄 smart_albums_list.html  # Liste albums intelligents
│   ├── 📄 category_management.html
│   └── 📄 statistics.html
│
├── 📁 static/                     # 📦 Fichiers statiques (dev)
│   ├── 📁 css/
│   ├── 📁 js/
│   └── 📁 images/
│
├── 📁 staticfiles/                # 📦 Fichiers statiques (prod)
│   └── (générés par collectstatic)
│
├── 📁 media/                      # 📸 Uploads utilisateur
│   └── 📁 gallery/                # Images/vidéos uploadées
│       ├── 📁 username1/
│       ├── 📁 username2/
│       └── 📁 thumbnails/
│
└── 📁 venv/                       # 🐍 Environnement virtuel Python
    └── (environnement isolé)
```

---

## 📊 Modèles de Données

### 🧑 **UserProfile**
- Profil utilisateur étendu
- Date de naissance, localisation

### 📁 **Category**
- Catégories personnalisées
- Icons, couleurs

### 🖼️ **Media**
- Images, vidéos, audio
- Métadonnées (taille, dimensions, durée)
- Relations : user, category, album

### 🤖 **MediaAnalysis**
- Résultats d'analyse IA
- Objets détectés
- Lieux/monuments
- Couleurs dominantes
- Émotions
- Descriptions générées

### 🏷️ **MediaTag**
- Tags manuels et automatiques
- Source : manual, ai, system
- Score de confiance

### 📚 **SmartAlbum**
- Albums intelligents automatiques
- Critères de filtrage
- Type : auto, manual

---

## 🔧 Services IA

### 📸 **VisionAIService** (`journal/services/vision_service.py`)

Analyse complète d'images avec :
- **Détection d'objets** - CLIP (Hugging Face)
- **Reconnaissance de monuments** - Patterns couleurs + CLIP
- **Analyse des couleurs** - K-means clustering
- **Détection d'émotions** - Analyse contextuelle
- **Descriptions** - Génération automatique

**Monuments détectés :**
- Tour Eiffel (Paris)
- Arc de Triomphe (Paris)
- Pyramides (Égypte)
- Et plus encore...

### 🎭 **EmotionAnalyzer** (À venir)
- Analyse de sentiment de texte
- Détection d'émotions multiples
- Score d'humeur global
- Tendances temporelles

### 💬 **TextGenerator** (À venir)
- Génération de titres
- Résumés automatiques
- Prompts personnalisés
- Légendes créatives

---

## 🚀 Flux de Travail

### 1. Upload d'un média
```
User upload → Media.save() 
→ Signal post_save 
→ VisionAIService.analyze_image() 
→ MediaAnalysis.save() 
→ MediaTag.create() 
→ SmartAlbum.auto_organize()
```

### 2. Création d'une entrée
```
User écrit → JournalEntry.save() 
→ (À venir) EmotionAnalyzer.analyze_text() 
→ (À venir) Generate insights 
→ Update user stats
```

### 3. Rappel intelligent
```
Cron job → ReminderService.check_users() 
→ Analyze user habits 
→ Generate personalized message 
→ Send notification
```

---

## 📈 Prochaines Fonctionnalités

### Phase 1 - En cours 🔄
- [ ] Rappels intelligents complets
- [ ] Analyse d'humeur avancée
- [ ] Génération de titres automatiques

### Phase 2 - Planifié 🎯
- [ ] Support audio avec transcription
- [ ] Timeline interactive
- [ ] Rétrospectives automatiques

### Phase 3 - Futur 🔮
- [ ] Recherche sémantique
- [ ] Export PDF/Livre photo
- [ ] Application mobile

---

## 🧪 Tests

```bash
# Lancer tous les tests
python manage.py test

# Tests d'une app spécifique
python manage.py test journal

# Tests avec coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 📝 Conventions de Code

- **Python** : PEP 8
- **Django** : Django Coding Style
- **Noms de fichiers** : snake_case
- **Classes** : PascalCase
- **Fonctions/variables** : snake_case
- **Constantes** : UPPER_CASE

---

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit vos changements
4. Push vers la branche
5. Ouvrir une Pull Request

---

**Documentation générée le 23 octobre 2025**
