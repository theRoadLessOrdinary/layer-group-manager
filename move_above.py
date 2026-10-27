import os
import sys

import inkex
from layer_manager_lib import move_first_above_second

STITCH_ORDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stitch-order')


class MoveAbove(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument('--stitch_order', type=inkex.Boolean, default=False)

    def effect(self):
        selected = list(self.svg.selection)
        if not move_first_above_second(self.svg):
            return
        if self.options.stitch_order:
            self.follow_in_stitch_order(selected)

    def follow_in_stitch_order(self, selected):
        """Number the moved items to sew right after the target, in the
        order they now stack (click order)."""
        *sources, target = selected
        sys.path.insert(0, STITCH_ORDER_DIR)
        try:
            import stitch_order as so
        except ImportError:
            inkex.errormsg('Stitch order not changed: the Stitch Order extension was not found.')
            return
        root = self.document.getroot()
        order = so.tagged_in_order(root)
        if target not in order:
            inkex.errormsg('Moved, but the stitch order was not changed: the target '
                           '(clicked last) has no stitch order number.')
            return
        rest = [n for n in order if n not in sources]
        at = rest.index(target) + 1
        so.write_order(rest[:at] + sources + rest[at:])
        so.StitchOrder.record_order(root)


if __name__ == '__main__':
    MoveAbove().run()
