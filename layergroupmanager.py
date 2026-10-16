
import inkex
import argparse

VERSION = "1.6.0"  # Increment this version number with each change


class LayersCmdDeck(inkex.EffectExtension):

    def add_arguments(self, pars):
        # NOTE: type=bool is a classic Python/argparse trap for these --xxx=true/false
        # style params -- Python's bool("false") is True (any non-empty string is
        # truthy). inkex.Boolean parses Inkscape's actual "true"/"false" param
        # strings correctly.
        pars.add_argument('--tab', type=str, default='main', help='Tab to display')
        pars.add_argument('--hide_others', type=inkex.Boolean, default=False, help='Hide other elements')
        pars.add_argument('--show_others', type=inkex.Boolean, default=False, help='Show other elements')
        pars.add_argument('--lock_others', type=inkex.Boolean, default=False, help='Lock other elements')
        pars.add_argument('--unlock_others', type=inkex.Boolean, default=False, help='Unlock other elements')
        pars.add_argument('--toggle_visible', type=inkex.Boolean, default=False, help='Toggle visibility of selected elements')
        pars.add_argument('--toggle_lock', type=inkex.Boolean, default=False, help='Toggle lock of selected elements')
        pars.add_argument('--show_all', type=inkex.Boolean, default=False, help='Show every hidden element')
        pars.add_argument('--unlock_all', type=inkex.Boolean, default=False, help='Unlock every locked element')
        # --output, --id, and --selected-nodes are already registered by the
        # base EffectExtension class; redeclaring them here raised
        # argparse.ArgumentError on every invocation (this extension never
        # actually ran because of it).
        self.dialog_title = f"Layer Group Manager - v{VERSION}"

    def effect(self):
        selected_ids = set(self.options.ids)

        def style_get(node):
            return inkex.Style(node.get('style'))

        def style_set(node, style):
            node.set('style', str(style))

        # One element set for every action, so they all behave the same
        # regardless of element type (text, ellipse, image, use, etc. are
        # all hideable/lockable from the Objects panel). Left out: the
        # root <svg> itself, <defs> and everything in it, the non-drawing
        # elements, and the insides of a <text> (tspans are part of their
        # text object, not objects of their own -- hiding them would blank
        # a selected text).
        elements = [n for n in self.svg.xpath(
            '//svg:*[not(ancestor-or-self::svg:defs) and not(ancestor::svg:text)'
            ' and not(self::svg:metadata or self::svg:title or self::svg:desc'
            ' or self::svg:style or self::svg:script)]',
            namespaces=inkex.NSS) if n is not self.svg]
        selected_elements = []

        for element in elements:
            if element.get('id') in selected_ids:
                selected_elements.append(element)

        def set_display(node, value):
            style = style_get(node)
            style['display'] = value
            style_set(node, style)

        # Inkscape treats an element as locked whenever sodipodi:insensitive
        # is present at all, whatever its value (sp-item.cpp does
        # `sensitive = !value` on the raw attribute string), so "false"
        # still means locked. Unlocking has to remove the attribute, and
        # "is it locked" has to test for presence, not for "true".
        def set_lock(node, locked):
            if locked:
                node.set(inkex.addNS('insensitive', 'sodipodi'), 'true')
            else:
                node.attrib.pop(inkex.addNS('insensitive', 'sodipodi'), None)

        def is_hidden(node):
            # The style property wins over the display presentation
            # attribute, so only fall back to the attribute when the style
            # doesn't say anything.
            display = style_get(node).get('display')
            if display is None:
                display = node.get('display')
            return display == 'none'

        def is_locked(node):
            return node.get(inkex.addNS('insensitive', 'sodipodi')) is not None

        # Show All / Unlock All work on the whole document and need no
        # selection, so they run before the selection check below. They
        # only touch elements that are actually hidden/locked.
        for element in elements:
            if self.options.show_all and is_hidden(element):
                set_display(element, 'inline')
            if self.options.unlock_all and is_locked(element):
                set_lock(element, False)

        if not selected_elements:
            return

        # Every action treats a selected element together with everything
        # inside it as one unit: the "all but selected" actions leave the
        # whole subtree alone, and the toggles apply to the whole subtree.
        element_set = set(elements)
        selected_set = set(selected_elements)

        def subtree(node):
            return [node] + [d for d in node.iterdescendants() if d in element_set]

        # A selected element that sits inside another selected element is
        # already covered by that one's subtree; handling it again on its
        # own would flip it a second time in the toggles.
        selected_roots = [e for e in selected_elements
                          if not any(a in selected_set for a in e.iterancestors())]

        selected_scope = set()
        for root in selected_roots:
            selected_scope.update(subtree(root))

        others = [e for e in elements if e not in selected_scope]

        # Handle the command-line arguments and apply to elements
        if self.options.hide_others:
            for element in others:
                set_display(element, 'none')

        if self.options.show_others:
            for element in others:
                set_display(element, 'inline')

        if self.options.lock_others:
            for element in others:
                set_lock(element, True)

        if self.options.unlock_others:
            for element in others:
                set_lock(element, False)

        # The toggles take the new state from each selected element's own
        # current state and apply that one state to it and everything
        # inside it (flipping each child from its own state would leave a
        # mixed subtree).
        if self.options.toggle_visible:
            for root in selected_roots:
                value = 'inline' if is_hidden(root) else 'none'
                for node in subtree(root):
                    set_display(node, value)

        if self.options.toggle_lock:
            for root in selected_roots:
                locked = not is_locked(root)
                for node in subtree(root):
                    set_lock(node, locked)

        # No explicit save call here: EffectExtension.run() serializes
        # self.svg to output itself once effect() returns. (A prior
        # `self.svg.save()` call here was a no-op method that doesn't exist
        # on SvgDocumentElement -- it raised AttributeError on every click.)


if __name__ == '__main__':
    # This was missing entirely -- without it, running this file does
    # nothing at all (the class gets defined, nothing gets invoked).
    LayersCmdDeck().run()
