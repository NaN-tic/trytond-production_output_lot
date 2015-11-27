#:inside:production/production:section:configuration#

En el campo |output_lot_creation| debemos definir en que momento se crearán los
lotes de salida de producción.  Los valores possibles són:

* *Producción en curso*: Los lotes de salida se creara al passar la producción
  en estado *En Curso*.
* *Producción realizada*: Los lotes de salida se creara al finalizar la
  producción.

Una vez definido el momento de creación del lote, deberemos definir una
sequencia en el campo |output_lot_sequence|. Esta sequencia se utilizará
para generar los números de lotes de las salidas de la producción.



.. |output_lot_creation| field:: production.configuration/output_lot_creation
.. |output_lot_sequence| field:: production.configuration/output_lot_sequence


#:inside:production/production:section:producir_materiales#

Creación de lotes de salida
---------------------------

Se creará un lote para cada uno de los movimientos que tengamos definidos en
la salida de una producción. En la :ref:`Configuración<sale-configuration>`
de la producción debemos definiren que momento se crean los lotes. Los valores
possibles són:

* *Producción en curso*: Los lotes de salida se creara al passar la producción
  en estado *En Curso*.
* *Producción realizada*: Los lotes de salida se creara al finalizar la
  producción.

En caso de que assignemos un lote en los movimientos de salida antes de alguno
de estos dos estados, el sistema no creará nuevos lotes, sinó que respetará los
que ya hagamos introducido previamente.
