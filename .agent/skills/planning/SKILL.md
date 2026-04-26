---
name: planning
description: Generates detailed, step-by-step implementation plans for coding tasks. Use when the user has a spec or requirements and needs a clear roadmap before writing code.
---

# Planning Implementation

## When to use this skill

- When you have a clear requirement or spec but no code yet.
- When the user asks for a "plan" or "roadmap".
- Before starting complex coding tasks to ensure all steps are thoughtful.

## Workflow

1.  **Analyze Context**: Understand the goal, tech stack, and existing codebase.
2.  **Create Plan File**: Create a new markdown file in `docs/plans/` (e.g., `docs/plans/YYYY-MM-DD-feature-name.md`).
3.  **Draft Headers**: Add the standard header with Goal, Architecture, and Tech Stack.
4.  **Break Down Tasks**: Create bite-sized tasks (2-5 mins each).
    - define the test
    - implementation steps
    - verification steps
5.  **Review**: Ensure every step has exact file paths and commands.

## Instructions

### Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**

- "Write the failing test"
- "Run it to make sure it fails"
- "Implement the minimal code to make the test pass"
- "Run the tests and make sure they pass"
- "Commit"

### Plan Document Header

Every plan **MUST** start with this header:

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure Template

Use this template for each task in the plan:

````markdown
### Task N: [Component Name]

**Files:**

- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**
[Code block with the test]

**Step 2: Run test to verify it fails**
Run: `[Command]`
Expected: FAIL with "[Error message]"

**Step 3: Write minimal implementation**
[Code block with implementation]

**Step 4: Run test to verify it passes**
Run: `[Command]`
Expected: PASS

**Step 5: Commit**

```bash
git add [files]
git commit -m "feat: [message]"
```
````

```

## Resources
- [See original source](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md)
```
