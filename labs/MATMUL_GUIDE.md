# Matmul labs — source code & test output guide

This document walks through the **TT-Metalium matmul programming examples**
that Labs 01–03 run on the virtual Wormhole. Read it alongside the per-lab
READMEs. All paths below use `$TT_METAL_HOME` ( `/opt/tt-metal` on the FULL
image).

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
    │  One Tensix core (Lab 01) or many (02/03)│
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

For all three labs, the default matrix sizes in `main()` are:

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

## 3. Lab 01 — single-core matmul

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

## 4. Lab 02 — multi-core matmul (SPMD)

**Directory:** `.../matmul/matmul_multi_core/`

**Run:** `tt-sim run metal_example_matmul_multi_core`

Same matrix sizes (640³) and same verification (409600 elements, PCC > 0.97).

### What changes vs Lab 01

| Aspect | Lab 01 (single core) | Lab 02 (multi core) |
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

The **compute kernel source** is nearly identical to Lab 01; the parallelism
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

## 5. Lab 03 — multicast matmul (data reuse)

**Directory:** `.../matmul/matmul_multicore_reuse_mcast/`

**Run:** `tt-sim run metal_example_matmul_multicore_reuse_mcast`

Same verification pattern (409600, PCC, Test Passed).

### What changes vs Lab 02

Lab 02 is **correct but wasteful**: every core independently reads the same
input tiles from DRAM when they are shared across output tiles.

Lab 03 fixes this with **multicast over the NoC**:

- A **sender** core reads a shared tile from DRAM **once**.
- It **multicasts** the tile to multiple **receiver** cores over the
  network-on-chip.
- **Semaphores** synchronize senders and receivers so nobody reads a tile
  before it has arrived in L1.

Conceptually:

```
Lab 02:  each core ──► DRAM (many redundant reads of the same A/B tiles)

Lab 03:  one sender ──► DRAM once ──► multicast ──► many receivers
```

### What to read

1. Host — multicast grid geometry (which cores are senders vs receivers).
2. Reader kernels — `noc_async_write_multicast` and matching wait calls.
3. Semaphore setup — `CreateSemaphore` and kernel-side wait/signal.

Compare reader kernels between Lab 02 and Lab 03 to see where per-core DRAM
reads were replaced by multicast.

---

## 6. Understanding the test output

When you run any of the three examples successfully, you see something like:

```
Timing — CPU golden: 842.315 ms | Metalium device: 45123.008 ms | device/CPU 53.57x
Output vector of size 409600
Metalium vs Golden -- PCC = 0.981743
Test Passed
```

The lab injects the **Timing** line via `scripts/patch-matmul-timing.py` (applied
at `tt-sim setup` / image build, or manually with `tt-sim patch-timing`).

### `Timing — CPU golden … | Metalium device … | device/CPU …x`

Host-side wall clock using `std::chrono::steady_clock`:

| Part | What is measured |
|---|---|
| **CPU golden** | `golden_matmul()` only — naive triple loop on the host CPU. |
| **Metalium device** | Full device path: DRAM upload, kernel execution on the (simulated) chip, DRAM readback. |
| **device/CPU ratio** | `device_ms / cpu_ms`. **> 1** means the device path took longer on this host. |

**Important:** under **ttsim** (this lab), the ratio is usually **tens to hundreds** —
software emulation of every Tensix core is slow. That does **not** mean Tenstorrent
hardware is slow; on real silicon Metalium is typically **much faster** than this
CPU golden for 640³ matmul. Use timing here to see *relative* changes (e.g. Lab 02
vs Lab 03), not absolute accelerator performance.

On real hardware, use the [device program profiler](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tools/device_program_profiler.html)
for kernel-level timing inside the chip.

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
| **01** | `matmul_single_core/matmul_single_core.cpp` | `kernels/compute/mm.cpp` | `kernels/dataflow/reader_single_core_mm.cpp` | `kernels/dataflow/writer_single_core_mm.cpp` |
| **02** | `matmul_multi_core/matmul_multi_core.cpp` | `kernels/compute/mm.cpp` | `kernels/dataflow/reader_mm_output_tiles_partitioned.cpp` | `kernels/dataflow/writer_unary_interleaved_start_id.cpp` |
| **03** | `matmul_multicore_reuse_mcast/*.cpp` | `kernels/compute/mm.cpp` (variant) | multicast reader(s) | writer(s) |

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

1. Run Lab 01, read this §3 and the host `main()` top to bottom.
2. Open `kernels/compute/mm.cpp` — follow one output tile through the loops.
3. Skim reader and writer for the same example.
4. Run Lab 02 — diff the **host** against Lab 01; find `split_work_to_cores`
   and the per-core runtime-arg loop.
5. Run Lab 03 — diff **reader** kernels against Lab 02; trace one multicast.

For the upstream theory writeups, see the
[TT-Metalium matmul labs](https://github.com/tenstorrent/tt-metal/tree/main/docs/source/tt-metalium/tt_metal/labs/matmul)
on docs.tenstorrent.com.
