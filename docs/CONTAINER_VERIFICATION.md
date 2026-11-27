# Local Linux container verification

## Gemini migration release candidate — 2026-11-27 (IST)

A fresh `linux/amd64` production build from the checkout at `761b930` plus the Flash-Lite reserve changes passed on Docker Engine 29.9.3 in an isolated Alpine WSL2 distro. The build pulled the base image and installed the API lockfile from scratch. The runtime passed `pip check`, ran as UID 1000 and contained neither the checkout's `.env` nor upload, example, test or frontend files.

The running image used the production launcher on a custom port. With 512 MiB and 0.1 CPU confirmed in cgroup v2, it reached health HTTP 200 in 10.67 seconds, created a session (201), enforced authentication and exact-origin CORS, loaded and removed the 4 × 5 sample, and returned 1,000 from the real worker using synthetic input. It peaked at 167.38 MiB, restarted in 10.70 seconds and invalidated the previous session. No provider keys or calls were used. This WSL engine reported no Docker swap-limit support, so the run did not verify a no-swap profile. The worker's basic execution checks are not a hardened security sandbox.

The existing Docker Desktop 4.97.0 launcher and backend still fail on a missing product registry key. The validation engine was isolated from its existing WSL disks. The test container was removed, and the separate `DataBuddy-Task5-Acceptance` distro and tagged image can be reused. Start `wsl -d DataBuddy-Task5-Acceptance --cd / -- dockerd --host=unix:///var/run/docker.sock` in one terminal, then run `wsl -d DataBuddy-Task5-Acceptance -- docker version` in another.

## Earlier verification

The reorganized production image built on 2026-11-05 and passed health/session/sample checks at 512 MiB/no swap/0.1 CPU, a real calculation worker and non-root/private-file checks. Hosted real-provider acceptance followed. See [hosted verification](WEBAPP_VERIFICATION.md). The 198-test suite for that release was exercised on Windows. The detailed October 30 measurements follow.

Date: 2026-10-30 (Asia/Kolkata). The owner authorized Docker installation and local container/resource testing after enabling WSL and restarting Windows. The hosting target remains Cloudflare Pages + Render Free. No hosting account, deployment, commit or push is part of this work.

## Environment and image

- WSL 3.0.3, Linux kernel 6.18.54.1, x86-64; Docker Desktop 4.97.0 and Engine 29.9.2, Linux containers and cgroup v2. Memory, swap and CPU-quota controls are supported.
- Installed Docker in per-user mode from its official versioned installer. Its SHA-256 matched the published package manifest and its Authenticode signature was valid for Docker Inc. No additional Windows elevation or cloud account was needed after the owner's WSL restart.
- Tested application source at `64b49c5`. Built the existing production Dockerfile for `linux/amd64`, without application or dependency changes. The runtime is Python 3.11.18; all **47** API-lock package versions match and `python -m pip check` passes.
- Production image: `databuddy:validation-20261030`, image/index ID `sha256:547c14922e9a108faca819306ed13f090c36babec7f13ae12fed5b72db626c1c`. The resolved `python:3.11-slim` base digest was `sha256:673719e071ecf27434fd2635bbd8d00f49f4fdd81f243143438a42ced8bedf60`. The Dockerfile retains its existing mutable base tag; future builds may select a newer Python patch/base.
- Confirmed UID 1000 (`appuser`) and absence of real environment files, keys, private uploads, saved state, tests and browser fixtures from the production image. No host `.env` or private-data directory was mounted into a verification container.

## Regression checks

- Windows: **183 Python tests passed in 44.83 seconds**, ten frontend tests passed, and TypeScript/Vite production build passed.
- Linux: **183 Python tests passed in 25.68 seconds**, with networking disabled. This includes installed-SDK fake streaming transports, real loopback HTTP streaming/reconnect/Stop, loader/worker checks and legacy interfaces. One previously documented Starlette/httpx deprecation warning remains.
- The Linux regression image derives from the production image and adds pinned pytest, psutil, Streamlit and explicit synthetic/source test files. Its API dependency versions are constrained to the production lock. The suite runs with 2 CPUs/2 GiB to test correctness, independently of the small-host resource probes below.
- Resource probes use a separate production-derived image adding **only psutil and the diagnostic scripts**. In particular, they do not install Streamlit/PyArrow or change pandas' optional-backend behavior.

All verification uses synthetic data, fake provider responses or endpoints that do not invoke providers. No live inference quota was used.

## Resource results

Each case runs alone with a **512 MiB hard memory limit and zero swap**, first at 1 CPU and then at 0.1 CPU. Linux cgroup counters confirm `memory.max=536870912`, `memory.swap.max=0` and `cpu.max=10000 100000` for the strict runs. All eight runs loaded the data and completed a real disposable calculation/chart worker, with zero cgroup OOM/kill events. The worker limit was 30 seconds.

| Synthetic case | Upload MiB | 1-CPU cgroup peak MiB | 0.1-CPU cgroup peak MiB | 0.1-CPU load/import seconds | 0.1-CPU worker seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Four-row sample | <0.01 | 163.07 | 162.83 | 23.51 | 16.81 |
| 240,000-row CSV | 19.45 | 356.05 | 355.98 | 34.80 | 18.80 |
| 200-column CSV | 19.07 | 330.45 | 330.41 | 38.00 | 17.50 |
| 20,000-row XLSX | 0.22 | 182.32 | 184.55 | 40.40 | 17.90 |

Load/import timing includes constructing the synthetic payload, imports of all three provider SDKs and API, parsing and profiling. The XLSX case also creates its workbook in that interval. These are diagnostic cold-process timings, not ordinary warm-upload or complete real-provider response latency. Summed parent/worker RSS is also sampled: the largest strict-run total was 385.50 MiB. Summed RSS can double-count shared pages; the cgroup peak measures the container's charged memory and is the main limit comparison.

The production image itself was separately started over real loopback HTTP at 512 MiB/no swap/0.1 CPU, using its normal command and a non-default `PORT`. Health, bearer authentication, explicit CORS/preflight, sample loading, failed replacement preserving the old dataset, reset and removal passed. Initial readiness and readiness after a restart each took **13.39 seconds**; the observed pre-restart memory peak was 72.53 MiB. The restart invalidated the old in-memory session as intended. No provider keys were supplied and no analysis-provider requests were submitted in this production smoke check.

## Reproduction

Docker Desktop must be running in Linux-container mode. A newly opened terminal picks up its installed CLI path. From the working checkout:

```powershell
docker build --platform linux/amd64 --tag databuddy:local .
docker run --rm --network none databuddy:local python -m pip check
docker run --rm --memory 512m --memory-swap 512m --cpus 0.1 -p 127.0.0.1:18008:8000 -e EXEC_TIMEOUT_SECONDS=30 databuddy:local
```

The last command exposes the API locally at `http://127.0.0.1:18008`; `/api/health` should return `{"status":"ok"}`. It deliberately supplies no provider credentials. Stop it before reusing the port.

For resource diagnostics, create a disposable image derived from `databuddy:local` that installs `psutil==7.2.2`, constrained by `/app/requirements/api-lock.txt`, then returns to `USER appuser`. Mount only this checkout's `scripts` directory read-only at `/app/scripts` and run `python /app/scripts/resource_check.py --case near-limit` with `--network none --memory 512m --memory-swap 512m --cpus 0.1 -e EXEC_TIMEOUT_SECONDS=30`. Repeat with `sample`, `wide` and `xlsx`. The ordinary probe prints size, timing, summed RSS and execution status; it exits normally even if `execution_ok` is false, so inspect that field rather than relying only on the process exit code.

The local aggregate JSON/build/test records and explicit disposable-context helpers are under ignored `output/docker-validation-2026-10-30/`; they are not part of the versioned application. All test containers were removed. Production and diagnostic images remain local for repeat checks.

## What this establishes and what remains

These checks establish that the locked application builds and runs on Linux amd64 and that the measured single-dataset workloads fit the locally enforced resource envelope. They support proceeding to Render Free deployment acceptance. No application change or upload-limit reduction was needed.

They do not certify every permitted 20 MiB file, all combinations of resident sessions, sustained concurrent traffic, or a complete real-provider exchange within its deadline. Parsing can peak before DataFrame admission. Strict 0.1-CPU operation is slow even when it succeeds. WSL2 CPU scheduling, local disk/page caches and networking differ from Render.

Still required after deployment authorization: actual Cloudflare/Render origins and private secret configuration; hosted cold wake-up and failure feedback; streaming through real proxies; actual-provider usage/fallback/Stop behavior; browser chart/export acceptance against the deployed API; and hosted resource monitoring. Local readiness is not a measurement of Render's idle wake-up time. The earlier live core acceptance remains historical, not a fresh live-provider check.

Basic execution checks and Docker packaging are **not a hardened security sandbox**. The application remains a trusted, session-only portfolio demo.

Official references used: [Docker Windows installation](https://docs.docker.com/desktop/setup/install/windows-install/), [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), [Render compute plans](https://render.com/docs/compute-plans).
