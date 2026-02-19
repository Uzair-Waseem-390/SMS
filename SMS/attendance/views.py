import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

from .models import StudentAttendance, StaffAttendance, STUDENT_STATUS_CHOICES, STAFF_STATUS_CHOICES
from .forms import DatePickerForm
from academics.models import Section
from students.models import Student
from staff.models import Teacher, Accountant, Employee
from accounts.utils import get_user_branch, get_user_school, can_manage_academics
from rbac.services import require_principal_or_manager, require_principal_or_manager_or_permission
from rbac.permissions import Permissions

User = get_user_model()


def _get_dashboard_redirect():
    return redirect('tenants:test_page')


def _can_mark_section_attendance(user, section):
    """
    Check if user can mark attendance for a specific section.
    Allowed: principal, manager, or teacher who is incharge of this section.
    """
    if can_manage_academics(user):
        return True
    if user.user_type == 'teacher':
        try:
            teacher = Teacher.objects.get(user=user, is_active=True)
            return teacher.incharge_section_id == section.id
        except Teacher.DoesNotExist:
            pass
    return False


# ─── Student Attendance: Bulk Mark for a Section ─────────────────

@login_required
def bulk_student_attendance(request, section_id):
    """Mark attendance for all students in a section at once."""
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user, request)
    if not branch or not school:
        messages.error(request, "No branch/school associated with your account.")
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch, is_active=True)

    if not _can_mark_section_attendance(request.user, section):
        raise PermissionDenied("You do not have permission to mark attendance for this section.")

    today = timezone.now().date()
    date_str = request.GET.get('date') or request.POST.get('attendance_date')
    if date_str:
        try:
            att_date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            att_date = today
    else:
        att_date = today

    students = Student.objects.filter(section=section, is_active=True).order_by('first_name', 'last_name')

    existing = {
        r.student_id: r
        for r in StudentAttendance.objects.filter(section=section, date=att_date)
    }

    if request.method == 'POST' and 'save_attendance' in request.POST:
        saved = 0
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'present')
            remark = request.POST.get(f'remarks_{student.id}', '')
            obj, created = StudentAttendance.objects.update_or_create(
                student=student, date=att_date,
                defaults={
                    'section': section, 'status': status, 'remarks': remark,
                    'branch': branch, 'school': school, 'marked_by': request.user,
                }
            )
            saved += 1
        messages.success(request, f'Attendance saved for {saved} student(s) on {att_date}.')
        return redirect(f'{request.path}?date={att_date}')

    student_rows = []
    for s in students:
        rec = existing.get(s.id)
        student_rows.append({
            'student': s,
            'status': rec.status if rec else 'present',
            'remarks': rec.remarks if rec else '',
            'saved': rec is not None,
        })

    return render(request, 'attendance/bulk_student_attendance.html', {
        'section': section,
        'class_obj': section.class_obj,
        'student_rows': student_rows,
        'att_date': att_date,
        'today': today,
        'status_choices': STUDENT_STATUS_CHOICES,
        'branch': branch,
        'title': f'Mark Attendance - {section.class_obj.name} {section.name}',
    })


# ─── Student Attendance: Individual ──────────────────────────────

@login_required
def individual_student_attendance(request, student_id):
    """View and edit attendance for one specific student."""
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user, request)
    if not branch or not school:
        return _get_dashboard_redirect()

    student = get_object_or_404(Student, id=student_id, section__class_obj__branch=branch, is_active=True)

    if not _can_mark_section_attendance(request.user, student.section):
        raise PermissionDenied("You do not have permission to mark attendance for this student.")

    today = timezone.now().date()
    date_str = request.GET.get('date') or request.POST.get('attendance_date')
    if date_str:
        try:
            att_date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            att_date = today
    else:
        att_date = today

    existing = StudentAttendance.objects.filter(student=student, date=att_date).first()

    if request.method == 'POST' and 'save_attendance' in request.POST:
        status = request.POST.get('status', 'present')
        remark = request.POST.get('remarks', '')
        StudentAttendance.objects.update_or_create(
            student=student, date=att_date,
            defaults={
                'section': student.section, 'status': status, 'remarks': remark,
                'branch': branch, 'school': school, 'marked_by': request.user,
            }
        )
        messages.success(request, f'Attendance saved for {student.full_name} on {att_date}.')
        return redirect(f'{request.path}?date={att_date}')

    recent = StudentAttendance.objects.filter(student=student).order_by('-date')[:30]

    return render(request, 'attendance/individual_student_attendance.html', {
        'student': student,
        'att_date': att_date,
        'today': today,
        'existing': existing,
        'recent': recent,
        'status_choices': STUDENT_STATUS_CHOICES,
        'title': f'Attendance - {student.full_name}',
    })


# ─── Staff Attendance: Bulk Mark ─────────────────────────────────

@login_required
@require_principal_or_manager()
def bulk_staff_attendance(request):
    """Mark attendance for all staff members at once."""
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user, request)
    if not branch or not school:
        messages.error(request, "No branch/school associated with your account.")
        return _get_dashboard_redirect()

    today = timezone.now().date()
    date_str = request.GET.get('date') or request.POST.get('attendance_date')
    if date_str:
        try:
            att_date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            att_date = today
    else:
        att_date = today

    teachers = Teacher.objects.filter(branch=branch, is_active=True).select_related('user')
    accountants = Accountant.objects.filter(branch=branch, is_active=True).select_related('user')
    employees = Employee.objects.filter(branch=branch, is_active=True).select_related('user')

    staff_users = []
    for t in teachers:
        staff_users.append({'user': t.user, 'type': 'Teacher', 'name': t.full_name})
    for a in accountants:
        staff_users.append({'user': a.user, 'type': 'Accountant', 'name': a.full_name})
    for e in employees:
        if e.user:
            staff_users.append({'user': e.user, 'type': e.get_employee_type_display(), 'name': e.full_name})

    user_ids = [s['user'].id for s in staff_users]
    existing = {
        r.user_id: r
        for r in StaffAttendance.objects.filter(user_id__in=user_ids, date=att_date)
    }

    if request.method == 'POST' and 'save_attendance' in request.POST:
        saved = 0
        for s in staff_users:
            uid = s['user'].id
            status = request.POST.get(f'status_{uid}', 'present')
            remark = request.POST.get(f'remarks_{uid}', '')
            late_time_str = request.POST.get(f'late_time_{uid}', '')
            half_leave_str = request.POST.get(f'half_leave_time_{uid}', '')
            late_time = _parse_time(late_time_str) if status == 'late' else None
            half_leave_time = _parse_time(half_leave_str) if status == 'halfleave' else None

            StaffAttendance.objects.update_or_create(
                user_id=uid, date=att_date,
                defaults={
                    'status': status, 'remarks': remark,
                    'late_time': late_time, 'half_leave_time': half_leave_time,
                    'branch': branch, 'school': school, 'marked_by': request.user,
                }
            )
            saved += 1
        messages.success(request, f'Attendance saved for {saved} staff member(s) on {att_date}.')
        return redirect(f'{request.path}?date={att_date}')

    staff_rows = []
    for s in staff_users:
        rec = existing.get(s['user'].id)
        staff_rows.append({
            'user': s['user'],
            'type': s['type'],
            'name': s['name'],
            'status': rec.status if rec else 'present',
            'remarks': rec.remarks if rec else '',
            'late_time': rec.late_time if rec else None,
            'half_leave_time': rec.half_leave_time if rec else None,
            'saved': rec is not None,
        })

    return render(request, 'attendance/bulk_staff_attendance.html', {
        'staff_rows': staff_rows,
        'att_date': att_date,
        'today': today,
        'status_choices': STAFF_STATUS_CHOICES,
        'branch': branch,
        'school': school,
        'title': f'Staff Attendance - {branch.name}',
    })


# ─── Staff Attendance: Individual ────────────────────────────────

@login_required
@require_principal_or_manager()
def individual_staff_attendance(request, user_id):
    """View and edit attendance for one specific staff member."""
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user, request)
    if not branch or not school:
        return _get_dashboard_redirect()

    staff_user = get_object_or_404(User, id=user_id, is_active=True)

    today = timezone.now().date()
    date_str = request.GET.get('date') or request.POST.get('attendance_date')
    if date_str:
        try:
            att_date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            att_date = today
    else:
        att_date = today

    existing = StaffAttendance.objects.filter(user=staff_user, date=att_date).first()

    if request.method == 'POST' and 'save_attendance' in request.POST:
        status = request.POST.get('status', 'present')
        remark = request.POST.get('remarks', '')
        late_time_str = request.POST.get('late_time', '')
        half_leave_str = request.POST.get('half_leave_time', '')
        late_time = _parse_time(late_time_str) if status == 'late' else None
        half_leave_time = _parse_time(half_leave_str) if status == 'halfleave' else None

        StaffAttendance.objects.update_or_create(
            user=staff_user, date=att_date,
            defaults={
                'status': status, 'remarks': remark,
                'late_time': late_time, 'half_leave_time': half_leave_time,
                'branch': branch, 'school': school, 'marked_by': request.user,
            }
        )
        messages.success(request, f'Attendance saved for {staff_user.get_full_name()} on {att_date}.')
        return redirect(f'{request.path}?date={att_date}')

    recent = StaffAttendance.objects.filter(user=staff_user).order_by('-date')[:30]

    return render(request, 'attendance/individual_staff_attendance.html', {
        'staff_user': staff_user,
        'att_date': att_date,
        'today': today,
        'existing': existing,
        'recent': recent,
        'status_choices': STAFF_STATUS_CHOICES,
        'title': f'Attendance - {staff_user.get_full_name()}',
    })


# ─── Reports ─────────────────────────────────────────────────────

@login_required
def student_attendance_report(request, section_id):
    """Attendance report/history for a section."""
    branch = get_user_branch(request.user, request)
    if not branch:
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch, is_active=True)

    if not _can_mark_section_attendance(request.user, section):
        if not can_manage_academics(request.user):
            raise PermissionDenied("You do not have permission to view this report.")

    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    students = Student.objects.filter(section=section, is_active=True).order_by('first_name')
    records = StudentAttendance.objects.filter(
        section=section, date__gte=start_date, date__lt=end_date
    )

    record_map = {}
    for r in records:
        record_map.setdefault(r.student_id, {})[r.date] = r.status

    import calendar
    num_days = calendar.monthrange(year, month)[1]
    days = [datetime.date(year, month, d) for d in range(1, num_days + 1)]

    student_data = []
    for s in students:
        row = {'student': s, 'days': []}
        s_records = record_map.get(s.id, {})
        present = 0
        absent = 0
        for d in days:
            st = s_records.get(d, '')
            row['days'].append(st)
            if st == 'present':
                present += 1
            elif st == 'absent':
                absent += 1
        row['present'] = present
        row['absent'] = absent
        student_data.append(row)

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    return render(request, 'attendance/student_attendance_report.html', {
        'section': section,
        'class_obj': section.class_obj,
        'student_data': student_data,
        'days': days,
        'month': month,
        'year': year,
        'months': months,
        'branch': branch,
        'title': f'Attendance Report - {section.class_obj.name} {section.name}',
    })


@login_required
@require_principal_or_manager()
def staff_attendance_report(request):
    """Attendance report/history for all staff in a branch."""
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user, request)
    if not branch or not school:
        return _get_dashboard_redirect()

    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    teachers = Teacher.objects.filter(branch=branch, is_active=True).select_related('user')
    accountants = Accountant.objects.filter(branch=branch, is_active=True).select_related('user')
    employees = Employee.objects.filter(branch=branch, is_active=True).select_related('user')

    staff_users = []
    for t in teachers:
        staff_users.append({'user': t.user, 'name': t.full_name, 'type': 'Teacher'})
    for a in accountants:
        staff_users.append({'user': a.user, 'name': a.full_name, 'type': 'Accountant'})
    for e in employees:
        if e.user:
            staff_users.append({'user': e.user, 'name': e.full_name, 'type': e.get_employee_type_display()})

    user_ids = [s['user'].id for s in staff_users]
    records = StaffAttendance.objects.filter(
        user_id__in=user_ids, date__gte=start_date, date__lt=end_date
    )

    record_map = {}
    for r in records:
        record_map.setdefault(r.user_id, {})[r.date] = r.status

    import calendar
    num_days = calendar.monthrange(year, month)[1]
    days = [datetime.date(year, month, d) for d in range(1, num_days + 1)]

    staff_data = []
    for s in staff_users:
        row = {'name': s['name'], 'type': s['type'], 'user': s['user'], 'days': []}
        u_records = record_map.get(s['user'].id, {})
        present = 0
        absent = 0
        for d in days:
            st = u_records.get(d, '')
            row['days'].append(st)
            if st == 'present':
                present += 1
            elif st == 'absent':
                absent += 1
        row['present'] = present
        row['absent'] = absent
        staff_data.append(row)

    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    return render(request, 'attendance/staff_attendance_report.html', {
        'staff_data': staff_data,
        'days': days,
        'month': month,
        'year': year,
        'months': months,
        'branch': branch,
        'school': school,
        'title': f'Staff Attendance Report - {branch.name}',
    })


# ─── Helpers ─────────────────────────────────────────────────────

def _parse_time(time_str):
    if not time_str:
        return None
    try:
        return datetime.time.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None
