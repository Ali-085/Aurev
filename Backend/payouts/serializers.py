from rest_framework import serializers
from .models import PayoutSubmission, PayoutSubmissionDetail, PayoutReviewLog
from .prop_firms import PropFirm
from users.serializers import UserSerializer
from servers.serializers import ServerSerializer

# SECURITY NOTE:
# - PublicPayoutSubmissionSerializer: For regular users (NO review fields)
# - PayoutSubmissionSerializer: For Admin/Moderator (includes reviewer, reviewed_at)


class PropFirmSerializer(serializers.ModelSerializer):
    """Serializer for PropFirm model."""
    
    class Meta:
        model = PropFirm
        fields = ['id', 'name', 'slug', 'logo_url', 'website_url']
        read_only_fields = ['id', 'slug']


class PayoutSubmissionDetailSerializer(serializers.ModelSerializer):
    """Serializer for PayoutSubmissionDetail model."""
    
    class Meta:
        model = PayoutSubmissionDetail
        fields = [
            'id', 'auto_detected_time', 'duplicate_flag',
            'risk_score', 'metadata'
        ]
        read_only_fields = ['id']


class PublicPayoutSubmissionSerializer(serializers.ModelSerializer):
    """SECURITY: Serializer for regular users - NO review fields exposed."""
    
    user = UserSerializer(read_only=True)
    server = ServerSerializer(read_only=True)
    prop_firm = PropFirmSerializer(read_only=True)
    details = PayoutSubmissionDetailSerializer(read_only=True)
    
    class Meta:
        model = PayoutSubmission
        fields = [
            'id', 'server', 'user', 'prop_firm', 'amount', 'currency',
            'market_category', 'instrument', 'screenshot',
            'payout_date', 'status', 'created_at', 'details'
        ]
        read_only_fields = [
            'id', 'status', 'created_at'
        ]


class PayoutSubmissionSerializer(serializers.ModelSerializer):
    """SECURITY: Admin/Moderator serializer with review fields - PROTECTED."""
    
    user = UserSerializer(read_only=True)
    server = ServerSerializer(read_only=True)
    prop_firm = PropFirmSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True)
    details = PayoutSubmissionDetailSerializer(read_only=True)
    has_private_verification_image = serializers.SerializerMethodField()
    
    class Meta:
        model = PayoutSubmission
        fields = [
            'id', 'server', 'user', 'prop_firm', 'amount', 'currency',
            'market_category', 'instrument', 'screenshot',
            'payout_date', 'status', 'reviewer', 'reviewed_at',
            'created_at', 'details', 'has_private_verification_image',
            'discord_contact_info'
        ]
        read_only_fields = [
            'id', 'status', 'reviewer', 'reviewed_at', 'created_at'
        ]
    
    def get_has_private_verification_image(self, obj):
        """SECURITY: Return boolean flag only - never expose direct URL."""
        return bool(obj.private_verification_image)


class PayoutSubmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payout submissions with secure image upload."""
    
    server_id = serializers.UUIDField(write_only=True)
    prop_firm_id = serializers.IntegerField(write_only=True)
    screenshot = serializers.ImageField(write_only=True, required=True)
    private_verification_image = serializers.ImageField(write_only=True, required=True)
    
    class Meta:
        model = PayoutSubmission
        fields = [
            'server_id', 'prop_firm_id', 'amount', 'currency', 'market_category',
            'instrument', 'screenshot', 'private_verification_image', 'payout_date',
            'discord_contact_info'
        ]
    
    def validate_screenshot(self, value):
        """
        SECURITY: Validate screenshot image through comprehensive security pipeline.
        
        This integrates the SecureImageUploader which provides:
        - File type validation (extension + magic bytes)
        - Size limits (enforced from PlatformLimits)
        - Dimension validation (100px - 4096px)
        - EXIF stripping (removes GPS, metadata)
        - Re-encoding (removes malicious code)
        - Secure filename generation (UUID)
        """
        from utils.image_upload import validate_payout_screenshot
        from platform_admin.enforcement import LimitsEnforcer
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        if not value:
            raise serializers.ValidationError("Screenshot is required")
        
        try:
            # Enforce platform file size and format limits
            LimitsEnforcer.validate_file_upload(value)
            
            # SECURITY: Process through comprehensive validation pipeline
            processed_image = validate_payout_screenshot(value)
            return processed_image
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Image validation failed: {str(e)}")
    
    def validate_private_verification_image(self, value):
        """
        SECURITY: Validate required private verification image.
        
        Uses same security pipeline as screenshot.
        This image is NEVER publicly accessible - only served to admin/moderator/superuser.
        """
        from utils.image_upload import validate_payout_screenshot
        from platform_admin.enforcement import LimitsEnforcer
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        if not value:
            raise serializers.ValidationError("Private verification image is required")
        
        try:
            # Enforce platform file size and format limits
            LimitsEnforcer.validate_file_upload(value)
            
            # SECURITY: Process through comprehensive validation pipeline
            processed_image = validate_payout_screenshot(value)
            return processed_image
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Image validation failed: {str(e)}")
    
    def validate_amount(self, value):
        """
        SECURITY: Validate payout amount against platform limits.
        """
        from platform_admin.enforcement import LimitsEnforcer
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        
        # Enforce platform max_payout_amount limit
        try:
            LimitsEnforcer.validate_payout_amount(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        return value
    
    def validate_market_category(self, value):
        """
        SECURITY: Validate market category against active database entries.
        Platform owner controls which markets are available.
        """
        from platform_admin.models import MarketCategory
        
        if not value or not value.strip():
            raise serializers.ValidationError("Market category is required")
        
        value = str(value).strip()
        
        # Check if market exists and is active
        if not MarketCategory.objects.filter(name=value, is_active=True).exists():
            active_markets = list(MarketCategory.objects.filter(is_active=True).values_list('name', flat=True))
            raise serializers.ValidationError(
                f"Invalid market category. Must be one of: {', '.join(active_markets)}"
            )
        
        return value
    
    def validate_instrument(self, value):
        """
        SECURITY: Sanitize instrument name to prevent XSS.
        """
        import re
        
        value = str(value).strip()
        
        # Only allow alphanumeric, spaces, and common trading symbols
        if not re.match(r'^[A-Za-z0-9\s/\-_.]+$', value):
            raise serializers.ValidationError("Invalid instrument format. Only alphanumeric and /-_. allowed")
        
        if len(value) > 100:
            raise serializers.ValidationError("Instrument name too long (max 100 characters)")
        
        return value
    
    def validate_discord_contact_info(self, value):
        """
        SECURITY: Validate and sanitize Discord contact info to prevent XSS.
        """
        import re
        import bleach
        
        if not value or not value.strip():
            raise serializers.ValidationError("Discord username/contact info is required")
        
        value = str(value).strip()
        
        # SECURITY: Strip HTML tags first
        value = bleach.clean(value, tags=[], strip=True)
        
        # Allow Discord username format: username#1234 or just username
        # Also allow common contact formats like email, phone, etc.
        # Pattern allows alphanumeric, spaces, dots, underscores, hashes, @, and common symbols
        if not re.match(r'^[A-Za-z0-9\s@._\-#]+$', value):
            raise serializers.ValidationError(
                "Invalid format. Only letters, numbers, spaces, and @._-# allowed"
            )
        
        if len(value) > 100:
            raise serializers.ValidationError("Discord contact info too long (max 100 characters)")
        
        return value
        """
        SECURITY: Validate payout date.
        """
        from datetime import date, timedelta
        
        if not value:
            raise serializers.ValidationError("Payout date is required")
        
        # SECURITY: Prevent future dates
        if value > date.today():
            raise serializers.ValidationError("Payout date cannot be in the future")
        
        # SECURITY: Prevent very old dates (adjust based on business logic)
        if value < date.today() - timedelta(days=365*2):  # 2 years
            raise serializers.ValidationError("Payout date too old (max 2 years back)")
        
        return value
    
    def validate_prop_firm_id(self, value):
        """Validate that prop firm exists and is active."""
        try:
            prop_firm = PropFirm.objects.get(id=value, is_active=True)
        except PropFirm.DoesNotExist:
            active_firms = PropFirm.objects.filter(is_active=True).values_list('name', flat=True)
            raise serializers.ValidationError(
                f"Invalid prop firm. Must be one of: {', '.join(active_firms)}"
            )
        return value
    
    def create(self, validated_data):
        from servers.models import Server, ServerMember
        from django.db import transaction
        from platform_admin.enforcement import enforce_payout_limits, LimitsEnforcer
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        user = self.context['request'].user
        server_id = validated_data.pop('server_id')
        prop_firm_id = validated_data.pop('prop_firm_id')
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            try:
                server = Server.objects.select_for_update().get(id=server_id)
            except Server.DoesNotExist:
                raise serializers.ValidationError({'server_id': 'Server not found'})
            
            # SECURITY: Verify user is server owner OR member
            is_owner = server.owner_user == user
            is_member = ServerMember.objects.filter(server=server, user=user).exists()
            
            if not (is_owner or is_member):
                raise serializers.ValidationError({
                    'server_id': 'You must be a member or owner of this server to submit payouts'
                })
            
            try:
                prop_firm = PropFirm.objects.get(id=prop_firm_id, is_active=True)
            except PropFirm.DoesNotExist:
                raise serializers.ValidationError({'prop_firm_id': 'Prop firm not found or inactive'})
            
            # SECURITY: Check if server is suspended or paused
            if server.suspended:
                raise serializers.ValidationError({'server_id': 'Server is suspended. Cannot submit payouts.'})
            
            if server.payout_submissions_paused:
                raise serializers.ValidationError({'server_id': 'Payout submissions are paused for this server.'})
            
            # ENFORCE PLATFORM LIMITS: Check all daily limits and quotas
            try:
                LimitsEnforcer.validate_daily_user_submissions(user)
                LimitsEnforcer.validate_daily_server_submissions(server)
                LimitsEnforcer.check_maintenance_mode()
            except DjangoValidationError as e:
                raise serializers.ValidationError({'non_field_errors': str(e)})
            
            # SECURITY: Check for duplicate payout submission
            # Prevent trader from resubmitting same payout across multiple servers
            duplicate_check = PayoutSubmission.objects.filter(
                user=user,
                amount=validated_data['amount'],
                market_category=validated_data['market_category'],
                prop_firm=prop_firm,
                instrument=validated_data['instrument'],
                payout_date=validated_data['payout_date']
            ).exists()
            
            if duplicate_check:
                raise serializers.ValidationError({
                    'non_field_errors': (
                        'This payout has already been submitted. '
                        'You cannot submit the same payout (same amount, market, prop firm, instrument, and date) '
                        'to multiple servers or resubmit it again.'
                    )
                })
            
            # SECURITY: Use transaction to ensure payout and details are created together
            with transaction.atomic():
                # Create payout submission
                payout = PayoutSubmission.objects.create(
                    server=server,
                    user=user,
                    prop_firm=prop_firm,
                    status='Pending',
                    **validated_data
                )
        
                # Create details record atomically
                PayoutSubmissionDetail.objects.create(payout_submission=payout)
        
        return payout


class PayoutReviewLogSerializer(serializers.ModelSerializer):
    """Serializer for PayoutReviewLog model."""
    
    reviewer_user = UserSerializer(read_only=True)
    
    class Meta:
        model = PayoutReviewLog
        fields = [
            'id', 'payout_submission', 'reviewer_user',
            'action', 'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PayoutReviewSerializer(serializers.Serializer):
    """Serializer for reviewing payout submissions."""
    
    action = serializers.ChoiceField(choices=['Approved', 'Rejected', 'MarkedSuspicious'])
    reason = serializers.CharField(max_length=500)
    
    def validate_reason(self, value):
        """
        SECURITY: Sanitize reason to prevent XSS attacks.
        """
        import bleach
        
        if not value or not value.strip():
            raise serializers.ValidationError("Reason cannot be empty")
        
        # SECURITY: Strip HTML tags and limit length
        value = bleach.clean(str(value).strip(), tags=[], strip=True)
        
        if len(value) > 500:
            raise serializers.ValidationError("Reason too long (max 500 characters)")
        
        return value
