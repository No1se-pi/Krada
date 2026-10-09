import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Trusted tenant boundary derived from a verified server-side session.

    Player-facing DTOs deliberately cannot construct or override this context. Keeping the
    school identifier in a dedicated value object makes tenant-sensitive repository calls
    conspicuous during review and leaves a seam for a future shard router.
    """

    school_id: uuid.UUID
