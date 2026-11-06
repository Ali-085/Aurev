"""
Email Verification Tests

Tests for:
- Token generation and validation
- User registration with inactive status
- Email verification flow
- Resend verification with cooldown
- Rate limiting
- Security features (anti-enumeration, logging)
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import time

from users.tokens import email_verification_token
from users.emails import send_verification_email, EmailServiceError

User = get_user_model()


class EmailVerificationTokenTests(TestCase):
    """Test token generation and validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.is_active = False
        self.user.save()
    
    def test_token_generation(self):
        """Test that tokens are generated successfully"""
        token = email_verification_token.make_token(self.user)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)
    
    def test_token_validation_success(self):
        """Test that valid tokens pass validation"""
        token = email_verification_token.make_token(self.user)
        is_valid = email_verification_token.check_token(self.user, token)
        self.assertTrue(is_valid)
    
    def test_token_validation_failure_wrong_token(self):
        """Test that invalid tokens fail validation"""
        is_valid = email_verification_token.check_token(self.user, 'invalid-token')
        self.assertFalse(is_valid)
    
    def test_token_validation_failure_wrong_user(self):
        """Test that tokens for different users fail validation"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        token = email_verification_token.make_token(self.user)
        is_valid = email_verification_token.check_token(other_user, token)
        self.assertFalse(is_valid)
    
    def test_token_invalidated_after_activation(self):
        """Test that tokens become invalid after user is activated"""
        token = email_verification_token.make_token(self.user)
        
        # Token valid before activation
        self.assertTrue(email_verification_token.check_token(self.user, token))
        
        # Activate user
        self.user.is_active = True
        self.user.save()
        
        # Token invalid after activation
        self.assertFalse(email_verification_token.check_token(self.user, token))


class UserRegistrationTests(APITestCase):
    """Test user registration with email verification"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
    
    @patch('users.views.send_verification_email')
    def test_registration_creates_inactive_user(self, mock_send_email):
        """Test that registration creates user with is_active=False"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'account_type': 'trader'
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check user was created
        user = User.objects.get(email='newuser@example.com')
        self.assertIsNotNone(user)
        
        # Check user is inactive
        self.assertFalse(user.is_active)
        
        # Check verification email was sent
        mock_send_email.assert_called_once_with(user)
    
    @patch('users.views.send_verification_email')
    def test_registration_returns_generic_message(self, mock_send_email):
        """Test that registration returns generic success message"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'account_type': 'trader'
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('If an account exists', response.data['detail'])
        self.assertEqual(response.data['redirect_to'], '/verify-notice')
    
    @patch('users.views.send_verification_email', side_effect=EmailServiceError("Test error"))
    def test_registration_succeeds_even_if_email_fails(self, mock_send_email):
        """Test that registration succeeds even if email sending fails"""
        data = {
            'username': 'testuser2',
            'email': 'test2@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'account_type': 'trader'
        }
        
        response = self.client.post(self.register_url, data)
        
        # Registration should still succeed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # User should be created
        user = User.objects.get(email='test2@example.com')
        self.assertFalse(user.is_active)


class EmailVerificationTests(APITestCase):
    """Test email verification endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.verify_url = '/api/auth/verify/'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.is_active = False
        self.user.save()
    
    def test_verification_success(self):
        """Test successful email verification"""
        # Generate valid token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = email_verification_token.make_token(self.user)
        
        data = {
            'uid': uid,
            'token': token
        }
        
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('verified successfully', response.data['detail'])
        
        # Check user is now active
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
    
    def test_verification_invalid_token(self):
        """Test verification with invalid token"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        data = {
            'uid': uid,
            'token': 'invalid-token'
        }
        
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invalid or expired', response.data['detail'].lower())
        
        # User should still be inactive
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_verification_invalid_uid(self):
        """Test verification with invalid uid"""
        token = email_verification_token.make_token(self.user)
        
        data = {
            'uid': 'invalid-uid',
            'token': token
        }
        
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verification_already_active_user(self):
        """Test verification for already active user"""
        # Activate user
        self.user.is_active = True
        self.user.save()
        
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = email_verification_token.make_token(self.user)
        
        data = {
            'uid': uid,
            'token': token
        }
        
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('already verified', response.data['detail'].lower())
    
    def test_verification_missing_parameters(self):
        """Test verification with missing uid or token"""
        # Missing token
        response = self.client.post(self.verify_url, {'uid': 'test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing uid
        response = self.client.post(self.verify_url, {'token': 'test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResendVerificationTests(APITestCase):
    """Test resend verification endpoint with cooldown"""
    
    def setUp(self):
        self.client = APIClient()
        self.resend_url = '/api/auth/resend-verification/'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.is_active = False
        self.user.save()
        
        # Clear cache before each test
        cache.clear()
    
    @patch('users.views.send_resend_verification_email')
    def test_resend_success(self, mock_send_email):
        """Test successful resend verification"""
        data = {'email': 'test@example.com'}
        
        response = self.client.post(self.resend_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('If an account exists', response.data['detail'])
        
        # Check email was sent
        mock_send_email.assert_called_once_with(self.user)
    
    @patch('users.views.send_resend_verification_email')
    def test_resend_cooldown(self, mock_send_email):
        """Test that resend has 60 second cooldown"""
        data = {'email': 'test@example.com'}
        
        # First request
        response1 = self.client.post(self.resend_url, data)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_send_email.call_count, 1)
        
        # Second request immediately (should be blocked by cooldown)
        response2 = self.client.post(self.resend_url, data)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        # Email should NOT be sent again
        self.assertEqual(mock_send_email.call_count, 1)
    
    @patch('users.views.send_resend_verification_email')
    def test_resend_for_active_user(self, mock_send_email):
        """Test that resend doesn't send email for already active users"""
        # Activate user
        self.user.is_active = True
        self.user.save()
        
        data = {'email': 'test@example.com'}
        
        response = self.client.post(self.resend_url, data)
        
        # Same generic response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # But email should NOT be sent
        mock_send_email.assert_not_called()
    
    @patch('users.views.send_resend_verification_email')
    def test_resend_for_nonexistent_user(self, mock_send_email):
        """Test that resend returns generic response for non-existent users"""
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(self.resend_url, data)
        
        # Same generic response (anti-enumeration)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('If an account exists', response.data['detail'])
        
        # Email should NOT be sent
        mock_send_email.assert_not_called()
    
    def test_resend_missing_email(self):
        """Test that resend requires email parameter"""
        response = self.client.post(self.resend_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('required', response.data['detail'].lower())


class LoginWithVerificationTests(APITestCase):
    """Test that login checks email verification"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/auth/login/'
        
        self.active_user = User.objects.create_user(
            username='activeuser',
            email='active@example.com',
            password='testpass123'
        )
        self.active_user.is_active = True
        self.active_user.save()
        
        self.inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='testpass123'
        )
        self.inactive_user.is_active = False
        self.inactive_user.save()
    
    def test_login_success_with_verified_email(self):
        """Test that verified users can log in"""
        data = {
            'email': 'active@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
    
    def test_login_blocked_for_unverified_email(self):
        """Test that unverified users cannot log in"""
        data = {
            'email': 'inactive@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('not verified', response.data['detail'].lower())
        self.assertEqual(response.data['error_code'], 'EMAIL_NOT_VERIFIED')


class AntiEnumerationTests(APITestCase):
    """Test anti-enumeration security features"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )
        self.existing_user.is_active = False
        self.existing_user.save()
    
    @patch('users.views.send_resend_verification_email')
    def test_resend_same_response_for_existing_and_nonexistent(self, mock_send):
        """Test that resend returns same response regardless of user existence"""
        # Request for existing user
        response1 = self.client.post(
            '/api/auth/resend-verification/',
            {'email': 'existing@example.com'}
        )
        
        # Request for non-existent user
        response2 = self.client.post(
            '/api/auth/resend-verification/',
            {'email': 'nonexistent@example.com'}
        )
        
        # Both should return same response
        self.assertEqual(response1.status_code, response2.status_code)
        self.assertEqual(response1.data['detail'], response2.data['detail'])


# Run tests with: python manage.py test users.tests.EmailVerificationTests
