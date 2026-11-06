from django.apps import AppConfig
import os
import sys

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Only run during server startup, not during migrations or other management commands
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
            
        if os.environ.get("CREATE_SUPERUSER") != "true":
            return

        from django.contrib.auth import get_user_model
        import logging

        User = get_user_model()
        logger = logging.getLogger(__name__)

        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            logger.warning("⚠️ CREATE_SUPERUSER=true but missing DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD")
            return

        try:
            # Check if user exists
            user = User.objects.filter(email=email).first()
            
            if user:
                # Fix existing user - ensure all superuser flags are set
                updated = False
                if not user.is_superuser:
                    user.is_superuser = True
                    updated = True
                if not user.is_active:
                    user.is_active = True
                    updated = True
                if not user.email_verified:
                    user.email_verified = True
                    updated = True
                
                if updated:
                    user.save(update_fields=['is_superuser', 'is_active', 'email_verified'])
                    logger.info(f"✅ Superuser flags fixed for {email}")
                    logger.info(f"   is_superuser={user.is_superuser}, is_active={user.is_active}, email_verified={user.email_verified}")
                else:
                    logger.info(f"✅ Superuser {email} already properly configured")
            else:
                # Create new superuser using create_superuser (ensures all flags are set correctly)
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                logger.info(f"✅ Superuser created: {email}")
                logger.info(f"   is_superuser={user.is_superuser}, is_active={user.is_active}, email_verified={user.email_verified}")
                
        except Exception as e:
            logger.error(f"❌ Superuser setup error: {str(e)}", exc_info=True)
