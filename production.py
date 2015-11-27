# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import Model, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Configuration', 'ConfigurationCompany', 'Production', 'StockMove']
__metaclass__ = PoolMeta

_OUTPUT_LOT_CREATION = [
    ('running', 'Production in Running'),
    ('done', 'Production is Done'),
    ]


class Configuration:
    __name__ = 'production.configuration'

    output_lot_creation = fields.Function(fields.Selection(
            _OUTPUT_LOT_CREATION, 'When Output Lot is created?', required=True,
            help='The Production\'s state in which the Output Lot will be '
            'created automatically, if the Output Product is configured to '
            'require lot in production.'),
        'get_company_config', setter='set_company_config')
    output_lot_sequence = fields.Function(fields.Many2One('ir.sequence',
            'Output Lot Sequence', required=True, domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('code', '=', 'stock.lot'),
                ]),
        'get_company_config', setter='set_company_config')

    @staticmethod
    def default_output_lot_creation():
        return 'running'

    @classmethod
    def get_company_config(cls, configs, names):
        pool = Pool()
        CompanyConfig = pool.get('production.configuration.company')

        company_id = Transaction().context.get('company')
        company_configs = CompanyConfig.search([
                ('company', '=', company_id),
                ])

        res = {}
        for fname in names:
            res[fname] = {
                configs[0].id: None,
                }
            if company_configs:
                val = getattr(company_configs[0], fname)
                if isinstance(val, Model):
                    val = val.id
                res[fname][configs[0].id] = val
        return res

    @classmethod
    def set_company_config(cls, configs, name, value):
        pool = Pool()
        CompanyConfig = pool.get('production.configuration.company')

        company_id = Transaction().context.get('company')
        company_configs = CompanyConfig.search([
                ('company', '=', company_id),
                ])
        if company_configs:
            company_config = company_configs[0]
        else:
            company_config = CompanyConfig(company=company_id)
        setattr(company_config, name, value)
        company_config.save()


class ConfigurationCompany(ModelSQL):
    'Production Configuration by Company'
    __name__ = 'production.configuration.company'

    company = fields.Many2One('company.company', 'Company', required=True,
        ondelete='CASCADE', select=True)
    output_lot_creation = fields.Selection([(None, '')] + _OUTPUT_LOT_CREATION,
            'When Output Lot is created?')
    output_lot_sequence = fields.Many2One('ir.sequence',
        'Output Lot Sequence', domain=[
            ('company', 'in', [Eval('company'), None]),
            ('code', '=', 'stock.lot'),
            ], depends=['company'])


class Production:
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
    __name__ = 'stock.move'

    @classmethod
    def __setup__(cls):
        super(StockMove, cls).__setup__()
        cls._error_messages.update({
                'no_sequence':  ('There is not output lot sequence defined. '
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
                input_expiry_dates = [i.lot.expiry_date for i in self.inputs
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
        if hasattr(self.product, 'lot_sequence_used'):
            sequence = self.product.lot_sequence_used
            if sequence:
                return sequence
        if not config.output_lot_sequence:
            self.raise_user_error('no_sequence')
        return config.output_lot_sequence
