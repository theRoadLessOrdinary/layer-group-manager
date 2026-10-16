import inkex
from layer_manager_lib import move_first_above_second


class MoveAbove(inkex.EffectExtension):
    def effect(self):
        move_first_above_second(self.svg)


if __name__ == '__main__':
    MoveAbove().run()
