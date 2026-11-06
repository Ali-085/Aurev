"""
Secure Image Upload Utility

Provides comprehensive validation and processing for image uploads:
- File type validation (extension + magic bytes)
- Size and dimension limits
- EXIF stripping (privacy + security)
- Re-encoding (removes embedded malicious code)
- Filename sanitization

Security measures:
1. Magic byte validation prevents extension spoofing
2. PIL verification detects corrupted/malicious images
3. Re-encoding strips any embedded scripts
4. Random UUID filenames prevent path traversal
5. EXIF removal protects user privacy and removes potential exploits
"""

import os
import uuid
import magic
from PIL import Image
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile


class SecureImageUploader:
    """
    Secure image upload handler with comprehensive validation.
    
    Security Features:
    - File type validation (extension + magic bytes)
    - File size limits
    - Image dimension limits
    - EXIF stripping
    - Re-encoding (removes malicious code)
    - Filename sanitization
    
    Usage:
        uploader = SecureImageUploader(upload_type='payout')
        processed_file = uploader.validate_and_process(uploaded_file)
    """
    
    ALLOWED_FORMATS = {
        'JPEG': ['image/jpeg', ['.jpg', '.jpeg']],
        'PNG': ['image/png', ['.png']],
        'WEBP': ['image/webp', ['.webp']],
    }
    
    def __init__(self, upload_type='payout'):
        """
        Initialize uploader with specific constraints.
        
        Args:
            upload_type (str): Type of upload - 'payout', 'logo', 'banner', or 'background'
        """
        self.upload_type = upload_type
        self.set_limits()
    
    def set_limits(self):
        """Set size and dimension limits based on upload type."""
        limits = {
            'payout': {
                'max_size': 10 * 1024 * 1024,  # 10MB
                'max_dimension': 4096,
                'min_dimension': 100,
            },
            'logo': {
                'max_size': 2 * 1024 * 1024,  # 2MB
                'max_dimension': 1024,
                'min_dimension': 64,
            },
            'banner': {
                'max_size': 5 * 1024 * 1024,  # 5MB
                'max_dimension': 2560,
                'min_dimension': 400,
            },
            'background': {
                'max_size': 5 * 1024 * 1024,  # 5MB
                'max_dimension': 2560,
                'min_dimension': 800,
            },
        }
        
        config = limits.get(self.upload_type, limits['payout'])
        self.max_size = config['max_size']
        self.max_dimension = config['max_dimension']
        self.min_dimension = config['min_dimension']
    
    def validate_and_process(self, uploaded_file):
        """
        Validate and process uploaded image through security pipeline.
        
        Security Pipeline:
        1. File size validation
        2. Extension whitelist check
        3. Magic byte verification (prevents spoofing)
        4. PIL image structure validation
        5. Dimension validation
        6. Aspect ratio validation (prevents exploits)
        7. EXIF stripping
        8. Re-encoding (removes embedded code)
        9. Secure filename generation
        
        Args:
            uploaded_file: Django UploadedFile object
        
        Returns:
            InMemoryUploadedFile: Processed and sanitized image
        
        Raises:
            ValidationError: If any validation step fails
        """
        # SECURITY: Step 1 - Validate file size
        self._validate_file_size(uploaded_file)
        
        # SECURITY: Step 2 - Validate file extension (basic check)
        self._validate_extension(uploaded_file.name)
        
        # SECURITY: Step 3 - Validate magic bytes (prevents extension spoofing)
        self._validate_magic_bytes(uploaded_file)
        
        # SECURITY: Step 4 - Validate image structure and dimensions
        image = self._validate_image_structure(uploaded_file)
        
        # SECURITY: Step 5 - Strip EXIF and re-encode (removes malicious code)
        processed_file = self._strip_and_reencode(image, uploaded_file)
        
        return processed_file
    
    def _validate_file_size(self, uploaded_file):
        """
        Validate file size is within acceptable limits.
        
        Prevents:
        - DoS attacks via huge file uploads
        - Storage exhaustion
        - Memory exhaustion during processing
        """
        if uploaded_file.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f'File too large. Maximum size: {max_mb}MB'
            )
        
        if uploaded_file.size < 1024:  # 1KB minimum
            raise ValidationError('File too small. Minimum size: 1KB')
    
    def _validate_extension(self, filename):
        """
        Validate file extension against whitelist.
        
        Note: This is a basic check. Extension can be spoofed.
        Magic byte validation (_validate_magic_bytes) is the real security check.
        """
        ext = os.path.splitext(filename)[1].lower()
        
        allowed_exts = []
        for format_info in self.ALLOWED_FORMATS.values():
            allowed_exts.extend(format_info[1])
        
        if ext not in allowed_exts:
            raise ValidationError(
                f'Invalid file extension. Allowed: {", ".join(allowed_exts)}'
            )
    
    def _validate_magic_bytes(self, uploaded_file):
        """
        Validate file type using magic bytes (file signature).
        
        SECURITY: This prevents extension spoofing attacks where
        a malicious file (e.g., .exe) is renamed to .jpg
        
        Magic bytes are the first few bytes of a file that identify
        the file format. For example:
        - JPEG: FF D8 FF
        - PNG: 89 50 4E 47
        - WebP: 52 49 46 46
        """
        # Read first 2048 bytes for magic number detection
        uploaded_file.seek(0)
        file_header = uploaded_file.read(2048)
        uploaded_file.seek(0)
        
        # Detect MIME type from file content (not extension)
        mime_type = magic.from_buffer(file_header, mime=True)
        
        # Check if MIME type is in our whitelist
        allowed_mimes = []
        for format_info in self.ALLOWED_FORMATS.values():
            allowed_mimes.append(format_info[0])
        
        if mime_type not in allowed_mimes:
            raise ValidationError(
                f'Invalid file type detected: {mime_type}. '
                f'Allowed types: {", ".join(allowed_mimes)}'
            )
    
    def _validate_image_structure(self, uploaded_file):
        """
        Validate image can be opened and check dimensions.
        
        SECURITY: This detects:
        - Corrupted images that could crash PIL
        - Malicious images with exploit payloads
        - Images with extreme dimensions (potential exploits)
        
        PIL.Image.verify() checks the image is valid without
        loading the full image into memory.
        """
        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image.verify()  # Verify image integrity without decoding
            
            # Re-open after verify (verify closes the file)
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            
        except Exception as e:
            raise ValidationError(f'Invalid or corrupted image: {str(e)}')
        
        # Check dimensions
        width, height = image.size
        
        if width > self.max_dimension or height > self.max_dimension:
            raise ValidationError(
                f'Image too large. Maximum dimension: {self.max_dimension}px. '
                f'Your image: {width}x{height}px'
            )
        
        if width < self.min_dimension or height < self.min_dimension:
            raise ValidationError(
                f'Image too small. Minimum dimension: {self.min_dimension}px. '
                f'Your image: {width}x{height}px'
            )
        
        # SECURITY: Reject images with unusual aspect ratios
        # Extremely wide/tall images can be used in exploits
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 10:  # More than 10:1 ratio
            raise ValidationError(
                'Invalid aspect ratio. Image dimensions are too extreme.'
            )
        
        return image
    
    def _strip_and_reencode(self, image, original_file):
        """
        Strip EXIF data and re-encode image.
        
        SECURITY: This removes:
        - EXIF data (privacy: GPS coordinates, camera info, timestamps)
        - Embedded scripts or payloads
        - Malicious metadata
        
        Re-encoding creates a clean image from scratch, removing
        any hidden data or exploits in the original file.
        """
        # Determine format
        format_name = image.format
        if format_name not in ['JPEG', 'PNG', 'WEBP']:
            format_name = 'JPEG'  # Default to JPEG
        
        # SECURITY: Convert to RGB if necessary
        # JPEG doesn't support transparency, so we need to flatten the image
        if format_name == 'JPEG' and image.mode in ('RGBA', 'P', 'LA'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            # Paste image onto white background
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        
        # Save to BytesIO with optimization
        output = BytesIO()
        
        save_kwargs = {
            'format': format_name,
            'optimize': True,  # Optimize file size
            'quality': 90 if format_name == 'JPEG' else None,  # Good quality
        }
        
        # Remove None values
        save_kwargs = {k: v for k, v in save_kwargs.items() if v is not None}
        
        # SECURITY: Save without EXIF data (default behavior)
        image.save(output, **save_kwargs)
        output.seek(0)
        
        # SECURITY: Generate random UUID filename (prevents path traversal)
        ext = self._get_extension_for_format(format_name)
        filename = f'{uuid.uuid4().hex}{ext}'
        
        # Create new InMemoryUploadedFile
        processed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            filename,
            f'image/{format_name.lower()}',
            output.getbuffer().nbytes,
            None
        )
        
        return processed_file
    
    def _get_extension_for_format(self, format_name):
        """Get file extension for PIL format."""
        extensions = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBP': '.webp',
        }
        return extensions.get(format_name, '.jpg')


# Convenience functions for each upload type

def validate_payout_screenshot(uploaded_file):
    """
    Validate payout screenshot upload.
    
    Limits:
    - Max size: 10MB
    - Max dimension: 4096px
    - Min dimension: 100px
    
    Args:
        uploaded_file: Django UploadedFile
    
    Returns:
        InMemoryUploadedFile: Processed image
    
    Raises:
        ValidationError: If validation fails
    """
    uploader = SecureImageUploader(upload_type='payout')
    return uploader.validate_and_process(uploaded_file)


def validate_server_logo(uploaded_file):
    """
    Validate server logo upload.
    
    Limits:
    - Max size: 2MB
    - Max dimension: 1024px
    - Min dimension: 64px
    
    Args:
        uploaded_file: Django UploadedFile
    
    Returns:
        InMemoryUploadedFile: Processed image
    
    Raises:
        ValidationError: If validation fails
    """
    uploader = SecureImageUploader(upload_type='logo')
    return uploader.validate_and_process(uploaded_file)


class AvatarUploader:
    """
    Specialized uploader for user/server avatars with WebP conversion.
    
    Features:
    - 2MB max file size
    - Resize to 512x512px (square, centered crop)
    - Convert to WebP format
    - Strip EXIF metadata
    - Magic byte validation
    """
    
    MAX_SIZE_MB = 2
    TARGET_SIZE = (512, 512)
    WEBP_QUALITY = 85
    
    ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def validate_and_process(self, uploaded_file):
        """
        Validate and process avatar upload.
        
        Returns dict with:
            - valid: bool
            - error: str (if invalid)
            - file_bytes: BytesIO (if valid)
            - size_bytes: int (if valid)
        """
        try:
            # Step 1: Validate file size
            max_bytes = self.MAX_SIZE_MB * 1024 * 1024
            if uploaded_file.size > max_bytes:
                return {
                    'valid': False,
                    'error': f'File too large. Maximum size is {self.MAX_SIZE_MB}MB'
                }
            
            # Step 2: Validate extension
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                return {
                    'valid': False,
                    'error': f'Invalid file extension. Allowed: JPG, PNG, WebP'
                }
            
            # Step 3: Validate magic bytes
            uploaded_file.seek(0)
            file_header = uploaded_file.read(2048)
            uploaded_file.seek(0)
            
            mime_type = magic.from_buffer(file_header, mime=True)
            if mime_type not in self.ALLOWED_MIME_TYPES:
                return {
                    'valid': False,
                    'error': f'Invalid file type. Detected: {mime_type}'
                }
            
            # Step 4: Open and validate image
            image = Image.open(uploaded_file)
            image.verify()
            
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            
            # Step 5: Validate dimensions (min 50x50px, max 4000x4000px)
            width, height = image.size
            if width < 50 or height < 50:
                return {
                    'valid': False,
                    'error': 'Image too small. Minimum size: 50x50px'
                }
            
            if width > 4000 or height > 4000:
                return {
                    'valid': False,
                    'error': 'Image too large. Maximum size: 4000x4000px'
                }
            
            # Step 6: Process image
            processed_bytes = self._process_image(image)
            
            return {
                'valid': True,
                'error': None,
                'file_bytes': processed_bytes,
                'size_bytes': processed_bytes.getbuffer().nbytes
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Failed to process image: {str(e)}'
            }
    
    def _process_image(self, image):
        """
        Process image: strip EXIF, resize to 512x512, convert to WebP.
        """
        from PIL import ImageOps
        
        # Convert to RGB (strips EXIF, handles transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize to 512x512 (square crop, centered)
        image = ImageOps.fit(
            image,
            self.TARGET_SIZE,
            Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )
        
        # Convert to WebP
        output = BytesIO()
        image.save(
            output,
            format='WEBP',
            quality=self.WEBP_QUALITY,
            method=6  # Best compression
        )
        output.seek(0)
        
        return output
