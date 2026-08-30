// Legacy April-2025 upper laser-cut plate.  The editable DXF is the 2D cut
// contour; this selector only gives it its original 7 mm printed thickness.

translate([0, 0, -7])
    linear_extrude(height = 7)
        import("legacy_base_plate_layer2.dxf");
