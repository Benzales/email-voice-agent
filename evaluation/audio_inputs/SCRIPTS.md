# Audio Input Scripts Overview

This directory contains audio input scripts for testing the email voice agent. Each action has its own subdirectory with 3 different phrasings:

1. **Minimal**: Short, direct command
2. **Long/Confusing**: Verbose or indirect phrasing to test understanding
3. **Short/Ambiguous**: Brief but potentially ambiguous phrasing

## Directory Structure

```
audio_inputs/
├── archive/          # Archive email actions
├── delete/           # Delete email actions
├── mark_unread/      # Mark as unread actions
├── mark_read/        # Mark as read actions
├── send_email/       # Send email actions
├── draft_email/      # Save as draft actions
├── move_to_label/    # Move to label actions
├── read_email/       # Read email content actions
├── list_labels/      # List available labels
├── create_label/     # Create new label
├── update_label/     # Update/rename label
└── delete_label/     # Delete label
```

Each subdirectory contains:
- `SCRIPTS.md` - Detailed scripts for each WAV file
- 3 WAV files with different phrasings

## Recording Guidelines

When recording these scripts:
1. Speak naturally as if talking to a voice assistant
2. Include pauses, "um"s, and natural speech patterns for the longer scripts
3. Vary your tone and speed between recordings
4. For ambiguous scripts, don't over-emphasize keywords that would make intent too clear 