from django.http import HttpResponse, HttpResponseBadRequest
from . import models
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.exceptions import PermissionDenied
from django.http import Http404

# Create your views here.
@login_required
def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", context={'assignments': assignments})

@login_required
def assignment(request, assignment_id):
    if request.method == "POST":
        assignment = get_object_or_404(models.Assignment, id=assignment_id)
        file = request.FILES.get('uploaded_file')
        if not file:
            return redirect(f"/{assignment_id}/")
        
        if file.size > 64 * 1024 * 1024: #64 MiB
            error = "The file size is too large."
            return redirect(f"/{assignment_id}/?error={error}")
        
        try:
            student_submission = assignment.submission_set.get(author__username=request.user.username)
        except ObjectDoesNotExist:
            student_submission = None
        
        if assignment.deadline < timezone.now():
            return HttpResponseBadRequest("The deadline for submitting this assignment has passed")
        
        if not is_pdf(file):
            error = 'The file type is not pdf.'
            return redirect(f"/{assignment_id}/?error={error}")

        if student_submission:
            student_submission.file = file
            student_submission.save()
        else:
            grader = pick_grader(assignment)
            student_submission = models.Submission(assignment=assignment, author=models.User.objects.get(username=request.user.username), grader=grader, file=file, score=None)
            student_submission.save()
        
        return redirect(f"/{assignment_id}/")

    is_stu = is_student(request.user)
    is_ta = is_TA(request.user)
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    submission_count = assignment.submission_set.count()
    graded_count = None
    if request.user.is_authenticated:
        graded_count = request.user.graded_set.filter(assignment=assignment).count()

    total_student = models.Group.objects.get(name="Students").user_set.count()
    try:
        student_submission = assignment.submission_set.get(author__username=request.user.username)
    except ObjectDoesNotExist:
        student_submission = None
    
    is_passed = assignment.deadline < timezone.now()
    percentage_score = 0
    if student_submission and student_submission.score:
        percentage_score = 100 * student_submission.score / assignment.points
    
    error = request.GET.get('error', None)
    
    return render(request, "assignment.html", context={'is_superuser': request.user.is_superuser, 'is_authenticated': request.user.is_authenticated, 'is_TA': is_ta, 'is_student': is_stu, 
                                                       'assignment': assignment, 'submission_count': submission_count, 'graded_count': graded_count, 'total_student': total_student, 
                                                       'student_submission': student_submission, 'is_passed': is_passed, 'percentage_score': percentage_score, 'error': error})

@login_required
def submissions(request, assignment_id):
    errors = {}
    isInvalidID = False
    if request.method == "POST":
        errors, isInvalidID = updateGrades(request.POST, assignment_id, request.user)
        if (not errors) and (not isInvalidID):
            return redirect(f"/{assignment_id}/submissions")
    
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    submission_set = []

    is_ta = is_TA(request.user)
    if is_ta:
        for submission in assignment.submission_set.filter(grader__username=request.user.username).order_by('author__username'):
            errors_submission = errors.get(submission.id, [])
            submission_set.append((submission, errors_submission))
    
    elif request.user.is_superuser:
        for submission in assignment.submission_set.all():
            errors_submission = errors.get(submission.id, [])
            submission_set.append((submission, errors_submission))
    else:
        raise PermissionDenied("You do not have permission to access this page.")
    
    return render(request, "submissions.html", context={'is_superuser': request.user.is_superuser, 'is_TA': is_ta,'assignment': assignment, 'submission_set': submission_set, 'is_invalid_id': isInvalidID})

@login_required
def profile(request):
    user = request.user
    assignments = models.Assignment.objects.all()
    assignment_info = []
    student_info = []
    percentage_grade = 0
    total_score = 0
    available_grade = 0
    for assignment in assignments:
        graded_count = None
        total_submission_count = None
        is_ta, is_stu, is_sup = False, False, False
        if is_TA(user):
            graded_count = user.graded_set.filter(assignment=assignment, score__isnull=False).count()
            total_submission_count = user.graded_set.filter(assignment=assignment).count()
            is_ta = True
        elif user.is_superuser:
            graded_count = assignment.submission_set.filter(score__isnull=False).count()
            total_submission_count = assignment.submission_set.count()
            is_sup = True
        elif is_student(user):
            is_passed = assignment.deadline < timezone.now()
            is_stu = True
            state = 'state'
            if is_passed:
                try:
                    submission = assignment.submission_set.get(author=user)
                except models.Submission.DoesNotExist:
                    submission = None

                if submission:
                    if submission.score:
                        available_grade += assignment.weight
                        percentage_grade = submission.score / assignment.points
                        total_score += percentage_grade * assignment.weight
                        state = 'Graded'
                    else:
                        state = 'Ungraded'
                else:
                    state = 'Missing'
                    available_grade += assignment.weight
            else:
                state = 'Not Due'
            
            student_info.append((assignment.id, assignment.title, 100 * percentage_grade, state))

        assignment_info.append((assignment.id, assignment.title, graded_count, total_submission_count))
    
    if available_grade != 0:
        final_grade = 100 * total_score / available_grade
    else:
        final_grade = 100
    
    return render(request, "profile.html", context={'is_student': is_stu, 'is_TA': is_ta, 'is_superuser': is_sup, 'assignment_info': assignment_info, 'user': request.user, 'student_info': student_info, 'final_grade': final_grade})

def login_form(request):
    if request.method == "POST":
        data = request.POST
        next = data.get("next", "")
        username = data.get("username", "")
        password = data.get("password", "")

        user = authenticate(username=username, password=password)
        if user is not None and url_has_allowed_host_and_scheme(next, None):
            login(request, user)
            if (len(next) > 1):
                next = next.rstrip('/')

            return redirect(next)
        else:
            next = next.rstrip('/')
            error = 'Username and password do not match'
            return render(request, "login.html", {'next': next, 'error': error})

    next = request.GET.get("next", "/profile/")
    next = next.rstrip('/')
    return render(request, "login.html", {'next': next})

def logout_form(request):
    logout(request)
    return redirect("/profile/login/")

@login_required
def show_upload(request, filename):
    submission = models.Submission.objects.get(file__iexact=filename)
    if not is_pdf(submission.file):
        raise Http404("This file can be dangerous.")
    
    http_response = HttpResponse(submission.view_submission(request.user).open())
    http_response['Content-Type'] = 'application/pdf'
    http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return http_response

def updateGrades(data, assignment_id, user):
    errors = {}
    isInvalidID = False
    for key in data:
        if key.startswith("grade-"):
            # Look up the Submission using the ID
            try:
                submission_id = int(key.removeprefix("grade-"))
                submission = models.Submission.objects.get(id=submission_id, assignment__id = assignment_id)
            except (ValueError, models.Submission.DoesNotExist):
                isInvalidID = True
                continue

            grade = data[key]

            if grade == "":
                submission.change_grade(user, None)
            else:
                isValid, message = validate_grade(grade, submission)
                if isValid:
                    submission.change_grade(user, float(grade))
                else:
                    errors.setdefault(submission_id, []).append(message)

            submission.save()  # Save the updated submission
    return errors, isInvalidID

def validate_grade(grade, submission):
    try:
        float_grade = float(grade)

        if 0 <= float_grade <= submission.assignment.points:
            return True, None
    
        else:
            return False, f"Grade must be between 0 and {submission.assignment.points}"
    
    except ValueError:
        return False, f"{grade} is invalid. Please enter a number!"
            
def is_student(user):
    return user.groups.filter(name="Students").exists()

def is_TA(user):
    return user.groups.filter(name="Teaching Assistants").exists()

def pick_grader(assignment):
    tas = models.Group.objects.get(name='Teaching Assistants')
    graders = tas.user_set.annotate(total_assigned=Count('graded_set'))
    grader = graders.order_by('total_assigned').first()
    return grader

def is_pdf(file):
    return file.name.endswith('.pdf') and next(file.chunks()).startswith(b'%PDF-')
