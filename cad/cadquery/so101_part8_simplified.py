"""Facet the lower side skirts, retaining the exact upstream motor interfaces.

This is a STEP-backed modification, not the approximate native reconstruction.
The shared loader pins the original source for both the candidate and comparison.
All dimensions are millimetres in the original part frame.
"""

import cadquery as cq

from so101_part8 import CAGE_INNER_Y


# End below the original contour; retain the bottom seat starting at x=9.8.
SKIRT_FACET = ((-18.0, -19.7), (9.8, -32.41))


def part8_simplified(original: cq.Shape) -> cq.Workplane:
    """Replace the curved underside of both side skirts with one planar facet.

    A keepout protects the rails and heel across the 24.8 mm motor cavity.
    The lower mounting seat, roll ears, bores, clips and foot are also retained.
    No material is added to the motor cavity or the motion envelope.
    """
    if not original.isValid() or len(original.Solids()) != 1:
        raise ValueError("part 8 requires one valid source solid")
    original = original.Solids()[0]
    left, right = SKIRT_FACET
    cutter = (
        cq.Workplane("XZ")
        .polyline([left, right, (right[0], -45.0), (left[0], -45.0)])
        .close()
        .extrude(30.0, both=True)
    )
    # The rails end at x=-10.6; keep another 0.1 mm of their supporting heel.
    rail_keepout = cq.Solid.makeBox(
        40, 2 * CAGE_INNER_Y, 100, (-50.5, -CAGE_INNER_Y, -45)
    )
    return cq.Workplane(obj=original).cut(cutter.cut(rail_keepout)).clean()
