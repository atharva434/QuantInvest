from django.shortcuts import redirect
from functools import wraps

def block_admins(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/client_login')
        if request.user.is_staff or request.user.is_superuser:
            return redirect('/client_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view