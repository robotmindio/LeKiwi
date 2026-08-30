"""Run in Fusion after opening the public Static Side Gripper F3D.

Select the small Static Side Gripper BRep body.  This adds the one legacy
R3.14994 mm through-hole as a native Fusion Combine/Cut feature.
"""

import adsk.core
import adsk.fusion


MM = 0.1  # Fusion API geometry values are centimetres.
RADIUS_MM = 3.149941806669
START_MM = (-19.125301303971, -24.300928850665, -70.134244680553)
END_MM = (-19.125301303971, -22.397081810826, -73.649901720044)
FEATURE_NAME = "Legacy static-side R3.14994 through-hole"


def point(values):
    return adsk.core.Point3D.create(*(value * MM for value in values))


def run(_):
    app = adsk.core.Application.get()
    ui = app.userInterface
    target = ui.selectEntity("Select the small Static Side Gripper body", "Bodies").entity
    if target.objectType != adsk.fusion.BRepBody.classType():
        raise RuntimeError("Select a BRep body, not a component or mesh body.")

    tool_shape = adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(
        point(START_MM), RADIUS_MM * MM, point(END_MM), RADIUS_MM * MM
    )
    if not tool_shape:
        raise RuntimeError("Fusion could not create the cylindrical cut tool.")

    component = target.parentComponent
    base_feature = component.features.baseFeatures.add()
    base_feature.name = FEATURE_NAME + " tool"
    base_feature.startEdit()
    tool = component.bRepBodies.add(tool_shape, base_feature)
    base_feature.finishEdit()

    tools = adsk.core.ObjectCollection.create()
    tools.add(tool)
    cut_input = component.features.combineFeatures.createInput(target, tools)
    cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    cut_input.isKeepToolBodies = False
    cut_input.isNewComponent = False
    component.features.combineFeatures.add(cut_input).name = FEATURE_NAME
    ui.messageBox(FEATURE_NAME + " added. Export the patched body as STL for validation.")
