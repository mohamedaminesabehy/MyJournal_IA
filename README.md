# 📔 MyJournal IA - Journal Personnel Intelligent

> Un journal intime moderne enrichi par l'intelligence artificielle pour capturer vos pensées, émotions et souvenirs de manière intelligente.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ Fonctionnalités Principales

### 📝 **Journal Multimodal**
- ✍️ Entrées textuelles riches
- 📸 Support images, vidéos et audio
- 🎨 Éditeur de texte moderne
- 🏷️ Tags et catégorisation

### 🤖 **Intelligence Artificielle**
- 🎭 **Analyse d'humeur automatique** - Détecte vos émotions et suit votre bien-être
- 📊 **Insights émotionnels** - Graphiques d'humeur sur 30 jours
- 💡 **Suggestions personnalisées** - Prompts d'écriture basés sur votre historique
- 🔔 **Rappels intelligents** - S'adaptent à vos habitudes d'écriture
- 🎯 **Détection de patterns** - Identifie vos tendances émotionnelles

### 🖼️ **Galerie Intelligente**
- 🔍 Vision AI - Détection d'objets, lieux, monuments
- 🎨 Analyse des couleurs dominantes
- 🏛️ Reconnaissance de monuments (Tour Eiffel, Arc de Triomphe, Pyramides...)
- 😊 Détection d'émotions dans les images
- 🏷️ Tags automatiques
- 📁 Albums intelligents automatiques

### 📈 **Analyse & Statistiques**
- 📊 Tableau de bord analytique
- 🔥 Suivi des séquences d'écriture (streaks)
- 📅 Timeline interactive de vos entrées
- 🌈 Visualisation des émotions
- 📖 Rétrospectives mensuelles/annuelles

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- pip
- virtualenv (recommandé)

### Étapes d'installation

1. **Cloner le repository**
```bash
git clone https://github.com/votre-repo/MyJournal_IA.git
cd MyJournal_IA-amineBranch
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
```

3. **Activer l'environnement virtuel**

Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

Linux/Mac:
```bash
source venv/bin/activate
```

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

5. **Configuration de l'environnement**

Créer un fichier `.env` à la racine du projet (voir `.env.example`):
```env
SECRET_KEY=votre_secret_key_django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données (optionnel, SQLite par défaut)
DATABASE_URL=sqlite:///db.sqlite3

# APIs (optionnel pour fonctionnalités avancées)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_VISION_API_KEY=your_google_vision_key_here
```

6. **Créer la base de données**
```bash
python manage.py migrate
```

7. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

8. **Lancer le serveur de développement**
```bash
python manage.py runserver
```

9. **Accéder à l'application**
- Application: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

---

## 📁 Structure du Projet

```
MyJournal_IA-amineBranch/
├── journal/                      # Application principale
│   ├── ai_services/             # Services IA
│   │   ├── config.py           # Configuration APIs
│   │   └── __init__.py
│   ├── services/                # Services métier
│   │   ├── vision_service.py   # Analyse d'images (CLIP, Vision AI)
│   │   └── __init__.py
│   ├── management/              # Commandes Django personnalisées
│   │   └── commands/
│   ├── migrations/              # Migrations de base de données
│   ├── models.py               # Modèles de données
│   ├── views.py                # Vues principales
│   ├── views_albums.py         # Vues pour albums intelligents
│   ├── views_training.py       # Vues pour training/analytics
│   ├── forms.py                # Formulaires Django
│   ├── urls.py                 # Routes URL
│   ├── admin.py                # Configuration admin
│   ├── signals.py              # Signals Django
│   └── tests.py                # Tests unitaires
│
├── my_journal_intime/           # Configuration Django
│   ├── settings.py             # Paramètres du projet
│   ├── urls.py                 # URLs principales
│   ├── wsgi.py                 # Configuration WSGI
│   └── asgi.py                 # Configuration ASGI
│
├── template/                    # Templates HTML
│   ├── base.html               # Template de base
│   ├── dashboard.html          # Tableau de bord
│   ├── gallery.html            # Galerie de médias
│   ├── media_detail.html       # Détail d'un média
│   ├── album_detail.html       # Détail d'un album
│   └── ...
│
├── static/                      # Fichiers statiques (CSS, JS, images)
├── media/                       # Fichiers uploadés par les utilisateurs
│   └── gallery/                # Images/vidéos de la galerie
│
├── manage.py                    # Script de gestion Django
├── requirements.txt             # Dépendances Python
├── .env.example                # Exemple de configuration
└── README.md                   # Ce fichier
```

---

## 🎯 Utilisation

### Créer une entrée de journal
1. Connectez-vous à votre compte
2. Cliquez sur "Nouvelle entrée" dans le dashboard
3. Rédigez votre texte, ajoutez des images/médias
4. Choisissez des tags et une catégorie
5. Sauvegardez - l'IA analysera automatiquement votre humeur

### Galerie intelligente
1. Accédez à "Galerie" depuis le menu
2. Uploadez vos photos/vidéos
3. L'IA détecte automatiquement :
   - Objets présents
   - Lieux et monuments
   - Couleurs dominantes
   - Émotions
4. Des tags sont créés automatiquement
5. Les albums intelligents s'organisent seuls

### Analyse d'humeur
- Consultez votre dashboard pour voir les graphiques d'humeur
- L'IA détecte automatiquement votre sentiment (positif/négatif/neutre)
- Recevez des insights sur vos patterns émotionnels
- Suivez votre évolution dans le temps

### Rappels intelligents
- Configurez vos préférences dans "Paramètres"
- L'IA apprend vos meilleurs moments d'écriture
- Recevez des rappels personnalisés selon votre contexte
- Les messages s'adaptent à votre humeur et séquence d'écriture

---

## 🔧 Technologies Utilisées

### Backend
- **Django 4.2** - Framework web Python
- **Python 3.9+** - Langage de programmation
- **SQLite** - Base de données (dev)
- **Pillow** - Traitement d'images

### Intelligence Artificielle
- **Hugging Face Transformers** - Modèles de deep learning
- **CLIP (OpenAI)** - Vision AI pour analyse d'images
- **OpenCV** - Traitement d'images avancé
- **scikit-learn** - Machine learning (K-means pour couleurs)
- **NumPy** - Calculs numériques

### Frontend
- **HTML5/CSS3** - Structure et style
- **Bootstrap 5** - Framework CSS
- **JavaScript (Vanilla)** - Interactivité
- **Chart.js** - Graphiques interactifs
- **AOS** - Animations au scroll

---

## 🎨 Fonctionnalités IA Détaillées

### 🔍 Vision AI (Analyse d'images)

#### Détection d'objets
```python
# Détecte automatiquement les éléments dans vos photos
detected_objects = [
    {"object": "plage", "confidence": 0.92},
    {"object": "mer", "confidence": 0.88},
    {"object": "coucher de soleil", "confidence": 0.85}
]
```

#### Reconnaissance de monuments
```python
# Identifie les monuments célèbres
detected_locations = [
    {
        "landmark": "Tour Eiffel",
        "city": "Paris",
        "confidence": 0.95
    }
]
```

#### Analyse des couleurs
```python
# Extrait la palette de couleurs dominantes
dominant_colors = [
    {"hex": "#FF5733", "name": "rouge orangé", "percentage": 45},
    {"hex": "#33B5FF", "name": "bleu ciel", "percentage": 30}
]
```

### 🎭 Analyse d'Émotions

L'IA analyse vos entrées textuelles pour détecter :
- **Sentiment général** : Positif, Négatif, Neutre
- **Émotions spécifiques** : Joie, Tristesse, Colère, Peur, Surprise
- **Intensité émotionnelle** : Score de 0 à 1
- **Thèmes récurrents** : Travail, Famille, Santé, Loisirs

### 📊 Insights & Analytics

- **Graphiques d'humeur** : Visualisation sur 7/30/90 jours
- **Détection de patterns** : "Vous êtes plus heureux les vendredis"
- **Alertes bien-être** : Détection de périodes difficiles
- **Évolution personnelle** : Suivi de votre croissance émotionnelle

---

## 🚧 Roadmap

### Version 1.0 (Actuelle) ✅
- [x] Système de journal de base
- [x] Galerie avec analyse Vision AI
- [x] Analyse d'humeur basique
- [x] Albums intelligents
- [x] Dashboard avec statistiques

### Version 1.5 (En cours) 🔄
- [ ] Rappels intelligents complets
- [ ] Génération de titres automatiques
- [ ] Prompts d'écriture personnalisés
- [ ] Détection de patterns avancée
- [ ] Rétrospectives automatiques

### Version 2.0 (Planifié) 🎯
- [ ] Support audio (notes vocales + transcription)
- [ ] Timeline interactive complète
- [ ] Analyse multimodale (texte + images)
- [ ] Export PDF/Livre photo
- [ ] Application mobile
- [ ] Synchronisation cloud

### Version 3.0 (Futur) 🔮
- [ ] Recherche sémantique en langage naturel
- [ ] Chatbot personnel basé sur votre historique
- [ ] Recommandations de contenu
- [ ] Partage sélectif avec proches
- [ ] Analyse vocale (ton, émotion)

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créez une branche pour votre feature (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📝 License

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 👤 Auteur

**Amine** - Développeur Full Stack & IA

---

## 🙏 Remerciements

- OpenAI pour CLIP
- Hugging Face pour les modèles pré-entraînés
- La communauté Django
- Tous les contributeurs

---

## 📧 Support

Pour toute question ou problème :
- Ouvrez une issue sur GitHub
- Email : support@myjournal-ia.com

---

## 🌟 Star le projet !

Si vous aimez ce projet, n'hésitez pas à lui donner une ⭐ sur GitHub !

---

**Fait avec ❤️ et 🤖 IA**
