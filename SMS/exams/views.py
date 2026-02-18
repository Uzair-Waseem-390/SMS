import json
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Exam, ExamAttendance, ExamResult, EXAM_TYPE_CHOICES, EXAM_ATTENDANCE_CHOICES
from .forms import ExamBulkCreateForm, ExamEditForm
from academics.models import Class, Section, Subject
from students.models import Student
from staff.models import Teacher
from accounts.utils import get_user_branch, get_user_school, can_manage_academics
from rbac.services import require_principal_or_manager, require_principal_or_manager_or_permission
from rbac.permissions import Permissions


def _dash():
    return redirect('tenants:test_page')


def _can_manage_section(user, section):
    if can_manage_academics(user):
        return True
    if user.user_type == 'teacher':
        try:
            t = Teacher.objects.get(user=user, is_active=True)
            return t.incharge_section_id == section.id
        except Teacher.DoesNotExist:
            pass
    return False


def _can_view_student_results(user, student):
    """Student or their parent can view their own results."""
    if can_manage_academics(user):
        return True
    if user.user_type == 'teacher':
        try:
            t = Teacher.objects.get(user=user, is_active=True)
            return t.incharge_section_id == student.section_id
        except Teacher.DoesNotExist:
            pass
    if user.user_type == 'student' and hasattr(user, 'student_profile'):
        return user.student_profile.id == student.id
    if user.user_type == 'parent' and hasattr(user, 'parent_profile'):
        return user.parent_profile.students.filter(id=student.id).exists()
    return False


# ═══ CRUD ═════════════════════════════════════════════════════════

@login_required
@require_principal_or_manager_or_permission(Permissions.EXAM_VIEW.value)
def exam_list(request):
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user)
    if not branch or not school:
        return _dash()

    exams = Exam.objects.filter(branch=branch, is_active=True).select_related(
        'subject', 'class_obj', 'section'
    ).order_by('-date', 'class_obj__numeric_level', 'section__name')

    et = request.GET.get('exam_type', '')
    cls = request.GET.get('class_id', '')
    sec = request.GET.get('section_id', '')
    sub = request.GET.get('subject_id', '')
    search = request.GET.get('q', '').strip()

    if et:
        exams = exams.filter(exam_type=et)
    if cls:
        exams = exams.filter(class_obj_id=cls)
    if sec:
        exams = exams.filter(section_id=sec)
    if sub:
        exams = exams.filter(subject_id=sub)
    if search:
        exams = exams.filter(
            Q(name__icontains=search) | Q(subject__name__icontains=search)
        )

    classes = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level')
    sections = Section.objects.filter(class_obj__branch=branch, is_active=True).select_related('class_obj')
    subjects = Subject.objects.filter(branch=branch, is_active=True).order_by('name')
    can_manage = can_manage_academics(request.user)

    return render(request, 'exams/exam_list.html', {
        'exams': exams, 'classes': classes,
        'sections': sections, 'subjects': subjects,
        'exam_types': EXAM_TYPE_CHOICES,
        'selected_type': et, 'selected_class': cls,
        'selected_section': sec, 'selected_subject': sub,
        'search_query': search,
        'can_manage': can_manage,
        'title': 'Exams',
    })


@login_required
@require_principal_or_manager()
def create_exam(request):
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user)
    if not branch or not school:
        return _dash()

    if request.method == 'POST':
        form = ExamBulkCreateForm(request.POST, branch=branch)
        if form.is_valid():
            cd = form.cleaned_data
            sections = cd['sections']
            batch = uuid.uuid4()
            created = 0
            for sec in sections:
                Exam.objects.create(
                    name=cd['name'],
                    exam_type=cd['exam_type'],
                    date=cd['date'],
                    start_time=cd['start_time'],
                    duration_minutes=cd['duration_minutes'],
                    subject=cd['subject'],
                    class_obj=sec.class_obj,
                    section=sec,
                    total_marks=cd['total_marks'],
                    passing_marks=cd['passing_marks'],
                    description=cd.get('description', ''),
                    branch=branch,
                    school=school,
                    batch_id=batch,
                    created_by=request.user,
                )
                created += 1

            sec_names = ', '.join(f"{s.class_obj.name}-{s.name}" for s in sections)
            messages.success(request, f'Exam "{cd["name"]}" created for {created} section(s): {sec_names}')
            return redirect('exams:exam_list')
    else:
        form = ExamBulkCreateForm(branch=branch)

    classes = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level').prefetch_related('sections')
    class_sections = {}
    for c in classes:
        class_sections[str(c.id)] = list(
            c.sections.filter(is_active=True).order_by('name').values('id', 'name')
        )

    selected_classes = request.POST.getlist('classes') if request.method == 'POST' else []

    return render(request, 'exams/exam_create.html', {
        'form': form,
        'classes': classes,
        'class_sections_json': json.dumps(class_sections),
        'selected_classes': selected_classes,
        'title': 'Create Exam',
    })


@login_required
@require_principal_or_manager()
def edit_exam(request, exam_id):
    branch = get_user_branch(request.user, request)
    school = get_user_school(request.user)
    if not branch or not school:
        return _dash()

    exam = get_object_or_404(Exam, id=exam_id, branch=branch)
    if request.method == 'POST':
        form = ExamEditForm(request.POST, instance=exam, branch=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Exam "{exam.name}" updated.')
            return redirect('exams:exam_detail', exam_id=exam.id)
    else:
        form = ExamEditForm(instance=exam, branch=branch)

    return render(request, 'exams/exam_edit.html', {
        'form': form, 'exam': exam, 'title': f'Edit Exam: {exam.name}',
    })


@login_required
@require_principal_or_manager()
def delete_exam(request, exam_id):
    branch = get_user_branch(request.user, request)
    exam = get_object_or_404(Exam, id=exam_id, branch=branch)

    if request.method == 'POST':
        delete_batch = request.POST.get('delete_batch') == 'on'
        if delete_batch and exam.batch_id:
            count = Exam.objects.filter(batch_id=exam.batch_id, is_active=True).update(is_active=False)
            messages.success(request, f'{count} exam(s) in the batch deactivated.')
        else:
            exam.is_active = False
            exam.save()
            messages.success(request, f'Exam "{exam.name}" deactivated.')
        return redirect('exams:exam_list')

    siblings = exam.sibling_exams.select_related('section', 'class_obj') if exam.batch_id else []

    return render(request, 'exams/delete_exam.html', {
        'exam': exam, 'siblings': siblings,
        'title': f'Delete Exam: {exam.name}',
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.EXAM_VIEW.value)
def exam_detail(request, exam_id):
    branch = get_user_branch(request.user, request)
    if not branch:
        return _dash()

    exam = get_object_or_404(
        Exam.objects.select_related('subject', 'class_obj', 'section', 'created_by'),
        id=exam_id, branch=branch
    )
    students = Student.objects.filter(section=exam.section, is_active=True).order_by('first_name')
    attendance = {a.student_id: a for a in ExamAttendance.objects.filter(exam=exam)}
    results = {r.student_id: r for r in ExamResult.objects.filter(exam=exam)}

    student_data = []
    for s in students:
        student_data.append({
            'student': s,
            'attendance': attendance.get(s.id),
            'result': results.get(s.id),
        })

    stats = ExamResult.objects.filter(exam=exam, is_absent=False, obtained_marks__isnull=False)
    avg_marks = stats.aggregate(avg=Avg('obtained_marks'))['avg']
    passed = stats.filter(obtained_marks__gte=exam.passing_marks).count()
    failed = stats.filter(obtained_marks__lt=exam.passing_marks).count()
    total_appeared = stats.count()
    total_students = students.count()
    att_marked = len(attendance)
    results_entered = len(results)

    siblings = exam.sibling_exams.select_related('section', 'class_obj') if exam.batch_id else []

    can_manage = can_manage_academics(request.user) or _can_manage_section(request.user, exam.section)

    return render(request, 'exams/exam_detail.html', {
        'exam': exam, 'student_data': student_data,
        'avg_marks': avg_marks, 'passed': passed, 'failed': failed,
        'total_appeared': total_appeared, 'total_students': total_students,
        'att_marked': att_marked, 'results_entered': results_entered,
        'siblings': siblings,
        'can_manage': can_manage,
        'title': f'Exam: {exam.name}',
    })


# ═══ AJAX ═════════════════════════════════════════════════════════

@login_required
def get_sections_for_class(request):
    """Returns sections for one or more class IDs (comma-separated)."""
    class_ids_str = request.GET.get('class_id', '')
    branch = get_user_branch(request.user, request)
    if class_ids_str and branch:
        try:
            class_ids = [int(c) for c in class_ids_str.split(',') if c.strip()]
        except ValueError:
            return JsonResponse([], safe=False)
        sections = Section.objects.filter(
            class_obj_id__in=class_ids, class_obj__branch=branch, is_active=True
        ).select_related('class_obj').order_by('class_obj__numeric_level', 'name').values(
            'id', 'name', 'class_obj__id', 'class_obj__name'
        )
        return JsonResponse(list(sections), safe=False)
    return JsonResponse([], safe=False)


# ═══ Exam Attendance ══════════════════════════════════════════════

@login_required
def exam_attendance(request, exam_id):
    branch = get_user_branch(request.user, request)
    if not branch:
        return _dash()

    exam = get_object_or_404(Exam, id=exam_id, branch=branch)
    if not _can_manage_section(request.user, exam.section):
        raise PermissionDenied("You cannot mark attendance for this exam.")

    students = Student.objects.filter(section=exam.section, is_active=True).order_by('first_name')
    existing = {a.student_id: a for a in ExamAttendance.objects.filter(exam=exam)}

    if request.method == 'POST':
        saved = 0
        for s in students:
            status = request.POST.get(f'status_{s.id}', 'present')
            remark = request.POST.get(f'remarks_{s.id}', '')
            ExamAttendance.objects.update_or_create(
                exam=exam, student=s,
                defaults={'status': status, 'remarks': remark, 'marked_by': request.user}
            )
            saved += 1
        messages.success(request, f'Exam attendance saved for {saved} student(s).')
        return redirect('exams:exam_attendance', exam_id=exam.id)

    rows = []
    for s in students:
        rec = existing.get(s.id)
        rows.append({
            'student': s,
            'status': rec.status if rec else 'present',
            'remarks': rec.remarks if rec else '',
            'saved': rec is not None,
        })

    return render(request, 'exams/exam_attendance.html', {
        'exam': exam, 'rows': rows,
        'status_choices': EXAM_ATTENDANCE_CHOICES,
        'title': f'Attendance: {exam.name}',
    })


# ═══ Exam Results Entry ══════════════════════════════════════════

@login_required
def exam_results_entry(request, exam_id):
    branch = get_user_branch(request.user, request)
    if not branch:
        return _dash()

    exam = get_object_or_404(Exam, id=exam_id, branch=branch)
    if not _can_manage_section(request.user, exam.section):
        raise PermissionDenied("You cannot enter results for this exam.")

    students = Student.objects.filter(section=exam.section, is_active=True).order_by('first_name')
    existing = {r.student_id: r for r in ExamResult.objects.filter(exam=exam)}
    att_map = {a.student_id: a for a in ExamAttendance.objects.filter(exam=exam)}

    if request.method == 'POST':
        saved = 0
        for s in students:
            marks_str = request.POST.get(f'marks_{s.id}', '').strip()
            remark = request.POST.get(f'remarks_{s.id}', '')
            is_absent = request.POST.get(f'absent_{s.id}') == 'on'

            obtained = None
            if not is_absent and marks_str:
                try:
                    obtained = float(marks_str)
                except (ValueError, TypeError):
                    obtained = None

            obj, _ = ExamResult.objects.update_or_create(
                exam=exam, student=s,
                defaults={
                    'obtained_marks': obtained,
                    'is_absent': is_absent,
                    'remarks': remark,
                    'entered_by': request.user,
                    'grade': '',
                }
            )
            obj.grade = obj.compute_grade()
            obj.save(update_fields=['grade'])
            saved += 1

        messages.success(request, f'Results saved for {saved} student(s).')
        return redirect('exams:exam_results_entry', exam_id=exam.id)

    rows = []
    for s in students:
        rec = existing.get(s.id)
        att = att_map.get(s.id)
        rows.append({
            'student': s,
            'obtained_marks': rec.obtained_marks if rec else None,
            'is_absent': rec.is_absent if rec else (att.status == 'absent' if att else False),
            'remarks': rec.remarks if rec else '',
            'grade': rec.grade if rec else '',
            'saved': rec is not None,
        })

    return render(request, 'exams/exam_results_entry.html', {
        'exam': exam, 'rows': rows,
        'title': f'Enter Results: {exam.name}',
    })


# ═══ Publish Results ═════════════════════════════════════════════

@login_required
@require_principal_or_manager()
def publish_results(request, exam_id):
    branch = get_user_branch(request.user, request)
    exam = get_object_or_404(Exam, id=exam_id, branch=branch)

    if request.method == 'POST':
        publish_batch = request.POST.get('publish_batch') == 'on'
        if publish_batch and exam.batch_id:
            count = Exam.objects.filter(batch_id=exam.batch_id, is_active=True).update(is_published=True)
            messages.success(request, f'Results published for {count} exam(s) in the batch.')
        else:
            exam.is_published = True
            exam.save(update_fields=['is_published'])
            messages.success(request, f'Results for "{exam.name}" have been published.')
        return redirect('exams:exam_detail', exam_id=exam.id)

    siblings = exam.sibling_exams.select_related('section', 'class_obj') if exam.batch_id else []
    return render(request, 'exams/publish_results.html', {
        'exam': exam, 'siblings': siblings,
        'title': f'Publish: {exam.name}',
    })


# ═══ Reports ═════════════════════════════════════════════════════

@login_required
def exam_report(request):
    """Overview report: all exams with stats, filterable."""
    branch = get_user_branch(request.user, request)
    if not branch:
        return _dash()

    exams = Exam.objects.filter(branch=branch, is_active=True).select_related('subject', 'class_obj', 'section')

    et = request.GET.get('exam_type', '')
    cls = request.GET.get('class_id', '')
    sec = request.GET.get('section_id', '')
    sub = request.GET.get('subject_id', '')
    if et:
        exams = exams.filter(exam_type=et)
    if cls:
        exams = exams.filter(class_obj_id=cls)
    if sec:
        exams = exams.filter(section_id=sec)
    if sub:
        exams = exams.filter(subject_id=sub)

    exam_data = []
    for e in exams:
        results = ExamResult.objects.filter(exam=e, is_absent=False, obtained_marks__isnull=False)
        agg = results.aggregate(avg=Avg('obtained_marks'), total=Count('id'))
        passed = results.filter(obtained_marks__gte=e.passing_marks).count()
        att_present = ExamAttendance.objects.filter(exam=e, status='present').count()
        att_absent = ExamAttendance.objects.filter(exam=e, status='absent').count()
        exam_data.append({
            'exam': e,
            'avg': agg['avg'],
            'appeared': agg['total'],
            'passed': passed,
            'present': att_present,
            'absent': att_absent,
        })

    classes = Class.objects.filter(branch=branch, is_active=True)
    subjects = Subject.objects.filter(branch=branch, is_active=True)
    sections = Section.objects.filter(class_obj__branch=branch, is_active=True)

    return render(request, 'exams/report_exam.html', {
        'exam_data': exam_data,
        'classes': classes, 'subjects': subjects, 'sections': sections,
        'exam_types': EXAM_TYPE_CHOICES,
        'filters': {'exam_type': et, 'class_id': cls, 'section_id': sec, 'subject_id': sub},
        'title': 'Exam Reports',
    })


@login_required
def student_result_report(request, student_id):
    """Individual student's exam results - visible to student, parent, teacher, principal, manager."""
    student = get_object_or_404(Student, id=student_id)

    if not _can_view_student_results(request.user, student):
        raise PermissionDenied("You do not have permission to view this student's results.")

    results = ExamResult.objects.filter(
        student=student, exam__is_active=True
    ).select_related('exam', 'exam__subject').order_by('-exam__date')

    attendance = ExamAttendance.objects.filter(
        student=student, exam__is_active=True
    ).select_related('exam').order_by('-exam__date')

    att_map = {a.exam_id: a for a in attendance}

    result_data = []
    total_obtained = 0
    total_max = 0
    for r in results:
        result_data.append({
            'result': r,
            'attendance': att_map.get(r.exam_id),
        })
        if r.obtained_marks is not None and not r.is_absent:
            total_obtained += float(r.obtained_marks)
            total_max += r.exam.total_marks

    overall_pct = round(total_obtained / total_max * 100, 1) if total_max > 0 else 0

    return render(request, 'exams/report_student.html', {
        'student': student,
        'result_data': result_data,
        'overall_pct': overall_pct,
        'total_obtained': total_obtained,
        'total_max': total_max,
        'title': f'Results: {student.full_name}',
    })
