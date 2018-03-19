#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
from decimal import Decimal
import doctest
import trytond.tests.test_tryton
from trytond.exceptions import UserError
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.tests.test_tryton import doctest_teardown
from trytond.tests.test_tryton import doctest_checker

from trytond.modules.company.tests import create_company, set_company


class TestCase(ModuleTestCase):
    'Test module'
    module = 'production_output_lot'

    @with_transaction()
    def test0010output_lot_creation(self):
        'Test output lot creation.'
        pool = Pool()
        LotType = pool.get('stock.lot.type')
        Location = pool.get('stock.location')
        ModelData = pool.get('ir.model.data')
        Product = pool.get('product.product')
        Production = pool.get('production')
        ProductConfig = pool.get('production.configuration')
        Sequence = pool.get('ir.sequence')
        Sequence_type = pool.get('ir.sequence.type')
        Template = pool.get('product.template')
        Template_lot_type = pool.get('product.template-stock.lot.type')
        Uom = pool.get('product.uom')

        # Create Company
        company = create_company()
        with set_company(company):
            kg, = Uom.search([('name', '=', 'Kilogram')])
            production_group_id = ModelData.get_id('production',
                'group_production')
            config = ProductConfig(1)

            if not Sequence_type.search([('code', '=', 'stock.lot')]):
                Sequence_type.create([{
                            'name': 'Lot',
                            'code': 'stock.lot',
                            'groups': [
                                ('add', [production_group_id]),
                                ],
                            }])
            sequences = Sequence.search([
                    ('code', '=', 'stock.lot'),
                    ])
            if not sequences:
                lot_sequence, = Sequence.create([{
                            'name': 'Lot',
                            'code': 'stock.lot',
                            'company': company.id,
                            }])
            else:
                lot_sequence = sequences[0]

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
            lot_types = LotType.search([])
            Template_lot_type.create([{
                    'template': output_template_w_lot.id,
                    'type': type_.id,
                    } for type_ in lot_types])

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
                                    'uom': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    }])
                        ],
                    'outputs': [
                        ('create', [{
                                    'product': output_product_wo_lot.id,
                                    'uom': kg.id,
                                    'quantity': 5,
                                    'from_location': production_loc.id,
                                    'to_location': storage_loc.id,
                                    'unit_price': Decimal('10'),
                                    }])
                        ],
                    }, {
                    'product': output_product_w_lot.id,
                    'quantity': 5,
                    'inputs': [
                        ('create', [{
                                    'product': input_product.id,
                                    'uom': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    }])
                        ],
                    'outputs': [
                        ('create', [{
                                    'product': output_product_w_lot.id,
                                    'uom': kg.id,
                                    'quantity': 5,
                                    'from_location': production_loc.id,
                                    'to_location': storage_loc.id,
                                    'unit_price': Decimal('10'),
                                    }])
                        ],
                    }])
            productions = [production_wo_lot, production_w_lot]
            production_w_lot2, = Production.copy([production_w_lot])

            Production.wait(productions)
            assigned = Production.assign_try(productions)
            self.assertTrue(assigned)
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

            Production.done(productions)
            self.assertEqual([p.state for p in productions],
                ['done', 'done'])

            self.assertEqual(production_w_lot.outputs[0].lot, created_lot)

            # Create lot on 'done' state
            config.output_lot_creation = 'done'
            config.save()

            Production.wait([production_w_lot2])
            assigned = Production.assign_try([production_w_lot2])

            Production.run([production_w_lot2])
            self.assertTrue(all(i.state == 'done'
                    for i in production_w_lot2.inputs))
            self.assertIsNone(production_w_lot2.outputs[0].lot)

            Production.done([production_w_lot2])
            self.assertEqual(production_w_lot2.state, 'done')
            self.assertIsNotNone(production_w_lot2.outputs[0].lot)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    suite.addTests(doctest.DocFileSuite('scenario_production_lot_sequence.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
