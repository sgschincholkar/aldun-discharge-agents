# Lessons & Corrections

## 2026-06-02

### Don't suggest unnecessary steps
**Mistake:** Suggested taking screenshots and navigating the browser when the user can simply open the UI themselves.
**Rule:** Before suggesting any action, ask: "Is this something the user can do themselves in 1 second?" If yes, just tell them what to do — don't reach for tools.

### Re-check context before responding
**Mistake:** Jumped to browser automation without re-reading what was already available (the Flask UI at localhost:5001 handles everything in one click).
**Rule:** Always re-read the relevant context (CLAUDE.md, current files, conversation history) before suggesting a next step. Don't suggest steps that are already handled.
