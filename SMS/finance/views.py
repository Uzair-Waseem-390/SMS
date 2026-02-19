from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal

from .models import BranchFeeStructure, Scholarship, StudentFee
from .forms import BranchFeeStructureForm, ScholarshipForm, GenerateFeeForm, RecordPaymentForm, EditSpecialFeeForm
from students.models import Student
from academics.models import Class, Section
from tenants.models import Branch
from accounts.utils import get_user_branch, get_user_school, get_school_and_branch, branch_url
from rbac.services import require_principal_or_manager


def _dash():
    return redirect('tenants:test_page')


def _can_manage_finance(user):
    return user.user_type in ('principal', 'manager', 'accountant')


def require_finance_access():
    """Decorator: principal, manager, or accountant."""
    from functools import wraps
    from django.core.exceptions import PermissionDenied

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if _can_manage_finance(request.user):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("Only principals, managers, and accountants can access this.")
        return _wrapped
    return decorator


# ═══ Dashboard ════════════════════════════════════════════════════

@login_required
@require_finance_access()
def finance_dashboard(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee_structure = BranchFeeStructure.objects.filter(branch=branch, is_active=True).first()
    total_fees = StudentFee.objects.filter(branch=branch, is_active=True)
    unpaid = total_fees.filter(status='unpaid')
    partial = total_fees.filter(status='partial')
    paid = total_fees.filter(status='paid')

    total_collected = paid.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    partial_collected = partial.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    total_outstanding = unpaid.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    partial_outstanding = partial.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    partial_outstanding -= partial_collected

    scholarships = Scholarship.objects.filter(branch=branch, is_active=True)
    special_fees_count = total_fees.filter(fee_type='special').count()

    return render(request, 'finance/dashboard.html', {
        'fee_structure': fee_structure,
        'total_fees_count': total_fees.count(),
        'unpaid_count': unpaid.count(),
        'partial_count': partial.count(),
        'paid_count': paid.count(),
        'total_collected': total_collected + partial_collected,
        'total_outstanding': total_outstanding + partial_outstanding,
        'scholarships_count': scholarships.count(),
        'special_fees_count': special_fees_count,
        'branch': branch,
        'title': 'Finance Dashboard',
    })


# ═══ Fee Structure ════════════════════════════════════════════════

@login_required
@require_principal_or_manager()
def fee_structure_detail(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee_structure = BranchFeeStructure.objects.filter(branch=branch, is_active=True).first()
    all_structures = BranchFeeStructure.objects.filter(branch=branch).order_by('-created_at')

    return render(request, 'finance/fee_structure_detail.html', {
        'fee_structure': fee_structure,
        'all_structures': all_structures,
        'branch': branch,
        'title': 'Fee Structure',
    })


@login_required
@require_principal_or_manager()
def edit_fee_structure(request, fs_id=None):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    instance = get_object_or_404(BranchFeeStructure, id=fs_id, branch=branch) if fs_id else None

    if request.method == 'POST':
        form = BranchFeeStructureForm(request.POST, instance=instance)
        if form.is_valid():
            fs = form.save(commit=False)
            fs.branch = branch
            fs.school = school
            fs.save()
            messages.success(request, 'Fee structure saved.')
            return redirect(branch_url(request, 'finance:fee_structure_detail'))
    else:
        form = BranchFeeStructureForm(instance=instance)

    return render(request, 'finance/fee_structure_form.html', {
        'form': form, 'instance': instance, 'branch': branch,
        'title': 'Edit Fee Structure' if instance else 'Create Fee Structure',
    })


# ═══ Scholarships ═════════════════════════════════════════════════

@login_required
@require_principal_or_manager()
def scholarship_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    scholarships = Scholarship.objects.filter(branch=branch).order_by('-is_active', '-created_at')
    return render(request, 'finance/scholarship_list.html', {
        'scholarships': scholarships, 'branch': branch, 'title': 'Scholarships',
    })


@login_required
@require_principal_or_manager()
def create_scholarship(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    if request.method == 'POST':
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.branch = branch
            s.school = school
            s.created_by = request.user
            s.save()
            messages.success(request, f'Scholarship "{s.name}" created.')
            return redirect(branch_url(request, 'finance:scholarship_list'))
    else:
        form = ScholarshipForm()

    return render(request, 'finance/scholarship_form.html', {
        'form': form, 'branch': branch, 'title': 'Create Scholarship', 'is_edit': False,
    })


@login_required
@require_principal_or_manager()
def edit_scholarship(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    scholarship = get_object_or_404(Scholarship, pk=pk, branch=branch)
    if request.method == 'POST':
        form = ScholarshipForm(request.POST, instance=scholarship)
        if form.is_valid():
            form.save()
            messages.success(request, f'Scholarship "{scholarship.name}" updated.')
            return redirect(branch_url(request, 'finance:scholarship_list'))
    else:
        form = ScholarshipForm(instance=scholarship)

    return render(request, 'finance/scholarship_form.html', {
        'form': form, 'scholarship': scholarship, 'branch': branch,
        'title': f'Edit: {scholarship.name}', 'is_edit': True,
    })


@login_required
@require_principal_or_manager()
def delete_scholarship(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    scholarship = get_object_or_404(Scholarship, pk=pk, branch=branch)
    if request.method == 'POST':
        scholarship.is_active = False
        scholarship.save()
        messages.success(request, f'Scholarship "{scholarship.name}" deactivated.')
        return redirect(branch_url(request, 'finance:scholarship_list'))

    return render(request, 'finance/delete_scholarship.html', {
        'scholarship': scholarship, 'title': f'Delete: {scholarship.name}',
    })


# ═══ AJAX ═════════════════════════════════════════════════════════

@login_required
def api_sections_for_class(request):
    """Return sections for a given class within the user's branch.
    If class_id is empty, returns ALL sections for the branch (with class prefix)."""
    branch = get_user_branch(request.user, request)
    if not branch:
        return JsonResponse({'sections': []})
    class_id = request.GET.get('class_id')
    qs = Section.objects.filter(class_obj__branch=branch, is_active=True)
    if class_id:
        qs = qs.filter(class_obj_id=class_id)
        sections = list(qs.order_by('name').values('id', 'name'))
    else:
        raw = qs.order_by('class_obj__numeric_level', 'name').values('id', 'name', 'class_obj__name')
        sections = [{'id': s['id'], 'name': f"{s['class_obj__name']} - {s['name']}"} for s in raw]
    return JsonResponse({'sections': sections})


# ═══ Fee Generation ═══════════════════════════════════════════════

@login_required
@require_finance_access()
def generate_fees(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee_structure = BranchFeeStructure.objects.filter(branch=branch, is_active=True).first()

    if request.method == 'POST':
        form = GenerateFeeForm(request.POST, branch=branch)
        if form.is_valid():
            cd = form.cleaned_data
            fee_type = cd.get('fee_type', 'academic')

            students_qs = Student.objects.filter(
                section__class_obj__branch=branch, is_active=True
            )
            if cd.get('class_filter'):
                students_qs = students_qs.filter(section__class_obj=cd['class_filter'])
            if cd.get('section_filter'):
                students_qs = students_qs.filter(section=cd['section_filter'])

            created = 0
            with transaction.atomic():
                for student in students_qs:
                    if fee_type == 'special':
                        amount = cd['special_fee_amount']
                        StudentFee.objects.create(
                            fee_type='special',
                            student=student,
                            fee_structure=None,
                            branch=branch,
                            school=school,
                            amount=amount,
                            scholarship_deduction=Decimal('0'),
                            net_amount=amount,
                            due_date=cd['due_date'],
                            label=cd.get('special_fee_name', ''),
                            created_by=request.user,
                        )
                    else:
                        if not fee_structure:
                            messages.error(request, 'No active fee structure for academic fees.')
                            return redirect(branch_url(request, 'finance:fee_structure_detail'))
                        amount = fee_structure.per_fee_amount
                        scholarship_deduction = Decimal('0')
                        if student.scholarship and student.scholarship.is_active:
                            scholarship_deduction = student.scholarship.calculate_deduction(amount)
                        net = amount - scholarship_deduction
                        StudentFee.objects.create(
                            fee_type='academic',
                            student=student,
                            fee_structure=fee_structure,
                            branch=branch,
                            school=school,
                            amount=amount,
                            scholarship_deduction=scholarship_deduction,
                            net_amount=net,
                            due_date=cd['due_date'],
                            label=cd.get('label', ''),
                            installment_number=cd.get('installment_number'),
                            created_by=request.user,
                        )
                    created += 1

            fee_label = 'special' if fee_type == 'special' else 'academic'
            messages.success(request, f'{fee_label.title()} fees generated for {created} student(s).')
            return redirect(branch_url(request, 'finance:fee_list'))
    else:
        form = GenerateFeeForm(branch=branch)

    return render(request, 'finance/generate_fees.html', {
        'form': form, 'fee_structure': fee_structure, 'branch': branch,
        'title': 'Generate Fees',
    })


# ═══ Fee List & Management ════════════════════════════════════════

@login_required
@require_finance_access()
def fee_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fees = StudentFee.objects.filter(branch=branch, is_active=True).select_related(
        'student', 'student__section', 'student__section__class_obj', 'received_by'
    )

    fee_type_filter = request.GET.get('fee_type', '')
    if fee_type_filter:
        fees = fees.filter(fee_type=fee_type_filter)

    status = request.GET.get('status', '')
    if status:
        fees = fees.filter(status=status)

    class_id = request.GET.get('class_id', '')
    if class_id:
        fees = fees.filter(student__section__class_obj_id=class_id)

    section_id = request.GET.get('section_id', '')
    if section_id:
        fees = fees.filter(student__section_id=section_id)

    search = request.GET.get('search', '')
    if search:
        fees = fees.filter(
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search) |
            Q(student__admission_number__icontains=search)
        )

    fees = fees.order_by('-due_date', 'student__first_name')

    classes = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level')

    summary = fees.aggregate(
        total_net=Sum('net_amount'),
        total_paid=Sum('amount_paid'),
    )

    return render(request, 'finance/fee_list.html', {
        'fees': fees, 'classes': classes, 'branch': branch,
        'selected_fee_type': fee_type_filter,
        'selected_status': status, 'selected_class': class_id,
        'selected_section': section_id, 'search_query': search,
        'summary': summary,
        'title': 'Student Fees',
    })


@login_required
@require_finance_access()
def fee_detail(request, fee_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee = get_object_or_404(
        StudentFee.objects.select_related(
            'student', 'student__section', 'student__section__class_obj',
            'student__scholarship', 'fee_structure', 'received_by', 'created_by'
        ),
        id=fee_id, branch=branch
    )

    return render(request, 'finance/fee_detail.html', {
        'fee': fee, 'title': f'Fee: {fee.student.full_name}',
    })


@login_required
@require_finance_access()
def edit_special_fee(request, fee_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee = get_object_or_404(StudentFee, id=fee_id, branch=branch, fee_type='special')

    if request.method == 'POST':
        form = EditSpecialFeeForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            fee.label = cd['special_fee_name']
            fee.amount = cd['amount']
            fee.net_amount = cd['amount']
            fee.due_date = cd['due_date']
            fee.save()
            messages.success(request, f'Special fee "{cd["special_fee_name"]}" updated for {fee.student.full_name}.')
            return redirect(branch_url(request, 'finance:fee_detail', fee_id=fee.id))
    else:
        form = EditSpecialFeeForm(initial={
            'special_fee_name': fee.label,
            'amount': fee.amount,
            'due_date': fee.due_date,
        })

    return render(request, 'finance/edit_special_fee.html', {
        'form': form, 'fee': fee,
        'title': f'Edit Special Fee - {fee.student.full_name}',
    })


@login_required
@require_finance_access()
def delete_special_fee(request, fee_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee = get_object_or_404(StudentFee, id=fee_id, branch=branch, fee_type='special')

    if request.method == 'POST':
        student_name = fee.student.full_name
        fee_name = fee.label
        fee.delete()
        messages.success(request, f'Special fee "{fee_name}" deleted for {student_name}.')
        return redirect(branch_url(request, 'finance:fee_list'))

    return render(request, 'finance/delete_special_fee.html', {
        'fee': fee,
        'title': f'Delete Special Fee - {fee.student.full_name}',
    })


@login_required
@require_finance_access()
def record_payment(request, fee_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee = get_object_or_404(StudentFee, id=fee_id, branch=branch)

    if fee.status == 'paid':
        messages.info(request, 'This fee is already fully paid.')
        return redirect(branch_url(request, 'finance:fee_detail', fee_id=fee.id))

    balance = fee.balance

    if request.method == 'POST':
        form = RecordPaymentForm(request.POST, max_amount=balance)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_type = form.cleaned_data['payment_type']
            notes = form.cleaned_data.get('notes', '')
            if notes:
                fee.notes = (fee.notes + '\n' + notes).strip() if fee.notes else notes

            fee.amount_paid += Decimal(str(amount))
            if payment_type == 'full' or fee.amount_paid >= fee.net_amount:
                fee.amount_paid = fee.net_amount
                fee.status = 'paid'
                fee.paid_date = timezone.now().date()
            else:
                fee.status = 'partial'

            fee.received_by = request.user
            fee.received_by_role = request.user.get_user_type_display()
            fee.save()

            status_label = 'Paid in Full' if fee.status == 'paid' else 'Partial Payment'
            messages.success(
                request,
                f'{status_label}: PKR {amount} recorded for {fee.student.full_name}. '
                f'Received by {request.user.full_name} ({request.user.get_user_type_display()}).'
            )
            return redirect(branch_url(request, 'finance:fee_detail', fee_id=fee.id))
    else:
        form = RecordPaymentForm(max_amount=balance)

    return render(request, 'finance/record_payment.html', {
        'form': form, 'fee': fee, 'balance': balance,
        'title': f'Record Payment - {fee.student.full_name}',
    })


# ═══ Fee Receipt (Print) ═════════════════════════════════════════

@login_required
@require_finance_access()
def fee_receipt(request, fee_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    fee = get_object_or_404(
        StudentFee.objects.select_related(
            'student', 'student__section', 'student__section__class_obj',
            'fee_structure', 'received_by', 'branch', 'school'
        ),
        id=fee_id, branch=branch
    )

    return render(request, 'finance/fee_receipt.html', {
        'fee': fee, 'school': school, 'branch': branch,
        'title': f'Fee Receipt - {fee.student.full_name}',
    })
