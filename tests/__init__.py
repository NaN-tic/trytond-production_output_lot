# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.production_output_lot.tests.test_production_output_lot import suite
except ImportError:
    from .test_production_output_lot import suite

__all__ = ['suite']
