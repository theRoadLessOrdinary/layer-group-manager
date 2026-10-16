"""
Shared logic for the Layer Manager family of extensions (layergroupmanager.py,
move_above.py, expand_recursive.py, sew_sequence.py). Each of those is a thin
inkex.EffectExtension wrapper; this module holds the actual behavior so it's
not duplicated across files that each need to be their own standalone,
param-less .inx entry (a param-less .inx is what makes Inkscape run the
script immediately on menu click instead of opening a dialog with a shared
Apply button).
"""

import inkex
import os
from copy import deepcopy
from lxml import etree

# --- Ink/Stitch interop constants -------------------------------------
# Ink/Stitch stores its own attributes under this namespace (see
# inkstitch/lib/svg/tags.py: etree.register_namespace + inkex.NSS entry).
# Registering it here too (not just in inkex.NSS) is what makes lxml reuse
# a single "inkstitch:" prefix declared once on the root, instead of
# minting a fresh ns0/ns1/ns2... prefix per attribute on documents that
# haven't already used Ink/Stitch (and so don't have it pre-declared).
etree.register_namespace('inkstitch', 'http://inkstitch.org/namespace')
inkex.NSS['inkstitch'] = 'http://inkstitch.org/namespace'

INKSCAPE_LABEL = inkex.addNS('label', 'inkscape')
CONNECTION_START = inkex.addNS('connection-start', 'inkscape')
CONNECTION_END = inkex.addNS('connection-end', 'inkscape')
CONNECTOR_TYPE = inkex.addNS('connector-type', 'inkscape')
XLINK_HREF = inkex.addNS('href', 'xlink')
SVG_PATH_TAG = inkex.addNS('path', 'svg')
SVG_USE_TAG = inkex.addNS('use', 'svg')
SVG_GROUP_TAG = inkex.addNS('g', 'svg')
TIES_ATTR = inkex.addNS('ties', 'inkstitch')

# Ties: 0 = Both | 1 = Before | 2 = After | 3 = Neither
# (matches inkstitch/lib/elements/element.py's 'ties' param dropdown order)
TIES_BEFORE = '1'
TIES_AFTER = '2'
TIES_NEITHER = '3'

_inkstitch_symbols_cache = None


def _load_inkstitch_symbols():
    """
    Find and parse Ink/Stitch's bundled symbols/inkstitch.svg, which holds
    the <symbol> definitions (trim, stop, etc.) used by its command markers.
    Ink/Stitch is installed as a sibling extension in the same Inkscape
    extensions directory, so we look there instead of vendoring a copy that
    could drift out of sync with the real one.
    """
    global _inkstitch_symbols_cache
    if _inkstitch_symbols_cache is not None:
        return _inkstitch_symbols_cache

    extensions_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for candidate in ('inkstitch', 'inkstitch-dev'):
        symbols_path = os.path.join(extensions_dir, candidate, 'symbols', 'inkstitch.svg')
        if os.path.isfile(symbols_path):
            with open(symbols_path) as f:
                _inkstitch_symbols_cache = inkex.load_svg(f).getroot()
            return _inkstitch_symbols_cache

    return None


# --- Ported from inkstitch/lib/svg/path.py -----------------------------
# Reproduced here (rather than imported) so this extension keeps working
# even if Ink/Stitch isn't installed/enabled, and doesn't depend on its
# internal (non-public) module layout. This is the exact transform math
# Ink/Stitch itself uses to place command markers in absolute document
# coordinates regardless of the target's ancestor transforms and the
# document's viewBox scaling (e.g. mm-unit documents with a px viewBox).

def _get_viewbox(svg):
    viewbox = svg.get('viewBox')
    if viewbox is None:
        viewbox = "0 0 0 0"
    return viewbox.strip().replace(',', ' ').split()


def _get_doc_size(svg):
    width = svg.get('width')
    height = svg.get('height')

    if width == "100%" and height == "100%":
        width = None
        height = None

    if width is None or height is None:
        viewbox = _get_viewbox(svg)
        width = viewbox[2]
        height = viewbox[3]

    doc_width = _convert_length(width)
    doc_height = _convert_length(height)

    return doc_width, doc_height


def _convert_length(length):
    value, units = inkex.units.parse_unit(str(length))
    if not units:
        units = 'px'
    return inkex.units.convert_unit(f"{value}{units}", 'px')


def _get_viewbox_transform(node):
    doc_width, doc_height = _get_doc_size(node)
    viewbox = _get_viewbox(node)

    dx = -float(viewbox[0])
    dy = -float(viewbox[1])
    transform = inkex.transforms.Transform("translate(%f, %f)" % (dx, dy))

    try:
        sx = doc_width / float(viewbox[2])
        sy = doc_height / float(viewbox[3])

        aspect_ratio = node.get('preserveAspectRatio', 'xMidYMid meet')
        if aspect_ratio != 'none':
            sx = sy = max(sx, sy) if 'slice' in aspect_ratio else min(sx, sy)

        scale_transform = inkex.transforms.Transform("scale(%f, %f)" % (sx, sy))
        transform = transform @ scale_transform
    except ZeroDivisionError:
        pass

    return transform


def _compose_parent_transforms(node, mat):
    trans = node.get('transform')
    if trans:
        mat = inkex.transforms.Transform(trans) @ mat
    parent = node.getparent()
    if parent is not None and parent.tag == SVG_GROUP_TAG:
        mat = _compose_parent_transforms(parent, mat)
    return mat


def _get_node_transform(node):
    transform = inkex.transforms.Transform([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    if node.getparent() is not None:
        transform = _compose_parent_transforms(node, transform)
    viewbox_transform = _get_viewbox_transform(node.getroottree().getroot())
    transform = viewbox_transform @ transform
    return transform


def _get_correction_transform(node):
    """Transform to apply to a new sibling of node so absolute coordinates work."""
    parent = node.getparent()
    if parent is not None:
        transform = _get_node_transform(parent)
    else:
        transform = inkex.Transform()
    return str(-transform)


# --- Trim command (ported from inkstitch/lib/commands.py) --------------

def _ensure_trim_symbol(svg):
    """Make sure the 'trim' symbol definition exists in this doc's <svg:defs>."""
    path = "./*[@id='inkstitch_trim']"
    defs = svg.defs
    if defs.find(path) is not None:
        return

    symbols_svg = _load_inkstitch_symbols()
    if symbols_svg is None:
        raise RuntimeError(
            "Could not find Ink/Stitch's symbols/inkstitch.svg. "
            "Is Ink/Stitch installed alongside Layer Manager?"
        )

    symbol = deepcopy(symbols_svg.defs.find(path))
    if symbol is None:
        raise RuntimeError("Ink/Stitch's symbols file has no 'trim' symbol.")

    symbol.set('transform', 'scale(0.25)')
    style = inkex.Style(symbol.get('style'))
    style['opacity'] = 0.7
    symbol.set('style', str(style))
    defs.append(symbol)


def _find_trim_command_group(node):
    """
    Find the command group (if any) that attaches a trim command to node,
    by locating a connector path whose connection-end points at node's id
    and whose sibling <use> in the same group references the trim symbol.
    """
    node_id = node.get('id')
    if not node_id:
        return None

    root = node.getroottree().getroot()
    for connector in root.iter(SVG_PATH_TAG):
        if connector.get(CONNECTION_END) != f'#{node_id}':
            continue
        group = connector.getparent()
        if group is None:
            continue
        for use in group.iterfind(SVG_USE_TAG):
            if use.get(XLINK_HREF) == '#inkstitch_trim':
                return group

    return None


def _remove_trim_command(node):
    group = _find_trim_command_group(node)
    if group is not None and group.getparent() is not None:
        group.getparent().remove(group)


def _add_trim_command(document, node):
    if _find_trim_command_group(node) is not None:
        return  # already there

    _ensure_trim_symbol(document)

    parent = node.getparent()
    group = inkex.Group(attrib={
        'id': document.get_unique_id('command_group'),
        INKSCAPE_LABEL: 'Ink/Stitch Command: Trim thread after sewing this object',
        'transform': _get_correction_transform(node),
    })
    parent.insert(parent.index(node) + 1, group)

    if node.get('id') is None:
        node.set('id', document.get_unique_id('object'))

    transform = _get_node_transform(parent) if parent is not None else inkex.Transform()
    try:
        bbox = node.bounding_box(transform)
    except Exception:
        bbox = None

    if bbox is not None:
        pos_x, pos_y = bbox.right, bbox.top
        center_x, center_y = bbox.center_x, bbox.center_y
    else:
        # Fall back to the origin if we can't compute a bounding box (e.g.
        # an empty group) -- the marker will need to be dragged into place.
        pos_x = pos_y = center_x = center_y = 0

    symbol = inkex.Use(attrib={
        'id': document.get_unique_id('command_use'),
        XLINK_HREF: '#inkstitch_trim',
        'height': '100%',
        'width': '100%',
        'x': str(pos_x),
        'y': str(pos_y),
        INKSCAPE_LABEL: 'command marker',
    })
    group.append(symbol)

    connector = inkex.PathElement(attrib={
        'id': document.get_unique_id('command_connector'),
        'd': f'M {pos_x},{pos_y} {center_x},{center_y}',
        'style': ('fill:none;stroke:#000000;stroke-width:1;stroke-opacity:0.5;'
                  'vector-effect: non-scaling-stroke;-inkscape-stroke: hairline;'),
        CONNECTION_START: f'#{symbol.get("id")}',
        CONNECTION_END: f'#{node.get("id")}',
        CONNECTOR_TYPE: 'polyline',
        INKSCAPE_LABEL: 'connector',
    })
    # Connector goes inside the same group, before the symbol -- matching
    # inkstitch/lib/commands.py's add_connector, which does
    # `symbol.getparent().insert(0, path)`.
    group.insert(0, connector)


# --- Actions (one per standalone action-button extension) --------------

def move_first_above_second(svg):
    """
    Select two or more layers/objects. The last one clicked is the target;
    everyone selected before it gets stacked together directly above it, in
    the order they were clicked (the one clicked right before the target
    ends up closest to it, the one clicked first ends up on top of the
    whole group).

    Click order matters here (unlike hide/show/lock/unlock, which treat the
    selection as an unordered set), so this reads svg.selection directly
    instead of a set of ids.
    """
    selected = list(svg.selection)

    if len(selected) < 2:
        inkex.errormsg("Move above needs at least two selected items (source(s), then target last).")
        return

    *sources, target = selected

    if any(source.get('id') == target.get('id') for source in sources):
        inkex.errormsg("Move above source(s) and target must be different.")
        return

    for source in sources:
        if target in source.iterancestors():
            inkex.errormsg(f"Move above refused: target is an ancestor of source {source.get('id')}.")
            return
        if target in source.iterdescendants():
            inkex.errormsg(f"Move above refused: target is a descendant of source {source.get('id')}.")
            return

    # addnext() detaches a node from wherever it currently lives and
    # reinserts it as the given node's immediate following sibling. Later
    # siblings paint on top, so walking sources in click order and each
    # time inserting right after the last-placed one builds the whole
    # group directly above target, in their original click order
    # (last-clicked source ends up topmost).
    #
    # addnext() only reparents -- it doesn't touch the moved node's own
    # transform attribute. If a source lives in a different layer/group
    # than target (different accumulated transform), the node keeps its
    # old local transform but is now interpreted under the new parent's
    # transform stack, so it visually jumps/rescales. Match
    # _add_trim_command's fix: compute each source's absolute transform
    # before the move, then set its local transform so it renders in the
    # same place under target's parent afterward.
    new_parent = target.getparent()
    new_parent_transform = _get_node_transform(new_parent) if new_parent is not None else inkex.Transform()

    anchor = target
    for source in sources:
        needs_correction = source.getparent() is not new_parent
        old_absolute_transform = _get_node_transform(source) if needs_correction else None

        anchor.addnext(source)
        anchor = source

        if needs_correction:
            source.set('transform', str((-new_parent_transform) @ old_absolute_transform))


def expand_recursively(svg):
    """
    Starting at each selected layer/group, clear the collapsed flag on it
    and on every descendant group/layer, so the Objects/Layers panel opens
    the whole subtree. Inkscape stores a group's collapsed state in the
    XML editor/objects panel as the inkscape:collapsed attribute ("true" =
    collapsed; absent or "false" = expanded).
    """
    collapsed_attr = inkex.addNS('collapsed', 'inkscape')
    selected = list(svg.selection)

    if not selected:
        inkex.errormsg("Expand recursively needs at least one selected layer/group.")
        return

    for node in selected:
        if node.TAG != 'g':
            continue
        node.set(collapsed_attr, 'false')
        for descendant in node.iterdescendants():
            if descendant.TAG == 'g':
                descendant.set(collapsed_attr, 'false')


def set_up_sew_sequence(svg):
    """
    Select >=2 stitchable objects, in the order they'll be sewn (click
    order, like move_first_above_second). Sets each one's Ink/Stitch 'ties'
    (lock stitch) attribute and trim command per its position:

      1st object:        ties = Before  ("lock stitch = beginning"), no trim
      middle object(s):  ties = Neither,                            no trim
      last object:       ties = After   ("lock stitch = after"),    trim

    "No trim" means removing an existing trim command if one is already
    attached, not just skipping the add.
    """
    selected = list(svg.selection)

    if len(selected) < 2:
        inkex.errormsg("Set sew sequence needs at least two selected stitchable objects, in sew order.")
        return

    last_index = len(selected) - 1

    for i, node in enumerate(selected):
        if i == 0:
            node.set(TIES_ATTR, TIES_BEFORE)
        elif i == last_index:
            node.set(TIES_ATTR, TIES_AFTER)
        else:
            node.set(TIES_ATTR, TIES_NEITHER)

        if i == last_index:
            _add_trim_command(svg, node)
        else:
            _remove_trim_command(node)
