"""Package the final submission into output/ and build team_name_voiceops.zip.
Adheres strictly to the Capstone Brief specifications (Page 14):
Includes: README.md, .env.example, requirements.txt, run.py, run.sh, src/, report.pdf, demo_script.md, sample_outputs/
Excludes: .env, API keys, __pycache__, virtual environments, dataset copy.
"""
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Copy standalone deliverables to output/
deliverables = [
    "README.md",
    "requirements.txt",
    ".env.example",
    "run.py",
    "run.sh",
    "report.pdf",
    "report.md",
    "demo_script.md",
    "app.py"
]

for d in deliverables:
    src_f = ROOT / d
    dst_f = OUTPUT_DIR / d
    if src_f.exists():
        shutil.copy2(src_f, dst_f)
        print(f"Copied {d} -> output/{d}")

# Copy sample_outputs/ to output/sample_outputs/
dst_samples = OUTPUT_DIR / "sample_outputs"
if (ROOT / "sample_outputs").exists():
    if dst_samples.exists():
        shutil.rmtree(dst_samples)
    shutil.copytree(ROOT / "sample_outputs", dst_samples)
    print(f"Copied sample_outputs/ -> output/sample_outputs/")

# Copy src/ to output/src/
dst_src = OUTPUT_DIR / "src"
if dst_src.exists():
    shutil.rmtree(dst_src)
shutil.copytree(ROOT / "src", dst_src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.log"))
print("Copied src/ -> output/src/")

# 2. Build Submission ZIP
zip_name = "zentromart_voiceops_submission.zip"
zip_path = OUTPUT_DIR / zip_name

print(f"\nBuilding submission archive: {zip_path.name}...")

exclude_patterns = {".env", "__pycache__", ".git", ".vscode", "venv", ".idea", "*.zip"}

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    # Add root files
    for item in deliverables:
        item_path = ROOT / item
        if item_path.exists():
            zf.write(item_path, arcname=item)
            print(f"  + Added {item}")

    # Add src/
    for root, dirs, files in os.walk(ROOT / "src"):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith((".pyc", ".pyo", ".log")):
                continue
            full_p = Path(root) / f
            rel_p = full_p.relative_to(ROOT)
            zf.write(full_p, arcname=str(rel_p))
            print(f"  + Added {rel_p}")

    # Add sample_outputs/
    for root, dirs, files in os.walk(ROOT / "sample_outputs"):
        for f in files:
            full_p = Path(root) / f
            rel_p = full_p.relative_to(ROOT)
            zf.write(full_p, arcname=str(rel_p))
            print(f"  + Added {rel_p}")

    # Add sample_inputs/
    for root, dirs, files in os.walk(ROOT / "sample_inputs"):
        for f in files:
            full_p = Path(root) / f
            rel_p = full_p.relative_to(ROOT)
            zf.write(full_p, arcname=str(rel_p))
            print(f"  + Added {rel_p}")

# Also create team_name_voiceops.zip copy as requested by spec
team_zip_path = OUTPUT_DIR / "team_name_voiceops.zip"
shutil.copy2(zip_path, team_zip_path)
print(f"Created alias: output/{team_zip_path.name}")

print(f"\n[Packaging Complete] All submission deliverables successfully assembled in:")
print(f"   {OUTPUT_DIR.resolve()}")
print(f"   Archive Size: {zip_path.stat().st_size / 1024:.1f} KB")
