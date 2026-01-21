from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect, get_object_or_404


# ✅ Only allow superusers
def superuser_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_superuser, login_url='adminpanel_login')(view_func)
    return decorated_view_func


def admin_login(request):
    """Custom login for superuser/admin only."""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Access denied. Only system administrators can log in.')

    # ✅ Correct template reference
    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    """Logout the admin and redirect to login."""
    logout(request)
    return redirect('adminpanel_login')


@superuser_required
def dashboard(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@superuser_required
def manage_users(request):
    users = User.objects.all().order_by('username')
    return render(request, 'admin_panel/manage_users.html', {'users': users})

# -- Manage users list --
@superuser_required
def manage_users(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.all().order_by('username')
    if query:
        users = users.filter(username__icontains=query) | users.filter(email__icontains=query)
    return render(request, 'admin_panel/manage_users.html', {'users': users, 'query': query})

# -- Add user --
@superuser_required
def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        is_staff = True if request.POST.get('is_staff') == 'on' else False
        is_active = True if request.POST.get('is_active') == 'on' else True

        # basic validation
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('add_user')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('add_user')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_staff = is_staff
        user.is_active = is_active
        user.save()
        messages.success(request, f"User '{username}' created successfully.")
        return redirect('manage_users')

    return render(request, 'admin_panel/add_user.html')


# -- Edit user --
@superuser_required
def edit_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        is_staff = True if request.POST.get('is_staff') == 'on' else False
        is_active = True if request.POST.get('is_active') == 'on' else True

        user.email = email
        user.is_staff = is_staff
        user.is_active = is_active
        user.save()
        messages.success(request, f"User '{user.username}' updated.")
        return redirect('manage_users')

    return render(request, 'admin_panel/edit_user.html', {'user': user})


# -- Delete user --
@superuser_required
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    username = user.username
    if request.method == 'POST':
        user.delete()
        messages.success(request, f"User '{username}' deleted.")
        return redirect('manage_users')

    # confirm page (simple)
    return render(request, 'admin_panel/confirm_delete.html', {'user': user})


# -- Reset password --
@superuser_required
def reset_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        new_password2 = request.POST.get('new_password2', '').strip()
        if not new_password:
            messages.error(request, "Password cannot be empty.")
            return redirect('reset_password', user_id=user_id)
        if new_password != new_password2:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password', user_id=user_id)

        user.set_password(new_password)
        user.save()
        messages.success(request, f"Password updated for {user.username}.")
        return redirect('manage_users')

    return render(request, 'admin_panel/reset_password.html', {'user': user})

@login_required(login_url='adminpanel_login')
@user_passes_test(lambda u: u.is_superuser)
def add_user(request):
    """Create a new user"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, 'User added successfully.')
            return redirect('manage_users')

    return render(request, 'admin_panel/add_user.html')


@login_required(login_url='adminpanel_login')
@user_passes_test(lambda u: u.is_superuser)
def edit_user(request, user_id):
    """Edit user details"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.is_active = 'is_active' in request.POST
        user.save()
        messages.success(request, 'User updated successfully.')
        return redirect('manage_users')

    return render(request, 'admin_panel/edit_user.html', {'user': user})


@login_required(login_url='adminpanel_login')
@user_passes_test(lambda u: u.is_superuser)
def reset_password(request, user_id):
    """Reset a user’s password"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        user.set_password(new_password)
        user.save()
        messages.success(request, f"Password reset for {user.username}")
        return redirect('manage_users')

    return render(request, 'admin_panel/reset_password.html', {'user': user})


@login_required(login_url='adminpanel_login')
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, f"User {user.username} deleted successfully.")
    return redirect('manage_users')