---
name: brainstorming
description: Facilitates creative exploration of ideas, requirements, and designs. Use before implementation to refine user intent and create architectural specs.
---

# Brainstorming & Design

## When to use this skill

- When the user has a vague idea or request.
- When starting a new feature or project from scratch.
- When the user asks to "brainstorm" or "think about" a problem.

## Workflow

1.  **Understand Context**: Check current project state, files, and docs.
2.  **Iterative Inquiry**: Ask **one question at a time** to clarify the idea. Prefer multiple-choice.
3.  **Explore Approaches**: Propose 2-3 approaches with trade-offs. Recommend one.
4.  **Draft Design**: Present the design in small sections (200-300 words) for feedback.
5.  **Finalize**: Write the validated design to `docs/plans/YYYY-MM-DD-topic-design.md`.

## Instructions

### Process Rules

- **One question at a time**: Don't overwhelm the user.
- **Multiple choice preferred**: "Should we use A, B, or C?" is better than "How should we do this?".
- **YAGNI ruthlessly**: Remove unnecessary features.
- **Incremental validation**: "Does this section look right so far?"

### Design Document Logic

Once the design is agreed upon, create a design doc including:

- **Overview**: What are we building?
- **Architecture**: High-level structural decisions.
- **Components**: breakdown of UI/logic units.
- **Data Flow**: How data moves.
- **Error Handling**: How things fail safely.
- **Testing Strategy**: How we verify it works.

## Resources

- [See original source](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
