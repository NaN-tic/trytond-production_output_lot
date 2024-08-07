import datetime
import unittest
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from proteus import Model
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        today = datetime.date.today()
        yesterday = today - relativedelta(days=1)

        # Install production_output_lot Module
        config = activate_modules(
            ['production_output_lot', 'stock_lot_sequence'])

        # Create company
        _ = create_company()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.producible = True
        template.list_price = Decimal(30)
        template.lot_required = [
            'supplier', 'customer', 'lost_found', 'storage', 'production'
        ]
        template.save()
        product.template = template
        product.cost_price = Decimal(20)
        product.save()

        # Create Components
        component1 = Product()
        template1 = ProductTemplate()
        template1.name = 'component 1'
        template1.default_uom = unit
        template1.type = 'goods'
        template1.list_price = Decimal(5)
        template1.save()
        component1.template = template1
        component1.cost_price = Decimal(1)
        component1.save()
        meter, = ProductUom.find([('name', '=', 'Meter')])
        centimeter, = ProductUom.find([('symbol', '=', 'cm')])
        component2 = Product()
        template2 = ProductTemplate()
        template2.name = 'component 2'
        template2.default_uom = meter
        template2.type = 'goods'
        template2.list_price = Decimal(7)
        template2.save()
        component2.template = template2
        component2.cost_price = Decimal(5)
        component2.save()

        # Create Bill of Material
        BOM = Model.get('production.bom')
        BOMInput = Model.get('production.bom.input')
        BOMOutput = Model.get('production.bom.output')
        bom = BOM(name='product')
        input1 = BOMInput()
        bom.inputs.append(input1)
        input1.product = component1
        input1.quantity = 5
        input2 = BOMInput()
        bom.inputs.append(input2)
        input2.product = component2
        input2.quantity = 150
        input2.unit = centimeter
        output = BOMOutput()
        bom.outputs.append(output)
        output.product = product
        output.quantity = 1
        bom.save()
        ProductBom = Model.get('product.product-production.bom')
        product.boms.append(ProductBom(bom=bom))
        product.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line1 = InventoryLine()
        inventory.lines.append(inventory_line1)
        inventory_line1.product = component1
        inventory_line1.quantity = 200
        inventory_line2 = InventoryLine()
        inventory.lines.append(inventory_line2)
        inventory_line2.product = component2
        inventory_line2.quantity = 60
        inventory.save()
        Inventory.confirm([inventory.id], config.context)
        self.assertEqual(inventory.state, 'done')

        # Configure production sequence
        Sequence = Model.get('ir.sequence')
        SequenceType = Model.get('ir.sequence.type')
        Config = Model.get('production.configuration')
        config = Config(1)
        config.output_lot_creation = 'done'
        sequence_type, = SequenceType.find([('name', '=', 'Stock Lot')])
        output_sequence = Sequence(sequence_type=sequence_type,
                                   name='Output Sequence')
        output_sequence.save()
        config.output_lot_sequence = output_sequence
        config.save()

        # Make a production which uses the lot from product
        Production = Model.get('production')
        production = Production()
        production.effective_date = yesterday
        production.product = product
        production.bom = bom
        production.quantity = 2
        production.click('wait')
        production.click('assign_try')
        production.click('run')
        production.click('do')
        output, = production.outputs
        self.assertEqual(output.state, 'done')
        self.assertEqual(output.lot.number, '1')
        output_sequence.reload()
        self.assertEqual(output.product.lot_sequence.number_next, 2)

        # Make a production wich uses default production lot sequence
        template.lot_sequence = None
        template.save()
        template.reload()
        product.reload()
        production = Production()
        production.product = product
        production.bom = bom
        production.quantity = 2
        production.click('wait')
        production.click('assign_try')
        production.click('run')
        production.click('do')
        output, = production.outputs
        self.assertEqual(output.state, 'done')
        self.assertEqual(output.lot.number, '1')
        output_sequence.reload()
        self.assertEqual(output_sequence.number_next, 2)
