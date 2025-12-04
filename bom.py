# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.i18n import gettext
from trytond.model.exceptions import ValidationError


class BOMInput(metaclass=PoolMeta):
    __name__ = 'production.bom.input'
    use_lot = fields.Boolean('Use Lot')

    @classmethod
    def validate(cls, boms):
        super().validate(boms)
        for bom in boms:
            bom.check_unique_use_lot_in_bom()

    def check_unique_use_lot_in_bom(self):
        inputs = self.search([
            ('bom', '=', self.bom.id),
            ('use_lot', '=', True)
            ])
        if len(inputs) > 1:
            raise ValidationError(
                gettext('production_output_lot.unique_use_lot_in_bom'))
