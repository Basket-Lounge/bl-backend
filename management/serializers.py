from rest_framework import serializers

from api.mixins import DynamicFieldsSerializerMixin
from management.models import Inquiry, InquiryMessage, InquiryModerator, InquiryModeratorMessage, InquiryType, InquiryTypeDisplayName
from teams.serializers import LanguageSerializer
from users.serializers import UserSerializer


class InquiryCreateSerializer(serializers.Serializer):
    inquiry_type = serializers.IntegerField()
    title = serializers.CharField(min_length=1, max_length=512)
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
            obj.inquirymoderatormessage_set, 
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_last_message(self, obj):
        if not hasattr(obj, 'inquirymoderatormessage_set'):
            return None
        
        context = self.context.get('inquirymoderatormessage_extra', {})
        serializer = InquiryModeratorMessageSerializer(
            obj.inquirymoderatormessage_set.last(), 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_unread_messages_count(self, obj):
        if not hasattr(obj, 'inquirymoderatormessage_set'):
            return None
        
        context = self.context.get('inquirymoderatormessage_extra', {})
        user = context.get('user_last_read_at', None)
        if not user:
            return None

        id = user.get('id', None)
        if not id:
            return None

        count = 0
        if obj.moderator.id != id:
            last_read_at = user.get('last_read_at', None)
            for message in obj.inquirymoderatormessage_set.all():
                if message.created_at > last_read_at:
                    count += 1

        return count
        

class InquiryMessageSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    inquiry_data = serializers.SerializerMethodField()

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
            obj.inquirymoderator_set, 
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_messages(self, obj):
        if not hasattr(obj, 'inquirymessage_set'):
            return None
        
        context = self.context.get('inquirymessage', {})
        serializer = InquiryMessageSerializer(
            obj.inquirymessage_set,
            many=True, 
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_last_message(self, obj):
        if not hasattr(obj, 'inquirymessage_set'):
            return None
        
        context = self.context.get('inquirymessage', {})
        serializer = InquiryMessageSerializer(
            obj.inquirymessage_set.last(),
            context=self.context,
            **context
        )
        return serializer.data
    
    def get_unread_messages_count(self, obj):
        if not hasattr(obj, 'inquirymessage_set'):
            return None
        
        context = self.context.get('inquirymessage_extra', {})
        user = context.get('user_last_read_at', None)
        if not user:
            return None
        
        id = user.get('id', None)
        if not id:
            return None
        
        count = 0
        if obj.user.id != id:
            last_read_at = user.get('last_read_at', None)
            for message in obj.inquirymessage_set.all():
                if message.created_at > last_read_at:
                    count += 1

        return count
