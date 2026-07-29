import numpy as np
from keras.models import load_model
from keras.utils import load_img, img_to_array
import json
import os
from django.conf import settings
import torch
import segmentation_models_pytorch as smp
import cv2

# Model ও class mapping একবারই লোড হবে (server চালু হওয়ার সময়)
MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_models", "brain_tumor_classifier.h5")
CLASS_MAPPING_PATH = os.path.join(settings.BASE_DIR, "ml_models", "class_mapping.json")

_model = None
_class_mapping = None


def get_model():
    global _model
    if _model is None:
        _model = load_model(MODEL_PATH)
    return _model


def get_class_mapping():
    global _class_mapping
    if _class_mapping is None:
        with open(CLASS_MAPPING_PATH, "r") as f:
            _class_mapping = json.load(f)
    return _class_mapping


def predict_tumor(image_path):
    """
    একটা MRI ছবির path নিয়ে classification prediction রিটার্ন করে।
    Output: {'classification': 'glioma', 'confidence': 92.4}
    """
    model = get_model()
    class_mapping = get_class_mapping()
    # index -> label mapping উল্টে নিচ্ছি (mapping এ label -> index আছে)
    index_to_label = {v: k for k, v in class_mapping.items()}

    IMG_SIZE = 224
    img = load_img(image_path, target_size=(IMG_SIZE, IMG_SIZE))
    img_array = img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # batch dimension যোগ করা
    # কোনো rescale না -- training এর সময় যেমন raw pixel দিয়েছিলাম, এখানেও তাই

    predictions = model.predict(img_array)
    predicted_index = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][predicted_index]) * 100

    return {
        "classification": index_to_label[predicted_index],
        "confidence": round(confidence, 2),
    }


# ===== Segmentation (নতুন যোগ হচ্ছে) =====
SEGMENTATION_MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_models", "segmentation_model_best.pth")

_segmentation_model = None

def get_segmentation_model():
    global _segmentation_model
    if _segmentation_model is None:
        model = smp.Unet(
            encoder_name="resnet18",
            encoder_weights=None,
            in_channels=3,
            classes=1,
            activation="sigmoid"
        )
        model.load_state_dict(torch.load(SEGMENTATION_MODEL_PATH, map_location=torch.device('cpu')))
        model.eval()
        _segmentation_model = model
    return _segmentation_model

def predict_segmentation(image_path, save_dir):
    """
    একটা MRI ছবি থেকে tumor segmentation mask তৈরি করে,
    overlay ছবি বানায়, এবং tumor area পরিমাপ করে।

    save_dir: যেখানে mask ও overlay ছবি সেভ হবে (media ফোল্ডারের path)

    Output: {
        'mask_path': '...',
        'overlay_path': '...',
        'tumor_area_pixels': int,
        'tumor_area_percentage': float
    }
    """
    model = get_segmentation_model()
    IMG_SIZE = 128  # training এর সময় যে size ব্যবহার করেছিলাম

    # ছবি লোড করে prepare করি
    original = cv2.imread(image_path)
    original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    original_h, original_w = original.shape[:2]

    resized = cv2.resize(original, (IMG_SIZE, IMG_SIZE))
    img_normalized = resized.astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(img_normalized).permute(2, 0, 1).unsqueeze(0)

    # Prediction
    with torch.no_grad():
        pred = model(img_tensor)
        pred_mask = pred.squeeze().cpu().numpy()

    binary_mask = (pred_mask > 0.5).astype(np.uint8) * 255

    # মূল ছবির আকারে ফিরিয়ে নিয়ে যাই (resize back)
    binary_mask_full = cv2.resize(binary_mask, (original_w, original_h))

    # Tumor area হিসাব করি
    tumor_area_pixels = int(np.sum(binary_mask_full > 127))
    total_pixels = original_w * original_h
    tumor_area_percentage = round((tumor_area_pixels / total_pixels) * 100, 2)

    # Overlay তৈরি করি (লাল রঙে tumor region highlight)
    overlay = original.copy()
    red_layer = np.zeros_like(original)
    red_layer[:, :, 0] = binary_mask_full  # লাল চ্যানেলে mask বসাই
    overlay = cv2.addWeighted(overlay, 1.0, red_layer, 0.5, 0)

    # ফাইল সেভ করি
    base_filename = os.path.splitext(os.path.basename(image_path))[0]
    mask_filename = f"{base_filename}_mask.png"
    overlay_filename = f"{base_filename}_overlay.png"

    mask_path = os.path.join(save_dir, mask_filename)
    overlay_path = os.path.join(save_dir, overlay_filename)

    cv2.imwrite(mask_path, binary_mask_full)
    cv2.imwrite(overlay_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))

    return {
        "mask_filename": mask_filename,
        "overlay_filename": overlay_filename,
        "tumor_area_pixels": tumor_area_pixels,
        "tumor_area_percentage": tumor_area_percentage,
    }