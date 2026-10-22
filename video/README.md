# Maintenance Atlas animated showcase

**Output:** Maintenance-Atlas-Showcase.mp4

48 seconds, 1920 × 1080, 30 fps. H.264 video with AAC stereo audio. The score is an original synthesized ambient track with no sampled music or narration.

## Scenes

| Time | Content |
| --- | --- |
| 00–05 | Banking aircraft and Atlas introduction |
| 05–10 | Animated plain-language fault entry |
| 10–16 | Illustrative historical-record retrieval |
| 16–22 | BM25 and BGE flow into rank fusion |
| 22–27 | Citation example using invented DEMO-007 |
| 27–32 | Illustrative evidence signals and refusal |
| 32–38 | Pulsing engine fault on the actual Atlas airframe |
| 38–43 | Internal engine illustration, rotating fan and source uncertainty |
| 43–48 | Closing message and pending deployment checks |

Main captions use short phrases. The graph explicitly shows illustrative signals, not measured scores. Demo evidence does not assert a real maintenance diagnosis. Educational component geometry and possible complications remain unverified.

## Editable sources

- `render-atlas.mjs`: timeline, typography, motion, diagrams and MP4 encoding.
- `make-soundtrack.py`: deterministic original score.
- `assets/`: rasterized versions of the project's authored SVG aircraft, engine highlight and engine cutaway.
- `preview.png`: cover frame.

The renderer reuses the actual airframe and engine SVG from `api/static/maintenance/`. It uses the available Node runtime's `@napi-rs/canvas` and `sharp` packages. Configure `RUNTIME_NODE_MODULES` for another machine. Encoding uses FFmpeg, supplied here through `imageio-ffmpeg` in the ignored `.video-build/deps` directory, or an executable set via `ATLAS_FFMPEG`.

Render the score with Python plus NumPy, then run the Node renderer from the repository root. Build frames and encoder logs stay in `.video-build/` and are excluded locally from Git.

Verification: all 1,440 frames encoded, representative scenes reviewed, and the complete MP4 decoded without errors. Duration 48.00 seconds, 1080p H.264/yuv420p at 30 fps, stereo AAC 44.1 kHz. This is a product explainer, not a recording of verified live backend operation.
