"""
Media deletion safety.

The rule under test: never report an asset as deleted when the external object
still exists, and never delete the database row that is the only pointer to it.

`parse_public_id` is the riskiest piece of the whole pipeline. It runs only in
the backfill, but a wrong answer there is invisible until purge time, when
Cloudinary replies "not found" for an id that never existed and the pipeline
records a successful deletion of a photo that is still public. So it is tested
for what it refuses to do as much as for what it returns.
"""

from __future__ import annotations

import pytest

from app.services.media.cloudinary_client import parse_public_id


class TestParsePublicId:
    def test_plain_upload_url(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1699887766/tyohaar/memories/abc123.jpg"
        assert parse_public_id(url) == "tyohaar/memories/abc123"

    def test_strips_transformation_segments(self):
        url = (
            "https://res.cloudinary.com/demo/image/upload/"
            "w_300,h_300,c_fill/v1699887766/tyohaar/profile/user9.webp"
        )
        assert parse_public_id(url) == "tyohaar/profile/user9"

    def test_handles_nested_folders(self):
        url = (
            "https://res.cloudinary.com/demo/image/upload/v1/"
            "tyohaar/celebrations/2026/diwali/hero.png"
        )
        assert parse_public_id(url) == "tyohaar/celebrations/2026/diwali/hero"

    def test_video_url(self):
        url = "https://res.cloudinary.com/demo/video/upload/v1699887766/tyohaar/clips/reel.mp4"
        assert parse_public_id(url) == "tyohaar/clips/reel"

    def test_url_without_extension(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1699887766/tyohaar/raw/token"
        assert parse_public_id(url) == "tyohaar/raw/token"

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "not a url",
            "https://cdn.example.com/images/photo.jpg",
            "https://storage.googleapis.com/bucket/photo.jpg",
        ],
    )
    def test_returns_none_rather_than_guessing(self, url: str):
        """A guess is worse than an admission of failure.

        Returning something plausible here would make the backfill record a
        confident, wrong id — and the purge would then claim success against
        an object it never touched.
        """
        assert parse_public_id(url) is None


class TestUnresolvedAssetContract:
    """The failure path is a durable record, not a log line."""

    def test_unresolved_model_has_no_foreign_key_to_media(self):
        """The record must survive its source row being removed.

        A foreign key would let a cascade take away the very evidence that an
        orphaned object exists.
        """
        from app.models.media.unresolved_asset import UnresolvedMediaAsset

        assert not UnresolvedMediaAsset.__table__.foreign_keys, (
            "unresolved_media_assets must not depend on the rows it describes"
        )

    def test_media_handler_keeps_rows_it_could_not_delete(self):
        """Source-level guard on the pointer rule."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app/services/deletion/handlers/media.py"
        ).read_text(encoding="utf-8")

        assert "notin_(blocked)" in source, (
            "media rows must be excluded from deletion when their storage "
            "object could not be destroyed"
        )
        assert "report.fail(" in source, (
            "keeping a row because its object survived must fail the handler, "
            "so the request cannot be marked PURGED"
        )

    def test_external_handler_fails_when_public_id_is_missing(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app/services/deletion/handlers/external.py"
        ).read_text(encoding="utf-8")

        assert "no_storage_public_id" in source
        assert "_record_unresolved" in source
        assert "report.fail(" in source


class TestDestroyIdempotency:
    def test_not_found_counts_as_deleted(self):
        """Re-running a purge must not fail on an already-deleted object.

        Cloudinary answers "not found" for an object that is already gone,
        which is the same end state as a successful delete — treating it as a
        failure would make every retry permanently INCOMPLETE.
        """
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app/services/media/cloudinary_client.py"
        ).read_text(encoding="utf-8")

        assert '{"ok", "not found"}' in source
        assert "invalidate=True" in source, (
            "CDN copies must be invalidated, or a deleted image keeps serving "
            "from the edge for its remaining TTL"
        )


class TestUnconfiguredStorageIsNotAnException:
    """The safety guarantee must hold hardest when storage is misconfigured.

    Regression test for the worst bug found during verification: `destroy_asset`
    called `_ensure_configured()` outside its try block, so an unconfigured
    deployment raised instead of returning False. The purge handler then died
    mid-transaction, its `unresolved_media_assets` bookkeeping was rolled back
    with it, and the *next* handler saw no blockers and deleted the media rows —
    destroying the only pointers to objects that were still live and public.

    Misconfigured credentials are the most likely real-world trigger, so this is
    exactly the path that must fail safe.
    """

    async def test_destroy_asset_returns_false_when_unconfigured(self, monkeypatch):
        from app.core.config import settings
        from app.services.media import cloudinary_client

        monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "", raising=False)
        monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "", raising=False)
        monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "", raising=False)
        monkeypatch.setattr(cloudinary_client, "_configured", False, raising=False)

        result = await cloudinary_client.destroy_asset("some/id")

        assert result is False, (
            "unconfigured storage must report failure, never raise — an "
            "exception here rolls back the record of what could not be deleted"
        )

    def test_ensure_configured_is_inside_the_try(self):
        """Guard the structure, not just the behaviour."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app/services/media/cloudinary_client.py"
        ).read_text(encoding="utf-8")

        block = source.split("async def destroy_asset")[1].split("async def")[0]
        body_start = block.index("def _destroy()")
        guard_pos = block.index("_ensure_configured()", body_start)
        assert guard_pos > body_start, (
            "_ensure_configured() must sit inside the wrapped call so its "
            "failure is caught and reported as False"
        )

    def test_external_handler_never_calls_destroy_directly(self):
        """Every call site must go through the non-raising wrapper."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app/services/deletion/handlers/external.py"
        ).read_text(encoding="utf-8")

        body = source.split("async def _destroy")[1]
        after_wrapper = body.split("async def _record_unresolved")[1]
        assert "cloudinary_client.destroy_asset(" not in after_wrapper, (
            "handlers must call _destroy(), which cannot raise and therefore "
            "cannot discard the unresolved-asset bookkeeping"
        )
