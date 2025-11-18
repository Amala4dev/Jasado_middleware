from django.core.management.base import BaseCommand
from apps.core.views import process_pending_exports


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        export_status = process_pending_exports()
        if export_status:
            self.stdout.write(self.style.SUCCESS("Export completed"))
        else:
            self.stdout.write(self.style.ERROR("Export Failed"))
