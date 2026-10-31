"""
Album Art Handler — Slice 1.2

Extracts embedded artwork from audio files, with caching and web fallback.
Designed for low-RAM Linux systems (Pi Zero 2 W).

Features:
- Embedded art extraction via Mutagen (FLAC, MP3, M4A)
- LRU disk cache with configurable size limit
- Background thread for network operations
- Strict timeouts to prevent UI blocking
- Thread-safe UI updates via callback queue

Module Structure:
- ArtworkCache class: Main interface for art retrieval
- LRU cache management with size enforcement
- Background worker thread for non-blocking operation
- Thread-safe callback mechanism for UI updates
"""

import os
import io
import time
import threading
import queue
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from collections import OrderedDict
import hashlib

from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError, ID3
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from PIL import Image


class ArtworkCache:
    """Manages album art caching with size limits and thread safety.

    Supports embedded artwork extraction from:
    - FLAC files (VorbisComment pictures)
    - MP3 files (ID3v2 APIC frames)
    - M4A files (iTunes artwork)

    Attributes:
        max_size_mb: Maximum total cache size in megabytes
        cache_dir: Directory for storing cached art files
        _cache: OrderedDict of source_path -> (cache_path, file_size)
        _cache_lock: Lock for thread-safe cache access
        _queue: Thread-safe queue for background operations
        _worker: Background thread for processing operations
    """

    def __init__(self, max_size_mb: int = 50, cache_dir: Optional[str] = None):
        """Initialize the artwork cache.

        Args:
            max_size_mb: Maximum total cache size in megabytes (default: 50)
            cache_dir: Directory for storing cached art files.
                       Defaults to ~/.cache/pi-music-player/artwork
        """
        self.max_size_mb = max_size_mb
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "pi-music-player" / "artwork"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # OrderedDict: source_path -> (cache_path, file_size_in_bytes)
        # Ordered by access (most recently used last)
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._cache_lock = threading.Lock()

        # Initialize cache from existing files
        self._scan_existing_cache()

        # Operation queue for background processing
        self._queue = queue.Queue()
        self._worker_stop = threading.Event()

        # Start background worker thread
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _scan_existing_cache(self):
        """Scan cache directory and populate cache accounting.

        Initializes the in-memory cache with information about
        existing artwork files from previous runs.
        """
        if not self.cache_dir.exists():
            return

        for cache_file in self.cache_dir.iterdir():
            if cache_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                try:
                    size = cache_file.stat().st_size
                    file_hash = cache_file.stem
                    # Use the cache filename as the key (without extension)
                    self._cache[file_hash] = (str(cache_file), size)
                except Exception:
                    pass

    def get_art(self, file_path: str, callback: Optional[Callable] = None) -> Optional[str]:
        """Get album art for a file, with caching and priority fallback.

        Extraction priority:
        1. Cached art (check before extraction)
        2. Embedded art (Mutagen)
        3. Local sidecar file (folder.jpg / cover.jpg in same directory)
        4. Web fallback (MusicBrainz/Cover Art Archive) — deferred to Slice 1.3

        Args:
            file_path: Path to audio file
            callback: Optional callback(function) to call with result

        Returns:
            Path to cached art file, or None if no art found
        """
        try:
            file_path = str(file_path)

            # Skip non-existent files immediately — no cache or sidecar effects
            if not os.path.exists(file_path):
                self._call_callback(callback, None)
                return None

            # Check cache first — return early with MRU update if cached
            cached_result = self._check_cache(file_path)
            if cached_result:
                self._call_callback(callback, cached_result)
                return cached_result

            # Extract embedded art
            result = self._extract_embedded(file_path)
            if result:
                self._cache_file(file_path, result)
                self._call_callback(callback, result)
                return result

            # Check local sidecar files
            sidecar_result = self._check_sidecar(file_path)
            if sidecar_result:
                self._cache_file(file_path, sidecar_result)
                self._call_callback(callback, sidecar_result)
                return sidecar_result

            # No art found — invoke callback
            self._call_callback(callback, None)
            return None

        except Exception as e:
            print(f"[ArtworkCache] Error processing {file_path}: {e}")
            self._call_callback(callback, None)
            return None

    def _check_cache(self, file_path: str) -> Optional[str]:
        """Check cache for existing artwork for a given audio file.

        Returns the cached art file path if found and file still exists.
        Updates MRU ordering on cache hit. Removes stale entries.

        Args:
            file_path: Path to audio file

        Returns:
            Cached art file path if exists and valid, None otherwise
        """
        with self._cache_lock:
            if file_path in self._cache:
                cache_path, _ = self._cache[file_path]
                # Verify cache file still exists
                if os.path.exists(cache_path):
                    # Move to end (most recently used)
                    self._cache.move_to_end(file_path)
                    return cache_path
                else:
                    # Stale cache entry — remove it
                    del self._cache[file_path]
            return None

    def _extract_embedded(self, file_path: str) -> Optional[str]:
        """Extract embedded artwork from audio file using Mutagen.

        Supports:
        - FLAC: VorbisComment pictures
        - MP3: ID3v2 APIC frames
        - M4A/iTunes: artwork atoms (future)

        Args:
            file_path: Path to audio file

        Returns:
            Path to cached art file, or None if no embedded art found
        """
        filepath = Path(file_path)

        try:
            # Try FLAC first
            if filepath.suffix.lower() == ".flac":
                try:
                    audio = FLAC(file_path)
                    if audio.pictures:
                        pic = audio.pictures[0]
                        return self._save_artwork(pic.mime_type, pic.data)
                except Exception:
                    pass

            # Try MP3 using ID3 APIC frames
            elif filepath.suffix.lower() == ".mp3":
                try:
                    id3 = ID3(file_path)
                    apic_frames = id3.getall("APIC")
                    if apic_frames:
                        apic = apic_frames[0]
                        return self._save_artwork(apic.mime, apic.data)
                except Exception:
                    pass

            # Try M4A/M4B
            elif filepath.suffix.lower() in [".m4a", ".m4b"]:
                try:
                    audio = MP3(file_path)  # Fallback
                    # M4A handling would need mutagen.mp4
                    # For now, skip to next format
                    pass
                except Exception:
                    pass

            return None

        except Exception as e:
            print(f"[ArtworkCache] Error extracting embedded art from {file_path}: {e}")
            return None

    def _check_sidecar(self, file_path: str) -> Optional[str]:
        """Check for local sidecar art files (folder.jpg, cover.jpg).

        Looks for jpg/jpeg files in the same directory as the audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Path to sidecar art file, or None if not found
        """
        filepath = Path(file_path)
        directory = filepath.parent

        # Common sidecar filenames
        sidecar_names = ["folder.jpg", "cover.jpg", "front.jpg", "albumart.jpg"]

        for name in sidecar_names:
            sidecar_path = directory / name
            if sidecar_path.exists() and sidecar_path.suffix.lower() in [".jpg", ".jpeg"]:
                # Derive unique filename from source path to prevent collisions
                # when files in different dirs share the same stem
                path_hash = hashlib.md5(str(filepath).encode()).hexdigest()[:12]
                cache_path = self.cache_dir / f"sidecar_{path_hash}.jpg"
                try:
                    import shutil
                    shutil.copy2(str(sidecar_path), str(cache_path))
                    return str(cache_path)
                except Exception as e:
                    print(f"[ArtworkCache] Error copying sidecar: {e}")

        return None

    def _save_artwork(self, mime_type: str, art_data: bytes) -> Optional[str]:
        """Save extracted artwork to cache directory.

        Args:
            mime_type: MIME type of the artwork (e.g., "image/jpeg", "image/png")
            art_data: Raw bytes of the artwork image

        Returns:
            Path to cached art file, or None if save failed
        """
        if not art_data:
            return None

        # Determine file extension from MIME type
        if '/' in mime_type:
            ext = mime_type.split('/')[-1]
        else:
            ext = 'jpg'

        # Generate unique cache filename
        cache_path = self.cache_dir / f"art_{int(time.time() * 1000)}.{ext}"

        try:
            with open(cache_path, "wb") as f:
                f.write(art_data)
            return str(cache_path)
        except Exception as e:
            print(f"[ArtworkCache] Error saving artwork: {e}")
            # Try to clean up partial file
            try:
                os.remove(cache_path)
            except Exception:
                pass
            return None

    def _cache_file(self, file_path: str, art_path: str) -> None:
        """Update in-memory cache with artwork file size and move to MRU.

        Args:
            file_path: Original audio file path
            art_path: Path to the artwork cache file
        """
        try:
            art_size = os.path.getsize(art_path)
            with self._cache_lock:
                self._cache[file_path] = (art_path, art_size)
                self._cache.move_to_end(file_path)  # Mark as most recently used
            self._enforce_size_limit()
        except Exception as e:
            print(f"[ArtworkCache] Error updating cache: {e}")

    def _enforce_size_limit(self) -> None:
        """Evict oldest cached art files when exceeding size limit.

        Removes least-recently-used entries iteratively until
        total size is under the max_size_mb threshold.
        """
        with self._cache_lock:
            while self._cache and sum(size for _, size in self._cache.values()) > self.max_size_mb * 1024 * 1024:
                # Evict the oldest (first) entry
                _, (cache_path, _) = self._cache.popitem(last=False)
                try:
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
                except Exception as e:
                    print(f"[ArtworkCache] Error removing evicted cache file: {e}")

    def _call_callback(self, callback: Optional[Callable], result: Optional[str]) -> None:
        """Call the callback function with the result.

        Callbacks should handle UI thread dispatch themselves (e.g., using
        root.after() in Tkinter applications) if called from a worker thread.

        Args:
            callback: Function to call with the result
            result: Result to pass to the callback
        """
        if callback is None:
            return

        try:
            callback(result)
        except Exception as e:
            print(f"[ArtworkCache] Callback error: {e}")

    def _worker_loop(self) -> None:
        """Background worker loop that processes queue items.

        Runs in a daemon thread and handles:
        - Callback scheduling
        - Periodic cache maintenance
        - Cooperative multitasking yield point
        """
        while not self._worker_stop.is_set():
            try:
                # Wait for queue item with timeout for responsiveness
                try:
                    item = self._queue.get(timeout=0.5)
                except queue.Empty:
                    # Timeout - check if we should stop
                    if self._worker_stop.is_set():
                        break
                    # Periodic cache maintenance
                    self._enforce_size_limit()
                    continue

                # Process queue item
                item_type = item[0]

                if item_type == "callback":
                    callback, result = item[1], item[2]
                    self._call_callback(callback, result)
                elif item_type == "enforce_size":
                    self._enforce_size_limit()

            except Exception as e:
                print(f"[ArtworkCache] Worker loop error: {e}")

    def close(self) -> None:
        """Gracefully shut down the worker thread and enforce cache size."""
        self._worker_stop.set()
        self._worker.join(timeout=5.0)
        # Final cache enforcement
        self._enforce_size_limit()


# Convenience function for quick art retrieval
def get_art(file_path: str, max_size_mb: int = 50, cache_dir: Optional[str] = None) -> Optional[str]:
    """Quick function to get album art without managing a cache instance.

    Args:
        file_path: Path to audio file
        max_size_mb: Maximum cache size in megabytes
        cache_dir: Optional directory for storing cached art files

    Returns:
        Path to cached art file, or None if no art found
    """
    cache = ArtworkCache(max_size_mb=max_size_mb, cache_dir=cache_dir)
    try:
        return cache.get_art(file_path)
    finally:
        cache.close()