
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tickets.models import BusOperator

class Command(BaseCommand):
    help = 'Creates user accounts for bus operators'

    def handle(self, *args, **kwargs):
        for operator in BusOperator.objects.filter(user__isnull=True):
            # Create user for each bus operator
            username = operator.name.replace(' ', '_').lower()
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password('password123')  # Set a default password (should be changed later)
                user.save()
                operator.user = user
                operator.save()
                self.stdout.write(f"Created user for bus operator: {operator.name}")
            else:
                self.stdout.write(f"User already exists for bus operator: {operator.name}")
