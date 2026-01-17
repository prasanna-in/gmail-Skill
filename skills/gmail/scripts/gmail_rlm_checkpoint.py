"""
Gmail RLM Checkpoint/Resume System

This module provides checkpoint and resume functionality for long-running
RLM operations. It allows parallel_map operations to save progress and
resume from where they left off if interrupted.

Features:
- Automatic checkpointing during parallel_map operations
- Resume from checkpoint with validation
- MD5 hash validation to ensure checkpoint matches current email set
- Session state preservation (token counts, call counts)
"""

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Any


@dataclass
class RLMCheckpoint:
    """
    Represents a checkpoint for an RLM operation.

    Stores intermediate results and session state to enable
    resumption of interrupted operations.
    """
    session_id: str
    checkpoint_id: str
    created_at: str
    emails_hash: str              # MD5 of email IDs for validation
    processed_indices: list[int]  # Which chunks have been completed
    intermediate_results: dict    # {chunk_index: result}
    session_state: dict           # Token counts, call count, etc.
    total_chunks: int
    prompt_hash: str              # Hash of the prompt for verification

    def save(self, path: Path) -> None:
        """
        Persist checkpoint to JSON file.

        Args:
            path: File path to save checkpoint
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "RLMCheckpoint":
        """
        Load checkpoint from file.

        Args:
            path: File path to load checkpoint from

        Returns:
            RLMCheckpoint instance

        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
            json.JSONDecodeError: If file is corrupted
        """
        path = Path(path)
        data = json.loads(path.read_text())
        return cls(**data)

    def is_valid_for(self, emails: list[dict], prompt: str = None) -> bool:
        """
        Check if checkpoint matches current email set and prompt.

        Args:
            emails: Current list of email dictionaries
            prompt: Optional prompt to verify (if stored)

        Returns:
            True if checkpoint is valid for this email set
        """
        current_hash = _compute_emails_hash(emails)
        if current_hash != self.emails_hash:
            return False

        # Optionally verify prompt hasn't changed
        if prompt is not None and self.prompt_hash:
            current_prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            if current_prompt_hash != self.prompt_hash:
                return False

        return True

    @property
    def progress_pct(self) -> float:
        """Return completion percentage."""
        if self.total_chunks == 0:
            return 0.0
        return len(self.processed_indices) / self.total_chunks * 100


def _compute_emails_hash(emails: list[dict]) -> str:
    """Compute MD5 hash of email IDs for checkpoint validation."""
    email_ids = sorted([e.get('id', str(i)) for i, e in enumerate(emails)])
    return hashlib.md5("|".join(email_ids).encode()).hexdigest()


def _compute_prompt_hash(prompt: str) -> str:
    """Compute MD5 hash of prompt for checkpoint validation."""
    return hashlib.md5(prompt.encode()).hexdigest()


def create_checkpoint(
    session_id: str,
    emails: list[dict],
    prompt: str,
    total_chunks: int,
    processed_indices: list[int] = None,
    intermediate_results: dict = None,
    session_state: dict = None
) -> RLMCheckpoint:
    """
    Create a new checkpoint.

    Args:
        session_id: RLM session ID
        emails: List of email dictionaries
        prompt: The prompt being used
        total_chunks: Total number of chunks to process
        processed_indices: List of completed chunk indices
        intermediate_results: Dict of {index: result}
        session_state: Session statistics dict

    Returns:
        RLMCheckpoint instance
    """
    import uuid
    return RLMCheckpoint(
        session_id=session_id,
        checkpoint_id=str(uuid.uuid4())[:8],
        created_at=datetime.now().isoformat(),
        emails_hash=_compute_emails_hash(emails),
        processed_indices=processed_indices or [],
        intermediate_results=intermediate_results or {},
        session_state=session_state or {},
        total_chunks=total_chunks,
        prompt_hash=_compute_prompt_hash(prompt)
    )


def checkpoint_parallel_map(
    func_prompt: str,
    chunks: list,
    context_fn: Callable = str,
    llm_query_fn: Callable = None,
    checkpoint_path: str = None,
    checkpoint_interval: int = 10,
    emails: list[dict] = None,
    session_state_fn: Callable = None,
    max_workers: int = 5,
    on_progress: Callable[[int, int], None] = None,
    **kwargs
) -> list[str]:
    """
    Parallel map with checkpoint/resume support.

    Like parallel_map but saves progress periodically and can resume
    from a checkpoint if interrupted.

    Args:
        func_prompt: Prompt to apply to each chunk
        chunks: List of data chunks
        context_fn: Function to convert chunk to context string
        llm_query_fn: The llm_query function to use
        checkpoint_path: Path to save/load checkpoint (None = no checkpointing)
        checkpoint_interval: Save checkpoint every N chunks (default: 10)
        emails: Original emails list (for checkpoint validation)
        session_state_fn: Function to get current session state dict
        max_workers: Not used in sequential mode (kept for API compatibility)
        on_progress: Optional callback(completed, total) for progress updates
        **kwargs: Additional arguments passed to llm_query_fn

    Returns:
        List of results in same order as chunks

    Example:
        results = checkpoint_parallel_map(
            func_prompt="Summarize these emails",
            chunks=chunk_by_size(emails, 20),
            context_fn=batch_extract_summaries,
            llm_query_fn=llm_query,
            checkpoint_path="/tmp/my_analysis.checkpoint",
            checkpoint_interval=5,
            emails=emails
        )
    """
    if llm_query_fn is None:
        raise ValueError("llm_query_fn is required")

    results = {}
    start_idx = 0
    checkpoint = None
    session_id = "unknown"

    # Try to load existing checkpoint
    if checkpoint_path:
        checkpoint_file = Path(checkpoint_path)
        if checkpoint_file.exists():
            try:
                checkpoint = RLMCheckpoint.load(checkpoint_file)
                if emails and checkpoint.is_valid_for(emails, func_prompt):
                    # Valid checkpoint - resume
                    results = {int(k): v for k, v in checkpoint.intermediate_results.items()}
                    start_idx = len(checkpoint.processed_indices)
                    session_id = checkpoint.session_id
                    print(f"Resuming from checkpoint: {start_idx}/{len(chunks)} completed ({checkpoint.progress_pct:.1f}%)", file=__import__('sys').stderr)
                else:
                    # Invalid checkpoint - start fresh
                    print("Checkpoint invalid for current data, starting fresh", file=__import__('sys').stderr)
            except Exception as e:
                print(f"Could not load checkpoint: {e}, starting fresh", file=__import__('sys').stderr)

    # Get session ID if not from checkpoint
    if session_id == "unknown" and session_state_fn:
        state = session_state_fn()
        session_id = state.get("session_id", "unknown")

    # Process chunks sequentially (for checkpointing reliability)
    # Note: For parallel processing with checkpointing, use parallel_map directly
    # and handle checkpointing at a higher level
    total = len(chunks)

    for i in range(start_idx, total):
        chunk = chunks[i]
        context = context_fn(chunk)

        # Make LLM call
        result = llm_query_fn(func_prompt, context, **kwargs)
        results[i] = result

        # Progress callback
        if on_progress:
            on_progress(i + 1, total)

        # Save checkpoint periodically
        if checkpoint_path and ((i + 1) % checkpoint_interval == 0 or i == total - 1):
            processed = list(range(i + 1))
            state = session_state_fn() if session_state_fn else {}

            cp = create_checkpoint(
                session_id=session_id,
                emails=emails or [],
                prompt=func_prompt,
                total_chunks=total,
                processed_indices=processed,
                intermediate_results={str(k): v for k, v in results.items()},
                session_state=state
            )
            cp.save(Path(checkpoint_path))

    # Return results in order
    return [results[i] for i in range(len(chunks))]


def load_checkpoint_info(checkpoint_path: str) -> Optional[dict]:
    """
    Load checkpoint metadata without full restoration.

    Args:
        checkpoint_path: Path to checkpoint file

    Returns:
        Dict with checkpoint info, or None if not found
    """
    path = Path(checkpoint_path)
    if not path.exists():
        return None

    try:
        checkpoint = RLMCheckpoint.load(path)
        return {
            "session_id": checkpoint.session_id,
            "checkpoint_id": checkpoint.checkpoint_id,
            "created_at": checkpoint.created_at,
            "progress": f"{len(checkpoint.processed_indices)}/{checkpoint.total_chunks}",
            "progress_pct": checkpoint.progress_pct,
            "session_state": checkpoint.session_state
        }
    except Exception:
        return None


def clear_checkpoint(checkpoint_path: str) -> bool:
    """
    Remove a checkpoint file.

    Args:
        checkpoint_path: Path to checkpoint file

    Returns:
        True if removed, False if not found
    """
    path = Path(checkpoint_path)
    if path.exists():
        path.unlink()
        return True
    return False
