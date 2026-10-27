# Layer Group Manager

Inkscape extensions for showing, hiding, locking and arranging layers, groups and objects, plus one for embroidery stitch order.

| Menu entry | Menu location | Extension ID |
|---|---|---|
| **Layer Manager** | General > Layers | `layers_cmd_deck` |
| **Expand Recursively** | General > Layers | `layers_cmd_deck.expand_recursive` |
| **Move 1st Selected Above 2nd** | General > Layers | `layers_cmd_deck.move_above` |
| **Move 1st Selected Above 2nd + Stitch Order** | General > Layers | `layers_cmd_deck.move_above_stitch_order` |
| **Set Sew Sequence (Trim/Lock Stitch)** | Embroidery > Stitch Settings | `layers_cmd_deck.sew_sequence` |

All are under **Extensions > Map's Edge Tools**. They are also buttons on the [Map's Edge Tool Panel](https://github.com/theRoadLessOrdinary/maps-edge-panel).

## Layer Manager

A dialog of buttons. A selected layer, group or object counts together with everything inside it.

| Button | What it does |
|---|---|
| Hide all but selected | Hides every other object, group and layer in the document |
| Show all but selected | Shows every other object, group and layer |
| Lock all but selected | Locks every other object, group and layer |
| Unlock all but selected | Unlocks every other object, group and layer |
| Toggle Visible | Flips the selection's visibility; everything inside a selected item gets that item's new state |
| Toggle Lock | Flips the selection's lock the same way |
| Show All | Shows everything in the document; needs no selection |
| Unlock All | Unlocks everything in the document; needs no selection |

## Expand Recursively

Select one or more layers or groups. Each one, and every layer and group inside it, is opened in the Layers and Objects panel.

## Move 1st Selected Above 2nd

Select two or more layers or objects. The last one you click is the target. Everything selected before it is stacked directly above it, in click order: the one clicked just before the target ends up next to it, the first one clicked ends up on top.

**Move 1st Selected Above 2nd + Stitch Order** (same menu, also no dialog; in the Tool Panel, the Also change stitch order checkbox beside the button) does the same move, and the moved items also get [Stitch Order](https://github.com/theRoadLessOrdinary/stitch-order) numbers right after the target's, in the order they now stack. The target needs a stitch order number, and the Stitch Order extension must be installed in the same extensions directory.

## Set Sew Sequence (Trim/Lock Stitch)

Select two or more embroidery objects in the order they will sew. Then:

- First object: lock stitch before.
- Objects in between: no lock stitch.
- Last object: lock stitch after, plus an Ink/Stitch trim command.
- A trim command already on any of the other selected objects is removed.

The trim command uses Ink/Stitch's own trim symbol, read from an Ink/Stitch install in a folder named `inkstitch` (or `inkstitch-dev`) in the same extensions directory.

The tools other than Layer Manager have no dialog, so each can be bound to a key in **Edit > Preferences > Interface > Keyboard Shortcuts**.

## Requirements

- Inkscape 1.x (developed and used on Inkscape 1.4.4, Flatpak, on Linux; other platforms have not been tried)
- Ink/Stitch installed in the same extensions directory, for Set Sew Sequence

## Install

Copy the files in this repository into a folder of their own inside Inkscape's user extensions directory, then restart Inkscape. To find that directory, open **Edit > Preferences > System** and look at **User extensions**. Typical locations:

| Install type | User extensions folder |
|---|---|
| Linux (native) | `~/.config/inkscape/extensions/` |
| Linux (Flatpak) | `~/.var/app/org.inkscape.Inkscape/config/inkscape/extensions/` |
| macOS | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/` |
| Windows | `%APPDATA%\inkscape\extensions\` |

For example, on native Linux:

```bash
git clone https://github.com/theRoadLessOrdinary/layer-group-manager.git \
    ~/.config/inkscape/extensions/LayerGroupManager
```

Keep all the files together in one folder: `layer_manager_lib.py` holds the shared code. The [Map's Edge Tool Panel](https://github.com/theRoadLessOrdinary/maps-edge-panel) finds these tools only in a folder named `LayerGroupManager`.

To uninstall, delete the folder and restart Inkscape.
