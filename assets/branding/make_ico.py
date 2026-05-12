from pathlib import Path

from PIL import Image


if __name__ == "__main__":
    branding_dir = Path(__file__).resolve().parent
    img = Image.open(branding_dir / "logo_main.png")
    img.save(
        branding_dir / "app_icon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("ICO creado con exito.")
