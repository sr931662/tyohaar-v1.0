"""
Daily retention job — the only scheduled component of the deletion pipeline.

Designed for Cloud Scheduler → Cloud Run Job, which is what the project
already deploys onto. No Celery, no APScheduler, no new infrastructure class:

    gcloud run jobs create tyohaar-retention \
        --image <same image as the API> \
        --command python --args -m,app.jobs.purge_job

    gcloud scheduler jobs create http tyohaar-retention-daily \
        --schedule "30 2 * * *" --uri <run job execute endpoint>

Two independent pieces of work run here, and the second does not depend on the
first:

  1. Purge deletion requests whose recovery window has closed.
  2. Expire guest contact data whose event is far enough in the past. This
     runs for every host, deleted or not — third-party guest PII has its own
     clock and must not be able to live forever just because the host stayed.

Exit code is 0 whenever the job ran to completion, including when individual
requests came back INCOMPLETE — those are a data condition to alert on, not a
job failure to retry-storm. A non-zero exit means the job itself broke.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.db.session import AsyncSessionLocal
from app.services.deletion.backfill import outstanding_unresolved_count
from app.services.deletion.handlers.guests import purge_expired_guest_pii
from app.services.deletion.service import DeletionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tyohaar.retention")


async def run() -> dict:
    service = DeletionService(AsyncSessionLocal)

    summary = await service.run_due()

    async with AsyncSessionLocal() as session:
        guest_counts = await purge_expired_guest_pii(session)
        await session.commit()

    unresolved = await outstanding_unresolved_count()

    result = {
        **summary,
        "guest_pii": guest_counts,
        "unresolved_media_assets": unresolved,
    }

    # Surfaced every run rather than only when it changes: an operator reading
    # yesterday's log should not have to search history to learn that media
    # deletion is currently unreliable.
    if unresolved:
        logger.warning(
            "%s media asset(s) cannot be deleted from storage — media purge "
            "is not fully reliable while this is above zero",
            unresolved,
        )

    if summary.get("incomplete"):
        logger.warning(
            "%s deletion request(s) finished INCOMPLETE and will be retried "
            "on the next run",
            summary["incomplete"],
        )

    return result


def main() -> int:
    try:
        result = asyncio.run(run())
    except Exception:  # noqa: BLE001 - the job itself failed
        logger.exception("retention job failed")
        return 1

    logger.info("retention job complete: %s", json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
