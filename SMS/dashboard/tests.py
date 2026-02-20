from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from tenants.models import SchoolTenant, Branch
from students.models import Student
from academics.models import Class, Section
from dashboard.services.principal import PrincipalDashboardService
from dashboard.services.manager import ManagerDashboardService

class DashboardTests(TestCase):
    def setUp(self):
        # Create Tenant
        self.user = CustomUser.objects.create_user(email='principal@test.com', password='password', user_type='principal')
        self.school = SchoolTenant.objects.create(name="Test School", owner=self.user, email="school@test.com")
        
        # Create Branch
        self.manager = CustomUser.objects.create_user(email='manager@test.com', password='password', user_type='manager')
        self.branch = Branch.objects.create(
            name="Main Branch", school=self.school, city="Test City", 
            manager=self.manager, email="branch@test.com"
        )
        self.manager.managed_branch = self.branch
        self.manager.save()
        
        # Create Class/Section/Student
        self.cls = Class.objects.create(name="Grade 1", branch=self.branch)
        self.section = Section.objects.create(name="A", class_obj=self.cls)
        self.student = Student.objects.create(
            first_name="John", last_name="Doe", 
            admission_number="123", section=self.section,
            is_active=True
        )
        
        self.client = Client()

    def test_principal_service_kpis(self):
        """Test Principal Dashboard Service Data"""
        service = PrincipalDashboardService(self.user)
        context = service.get_context()
        self.assertEqual(context['kpis']['total_students'], 1)
        self.assertEqual(context['school'], self.school)

    def test_manager_service_kpis(self):
        """Test Manager Dashboard Service Data"""
        service = ManagerDashboardService(self.manager)
        context = service.get_context()
        # Admissions this month check (student created today)
        self.assertEqual(context['kpis']['admissions_this_month'], 1) 
        self.assertEqual(context['branch'], self.branch)

    def test_dashboard_view_principal(self):
        """Test View resolves correct template and service for Principal"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
        self.assertContains(response, 'Principal Dashboard')
        self.assertContains(response, 'Total Students') # KPI label

    def test_dashboard_view_manager(self):
        """Test View resolves correct template and service for Manager"""
        self.client.force_login(self.manager)
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manager Dashboard')
        self.assertContains(response, 'Admissions This Month')

