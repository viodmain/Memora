# Memora Project Instructions

## Auto Memory Extraction

At the end of every conversation, you MUST call the `extract_and_save` MCP tool to extract and save any valuable information from the conversation. This includes:

- Technical decisions (frameworks, tools, architecture choices)
- User preferences (coding style, tools, workflows)
- Important facts (deployment info, configurations, credentials locations)
- Lessons learned (debugging insights, gotchas)

Example call:
```
extract_and_save(messages=[...conversation messages...])
```

## Memory Recall

At the start of a new conversation, if the user asks about previous work or context, call `recall` to search for relevant memories before responding.

## Document Ingestion

When the user shares or references a document, offer to ingest it with `ingest_document`.
