# Copilot Instructions for WESI

## 1. Big picture
- Single-module desktop app in `main.py`; no service boundary split currently.
- Uses `ttkbootstrap` + `tkinter` for UI. `SalaryPetApp` is the orchestration root.
- Persistent state in `data/app_state.json` via `DataStore`. On load, it deep-merges with `DEFAULT_STATE` and writes defaults when missing/corrupt.
- Features: salary timer, quote system, battle mode, tarot reading, virtual pet (forage/inventory), achievements.
- Assets under `assets/`; data under `data/` (`tarot_cards_zh.json`, `tarot-images.json`, `quotes_library.json`, optional `d2data_json/`).

## 2. Startup / developer workflow
- Install dependencies:
  - `pip install -r requirements.txt`
- Run app:
  - `python main.py`
- Regenerate tarot data from source:
  - `python tools/make_tarot_json.py` (reads `data/tarot-images.json`, writes `data/tarot_cards_zh.json`).

## 3. Key structural patterns
- UI view open/focus management: `SalaryPetApp._open_or_focus(key, windowClass)` ensures one window instance per type.
- Theme runtime: `apply_theme` + `_refresh_color_overrides` use `store.state["theme"]` colors.
- Savings pattern: state updates go through `self.store.state` and `self.store.save()` (especially in settings, battle, pet, achievements).
- Achievement triggers in `increment_achievement_check`; called every 200ms from `update_income_ui`.
- `DataStore.load()` uses `deep_merge` so schema changes are additive and backward-compatible.

## 4. Important functions to know
- `get_income_stats()` + `earnings_between()` (salary compute across month boundaries).
- `choose_weighted` + `RARITY_WEIGHTS` (random loot logic in pet forage).
- `load_tarot_cards()` requires JSON shaping as `{"cards": [...]}` and may throw if missing.
- `safe_copy_image` and `make_rounded_image` used for avatar/pet assets; `Pillow` optional fallback.

## 5. Data and format expectations
- App state keys: `income`, `theme`, `battle`, `quotes`, `pet`, `tarot`, `achievements`.
- `pet.inventory` items are dicts (`name`, `rarity`, `desc`) and `forage_count` used for achievement checks.
- `tarot.history` stores draws and shown in `TarotHistoryWindow`.

## 6. Localized convention
- UI labels/messages are primarily simplified Chinese (e.g. `"设置"`, `"成就"`).
- Keep existing Chinese/English mix in text constants for style consistency.

## 7. If adding features
- Prefer adding new helper functions near top-level util section (`parse_dt`, `format_now`, etc.).
- Add UI flows in `SalaryPetApp.build_ui` + window class in `main.py`.
- For new persistent state fields, extend `DEFAULT_STATE` and let `deep_merge` handle existing files.

## 8. Common gotchas
- `ttkbootstrap` theme mismatch: fallback to `darkly` in `apply_theme`.
- `data/app_state.json` can be overwritten to defaults on parse errors.
- `load_quote_library` returns built-in fallback if `quotes_library.json` malformed.

## 9. No dedicated tests yet
- No tests found in repository; focus on behavior verification via running app and manually clicking flows.

## 10. Ask for clarification
- If uncertain about a UI flow (e.g., battle damage formulas or tarot layout), inspect `BattleWindow`, `TarotWindow`, and `PetWindow` in `main.py`.
