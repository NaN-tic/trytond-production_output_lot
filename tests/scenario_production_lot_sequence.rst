===========================================
Production with Stock Lot Sequence Scenario
===========================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> today = datetime.date.today()
    >>> yesterday = today - relativedelta(days=1)

Install production_output_lot Module::

    >>> config = activate_modules(['production_output_lot', 'stock_lot_sequence'])

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.producible = True
    >>> template.list_price = Decimal(30)
    >>> template.lot_required = ['supplier', 'customer', 'lost_found',
    ...     'storage', 'production']
    >>> template.save()
    >>> product.template = template
    >>> product.cost_price = Decimal(20)
    >>> product.save()

Create Components::

    >>> component1 = Product()
    >>> template1 = ProductTemplate()
    >>> template1.name = 'component 1'
    >>> template1.default_uom = unit
    >>> template1.type = 'goods'
    >>> template1.list_price = Decimal(5)
    >>> template1.save()
    >>> component1.template = template1
    >>> component1.cost_price = Decimal(1)
    >>> component1.save()

    >>> meter, = ProductUom.find([('name', '=', 'Meter')])
    >>> centimeter, = ProductUom.find([('name', '=', 'centimeter')])
    >>> component2 = Product()
    >>> template2 = ProductTemplate()
    >>> template2.name = 'component 2'
    >>> template2.default_uom = meter
    >>> template2.type = 'goods'
    >>> template2.list_price = Decimal(7)
    >>> template2.save()
    >>> component2.template = template2
    >>> component2.cost_price = Decimal(5)
    >>> component2.save()

Create Bill of Material::

    >>> BOM = Model.get('production.bom')
    >>> BOMInput = Model.get('production.bom.input')
    >>> BOMOutput = Model.get('production.bom.output')
    >>> bom = BOM(name='product')
    >>> input1 = BOMInput()
    >>> bom.inputs.append(input1)
    >>> input1.product = component1
    >>> input1.quantity = 5
    >>> input2 = BOMInput()
    >>> bom.inputs.append(input2)
    >>> input2.product = component2
    >>> input2.quantity = 150
    >>> input2.uom = centimeter
    >>> output = BOMOutput()
    >>> bom.outputs.append(output)
    >>> output.product = product
    >>> output.quantity = 1
    >>> bom.save()

    >>> ProductBom = Model.get('product.product-production.bom')
    >>> product.boms.append(ProductBom(bom=bom))
    >>> product.save()

Create an Inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> InventoryLine = Model.get('stock.inventory.line')
    >>> Location = Model.get('stock.location')
    >>> storage, = Location.find([
    ...         ('code', '=', 'STO'),
    ...         ])
    >>> inventory = Inventory()
    >>> inventory.location = storage
    >>> inventory_line1 = InventoryLine()
    >>> inventory.lines.append(inventory_line1)
    >>> inventory_line1.product = component1
    >>> inventory_line1.quantity = 200
    >>> inventory_line2 = InventoryLine()
    >>> inventory.lines.append(inventory_line2)
    >>> inventory_line2.product = component2
    >>> inventory_line2.quantity = 60
    >>> inventory.save()
    >>> Inventory.confirm([inventory.id], config.context)
    >>> inventory.state
    'done'

Configure production sequence::

    >>> Sequence = Model.get('ir.sequence')
    >>> Config = Model.get('production.configuration')
    >>> config = Config()
    >>> config.output_lot_creation = 'done'
    >>> output_sequence = Sequence(code='stock.lot', name='Output Sequence')
    >>> output_sequence.save()
    >>> config.output_lot_sequence = output_sequence
    >>> config.save()

Make a production::

    >>> Production = Model.get('production')
    >>> production = Production()
    >>> production.product = product
    >>> production.bom = bom
    >>> production.quantity = 2
    >>> production.click('wait')
    >>> production.click('assign_try')
    True
    >>> production.click('run')
    >>> production.click('done')
    >>> output, = production.outputs
    >>> output.state
    'done'
    >>> output.lot.number
    '1'
    >>> output_sequence.reload()
    >>> output_sequence.number_next == 2
    True


Make a production which uses the lot from product::

    >>> product_sequence = Sequence(code='stock.lot', name='Product Sequence')
    >>> product_sequence.save()
    >>> template.lot_sequence = product_sequence
    >>> template.save()
    >>> template.reload()
    >>> product.reload()
    >>> production = Production()
    >>> production.effective_date = yesterday
    >>> production.product = product
    >>> production.bom = bom
    >>> production.quantity = 2
    >>> production.click('wait')
    >>> production.click('assign_try')
    True
    >>> production.click('run')
    >>> production.click('done')
    >>> output, = production.outputs
    >>> output.state
    'done'
    >>> output.lot.number
    '2'
    >>> output_sequence.reload()
    >>> output_sequence.number_next == 3
    True
    >>> product_sequence.reload()
    >>> product_sequence.number_next == 1
    True
