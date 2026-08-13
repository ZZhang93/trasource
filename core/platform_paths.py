"""Cross-platform locations for writable application data."""

import os
import logging
import shutil
import sys
import tempfile
from typing import Mapping, Optional


logger = logging.getLogger(__name__)


def get_app_data_dir(
    app_name: str = "trasource",
    *,
    platform: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[str] = None,
) -> str:
    """Return the conventional per-user data directory for this platform."""
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = os.path.expanduser("~") if home is None else home

    if platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    elif platform.startswith("win"):
        base = env.get("LOCALAPPDATA") or env.get("APPDATA")
        if not base:
            base = os.path.join(home, "AppData", "Local")
    else:
        base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")

    return os.path.abspath(os.path.join(base, app_name))


def migrate_legacy_app_data(new_dir: str, *, home: Optional[str] = None) -> bool:
    """Move the pre-1.3.3 macOS-shaped data path on Windows/Linux once.

    Older frozen builds used ``~/Library/Application Support/trasource`` on
    every platform. Only migrate when the new conventional directory is absent,
    so a newer data set is never overwritten.
    """
    home = os.path.expanduser("~") if home is None else home
    legacy = os.path.abspath(
        os.path.join(home, "Library", "Application Support", "trasource")
    )
    new_dir = os.path.abspath(new_dir)
    if legacy == new_dir or os.path.exists(new_dir) or not os.path.isdir(legacy):
        return False
    os.makedirs(os.path.dirname(new_dir), exist_ok=True)
    try:
        os.replace(legacy, new_dir)
    except OSError:
        # A direct rename can fail across volumes. Never copy into the final
        # directory: a disk-full or permission error would leave a partial path
        # that the next startup mistakes for a completed migration.
        staging = tempfile.mkdtemp(
            prefix=f".{os.path.basename(new_dir)}-migrating-",
            dir=os.path.dirname(new_dir),
        )
        try:
            shutil.copytree(legacy, staging, dirs_exist_ok=True)
            os.replace(staging, new_dir)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        try:
            shutil.rmtree(legacy)
        except OSError as error:
            # The committed target is complete. Keeping a legacy duplicate is
            # safer than failing startup or deleting any part of the new copy.
            logger.warning("旧数据目录清理失败，已保留备份：%s", error)
    return True
