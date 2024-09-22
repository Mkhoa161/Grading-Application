from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.
class Assignment(models.Model):
    title = models.CharField(max_length=200, blank=False, null=False)
    description = models.TextField(blank=True, null=False)
    deadline = models.DateTimeField(blank=True, null=False)
    weight = models.IntegerField(blank=False, null=False)
    points = models.IntegerField(blank=True, null=False)


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    grader = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, related_name='graded_set') #TODO: will consider to change null
    file = models.FileField(null=False)
    score = models.FloatField(null=True, blank=True) #TODO: will consider to change null
