"""Shared constants for VRM Control Rig."""

ADDON_ID = "vrm_control_rig"

CONTROL_COLLECTION = "Controls"
HELPER_COLLECTION = "Helpers"
SHAPE_COLLECTION = "_VRM Control Rig Shapes"

GENERATED_BONES = (
    "Root_CTRL",
    "Hips_IK",
    "Eyes_CTRL",
    "Eye_Target.L",
    "Eye_Target.R",
    "Hand_IK.L",
    "Hand_IK.R",
    "Foot_IK.L",
    "Foot_IK.R",
    "Thumb_Curl.L",
    "Index_Curl.L",
    "Middle_Curl.L",
    "Ring_Curl.L",
    "Little_Curl.L",
    "Thumb_Curl.R",
    "Index_Curl.R",
    "Middle_Curl.R",
    "Ring_Curl.R",
    "Little_Curl.R",
    "Elbow_Pole.L",
    "Elbow_Pole.R",
    "Knee_Pole.L",
    "Knee_Pole.R",
)

CONTROL_BONES = (
    "Root_CTRL",
    "Hips_IK",
    "Eyes_CTRL",
    "Hand_IK.L",
    "Hand_IK.R",
    "Foot_IK.L",
    "Foot_IK.R",
    "Thumb_Curl.L",
    "Index_Curl.L",
    "Middle_Curl.L",
    "Ring_Curl.L",
    "Little_Curl.L",
    "Thumb_Curl.R",
    "Index_Curl.R",
    "Middle_Curl.R",
    "Ring_Curl.R",
    "Little_Curl.R",
)

HELPER_BONES = (
    "Eye_Target.L",
    "Eye_Target.R",
    "Elbow_Pole.L",
    "Elbow_Pole.R",
    "Knee_Pole.L",
    "Knee_Pole.R",
)

IK_CONSTRAINT_NAME = "VRM Control Rig IK"
ROOT_CONSTRAINT_NAME = "VRM Control Rig Root"
ROTATION_CONSTRAINT_NAME = "VRM Control Rig Rotation"
EYE_CONSTRAINT_NAME = "VRM Control Rig Eye Track"
FINGER_CURL_CONSTRAINT_NAME = "VRM Control Rig Finger Curl"
FINGER_CURL_DRIVER_GROUP = "VRM Control Rig Finger Curl"
FINGER_CURL_DRIVER_TAG = "vcr_finger_curl"

HUMANOID_BONES = (
    "hips",
    "spine",
    "chest",
    "upper_chest",
    "neck",
    "head",
    "eye.L",
    "eye.R",
    "upper_arm.L",
    "lower_arm.L",
    "hand.L",
    "upper_arm.R",
    "lower_arm.R",
    "hand.R",
    "upper_leg.L",
    "lower_leg.L",
    "foot.L",
    "upper_leg.R",
    "lower_leg.R",
    "foot.R",
)

# Upper chest and chest are optional in some VRM files. The rig can still build
# useful root and limb controls without them.
REQUIRED_BONES = (
    "hips",
    "spine",
    "neck",
    "head",
    "upper_arm.L",
    "lower_arm.L",
    "hand.L",
    "upper_arm.R",
    "lower_arm.R",
    "hand.R",
    "upper_leg.L",
    "lower_leg.L",
    "foot.L",
    "upper_leg.R",
    "lower_leg.R",
    "foot.R",
)
