import inkex
from layer_manager_lib import set_up_sew_sequence


class SewSequence(inkex.EffectExtension):
    def effect(self):
        set_up_sew_sequence(self.svg)


if __name__ == '__main__':
    SewSequence().run()
