from __future__ import annotations

import base64
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path.cwd()
PARTS = ROOT / ".rewrite" / "parts"
EXPECTED_B64_LENGTH = 59352
EXPECTED_B64_SHA256 = "4042987efb55e00f19b67f62528805a267a8050cb732be5ee120a91b1bb24ccf"
EXPECTED_ZIP_SHA256 = "c791691ce537a22cd5e3d7a32eeac17023a92f1769173eac1f95c446fc5fe4e4"
EXPECTED_FINAL_TAIL = (
    "TW91c2UgSHViLmJhdFVUBQADN7FnanV4CwABBAAAAAAEAAAAA"
    "FBLBQYAAAAARABEANEXAAD6lQAAAAA="
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_payload() -> str:
    chunks: list[str] = []
    for index in range(8):
        path = PARTS / f"part_{index:02d}"
        if not path.exists():
            raise FileNotFoundError(f"Missing rewrite payload part: {path}")
        text = path.read_text(encoding="ascii").strip()
        if index < 7:
            # Every normal chunk is exactly 8,000 characters. Taking the first
            # 8,000 also makes staging resilient to an accidentally duplicated tail.
            if len(text) < 8000:
                raise ValueError(f"Payload part {index:02d} is too short: {len(text)}")
            text = text[:8000]
        else:
            if len(text) < len(EXPECTED_FINAL_TAIL):
                raise ValueError("Final payload part is too short")
            # Restore the known final ZIP directory tail before hashing.
            text = text[:-len(EXPECTED_FINAL_TAIL)] + EXPECTED_FINAL_TAIL
        chunks.append(text)

    encoded = "".join(chunks)
    if len(encoded) != EXPECTED_B64_LENGTH:
        raise ValueError(f"Unexpected base64 length: {len(encoded)}")
    if sha256_bytes(encoded.encode("ascii")) != EXPECTED_B64_SHA256:
        raise ValueError("Rewrite payload SHA-256 mismatch")
    return encoded


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination not in target.parents and target != destination:
            raise ValueError(f"Unsafe ZIP path: {member.filename}")
    archive.extractall(destination)


def main() -> None:
    encoded = read_payload()
    archive_bytes = base64.b64decode(encoded, validate=True)
    if sha256_bytes(archive_bytes) != EXPECTED_ZIP_SHA256:
        raise ValueError("Decoded ZIP SHA-256 mismatch")

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_path = temp_dir / "repo.zip"
        staged_repo = temp_dir / "repo"
        archive_path.write_bytes(archive_bytes)
        staged_repo.mkdir()

        with zipfile.ZipFile(archive_path) as archive:
            safe_extract(archive, staged_repo)

        required = [
            staged_repo / "VERSION",
            staged_repo / "README.md",
            staged_repo / "turbo-project.json",
            staged_repo / "Start Project.bat",
            staged_repo / "ai_mouse_lab" / "app.py",
        ]
        missing = [str(path.relative_to(staged_repo)) for path in required if not path.exists()]
        if missing:
            raise ValueError(f"Staged repository is incomplete: {missing}")
        if (staged_repo / "VERSION").read_text(encoding="utf-8").strip() != "1.0.0":
            raise ValueError("Staged repository has the wrong version")

        for child in list(ROOT.iterdir()):
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

        for child in staged_repo.iterdir():
            destination = ROOT / child.name
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)


if __name__ == "__main__":
    main()
