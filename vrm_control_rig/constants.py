"""Shared constants for VRM Control Rig."""

ADDON_ID = "vrm_control_rig"

CONTROL_COLLECTION = "Controls"
HELPER_COLLECTION = "Helpers"
SHAPE_COLLECTION = "_VRM Control Rig Shapes"

# Prefixes for generated bones
P_CTRL = "CTRL-"
P_IK = "IK-"
P_MCH = "MCH-"

# Bone Names
B_ROOT = P_CTRL + "Root"
B_HIPS = P_IK + "Hips"
B_EYES = P_CTRL + "Eyes"

B_EYE_TARGET_L = P_MCH + "Eye_Target.L"
B_EYE_TARGET_R = P_MCH + "Eye_Target.R"

B_HAND_IK_L = P_IK + "Hand.L"
B_HAND_IK_R = P_IK + "Hand.R"
B_FOOT_IK_L = P_IK + "Foot.L"
B_FOOT_IK_R = P_IK + "Foot.R"

B_ELBOW_POLE_L = P_MCH + "Elbow_Pole.L"
B_ELBOW_POLE_R = P_MCH + "Elbow_Pole.R"
B_KNEE_POLE_L = P_MCH + "Knee_Pole.L"
B_KNEE_POLE_R = P_MCH + "Knee_Pole.R"

# Finger Controls
B_THUMB_CURL_L = P_CTRL + "Thumb_Curl.L"
B_INDEX_CURL_L = P_CTRL + "Index_Curl.L"
B_MIDDLE_CURL_L = P_CTRL + "Middle_Curl.L"
B_RING_CURL_L = P_CTRL + "Ring_Curl.L"
B_LITTLE_CURL_L = P_CTRL + "Little_Curl.L"

B_THUMB_CURL_R = P_CTRL + "Thumb_Curl.R"
B_INDEX_CURL_R = P_CTRL + "Index_Curl.R"
B_MIDDLE_CURL_R = P_CTRL + "Middle_Curl.R"
B_RING_CURL_R = P_CTRL + "Ring_Curl.R"
B_LITTLE_CURL_R = P_CTRL + "Little_Curl.R"

GENERATED_BONES = (
    B_ROOT,
    B_HIPS,
    B_EYES,
    B_EYE_TARGET_L,
    B_EYE_TARGET_R,
    B_HAND_IK_L,
    B_HAND_IK_R,
    B_FOOT_IK_L,
    B_FOOT_IK_R,
    B_THUMB_CURL_L,
    B_INDEX_CURL_L,
    B_MIDDLE_CURL_L,
    B_RING_CURL_L,
    B_LITTLE_CURL_L,
    B_THUMB_CURL_R,
    B_INDEX_CURL_R,
    B_MIDDLE_CURL_R,
    B_RING_CURL_R,
    B_LITTLE_CURL_R,
    B_ELBOW_POLE_L,
    B_ELBOW_POLE_R,
    B_KNEE_POLE_L,
    B_KNEE_POLE_R,
)

CONTROL_BONES = (
    B_ROOT,
    B_HIPS,
    B_EYES,
    B_HAND_IK_L,
    B_HAND_IK_R,
    B_FOOT_IK_L,
    B_FOOT_IK_R,
    B_THUMB_CURL_L,
    B_INDEX_CURL_L,
    B_MIDDLE_CURL_L,
    B_RING_CURL_L,
    B_LITTLE_CURL_L,
    B_THUMB_CURL_R,
    B_INDEX_CURL_R,
    B_MIDDLE_CURL_R,
    B_RING_CURL_R,
    B_LITTLE_CURL_R,
)

HELPER_BONES = (
    B_EYE_TARGET_L,
    B_EYE_TARGET_R,
    B_ELBOW_POLE_L,
    B_ELBOW_POLE_R,
    B_KNEE_POLE_L,
    B_KNEE_POLE_R,
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
