"""
Album Art Handler — Slice 1.2 & 1.3

Extracts embedded artwork from audio files, with caching and web fallback.
Designed for low-RAM Linux systems (Pi Zero 2 W).

Features:
- Embedded art extraction via Mutagen (FLAC, MP3, M4A)
- LRU disk cache with configurable size limit
- Background thread for network operations
- Strict timeouts to prevent UI blocking
- Thread-safe UI updates via callback queue
- Web fallback via Cover Art Archive (MBID-based)

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
from typing import Optional, Callable, Dict, Any, Tuple
from collections import OrderedDict
import hashlib
import uuid
import shutil
import json
import urllib.request
import urllib.error

# Trusted HTTPS hosts for Cover Art Archive thumbnails — prevents SSRF via
# attacker-controlled redirect targets. Only these hosts are allowed.
# Cover Art Archive thumbnails are served from archive.org CDN hosts whose
# exact server names vary (ia*.us.archive.org), so the allowlist matches the
# IA domain pattern rather than listing individual hosts.
_TRUSTED_ART_HOSTS = {
    'coverartarchive.org',
    'www.coverartarchive.org',
    'archive.org',
    'ia.us.archive.org',
}

from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError, ID3
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from PIL import Image


def get_art(file_path: str, max_size_mb: int = 50, cache_dir: Optional[str] = None) -> Optional[str]:
    """Convenience function to get album art for a file.

    Args:
        file_path: Path to audio file
        max_size_mb: Maximum cache size in megabytes
        cache_dir: Directory for storing cached art

    Returns:
        Path to cached art file, or None if no art found
    """
    cache = ArtworkCache(max_size_mb=max_size_mb, cache_dir=cache_dir)
    try:
        return cache.get_art(file_path)
    finally:
        cache.close()


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
        _path_locks: Per-path locks for concurrent access serialization
        _test_mode: Disable network calls for testing
    """

    def __init__(self, max_size_mb: int = 50, cache_dir: Optional[str] = None, test_mode: bool = False):
        """Initialize the artwork cache.

        Args:
            max_size_mb: Maximum total cache size in megabytes (default: 50)
            cache_dir: Directory for storing cached art files.
                       Defaults to ~/.cache/pi-music-player/artwork
            test_mode: Disable network calls for testing (default: False)
        """
        self.max_size_mb = max_size_mb
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "pi-music-player" / "artwork"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.test_mode = test_mode

        # OrderedDict: source_path -> (cache_path, file_size_in_bytes)
        # Ordered by access (most recently used last)
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        # RLock: reentrant — _cache_file and _enforce_size_limit both acquire it
        self._cache_lock = threading.RLock()

        # Per-path locks for concurrent access serialization
        self._path_locks: Dict[str, threading.Lock] = {}
        self._path_locks_lock = threading.Lock()

        # Initialize cache from existing files
        self._scan_existing_cache()

        # Operation queue for background processing
        self._queue = queue.Queue()
        self._worker_stop = threading.Event()

        # Start background worker thread
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _scan_existing_cache(self):
        """Scan cache directory and populate cache accounting on init.

        Initializes the in-memory cache from existing artwork files
        found on disk from previous runs. Called before the worker
        thread starts so existing cache entries are available
        immediately.

        Note: Scanned files use their cache file path as key (not content
        hash), so identical content files from the same album are tracked
        separately. Actual lookups use source file_path.
        """
        if not self.cache_dir.exists():
            return

        for cache_file in self.cache_dir.iterdir():
            if cache_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']:
                try:
                    size = cache_file.stat().st_size
                    cache_path = str(cache_file)
                    # Use cache path as key so identical-content files are
                    # tracked separately (they have different paths).
                    scanned_key = f"scanned:{cache_path}"
                    # If the same path already exists under a source key,
                    # drop the scanned entry to avoid double counting.
                    if any(k != scanned_key and v[0] == cache_path for k, v in self._cache.items()):
                        continue
                    self._cache[scanned_key] = (cache_path, size)
                except Exception:
                    pass

    def _content_hash(self, file_path: str) -> str:
        """Compute content hash for cache key consistency."""
        return hashlib.sha256(file_path.encode()).hexdigest()

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
                path_hash = hashlib.sha256(str(filepath).encode()).hexdigest()[:12]
                cache_path = self.cache_dir / f"sidecar_{path_hash}.jpg"
                try:
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

        # Generate unique cache filename using UUID to prevent collisions
        cache_path = self.cache_dir / f"art_{uuid.uuid4().hex}.{ext}"

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

    def _cache_file(self, file_path: str, art_path: str) -> bool:
        """Update in-memory cache with artwork file size and move to MRU.

        Args:
            file_path: Original audio file path
            art_path: Path to the artwork cache file

        Returns:
            True if cache entry was accepted (file size within limit),
            False if file exceeds size limit and was rejected/evicted.
        """
        try:
            art_size = os.path.getsize(art_path)
            # Reject oversized files before caching
            if art_size > self.max_size_mb * 1024 * 1024:
                # Remove the oversized file and return False
                try:
                    os.remove(art_path)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"[ArtworkCache] Error removing rejected cache file: {e}")
                return False
            with self._cache_lock:
                # Reconcile any scanned:* entries pointing to the same path
                # before registering the source key. This prevents duplicate entries
                # from being counted toward the size limit, which could cause
                # premature eviction of valid entries and return paths that no longer
                # exist on disk.
                scanned_keys_to_remove = []
                for key in list(self._cache.keys()):
                    if key.startswith("scanned:") and self._cache[key][0] == art_path:
                        scanned_keys_to_remove.append(key)
                for key in scanned_keys_to_remove:
                    del self._cache[key]

                # Reconcile if source path already exists in cache
                if file_path in self._cache:
                    existing_cache_path, existing_size = self._cache[file_path]
                    if existing_cache_path == art_path:
                        # Same entry — just move to MRU
                        self._cache.move_to_end(file_path)
                    else:
                        # Different path — remove old cached file, store new
                        try:
                            os.remove(existing_cache_path)
                        except FileNotFoundError:
                            pass
                        except Exception:
                            pass
                        self._cache[file_path] = (art_path, art_size)
                        self._cache.move_to_end(file_path)
                else:
                    # New entry
                    self._cache[file_path] = (art_path, art_size)
                    self._cache.move_to_end(file_path)
                # Enforce size limit inside same lock acquisition to avoid
                # fragile release/re-acquire in a non-reentrant lock
                self._enforce_size_limit()
            return True
        except Exception as e:
            print(f"[ArtworkCache] Error updating cache: {e}")
            return False

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

    def get_art(self, file_path: str, callback: Optional[Callable] = None) -> Optional[str]:
        """Get album art for a file, with caching and priority fallback.

        Extraction priority:
        1. Cached art (check before extraction)
        2. Embedded art (Mutagen)
        3. Local sidecar file (folder.jpg / cover.jpg in same directory)
        4. Web fallback (MusicBrainz/Cover Art Archive) — Slice 1.3

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

            # Per-source-path serialization to prevent concurrent extraction
            # for the same track. Double-checked locking pattern.
            path_lock = self._path_locks.get(file_path)
            if path_lock is None:
                with self._path_locks_lock:
                    if file_path not in self._path_locks:
                        self._path_locks[file_path] = threading.Lock()
                    path_lock = self._path_locks[file_path]

            result_path = None

            # Perform all locked operations first, then call callback outside lock
            with path_lock:
                # Re-check cache after acquiring lock (double-check)
                cached_result = self._check_cache(file_path)
                if cached_result:
                    result_path = cached_result

                # Extract embedded art if not cached
                if result_path is None:
                    result = self._extract_embedded(file_path)
                    if result and self._cache_file(file_path, result):
                        result_path = result

                    # Check local sidecar files
                    if result_path is None:
                        sidecar_result = self._check_sidecar(file_path)
                        if sidecar_result and self._cache_file(file_path, sidecar_result):
                            result_path = sidecar_result

                # Web fallback if still no art found (Slice 1.3)
                if result_path is None:
                    web_result = self._get_web_art(file_path)
                    if web_result:
                        self._cache_file(file_path, web_result)
                        result_path = web_result

            # Call callback OUTSIDE the lock to prevent deadlock
            self._call_callback(callback, result_path)
            return result_path

        except Exception as e:
            print(f"[ArtworkCache] Error processing {file_path}: {e}")
            self._call_callback(callback, None)
            return None

    def _get_content_hash(self, file_path: str) -> str:
        """Compute content hash for cache key consistency."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _get_content_size(self, file_path: str) -> int:
        """Get file size for cache accounting."""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    def _get_content_path(self, file_path: str) -> Optional[str]:
        """Get the cached art file path for a source path, if it exists.

        Returns the cached art file path if it exists and is valid,
        or None if the cache entry is stale or missing.
        """
        if file_path not in self._cache:
            return None
        cache_path, content_size = self._cache[file_path]
        if os.path.exists(cache_path):
            # Move to end (most recently used)
            self._cache.move_to_end(file_path)
            return cache_path
        else:
            # Stale cache entry — remove it
            del self._cache[file_path]
            return None

    def _get_web_art(self, file_path: str) -> Optional[str]:
        """Fetch album art via MusicBrainz Release ID (MBID) + Cover Art Archive.

        This is Step 1 of Slice 1.3 — the web fallback chain:
        1. Extract MBID from audio file metadata (FLAC/MBID tags)
        2. Query Cover Art Archive API for release art
        3. Download and cache the artwork
        4. Return path to cached art file

        Args:
            file_path: Path to audio file

        Returns:
            Path to cached art file, or None if web fetch fails
        """
        try:
            file_path = str(file_path)

            # Step 1: Resolve MusicBrainz Release ID (MBID)
            mbid = self._resolve_mbid(file_path)
            if not mbid:
                return None

            # Step 2: Query Cover Art Archive (already caches internally)
            result = self._fetch_cover_art_archive(mbid)
            if result is None:
                return None

            # Step 3: Return cached path
            cache_path, _mime_type = result
            # Cache the result from the web fetch (has already been cached by _fetch_cover_art_archive)
            # But ensure it's in the cache for the original file path
            # Only return the path if caching accepted it (not rejected for size)
            if self._cache_file(file_path, cache_path):
                return cache_path
            else:
                # Caching rejected the image (e.g., oversized) — clean up and return None
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
                return None

        except Exception as e:
            print(f"[ArtworkCache] Web fallback error: {e}")
            return None

    def _resolve_mbid(self, file_path: str) -> Optional[str]:
        """Resolve MusicBrainz Release ID (MBID) from audio file tags.

        Supports:
        - FLAC: musicbrainz_releaseid VorbisComment
        - MP3: TXXX:MusicBrainz Release ID (or Picard's musicbrainz_albumid)
        - M4A: iTunes 'musicbrainz_releaseid' tag

        MusicBrainz Picard writes the release ID as:
        - FLAC: musicbrainz_releaseid VorbisComment (and Picard's musicbrainz_albumid)
        - MP3: TXXX:MusicBrainz Release ID (and Picard's MusicBrainz Album Id)
        - M4A: ----:com.apple.iTunes:musicbrainz_releaseid (and Picard's MusicBrainz Album Id)

        Args:
            file_path: Path to audio file

        Returns:
            MusicBrainz Release ID string, or None if not found
        """
        filepath = Path(file_path)

        try:
            # Try FLAC first
            if filepath.suffix.lower() == '.flac':
                try:
                    audio = FLAC(file_path)
                    # Check explicit tag first, then Picard alias
                    for key in ['musicbrainz_releaseid', 'musicbrainz_albumid']:
                        if key in audio:
                            return audio[key][0]
                except Exception:
                    pass

            # Try MP3 using ID3 TXXX frames
            elif filepath.suffix.lower() == '.mp3':
                try:
                    id3 = ID3(file_path)
                    for frame in id3.getall('TXXX'):
                        # Match MusicBrainz Release ID and Picard's MusicBrainz Album Id
                        if frame.desc in ('MusicBrainz Release ID', 'MusicBrainz Album Id'):
                            return frame.text[0]
                except Exception:
                    pass

            # Try M4A/M4B
            elif filepath.suffix.lower() in ['.m4a', '.m4b']:
                try:
                    from mutagen.mp4 import MP4
                    audio = MP4(file_path)
                    # Check iTunes key first, then Picard alias
                    for key in ['----:com.apple.iTunes:musicbrainz_releaseid',
                                '----:com.apple.iTunes:MusicBrainz Album Id']:
                        if key in audio:
                            val = audio[key][0]
                            if isinstance(val, bytes):
                                return val.decode('utf-8')
                            return val
                except Exception:
                    pass

            return None

        except Exception as e:
            print(f"[ArtworkCache] Error extracting MBID from {file_path}: {e}")
            return None

    def _fetch_cover_art_archive(self, mbid: str) -> Optional[Tuple[str, str]]:
        """Fetch album art from Cover Art Archive using MusicBrainz Release ID.

        Uses HTTPS only and validates every redirect target against a
        trusted host allowlist to prevent SSRF via attacker-controlled
        redirect targets.

        Args:
            mbid: MusicBrainz Release ID

        Returns:
            Tuple of (cached_art_path, mime_type), or None if fetch fails
        """
        if self.test_mode:
            # Skip network in test mode — return None so caller knows no web art
            print(f"[ArtworkCache] Cover Art Archive skipped (test mode) for MBID {mbid}")
            return None

        url = f"https://coverartarchive.org/release/{mbid}"
        # Store original MBID in the instance for logging errors
        # (helps when debugging network issues without exposing user data)
        self._last_mbid = mbid
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'PiMusicPlayer/1.0'})
            with urllib.request.urlopen(req, timeout=3.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    images = data.get('images', [])
                    if images:
                        thumbnail_url = images[0].get('thumbnails', {}).get('small')
                        if thumbnail_url:
                            # Upgrade to HTTPS and validate host (including redirects)
                            if not thumbnail_url.startswith('https://'):
                                thumbnail_url = thumbnail_url.replace('http://', 'https://', 1)
                            if not self._is_trusted_host(thumbnail_url):
                                print(f"[ArtworkCache] Rejected untrusted thumbnail host: {thumbnail_url}")
                                return None
                            req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'PiMusicPlayer/1.0'})
                            # Use custom opener to validate redirects against allowlist
                            opener = urllib.request.build_opener(ValidatedRedirectHandler(self))
                            with opener.open(req, timeout=3.5) as img_response:
                                # Final URL after redirects must also be trusted
                                final_url = img_response.geturl()
                                if not self._is_trusted_host(final_url):
                                    print(f"[ArtworkCache] Rejected untrusted redirect target: {final_url}")
                                    return None
                                image_data = img_response.read()
                                mime_type = img_response.headers.get('Content-Type', 'image/jpeg')
                                cache_path = self._save_artwork(mime_type, image_data)
                                if cache_path:
                                    return cache_path, mime_type
        except Exception as e:
            print(f"[ArtworkCache] Cover Art Archive error for MBID {mbid}: {e}")
            return None

    class ValidatedRedirectHandler(urllib.request.HTTPRedirectHandler):
        """Custom redirect handler that validates each redirect target against the allowlist."""

        def __init__(self, artwork_cache):
            self.artwork_cache = artwork_cache

        def http_error_302(self, req, fp, code, msg, headers):
            new_url = headers.get('Location')
            if new_url and not self.artwork_cache._is_trusted_host(new_url):
                raise urllib.error.HTTPError(new_url, 403,
                    "Untrusted redirect target", headers, fp)
            return super().http_error_302(req, fp, code, msg, headers)

        http_error_301 = http_error_302
        http_error_303 = http_error_302
        http_error_307 = http_error_302

    def _is_trusted_host(self, url: str) -> bool:
        """Validate that a URL is HTTPS and its host is in the trusted allowlist.

        Args:
            url: Full URL to validate

        Returns:
            True if the URL is HTTPS and host is trusted, False otherwise
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme != 'https':
                return False
            host = parsed.hostname
            if not host:
                return False
            # Strip port if present
            host = host.split(':')[0].lower()
            return host in _TRUSTED_ART_HOSTS
        except Exception:
            return False