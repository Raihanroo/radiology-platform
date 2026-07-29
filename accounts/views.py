from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    যে কেউ এখানে account বানাতে পারবে -- কিন্তু সবসময় role='patient' হবে
    (RegisterSerializer.create() দেখুন)।
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  -> নিজের প্রোফাইল দেখা
    PATCH/PUT /api/auth/profile/ -> নিজের প্রোফাইল আপডেট করা (role বাদে)
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    ডিফল্ট simplejwt login-এর বদলে এটা ব্যবহার করলে response-এ
    user-এর id/username/role ও পাওয়া যাবে।
    """

    serializer_class = CustomTokenObtainPairSerializer
