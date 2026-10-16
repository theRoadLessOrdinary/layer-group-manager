import inkex
from layer_manager_lib import expand_recursively


class ExpandRecursive(inkex.EffectExtension):
    def effect(self):
        expand_recursively(self.svg)


if __name__ == '__main__':
    ExpandRecursive().run()
