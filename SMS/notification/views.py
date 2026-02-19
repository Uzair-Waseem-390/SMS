from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Notification, Timetable, NOTIFICATION_TYPE_CHOICES, VISIBILITY_CHOICES
from .forms import NotificationForm, TimetableForm
from tenants.models import Branch
from accounts.utils import get_user_branch, get_user_school, can_manage_academics, branch_url
from rbac.services import require_principal_or_manager


def _dash():
    return redirect('tenants:test_page')


# ═══ Notifications ════════════════════════════════════════════════

@login_required
@require_principal_or_manager()
def notification_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school:
        return _dash()

    is_principal = request.user.user_type == 'principal'

    if is_principal:
        notifications = Notification.objects.filter(school=school, is_active=True)
        branch_filter = request.GET.get('branch_id', '')
        if branch_filter:
            notifications = notifications.filter(branch_id=branch_filter)
    else:
        notifications = Notification.objects.filter(branch=branch, is_active=True) if branch else Notification.objects.none()
        branch_filter = ''

    ntype = request.GET.get('type', '')
    if ntype:
        notifications = notifications.filter(notification_type=ntype)

    notifications = notifications.select_related('branch', 'created_by').order_by('-date', '-time')

    branches = Branch.objects.filter(school=school, is_active=True) if is_principal else []

    return render(request, 'notification/notification_list.html', {
        'notifications': notifications,
        'branches': branches,
        'notification_types': NOTIFICATION_TYPE_CHOICES,
        'selected_branch': branch_filter,
        'selected_type': ntype,
        'is_principal': is_principal,
        'title': 'Notifications',
    })


@login_required
@require_principal_or_manager()
def create_notification(request):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    if request.method == 'POST':
        form = NotificationForm(request.POST, user=request.user, school=school)
        if form.is_valid():
            notif = form.save(commit=False)
            notif.school = school
            notif.created_by = request.user
            notif.save()
            messages.success(request, f'Notification "{notif.title}" created successfully!')
            return redirect(branch_url(request, 'notification:notification_list'))
    else:
        form = NotificationForm(user=request.user, school=school)

    return render(request, 'notification/notification_form.html', {
        'form': form, 'title': 'Create Notification', 'is_edit': False,
    })


@login_required
@require_principal_or_manager()
def edit_notification(request, notif_id):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    notif = get_object_or_404(Notification, id=notif_id, school=school)

    if request.method == 'POST':
        form = NotificationForm(request.POST, instance=notif, user=request.user, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, f'Notification "{notif.title}" updated.')
            return redirect(branch_url(request, 'notification:notification_list'))
    else:
        form = NotificationForm(instance=notif, user=request.user, school=school)

    return render(request, 'notification/notification_form.html', {
        'form': form, 'notif': notif, 'title': f'Edit: {notif.title}', 'is_edit': True,
    })


@login_required
@require_principal_or_manager()
def delete_notification(request, notif_id):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    notif = get_object_or_404(Notification, id=notif_id, school=school)

    if request.method == 'POST':
        notif.is_active = False
        notif.save()
        messages.success(request, f'Notification "{notif.title}" deleted.')
        return redirect(branch_url(request, 'notification:notification_list'))

    return render(request, 'notification/delete_notification.html', {
        'notif': notif, 'title': f'Delete: {notif.title}',
    })


@login_required
@require_principal_or_manager()
def notification_detail(request, notif_id):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    notif = get_object_or_404(
        Notification.objects.select_related('branch', 'created_by'),
        id=notif_id, school=school,
    )

    return render(request, 'notification/notification_detail.html', {
        'notif': notif, 'title': notif.title,
    })


# ═══ Timetable ═══════════════════════════════════════════════════

@login_required
@require_principal_or_manager()
def timetable_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school:
        return _dash()

    is_principal = request.user.user_type == 'principal'

    if is_principal:
        timetables = Timetable.objects.filter(school=school)
        branch_filter = request.GET.get('branch_id', '')
        if branch_filter:
            timetables = timetables.filter(branch_id=branch_filter)
    else:
        timetables = Timetable.objects.filter(branch=branch) if branch else Timetable.objects.none()
        branch_filter = ''

    timetables = timetables.select_related('branch', 'created_by').order_by('-created_at')

    branches = Branch.objects.filter(school=school, is_active=True) if is_principal else []

    return render(request, 'notification/timetable_list.html', {
        'timetables': timetables,
        'branches': branches,
        'selected_branch': branch_filter,
        'is_principal': is_principal,
        'title': 'Timetables',
    })


@login_required
@require_principal_or_manager()
def create_timetable(request):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    if request.method == 'POST':
        form = TimetableForm(request.POST, request.FILES, user=request.user, school=school)
        if form.is_valid():
            tt = form.save(commit=False)
            tt.school = school
            tt.created_by = request.user
            tt.save()
            messages.success(request, f'Timetable "{tt.title}" uploaded!')
            return redirect(branch_url(request, 'notification:timetable_list'))
    else:
        form = TimetableForm(user=request.user, school=school)

    return render(request, 'notification/timetable_form.html', {
        'form': form, 'title': 'Upload Timetable', 'is_edit': False,
    })


@login_required
@require_principal_or_manager()
def edit_timetable(request, tt_id):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    tt = get_object_or_404(Timetable, id=tt_id, school=school)

    if request.method == 'POST':
        form = TimetableForm(request.POST, request.FILES, instance=tt, user=request.user, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, f'Timetable "{tt.title}" updated.')
            return redirect(branch_url(request, 'notification:timetable_list'))
    else:
        form = TimetableForm(instance=tt, user=request.user, school=school)

    return render(request, 'notification/timetable_form.html', {
        'form': form, 'timetable': tt, 'title': f'Edit: {tt.title}', 'is_edit': True,
    })


@login_required
@require_principal_or_manager()
def delete_timetable(request, tt_id):
    school = get_user_school(request.user, request)
    if not school:
        return _dash()

    tt = get_object_or_404(Timetable, id=tt_id, school=school)

    if request.method == 'POST':
        tt.delete()
        messages.success(request, f'Timetable "{tt.title}" deleted.')
        return redirect(branch_url(request, 'notification:timetable_list'))

    return render(request, 'notification/delete_timetable.html', {
        'timetable': tt, 'title': f'Delete: {tt.title}',
    })
