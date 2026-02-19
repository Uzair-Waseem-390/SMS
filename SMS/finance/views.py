from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q, Count, F
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal

from .models import BranchFeeStructure, Scholarship, StudentFee, Expense, SalaryRecord
from .forms import (
    BranchFeeStructureForm, ScholarshipForm, GenerateFeeForm, RecordPaymentForm,
    EditSpecialFeeForm, ExpenseForm, GenerateSalaryForm, EditSalaryForm,
)
from students.models import Student
from academics.models import Class, Section
from tenants.models import Branch
from accounts.utils import get_user_branch, get_user_school, get_school_and_branch, branch_url
from rbac.services import require_principal_or_manager
from django.contrib.auth import get_user_model
import calendar

User = get_user_model()


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
    academic_fees = total_fees.filter(fee_type='academic')
    special_fees = total_fees.filter(fee_type='special')
    unpaid = total_fees.filter(status='unpaid')
    partial = total_fees.filter(status='partial')
    paid = total_fees.filter(status='paid')

    total_collected = paid.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    partial_collected = partial.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    total_outstanding = unpaid.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    partial_outstanding = partial.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    partial_outstanding -= partial_collected

    total_income = total_collected + partial_collected

    scholarships = Scholarship.objects.filter(branch=branch, is_active=True)
    total_scholarship_deductions = total_fees.aggregate(s=Sum('scholarship_deduction'))['s'] or Decimal('0')

    expenses_qs = Expense.objects.filter(branch=branch)
    total_expenses = expenses_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    recent_expenses = expenses_qs.order_by('-expense_date')[:5]

    from .models import EXPENSE_CATEGORY_CHOICES
    top_expense_cats = []
    for code, label in EXPENSE_CATEGORY_CHOICES:
        amt = expenses_qs.filter(category=code).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        if amt:
            top_expense_cats.append({'cat': label, 'amt': amt})
    top_expense_cats.sort(key=lambda x: x['amt'], reverse=True)

    salaries_qs = SalaryRecord.objects.filter(branch=branch)
    total_salaries_paid = salaries_qs.filter(status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    total_salaries_pending = salaries_qs.filter(status='unpaid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    salary_employee_count = salaries_qs.values('employee').distinct().count()

    now = timezone.now()
    cur_month_salaries = salaries_qs.filter(month=now.month, year=now.year)
    cur_salary_total = cur_month_salaries.aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    cur_salary_paid = cur_month_salaries.filter(status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    cur_salary_unpaid = cur_salary_total - cur_salary_paid

    net_profit = total_income - total_expenses - total_salaries_paid

    total_receivable = total_fees.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    collection_rate = (total_income / total_receivable * 100) if total_receivable else Decimal('0')

    return render(request, 'finance/dashboard.html', {
        'fee_structure': fee_structure,
        'branch': branch,
        'total_fees_count': total_fees.count(),
        'academic_fees_count': academic_fees.count(),
        'special_fees_count': special_fees.count(),
        'unpaid_count': unpaid.count(),
        'partial_count': partial.count(),
        'paid_count': paid.count(),
        'total_income': total_income,
        'total_outstanding': total_outstanding + partial_outstanding,
        'total_receivable': total_receivable,
        'collection_rate': collection_rate,
        'scholarships_count': scholarships.count(),
        'total_scholarship_deductions': total_scholarship_deductions,
        'total_expenses': total_expenses,
        'recent_expenses': recent_expenses,
        'top_expense_cats': top_expense_cats[:5],
        'total_salaries_paid': total_salaries_paid,
        'total_salaries_pending': total_salaries_pending,
        'salary_employee_count': salary_employee_count,
        'cur_month_name': calendar.month_name[now.month],
        'cur_salary_total': cur_salary_total,
        'cur_salary_paid': cur_salary_paid,
        'cur_salary_unpaid': cur_salary_unpaid,
        'net_profit': net_profit,
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


# ═══ Expenses ═════════════════════════════════════════════════════

@login_required
@require_finance_access()
def expense_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    expenses = Expense.objects.filter(branch=branch).order_by('-expense_date', '-created_at')

    cat = request.GET.get('category', '')
    if cat:
        expenses = expenses.filter(category=cat)

    search = request.GET.get('search', '')
    if search:
        expenses = expenses.filter(Q(title__icontains=search) | Q(description__icontains=search))

    total = expenses.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    from .models import EXPENSE_CATEGORY_CHOICES
    return render(request, 'finance/expense_list.html', {
        'expenses': expenses, 'total': total, 'branch': branch,
        'categories': EXPENSE_CATEGORY_CHOICES,
        'selected_category': cat, 'search_query': search,
        'title': 'Expenses',
    })


@login_required
@require_finance_access()
def create_expense(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.branch = branch
            exp.school = school
            exp.created_by = request.user
            exp.save()
            messages.success(request, f'Expense "{exp.title}" of PKR {exp.amount} added.')
            return redirect(branch_url(request, 'finance:expense_list'))
    else:
        form = ExpenseForm()

    return render(request, 'finance/expense_form.html', {
        'form': form, 'branch': branch, 'title': 'Add Expense', 'is_edit': False,
    })


@login_required
@require_finance_access()
def edit_expense(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    expense = get_object_or_404(Expense, pk=pk, branch=branch)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense "{expense.title}" updated.')
            return redirect(branch_url(request, 'finance:expense_list'))
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'finance/expense_form.html', {
        'form': form, 'expense': expense, 'branch': branch,
        'title': f'Edit: {expense.title}', 'is_edit': True,
    })


@login_required
@require_finance_access()
def delete_expense(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    expense = get_object_or_404(Expense, pk=pk, branch=branch)
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f'Expense "{title}" deleted.')
        return redirect(branch_url(request, 'finance:expense_list'))

    return render(request, 'finance/delete_expense.html', {
        'expense': expense, 'title': f'Delete: {expense.title}',
    })


# ═══ Salary ═══════════════════════════════════════════════════════

def _get_branch_employees(branch):
    """Return all employees of a branch with their salary amount and type."""
    from staff.models import Teacher, Accountant, Employee
    employees = []

    if branch.manager:
        employees.append({
            'user': branch.manager,
            'type': 'Manager',
            'salary': branch.manager_salary or Decimal('0'),
        })

    for t in Teacher.objects.filter(branch=branch, is_active=True).select_related('user'):
        employees.append({
            'user': t.user,
            'type': 'Teacher',
            'salary': t.salary or Decimal('0'),
        })

    for a in Accountant.objects.filter(branch=branch, is_active=True).select_related('user'):
        employees.append({
            'user': a.user,
            'type': 'Accountant',
            'salary': a.salary or Decimal('0'),
        })

    for e in Employee.objects.filter(branch=branch, is_active=True).select_related('user'):
        employees.append({
            'user': e.user,
            'type': e.get_employee_type_display(),
            'salary': e.salary or Decimal('0'),
        })

    return employees


@login_required
@require_finance_access()
def salary_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    records = SalaryRecord.objects.filter(branch=branch).select_related('employee', 'paid_by')

    month_f = request.GET.get('month', '')
    year_f = request.GET.get('year', '')
    status_f = request.GET.get('status', '')

    if month_f:
        records = records.filter(month=int(month_f))
    if year_f:
        records = records.filter(year=int(year_f))
    if status_f:
        records = records.filter(status=status_f)

    total_salary = records.aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    total_paid = records.filter(status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')

    return render(request, 'finance/salary_list.html', {
        'records': records, 'branch': branch,
        'total_salary': total_salary, 'total_paid': total_paid,
        'selected_month': month_f, 'selected_year': year_f, 'selected_status': status_f,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'title': 'Salary Records',
    })


@login_required
@require_finance_access()
def generate_salary(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    if request.method == 'POST':
        form = GenerateSalaryForm(request.POST)
        if form.is_valid():
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])

            employees = _get_branch_employees(branch)
            created = 0
            skipped = 0
            with transaction.atomic():
                for emp in employees:
                    if not emp['user']:
                        continue
                    exists = SalaryRecord.objects.filter(
                        employee=emp['user'], month=month, year=year
                    ).exists()
                    if exists:
                        skipped += 1
                        continue
                    SalaryRecord.objects.create(
                        branch=branch, school=school,
                        employee=emp['user'],
                        employee_type=emp['type'],
                        salary_amount=emp['salary'],
                        month=month, year=year,
                        created_by=request.user,
                    )
                    created += 1

            msg = f'Salary records generated for {created} employee(s) for {calendar.month_name[month]} {year}.'
            if skipped:
                msg += f' {skipped} already existed and were skipped.'
            messages.success(request, msg)
            return redirect(branch_url(request, 'finance:salary_list') + f'?month={month}&year={year}')
    else:
        form = GenerateSalaryForm()

    employees = _get_branch_employees(branch)
    return render(request, 'finance/generate_salary.html', {
        'form': form, 'branch': branch, 'employees': employees,
        'title': 'Generate Salary Records',
    })


@login_required
@require_finance_access()
def edit_salary(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    record = get_object_or_404(SalaryRecord, pk=pk, branch=branch)

    if request.method == 'POST':
        form = EditSalaryForm(request.POST)
        if form.is_valid():
            record.salary_amount = form.cleaned_data['salary_amount']
            record.description = form.cleaned_data.get('description', '')
            record.save()
            messages.success(request, f'Salary record for {record.employee.full_name} updated.')
            return redirect(branch_url(request, 'finance:salary_list') + f'?month={record.month}&year={record.year}')
    else:
        form = EditSalaryForm(initial={
            'salary_amount': record.salary_amount,
            'description': record.description,
        })

    return render(request, 'finance/edit_salary.html', {
        'form': form, 'record': record, 'branch': branch,
        'title': f'Edit Salary - {record.employee.full_name}',
    })


@login_required
@require_finance_access()
def delete_salary(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    record = get_object_or_404(SalaryRecord, pk=pk, branch=branch)
    if request.method == 'POST':
        name = record.employee.full_name
        record.delete()
        messages.success(request, f'Salary record for {name} deleted.')
        return redirect(branch_url(request, 'finance:salary_list'))

    return render(request, 'finance/delete_salary.html', {
        'record': record, 'title': f'Delete Salary - {record.employee.full_name}',
    })


@login_required
@require_finance_access()
def pay_salary(request):
    """Page to pay salaries for a specific month/year. Lists all unpaid records."""
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    month = request.GET.get('month', str(timezone.now().month))
    year = request.GET.get('year', str(timezone.now().year))

    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        month = timezone.now().month
        year = timezone.now().year

    records = SalaryRecord.objects.filter(
        branch=branch, month=month, year=year
    ).select_related('employee').order_by('employee__full_name')

    if request.method == 'POST':
        salary_ids = request.POST.getlist('salary_ids')
        paid_count = 0
        with transaction.atomic():
            for sid in salary_ids:
                try:
                    rec = SalaryRecord.objects.get(pk=int(sid), branch=branch, status='unpaid')
                    rec.status = 'paid'
                    rec.payment_date = timezone.now().date()
                    rec.paid_by = request.user
                    rec.paid_by_role = request.user.get_user_type_display()
                    rec.save()
                    paid_count += 1
                except SalaryRecord.DoesNotExist:
                    continue

        messages.success(request, f'{paid_count} salary(ies) marked as paid for {calendar.month_name[month]} {year}.')
        return redirect(branch_url(request, 'finance:pay_salary') + f'?month={month}&year={year}')

    total = records.aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    paid_total = records.filter(status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    unpaid_total = records.filter(status='unpaid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')

    return render(request, 'finance/pay_salary.html', {
        'records': records, 'branch': branch,
        'month': month, 'year': year,
        'month_name': calendar.month_name[month],
        'total': total, 'paid_total': paid_total, 'unpaid_total': unpaid_total,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'title': f'Pay Salary - {calendar.month_name[month]} {year}',
    })


# ═══ Financial Reports ════════════════════════════════════════════

@login_required
@require_finance_access()
def financial_report(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return _dash()

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    fees_qs = StudentFee.objects.filter(branch=branch, is_active=True)
    expenses_qs = Expense.objects.filter(branch=branch)
    salaries_qs = SalaryRecord.objects.filter(branch=branch)

    if date_from:
        fees_qs = fees_qs.filter(due_date__gte=date_from)
        expenses_qs = expenses_qs.filter(expense_date__gte=date_from)
        salaries_qs = salaries_qs.filter(payment_date__gte=date_from)
    if date_to:
        fees_qs = fees_qs.filter(due_date__lte=date_to)
        expenses_qs = expenses_qs.filter(expense_date__lte=date_to)
        salaries_qs = salaries_qs.filter(payment_date__lte=date_to)

    total_collected = fees_qs.filter(
        status__in=['paid', 'partial']
    ).aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')

    total_pending = fees_qs.exclude(
        status='paid'
    ).aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    total_paid_towards_pending = fees_qs.exclude(
        status='paid'
    ).aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    total_pending -= total_paid_towards_pending

    total_expenses = expenses_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_salaries = salaries_qs.filter(status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    total_salaries_pending = salaries_qs.filter(status='unpaid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
    net_profit = total_collected - total_expenses - total_salaries
    total_outflow = total_expenses + total_salaries

    total_receivable = fees_qs.aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    collection_rate = (total_collected / total_receivable * 100) if total_receivable else Decimal('0')

    total_scholarship_given = fees_qs.aggregate(s=Sum('scholarship_deduction'))['s'] or Decimal('0')

    # Fee type breakdown
    academic_count = fees_qs.filter(fee_type='academic').count()
    special_count = fees_qs.filter(fee_type='special').count()
    academic_collected = fees_qs.filter(fee_type='academic', status__in=['paid', 'partial']).aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    special_collected = fees_qs.filter(fee_type='special', status__in=['paid', 'partial']).aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    academic_pending = fees_qs.filter(fee_type='academic').exclude(status='paid').aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    academic_pending -= fees_qs.filter(fee_type='academic').exclude(status='paid').aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    special_pending = fees_qs.filter(fee_type='special').exclude(status='paid').aggregate(s=Sum('net_amount'))['s'] or Decimal('0')
    special_pending -= fees_qs.filter(fee_type='special').exclude(status='paid').aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')

    # Fee status counts
    paid_count = fees_qs.filter(status='paid').count()
    partial_count = fees_qs.filter(status='partial').count()
    unpaid_count = fees_qs.filter(status='unpaid').count()

    # Expense category breakdown
    from .models import EXPENSE_CATEGORY_CHOICES
    expense_by_cat = []
    for code, label in EXPENSE_CATEGORY_CHOICES:
        amt = expenses_qs.filter(category=code).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        if amt:
            pct = (amt / total_expenses * 100) if total_expenses else Decimal('0')
            expense_by_cat.append({'category': label, 'amount': amt, 'pct': pct})
    expense_by_cat.sort(key=lambda x: x['amount'], reverse=True)

    # Salary by employee type
    salary_by_type = salaries_qs.values('employee_type').annotate(
        total=Sum('salary_amount'),
        paid=Sum('salary_amount', filter=Q(status='paid')),
        unpaid=Sum('salary_amount', filter=Q(status='unpaid')),
        count=Count('id'),
    ).order_by('-total')
    for item in salary_by_type:
        item['paid'] = item['paid'] or Decimal('0')
        item['unpaid'] = item['unpaid'] or Decimal('0')

    # Monthly trends (last 6 months)
    monthly_data = []
    now = timezone.now()
    for offset in range(5, -1, -1):
        m = now.month - offset
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        month_label = f"{calendar.month_abbr[m]} {y}"
        m_fees = StudentFee.objects.filter(branch=branch, is_active=True, due_date__month=m, due_date__year=y)
        m_income = m_fees.filter(status__in=['paid', 'partial']).aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
        m_expense = Expense.objects.filter(branch=branch, expense_date__month=m, expense_date__year=y).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        m_salary = SalaryRecord.objects.filter(branch=branch, month=m, year=y, status='paid').aggregate(s=Sum('salary_amount'))['s'] or Decimal('0')
        monthly_data.append({
            'label': month_label,
            'income': m_income,
            'expense': m_expense,
            'salary': m_salary,
            'profit': m_income - m_expense - m_salary,
        })

    # Top defaulters (students with highest unpaid balances)
    top_defaulters = (
        fees_qs.exclude(status='paid')
        .values('student__first_name', 'student__last_name', 'student__id')
        .annotate(
            balance=Sum(F('net_amount') - F('amount_paid')),
            fee_count=Count('id'),
        )
        .order_by('-balance')[:10]
    )

    return render(request, 'finance/financial_report.html', {
        'branch': branch,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'total_expenses': total_expenses,
        'total_salaries': total_salaries,
        'total_salaries_pending': total_salaries_pending,
        'total_outflow': total_outflow,
        'net_profit': net_profit,
        'total_receivable': total_receivable,
        'collection_rate': collection_rate,
        'total_scholarship_given': total_scholarship_given,
        'academic_count': academic_count,
        'special_count': special_count,
        'academic_collected': academic_collected,
        'special_collected': special_collected,
        'academic_pending': academic_pending,
        'special_pending': special_pending,
        'paid_count': paid_count,
        'partial_count': partial_count,
        'unpaid_count': unpaid_count,
        'total_fees_count': fees_qs.count(),
        'expense_by_cat': expense_by_cat,
        'salary_by_type': salary_by_type,
        'monthly_data': monthly_data,
        'top_defaulters': top_defaulters,
        'date_from': date_from, 'date_to': date_to,
        'title': 'Financial Report',
    })
