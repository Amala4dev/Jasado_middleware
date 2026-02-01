from apps.core.models import LogEntry


class ShopwareLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(
            source=LogEntry.SHOPWARE, level=LogEntry.INFO, message=msg
        )

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(
            source=LogEntry.SHOPWARE, level=LogEntry.WARNING, message=msg
        )

    @staticmethod
    def error(msg):
        LogEntry.objects.create(
            source=LogEntry.SHOPWARE, level=LogEntry.ERROR, message=msg
        )


def get_rule_name(paid_qty, free_qty):
    return f"RULE_BUY_{paid_qty}_GET_{free_qty}"


def get_promotion_name(paid_qty, free_qty, valid_from, valid_until=None):
    return f"PROMO_BUY_{paid_qty}_GET_{free_qty}__{valid_from}__{valid_until or 'OPEN'}"
