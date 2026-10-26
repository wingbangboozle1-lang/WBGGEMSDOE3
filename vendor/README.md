# Shared instruments — unmodified, not a private fork

Seven files from buffedlizard55-lab/GEMSDOE24 at commit fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1 are retained byte-for-byte for reuse and review. `pins.json` records origin URLs, paths and SHA-256 values; tests verify every byte. Attribution and module documentation remain intact.

These are peer-maintained instruments, not organizer-authenticated code. They are not a complete model repository. Use `gems.holdout.SegmentHoldout`, not the legacy `Holdout`, for the prospective protocol. The method-specific upstream `scripts/evaluate_holdout.py` is deliberately not advertised as a generic runner. No feature stack or experiment is packaged here. Template identity needs reconciliation with peers that pin 57GEMSDOE.

The writer sanitizes/clips input and supports zero/NaN outside variants. For a future release, reject malformed model inputs before writer invocation rather than concealing upstream errors through sanitization. The shared note helper allows a longer note than this brief: enforce the brief's 140-character limit externally. No files were privately patched.
