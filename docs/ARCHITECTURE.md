# Architecture

```text
UI
├── MainWindow          minimal recorder and multi-monitor trace
└── AimLabWindow        automatically balanced local target test

Capture
├── MouseRecorder       pynput mouse-only events
├── RawMouseListener    Windows relative dx/dy
└── InputModeDetector   absolute vs relative game behavior

Analysis
├── metrics             natural movement metrics
├── aim_metrics         exact target behavior
├── aim_scheduler       balanced target generation
└── profile_builder     combines every local session

Storage
└── SessionWriter       append-only JSONL + summaries
```

## Coordinate model

Normal use stores global desktop X/Y. Monitor geometry may include negative coordinates. Gaming also stores unbounded relative raw counts. Optional calibration converts raw counts into virtual yaw/pitch.

## Safety boundary

Recorded data is analyzed and replayed only as a visual trace inside the app. There is no external cursor playback or keyboard hook.
