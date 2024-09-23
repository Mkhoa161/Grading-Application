from . import models
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User


# Create your views here.
def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", context={'assignments': assignments})

def assignment(request, assignment_id):
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    submission_count = assignment.submission_set.count()
    graded_count = request.user.graded_set.filter(assignment=assignment).count()
    total_student = models.Group.objects.get(name="Students").user_set.count()
    return render(request, "assignment.html", context={'assignment': assignment, 'submission_count': submission_count, 'graded_count': graded_count, 'total_student': total_student})

def submissions(request, assignment_id):
    assignment = get_object_or_404(models.Assignment, id=assignment_id)
    return render(request, "submissions.html", context={'assignment': assignment, 'submission_set': assignment.submission_set.filter(grader__username='g').order_by('author__username')})

def profile(request):
    g = User.objects.get(username='g')
    assignments = models.Assignment.objects.all()
    assignment_info = []
    for assignment in assignments:
        assignment_info.append((assignment.id, assignment.title, g.graded_set.filter(assignment=assignment, score__isnull=False).count(), g.graded_set.filter(assignment=assignment).count())) 
    
    return render(request, "profile.html", context={'assignment_info': assignment_info})

def login_form(request):
    return render(request, "login.html")