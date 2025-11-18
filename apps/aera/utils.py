from apps.core.models import LogEntry

class AeraLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(source=LogEntry.AERA, level=LogEntry.INFO, message=msg)

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(source=LogEntry.AERA, level=LogEntry.WARNING, message=msg)

    @staticmethod
    def error(msg):
        LogEntry.objects.create(source=LogEntry.AERA, level=LogEntry.ERROR, message=msg)
