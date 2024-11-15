from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied

# Create your models here.
class Assignment(models.Model):
    title = models.CharField(max_length=200, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)
    weight = models.IntegerField(blank=False, null=False, default=1)
    points = models.IntegerField(blank=False, null=False, default=100)


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    grader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='graded_set')
    file = models.FileField(null=False)
    score = models.FloatField(null=True, blank=True)

    def change_grade(self, user, new_score):
        if not user == self.grader and not user.is_superuser:
            raise PermissionDenied("You do not have permission to change grade.")
        
        self.score = new_score

    def view_submission(self, user):
        if not user == self.author and not user == self.grader and not user.is_superuser:
            raise PermissionDenied("You do not have permission to view the submission")
        
        return self.file

