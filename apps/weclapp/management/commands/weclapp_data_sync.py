from django.core.management.base import BaseCommand
from apps.weclapp.views import (
    bootstrap_weclapp_ids,
    bootstrap_manufacturer_weclapp_ids,
    bootstrap_customs_position_weclapp_ids,
    bootstrap_article_category_weclapp_ids,
)
from apps.weclapp.views_async import sync_master_data
import asyncio
from django.utils import timezone


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        ids_synced = bootstrap_weclapp_ids()
        manu_ids_synced = bootstrap_manufacturer_weclapp_ids()
        custom_pos_synced = bootstrap_customs_position_weclapp_ids()
        category_ids_synced = bootstrap_article_category_weclapp_ids()

        if all(
            [
                ids_synced,
                manu_ids_synced,
                custom_pos_synced,
                category_ids_synced,
            ]
        ):
            self.stdout.write(
                self.style.WARNING(
                    f"Master data sync to Weclapp started {timezone.now()}"
                )
            )

            asyncio.run(sync_master_data())
            self.stdout.write(
                self.style.SUCCESS(
                    f"Master data sync to Weclapp completed {timezone.now()}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Master data did not sync to Weclapp, something Failed"
                )
            )
