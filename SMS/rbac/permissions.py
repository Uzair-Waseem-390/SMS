"""
Centralized Permission Codes
This file defines all permission codes used throughout the system.
Using constants prevents typos and makes refactoring easier.
"""

from enum import Enum
from typing import List, Dict, Any

class Permissions(Enum):
    """
    Enumeration of all system permissions.
    Format: CATEGORY_ACTION = "category.action"
    """
    
    # Student Management
    STUDENT_VIEW = "student.view"
    STUDENT_CREATE = "student.create"
    STUDENT_EDIT = "student.edit"
    STUDENT_DELETE = "student.delete"
    STUDENT_IMPORT = "student.import"
    STUDENT_EXPORT = "student.export"
    STUDENT_ACTIVATE = "student.activate"
    STUDENT_DEACTIVATE = "student.deactivate"
    STUDENT_TRANSFER = "student.transfer"  # Move between branches
    
    # Parent Management
    PARENT_VIEW = "parent.view"
    PARENT_CREATE = "parent.create"
    PARENT_EDIT = "parent.edit"
    PARENT_LINK = "parent.link"  # Link parent to student
    
    # Academic Management
    CLASS_VIEW = "class.view"
    CLASS_CREATE = "class.create"
    CLASS_EDIT = "class.edit"
    CLASS_DELETE = "class.delete"
    SECTION_VIEW = "section.view"
    SECTION_CREATE = "section.create"
    SECTION_EDIT = "section.edit"
    SUBJECT_VIEW = "subject.view"
    SUBJECT_CREATE = "subject.create"
    SUBJECT_EDIT = "subject.edit"
    SUBJECT_ASSIGN = "subject.assign"  # Assign teacher to subject
    TIMETABLE_VIEW = "timetable.view"
    TIMETABLE_CREATE = "timetable.create"
    TIMETABLE_EDIT = "timetable.edit"
    
    # Attendance Management
    ATTENDANCE_VIEW = "attendance.view"
    ATTENDANCE_MARK = "attendance.mark"
    ATTENDANCE_EDIT = "attendance.edit"
    ATTENDANCE_REPORT = "attendance.report"
    ATTENDANCE_EXPORT = "attendance.export"
    STAFF_ATTENDANCE_VIEW = "staff.attendance.view"
    STAFF_ATTENDANCE_MARK = "staff.attendance.mark"
    
    # Finance Management
    FEE_VIEW = "fee.view"
    FEE_CREATE = "fee.create"
    FEE_EDIT = "fee.edit"
    FEE_COLLECT = "fee.collect"
    FEE_REFUND = "fee.refund"
    FEE_REPORT = "fee.report"
    EXPENSE_VIEW = "expense.view"
    EXPENSE_CREATE = "expense.create"
    EXPENSE_APPROVE = "expense.approve"
    SALARY_VIEW = "salary.view"
    SALARY_PROCESS = "salary.process"
    SALARY_APPROVE = "salary.approve"
    PAYMENT_VIEW = "payment.view"
    PAYMENT_RECEIPT = "payment.receipt"
    
    # Exam & Result Management
    EXAM_VIEW = "exam.view"
    EXAM_CREATE = "exam.create"
    EXAM_EDIT = "exam.edit"
    EXAM_PUBLISH = "exam.publish"
    RESULT_VIEW = "result.view"
    RESULT_ENTER = "result.enter"
    RESULT_EDIT = "result.edit"
    RESULT_PUBLISH = "result.publish"
    RESULT_EXPORT = "result.export"
    GRADE_VIEW = "grade.view"
    GRADE_CREATE = "grade.create"
    
    # Staff Management
    STAFF_VIEW = "staff.view"
    STAFF_CREATE = "staff.create"
    STAFF_EDIT = "staff.edit"
    STAFF_TERMINATE = "staff.terminate"
    STAFF_PROMOTE = "staff.promote"
    STAFF_SALARY_VIEW = "staff.salary.view"
    STAFF_SALARY_SET = "staff.salary.set"
    
    # Branch Management
    BRANCH_VIEW = "branch.view"
    BRANCH_CREATE = "branch.create"
    BRANCH_EDIT = "branch.edit"
    BRANCH_MANAGER_ASSIGN = "branch.manager.assign"
    BRANCH_REPORT = "branch.report"
    
    # Notification Management
    NOTIFICATION_VIEW = "notification.view"
    NOTIFICATION_CREATE = "notification.create"
    NOTIFICATION_SEND = "notification.send"
    NOTIFICATION_BROADCAST = "notification.broadcast"
    
    # Report Management
    REPORT_VIEW = "report.view"
    REPORT_GENERATE = "report.generate"
    REPORT_EXPORT = "report.export"
    REPORT_SCHEDULE = "report.schedule"
    
    # System Administration
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_ACTIVATE = "user.activate"
    USER_DEACTIVATE = "user.deactivate"
    USER_ROLE_ASSIGN = "user.role.assign"
    ROLE_VIEW = "role.view"
    ROLE_CREATE = "role.create"
    ROLE_EDIT = "role.edit"
    ROLE_DELETE = "role.delete"
    PERMISSION_ASSIGN = "permission.assign"
    AUDIT_LOG_VIEW = "audit.log.view"
    
    # Dashboard Access
    DASHBOARD_VIEW = "dashboard.view"
    DASHBOARD_PRINCIPAL = "dashboard.principal"
    DASHBOARD_MANAGER = "dashboard.manager"
    DASHBOARD_TEACHER = "dashboard.teacher"
    DASHBOARD_PARENT = "dashboard.parent"
    DASHBOARD_STUDENT = "dashboard.student"
    
    @classmethod
    def get_all_permissions(cls) -> List[str]:
        """Get all permission codes as strings."""
        return [perm.value for perm in cls]
    
    @classmethod
    def get_by_category(cls, category: str) -> List[str]:
        """Get permissions by category (first part of the code)."""
        return [perm.value for perm in cls if perm.value.startswith(f"{category}.")]
    
    @classmethod
    def get_permission_matrix(cls) -> Dict[str, List[str]]:
        """Get permissions organized by category."""
        matrix = {}
        for perm in cls:
            category = perm.value.split('.')[0]
            if category not in matrix:
                matrix[category] = []
            matrix[category].append(perm.value)
        return matrix


# Permission categories for easy access
STUDENT_PERMISSIONS = [
    Permissions.STUDENT_VIEW,
    Permissions.STUDENT_CREATE,
    Permissions.STUDENT_EDIT,
    Permissions.STUDENT_DELETE,
    Permissions.STUDENT_IMPORT,
    Permissions.STUDENT_EXPORT,
    Permissions.STUDENT_ACTIVATE,
    Permissions.STUDENT_DEACTIVATE,
    Permissions.STUDENT_TRANSFER,
]

PARENT_PERMISSIONS = [
    Permissions.PARENT_VIEW,
    Permissions.PARENT_CREATE,
    Permissions.PARENT_EDIT,
    Permissions.PARENT_LINK,
]

ACADEMIC_PERMISSIONS = [
    Permissions.CLASS_VIEW,
    Permissions.CLASS_CREATE,
    Permissions.CLASS_EDIT,
    Permissions.CLASS_DELETE,
    Permissions.SECTION_VIEW,
    Permissions.SECTION_CREATE,
    Permissions.SECTION_EDIT,
    Permissions.SUBJECT_VIEW,
    Permissions.SUBJECT_CREATE,
    Permissions.SUBJECT_EDIT,
    Permissions.SUBJECT_ASSIGN,
    Permissions.TIMETABLE_VIEW,
    Permissions.TIMETABLE_CREATE,
    Permissions.TIMETABLE_EDIT,
]

ATTENDANCE_PERMISSIONS = [
    Permissions.ATTENDANCE_VIEW,
    Permissions.ATTENDANCE_MARK,
    Permissions.ATTENDANCE_EDIT,
    Permissions.ATTENDANCE_REPORT,
    Permissions.ATTENDANCE_EXPORT,
    Permissions.STAFF_ATTENDANCE_VIEW,
    Permissions.STAFF_ATTENDANCE_MARK,
]

FINANCE_PERMISSIONS = [
    Permissions.FEE_VIEW,
    Permissions.FEE_CREATE,
    Permissions.FEE_EDIT,
    Permissions.FEE_COLLECT,
    Permissions.FEE_REFUND,
    Permissions.FEE_REPORT,
    Permissions.EXPENSE_VIEW,
    Permissions.EXPENSE_CREATE,
    Permissions.EXPENSE_APPROVE,
    Permissions.SALARY_VIEW,
    Permissions.SALARY_PROCESS,
    Permissions.SALARY_APPROVE,
    Permissions.PAYMENT_VIEW,
    Permissions.PAYMENT_RECEIPT,
]

EXAM_PERMISSIONS = [
    Permissions.EXAM_VIEW,
    Permissions.EXAM_CREATE,
    Permissions.EXAM_EDIT,
    Permissions.EXAM_PUBLISH,
    Permissions.RESULT_VIEW,
    Permissions.RESULT_ENTER,
    Permissions.RESULT_EDIT,
    Permissions.RESULT_PUBLISH,
    Permissions.RESULT_EXPORT,
    Permissions.GRADE_VIEW,
    Permissions.GRADE_CREATE,
]

STAFF_PERMISSIONS = [
    Permissions.STAFF_VIEW,
    Permissions.STAFF_CREATE,
    Permissions.STAFF_EDIT,
    Permissions.STAFF_TERMINATE,
    Permissions.STAFF_PROMOTE,
    Permissions.STAFF_SALARY_VIEW,
    Permissions.STAFF_SALARY_SET,
]

BRANCH_PERMISSIONS = [
    Permissions.BRANCH_VIEW,
    Permissions.BRANCH_CREATE,
    Permissions.BRANCH_EDIT,
    Permissions.BRANCH_MANAGER_ASSIGN,
    Permissions.BRANCH_REPORT,
]

NOTIFICATION_PERMISSIONS = [
    Permissions.NOTIFICATION_VIEW,
    Permissions.NOTIFICATION_CREATE,
    Permissions.NOTIFICATION_SEND,
    Permissions.NOTIFICATION_BROADCAST,
]

REPORT_PERMISSIONS = [
    Permissions.REPORT_VIEW,
    Permissions.REPORT_GENERATE,
    Permissions.REPORT_EXPORT,
    Permissions.REPORT_SCHEDULE,
]

SYSTEM_PERMISSIONS = [
    Permissions.USER_VIEW,
    Permissions.USER_CREATE,
    Permissions.USER_EDIT,
    Permissions.USER_ACTIVATE,
    Permissions.USER_DEACTIVATE,
    Permissions.USER_ROLE_ASSIGN,
    Permissions.ROLE_VIEW,
    Permissions.ROLE_CREATE,
    Permissions.ROLE_EDIT,
    Permissions.ROLE_DELETE,
    Permissions.PERMISSION_ASSIGN,
    Permissions.AUDIT_LOG_VIEW,
]

DASHBOARD_PERMISSIONS = [
    Permissions.DASHBOARD_VIEW,
    Permissions.DASHBOARD_PRINCIPAL,
    Permissions.DASHBOARD_MANAGER,
    Permissions.DASHBOARD_TEACHER,
    Permissions.DASHBOARD_PARENT,
    Permissions.DASHBOARD_STUDENT,
]