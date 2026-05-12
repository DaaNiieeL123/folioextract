from pathlib import Path
import shutil


def copy_branding_icons() -> None:
    root = Path(__file__).resolve().parents[1]
    branding_dir = root / "assets" / "branding"
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)

    shutil.copyfile(branding_dir / "app_icon.ico", assets_dir / "icon.ico")
    shutil.copyfile(branding_dir / "favicon.png", assets_dir / "icon.png")
    print("FolioExtract icons copied to assets/icon.ico and assets/icon.png.")


if __name__ == "__main__":
    copy_branding_icons()
