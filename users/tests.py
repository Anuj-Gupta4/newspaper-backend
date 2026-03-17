from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


User = get_user_model()


class AuthEndpointsTests(APITestCase):
    def test_register_creates_user_and_returns_token(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'StrongPass123!',
                'password_confirm': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='alice').exists())
        self.assertIn('token', response.data['data'])

    def test_login_returns_existing_user_token(self):
        user = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='StrongPass123!',
        )

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'bob', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user']['id'], user.id)
        self.assertIn('token', response.data['data'])

    def test_profile_returns_authenticated_user(self):
        user = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='StrongPass123!',
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], 'charlie')
