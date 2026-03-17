# 📰 Newspaper RSS API (Django)

A backend service built using **Django** and **Django REST Framework** that aggregates news from external RSS feeds, stores them in a database, and exposes them via APIs for frontend applications.

The project follows a modular architecture with separate apps for **authentication** and **RSS/news management**, making it scalable and maintainable.

---

## 🚀 Features

- 📡 Fetch news articles from external RSS feeds  
- 🗂 Store and manage articles in the database  
- 🔗 Expose news via REST APIs  
- ❤️ Like/unlike posts  
- 🔐 User authentication (register, login, logout)  
- 🛠 Admin panel for managing feeds and posts  
- ✏️ Edit RSS sources and articles via admin  
- 🔄 Manual or scheduled RSS syncing  

---

## 📁 Project Structure

```text
newspaper-backend/
├── manage.py
├── readme.md
├── newspaper/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── articles/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
└── users/
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── tests.py
    └── views.py
```

- `manage.py`: Django management entry point
- `newspaper/`: Main project configuration, settings, and URL routing
- `articles/`: News article domain logic, admin setup, API views, and tests
- `users/`: Authentication and user-related logic, admin setup, API views, and tests


