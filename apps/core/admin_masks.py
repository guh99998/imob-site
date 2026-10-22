"""Mixin que aplica máscaras a campos do ModelAdmin: `masks = {"zip_code": "cep"}`."""

from django.db import models

from .widgets import BRDecimalField, MaskedTextInput


class MaskedAdminMixin:
    masks: dict[str, str] = {}

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        mask = self.masks.get(db_field.name)
        if mask and isinstance(db_field, models.DecimalField):
            kwargs.update(
                form_class=BRDecimalField,
                widget=MaskedTextInput(mask),
                max_digits=db_field.max_digits,
                decimal_places=db_field.decimal_places,
            )
            return db_field.formfield(**kwargs)
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if mask and field is not None:
            field.widget = MaskedTextInput(mask)
        return field
