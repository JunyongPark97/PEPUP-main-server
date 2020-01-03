from rest_framework import permissions


class IsOwnerByToken(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        print(obj.key)
        print(request.headers['Authorization'])
        print(obj.key == request.headers['Authorization'].split(' ')[1])
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.key == request.headers['Authorization'].split(' ')[1]