# Newspaper RSS API (Django)

A backend service built using **Django** and **Django REST Framework** that aggregates news from external RSS feeds, stores them in a database, and exposes them via APIs for frontend applications.

The project follows a modular architecture with separate apps for **authentication** and **RSS/news management**, making it scalable and maintainable.

---

## Features

- Fetch news articles from external RSS feeds  
- Store and manage articles in the database  
- Expose news via REST APIs  
- Like/unlike posts  
- User authentication with JWT bearer tokens  
- Redis caching for improved API performance  
- Admin panel for managing feeds and posts  
- Edit RSS sources and articles via admin  
- Manual or scheduled RSS syncing  

---

## Project Structure

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
│   ├── serializers.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
└── users/
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── serializers.py
    ├── urls.py
    ├── views.py
    └── tests.py
```

- `manage.py`: Django management entry point
- `newspaper/`: Main project configuration, settings, and root URL routing
- `articles/`: Article domain logic including models, serializers, API views, and app routes
- `users/`: Authentication and user-related logic including models, serializers, API views, and app routes


Notes:

- Keep the endpoint responses consistent throughout the app
- Authenticate protected endpoints with `Authorization: Bearer <access_token>`