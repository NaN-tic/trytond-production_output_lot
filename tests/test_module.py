
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from decimal import Decimal
from trytond.exceptions import UserError
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction

from trytond.modules.company.tests import create_company, set_company, CompanyTestMixin


class ProductionOutputLotTestCase(CompanyTestMixin, ModuleTestCase):
    'Test ProductionOutputLot module'
    module = 'production_output_lot'

    @with_transaction()
    def test0010output_lot_creation(self):
        'Test output lot creation.'
        pool = Pool()
        Location = pool.get('stock.location')
        Product = pool.get('product.product')
        Production = pool.get('production')
        ProductConfig = pool.get('production.configuration')
        Sequence = pool.get('ir.sequence')
        SequenceType = pool.get('ir.sequence.type')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')
        ModelData = pool.get('ir.model.data')

        # Create Company
        company = create_company()
        with set_company(company):
            kg, = Uom.search([('name', '=', 'Kilogram')])
            config = ProductConfig(1)

            sequence_type = SequenceType(ModelData.get_id('stock_lot',
                                'sequence_type_stock_lot'))
            lot_sequence = Sequence(sequence_type=sequence_type,
                        name='Lot')

            (input_template, output_template_wo_lot,
                output_template_w_lot) = Template.create([{
                        'name': 'Input Product',
                        'type': 'goods',
                        'consumable': True,
                        'list_price': Decimal(10),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }, {
                        'name': 'Output Product without Lot',
                        'type': 'goods',
                        'producible': True,
                        'list_price': Decimal(20),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }, {
                        'name': 'Output Product with Lot',
                        'type': 'goods',
                        'producible': True,
                        'list_price': Decimal(20),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        'lot_required': ['supplier', 'customer', 'lost_found',
                            'storage', 'production'],
                        }])
            (input_product, output_product_wo_lot,
                output_product_w_lot) = Product.create([{
                        'template': input_template.id,
                        'cost_price': Decimal(5),
                        }, {
                        'template': output_template_wo_lot.id,
                        'cost_price': Decimal(10),
                        }, {
                        'template': output_template_w_lot.id,
                        'cost_price': Decimal(10),
                        }])

            warehouse = Location(Production.default_warehouse())
            storage_loc = warehouse.storage_location
            production_loc = warehouse.production_location
            self.assertTrue(
                output_product_w_lot.lot_is_required(production_loc,
                    storage_loc))

            production_wo_lot, production_w_lot = Production.create([{
                    'product': output_product_wo_lot.id,
                    'quantity': 5,
                    'inputs': [
                        ('create', [{
                                    'product': input_product.id,
                                    'unit': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    'currency': company.currency.id,
                                    }])
                        ],
                    'outputs': [
                        ('create', [{
                                    'product': output_product_wo_lot.id,
                                    'unit': kg.id,
                                    'quantity': 5,
                                    'from_location': production_loc.id,
                                    'to_location': storage_loc.id,
                                    'unit_price': Decimal('10'),
                                    'currency': company.currency.id,
                                    }])
                        ],
                    }, {
                    'product': output_product_w_lot.id,
                    'quantity': 5,
                    'inputs': [
                        ('create', [{
                                    'product': input_product.id,
                                    'unit': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    'currency': company.currency.id,
                                    }])
                        ],
                    'outputs': [
                        ('create', [{
                                    'product': output_product_w_lot.id,
                                    'unit': kg.id,
                                    'quantity': 5,
                                    'from_location': production_loc.id,
                                    'to_location': storage_loc.id,
                                    'unit_price': Decimal('10'),
                                    'currency': company.currency.id,
                                    }])
                        ],
                    }])
            productions = [production_wo_lot, production_w_lot]
            production_w_lot2, = Production.copy([production_w_lot])

            Production.wait(productions)
            Production.assign_try(productions)
            self.assertTrue(all(i.state == 'assigned' for p in productions
                    for i in p.inputs))

            # Production can't be done before configure
            with self.assertRaises(UserError):
                Production.run(productions)

            # Create lot on 'running' state
            config.output_lot_creation = 'running'
            config.output_lot_sequence = lot_sequence
            config.save()

            Production.run(productions)
            self.assertTrue(all(i.state == 'done' for p in productions
                    for i in p.inputs))
            self.assertIsNone(production_wo_lot.outputs[0].lot)
            self.assertIsNotNone(production_w_lot.outputs[0].lot)
            created_lot = production_w_lot.outputs[0].lot

            Production.do(productions)
            self.assertEqual([p.state for p in productions],
                ['done', 'done'])

            self.assertEqual(production_w_lot.outputs[0].lot, created_lot)

            # Create lot on 'done' state
            config.output_lot_creation = 'done'
            config.save()

            Production.wait([production_w_lot2])
            Production.assign_try([production_w_lot2])

            Production.run([production_w_lot2])
            self.assertTrue(all(i.state == 'done'
                    for i in production_w_lot2.inputs))
            self.assertIsNone(production_w_lot2.outputs[0].lot)

            Production.do([production_w_lot2])
            self.assertEqual(production_w_lot2.state, 'done')
            self.assertIsNotNone(production_w_lot2.outputs[0].lot)


del ModuleTestCase
