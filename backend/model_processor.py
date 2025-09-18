import albumentations as A
import cv2
import numpy as np
import segmentation_models_pytorch as smp
import torch
import json
import rasterio
from shapely.geometry import mapping, LineString, MultiLineString
import os
import pyproj

# ---------- Config ----------
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BEST_STATE_PATH = "./model/best_model_state.pth"


# ---------- Utils ----------
def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype("float32")


def get_preprocessing(preprocessing_fn=None):
    ops = []
    if preprocessing_fn:
        ops.append(A.Lambda(image=preprocessing_fn))
    ops.append(A.Lambda(image=to_tensor))
    return A.Compose(ops)


# ---------- Load Model ----------
try:
    ckpt = torch.load(BEST_STATE_PATH, map_location=DEVICE)
    best_model = smp.DeepLabV3Plus(
        encoder_name=ckpt["encoder"],
        encoder_weights=None,
        classes=ckpt["n_classes"],
        activation=None,
    ).to(DEVICE)
    best_model.load_state_dict(ckpt["state_dict"])
    best_model.eval()

    preprocessing_fn = smp.encoders.get_preprocessing_fn(
        ckpt["encoder"], ckpt["encoder_weights"]
    )
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    best_model = None


# ---------- Core Function (TIFF Only) ----------
@torch.no_grad()
def get_road_geojson(image_path):
    # Use Rasterio to read the GeoTIFF and its metadata
    with rasterio.open(image_path) as src:
        img_raw = src.read()  # (C,H,W)
        src_transform = src.transform
        src_crs = src.crs
        img = np.transpose(img_raw, (1, 2, 0))  # Convert to (H,W,C)

    orig_h, orig_w = img.shape[:2]
    img_resized = cv2.resize(img, (1024, 1024))

    # Model inference
    sample = get_preprocessing(preprocessing_fn)(image=img_resized)
    x = torch.from_numpy(sample["image"]).unsqueeze(0).to(DEVICE)
    logits = best_model(x)
    probs = torch.sigmoid(logits).squeeze().cpu().numpy()
    pred_mask = (
        np.argmax(probs, axis=0) if probs.ndim == 3 else (probs > 0.5).astype("uint8")
    )

    # Resize mask back and ensure it's uint8
    mask_resized = cv2.resize(
        pred_mask.astype(np.uint8), (orig_w, orig_h), interpolation=cv2.INTER_NEAREST
    )
    mask_resized = (mask_resized > 0).astype(np.uint8)

    # Define the transformer for coordinate conversion
    # We transform from the image's CRS to WGS84 (lat/lon)
    transformer = pyproj.Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

    # Extract contours
    contours, _ = cv2.findContours(
        mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    road_lines = []
    for cnt in contours:
        if len(cnt) > 1:
            coords = []
            for p in cnt.squeeze():
                x, y = float(p[0]), float(p[1])
                # 1. Convert pixel coordinates to geographic coordinates (in the source CRS)
                lon, lat = src_transform * (x, y)
                # 2. Reproject to WGS84 (lon, lat)
                lon_wgs84, lat_wgs84 = transformer.transform(lon, lat)
                coords.append((lon_wgs84, lat_wgs84))
            road_lines.append(LineString(coords))

    if not road_lines:
        return {"type": "FeatureCollection", "features": []}

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(MultiLineString(road_lines)),
                "properties": {"source": os.path.basename(image_path)},
            }
        ],
    }

    # The CRS is no longer needed in the output as GeoJSON assumes WGS84
    return geojson


# ---------- Run Test ----------
if __name__ == "__main__":
    test_image_path = "./test_image.tif"
    out_path = "./detected_roads.geojson"
    try:
        geojson = get_road_geojson(test_image_path)
        with open(out_path, "w") as f:
            json.dump(geojson, f, indent=2)
        print(f"✅ Roads saved to {out_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
