import numpy as np
from keras.models import load_model
from keras.utils import load_img, img_to_array
import json
import os
from django.conf import settings

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
