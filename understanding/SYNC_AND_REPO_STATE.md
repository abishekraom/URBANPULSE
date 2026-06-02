# Sync and Repository State

## Git synchronization result

Commands run from `D:/URBANPULSE`:

```bash
git fetch origin --prune
git status --short --branch
git rev-list --left-right --count HEAD...@{upstream}
git log --oneline --decorate --graph --max-count=10 --all
```

Observed state:

```text
## main...origin/main
 m .agent/skills/remotion-video-pipeline/resources/template

Divergence: 0 0
HEAD: 1e1eea0 (HEAD -> main, origin/main, origin/HEAD) Merge pull request #5 from amoghshetty1313-clg/main
```

## Pull needed?

No pull is needed right now. `main` is exactly synchronized with `origin/main` after fetch.

## Dirty working tree

Before creating this `understanding/` folder, the only dirty item was:

```text
.agent/skills/remotion-video-pipeline/resources/template
```

That path is outside the UrbanPulse application source and looks like an agent-skill/resource artifact. Do not overwrite or clean it unless Lust explicitly asks.

After this analysis, `understanding/` files are intentionally added/updated as durable project reference docs.

## Remotes

```text
origin https://github.com/abishekraom/URBANPULSE.git (fetch)
origin https://github.com/abishekraom/URBANPULSE.git (push)
```

## Branches seen

```text
main    1e1eea0 [origin/main]
backend 61f9d99 docs: fix mock publisher node argument in README
```

## Codebase size survey

`pygount` summary excluding `.git,node_modules,dist,__pycache__,.agent`:

| Language | Files | Code lines | Comment/doc lines |
|---|---:|---:|---:|
| Python | 27 | 1481 | 318 |
| JSX | 10 | 1221 | 54 |
| HTML | 2 | 866 | 21 |
| Arduino | 3 | 695 | 210 |
| CSS+Lasso | 1 | 88 | 7 |
| JSON | 2 | 73 | 0 |
| JavaScript | 3 | 72 | 0 |
| INI | 2 | 16 | 0 |
| Markdown | 78 | 0 | 3399 |
| Total | 138 files | 4539 code | 4108 comments/docs |

## Important non-vendor file tree

```text
backend/
  api/routers/{alerts,nodes,sensor_data,system,ws}.py
  core/{classifier,contract,firmware_adapter,health_score,heartbeat,pipeline}.py
  db/{connection,queries}.py
  mqtt/{ingester,publisher}.py
  ws/hub.py
  main.py
  mock_publisher.py
  stress_test.py
  endurance_test.py
  test_ws.py
  config.json
  requirements.txt
  mosquitto.conf

frontend/
  src/App.jsx
  src/store.js
  src/components/{AlertTimeline,FFTWaveform,Footer,HistoricalChart,NodeCard,RawDataGrid,StatusBanner,StructuralMap}.jsx
  src/index.css
  vite.config.js
  package.json

firmware/hardware:
  sensor_node/src/sensor_node.ino
  pio_gateway/src/gateway_node.ino
  gateway_node/gateway_node.ino
  sensor_node/platformio.ini
  pio_gateway/platformio.ini
  pin_connections.txt

project docs:
  urbanpulse_project_bible.html
  README.md
  SESSION_CHANGES.md
  .gsd/STATE.md
  .gsd/SPEC.md
  .gsd/ROADMAP.md
```
