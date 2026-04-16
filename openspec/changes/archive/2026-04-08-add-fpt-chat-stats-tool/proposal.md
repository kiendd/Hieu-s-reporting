# Change: Add FPT Chat Statistics Tool

## Why
The "Hau reporting" team needs a repeatable way to track document-request activity inside FPT Chat group conversations. Currently, someone must scroll through chat history manually to identify who requested what reports and how many files were served. A CLI tool that calls the FPT Chat API and produces a structured report eliminates that manual work.

## What Changes
- **NEW** `fpt_chat_stats.py` — single-file CLI script that fetches the full message history of a chat group, analyzes it, and outputs a statistical report (text or JSON).
- **NEW** `requirements.txt` — declares the `requests` dependency.

## Impact
- Affected specs: `fpt-chat-stats` (new capability, no existing spec to modify)
- Affected code: `fpt_chat_stats.py`, `requirements.txt`
- No breaking changes; this is a net-new addition.
