"""
Management command to seed initial RBAC data.

Usage:
    python manage.py seed_rbac
    python manage.py seed_rbac --tenant-id 3
    python manage.py seed_rbac --force
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from tenants.models import SchoolTenant
from rbac.models import Role, Permission, RolePermission
# 'get_all_permission_codes' does not exist — removed from import. (Error #14)
# Use the classmethod Permissions.get_all_permissions() instead.
from rbac.permissions import Permissions

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed default roles and permissions for the RBAC system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='Seed for a specific tenant (optional)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update / replace existing role-permission assignments',
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        force = options.get('force', False)

        self.stdout.write(self.style.SUCCESS('Starting RBAC seeding...'))

        if tenant_id:
            try:
                tenant = SchoolTenant.objects.get(id=tenant_id)
                self.seed_for_tenant(tenant, force)
            except SchoolTenant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Tenant with id {tenant_id} not found')
                )
                return
        else:
            self.seed_all(force)

        self.stdout.write(self.style.SUCCESS('RBAC seeding completed successfully!'))

    @transaction.atomic
    def seed_all(self, force=False):
        """Seed for all tenants and create system-wide records."""
        self.create_permissions(force)
        self.create_system_roles()

        for tenant in SchoolTenant.objects.all():
            self.seed_for_tenant(tenant, force)

    # ─────────────────────────────────────────────────────────────
    # Permissions
    # ─────────────────────────────────────────────────────────────

    def create_permissions(self, force=False):
        """Upsert every permission record derived from the permission matrix."""
        self.stdout.write('Creating permissions...')

        permission_matrix = {
            'student': {
                'view': 'View student details',
                'create': 'Create new students',
                'edit': 'Edit student information',
                'delete': 'Delete students',
                'import': 'Import students from file',
                'export': 'Export student data',
                'activate': 'Activate students',
                'deactivate': 'Deactivate students',
                'transfer': 'Transfer students between branches',
            },
            'parent': {
                'view': 'View parent details',
                'create': 'Create parent accounts',
                'edit': 'Edit parent information',
                'link': 'Link parents to students',
            },
            'class': {
                'view': 'View classes',
                'create': 'Create classes',
                'edit': 'Edit classes',
                'delete': 'Delete classes',
            },
            'section': {
                'view': 'View sections',
                'create': 'Create sections',
                'edit': 'Edit sections',
                'delete': 'Delete sections',
            },
            'subject': {
                'view': 'View subjects',
                'create': 'Create subjects',
                'edit': 'Edit subjects',
                'delete': 'Delete subjects',
                'assign': 'Assign teachers to subjects',
            },
            'timetable': {
                'view': 'View timetables',
                'create': 'Create timetables',
                'edit': 'Edit timetables',
            },
            'attendance': {
                'view': 'View attendance',
                'mark': 'Mark attendance',
                'edit': 'Edit attendance',
                'report': 'Generate attendance reports',
                'export': 'Export attendance data',
            },
            'fee': {
                'view': 'View fees',
                'create': 'Create fee structures',
                'edit': 'Edit fees',
                'collect': 'Collect payments',
                'refund': 'Process refunds',
                'report': 'Generate fee reports',
            },
            'expense': {
                'view': 'View expenses',
                'create': 'Create expenses',
                'approve': 'Approve expenses',
            },
            'salary': {
                'view': 'View salaries',
                'process': 'Process salary payments',
                'approve': 'Approve salary sheets',
            },
            'payment': {
                'view': 'View payments',
                'receipt': 'Generate receipts',
            },
            'exam': {
                'view': 'View exams',
                'create': 'Create exams',
                'edit': 'Edit exams',
                'publish': 'Publish exam schedules',
            },
            'result': {
                'view': 'View results',
                'enter': 'Enter marks',
                'edit': 'Edit results',
                'publish': 'Publish results',
                'export': 'Export results',
            },
            'grade': {
                'view': 'View grades',
                'create': 'Create grade scales',
            },
            'staff': {
                'view': 'View staff',
                'create': 'Create staff',
                'edit': 'Edit staff',
                'terminate': 'Terminate staff',
                'promote': 'Promote staff',
                'attendance.view': 'View staff attendance',
                'attendance.mark': 'Mark staff attendance',
                'attendance.edit': 'Edit staff attendance',
                'salary.view': 'View individual staff salary',
                'salary.set': 'Set individual staff salary',
            },
            'branch': {
                'view': 'View branches',
                'create': 'Create branches',
                'edit': 'Edit branches',
                'manager.assign': 'Assign branch managers',
                'report': 'Generate branch reports',
            },
            'notification': {
                'view': 'View notifications',
                'create': 'Create notifications',
                'send': 'Send notifications',
                'broadcast': 'Broadcast to all users',
            },
            'report': {
                'view': 'View reports',
                'generate': 'Generate reports',
                'export': 'Export reports',
                'schedule': 'Schedule reports',
            },
            'user': {
                'view': 'View users',
                'create': 'Create users',
                'edit': 'Edit users',
                'activate': 'Activate users',
                'deactivate': 'Deactivate users',
                'role.assign': 'Assign roles to users',
            },
            'role': {
                'view': 'View roles',
                'create': 'Create roles',
                'edit': 'Edit roles',
                'delete': 'Delete roles',
            },
            'permission': {
                'assign': 'Assign permissions to roles',
            },
            'audit': {
                'log.view': 'View audit logs',
            },
            'dashboard': {
                'view': 'View dashboard',
                'principal': 'Access principal dashboard',
                'manager': 'Access manager dashboard',
                'teacher': 'Access teacher dashboard',
                'parent': 'Access parent dashboard',
                'student': 'Access student dashboard',
            },
        }

        created_count = 0
        updated_count = 0

        for category, actions in permission_matrix.items():
            for action, description in actions.items():
                code = f"{category}.{action}"
                name = ' '.join(
                    [category.capitalize(), action.replace('_', ' ').replace('.', ' ').capitalize()]
                )

                _, created = Permission.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'description': description,
                        'category': category,
                        'is_active': True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Permissions — created: {created_count}, updated: {updated_count}'
            )
        )

    # ─────────────────────────────────────────────────────────────
    # System roles
    # ─────────────────────────────────────────────────────────────

    def create_system_roles(self):
        """Create (or update) system-wide roles that belong to no tenant."""
        self.stdout.write('Creating system roles...')

        Role.objects.update_or_create(
            name='superadmin',
            tenant=None,
            defaults={
                'display_name': 'Super Administrator',
                'level_rank': 0,   # outranks all tenant roles
                'is_system_role': True,
                'description': 'System-wide administrator with all permissions',
            },
        )
        self.stdout.write('  Created / updated superadmin role')

    # ─────────────────────────────────────────────────────────────
    # Per-tenant seeding
    # ─────────────────────────────────────────────────────────────

    def seed_for_tenant(self, tenant, force=False):
        """Create roles and assign permissions for one tenant."""
        self.stdout.write(f'Seeding tenant: {tenant.name} (ID: {tenant.id})')

        role_definitions = [
            {
                'name': 'principal',
                'display_name': 'Principal',
                'level_rank': 1,
                'description': 'School owner with full control over the tenant',
            },
            {
                'name': 'manager',
                'display_name': 'Branch Manager',
                'level_rank': 2,
                'description': 'Manages day-to-day operations of a branch',
            },
            {
                'name': 'accountant',
                'display_name': 'Accountant',
                'level_rank': 3,
                'description': 'Handles financial transactions and records',
            },
            {
                'name': 'teacher',
                'display_name': 'Teacher',
                'level_rank': 4,
                'description': 'Manages classes, attendance, and grades',
            },
            {
                'name': 'employee',
                'display_name': 'Employee',
                'level_rank': 5,
                'description': 'Non-teaching staff member',
            },
            {
                'name': 'parent',
                'display_name': 'Parent',
                'level_rank': 6,
                'description': 'Parent or guardian of students',
            },
            {
                'name': 'student',
                'display_name': 'Student',
                'level_rank': 7,
                'description': 'Enrolled student',
            },
        ]

        roles = {}
        for role_def in role_definitions:
            role, created = Role.objects.update_or_create(
                name=role_def['name'],
                tenant=tenant,
                defaults={
                    'display_name': role_def['display_name'],
                    'level_rank': role_def['level_rank'],
                    'description': role_def['description'],
                    'is_system_role': False,
                },
            )
            roles[role_def['name']] = role
            if created:
                self.stdout.write(f"  Created role: {role.display_name}")

        self.assign_role_permissions(tenant, roles, force)

    def assign_role_permissions(self, tenant, roles, force=False):
        """Bulk-assign permissions to roles according to the permission matrix."""
        self.stdout.write('  Assigning permissions to roles...')

        all_permissions = [p.value for p in Permissions]  # replaces missing helper

        permission_matrix = {
            'principal': all_permissions,   # full access
            'manager': [
                # Students
                Permissions.STUDENT_VIEW.value,
                Permissions.STUDENT_CREATE.value,
                Permissions.STUDENT_EDIT.value,
                Permissions.STUDENT_ACTIVATE.value,
                Permissions.STUDENT_DEACTIVATE.value,
                Permissions.STUDENT_TRANSFER.value,
                Permissions.STUDENT_EXPORT.value,
                # Parents
                Permissions.PARENT_VIEW.value,
                Permissions.PARENT_CREATE.value,
                Permissions.PARENT_EDIT.value,
                Permissions.PARENT_LINK.value,
                # Academic
                Permissions.CLASS_VIEW.value,
                Permissions.CLASS_CREATE.value,
                Permissions.CLASS_EDIT.value,
                Permissions.CLASS_DELETE.value,
                Permissions.SECTION_VIEW.value,
                Permissions.SECTION_CREATE.value,
                Permissions.SECTION_EDIT.value,
                Permissions.SECTION_DELETE.value,
                Permissions.SUBJECT_VIEW.value,
                Permissions.SUBJECT_CREATE.value,
                Permissions.SUBJECT_EDIT.value,
                Permissions.SUBJECT_DELETE.value,
                Permissions.SUBJECT_ASSIGN.value,
                Permissions.TIMETABLE_VIEW.value,
                Permissions.TIMETABLE_CREATE.value,
                Permissions.TIMETABLE_EDIT.value,
                # Attendance
                Permissions.ATTENDANCE_VIEW.value,
                Permissions.ATTENDANCE_MARK.value,
                Permissions.ATTENDANCE_EDIT.value,
                Permissions.ATTENDANCE_REPORT.value,
                Permissions.ATTENDANCE_EXPORT.value,
                Permissions.STAFF_ATTENDANCE_VIEW.value,
                Permissions.STAFF_ATTENDANCE_MARK.value,
                Permissions.STAFF_ATTENDANCE_EDIT.value,
                # Staff
                Permissions.STAFF_VIEW.value,
                Permissions.STAFF_CREATE.value,
                Permissions.STAFF_EDIT.value,
                # Branch
                Permissions.BRANCH_VIEW.value,
                Permissions.BRANCH_REPORT.value,
                # Notifications
                Permissions.NOTIFICATION_VIEW.value,
                Permissions.NOTIFICATION_CREATE.value,
                Permissions.NOTIFICATION_SEND.value,
                Permissions.NOTIFICATION_BROADCAST.value,
                # Reports
                Permissions.REPORT_VIEW.value,
                Permissions.REPORT_GENERATE.value,
                Permissions.REPORT_EXPORT.value,
                # Dashboard
                Permissions.DASHBOARD_VIEW.value,
                Permissions.DASHBOARD_MANAGER.value,
            ],
            'accountant': [
                Permissions.FEE_VIEW.value,
                Permissions.FEE_CREATE.value,
                Permissions.FEE_EDIT.value,
                Permissions.FEE_COLLECT.value,
                Permissions.FEE_REFUND.value,
                Permissions.FEE_REPORT.value,
                Permissions.EXPENSE_VIEW.value,
                Permissions.EXPENSE_CREATE.value,
                Permissions.SALARY_VIEW.value,
                Permissions.SALARY_PROCESS.value,
                Permissions.PAYMENT_VIEW.value,
                Permissions.PAYMENT_RECEIPT.value,
                Permissions.STUDENT_VIEW.value,
                Permissions.REPORT_VIEW.value,
                Permissions.REPORT_GENERATE.value,
                Permissions.REPORT_EXPORT.value,
                Permissions.DASHBOARD_VIEW.value,
            ],
            'teacher': [
                Permissions.STUDENT_VIEW.value,
                Permissions.ATTENDANCE_VIEW.value,
                Permissions.ATTENDANCE_MARK.value,
                Permissions.ATTENDANCE_EDIT.value,
                Permissions.CLASS_VIEW.value,
                Permissions.SECTION_VIEW.value,
                Permissions.SUBJECT_VIEW.value,
                Permissions.TIMETABLE_VIEW.value,
                Permissions.EXAM_VIEW.value,
                Permissions.RESULT_VIEW.value,
                Permissions.RESULT_ENTER.value,
                Permissions.NOTIFICATION_VIEW.value,
                Permissions.NOTIFICATION_CREATE.value,
                Permissions.NOTIFICATION_SEND.value,
                Permissions.DASHBOARD_VIEW.value,
                Permissions.DASHBOARD_TEACHER.value,
            ],
            'employee': [
                Permissions.STUDENT_VIEW.value,
                Permissions.CLASS_VIEW.value,
                Permissions.STAFF_ATTENDANCE_VIEW.value,
                Permissions.STAFF_ATTENDANCE_MARK.value,
                Permissions.NOTIFICATION_VIEW.value,
                Permissions.DASHBOARD_VIEW.value,
            ],
            'parent': [
                Permissions.STUDENT_VIEW.value,
                Permissions.ATTENDANCE_VIEW.value,
                Permissions.RESULT_VIEW.value,
                Permissions.FEE_VIEW.value,
                Permissions.NOTIFICATION_VIEW.value,
                Permissions.DASHBOARD_VIEW.value,
                Permissions.DASHBOARD_PARENT.value,
            ],
            'student': [
                Permissions.STUDENT_VIEW.value,
                Permissions.ATTENDANCE_VIEW.value,
                Permissions.RESULT_VIEW.value,
                Permissions.CLASS_VIEW.value,
                Permissions.SUBJECT_VIEW.value,
                Permissions.TIMETABLE_VIEW.value,
                Permissions.NOTIFICATION_VIEW.value,
                Permissions.DASHBOARD_VIEW.value,
                Permissions.DASHBOARD_STUDENT.value,
            ],
        }

        if force:
            RolePermission.objects.filter(role__tenant=tenant).delete()

        assigned_count = 0
        for role_name, permission_codes in permission_matrix.items():
            role = roles.get(role_name)
            if not role:
                continue

            for code in permission_codes:
                try:
                    permission = Permission.objects.get(code=code, is_active=True)
                    _, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                    )
                    if created:
                        assigned_count += 1
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    Permission not found, skipping: {code}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'  Assigned {assigned_count} new permissions to roles')
        )