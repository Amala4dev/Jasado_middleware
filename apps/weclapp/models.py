from django.db import models
from django.db.models import F
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models import ForeignKey
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import IntegerField
from django.db.models import DateTimeField
from django.db.models import SET_NULL
from utils import CleanDecimalField
from django.core.validators import MaxValueValidator
from apps.core.models import Product
from decimal import Decimal
from django.utils import timezone


class CustomsPositionMap(Model):
    customs_number = CharField(max_length=100, unique=True)
    weclapp_id = CharField(max_length=100)

    def __str__(self):
        return self.customs_number


class SyncStatus(Model):
    STATUS_ONGOING = "ongoing"
    STATUS_COMPLETED = "completed"
    DEFAULT_NAME = "Master Data Transfer"
    DEFAULT_DURATION = "Not Completed yet"

    name = CharField(max_length=100, unique=True, default=DEFAULT_NAME)
    status = CharField(max_length=100)
    time_started = DateTimeField(null=True, blank=True)
    time_completed = DateTimeField(null=True, blank=True)
    task_duration = CharField(max_length=100, default="Not Completed yet")

    def save(self, *args, **kwargs):
        if self.time_started and self.time_completed:
            duration = self.time_completed - self.time_started
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            parts = []
            if hours:
                parts.append(f"{hours}hrs")
            if minutes:
                parts.append(f"{minutes} minutes")
            if seconds or not parts:
                parts.append(f"{seconds} seconds")
            self.task_duration = " ".join(parts)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @classmethod
    def is_ongoing(cls):
        sync_status = cls.objects.filter(name=cls.DEFAULT_NAME).first()
        if not sync_status:
            return False
        return sync_status.status == cls.STATUS_ONGOING

    @classmethod
    def set_ongoing(cls):
        cls.objects.update_or_create(
            name=cls.DEFAULT_NAME,
            defaults={
                "status": cls.STATUS_ONGOING,
                "time_started": timezone.now(),
                "time_completed": None,
                "task_duration": cls.DEFAULT_DURATION,
            },
        )

    @classmethod
    def set_completed(cls):
        cls.objects.update_or_create(
            name=cls.DEFAULT_NAME,
            defaults={
                "status": cls.STATUS_COMPLETED,
                "time_completed": timezone.now(),
            },
        )
