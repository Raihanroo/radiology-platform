from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public registration serializer.

    গুরুত্বপূর্ণ: এখান দিয়ে শুধু 'patient' role-এর অ্যাকাউন্ট তৈরি করা যাবে।
    Radiologist/Doctor/Admin অ্যাকাউন্ট ইচ্ছাকৃতভাবেই এখানে বানানো যাবে না —
    এগুলো Django admin থেকে বা future invite-system দিয়ে তৈরি করতে হবে।
    এটা privilege escalation ঠেকানোর জন্য (কেউ নিজেকে 'doctor' বানিয়ে ফেলতে না পারে)।
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "phone_number",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "দুটো পাসওয়ার্ড মিলছে না।"}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        # role সবসময় 'patient' -- serializer fields-এ role নেই, তাই client পাঠাতে পারবে না
        user = User(role="patient", **validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    নিজের প্রোফাইল দেখা/আপডেট করার জন্য।
    role read-only রাখা হয়েছে -- ইউজার নিজে নিজের role বদলাতে পারবে না।
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "role", "date_joined"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    ডিফল্ট JWT login response-এ শুধু access/refresh token থাকে।
    এখানে user-এর id, username, role যোগ করা হয়েছে -- যাতে frontend
    login করার সাথে সাথেই জানতে পারে কোন dashboard-এ পাঠাতে হবে
    (patient / radiologist / doctor / admin)।
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "role": self.user.role,
        }
        return data