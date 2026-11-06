"""
Celery Tasks for Image Upload Cleanup

Periodic tasks to clean up temporary and orphaned images.
"""

from celery import shared_task
from django.utils import timezone
from django.core.files.storage import default_storage
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_temp_uploads():
    """
    Clean up temporary uploads older than 24 hours.
    
    Temporary uploads are stored when users upload screenshots
    but haven't completed their payout submission yet.
    
    Schedule: Run daily at 3 AM
    """
    temp_dir = 'payouts/temp/'
    cutoff_time = timezone.now() - timedelta(hours=24)
    deleted_count = 0
    error_count = 0
    
    logger.info(f"Starting cleanup of temp uploads older than {cutoff_time}")
    
    try:
        # List files in temp directory
        directories, files = default_storage.listdir(temp_dir)
        
        for file_name in files:
            file_path = f'{temp_dir}{file_name}'
            
            try:
                # Get file modified time
                modified_time = default_storage.get_modified_time(file_path)
                
                if modified_time < cutoff_time:
                    # Delete old file
                    default_storage.delete(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted temp file: {file_path}")
                    
            except Exception as e:
                error_count += 1
                logger.warning(f"Error deleting temp file {file_path}: {str(e)}")
        
        logger.info(
            f"Temp uploads cleanup complete. "
            f"Deleted: {deleted_count}, Errors: {error_count}"
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup temp uploads: {str(e)}")
        raise
    
    return {
        'deleted_count': deleted_count,
        'error_count': error_count
    }


@shared_task
def cleanup_orphaned_images():
    """
    Clean up images not referenced in database.
    
    This finds images in storage that are not referenced by any
    PayoutSubmission records.
    
    Schedule: Run weekly on Sunday at 4 AM
    
    Note: Be careful with this task. Only run if you're confident
    your database is the source of truth.
    """
    from payouts.models import PayoutSubmission
    
    
    logger.info("Starting cleanup of orphaned images")
    
    deleted_count = 0
    error_count = 0
    
    # Clean up orphaned payout screenshots
    try:
        payout_dir = 'payouts/'
        directories, files = default_storage.listdir(payout_dir)
        
        # Get all screenshot filenames from database
        db_screenshots = set(
            PayoutSubmission.objects
            .filter(screenshot__isnull=False)
            .values_list('screenshot', flat=True)
        )
        
        # Extract just filenames
        db_filenames = set()
        for screenshot_path in db_screenshots:
            if screenshot_path:
                # Extract filename from path (e.g., 'payouts/2024/01/abc123.jpg' -> 'abc123.jpg')
                filename = screenshot_path.split('/')[-1]
                db_filenames.add(filename)
        
        # Check each file in storage
        for year_dir in directories:
            if year_dir == 'temp':
                continue  # Skip temp directory (handled by cleanup_temp_uploads)
            
            year_path = f'{payout_dir}{year_dir}/'
            
            try:
                month_dirs, year_files = default_storage.listdir(year_path)
                
                for month_dir in month_dirs:
                    month_path = f'{year_path}{month_dir}/'
                    
                    try:
                        _, month_files = default_storage.listdir(month_path)
                        
                        for file_name in month_files:
                            if file_name not in db_filenames:
                                # Orphaned file - not in database
                                file_path = f'{month_path}{file_name}'
                                
                                try:
                                    default_storage.delete(file_path)
                                    deleted_count += 1
                                    logger.debug(f"Deleted orphaned payout screenshot: {file_path}")
                                except Exception as e:
                                    error_count += 1
                                    logger.warning(f"Error deleting {file_path}: {str(e)}")
                    
                    except Exception as e:
                        logger.warning(f"Error processing month directory {month_path}: {str(e)}")
                        
            except Exception as e:
                logger.warning(f"Error processing year directory {year_path}: {str(e)}")
        
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned payout screenshots: {str(e)}")
    
    logger.info(
        f"Orphaned images cleanup complete. "
        f"Deleted: {deleted_count}, Errors: {error_count}"
    )
    
    return {
        'deleted_count': deleted_count,
        'error_count': error_count
    }


@shared_task
def generate_image_thumbnails():
    """
    Generate thumbnails for uploaded images.
    
    Optional: Generate smaller versions of images for faster loading.
    
    This could be expanded to create:
    - Thumbnails (150x150px)
    - Medium (512x512px)
    - Large (1024x1024px)
    """
    # Implementation placeholder
    # Use PIL to resize images and save to different directories
    pass


@shared_task
def monitor_storage_usage():
    """
    Monitor storage usage and send alerts if approaching limits.
    
    Useful for preventing storage exhaustion.
    """
    from django.core.mail import mail_admins
    
    try:
        # Get storage statistics
        # Implementation depends on storage backend (S3, local, etc.)
        
        # Example for local storage:
        import os
        from django.conf import settings
        
        if hasattr(settings, 'MEDIA_ROOT'):
            media_root = settings.MEDIA_ROOT
            
            # Calculate directory size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(media_root):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            
            # Convert to GB
            total_gb = total_size / (1024 ** 3)
            
            # Alert if over 80% of 100GB limit
            if total_gb > 80:
                mail_admins(
                    'Storage Usage Alert',
                    f'Media storage is at {total_gb:.2f}GB. Consider cleanup or expansion.',
                    fail_silently=True
                )
                logger.warning(f"High storage usage: {total_gb:.2f}GB")
            
            logger.info(f"Storage usage: {total_gb:.2f}GB")
            
            return {'storage_gb': total_gb}
        
    except Exception as e:
        logger.error(f"Failed to monitor storage usage: {str(e)}")
        raise
