from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    """শুধু 'patient' role-এর ইউজার access পাবে।"""

    message = "শুধু patient অ্যাকাউন্ট দিয়ে এই action করা যাবে।"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "patient"
        )


class IsRadiologist(BasePermission):
    """শুধু 'radiologist' role-এর ইউজার access পাবে।"""

    message = "শুধু radiologist অ্যাকাউন্ট দিয়ে এই action করা যাবে।"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "radiologist"
        )


class IsDoctor(BasePermission):
    """শুধু 'doctor' role-এর ইউজার access পাবে।"""

    message = "শুধু doctor অ্যাকাউন্ট দিয়ে এই action করা যাবে।"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
        )


class IsAdminRole(BasePermission):
    """'admin' বা 'super_admin' role-এর ইউজার access পাবে।"""

    message = "শুধু admin/super_admin অ্যাকাউন্ট দিয়ে এই action করা যাবে।"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "super_admin")
        )


class IsRadiologistOrDoctor(BasePermission):
    """Radiologist অথবা Doctor -- দুজনেই review-related কাজ করতে পারবে।"""

    message = "শুধু radiologist বা doctor অ্যাকাউন্ট দিয়ে এই action করা যাবে।"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("radiologist", "doctor")
        )
