import torch
import numpy as np
import cv2
import segmentation_models_pytorch as smp
import rasterio
from shapely.geometry import Polygon
import albumentations as A


def test_torch():
    """Test PyTorch installation and CUDA availability."""
    print("Testing PyTorch...")
    print(f"PyTorch version: {torch.__version__}")
    if torch.cuda.is_available():
        print("✅ CUDA is available. Using GPU.")
        device = "cuda"
    else:
        print("⚠️ CUDA is not available. Using CPU.")
        device = "cpu"
    x = torch.randn(2, 3, device=device)
    assert x.device.type == device
    print("PyTorch test passed. 👍")


# ----------------------------------------


def test_numpy():
    """Test NumPy installation."""
    print("\nTesting NumPy...")
    arr = np.array([1, 2, 3])
    assert arr.shape == (3,)
    print(f"NumPy version: {np.__version__}")
    print("NumPy test passed. 👍")


# ----------------------------------------


def test_opencv():
    """Test OpenCV installation by creating a simple image array."""
    print("\nTesting OpenCV...")
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    assert img.shape == (10, 10, 3)
    assert cv2.__version__ is not None
    print(f"OpenCV version: {cv2.__version__}")
    print("OpenCV test passed. 👍")


# ----------------------------------------


def test_segmentation_models():
    """Test segmentation-models-pytorch by creating a model instance."""
    print("\nTesting segmentation-models-pytorch...")
    model = smp.Unet(encoder_name="resnet18", classes=1)
    assert model is not None
    print("segmentation-models-pytorch test passed. 👍")


# ----------------------------------------


def test_rasterio():
    """Test Rasterio by creating a mock dataset."""
    print("\nTesting Rasterio...")
    mock_data = np.ones((1, 10, 10), dtype=np.uint8)
    with rasterio.MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff", height=10, width=10, count=1, dtype=np.uint8
        ) as dataset:
            dataset.write(mock_data)
        assert dataset is not None
    print(f"Rasterio version: {rasterio.__version__}")
    print("Rasterio test passed. 👍")


# ----------------------------------------


def test_shapely():
    """Test Shapely by creating a simple polygon."""
    print("\nTesting Shapely...")
    polygon = Polygon([(0, 0), (1, 1), (1, 0)])
    assert polygon.area > 0
    print("Shapely test passed. 👍")


# ----------------------------------------


def test_albumentations():
    """Test Albumentations by applying a simple transform."""
    print("\nTesting Albumentations...")
    mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
    transform = A.Resize(50, 50)
    transformed_image = transform(image=mock_image)["image"]
    assert transformed_image.shape == (50, 50, 3)
    print("Albumentations test passed. 👍")


# ----------------------------------------

if __name__ == "__main__":
    try:
        test_torch()
        test_numpy()
        test_opencv()
        test_segmentation_models()
        test_rasterio()
        test_shapely()
        test_albumentations()
        print("\nAll packages are installed and working correctly! ✅")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check the error message to troubleshoot the failing package.")
