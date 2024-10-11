from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class PasswordMixin(serializers.ModelSerializer):

    def validate_password(self, value):
        user = self.instance if self.instance else None
        validate_password(value, user)
        return value


class PasswordChangeMixin(serializers.Serializer):

    def validate_new_password(self, value):
        user = self.context['request'].user
        validate_password(value, user)
        return value

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверен.')
        return value
