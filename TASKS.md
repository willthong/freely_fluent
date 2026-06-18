# Freely Fluent — TDD Tasks

Tracking development across issues using TDD + separate MRs.

| # | Issue | Branch | Status | Notes |
|---|---|---|---|---|
| 2 | Back button / breadcrumb | `issue-2-back-button` | ✅ Done | Backend + frontend + tests. |
| 4 | English-only search button | `issue-4-english-search` | ✅ Done | Button + template context + tests. |
| 6 | Image preview on hover/long-press | — | ⬜ Not started | CSS uncrop + overlay. |
| 5 | Multi-image selection | — | ⬜ Not started | Checkboxes + accumulate. Backend done. |
| 1 | Auto-downscale images | — | ⬜ Not started | Pillow + CardGenerator. |

## Progress

### Issue #2 — Back button / breadcrumb

**Plan:**
- [ ] Add a POST `/sessions/{session_id}/back` button to the step bar in `base.html`
- [ ] Make "done" step labels clickable
- [ ] Write frontend integration tests

**TDD cycles:**
- [ ] RED: Write test → fail
- [ ] GREEN: Implement → pass
- [ ] REFACTOR

### Issue #4 — English-only search button

**Plan:**
- [ ] Add "Search in English 🔤" button to `image_step.html`
- [ ] Add route or modify existing re-search to pre-fill with English word
- [ ] Write tests

**TDD cycles:**
- [ ] RED: Write test → fail
- [ ] GREEN: Implement → pass
- [ ] REFACTOR

### Issue #6 — Image preview on hover/long-press

**Plan:**
- [ ] CSS to uncrop thumbnails (correct aspect ratio)
- [ ] Hover overlay showing full uncropped image
- [ ] Long-press support for mobile

**TDD cycles:**
- [ ] RED: Write test → fail
- [ ] GREEN: Implement → pass
- [ ] REFACTOR

### Issue #5 — Multi-image selection

**Plan:**
- [ ] Change image cards from radio/click to checkboxes
- [ ] Accumulate selections across standard + custom search
- [ ] Show selected images area with deselect
- [ ] Write tests

**TDD cycles:**
- [ ] RED: Write test → fail
- [ ] GREEN: Implement → pass
- [ ] REFACTOR

### Issue #1 — Auto-downscale images

**Plan:**
- [ ] Add `Pillow` dependency
- [ ] Add `max_image_width` config (default 800)
- [ ] Downscale in `CardGenerator._write_media` or image writing path
- [ ] Write tests

**TDD cycles:**
- [ ] RED: Write test → fail
- [ ] GREEN: Implement → pass
- [ ] REFACTOR
