#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
from decimal import Decimal
import trytond.tests.test_tryton
from trytond.exceptions import UserError
from trytond.tests.test_tryton import (POOL, DB_NAME, USER, CONTEXT,
    test_view, test_depends)
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    '''
    Test module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('production_output_lot')
        self.company = POOL.get('company.company')
        self.lot_type = POOL.get('stock.lot.type')
        self.location = POOL.get('stock.location')
        self.model_data = POOL.get('ir.model.data')
        self.product = POOL.get('product.product')
        self.production = POOL.get('production')
        self.production_config = POOL.get('production.configuration')
        self.sequence = POOL.get('ir.sequence')
        self.sequence_type = POOL.get('ir.sequence.type')
        self.template = POOL.get('product.template')
        self.template_lot_type = POOL.get('product.template-stock.lot.type')
        self.uom = POOL.get('product.uom')
        self.user = POOL.get('res.user')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('production_output_lot')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0010output_lot_creation(self):
        '''
        Test output lot creation.
        '''
        with Transaction().start(DB_NAME, USER,
                context=CONTEXT):
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ])
            self.user.write([self.user(USER)], {
                    'main_company': company.id,
                    'company': company.id,
                    })
            Transaction().context['company'] = company.id

            currency = company.currency
            kg, = self.uom.search([('name', '=', 'Kilogram')])
            production_group_id = self.model_data.get_id('production',
                'group_production')
            config = self.production_config(1)

            if not self.sequence_type.search([('code', '=', 'stock.lot')]):
                self.sequence_type.create([{
                            'name': 'Lot',
                            'code': 'stock.lot',
                            'groups': [
                                ('add', [production_group_id]),
                                ],
                            }])
            sequences = self.sequence.search([
                    ('code', '=', 'stock.lot'),
                    ])
            if not sequences:
                lot_sequence, = self.sequence.create([{
                            'name': 'Lot',
                            'code': 'stock.lot',
                            'company': company.id,
                            }])
            else:
                lot_sequence = sequences[0]

            (input_template, output_template_wo_lot,
                output_template_w_lot) = self.template.create([{
                        'name': 'Input Product',
                        'type': 'goods',
                        'consumable': True,
                        'list_price': Decimal(10),
                        'cost_price': Decimal(5),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }, {
                        'name': 'Output Product without Lot',
                        'type': 'goods',
                        'list_price': Decimal(20),
                        'cost_price': Decimal(10),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }, {
                        'name': 'Output Product with Lot',
                        'type': 'goods',
                        'list_price': Decimal(20),
                        'cost_price': Decimal(10),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        }])
            (input_product, output_product_wo_lot,
                output_product_w_lot) = self.product.create([{
                        'template': input_template.id,
                        }, {
                        'template': output_template_wo_lot.id,
                        }, {
                        'template': output_template_w_lot.id,
                        }])
            lot_types = self.lot_type.search([])
            self.template_lot_type.create([{
                    'template': output_template_w_lot.id,
                    'type': type_.id,
                    } for type_ in lot_types])

            warehouse = self.location(self.production.default_warehouse())
            storage_loc = warehouse.storage_location
            production_loc = warehouse.production_location
            self.assertTrue(
                output_product_w_lot.lot_is_required(production_loc,
                    storage_loc))

            production_wo_lot, production_w_lot = self.production.create([{
                    'product': output_product_wo_lot.id,
                    'quantity': 5,
                    'company': company.id,
                    'inputs': [
                        ('create', [{
                                    'product': input_product.id,
                                    'uom': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    'company': company.id,
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
                                    'currency': currency.id,
                                    'company': company.id,
                                    }])
                        ],
                    }, {
                    'product': output_product_w_lot.id,
                    'quantity': 5,
                    'company': company.id,
                    'inputs': [
                        ('create', [{
                                    'product': input_product.id,
                                    'uom': kg.id,
                                    'quantity': 10,
                                    'from_location': storage_loc.id,
                                    'to_location': production_loc.id,
                                    'company': company.id,
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
                                    'currency': currency.id,
                                    'company': company.id,
                                    }])
                        ],
                    }])
            productions = [production_wo_lot, production_w_lot]
            production_w_lot2, = self.production.copy([production_w_lot])

            self.production.wait(productions)
            assigned = self.production.assign_try(productions)
            self.assertTrue(assigned)
            self.assertTrue(all(i.state == 'assigned' for p in productions
                    for i in p.inputs))

            # Production can't be done before configure
            with self.assertRaises(UserError):
                self.production.run(productions)

            # Create lot on 'running' state
            config.output_lot_creation = 'running'
            config.output_lot_sequence = lot_sequence
            config.save()

            self.production.run(productions)
            self.assertTrue(all(i.state == 'done' for p in productions
                    for i in p.inputs))
            self.assertIsNone(production_wo_lot.outputs[0].lot)
            self.assertIsNotNone(production_w_lot.outputs[0].lot)
            created_lot = production_w_lot.outputs[0].lot

            self.production.done(productions)
            self.assertEqual([p.state for p in productions],
                ['done', 'done'])

            self.assertEqual(production_w_lot.outputs[0].lot, created_lot)

            # Create lot on 'done' state
            config.output_lot_creation = 'done'
            config.save()

            self.production.wait([production_w_lot2])
            assigned = self.production.assign_try([production_w_lot2])

            self.production.run([production_w_lot2])
            self.assertTrue(all(i.state == 'done'
                    for i in production_w_lot2.inputs))
            self.assertIsNone(production_w_lot2.outputs[0].lot)

            self.production.done([production_w_lot2])
            self.assertEqual(production_w_lot2.state, 'done')
            self.assertIsNotNone(production_w_lot2.outputs[0].lot)


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    exclude_tests = ('test0005views', 'test0006depends',
        'test0020company_recursion', 'test0040user',
        'test0020mon_grouping', 'test0040rate_unicity',
        'test0060compute_nonfinite', 'test0070compute_nonfinite_worounding',
        'test0080compute_same', 'test0090compute_zeroamount',
        'test0100compute_zerorate', 'test0110compute_missingrate',
        'test0120compute_bothmissingrate', 'test0130delete_cascade')
    for test in test_company.suite():
        if test not in suite and test.id().split('.')[-1] not in exclude_tests:
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
