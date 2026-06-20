# Matmul labs — source code & test output guide

This document walks through the **TT-Metalium matmul programming examples**
for **Labs 04–06** on the virtual Wormhole. Complete **Labs 01–02** (elementwise
add and multicast intro under [`ttnn/examples/`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples))
first — they teach the same reader/compute/writer model without matmul complexity.

Read alongside the per-lab READMEs. All paths below use `$TT_METAL_HOME`
( `/opt/tt-metal` on the FULL image).

**API lookup:** [§9 API glossary](#9-api-glossary-source--docs) lists every
major function used in the examples with links to tt-metal **source** and
**official docs**.

Upstream source (same commit the FULL image builds):

- [matmul_single_core.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_single_core/matmul_single_core.cpp)
- [matmul_multi_core.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_multi_core/matmul_multi_core.cpp)
- [matmul_multicore_reuse_mcast](https://github.com/tenstorrent/tt-metal/tree/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast)

---

## 1. Big picture: what a tt-metal program is

Every matmul example follows the same pattern:

```
  Host (C++ on the CPU)
    │  allocates DRAM buffers, configures circular buffers (CBs),
    │  creates kernels, uploads data, launches program, reads result
    ▼
  Device (virtual Wormhole / real silicon)
    ┌─────────────────────────────────────────┐
    │  One Tensix core (Lab 04) or many (05/06)│
    │                                          │
    │  Reader (RISC-V)  ──► CBs ──► Compute (FPU) ──► CB ──► Writer │
    │       ▲                              │                    │   │
    │       └──────── DRAM (A, B)          │                    └──► DRAM (C)
    └─────────────────────────────────────────┘
```

| Piece | Runs on | Job |
|---|---|---|
| **Host** | CPU in the Codespace | Setup, launch, verify |
| **Reader kernel** | Tensix data-movement RISC-V | Read input **tiles** from DRAM into L1 circular buffers |
| **Compute kernel** | Tensix FPU (matrix engine) | `matmul_tiles` — multiply-accumulate 32×32 tiles |
| **Writer kernel** | Tensix data-movement RISC-V | Write output tiles from L1 back to DRAM |
| **Circular buffers (CBs)** | L1 SRAM on the core | FIFO queues connecting reader → compute → writer |

Kernels do **not** call each other. They synchronize through CBs: the reader
**pushes** tiles in, the compute kernel **waits**, multiplies, **pushes** out,
the writer **pops** and writes to DRAM.

---

## 2. Tiles, dimensions, and memory layout

The hardware thinks in **32×32 tiles**, not individual floating-point numbers.

For all three matmul labs, the default matrix sizes in `main()` are:

| Symbol | Meaning | Default value |
|---|---|---|
| `M` | Rows of A, rows of C | 640 |
| `K` | Cols of A, rows of B | 640 |
| `N` | Cols of B, cols of C | 640 |

Tile counts:

```
Mt = M / 32 = 20    (tile rows of the output)
Kt = K / 32 = 20    (tiles along the dot-product / reduction axis)
Nt = N / 32 = 20    (tile columns of the output)
```

Total output **elements** (not tiles):

```
M × N = 640 × 640 = 409,600
```

That is why you see **`Output vector of size 409600`** — it is the flattened
result matrix C in row-major order, one `bfloat16` per element.

Before sending data to the device, the host **tilizes** row-major matrices into
the layout the hardware expects (`tilize_nfaces`). After reading the result
back, it **untilizes** to row-major for comparison with the CPU golden.

---

## 3. Lab 04 — single-core matmul

**Directory:** `$TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core/`

**Run:** `tt-sim run metal_example_matmul_single_core`

### 3.1 Host program (`matmul_single_core.cpp`)

Execution order in `main()`:

1. **Open device** — `MeshDevice::create_unit_mesh(0)` (one Wormhole).
2. **Generate inputs** — random `bfloat16` values in `[0, 1)` for matrices A
   (`M×K`) and B (`K×N`).
3. **Golden reference** — `golden_matmul()` on the CPU: plain triple-nested
   loop, same math as textbook matrix multiply, stored in `golden_vec`.
4. **Tilize** — convert A and B to tiled layout.
5. **Run on device** — `matmul_single_core(...)` uploads, launches kernels,
   reads result into `result_vec`.
6. **Untilize** — convert result back to row-major.
7. **Verify** — compare `result_vec` vs `golden_vec` using PCC (see §6).

Inside `matmul_single_core()` the host:

- Targets **one core** at `CoreCoord{0, 0}`.
- Creates **three DRAM buffers** (A, B, C) with page size = one tile (2048 B).
- Creates **three circular buffers** on that core:
  - `c_0` — tiles of A (2-tile depth for double buffering)
  - `c_1` — tiles of B
  - `c_16` — output tiles
- **Creates three kernels** on the same core (reader, writer, compute).
- Passes **compile-time args** `{Mt, Kt, Nt}` to the compute kernel.
- Passes **runtime args** to reader/writer (DRAM addresses + tile counts).
- **Enqueues** write → workload → read on the command queue.

### 3.2 Reader kernel (`kernels/dataflow/reader_single_core_mm.cpp`)

Runs on a data-movement RISC-V core. For **each output tile** `(mt, nt)` it
must feed `Kt` pairs of input tiles along the reduction dimension:

- For each `kt` from 0 to Kt−1: read tile `A[mt, kt]` and tile `B[kt, nt]`
  from DRAM and **push** them into `cb_in0` and `cb_in1`.

The reader is responsible for presenting tiles to the compute kernel in the
order the compute loop expects.

### 3.3 Compute kernel (`kernels/compute/mm.cpp`)

Runs on the FPU. Pseudocode:

```
mm_init(cb_in0, cb_in1, cb_out)     // configure matrix engine

for each output tile (mt, nt):
    tile_regs_acquire()              // zero / acquire destination registers
    for kt in 0 .. Kt-1:
        wait for 1 tile on cb_in0    // A[mt, kt]
        wait for 1 tile on cb_in1    // B[kt, nt]
        matmul_tiles(...)            // accumulate into dest registers
        pop both input CBs
    pack result tile → cb_out
    tile_regs_release()
```

Key API calls:

- `mm_init` — set up for matmul (not `binary_op_init_common`, which is for
  elementwise ops).
- `matmul_tiles` — multiply one A tile by one B tile and **add** into the
  destination register (accumulate over `kt`).
- `tile_regs_acquire` / `tile_regs_commit` / `tile_regs_release` — manage
  the FPU register file lifecycle.

### 3.4 Writer kernel (`kernels/dataflow/writer_single_core_mm.cpp`)

Pops finished output tiles from `cb_out` and writes them to the correct
location in DRAM buffer C.

### 3.5 Dataflow for one output tile

For output tile C[mt, nt] (a 32×32 block of the result):

```
C[mt,nt] = sum over kt of  A[mt,kt] × B[kt,nt]
           ─────────────    ────────   ────────
           Kt matmul_tiles  one tile   one tile
           accumulations    of A       of B
```

With M=N=K=640: **20 × 20 = 400 output tiles**, each requiring **20**
multiply-accumulate steps along K.

---

## 4. Lab 05 — multi-core matmul (SPMD)

**Directory:** `.../matmul/matmul_multi_core/`

**Run:** `tt-sim run metal_example_matmul_multi_core`

Same matrix sizes (640³) and same verification (409600 elements, PCC > 0.97).

### What changes vs Lab 04

| Aspect | Lab 04 (single core) | Lab 05 (multi core) |
|---|---|---|
| Cores used | One: `{0,0}` | Entire compute grid (`split_work_to_cores`) |
| Work split | All 400 output tiles on one core | Output tiles partitioned across cores |
| Kernel binaries | Same reader/compute/writer per core | **Same** binaries on every core (SPMD) |
| Per-core behavior | N/A | **Runtime args** differ: each core gets `work_offset` + `work_per_core` |
| DRAM reads | One core reads all input tiles | Each core reads the tiles **it** needs (redundant reads across cores) |

Host highlights in `matmul_multi_core()`:

```cpp
auto [num_cores, all_cores, core_group_1, core_group_2,
      work_per_core1, work_per_core2] =
    split_work_to_cores(core_grid, num_output_tiles_total);
```

- `num_output_tiles_total = (M × N) / (32×32) = 400`.
- Work is split across the Wormhole Tensix grid. If 400 tiles do not divide
  evenly, some cores get one extra tile (`core_group_1` vs `core_group_2`).
- For **each core**, the host sets runtime args on reader, writer, and compute
  telling that core which slice of the 400 output tiles to produce.

The **compute kernel source** is nearly identical to Lab 04; the parallelism
is almost entirely in the **host** and in **per-core runtime args**.

### Files to compare

```bash
diff -ru \
  $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core/kernels/compute/mm.cpp \
  $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multi_core/kernels/compute/mm.cpp
```

You should see the multi-core reader is different:
`reader_mm_output_tiles_partitioned.cpp` — it knows its tile range from
runtime args.

---

## 5. Lab 06 — multicast matmul (data reuse)

**Directory:** `.../matmul/matmul_multicore_reuse_mcast/`

**Run:** `tt-sim run metal_example_matmul_multicore_reuse_mcast`

Same verification pattern (409600, PCC, Test Passed).

### What changes vs Lab 05

Lab 05 is **correct but wasteful**: every core independently reads the same
input tiles from DRAM when they are shared across output tiles.

Lab 06 fixes this with **multicast over the NoC**:

- A **sender** core reads a shared tile from DRAM **once**.
- It **multicasts** the tile to multiple **receiver** cores over the
  network-on-chip.
- **Semaphores** synchronize senders and receivers so nobody reads a tile
  before it has arrived in L1.

Conceptually:

```
Lab 05:  each core ──► DRAM (many redundant reads of the same A/B tiles)

Lab 06:  one sender ──► DRAM once ──► multicast ──► many receivers
```

### What to read

1. Host — multicast grid geometry (which cores are senders vs receivers).
2. Reader kernels — `noc_async_write_multicast` and matching wait calls.
3. Semaphore setup — `CreateSemaphore` and kernel-side wait/signal.

Compare reader kernels between Lab 05 and Lab 06 to see where per-core DRAM
reads were replaced by multicast.

---

## 6. Understanding the test output

When you run any of the three examples successfully, you see something like:

```
Matrix multiply C = A x B: 640 x 640 * 640 x 640 = 640 x 640
Sample C[i] (device vs CPU golden):
  C[0] device 159.875000  golden 159.875000
  ...
Output vector of size 409600
Metalium vs Golden -- PCC = 0.981743
Test Passed
```

Sample **C[i]** lines are injected by `scripts/patch-lab-output.py` (applied at
`tt-sim setup` / image build, or manually with `tt-sim patch-output`).

### `Output vector of size 409600`

- The result matrix C has shape **M × N = 640 × 640**.
- Each entry is one **`bfloat16`** (16-bit brain float).
- Stored as a **flat row-major vector**: row 0, then row 1, … → 409600 elements.
- Printed in `main()` after `untilize_nfaces` converts the device result back
  to row-major layout.

Quick check:

```
640 × 640 = 409,600   ✓
```

If you change M/N in the host code (keeping them multiples of 32), this number
changes accordingly (`M × N`).

### `Metalium vs Golden -- PCC = 0.981743`

**Golden** = CPU reference (`golden_matmul` in the host `.cpp`). Plain fp32
math, then cast to `bfloat16`.

**Metalium** = what the virtual chip (or real silicon) computed via tiled
matmul on the FPU.

**PCC** = **Pearson correlation coefficient** between the two vectors. It
measures how similarly the two result vectors vary together:

| PCC | Meaning |
|---|---|
| 1.0 | Perfect linear correlation (identical up to scale) |
| ~0.98 | Very strong agreement — typical for a passing matmul run |
| < 0.97 | **Fail** — the example aborts |

The test enforces a threshold in code:

```cpp
TT_FATAL(pearson > 0.97, "PCC not high enough...");
```

Why isn't PCC exactly 1.0?

- **`bfloat16` rounding** — the device uses 16-bit floats; the golden path
  accumulates in fp32 then casts. Small numerical differences are expected.
- **Tiled accumulation order** — the FPU accumulates across K tiles in
  hardware order, which may differ slightly from the CPU loop order.
- **Math fidelity** — compute kernels use `MathFidelity::HiFi4`, but still
  not identical to fp32 CPU math.

A PCC of **0.981743** is well above the **0.97** pass threshold — the results
are numerically trustworthy for this lab.

### `Test Passed`

Printed when:

1. Device opened and program ran without exception.
2. PCC exceeded 0.97.
3. Device closed cleanly.

If something goes wrong (wrong kernel, bad dimensions, simulator error), you
get `Test failed with exception!` and a backtrace instead.

---

## 7. Source file map (all labs)

| Lab | Host | Compute | Reader | Writer |
|---|---|---|---|---|
| **04** | `matmul_single_core/matmul_single_core.cpp` | `kernels/compute/mm.cpp` | `kernels/dataflow/reader_single_core_mm.cpp` | `kernels/dataflow/writer_single_core_mm.cpp` |
| **05** | `matmul_multi_core/matmul_multi_core.cpp` | `kernels/compute/mm.cpp` | `kernels/dataflow/reader_mm_output_tiles_partitioned.cpp` | `kernels/dataflow/writer_unary_interleaved_start_id.cpp` |
| **06** | `matmul_multicore_reuse_mcast/*.cpp` | `kernels/compute/mm.cpp` (variant) | multicast reader(s) | writer(s) |

All under:

```
$TT_METAL_HOME/tt_metal/programming_examples/matmul/
```

Built binaries:

```
$TT_METAL_HOME/build/programming_examples/metal_example_matmul_*
```

---

## 8. Suggested reading order for students

1. Complete Labs **01–02**, then run Lab **04** and read this §3.
2. Open `kernels/compute/mm.cpp` — follow one output tile through the loops.
3. Skim reader and writer for the same example.
4. Run Lab **05** — diff the **host** against Lab 04; find `split_work_to_cores`
   and the per-core runtime-arg loop.
5. Run Lab **06** — diff **reader** kernels against Lab 05; trace one multicast.
6. Keep [§9](#9-api-glossary-source--docs) open as a lookup while reading each `.cpp`.

For the upstream theory writeups, see the
[TT-Metalium matmul labs](https://github.com/tenstorrent/tt-metal/tree/main/docs/source/tt-metalium/tt_metal/labs/matmul)
on docs.tenstorrent.com.

---

## 9. API glossary (source + docs)

Quick reference for APIs that appear in the Lab **04–06** matmul programming
examples (and Lab **02** multicast intro). Links point at commit **`5a4436244ae1b421504da84c01f81fdfdf6049de`**
(the tt-sim-lab pin). Official docs use the **`latest`** doc build; behavior
matches the concepts even if signatures drift slightly on `main`.

**Legend:** **L4** = Lab 04 single-core matmul · **L5** = Lab 05 multi-core · **L6** =
Lab 06 multicast matmul · **L2** = Lab 02 multicast intro · **H** = host · **K** = kernel

### 9.1 Host — device, program, and launch

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `distributed::MeshDevice::create_unit_mesh` | Open a 1×1 mesh (one chip) for programming examples. | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `mesh_device->mesh_command_queue()` | Command queue used for all host→device uploads, launches, and readbacks. | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Getting Started](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/get_started/get_started.html) |
| `distributed::MeshBuffer::create` | Allocate a DRAM buffer on the device (replicated on a unit mesh). | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `distributed::EnqueueWriteMeshBuffer` | Upload host vector data into device DRAM (non-blocking unless waited). | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `distributed::EnqueueMeshWorkload` | Submit a compiled program (all kernels) to the device. | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `distributed::EnqueueReadMeshBuffer` | Read result tensor from device DRAM back to host (`blocking=true` waits). | H · L4–L6 | [distributed.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/distributed.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `mesh_device->close()` | Tear down device; profiler (if enabled) flushes here. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CloseDevice](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/device_management/CloseDevice.html) |
| `Program` | Host-side container for kernels, CBs, and semaphores on a launch. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CreateProgram](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/program/CreateProgram.html) |
| `tt_metal::CreateKernel` | Register a kernel `.cpp` on a core or core range; triggers JIT when run. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CreateKernel](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/kernels/CreateKernel.html) |
| `tt_metal::CreateCircularBuffer` | Allocate L1 CB storage on core(s) and bind a CB index to a data format. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CircularBuffers](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/buffers/CircularBuffers.html) |
| `tt_metal::SetRuntimeArgs` | Per-launch (and per-core) values: DRAM addresses, tile counts, work slice. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [Runtime args](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/runtime_args/runtime_args.html) |
| `tt_metal::CreateSemaphore` | Allocate a device semaphore for sender/receiver sync (Labs 02, 06). | H · L2 · L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CreateSemaphore](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/buffers/CreateSemaphore.html) |
| `CoreCoord` / `CoreRangeSet` | Identify one Tensix core (L4) or a set of cores (L5/L6). | H · L4–L6 | [core_coord.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/core_coord.hpp) | [Lab 1 tutorial](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst) |
| `split_work_to_cores` | Partition output tiles across the Tensix grid (SPMD). | H · L5–L6 | [work_split.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/work_split.hpp) | [Matmul (Multi Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_multi_core.html) |
| `TensorAccessorArgs` | Pack tensor layout into compile-time kernel args for `TensorAccessor`. | H · L4–L6 | [tensor_accessor_args.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/tensor_accessor_args.hpp) | [Tensor accessor tech report](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tech_reports/tensor_accessor/tensor_accessor.md) |
| `MathFidelity::HiFi4` | Highest-precision FPU math mode for compute kernels. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `DataMovementConfig` / `ComputeConfig` | Select RISC-V processor, NoC, compile-time args, math fidelity. | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [CreateKernel](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/kernels/CreateKernel.html) |

### 9.2 Host — data layout and verification

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `tilize_nfaces` | Convert row-major host matrix → tiled layout for device. | H · L4–L6 | [tilize_utils.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/tilize_utils.hpp) | [Lab 1 tutorial §Tile-Based Architecture](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst) |
| `untilize_nfaces` | Convert tiled device result → row-major for CPU compare. | H · L4–L6 | [tilize_utils.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/tilize_utils.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `golden_matmul` | Local CPU reference matmul in each example's host `.cpp`. | H · L4–L6 | [matmul_single_core.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_single_core/matmul_single_core.cpp) | [Lab 1 tutorial §Exercise 7](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst) |
| `check_bfloat16_vector_pcc` | Pearson correlation between golden and device vectors. | H · L4–L6 | via `#include <bmm_op.hpp>` in examples | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `TT_FATAL` | Abort with message if condition false (e.g. PCC too low). | H · L4–L6 | [host_api.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/host_api.hpp) | [Matmul (Single Core) example](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `TILE_HEIGHT` / `TILE_WIDTH` | Tile size constants (32 on Wormhole). | H · K · L4–L6 | [constants.hpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/api/tt-metalium/constants.hpp) | [Lab 1 tutorial §Tile-Based Architecture](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst) |

### 9.3 Kernel — arguments (compile-time vs runtime)

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `get_compile_time_arg_val(i)` | Read host-provided compile-time arg baked into kernel binary. | K · L4 compute | [compile_time_args.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compile_time_args.h) | [get_compile_time_arg_val](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/kernel_args/get_compile_time_arg_val.html) |
| `get_arg_val<T>(i)` | Read per-launch runtime arg (DRAM addr, Mt/Kt/Nt, work slice). | K · readers/writers · L5 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [get_arg_val](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/kernel_args/get_arg_val.html) |
| `TensorAccessorArgs<N>` | Device-side unpack of host `TensorAccessorArgs` compile blob. | K · L4–L6 readers/writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [Tensor accessor tech report](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tech_reports/tensor_accessor/tensor_accessor.md) |
| `TensorAccessor(args, base_addr)` | Map logical tile index → physical DRAM address. | K · L4–L6 readers/writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_read_page](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_read_page.html) |

### 9.4 Kernel — circular buffers (reader ↔ compute ↔ writer)

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `cb_reserve_back(cb, n)` | Writer side: reserve space for `n` tiles at CB back. | K · readers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [cb_reserve_back](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/cb_reserve_back.html) |
| `cb_push_back(cb, n)` | Mark `n` tiles ready for reader at front (hand off to compute). | K · readers · compute | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [cb_push_back](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/cb_push_back.html) |
| `cb_wait_front(cb, n)` | Wait until `n` tiles available at CB front. | K · compute · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [cb_wait_front](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/cb_wait_front.html) |
| `cb_pop_front(cb, n)` | Consumer frees `n` tiles after use. | K · compute · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [cb_pop_front](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/cb_pop_front.html) |
| `get_write_ptr(cb)` | L1 address to DMA into when filling a CB (reader). | K · readers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [get_write_ptr](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/get_write_ptr.html) |
| `get_read_ptr(cb)` | L1 address to DMA from when draining a CB (writer). | K · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [get_read_ptr](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/get_read_ptr.html) |

### 9.5 Kernel — NoC DRAM transfer (Labs 01–02)

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `noc_async_read_page(tile_idx, accessor, dst)` | Start async DRAM→L1 read of one tile. | K · readers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_read_page](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_read_page.html) |
| `noc_async_read_barrier` | Wait until outstanding reads complete. | K · readers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_read_barrier](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_read_barrier.html) |
| `noc_async_write_page(tile_idx, accessor, src)` | Start async L1→DRAM write of one tile. | K · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_write](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_write.html) |
| `noc_async_write_barrier` | Wait until outstanding writes complete. | K · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_write_barrier](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_write_barrier.html) |
| `noc_async_write_flushed` | Ensure posted writes are visible before reuse. | K · writers | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_posted_writes_flushed](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_posted_writes_flushed.html) |

Example reader/writer sources:

- L4: [reader_single_core_mm.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_single_core/kernels/dataflow/reader_single_core_mm.cpp) · [writer_single_core_mm.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_single_core/kernels/dataflow/writer_single_core_mm.cpp)
- L5: [reader_mm_output_tiles_partitioned.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_multi_core/kernels/dataflow/reader_mm_output_tiles_partitioned.cpp) · [writer_unary_interleaved_start_id.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_multi_core/kernels/dataflow/writer_unary_interleaved_start_id.cpp)

### 9.6 Kernel — compute / FPU (all labs)

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `mm_init(in0, in1, out)` | Configure matrix engine for tile matmul (call once). | K · L4–L6 | [matmul.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/matmul.h) | [matmul_tiles / mm_init](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/compute/matmul_tiles.html) |
| `matmul_tiles(in0, in1, …, idst)` | Multiply one A tile × one B tile; **accumulate** into dest register. | K · L4–L6 | [matmul.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/matmul.h) | [matmul_tiles](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/compute/matmul_tiles.html) |
| `tile_regs_acquire` | Acquire/zero destination register tile before K-loop. | K · L4–L5 | [tile_move_copy.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/tile_move_copy.h) | [acquire_dst](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/compute/acquire_dst.html) |
| `tile_regs_commit` | Signal compute RISC finished writing dest register. | K · L4–L5 | [tile_move_copy.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/tile_move_copy.h) | [matmul_tiles example flow](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `tile_regs_wait` | Pack RISC waits for dest register ready. | K · L4–L5 | [tile_move_copy.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/tile_move_copy.h) | [matmul_tiles example flow](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html) |
| `tile_regs_release` | Release dest register for next output tile. | K · L4–L5 | [tile_move_copy.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/tile_move_copy.h) | [release_dst](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/compute/release_dst.html) |
| `pack_tile(idst, cb_out)` | Move result tile from register file into output CB. | K · L4–L5 | [tile_move_copy.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/compute/tile_move_copy.h) | [pack_tile](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/pack_unpack/pack_tile.html) |

L4 compute reference: [kernels/compute/mm.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_single_core/kernels/compute/mm.cpp)

L6 uses a block variant: [bmm_large_block_zm.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_common/kernels/compute/bmm_large_block_zm.cpp)

### 9.7 Kernel — multicast & semaphores (Labs 02 & 06)

| API | What it does | Where | Source | Docs |
|---|---|---|---|---|
| `noc_async_write_multicast` | Broadcast a tile from sender L1 to many cores over NoC. | K · L2 · L6 senders | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_write_multicast](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_write_multicast.html) |
| `get_noc_multicast_addr` | Build multicast destination address list. | K · L2 · L6 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [get_noc_multicast_addr](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/get_noc_multicast_addr.html) |
| `get_semaphore` | Device-side handle to a host-created semaphore. | K · L2 · L6 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [get_semaphore](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/get_semaphore.html) |
| `noc_semaphore_set` / `noc_semaphore_set_multicast` | Sender signals receivers that data is ready. | K · L2 · L6 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_semaphore_set_multicast](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_semaphore_set_multicast.html) |
| `noc_semaphore_wait` | Receiver blocks until sender's signal arrives. | K · L2 · L6 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_semaphore_wait](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_semaphore_wait.html) |
| `noc_async_writes_flushed` | Ensure multicast writes completed before signaling. | K · L2 · L6 | [dataflow_api.h](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/hw/inc/api/dataflow/dataflow_api.h) | [noc_async_posted_writes_flushed](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/data_movement/noc_async_posted_writes_flushed.html) |

L6 reader variants live under [matmul_common/kernels/dataflow/](https://github.com/tenstorrent/tt-metal/tree/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_common/kernels/dataflow)
(e.g. `reader_bmm_tile_layout_in0_sender_in1_sender.cpp`). Host setup:
[matmul_multicore_reuse_mcast.cpp](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast/matmul_multicore_reuse_mcast.cpp)

### 9.8 Full API index (upstream)

Browse all documented kernel and host APIs:

- [Kernel APIs index](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/kernel_apis.html)
- [Host APIs index](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/host_apis/host_apis.html)
- [tt-metal repo](https://github.com/tenstorrent/tt-metal) · pinned tree: [commit 5a443624](https://github.com/tenstorrent/tt-metal/tree/5a4436244ae1b421504da84c01f81fdfdf6049de)

**Not covered here:** debug APIs (`DPRINT`, `TT_METAL_DEVICE_PROFILER`) — see
[Lab 1 tutorial §Debug / §Profiler](https://github.com/tenstorrent/tt-metal/blob/5a4436244ae1b421504da84c01f81fdfdf6049de/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst)
and [Device Program Profiler](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tools/device_program_profiler.html).
