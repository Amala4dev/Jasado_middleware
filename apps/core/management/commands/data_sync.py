from django.core.management.base import BaseCommand
from apps.core.views import run_automations


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        automation_status = run_automations()
        if automation_status:
            self.stdout.write(self.style.SUCCESS("automation completed"))
        else:
            self.stdout.write(self.style.ERROR("automation Failed"))
