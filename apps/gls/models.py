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

ARTICLE_GROUP_MAP = {
    "0": "Material & Instrumente",
    "1": "Kleingeräte",
    "2": "Ersatzteile",
    "3": "Zähne",
    "5": "Hand-&Winkelstücke",
}


PRODUCT_GROUP_MAP = {
    "0": "Material & Instrumente",
    "1": "Kleingeräte",
    "2": "Ersatzteile",
    "3": "Zähne",
    "5": "Hand-&Winkelstücke",
}


SHIPPING_SERVICES = {
    "20": "GLS National",
    "31": "GLS International",
    "32": "GLS Express",
    "02": "TOF Normal",
    "18": "TOF Express 12 Uhr",
    "19": "TOF Express 10 Uhr",
    "08": "Speditionsabwicklung",
}


class GLSSupplier(Model):
    supplier_no = CharField(max_length=20, unique=True)
    name1 = CharField(max_length=200, blank=True, null=True)
    name2 = CharField(max_length=200, blank=True, null=True)
    street = CharField(max_length=100, blank=True, null=True)
    country = CharField(max_length=10, blank=True, null=True)
    postal_code = CharField(max_length=30, blank=True, null=True)
    city = CharField(max_length=100, blank=True, null=True)
    search_term = CharField(max_length=100, blank=True, null=True)
    phone = CharField(max_length=50, blank=True, null=True)
    fax = CharField(max_length=50, blank=True, null=True)
    email = CharField(max_length=150, blank=True, null=True)
    vat_id = CharField(max_length=30, blank=True, null=True)
    url = CharField(max_length=255, blank=True, null=True)
    blocked = BooleanField(default=False)
    drug_ban = BooleanField(default=False)
    packaging_reg_no = CharField(max_length=50, blank=True, null=True)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Supplier ls.320"
        verbose_name_plural = "GLS Suppliers ls.320"

    def __str__(self):
        return self.supplier_no or "Supplier"


class GLSProductGroup(Model):
    product_group_no = CharField(max_length=20, unique=True)
    product_group_name = CharField(max_length=100, null=True, blank=True)
    last_updated = DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.product_group_no


class GLSMasterData(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="gls_master_data",
        verbose_name="Product SKU",
        # editable=False,
    )
    article_no = CharField(max_length=50, unique=True)
    description = CharField(max_length=255, blank=True, null=True)
    article_group_no = CharField(max_length=10, blank=True, null=True)
    abc_license_plate = CharField(max_length=5, blank=True, null=True)
    manufacturer = CharField(
        verbose_name="Manufacturer no", max_length=100, blank=True, null=True
    )
    manufacturer_article_no = CharField(max_length=50, blank=True, null=True)
    packaging_unit = CleanDecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    alternative_article_no = CharField(max_length=50, blank=True, null=True)
    customs_position = CharField(max_length=20, blank=True, null=True)
    country_of_origin = CharField(max_length=20, blank=True, null=True)
    blocked = BooleanField(default=False)
    country_of_origin_alt = CharField(
        verbose_name="Country of Origin (Alt)", max_length=20, blank=True, null=True
    )
    vat_rate = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    created_on = DateField(null=True, blank=True)
    medical_device = CharField(max_length=10, blank=True, null=True)
    drug = CharField(max_length=10, blank=True, null=True)
    pzn_no = CharField(max_length=20, blank=True, null=True)
    avg_delivery_time = CleanDecimalField(
        verbose_name="Last average delivery time",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    order_suggestion = BooleanField(
        default=False, help_text="True = Sale item (Y), False = Regular item (N)"
    )
    un_number = CharField(max_length=50, blank=True, null=True)
    packing_unit = CharField(max_length=20, blank=True, null=True)
    hazard_code = CharField(max_length=20, blank=True, null=True)
    package_contents = CleanDecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    length = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    width = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    height = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    weight = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    dangerous_goods = BooleanField(default=False)
    store_refrigerated = BooleanField(default=False)
    batch_number_required = BooleanField(default=True)
    serial_number_required = BooleanField(default=False)
    mhd_compulsory = BooleanField(default=False)
    warehouse = CharField(max_length=20, blank=True, null=True)
    product_group_no = CharField(max_length=20, blank=True, null=True)
    freely_available = BooleanField(default=True)
    hibc_manufacturer_id = CharField(max_length=10, blank=True, null=True)
    hibc_article_no = CharField(max_length=30, blank=True, null=True)
    hibc_packaging_index = CharField(max_length=5, blank=True, null=True)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    @property
    def article_group_name(self):
        return ARTICLE_GROUP_MAP.get(self.article_group_no, "Unknown")

    @property
    def product_group_name(self):
        product_group = GLSProductGroup.objects.filter(
            product_group_no=self.product_group_no
        ).first()
        if product_group:
            return product_group.product_group_name
        return "Unknown"

    @property
    def manufacturer_name(self):
        supplier = GLSSupplier.objects.filter(supplier_no=self.manufacturer).first()
        if supplier:
            return f"{supplier.name1 or ''} {supplier.name2 or ''}".strip() or "Unknown"
        return "Unknown"

    class Meta:
        verbose_name = "GLS Master Data as.316"
        verbose_name_plural = "GLS Master Data as.316"

    def __str__(self):
        return self.article_no


class GLSStockLevel(Model):
    article_no = CharField(max_length=50, unique=True)
    inventory = CleanDecimalField(max_digits=14, decimal_places=4)
    ordered_qty = CleanDecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    next_receipt_date = DateField(
        verbose_name="Nächstes WE-datum", null=True, blank=True
    )
    next_receipt_qty = CleanDecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Stock Level lb.315"
        verbose_name_plural = "GLS Stock Level lb.315"

    def __str__(self):
        return self.article_no


class GLSPriceList(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="gls_price_list",
        editable=False,
    )
    article_no = CharField(max_length=50, unique=True)
    purchase_price = CleanDecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    bill_back_price = CleanDecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    recommended_retail_price = CleanDecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Price List pl.317"
        verbose_name_plural = "GLS Price List pl.317"

    def __str__(self):
        return self.article_no


class GLSOrderConfirmation(Model):
    RECORD_TYPE_CHOICES = [
        ("1", "Actual qty (IST) entry"),  # Satzart 1 – Istmenge dieser Position
        ("2", "Serial number (IST)"),  # Satzart 2 – Seriennummern
        ("3", "Batch number (IST)"),  # Satzart 3 – Chargennummern
        ("4", "Expiration date / MHD (IST)"),  # Satzart 4 – Mindesthaltbarkeitsdatum
        ("5", "Siemens process number (IST)"),  # Satzart 5 – Siemensvorgangsnr.
        ("6", "Package information (IST)"),  # Satzart 6 – Packstückinfo
        ("7", "Planned qty / availability (SOLL)"),  # Satzart 7 – Sollrückmeldung
        ("8", "Backorder information (INFO)"),  # Satzart 8 – Rückstandsinfo
    ]

    record_type = CharField(max_length=5, blank=True, null=True, db_index=True)
    order_number = CharField(max_length=50, blank=True, null=True, db_index=True)
    position = CharField(max_length=10, blank=True, null=True)
    actual_value = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    control_number = CharField(max_length=150, blank=True, null=True)
    shipping_info = CharField(max_length=50, blank=True, null=True)
    packing_time = CharField(max_length=10, blank=True, null=True)
    goods_receipt_date = DateField(blank=True, null=True)
    ordered_qty = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    info = CharField(max_length=150, blank=True, null=True)
    order_method = CharField(max_length=10, blank=True, null=True)
    end_customer_id = CharField(max_length=50, blank=True, null=True)
    customer_number = CharField(max_length=20, blank=True, null=True)
    article_no = CharField(max_length=50, blank=True, null=True, db_index=True)
    unit_price = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    internal_user = CharField(max_length=20, blank=True, null=True)
    document_number = CharField(max_length=20, blank=True, null=True)
    delivery_note_date = DateField(blank=True, null=True)
    expected_delivery_date = DateField(blank=True, null=True)
    backorder_text = CharField(max_length=200, blank=True, null=True)
    processed = BooleanField(editable=False, default=False, db_index=True)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Order Confirmation no.304"
        verbose_name_plural = "GLS Order Confirmation no.304"

    def __str__(self):
        return f"Confirmation {self.order_number}"


class GLSBackorder(Model):
    order_number = CharField(
        max_length=50, blank=True, null=True, db_index=True
    )  # Auftragsnr. (1)
    position_number = CharField(
        max_length=50, blank=True, null=True
    )  # Positionsnr. (2)
    backorder_qty = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Rückstand (3)
    next_goods_receipt = DateField(blank=True, null=True)  # Nächster WE (4)
    order_receipt_date = DateField(blank=True, null=True)  # Eingangsdatum (5)
    confirmed_delivery_date = DateField(
        blank=True, null=True
    )  # Bestätigter Liefert. (6)
    customer_number = CharField(
        max_length=20, blank=True, null=True
    )  # Kundennummer (7)
    article_no = CharField(
        max_length=50, blank=True, null=True
    )  # Nutzer Artikelnummer (8)
    description = CharField(max_length=100, blank=True, null=True)  # Beschreibung (9)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Backorder x.310"
        verbose_name_plural = "GLS Backorders x.310"

    def __str__(self):
        return self.order_number or "Backorder"


class GLSPromotionHeader(Model):
    action_code = CharField(
        max_length=20, blank=True, null=True, db_index=True
    )  # Aktionskennzeichen (1)
    origin_code = CharField(
        max_length=5, blank=True, null=True
    )  # Herkunftskennzeichen (2)
    valid_from = DateField(blank=True, null=True)  # gültig ab (3)
    valid_to = DateField(blank=True, null=True)  # gültig bis (4)
    customer_number = CharField(
        max_length=50, blank=True, null=True
    )  # Debitorennummer (5)
    short_text = CharField(max_length=50, blank=True, null=True)  # Aktionskurztext (6)
    action_type = CharField(max_length=5, blank=True, null=True)  # Aktionsart (7)
    min_value_eur = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # SetMindWert (8)
    max_value_eur = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # SetMaxWert (9)
    min_qty = CharField(max_length=20, blank=True, null=True)  # MinMenge StCK (10)
    max_qty = CharField(max_length=20, blank=True, null=True)  # MaxMenge (11)
    invoice_text_1 = CharField(
        max_length=50, blank=True, null=True
    )  # FakturaTextFeld 1 (12)
    set_price = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # SetPreis (13)
    currency = CharField(max_length=5, blank=True, null=True)  # Währung (14)
    bom_flag = CharField(max_length=5, blank=True, null=True)  # StücklistenKZ (15)
    print_invoice_text = BooleanField(blank=True, null=True)  # FakturaText drucken (16)
    natural_discount_qty = CharField(
        max_length=100, blank=True, null=True
    )  # Menge Naturalrabatt (17)
    credit_flag = BooleanField(blank=True, null=True)  # Gutschrift (18)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Promotion Header 501"
        verbose_name_plural = "GLS Promotion Headers 501"

    def __str__(self):
        return f"{self.action_code} ({self.short_text})"


class GLSPromotionPosition(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="gls_promotional_position",
        editable=False,
    )
    action_code = CharField(
        max_length=20, blank=True, null=True, db_index=True
    )  # Aktionskennzeichen (1)
    origin_code = CharField(
        max_length=5, blank=True, null=True
    )  # Herkunftskennzeichen (2)
    position_number = CharField(
        max_length=20, blank=True, null=True
    )  # Positionsnummer (3)
    article_no = CharField(
        max_length=50, blank=True, null=True, db_index=True
    )  # Artikelnummer (4)
    set_qty = CharField(max_length=20, blank=True, null=True)  # SetMenge (5)
    qty_editable = CharField(max_length=5, blank=True, null=True)  # Menge änderbar (6)
    incentive_article = BooleanField(blank=True)  # Incentiveartikel (7)
    net_gross_flag = CharField(max_length=5, blank=True, null=True)  # NettoKZ (8)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Promotion Position 502"
        verbose_name_plural = "GLS Promotion Positions 502"

    def __str__(self):
        return f"{self.action_code} - {self.article_no}"


class GLSPromotionPrice(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="gls_promotional_price",
        editable=False,
    )
    action_code = CharField(
        max_length=20, blank=True, null=True, db_index=True
    )  # Aktionskennzeichen (1)
    origin_code = CharField(
        max_length=5, blank=True, null=True
    )  # Herkunftskennzeichen (2)
    article_no = CharField(
        max_length=50, blank=True, null=True, db_index=True
    )  # GLS-Artikelnummer (3)
    valid_from = DateField(blank=True, null=True)  # Preis gültig ab (4)
    valid_to = DateField(blank=True, null=True)  # Preis gültig bis (5)
    promotion_price = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # AktionsVerkaufspreis (6)
    qty_tier_1 = CharField(max_length=20, blank=True, null=True)  # Staffel Menge1 (7)
    qty_tier_2 = CharField(max_length=20, blank=True, null=True)  # Staffel Menge2 (8)
    qty_tier_3 = CharField(max_length=20, blank=True, null=True)  # Staffel Menge3 (9)
    qty_tier_4 = CharField(max_length=20, blank=True, null=True)  # Staffel Menge4 (10)
    qty_tier_5 = CharField(max_length=20, blank=True, null=True)  # Staffel Menge5 (11)
    price_tier_1 = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Staffel Preis1 (12)
    price_tier_2 = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Staffel Preis2 (13)
    price_tier_3 = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Staffel Preis3 (14)
    price_tier_4 = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Staffel Preis4 (15)
    price_tier_5 = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # Staffel Preis5 (16)
    change_flag = CharField(
        max_length=5, blank=True, null=True
    )  # Änderungskennzeichen (17)
    promotional_purchase_price = CleanDecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )  # AktionsEinkaufspreis (18)
    net_gross_flag = CharField(max_length=5, blank=True, null=True)  # NettoKZ (19)
    last_fetch_from_gls = DateTimeField(
        verbose_name="Last Fetched from GLS",
        help_text="Timestamp of the last data fetch from GLS",
        auto_now=True,
    )

    @property
    def short_text(self):
        header = GLSPromotionHeader.objects.filter(action_code=self.action_code).first()
        if header:
            return header.short_text
        return "N/A"

    @property
    def article_name(self):
        master_data = GLSMasterData.objects.filter(article_no=self.article_no).first()
        if master_data:
            return master_data.description
        return "N/A"

    class Meta:
        verbose_name = "GLS Promotion Price 503"
        verbose_name_plural = "GLS Promotion Prices 503"

    def __str__(self):
        return f"{self.article_no} ({self.action_code})"


class GLSOrderHeader(Model):
    record_type = CharField(max_length=5, null=True, blank=True)  # Satzart
    order_number = CharField(max_length=50, null=True, blank=True)  # Bestellnummer
    branch_no = CharField(max_length=50, null=True, blank=True)  # Filiale (GLS account)
    customer_id = CharField(max_length=50, null=True, blank=True)  # KundenID
    end_customer_no = CharField(max_length=20, null=True, blank=True)
    billing_name = CharField(max_length=50, null=True, blank=True)
    billing_name2 = CharField(max_length=50, null=True, blank=True)
    billing_name3 = CharField(max_length=50, null=True, blank=True)
    billing_name4 = CharField(max_length=50, null=True, blank=True)
    billing_street = CharField(max_length=50, null=True, blank=True)
    billing_zip = CharField(max_length=20, null=True, blank=True)
    billing_city = CharField(max_length=50, null=True, blank=True)
    billing_country = CharField(max_length=20, null=True, blank=True)
    shipping_name = CharField(max_length=50, null=True, blank=True)
    shipping_name2 = CharField(max_length=50, null=True, blank=True)
    shipping_name3 = CharField(max_length=50, null=True, blank=True)
    shipping_name4 = CharField(max_length=50, null=True, blank=True)
    shipping_street = CharField(max_length=50, null=True, blank=True)
    shipping_zip = CharField(max_length=20, null=True, blank=True)
    shipping_city = CharField(max_length=50, null=True, blank=True)
    shipping_country = CharField(max_length=20, null=True, blank=True)
    distribution_key = CharField(max_length=5, null=True, blank=True)  # Lieferschein
    document_type = CharField(max_length=5, null=True, blank=True)  # Lieferschein
    copies = IntegerField(default=1, validators=[MaxValueValidator(99)])
    open_field = CharField(max_length=5, null=True, blank=True)
    message = CharField(max_length=100, null=True, blank=True)
    carrier_code = CharField(max_length=5, null=True, blank=True)
    registration_code = CharField(max_length=50, null=True, blank=True)
    redelivery_method = IntegerField(
        null=True, blank=True, validators=[MaxValueValidator(9)]
    )
    order_type = IntegerField(null=True, blank=True, validators=[MaxValueValidator(9)])
    delivery_date = DateField(blank=True, null=True)
    contact_person = CharField(max_length=50, null=True, blank=True)
    email_address = CharField(max_length=50, null=True, blank=True)
    phone_number = CharField(max_length=50, null=True, blank=True)
    discount_period = IntegerField(null=True, blank=True)
    currency = CharField(max_length=5, null=True, blank=True)
    show_price_on_ls = BooleanField(default=False)
    print_format = CharField(max_length=5, null=True, blank=True)
    vat_id = CharField(max_length=50, null=True, blank=True)
    export_country = CharField(max_length=20, null=True, blank=True)
    is_processed = BooleanField(default=False)
    header_uploaded = BooleanField(default=False)
    header_renamed = BooleanField(default=False)
    lines_uploaded = BooleanField(default=False)
    lines_renamed = BooleanField(default=False)

    class Meta:
        verbose_name = "GLS Order Header 101"
        verbose_name_plural = "GLS Order Header 101"

    def __str__(self):
        return str(self.order_number)


class GLSOrderLine(Model):
    # GLS fields
    record_type = CharField(max_length=5, null=True, blank=True)  # Satzart
    order_header = ForeignKey(
        GLSOrderHeader,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lines",
    )
    order_number = CharField(
        max_length=50, null=True, blank=True, db_index=True
    )  # Bestellnummer
    position = CharField(max_length=20, null=True, blank=True, db_index=True)
    gls_article_no = CharField(max_length=50, null=True, blank=True, db_index=True)
    customer_article_no = CharField(max_length=50, null=True, blank=True)
    unit_price = CleanDecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    description = CharField(max_length=100, null=True, blank=True)
    description2 = CharField(max_length=100, null=True, blank=True)
    qty = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    promotion_code = CharField(max_length=20, null=True, blank=True)
    promotion_origin = CharField(max_length=5, null=True, blank=True)
    free_item = BooleanField(default=False)

    class Meta:
        verbose_name = "GLS Order Line 102"
        verbose_name_plural = "GLS Order Line 102"

    def __str__(self):
        return f"{self.order_number} - {self.gls_article_no}"


class GLSOrderStatusQuerySet(QuerySet):
    def cancelled(self):
        return self.filter(
            status_info__iregex=r"STORNO|GESPERRT|AUSFUHR", admin_notified=False
        )

    def new_updates(self):
        return self.exclude(status_info__iregex=r"STORNO|GESPERRT|AUSFUHR").filter(
            delivered_qty__gt=F("last_sent_qty")
        )


class GLSOrderStatus(Model):
    order_number = CharField(
        max_length=50, null=True, blank=True, db_index=True
    )  # Bestellnummer
    position = CharField(max_length=20, null=True, blank=True, db_index=True)
    article_no = CharField(max_length=50, null=True, blank=True)
    delivered = BooleanField(default=False, editable=False)
    delivered_qty = models.BigIntegerField(null=True, blank=True)
    planned_qty = models.BigIntegerField(null=True, blank=True)
    ordered_qty = models.BigIntegerField(null=True, blank=True)
    last_sent_qty = models.BigIntegerField(default=0, null=True, blank=True)
    control_number = CharField(
        verbose_name="Delivery note/Invoice Number",
        max_length=100,
        null=True,
        blank=True,
    )
    serial_number = CharField(max_length=100, null=True, blank=True)
    batch_number = CharField(max_length=100, null=True, blank=True)
    siemens_process_no = CharField(max_length=100, null=True, blank=True)
    package_type = CharField(max_length=50, null=True, blank=True)
    number_of_package = CharField(max_length=50, null=True, blank=True)
    package_number = CharField(max_length=50, null=True, blank=True)
    dfu_number = models.CharField(max_length=50, null=True, blank=True)
    pack_time = CharField(max_length=50, null=True, blank=True)
    pack_date = CharField(max_length=50, null=True, blank=True)
    expected_delivery_date = CharField(max_length=50, null=True, blank=True)
    delivery_date = CharField(max_length=50, null=True, blank=True)
    planned_goods_receipt_date = CharField(max_length=50, null=True, blank=True)
    shipping_service = CharField(max_length=150, null=True, blank=True)
    end_customer_id = CharField(max_length=50, blank=True, null=True)
    customer_number = CharField(max_length=50, blank=True, null=True)
    unit_price = CharField(max_length=50, blank=True, null=True)
    internal_user = models.CharField(max_length=50, null=True, blank=True)
    document_number = CharField(max_length=20, blank=True, null=True)
    expiry_date = CharField(max_length=50, blank=True, null=True)  # Versandinfo (6)
    backorder_text = CharField(max_length=200, blank=True, null=True)  # Rückstände (20)
    status_info = CharField(max_length=150, blank=True, null=True)  # Info (10)
    admin_notified = BooleanField(default=False, editable=False)
    objects = GLSOrderStatusQuerySet.as_manager()
    last_updated = DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "GLS Order Status"
        verbose_name_plural = "GLS Order Status"
        unique_together = ("order_number", "position")

    def __str__(self):
        return f" Order-No: {self.order_number or ''}"


class GLSHandlingSurcharge(Model):
    PERCENT = "percent"
    ABSOLUTE = "absolute"

    FEE_TYPE_CHOICES = [
        (PERCENT, "Percent"),
        (ABSOLUTE, "Absolute"),
    ]

    article_group_no = CharField(max_length=10, unique=True)
    article_group_name = CharField(max_length=100, null=True, blank=True)
    fee_type = models.CharField(
        max_length=10, choices=FEE_TYPE_CHOICES, default=PERCENT
    )
    value = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name_plural = "GLS Handling Surcharge"

    def __str__(self):
        return self.article_group_no

    @property
    def normalised_value(self):
        if self.fee_type == self.PERCENT:
            return self.value / Decimal(100)
        return self.value
