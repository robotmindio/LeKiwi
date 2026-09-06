"""Facet the lower side skirts, retaining the exact upstream motor interfaces.

This is a STEP-backed modification, not the approximate native reconstruction.
The shared loader pins the original source for both the candidate and comparison.
All dimensions are millimetres in the original part frame.
"""

import cadquery as cq

# Start beyond the rail ending at x=-10.6; stop before the seat at x=9.8.
# A 0.05 mm inward offset avoids near-tangent boolean cuts in the source splines.
SKIRT_FACET = ((-10.5, -24.61), (9.8, -32.36))


def part8_simplified(original: cq.Shape) -> cq.Workplane:
    """Replace the curved underside of both side skirts with one planar facet.

    The facet stays between the rails and the lower mounting seat.
    The heel, roll ears, bores, clips and foot are also retained.
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
    return cq.Workplane(obj=original).cut(cutter).clean()
