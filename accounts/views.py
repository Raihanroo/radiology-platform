from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
)

from rest_framework import generics
from .permissions import IsAdminRole
from .serializers import AdminUserSerializer


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


class AdminUserListView(generics.ListCreateAPIView):
    """
    GET /api/auth/users/ -> অ্যাডমিন সব ইউজারের লিস্ট দেখবে।
    POST /api/auth/users/ -> অ্যাডমিন নতুন ডাক্তার/রেডিওলজিস্ট অ্যাকাউন্ট তৈরি করবে।
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/auth/users/<id>/ -> নির্দিষ্ট ইউজারের ডিটেইলস দেখা।
    PATCH /api/auth/users/<id>/ -> ইউজারের রোল পরিবর্তন বা ডিঅ্যাক্টিভেট (is_active=False) করা।
    DELETE /api/auth/users/<id>/ -> ইউজার ডিলিট করা।
    """

    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]


