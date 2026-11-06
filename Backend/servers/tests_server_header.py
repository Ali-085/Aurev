"""
Test Suite for Server Public Profile Header

Tests all components of the server header redesign:
- Logo upload and validation
- Market categories validation
- Dashboard endpoint response
- Serializer computed fields
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image
from io import BytesIO
import json

from servers.models import Server
from analytics.models import ServerRanking
from platform_admin.models import MarketCategory

User = get_user_model()


class ServerHeaderTestCase(TestCase):
    """Test server public profile header components."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123',
            email_verified=True
        )
        
        # Create market categories
        self.futures_cat = MarketCategory.objects.create(
            name='Futures',
            is_active=True,
            display_order=1
        )
        self.forex_cat = MarketCategory.objects.create(
            name='Forex',
            is_active=True,
            display_order=2
        )
        self.inactive_cat = MarketCategory.objects.create(
            name='Inactive',
            is_active=False,
            display_order=3
        )
        
        # Create test server
        self.server = Server.objects.create(
            owner_user=self.user,
            name='Test Trading Server',
            description='Test server description',
            platform='Discord',
            invite_link='https://discord.gg/test',
            market_categories=['Futures', 'Forex'],
            is_verified=True
        )
        
        # Create server ranking
        self.ranking = ServerRanking.objects.create(
            server=self.server,
            global_rank=42,
            monthly_rank=15,
            weekly_rank=8
        )
    
    def create_test_image(self, size=(512, 512), format='PNG'):
        """Create a test image file."""
        image = Image.new('RGB', size, color='red')
        image_io = BytesIO()
        image.save(image_io, format=format)
        image_io.seek(0)
        return SimpleUploadedFile(
            name=f'test_logo.{format.lower()}',
            content=image_io.read(),
            content_type=f'image/{format.lower()}'
        )
    
    def test_dashboard_includes_header_fields(self):
        """Test that dashboard endpoint includes all header fields."""
        response = self.client.get(
            f'/api/servers/public/{self.server.id}/dashboard/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check server section
        self.assertIn('server', data)
        server_data = data['server']
        
        # Verify all header fields present
        self.assertEqual(server_data['name'], 'Test Trading Server')
        self.assertEqual(server_data['description'], 'Test server description')
        self.assertEqual(server_data['platform'], 'Discord')
        self.assertIn('logo_url', server_data)
        self.assertEqual(server_data['market_categories'], ['Futures', 'Forex'])
        self.assertEqual(server_data['is_verified'], True)
        self.assertIn('created_at', server_data)
        
        # Check rankings section
        self.assertIn('rankings', data)
        rankings_data = data['rankings']
        self.assertEqual(rankings_data['global_rank'], 42)
        self.assertEqual(rankings_data['monthly_rank'], 15)
        self.assertEqual(rankings_data['weekly_rank'], 8)
    
    def test_logo_url_returns_none_when_no_logo(self):
        """Test that logo_url is null when server has no logo."""
        response = self.client.get(
            f'/api/servers/public/{self.server.id}/dashboard/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['server']['logo_url'])
    
    def test_global_rank_returns_none_when_no_ranking(self):
        """Test that global_rank is null for unranked servers."""
        # Create server without ranking
        unranked_server = Server.objects.create(
            owner_user=self.user,
            name='Unranked Server',
            description='No ranking yet',
            platform='Discord',
            invite_link='https://discord.gg/unranked'
        )
        
        response = self.client.get(
            f'/api/servers/public/{unranked_server.id}/dashboard/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['rankings']['global_rank'])
    
    @override_settings(MEDIA_ROOT='/tmp/test_media/')
    def test_create_server_with_valid_logo(self):
        """Test server creation with valid logo upload."""
        self.client.force_authenticate(user=self.user)
        
        logo_file = self.create_test_image(size=(512, 512), format='PNG')
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Server with logo',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'logo': logo_file,
                'market_categories': json.dumps(['Futures'])
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNotNone(data['logo'])
        self.assertIn('logo_url', data)
        self.assertIsNotNone(data['logo_url'])
    
    @override_settings(MEDIA_ROOT='/tmp/test_media/')
    def test_logo_validation_rejects_oversized_image(self):
        """Test that oversized logos are rejected."""
        self.client.force_authenticate(user=self.user)
        
        # Create 2000x2000 image (exceeds 1024px limit)
        logo_file = self.create_test_image(size=(2000, 2000), format='PNG')
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Server with oversized logo',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'logo': logo_file
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('logo', response.json())
    
    @override_settings(MEDIA_ROOT='/tmp/test_media/')
    def test_logo_validation_rejects_undersized_image(self):
        """Test that undersized logos are rejected."""
        self.client.force_authenticate(user=self.user)
        
        # Create 50x50 image (below 64px minimum)
        logo_file = self.create_test_image(size=(50, 50), format='PNG')
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Server with undersized logo',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'logo': logo_file
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('logo', response.json())
    
    def test_market_categories_validation_accepts_valid_categories(self):
        """Test that valid market categories are accepted."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Valid categories',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'market_categories': json.dumps(['Futures', 'Forex'])
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(set(data['market_categories']), {'Futures', 'Forex'})
    
    def test_market_categories_validation_rejects_invalid_categories(self):
        """Test that invalid market categories are rejected."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Invalid categories',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'market_categories': json.dumps(['Stocks', 'Options'])
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('market_categories', response.json())
        error_message = response.json()['market_categories'][0]
        self.assertIn('Invalid market categories', error_message)
        self.assertIn('Stocks', error_message)
        self.assertIn('Options', error_message)
    
    def test_market_categories_validation_rejects_inactive_categories(self):
        """Test that inactive market categories are rejected."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'Inactive category',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'market_categories': json.dumps(['Inactive'])
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('market_categories', response.json())
        error_message = response.json()['market_categories'][0]
        self.assertIn('Invalid market categories', error_message)
        self.assertIn('Inactive', error_message)
    
    def test_market_categories_accepts_empty_list(self):
        """Test that empty market_categories list is accepted."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/servers/',
            {
                'name': 'New Server',
                'description': 'No categories',
                'platform': 'Discord',
                'invite_link': 'https://discord.gg/newserver',
                'market_categories': json.dumps([])
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['market_categories'], [])
    
    def test_server_serializer_includes_logo_url(self):
        """Test that ServerSerializer includes logo_url field."""
        from servers.serializers import ServerSerializer
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.get('/')
        
        serializer = ServerSerializer(
            self.server,
            context={'request': request}
        )
        
        self.assertIn('logo_url', serializer.data)
        self.assertIn('global_rank', serializer.data)
        self.assertEqual(serializer.data['global_rank'], 42)
    
    def test_server_serializer_includes_market_categories(self):
        """Test that ServerSerializer includes market_categories."""
        from servers.serializers import ServerSerializer
        
        serializer = ServerSerializer(self.server)
        
        self.assertIn('market_categories', serializer.data)
        self.assertEqual(
            set(serializer.data['market_categories']),
            {'Futures', 'Forex'}
        )
    
    def test_verified_badge_field_present(self):
        """Test that is_verified field is included in response."""
        response = self.client.get(
            f'/api/servers/public/{self.server.id}/dashboard/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('is_verified', data['server'])
        self.assertTrue(data['server']['is_verified'])
    
    def test_established_date_field_present(self):
        """Test that created_at field is included in response."""
        response = self.client.get(
            f'/api/servers/public/{self.server.id}/dashboard/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('created_at', data['server'])
        self.assertIsNotNone(data['server']['created_at'])
        # Verify it's in ISO format
        from datetime import datetime
        datetime.fromisoformat(data['server']['created_at'].replace('Z', '+00:00'))


class ImageUploadSecurityTestCase(TestCase):
    """Test security features of logo upload."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            email_verified=True
        )
    
    def test_validate_server_logo_function_exists(self):
        """Test that validate_server_logo function exists and is callable."""
        from utils.image_upload import validate_server_logo
        self.assertTrue(callable(validate_server_logo))
    
    def test_validate_server_logo_with_valid_image(self):
        """Test validate_server_logo with valid image."""
        from utils.image_upload import validate_server_logo
        
        # Create valid image
        image = Image.new('RGB', (512, 512), color='blue')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_io.seek(0)
        
        uploaded_file = SimpleUploadedFile(
            name='test.png',
            content=image_io.read(),
            content_type='image/png'
        )
        
        # Should not raise exception
        result = validate_server_logo(uploaded_file)
        self.assertIsNotNone(result)
    
    def test_secure_image_uploader_logo_type(self):
        """Test that SecureImageUploader handles 'logo' type correctly."""
        from utils.image_upload import SecureImageUploader
        
        uploader = SecureImageUploader(upload_type='logo')
        
        # Verify logo limits
        self.assertEqual(uploader.max_size, 2 * 1024 * 1024)  # 2MB
        self.assertEqual(uploader.max_dimension, 1024)
        self.assertEqual(uploader.min_dimension, 64)
