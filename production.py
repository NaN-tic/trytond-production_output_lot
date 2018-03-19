# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.company.model import CompanyValueMixin

__all__ = ['Configuration', 'ConfigurationCompany', 'Production', 'StockMove']

_OUTPUT_LOT_CREATION = [
    ('running', 'Production in Running'),
    ('done', 'Production is Done'),
    ]


class Configuration:
    __metaclass__ = PoolMeta
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


class Production:
    __metaclass__ = PoolMeta
    __name__ = 'production'

    @classmethod
    def __setup__(cls):
        super(Production, cls).__setup__()
        cls._error_messages.update({
                'missing_output_lot_creation_config': (
                    'The "When Output Lot is created?" or '
                    '"Output Lot Sequence" Production configuration params '
                    'are empty.'),
                })

    @classmethod
    def run(cls, productions):
        pool = Pool()
        Config = pool.get('production.configuration')
        config = Config(1)
        if not config.output_lot_creation:
            cls.raise_user_error('missing_output_lot_creation_config')

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
            cls.raise_user_error('missing_output_lot_creation_config')

        if config.output_lot_creation == 'done':
            for production in productions:
                production.create_output_lots()
        super(Production, cls).done(productions)

    def create_output_lots(self):
        Config = Pool().get('production.configuration')
        config = Config(1)
        if not config.output_lot_creation or not config.output_lot_sequence:
            self.raise_user_error('missing_output_lot_creation_config')

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


class StockMove:
    __metaclass__ = PoolMeta
    __name__ = 'stock.move'

    @classmethod
    def __setup__(cls):
        super(StockMove, cls).__setup__()
        cls._error_messages.update({
                'no_sequence': ('There is not output lot sequence defined. '
                    'Please define one in production configuration.'),
                })

    def get_production_output_lot(self):
        pool = Pool()
        Lot = pool.get('stock.lot')
        Sequence = pool.get('ir.sequence')

        if not self.production_output:
            return

        number = Sequence.get_id(self._get_output_lot_sequence().id)
        lot = Lot(product=self.product, number=number)

        if hasattr(Lot, 'expiry_date'):
            if self.product.expiry_time:
                input_expiry_dates = [i.lot.expiry_date
                    for i in self.production_output.inputs
                    if i.lot and i.lot.expiry_date]
                if input_expiry_dates:
                    lot.expiry_date = min(input_expiry_dates)
                else:
                    expiry_date = lot.on_change_product().get('expiry_date')
                    if expiry_date:
                        lot.expiry_date = expiry_date
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
            self.raise_user_error('no_sequence')
        return config.output_lot_sequence
