from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .base import BaseDashboardService
from finance.models import StudentFee, Expense, SalaryRecord
import datetime

class AccountantDashboardService(BaseDashboardService):
    def _get_kpis(self):
        branch = self.branch
        if not branch:
            return {}
            
        fee_filter = {'branch': branch, 'status': 'paid'}
        expense_filter = {'branch': branch}
        salary_filter = {'branch': branch, 'status': 'paid'}

        # 1. Fee Collected Today
        today_collection = StudentFee.objects.filter(
            paid_date=self.today,
            **fee_filter
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        # 2. Fee Collected This Month
        month_collection = StudentFee.objects.filter(
            paid_date__month=self.current_month,
            paid_date__year=self.current_year,
            **fee_filter
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        # 3. Pending Dues
        pending_dues = StudentFee.objects.filter(
            branch=branch,
            status__in=['unpaid', 'partial']
        ).aggregate(
            total_net=Sum('net_amount'),
            total_paid=Sum('amount_paid')
        )
        total_pending = (pending_dues['total_net'] or 0) - (pending_dues['total_paid'] or 0)

        # 4. Monthly Expenses
        monthly_expenses = Expense.objects.filter(
            expense_date__month=self.current_month,
            expense_date__year=self.current_year,
            **expense_filter
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 5. Net Balance (Approximation for this month)
        # Income = Fees
        # Outflow = Expenses + Salaries
        monthly_salaries = SalaryRecord.objects.filter(
            payment_date__month=self.current_month,
            payment_date__year=self.current_year,
            **salary_filter
        ).aggregate(total=Sum('salary_amount'))['total'] or 0
        
        net_balance = month_collection - (monthly_expenses + monthly_salaries)

        return {
            'today_collection': today_collection,
            'month_collection': month_collection,
            'pending_dues': total_pending,
            'monthly_expenses': monthly_expenses,
            'net_balance': net_balance,
        }

    def _get_charts(self):
        branch = self.branch
        if not branch:
            return {}
            
        charts = {}
        
        # Chart 1: Income vs Expense (Last 6 Months)
        six_months_ago = self.today - datetime.timedelta(days=180)
        
        # Income
        income_trend = StudentFee.objects.filter(
            branch=branch,
            paid_date__gte=six_months_ago,
            status='paid'
        ).annotate(
            month=TruncMonth('paid_date')
        ).values('month').annotate(
            total=Sum('amount_paid')
        ).order_by('month')
        
        # Expense
        expense_trend = Expense.objects.filter(
            branch=branch,
            expense_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('expense_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # Merge data (basic approach)
        labels = sorted(list(set(
            [item['month'].strftime('%b %Y') for item in income_trend] + 
            [item['month'].strftime('%b %Y') for item in expense_trend]
        )))
        
        income_data = {item['month'].strftime('%b %Y'): float(item['total']) for item in income_trend}
        expense_data = {item['month'].strftime('%b %Y'): float(item['total']) for item in expense_trend}
        
        charts['financial_trend'] = {
            'labels': labels,
            'income': [income_data.get(label, 0) for label in labels],
            'expense': [expense_data.get(label, 0) for label in labels],
        }
        
        # Chart 2: Payment Status Breakdown
        status_counts = StudentFee.objects.filter(
            branch=branch
        ).values('status').annotate(
            count=Count('id')
        )
        
        charts['payment_status'] = {
            'labels': [item['status'].title() for item in status_counts],
            'data': [item['count'] for item in status_counts]
        }
        
        return charts

    def _get_tables(self):
        branch = self.branch
        if not branch:
            return {}
            
        # Recent Transactions
        recent_transactions = StudentFee.objects.filter(
            branch=branch,
            status='paid'
        ).select_related('student').order_by('-paid_date')[:10]
        
        # Top Defaulters
        defaulters = StudentFee.objects.filter(
            branch=branch,
            status__in=['unpaid', 'partial']
        ).select_related('student').annotate(
            balance=F('net_amount') - F('amount_paid')
        ).order_by('-balance')[:10]
        
        return {
            'recent_transactions': recent_transactions,
            'top_defaulters': defaulters,
        }
