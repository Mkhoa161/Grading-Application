from django.http import HttpResponse
from . import models
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

# Create your views here.
def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", context={'assignments': assignments})

def assignment(request, assignment_id):
    if request.method == "POST":
        assignment = get_object_or_404(models.Assignment, id=assignment_id)
        file = request.FILES.get('uploaded_file')
        try:
            alice_submission = assignment.submission_set.get(author__username="a")
        except ObjectDoesNotExist:
            alice_submission = None
        
        if alice_submission:
            alice_submission.file = file
            alice_submission.save()
        else:
            alice_submission = models.Submission(assignment=assignment, author=models.User.objects.get(username="a"), grader=models.User.objects.get(username="g"), file=file, score=None)
            alice_submission.save()
        
        return redirect(f"/{assignment_id}/")

    g = User.objects.get(username='g')
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    submission_count = assignment.submission_set.count()
    graded_count = g.graded_set.filter(assignment=assignment).count()
    total_student = models.Group.objects.get(name="Students").user_set.count()
    try:
        alice_submission = assignment.submission_set.get(author__username="a")
    except ObjectDoesNotExist:
        alice_submission = None

    return render(request, "assignment.html", context={'assignment': assignment, 'submission_count': submission_count, 'graded_count': graded_count, 'total_student': total_student, 'alice_submission': alice_submission})

def submissions(request, assignment_id):
    errors = {}
    isInvalidID = False
    if request.method == "POST":
        errors, isInvalidID = updateGrades(request.POST, assignment_id)
        if (not errors) and (not isInvalidID):
            return redirect(f"/{assignment_id}/submissions")
    
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    submission_set = []
    for submission in assignment.submission_set.filter(grader__username='g').order_by('author__username'):
        errors_submission = errors.get(submission.id, [])
        submission_set.append((submission, errors_submission))

    return render(request, "submissions.html", context={'assignment': assignment, 'submission_set': submission_set, 'is_invalid_id': isInvalidID})

def profile(request):
    g = User.objects.get(username='g')
    assignments = models.Assignment.objects.all()
    assignment_info = []
    for assignment in assignments:
        assignment_info.append((assignment.id, assignment.title, g.graded_set.filter(assignment=assignment, score__isnull=False).count(), g.graded_set.filter(assignment=assignment).count())) 
    
    return render(request, "profile.html", context={'assignment_info': assignment_info})

def login_form(request):
    return render(request, "login.html")

def show_upload(request, filename):
    submission = models.Submission.objects.get(file__iexact=filename)
    return HttpResponse(submission.file.open())

def updateGrades(data, assignment_id):
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
                submission.score = None
            else:
                isValid, message = validate_grade(grade, submission)
                if isValid:
                    submission.score = float(grade)
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
            
            
