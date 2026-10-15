from apps.academics.models import (
    AdvisorAssignment,
    Course,
    EligibilityPolicy,
    Enrollment,
    Term,
)
from apps.accounts.models import User


def get_current_term() -> Term | None:
    return Term.objects.filter(is_current=True).first()


def get_courses_for_teacher(teacher: User) -> list[Course]:
    return list(
        Course.objects.filter(teacher=teacher).select_related("term", "default_room")
    )


def get_enrollments_for_course(course: Course) -> list[Enrollment]:
    return list(Enrollment.objects.filter(course=course).select_related("student"))


def get_enrollments_for_student(student: User) -> list[Enrollment]:
    return list(Enrollment.objects.filter(student=student).select_related("course__term"))


def get_advisees_for_advisor(advisor: User) -> list[User]:
    assignments = AdvisorAssignment.objects.filter(advisor=advisor).select_related("student")
    return [assignment.student for assignment in assignments]


def get_advisors_for_student(student: User) -> list[User]:
    assignments = AdvisorAssignment.objects.filter(student=student).select_related("advisor")
    return [assignment.advisor for assignment in assignments]


def get_eligibility_policy_for_course(course: Course) -> EligibilityPolicy:
    policy = EligibilityPolicy.objects.filter(course=course).first()
    if policy:
        return policy
    return EligibilityPolicy.objects.filter(course__isnull=True).first()


def get_eligibility_policies() -> list[EligibilityPolicy]:
    return list(EligibilityPolicy.objects.all().select_related("course"))
