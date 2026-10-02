from django.core.management.base import BaseCommand

from common.forms import PersonForm


class Command(BaseCommand):
    help = "Verify enlist form uses structured present/permanent address fields."

    def handle(self, *args, **options):
        fields = PersonForm().fields
        if "present_district" in fields:
            self.stdout.write(
                self.style.SUCCESS(
                    "Structured address form is active "
                    "(District, Upazila, Thana, Area/Road/House)."
                )
            )
            return
        if "present_address" in fields:
            self.stdout.write(
                self.style.ERROR(
                    "Old address form still active (present_address textarea). "
                    "Run: git pull origin main && python manage.py migrate common"
                )
            )
            return
        self.stdout.write(self.style.WARNING("Unexpected PersonForm address fields."))
