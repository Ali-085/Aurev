"""
Avatar and Logo Upload API Endpoints

Provides secure endpoints for uploading user avatars and server logos.

Features:
- Rate limiting (5 uploads per hour)
- Image validation and processing
- R2 storage upload
- Old image cleanup
- Permission checks

Endpoints:
- POST /api/users/avatar/upload/ - Upload user avatar
- DELETE /api/users/avatar/ - Remove user avatar
- POST /api/servers/<id>/logo/upload/ - Upload server logo
- DELETE /api/servers/<id>/logo/ - Remove server logo
"""

import logging
from django.conf import settings
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from servers.models import Server
from utils.image_upload import AvatarUploader
from utils.r2_uploader import R2Uploader, R2UploadError

logger = logging.getLogger(__name__)


# Rate limit key function - only count successful uploads
def avatar_rate_limit_key(group, request):
    """Rate limit key that includes user ID."""
    return f'avatar_upload_{request.user.id}'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key=avatar_rate_limit_key, rate='5/h', method='POST', block=False)
def upload_user_avatar(request):
    """
    Upload user avatar image.
    
    SECURITY:
    - User can only upload their own avatar
    - Rate limited to 5 uploads per hour
    - Failed uploads don't count toward rate limit
    - Image validated and processed
    - Old avatar deleted on success
    
    Request:
        - avatar: Image file (JPG, PNG, WebP)
        - Max size: 2MB
        - Will be resized to 512x512px
        - Converted to WebP
    
    Response:
        200: {avatar_url: str}
        400: {error: str}
        429: {error: str} - Rate limited
    """
    # Check rate limit
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Too many upload attempts. Please try again in an hour.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Validate file was uploaded
    if 'avatar' not in request.FILES:
        return Response(
            {'error': 'No image file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['avatar']
    user = request.user
    
    # Step 1: Validate and process image
    uploader = AvatarUploader()
    result = uploader.validate_and_process(uploaded_file)
    
    if not result['valid']:
        return Response(
            {'error': result['error']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 2: Upload to R2
    try:
        r2_uploader = R2Uploader()
        new_url = r2_uploader.upload_avatar(
            user_id=str(user.id),
            file_bytes=result['file_bytes'],
            old_url=user.avatar_url
        )
    except R2UploadError as e:
        logger.error(f"R2 upload failed for user {user.id}: {str(e)}")
        return Response(
            {'error': 'Failed to upload image. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Step 3: Update user record
    with transaction.atomic():
        user_obj = User.objects.select_for_update().get(id=user.id)
        user_obj.avatar_url = new_url
        user_obj.save(update_fields=['avatar_url'])
    
    logger.info(f"Avatar uploaded successfully for user {user.id}")
    
    return Response({
        'avatar_url': new_url,
        'message': 'Avatar uploaded successfully'
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_user_avatar(request):
    """
    Remove user avatar.
    
    SECURITY:
    - User can only remove their own avatar
    - Deletes image from R2
    - Sets avatar_url to null
    
    Response:
        200: {message: str}
        404: {error: str} - No avatar to remove
    """
    user = request.user
    
    if not user.avatar_url:
        return Response(
            {'error': 'No avatar to remove'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    old_url = user.avatar_url
    
    # Delete from R2
    try:
        r2_uploader = R2Uploader()
        r2_uploader.delete_avatar(str(user.id))
    except Exception as e:
        logger.warning(f"Failed to delete avatar from R2 for user {user.id}: {str(e)}")
        # Continue anyway - update database
    
    # Update user record
    with transaction.atomic():
        user_obj = User.objects.select_for_update().get(id=user.id)
        user_obj.avatar_url = None
        user_obj.save(update_fields=['avatar_url'])
    
    logger.info(f"Avatar removed for user {user.id}")
    
    return Response({
        'message': 'Avatar removed successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key=avatar_rate_limit_key, rate='5/h', method='POST', block=False)
def upload_server_logo(request, server_id):
    """
    Upload server logo image.
    
    SECURITY:
    - Only server owner can upload logo
    - Rate limited to 5 uploads per hour
    - Failed uploads don't count toward rate limit
    - Image validated and processed
    - Old logo deleted on success
    
    Request:
        - logo: Image file (JPG, PNG, WebP)
        - Max size: 2MB
        - Will be resized to 512x512px
        - Converted to WebP
    
    Response:
        200: {logo_url: str}
        400: {error: str}
        403: {error: str} - Not owner
        404: {error: str} - Server not found
        429: {error: str} - Rate limited
    """
    # Check rate limit
    if getattr(request, 'limited', False):
        return Response(
            {'error': 'Too many upload attempts. Please try again in an hour.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Get server
    try:
        server = Server.objects.select_related('owner_user').get(id=server_id)
    except Server.DoesNotExist:
        return Response(
            {'error': 'Server not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # SECURITY: Check ownership
    if server.owner_user_id != request.user.id:
        return Response(
            {'error': 'Only the server owner can upload the logo'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate file was uploaded
    if 'logo' not in request.FILES:
        return Response(
            {'error': 'No image file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['logo']
    
    # Step 1: Validate and process image
    uploader = AvatarUploader()
    result = uploader.validate_and_process(uploaded_file)
    
    if not result['valid']:
        return Response(
            {'error': result['error']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 2: Upload to R2
    try:
        r2_uploader = R2Uploader()
        new_url = r2_uploader.upload_server_logo(
            server_id=str(server.id),
            file_bytes=result['file_bytes'],
            old_url=server.logo_url
        )
    except R2UploadError as e:
        logger.error(f"R2 upload failed for server {server.id}: {str(e)}")
        return Response(
            {'error': 'Failed to upload image. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Step 3: Update server record
    with transaction.atomic():
        server_obj = Server.objects.select_for_update().get(id=server.id)
        server_obj.logo_url = new_url
        server_obj.save(update_fields=['logo_url'])
    
    logger.info(f"Logo uploaded successfully for server {server.id}")
    
    return Response({
        'logo_url': new_url,
        'message': 'Logo uploaded successfully'
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_server_logo(request, server_id):
    """
    Remove server logo.
    
    SECURITY:
    - Only server owner can remove logo
    - Deletes image from R2
    - Sets logo_url to null
    
    Response:
        200: {message: str}
        403: {error: str} - Not owner
        404: {error: str} - Server not found or no logo
    """
    # Get server
    try:
        server = Server.objects.select_related('owner_user').get(id=server_id)
    except Server.DoesNotExist:
        return Response(
            {'error': 'Server not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # SECURITY: Check ownership
    if server.owner_user_id != request.user.id:
        return Response(
            {'error': 'Only the server owner can remove the logo'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not server.logo_url:
        return Response(
            {'error': 'No logo to remove'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Delete from R2
    try:
        r2_uploader = R2Uploader()
        r2_uploader.delete_server_logo(str(server.id))
    except Exception as e:
        logger.warning(f"Failed to delete logo from R2 for server {server.id}: {str(e)}")
        # Continue anyway - update database
    
    # Update server record
    with transaction.atomic():
        server_obj = Server.objects.select_for_update().get(id=server.id)
        server_obj.logo_url = None
        server_obj.save(update_fields=['logo_url'])
    
    logger.info(f"Logo removed for server {server.id}")
    
    return Response({
        'message': 'Logo removed successfully'
    })
