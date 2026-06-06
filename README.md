# VRM Control Rig

Blender 5.x addon that creates lightweight animation controls directly on an existing VRM humanoid armature.

It does not create a replacement armature, rename source bones, reparent the VRM hierarchy, or touch VRM spring bone settings. Generated bones are non-deforming and tagged so they can be deleted or rebuilt safely.

## File Structure

```text
vrm_control_rig/
  __init__.py        addon metadata and registration
  constants.py       generated names and shared identifiers
  properties.py      scene settings
  detection.py       VRM0/VRM1/common humanoid bone name detection
  logs.py            generation diagnostics and before/after transform logs
  shapes.py          hidden custom shape meshes
  rig.py             control bone generation, collections, constraints, delete
  bake.py            visual bake to original VRM humanoid bones
  operators.py       Blender operators
  ui.py              View3D sidebar panel
README.md
```

## Install

Zip the `vrm_control_rig` folder or copy it into Blender's addon directory, then enable **VRM Control Rig** in Blender preferences.

## Use

Select a VRM armature and open:

`View3D > Sidebar > VRM Control Rig`

Click **Generate Control Rig**.

The addon creates:

- `Root_CTRL`
- `Eyes_CTRL`
- `Eye_Target.L`, `Eye_Target.R` when eye bones are detected
- `Hand_IK.L`, `Hand_IK.R`
- `Foot_IK.L`, `Foot_IK.R`
- `Thumb_Curl.*`, `Index_Curl.*`, `Middle_Curl.*`, `Ring_Curl.*`, `Little_Curl.*` when matching finger chains are detected
- `Elbow_Pole.L`, `Elbow_Pole.R`
- `Knee_Pole.L`, `Knee_Pole.R`

Controllers are placed in the `Controls` bone collection. Pole targets and eye target bones are placed in `Helpers`.

`Hand_IK.*` and `Foot_IK.*` drive both IK position and wrist/ankle rotation. Rotate these rounded wire controllers directly when posing hands and feet.

`Root_CTRL` uses an X/Y floor circle with arrows and a center box, and its Z translation is locked. `Eyes_CTRL` moves both eye targets together, while `Eye_Target.L/R` can be adjusted individually.

Finger curl controls use local X scale to curl that one finger chain. Select an individual `*_Curl.L/R` controller and scale it in pose mode to close the matching finger.

Enable **Source Bones Wire** to make the original armature display as wire bones. Enable **Hide Extra Bones** to hide non-humanoid source bones such as skirt, hair, and accessory bones while generating controls. The addon hides those extra bones instead of deleting them so VRM spring-bone setups remain intact.

After updating from an older addon version, use **Regenerate Control Rig** so the new custom shapes, rotation constraints, and eye controls are created.

Before export, use **Bake To VRM Skeleton** to bake visual constrained motion onto the original VRM bones. Enable **Delete Controls** in the bake options when exporting to pipelines that reject extra non-deforming bones.

## Diagnostics

Generation writes detailed diagnostics to a Blender text datablock named `VRM Control Rig Log` when **Diagnostics Log** is enabled.

The log includes:

- Detected humanoid bone mapping
- Missing required bones
- Before-generation source bone position and rotation
- Generated control bone position and rotation
- After-generation source bone position and rotation
- Per-bone position and rotation deltas
- Calibrated IK pole angles
