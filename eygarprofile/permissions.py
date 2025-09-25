from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'eygar_host'):
            return obj.eygar_host.user == request.user
        
        return False


class IsAdminOrModerator(permissions.BasePermission):
    """
    Custom permission for admin and moderator users.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.is_superuser or 
             hasattr(request.user, 'is_moderator') and request.user.is_moderator)
        )


class IsEygarHostOwner(permissions.BasePermission):
    """
    Permission to check if user owns the host profile.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanAccessEygarHostStep(permissions.BasePermission):
    """
    Permission to check if user can access specific host profile step.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            from .models import EygarHost
            profile = EygarHost.objects.get(user=request.user)
            
            # Get the step from the view action
            step = getattr(view, 'action', None)
            if step:
                return profile.can_proceed_to_step(step)
            
            return True
        except EygarHost.DoesNotExist:
            # If no profile exists, user can create one
            return True


class IsVerified(permissions.BasePermission):
    """
    Permission to check if eygar host is verified/approved.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            from .models import EygarHost
            profile = EygarHost.objects.get(user=request.user)
            return profile.status == 'approved'
        except EygarHost.DoesNotExist:
            return False