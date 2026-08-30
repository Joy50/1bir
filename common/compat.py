from django.db import models


def make_check_constraint(expression, name):
    """Build a CheckConstraint for Django 4.x (check=) and 5.1+ (condition=)."""
    try:
        return models.CheckConstraint(check=expression, name=name)
    except TypeError:
        return models.CheckConstraint(condition=expression, name=name)
