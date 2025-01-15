from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from management.models import (
    Inquiry, 
    InquiryMessage, 
    InquiryModerator, 
    InquiryModeratorMessage, 
    InquiryType, 
    InquiryTypeDisplayName, 
    Report, 
    ReportType, 
    ReportTypeDisplayName
)
from teams.serializers import LanguageSerializer
from users.models import Role
from users.serializers import UserSerializer

from django.contrib.auth import get_user_model


class InquiryCreateSerializer(serializers.Serializer):
    inquiry_type = serializers.IntegerField()
    title = serializers.CharField(min_length=8, max_length=512)
    message = serializers.CharField(min_length=1, max_length=4096)

    def create(self, validated_data):
        if not validated_data.get('user', None):
            raise serializers.ValidationError('User is required')
        
        inquiry_type = InquiryType.objects.filter(id=validated_data['inquiry_type']).first()
        if not inquiry_type:
            raise serializers.ValidationError('Invalid inquiry type')
        
        inquiry = Inquiry.objects.create(
            user=validated_data['user'],
            inquiry_type=inquiry_type,
            title=validated_data['title'],
        )

        InquiryMessage.objects.create(
            inquiry=inquiry,
            message=validated_data['message'],
        )

        return inquiry
    
class InquiryUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=1, max_length=512)
    inquiry_type = serializers.IntegerField()
    solved = serializers.BooleanField()

    def update(self, instance, validated_data):
        title = validated_data.get('title', None)
        inquiry_type = validated_data.get('inquiry_type', None)
        solved = validated_data.get('solved', None)

        if isinstance(title, str):
            instance.title = title
        if isinstance(inquiry_type, int):
            inquiry_type = InquiryType.objects.filter(id=validated_data['inquiry_type']).first()
            if not inquiry_type:
                raise serializers.ValidationError('Invalid inquiry type')
            instance.inquiry_type = inquiry_type 
        if isinstance(solved, bool):
            instance.solved = solved

        instance.save()
        return instance


class InquiryMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=4096)

    def create(self, validated_data):
        inquiry = Inquiry.objects.filter(id=validated_data['inquiry']).first()
        if not inquiry:
            raise serializers.ValidationError('Invalid inquiry')
        
        message = InquiryMessage.objects.create(
            inquiry=inquiry,
            message=validated_data['message'],
        )

        inquiry.save()

        return message


class InquiryTypeDisplayNameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_type_data = serializers.SerializerMethodField()
    language_data = serializers.SerializerMethodField()

    class Meta:
        model = InquiryTypeDisplayName
        exclude = ('inquiry_type', 'language')

    def get_inquiry_type_data(self, obj):
        if not hasattr(obj, 'inquiry_type'):
            return None
        
        context = self.context.get('inquiry_type', {})
        serializer = InquiryTypeSerializer(
            obj.inquiry_type, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_language_data(self, obj):
        if not hasattr(obj, 'language'):
            return None
        
        context = self.context.get('language', {})
        serializer = LanguageSerializer(
            obj.language, 
            context=self.context,
            **context    
        )
        return serializer.data


class InquiryTypeSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    display_names = serializers.SerializerMethodField()

    class Meta:
        model = InquiryType
        fields = '__all__'

    def get_display_names(self, obj):
        if not hasattr(obj, 'inquirytypedisplayname_set'):
            return None
        
        context = self.context.get('inquirytypedisplayname', {})
        serializer = InquiryTypeDisplayNameSerializer(
            obj.inquirytypedisplayname_set, 
            many=True, 
            context=self.context,
            **context
        )

        return serializer.data

class InquiryModeratorMessageSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_moderator_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()

    class Meta:
        model = InquiryModeratorMessage
        exclude = ('inquiry_moderator',)

    def get_inquiry_moderator_data(self, obj):
        if not hasattr(obj, 'inquiry_moderator'):
            return None
        
        context = self.context.get('inquirymoderator', {})
        serializer = InquiryModeratorSerializer(
            obj.inquiry_moderator, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'inquiry_moderator') or not hasattr(obj.inquiry_moderator, 'moderator'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.inquiry_moderator.moderator, 
            context=self.context,
            **context    
        )
        return serializer.data


class InquiryModeratorMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1)

    def create(self, validated_data):
        inquiry_moderator = validated_data.get('inquiry_moderator', None)
        if not inquiry_moderator:
            raise serializers.ValidationError('Invalid inquiry moderator')
        
        message = InquiryModeratorMessage.objects.create(
            inquiry_moderator=inquiry_moderator,
            message=validated_data['message'],
        )

        return message


class InquiryModeratorSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_data = serializers.SerializerMethodField()
    moderator_data = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = InquiryModerator
        exclude = ('inquiry', 'moderator')

    def get_inquiry_data(self, obj):
        if not hasattr(obj, 'inquiry'):
            return None
        
        context = self.context.get('inquiry', {})
        serializer = InquirySerializer(
            obj.inquiry, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_moderator_data(self, obj):
        if not hasattr(obj, 'moderator'):
            return None
        
        context = self.context.get('moderator', {})
        serializer = UserSerializer(
            obj.moderator, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_messages(self, obj):
        if not hasattr(obj, 'inquirymoderatormessage_set'):
            return None
        
        context = self.context.get('inquirymoderatormessage', {})
        serializer = InquiryModeratorMessageSerializer(
            obj.inquirymoderatormessage_set.all()[:50],
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_last_message(self, obj):
        if not hasattr(obj, 'inquirymoderatormessage_set'):
            return None
        
        messages = obj.inquirymoderatormessage_set.all()
        if not messages:
            return None
        
        context = self.context.get('inquirymoderatormessage', {})
        serializer = InquiryModeratorMessageSerializer(
            obj.inquirymoderatormessage_set.all()[0],
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_unread_messages_count(self, obj):
        if not hasattr(obj, 'inquirymoderatormessage_set'):
            return None
        
        context = self.context.get('inquirymoderatormessage_extra', {})
        user_last_read_at = context.get('user_last_read_at', None)
        if not user_last_read_at:
            return None

        inquiry_id = obj.inquiry.id 
        if not user_last_read_at.get(inquiry_id, None):
            return None
        
        user_last_read_at = user_last_read_at[inquiry_id]
        count = 0
        if obj.moderator.id != user_last_read_at['id']:
            last_read_at = user_last_read_at.get('last_read_at', None)
            for message in obj.inquirymoderatormessage_set.all():
                if message.created_at > last_read_at:
                    count += 1
                else:
                    break

        return count


class InquiryMessageSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()

    class Meta:
        model = InquiryMessage
        exclude = ('inquiry',)

    def get_inquiry_data(self, obj):
        if not hasattr(obj, 'inquiry'):
            return None
        
        context = self.context.get('inquiry', {})
        serializer = InquirySerializer(
            obj.inquiry, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_user_data(self, obj):
        if not hasattr(obj, 'inquiry') or not hasattr(obj.inquiry, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.inquiry.user, 
            context=self.context,
            **context    
        )
        return serializer.data
    

class InquirySerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_type_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    moderators = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        exclude = ('inquiry_type', 'user')

    def get_inquiry_type_data(self, obj):
        if not hasattr(obj, 'inquiry_type'):
            return None
        
        context = self.context.get('inquiry_type', {})
        serializer = InquiryTypeSerializer(
            obj.inquiry_type, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_user_data(self, obj):
        if not hasattr(obj, 'user'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.user, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_moderators(self, obj):
        if not hasattr(obj, 'inquirymoderator_set'):
            return None
        
        context = self.context.get('inquirymoderator', {})
        serializer = InquiryModeratorSerializer(
            obj.inquirymoderator_set.all(),
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_messages(self, obj):
        if not hasattr(obj, 'messages'):
            return None
        
        context = self.context.get('inquirymessage', {})
        serializer = InquiryMessageSerializer(
            obj.messages.all()[:50],
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_last_message(self, obj):
        if not hasattr(obj, 'messages'):
            return None
        
        messages = obj.messages.all()
        if not messages:
            return None
        
        context = self.context.get('inquirymessage', {})
        serializer = InquiryMessageSerializer(
            messages[0],
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_unread_messages_count(self, obj):
        if not hasattr(obj, 'messages'):
            return None
        
        context = self.context.get('inquirymessage_extra', {})
        user_last_read_at = context.get('user_last_read_at', None)
        if not user_last_read_at:
            return None
        
        if not user_last_read_at.get('id', None):
            user_last_read_at = user_last_read_at.get(obj.id, None)
            if not user_last_read_at:
                return None

        count = 0
        if obj.user.id != user_last_read_at['id']:
            last_read_at = user_last_read_at.get('last_read_at', None)
            for message in obj.messages.all():
                if message.created_at > last_read_at:
                    count += 1

        return count
    
class InquiryCommonMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    message = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    user_type = serializers.CharField()
    user_id = serializers.IntegerField()
    user_username = serializers.CharField()
    

class ReportTypeSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    display_names = serializers.SerializerMethodField()

    class Meta:
        model = ReportType
        fields = '__all__'

    def get_display_names(self, obj):
        if not hasattr(obj, 'reporttypedisplayname_set'):
            return None
        
        context = self.context.get('reporttypedisplayname', {})
        serializer = ReportTypeDisplayNameSerializer(
            obj.reporttypedisplayname_set, 
            many=True, 
            context=self.context,
            **context
        )

        return serializer.data


class ReportTypeDisplayNameSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    report_type_data = serializers.SerializerMethodField()
    language_data = serializers.SerializerMethodField()

    class Meta:
        model = ReportTypeDisplayName
        exclude = ('report_type', 'language')

    def get_report_type_data(self, obj):
        if not hasattr(obj, 'report_type'):
            return None
        
        context = self.context.get('report_type', {})
        serializer = ReportTypeSerializer(
            obj.report_type, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_language_data(self, obj):
        if not hasattr(obj, 'language'):
            return None
        
        context = self.context.get('language', {})
        serializer = LanguageSerializer(
            obj.language, 
            context=self.context,
            **context    
        )
        return serializer.data


class ReportSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    type_data = serializers.SerializerMethodField()
    accused_data = serializers.SerializerMethodField()
    accuser_data = serializers.SerializerMethodField()

    class Meta:
        model = Report
        exclude = ('type', 'accused', 'accuser')

    def get_type_data(self, obj):
        if not hasattr(obj, 'type'):
            return None
        
        context = self.context.get('reporttype', {})
        serializer = ReportTypeSerializer(
            obj.type, 
            context=self.context,
            **context    
        )
        return serializer.data

    def get_accused_data(self, obj):
        if not hasattr(obj, 'accused'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.accused, 
            context=self.context,
            **context    
        )
        return serializer.data
    
    def get_accuser_data(self, obj):
        if not hasattr(obj, 'accuser'):
            return None
        
        context = self.context.get('user', {})
        serializer = UserSerializer(
            obj.accuser, 
            context=self.context,
            **context    
        )
        return serializer.data


class ReportCreateSerializer(serializers.Serializer):
    report_type = serializers.IntegerField()
    title = serializers.CharField(min_length=1, max_length=512)
    description = serializers.CharField(min_length=1, max_length=4096)

    def create(self, validated_data):
        accuser = validated_data.get('accuser', None)
        if not accuser:
            raise serializers.ValidationError('Accuser is required')
        
        report_type = ReportType.objects.filter(id=validated_data['report_type']).first()
        if not report_type:
            raise serializers.ValidationError('Invalid report type')

        accused = validated_data.get('accused', None) 
        if not accused:
            raise serializers.ValidationError('Invalid accused')
        
        report = Report.objects.create(
            accuser=accuser,
            type=report_type,
            accused=accused,
            title=validated_data['title'],
            description=validated_data['description'],
        )

        return report
    

class ReportUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=1, max_length=512)
    description = serializers.CharField(min_length=1, max_length=4096)
    report_type = serializers.IntegerField()
    solved = serializers.BooleanField()

    def update(self, instance, validated_data):
        title = validated_data.get('title', None)
        description = validated_data.get('description', None)
        report_type = validated_data.get('report_type', None)
        solved = validated_data.get('solved', None)

        if isinstance(title, str):
            instance.title = validated_data['title']
        if isinstance(description, str):
            instance.description = validated_data['description']
        if isinstance(report_type, int):
            report_type = ReportType.objects.filter(id=validated_data['report_type']).first()
            if not report_type:
                raise serializers.ValidationError('Invalid report type')
            instance.report_type = report_type
        if isinstance(solved, bool):
            instance.solved = validated_data['solved']

        instance.save()

class UserUpdateSerializer(serializers.Serializer):
    introduction = serializers.CharField(min_length=1)
    is_profile_visible = serializers.BooleanField()
    chat_blocked = serializers.BooleanField()
    role = serializers.IntegerField()
    username = serializers.CharField(min_length=1, max_length=128)

    def update(self, instance, validated_data):
        introduction = validated_data.get('introduction', None)
        is_profile_visible = validated_data.get('is_profile_visible', None)
        chat_blocked = validated_data.get('chat_blocked', None)
        role = validated_data.get('role', None)
        username = validated_data.get('username', None)

        if introduction:
            stripped_introduction = introduction.strip()
            if not stripped_introduction:
                raise serializers.ValidationError('Introduction cannot be empty')

            instance.introduction = stripped_introduction

        if is_profile_visible is not None:
            instance.is_profile_visible = is_profile_visible

        if chat_blocked is not None:
            instance.chat_blocked = chat_blocked

        if username:
            User = get_user_model()
            stripped_username = username.strip()
            if not stripped_username:
                raise serializers.ValidationError('Username cannot be empty')

            if instance.username != stripped_username:
                if User.objects.filter(username=stripped_username).exists():
                    raise serializers.ValidationError('Username already exists')

            instance.username = username

        if role:
            role_obj = Role.objects.filter(id=role).first()
            if role_obj:
                if role_obj.weight <= 2:
                    raise serializers.ValidationError('Cannot assign admin role to user')

                instance.role = role_obj
            
        instance.save()
        return instance