# Project Context

## Purpose
Internal tooling for the "Hau reporting" initiative at FPT.  
The project provides CLI utilities that read data from FPT Chat (internal messaging platform) and produce statistical reports on user activity — primarily tracking who requests documents and what files are shared in group chats.

## Tech Stack
- Python 3.11+
- `requests` library for HTTP API calls
- Standard library only beyond that (no framework, no database)

## Project Conventions

### Code Style
- Single-file scripts preferred; split only when complexity warrants it.
- `argparse` for CLI interfaces.
- UTF-8 everywhere; Vietnamese strings are first-class.
- Print progress/debug to `stderr`; report output to `stdout`.

### Architecture Patterns
- **Fetch → Analyze → Report** pipeline per tool.
- Pagination is cursor-based: pass the oldest fetched message ID as `before=<id>` to get older pages.
- Auth: send token as both `Authorization: Bearer <token>` header and `fchat_ddtk` cookie.

### Testing Strategy
- Tools support `--load <file>` to run offline against a saved JSON snapshot.
- No automated test suite yet; manual validation with sample data.

### Git Workflow
- Direct commits to `main`; no branch strategy enforced yet.

## Domain Context
- FPT Chat API base: `https://api-chat.fpt.com`
- Message types: `TEXT`, `FILE`, `ACTIVITY`
- Group messages endpoint: `/message-query/group/<groupId>/message?limit=<n>`
- Token: `fchat_ddtk` value from the FPT Chat login URL query parameter.
- Group ID: 24-character hex MongoDB ObjectId extracted from the chat URL.

## Important Constraints
- Token is a personal session key — never commit tokens to source control.
- Tools are read-only; no write operations against the chat API.

## External Dependencies
- FPT Chat API: `https://api-chat.fpt.com` (internal, no public docs)
