# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.company.model import CompanyValueMixin
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['Configuration', 'ConfigurationCompany', 'Production', 'StockMove']

_OUTPUT_LOT_CREATION = [
    ('running', 'Production in Running'),
    ('done', 'Production is Done'),
    ]


class Configuration(metaclass=PoolMeta):
    __name__ = 'production.configuration'

    output_lot_creation = fields.MultiValue(fields.Selection(
            _OUTPUT_LOT_CREATION, 'When Output Lot is created?', required=True,
            help='The Production\'s state in which the Output Lot will be '
            'created automatically, if the Output Product is configured to '
            'require lot in production.'))
    output_lot_sequence = fields.MultiValue(fields.Many2One('ir.sequence',
            'Output Lot Sequence', required=True, domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('code', '=', 'stock.lot'),
                ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'output_lot_creation', 'output_lot_sequence'}:
            return pool.get('production.configuration.company')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_output_lot_creation(cls, **pattern):
        return cls.multivalue_model(
            'output_lot_creation').default_output_lot_creation()


class ConfigurationCompany(ModelSQL, CompanyValueMixin):
    'Production Configuration by Company'
    __name__ = 'production.configuration.company'

    output_lot_creation = fields.Selection([(None, '')] + _OUTPUT_LOT_CREATION,
            'When Output Lot is created?')
    output_lot_sequence = fields.Many2One('ir.sequence',
        'Output Lot Sequence', domain=[
            ('company', 'in', [Eval('company'), None]),
            ('code', '=', 'stock.lot'),
            ], depends=['company'])

    @classmethod
    def default_output_lot_creation(cls):
        return 'running'


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    @classmethod
    def run(cls, productions):
        pool = Pool()
        Config = pool.get('production.configuration')
        config = Config(1)
        if not config.output_lot_creation:
            raise UserError(gettext(
                'production_output_lot.missing_output_lot_creation_config'))

        super(Production, cls).run(productions)
        if config.output_lot_creation == 'running':
            for production in productions:
                production.create_output_lots()

    @classmethod
    def done(cls, productions):
        pool = Pool()
        Config = pool.get('production.configuration')
        config = Config(1)
        if not config.output_lot_creation:
            raise UserError(gettext(
                'production_output_lot.missing_output_lot_creation_config'))

        if config.output_lot_creation == 'done':
            for production in productions:
                production.create_output_lots()
        super(Production, cls).done(productions)

    def create_output_lots(self):
        Config = Pool().get('production.configuration')
        config = Config(1)
        if not config.output_lot_creation or not config.output_lot_sequence:
            raise UserError(gettext(
                'production_output_lot.missing_output_lot_creation_config'))

        created_lots = []
        for output in self.outputs:
            if output.lot:
                continue
            if output.product.lot_is_required(output.from_location,
                    output.to_location):
                lot = output.get_production_output_lot()
                lot.save()
                output.lot = lot
                output.save()
                created_lots.append(lot)
        return created_lots


class StockMove(metaclass=PoolMeta):
    __name__ = 'stock.move'


    def get_production_output_lot(self):
        pool = Pool()
        Lot = pool.get('stock.lot')
        Sequence = pool.get('ir.sequence')

        if not self.production_output:
            return

        number = Sequence.get_id(self._get_output_lot_sequence().id)
        lot = Lot(product=self.product, number=number)

        if hasattr(Lot, 'expiration_date'):
            if self.product.expiry_time:
                input_expiry_dates = [i.lot.expiration_date
                    for i in self.production_output.inputs
                    if i.lot and i.lot.expiration_date]
                if input_expiry_dates:
                    lot.expiration_date = min(input_expiry_dates)
                else:
                    lot.on_change_product()
        return lot

    def _get_output_lot_sequence(self):
        pool = Pool()
        Config = pool.get('production.configuration')
        config = Config(1)
        if hasattr(self.product, 'lot_sequence'):
            sequence = self.product.lot_sequence
            if sequence:
                return sequence
        if not config.output_lot_sequence:
            raise UserError(gettext('production_output_lot.no_sequence'))
        return config.output_lot_sequence
