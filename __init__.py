# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import production
from . import bom


def register():
    Pool.register(
        bom.BOMInput,
        production.Configuration,
        production.ConfigurationCompany,
        production.Production,
        production.StockMove,
        module='production_output_lot', type_='model')
