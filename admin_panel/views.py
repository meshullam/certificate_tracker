from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User


# ==================================================================
# CUSTOM DECORATOR - Require Superuser Access
# ==================================================================

def superuser_required(view_func):
    """
    Decorator that requires user to be a superuser.
    Redirects to login page if not authenticated or not superuser.
    """
    decorated = login_required(login_url='adminpanel_login')(view_func)
    decorated = user_passes_test(
        lambda u: u.is_superuser,
        login_url='adminpanel_login'
    )(decorated)
    return decorated


# ==================================================================
# AUTHENTICATION VIEWS
# ==================================================================

def admin_login(request):
    """
    Custom login view for superuser/admin only.
    Only users with is_superuser=True can access the admin panel.
    """
    # If already logged in and is superuser, redirect to dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Access denied. Only system administrators can log in.')

    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    """
    Logout the admin user and redirect to login page.
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('adminpanel_login')


# ==================================================================
# DASHBOARD
# ==================================================================

@superuser_required
def dashboard(request):
    """
    Admin dashboard showing user statistics.
    """
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    staff_users = User.objects.filter(is_staff=True).count()

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'staff_users': staff_users,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ==================================================================
# USER MANAGEMENT - LIST & SEARCH
# ==================================================================

@superuser_required
def manage_users(request):
    """
    Display and search users.
    Supports search by username or email.
    """
    query = request.GET.get('q', '').strip()
    
    # Get all users, ordered by username
    users = User.objects.all().order_by('username')
    
    # Apply search filter if query exists
    if query:
        users = users.filter(
            username__icontains=query
        ) | users.filter(
            email__icontains=query
        )
    
    context = {
        'users': users,
        'query': query,
    }
    return render(request, 'admin_panel/manage_users.html', context)


# ==================================================================
# USER MANAGEMENT - CREATE
# ==================================================================

@superuser_required
def add_user(request):
    """
    Create a new user with validation.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # Validation
        if not username:
            messages.error(request, 'Username is required.')
            return redirect('add_user')
        
        if not password:
            messages.error(request, 'Password is required.')
            return redirect('add_user')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('add_user')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect('add_user')

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.is_staff = is_staff
            user.is_active = is_active
            user.save()
            
            messages.success(request, f'User "{username}" created successfully.')
            return redirect('manage_users')
        
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('add_user')

    return render(request, 'admin_panel/add_user.html')


# ==================================================================
# USER MANAGEMENT - UPDATE
# ==================================================================

@superuser_required
def edit_user(request, user_id):
    """
    Edit user details (email, staff status, active status).
    Username cannot be changed for security reasons.
    """
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # Update user
        user.email = email
        user.is_staff = is_staff
        user.is_active = is_active
        user.save()
        
        messages.success(request, f'User "{user.username}" updated successfully.')
        return redirect('manage_users')

    context = {'user': user}
    return render(request, 'admin_panel/edit_user.html', context)


# ==================================================================
# USER MANAGEMENT - PASSWORD RESET
# ==================================================================

@superuser_required
def reset_password(request, user_id):
    """
    Reset a user's password.
    Requires password confirmation for security.
    """
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        new_password2 = request.POST.get('new_password2', '').strip()
        
        # Validation
        if not new_password:
            messages.error(request, 'Password cannot be empty.')
            return redirect('reset_password', user_id=user_id)
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('reset_password', user_id=user_id)
        
        if new_password != new_password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('reset_password', user_id=user_id)

        # Reset password
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f'Password reset successfully for "{user.username}".')
        return redirect('manage_users')

    context = {'user': user}
    return render(request, 'admin_panel/reset_password.html', context)


# ==================================================================
# USER MANAGEMENT - DELETE
# ==================================================================

@superuser_required
def delete_user(request, user_id):
    """
    Delete a user after confirmation.
    Prevents deletion of superuser accounts for safety.
    """
    user = get_object_or_404(User, pk=user_id)
    
    # Prevent deleting superuser accounts
    if user.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts for security reasons.')
        return redirect('manage_users')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully.')
        return redirect('manage_users')

    # Show confirmation page
    context = {'user': user}
    return render(request, 'admin_panel/confirm_delete.html', context)