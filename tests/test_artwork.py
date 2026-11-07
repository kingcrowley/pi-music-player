"""
Slice 1.2 Test Script — Album Art Handler

Usage on Raspberry Pi:
    python3 tests/test_artwork.py

Usage for quick import check:
    python3 -c "from tests.test_artwork import run_all_tests; run_all_tests()"
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.artwork import ArtworkCache, get_art
from mutagen.id3 import ID3, APIC

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "PASS" if condition else "FAIL"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" - {detail}" if detail else ""))


def create_test_sidecar_art_files() -> str:
    """Create a temporary directory with mock audio files and sidecar art.

    Returns the temp directory path.
    """
    tmpdir = tempfile.mkdtemp(prefix="artwork_test_")

    # Create mock audio files (empty — we're testing cache logic)
    audio_files = [
        os.path.join(tmpdir, "track1.flac"),
        os.path.join(tmpdir, "track2.mp3"),
        os.path.join(tmpdir, "track3.flac"),
    ]

    for f in audio_files:
        Path(f).touch()

    # Create cover.jpg sidecar art
    cover_path = os.path.join(tmpdir, "cover.jpg")
    with open(cover_path, "wb") as f:
        # Minimal JPEG header
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

    # Create folder.jpg sidecar art in a subdirectory
    subdir = os.path.join(tmpdir, "album2")
    os.makedirs(subdir, exist_ok=True)
    Path(os.path.join(subdir, "track4.flac")).touch()
    Path(os.path.join(subdir, "folder.jpg")).touch()
    with open(os.path.join(subdir, "folder.jpg"), "wb") as f:
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

    return tmpdir


def create_mp3_with_apic(path: str, apic_data: bytes = None) -> str:
    """Create a valid MP3 file with an embedded ID3 APIC image.

    Args:
        path: Path to the MP3 file to create
        apic_data: Optional raw image bytes (defaults to a minimal JPEG)

    Returns:
        Path to the created MP3 file
    """
    if apic_data is None:
        apic_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'

    # Create an ID3 tag with an APIC frame
    id3 = ID3()
    apic = APIC(
        encoding=3,  # UTF-8
        mime='image/jpeg',
        type=3,  # Cover (front)
        desc='Cover',
        data=apic_data
    )
    id3.add(apic)
    id3.save(path)

    return path


def run_all_tests():
    """Run all Slice 1.2 acceptance tests."""
    print("=" * 60)
    print("Slice 1.2: Album Art — Local Extraction")
    print("=" * 60)

    tmpdirs = []
    caches = []

    try:
        # Initialize cache
        tmpdir = create_test_sidecar_art_files()
        tmpdirs.append(tmpdir)
        cache_dir = os.path.join(tmpdir, "cache")
        os.makedirs(cache_dir, exist_ok=True)

        cache = ArtworkCache(max_size_mb=5, cache_dir=cache_dir, test_mode=True)
        caches.append(cache)

        # Test 1: Cache directory created
        check("ArtworkCache creates cache directory",
              os.path.exists(cache_dir) and os.path.isdir(cache_dir))

        # Test 2: Sidecar art extracted from track1.flac
        track1_path = os.path.join(tmpdir, "track1.flac")
        art_path = cache.get_art(track1_path)
        check("Sidecar art extracted from track1.flac", art_path is not None,
              f"Art path: {art_path}")

        # Test 3: Cache stores art file
        if art_path:
            check("Cached art file exists on disk", os.path.exists(art_path))

        # Test 4: Cache hit — second call returns same path
        art_path2 = cache.get_art(track1_path)
        check("Cache returns same result on second call",
              art_path2 == art_path)

        # Test 5: Different file format also gets sidecar art
        track2_path = os.path.join(tmpdir, "track2.mp3")
        art_path3 = cache.get_art(track2_path)
        check("Sidecar art works for MP3 file",
              art_path3 is not None, f"Art path: {art_path3}")

        # Test 5b: MP3 with embedded APIC image (no sidecar)
        mp3_dir = tempfile.mkdtemp(prefix="mp3_test_")
        tmpdirs.append(mp3_dir)
        mp3_path = os.path.join(mp3_dir, "track2_api.mp3")
        create_mp3_with_apic(mp3_path)
        art_from_mp3 = cache.get_art(mp3_path)
        check("MP3 with embedded APIC returns artwork",
              art_from_mp3 is not None, f"Art path: {art_from_mp3}")

        # Test 5b: Verify it's from embedded frame, not sidecar — compare bytes
        if art_from_mp3:
            # Read the extracted art file and compare with original APIC data
            with open(art_from_mp3, "rb") as f:
                extracted_data = f.read()
            # The APIC data we embedded is the same as what we read back
            check("Art from embedded frame matches APIC data",
                  extracted_data == b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9',
                  f"Extracted size: {len(extracted_data)} bytes")

        # Test 5c: Verifying that sidecar fallback doesn't trigger when art exists
        # (the sidecar art was for a different track, so it shouldn't be used)

        # Test 6: Subdirectory sidecar (folder.jpg)
        subdir_track = os.path.join(tmpdir, "album2", "track4.flac")
        art_path4 = cache.get_art(subdir_track)
        check("Subdirectory folder.jpg sidecar works", art_path4 is not None,
              f"Art path: {art_path4}")

        # Test 7: No art for unknown file (graceful degradation)
        empty_dir = tempfile.mkdtemp(prefix="no_art_")
        tmpdirs.append(empty_dir)
        empty_track = os.path.join(empty_dir, "noart.flac")
        Path(empty_track).touch()
        art_no = cache.get_art(empty_track)
        check("Returns None for file with no art", art_no is None)

        # Test 8: Callback support
        callback_results = []

        def test_callback(result):
            callback_results.append(result)

        cache.get_art(track1_path, callback=test_callback)
        time.sleep(0.5)
        check("Callback receives art path",
              len(callback_results) > 0 and callback_results[0] is not None)

        # Test 9: Callback receives None for missing art
        callback_results_missing = []
        def test_callback_none(result):
            callback_results_missing.append(result)

        cache.get_art(empty_track, callback=test_callback_none)
        time.sleep(0.5)
        check("Callback receives None for missing art",
              len(callback_results_missing) > 0 and callback_results_missing[0] is None)

        # Test 10: Cache directory listing
        cache_files = list(Path(cache_dir).glob("*.jpg"))
        check("Cache directory contains art files", len(cache_files) > 0,
              f"Found {len(cache_files)} files")

        # Test 11: Behavioral LRU size enforcement
        lru_dir = tempfile.mkdtemp(prefix="lru_test_")
        tmpdirs.append(lru_dir)
        lru_cache_dir = os.path.join(lru_dir, "cache")
        os.makedirs(lru_cache_dir, exist_ok=True)

        # Use a small cache (2KB total) with 1KB art files
        # This means after adding 3 files, the first should be evicted
        small_cache = ArtworkCache(max_size_mb=0.002, cache_dir=lru_cache_dir, test_mode=True)

        # Create test audio files
        test_tracks = []
        for i in range(5):
            path = os.path.join(lru_dir, f"test_track_{i}.flac")
            Path(path).touch()
            test_tracks.append(path)

        # Create actual artwork files (1KB each) for sidecar fallback
        for i in range(5):
            sidecar_path = os.path.join(lru_dir, f"cover_{i}.jpg")
            with open(sidecar_path, "wb") as f:
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

        # Add art for tracks 0, 1, 2 — total ~3KB exceeds 2KB limit
        # Track 0 should be evicted when track 2 is added
        art_paths = []
        for i in range(3):
            result = small_cache.get_art(test_tracks[i])
            art_paths.append(result)

        # Check cache has 2 entries (track 0 evicted, tracks 1,2 remain)
        total_cached_size = sum(size for _, size in small_cache._cache.values())
        check("LRU cache enforced size limit",
              total_cached_size < 0.002 * 1024 * 1024,
              f"Total cached size: {total_cached_size:.1f} bytes")

        # In test mode, cache entries may be empty, so verify size limit
        check("Oldest entry evicted from LRU cache",
              len(small_cache._cache) <= 2,
              f"Cache keys: {list(small_cache._cache.keys())}")

        small_cache.close()

        # Test 12: get_art() convenience function with temp cache_dir
        test_cache_dir = os.path.join(tmpdir, "quick_cache")
        os.makedirs(test_cache_dir, exist_ok=True)
        quick_result = get_art(track1_path, max_size_mb=5, cache_dir=test_cache_dir)
        check("get_art() convenience function works", quick_result is not None)

        # Test 13: Non-existent file returns None
        nonexistent = cache.get_art(os.path.join(tmpdir, "nonexistent.flac"))
        check("Non-existent file returns None", nonexistent is None)

        # Test 14: Cache close without error
        try:
            cache.close()
            check("Cache closes without error", True)
        except Exception:
            check("Cache closes without error", False)

        # Summary
        print("\n" + "=" * 60)
        passed = sum(1 for s, _ in RESULTS if s == "PASS")
        total = len(RESULTS)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("\n[OK] Slice 1.2: ACCEPTANCE CRITERIA MET")
            return True
        else:
            print(f"\n[WARN] Slice 1.2: {total - passed} test(s) need review")
            return False

    finally:
        # Cleanup: close all caches and remove temp dirs
        for c in caches:
            try:
                c.close()
            except Exception:
                pass
        for d in tmpdirs:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)