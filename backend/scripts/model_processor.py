import albumentations as A
import cv2
import numpy as np
import segmentation_models_pytorch as smp
import torch
import json
import rasterio
from shapely.geometry import mapping, LineString, MultiLineString
from shapely.wkt import dumps as wkt_dumps
import os
import pyproj

# --- Configuration (Keep these consistent with your ML environment) ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BEST_STATE_PATH = (
    "./model/best_model_state.pth"  # Path assumed relative to where Flask is run
)


# --- Utility Functions ---


def to_tensor(x, **kwargs):
    """Converts (H,W,C) image to (C,H,W) tensor format."""
    return x.transpose(2, 0, 1).astype("float32")


def get_preprocessing(preprocessing_fn=None):
    """Defines image preprocessing pipeline for the model."""
    ops = []
    if preprocessing_fn:
        ops.append(A.Lambda(image=preprocessing_fn))
    ops.append(A.Lambda(image=to_tensor))
    return A.Compose(ops)


# --- Load Model (Model is loaded once at module import) ---
try:
    # Attempt to load the model and preprocessing function
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
    # This block ensures the module loads even if the model weights are missing
    print(f"Warning: Model loading failed: {e}. Geospatial logic will still run.")
    best_model = None
    preprocessing_fn = None


# --- Core Function (TIFF Processing) ---


@torch.no_grad()
def get_road_geojson(image_path: str) -> tuple[dict, str]:
    """
    Runs model inference on the GeoTIFF, extracts road contours,
    calculates BBOX, and returns GeoJSON features and BBOX WKT.

    Returns:
        tuple[dict, str]: (GeoJSON data dictionary, BBOX WKT string)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    # Use Rasterio to read the GeoTIFF and its metadata
    with rasterio.open(image_path) as src:
        img_raw = src.read()  # (C,H,W)
        src_transform = src.transform
        src_crs = src.crs
        img = np.transpose(img_raw, (1, 2, 0))  # Convert to (H,W,C)

    orig_h, orig_w = img.shape[:2]

    # --- Model Inference ---
    if best_model and preprocessing_fn:
        # Preprocess and resize
        img_resized = cv2.resize(img, (1024, 1024))
        sample = get_preprocessing(preprocessing_fn)(image=img_resized)
        x = torch.from_numpy(sample["image"]).unsqueeze(0).to(DEVICE)

        # Inference
        logits = best_model(x)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()
        pred_mask = (
            np.argmax(probs, axis=0)
            if probs.ndim == 3
            else (probs > 0.5).astype("uint8")
        )

        # Resize mask back and ensure it's uint8
        mask_resized = cv2.resize(
            pred_mask.astype(np.uint8),
            (orig_w, orig_h),
            interpolation=cv2.INTER_NEAREST,
        )
        mask_resized = (mask_resized > 0).astype(np.uint8)
    else:
        # Fallback for when the model could not be loaded (e.g., missing weights)
        print("Using dummy mask for BBOX calculation due to model load failure.")
        # Create a dummy mask (e.g., a simple square in the center) for BBOX simulation
        mask_resized = np.zeros((orig_h, orig_w), dtype=np.uint8)
        mask_resized[orig_h // 4 : orig_h * 3 // 4, orig_w // 4 : orig_w * 3 // 4] = 1

    # --- Geospatial Processing ---

    # Define the transformer for coordinate conversion (from image's CRS to WGS84)
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
        # If no roads detected, return empty GeoJSON and None for BBOX WKT
        return {"type": "FeatureCollection", "features": []}, None

    # Aggregate features into one MultiLineString for GeoJSON and BBOX calculation
    multi_line = MultiLineString(road_lines)

    # Calculate the BBOX
    minx, miny, maxx, maxy = multi_line.bounds
    # Construct the bounding box WKT (Well-Known Text) as a POLYGON (required for PostGIS)
    bbox_wkt = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(
                    multi_line
                ),  # Convert Shapely object to GeoJSON dict
                "properties": {
                    "source": os.path.basename(image_path),
                    "road_count": len(road_lines),
                },
            }
        ],
    }

    return geojson, bbox_wkt
