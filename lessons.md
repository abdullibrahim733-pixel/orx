# Lessons Learned: Bottlenecks in Orx and How We Fixed Them

> A field guide for engineers learning Python and C++ — what went slow, why, and what we did about it.

---

## Table of Contents

- [Lesson 0: The Most Important Lesson](#lesson-0-the-most-important-lesson)
- [Lesson 1: 960 Rays Is Too Many Rays](#lesson-1-960-rays-is-too-many-rays)
- [Lesson 2: Never Call `set_at` 200,000 Times Per Frame](#lesson-2-never-call-set_at-200000-times-per-frame)
- [Lesson 3: The Two-Pass Problem](#lesson-3-the-two-pass-problem)
- [Lesson 4: When Python's Loop Isn't Fast Enough (C++ Time)](#lesson-4-when-pythons-loop-isnt-fast-enough-c-time)
- [Lesson 5: The GIL Is Real](#lesson-5-the-gil-is-real)
- [Lesson 6: Procedural Generation Is Cheap, But Not Free](#lesson-6-procedural-generation-is-cheap-but-not-free)
- [Lesson 7: Start Screen Was Free (and You Should Have One)](#lesson-7-start-screen-was-free-and-you-should-have-one)
- [The Before/After Numbers](#the-beforeafter-numbers)
- [Key Takeaways for a Learning Engineer](#key-takeaways-for-a-learning-engineer)

---

## Lesson 0: The Most Important Lesson

**You cannot optimize what you do not measure.**

Before changing anything, we should have run a profiler. But even without one, we could reason about bottlenecks by understanding *how much work each line of code does*.

A single `screen.set_at(x, y, color)` in Python looks cheap. But when you call it **half a million times per second**, it's the most expensive thing in your program.

Always ask: *"How many times does this line run per frame?"*

---

## Lesson 1: 960 Rays Is Too Many Rays

### The Problem

The original code had:

```python
NUM_RAYS = SCREEN_WIDTH   # 960
```

That means every frame, the game casts **960 individual rays** using the DDA algorithm. Each ray walks along a grid, doing a handful of math operations per step. With `MAX_DEPTH = 20`, a single ray walks roughly 20-40 steps. That's **960 × 30 = ~29,000 DDA steps per frame** — each step involves:

- A comparison (`side_dist_x < side_dist_y`)
- Two additions (`side_dist_x += delta_dist_x`)
- Two integer assignments (`map_x += step_x`)
- A wall lookup (`world.is_wall(map_x, map_y)`)
- If a wall is hit: a division, some multiplies, modulo, and a tuple construction

In Python, a single addition is fast (~10-20 nanoseconds). But wrapped in a Python bytecode loop with function calls, attribute lookups, and list appends, each step costs **microseconds**, not nanoseconds. 29,000 steps × 2μs = **58ms per frame** just for ray casting. At 120 FPS, you only have 8.3ms per frame. We were already over budget before drawing a single pixel.

### Why Was It Like This?

The original code treated every horizontal pixel as a ray column. This makes sense for a hardware-accelerated renderer (Wolfenstein 3D did this), but **not for Python software rendering**. The CPU has to do all the work, and Python adds 50-100× overhead compared to C for the same loop.

### The Fix

```python
NUM_RAYS = 320
STRIP_WIDTH = SCREEN_WIDTH // NUM_RAYS   # = 3
```

We cast **320 rays** instead of 960. Each ray renders a 3-pixel wide column. This cuts the ray-casting work by **3×** with almost no visible difference — at 960px resolution, 3-pixel strips are barely noticeable.

### The Concept: Resolution vs. Performance Tradeoff

In software rendering, every pixel is a cost. There's no GPU to do it for free. So you have to ask: *"Do I really need full horizontal resolution?"*

Classic games like Wolfenstein 3D rendered at **320×200** — not because monitors were bad, but because the CPU couldn't do more. We scaled up to 960×540 but kept the ray resolution at roughly the same horizontal count as a 1992 game. The result? Looks good, runs fast.

### Lesson

**When working in Python, always count how many times your inner loop runs.** If it's in the thousands per frame, ask yourself whether you can reduce it. A 3× reduction on the hottest path often means 3× the frame rate.

---

## Lesson 2: Never Call `set_at` 200,000 Times Per Frame

### The Problem

The original renderer did this for every wall column:

```python
for y in range(draw_start, draw_end + 1):
    tex_y = int(((y - draw_start) / line_height) * tex.get_height()) % tex.get_height()
    pixel_color = tex.get_at((tex_x, tex_y))
    r = int(pixel_color[0] * shade)
    g = int(pixel_color[1] * shade)
    b = int(pixel_color[2] * shade)
    self.screen.set_at((col, y), (r, g, b))
```

Let's do the math:
- 960 columns
- Average wall height: ~270 pixels (half the screen)
- Total: **~259,000 `set_at` calls per frame**
- At 120 FPS: **31 million calls per second**

Each `set_at` call has to:
1. Look up the pygame surface's internal pixel buffer
2. Compute the memory offset for (x, y)
3. Write 3-4 bytes

That sounds fast, and in C it is. But in Python, each call involves:
- A method attribute lookup on the surface object
- Argument tuple packing
- The actual C function call (through the CPython API)
- Return value handling

This overhead turns a ~20ns C operation into a ~500ns Python call. 259,000 × 500ns = **130ms per frame**. That's already 15× over our 8.3ms budget at 120 FPS.

### Why Was It Like This?

The original code was written for clarity: "For each pixel in the wall column, get the texture color, shade it, and set it on the screen." It maps directly to how you think about rendering. But in Python, the most natural code is often the slowest.

### The Fix

Instead of setting pixels one at a time, we do all the pixel work in C:

```python
tex_col = tex.subsurface((tex_x, 0, 1, tex.get_height()))
scaled = pygame.transform.scale(tex_col, (C.STRIP_WIDTH, col_height))
shade_255 = int(shade * 255)
scaled.fill((shade_255, shade_255, shade_255), None, pygame.BLEND_RGB_MULT)
self.screen.blit(scaled, (screen_x, draw_start))
```

What happens here:
1. `subsurface()` — creates a view into the texture (no data copy, just a pointer)
2. `transform.scale()` — stretches the 1px-wide column to the correct wall height and strip width (**entirely in C**)
3. `fill()` with `BLEND_RGB_MULT` — multiplies every pixel by the shade value in one call (**entirely in C**)
4. `blit()` — copies the scaled, shaded strip to the screen (**entirely in C**)

Instead of 259,000 Python calls, we now make **4 C-level calls per column** = 960 × 4 = 3,840 calls. That's a **67× reduction** in Python function calls on the render path.

### The Concept: Batch Work Into C

pygame is a C library with a Python wrapper. Every time you call a pygame function, the Python wrapper does some setup and then calls into C. The expensive part is the **Python-to-C boundary crossing**.

Strategy: **cross the boundary as few times as possible**. One `blit` of a 300-pixel column is 300× cheaper than 300 `set_at` calls, even though they do the same work.

### Lesson

**Look for per-pixel loops in your Python code and eliminate them.** Almost any image operation has a C-level equivalent in pygame. If you find yourself writing `for y in range(...): surface.set_at(...)`, you are doing it wrong. Use `blit`, `transform.scale`, `fill`, or `draw` functions instead.

> Rule of thumb: if your loop iterates more than 1000 times per frame, it should probably be in C.

---

## Lesson 3: The Two-Pass Problem

### The Problem

The original code had a second loop after wall rendering:

```python
if hit.side == 1:
    for y in range(draw_start, draw_end + 1):
        current = self.screen.get_at((col, y))
        darker = (int(current[0] * 0.7), ...)
        self.screen.set_at((col, y), darker)
```

This doubles the per-pixel work for side-facing walls. Every pixel on a side wall gets:
1. Written once during wall rendering  
2. Read back and written again during side-darkening

That's **two Python-to-C crossings per pixel** instead of one.

### The Fix

Fold the side-darkening into the shade calculation:

```python
shade = max(0.15, min(1.0, 1.0 - (perp_dist / C.MAX_DEPTH)))
if hit.side == 1:
    shade *= 0.7    # side walls are 30% darker
```

Now everything is applied in a single `fill()` call. Zero extra passes.

### The Concept: Combine Operations

Every pass over your data costs time. If you can merge two passes into one, you roughly halve the cost of that work.

This applies everywhere in programming:
- Database queries: combine joins instead of N+1 queries
- Image processing: apply all filters in one kernel pass
- Rendering: bake all modifications into a single color/shade value before applying

### Lesson

**Look for opportunities to combine passes.** If you find yourself iterating over the same data twice, ask: "Can I do this in one loop?"

---

## Lesson 4: When Python's Loop Isn't Fast Enough (C++ Time)

### The Problem

Even with 320 rays, the DDA algorithm is still running in Python. Each ray does:

```python
for _ in range(max_steps):
    if side_dist_x < side_dist_y:
        side_dist_x += delta_dist_x
        map_x += step_x
        side = 0
    else:
        side_dist_y += delta_dist_y
        map_y += step_y
        side = 1

    if world.is_wall(map_x, map_y):
        # compute hit
        ...
```

This is 320 rays × ~30 steps = ~9,600 loop iterations per frame, each with:
- Two attribute lookups (`side_dist_x`, `delta_dist_x`)
- Comparisons and branches
- Integer arithmetic
- A method call (`world.is_wall`)
- Floating-point math on hit

Python handles this at roughly **5-10 million operations per second**. On a 3GHz CPU that can do 3 billion things per second, Python wastes 99.7% of the CPU's potential to overhead.

### The Fix (C++ Extension)

The same algorithm in C++:

```cpp
for (int i = 0; i < max_steps; i++) {
    if (side_dist_x < side_dist_y) {
        side_dist_x += delta_dist_x;
        map_x += step_x;
        side = 0;
    } else {
        side_dist_y += delta_dist_y;
        map_y += step_y;
        side = 1;
    }

    if (grid.is_wall(map_x, map_y)) {
        // compute hit
        ...
    }
}
```

Compiled with `-O3 -std=c++17`, this runs at **native CPU speed** — roughly 50-100× faster than the Python equivalent. The C++ function is called once per frame via pybind11, does all the work, and returns a list of results.

### The Concept: When to Drop to C++

Python is great for:
- String manipulation
- Dictionary/object management
- Calling into C libraries
- Orchestrating systems

C++ is necessary when:
- You have tight loops (millions of iterations)
- You need per-pixel or per-element operations
- Memory layout and cache behavior matters
- You're doing heavy math

The hybrid approach gives you the best of both:
- **Python for game logic** (enemy AI, UI, state management, level generation)
- **C++ for hot loops** (ray casting, collision resolution)

### How pybind11 Works

```cpp
PYBIND11_MODULE(orx_cpp, m) {
    m.def("cast_rays", &cast_rays, "...");
    m.def("resolve_collision", &resolve_collision, "...");
}
```

pybind11 generates the glue code that converts Python arguments to C++ types, calls your function, and converts the result back. You write normal C++ and it becomes a normal Python module.

### Lesson

**Python is glue, not a hot-path language.** Write your game logic in Python. Write your inner loops in C++. The boundary between them is the most important architectural decision you'll make.

**When you find yourself optimizing a Python loop** with micro-optimizations (local variable bindings, avoiding attribute lookups, etc.), stop. You're getting 2-3× speedups with 100× effort. Instead, rewrite that loop in C++ for 50-100× with clean code.

---

## Lesson 5: The GIL Is Real

### The Problem

Python has a **Global Interpreter Lock** (GIL). It means only one thread can execute Python bytecode at a time. Even if you had 16 CPU cores, your Python ray-casting loop would only use one.

This isn't a bug — it's a design decision that makes Python's memory model simple and safe. But it means **Python is inherently single-threaded for CPU-bound work**.

### How We Work Around It

The C++ extension does NOT hold the GIL while running `cast_rays`. pybind11 automatically releases the GIL when you call a C++ function (since it's not running Python code). This means:

- The C++ raycaster can use 100% of a CPU core without Python overhead
- If we had multiple threads, they could run in parallel with the C++ code

For now, the dispatch is simple:

```python
if HAS_CPP:
    return orx_cpp.cast_rays(...)  # GIL released, runs at full speed
return cast_rays_py(...)           # GIL held, Python overhead
```

### The Concept: The Boundary Matters

The GIL only protects Python's internal state. When you call into a C extension, the GIL is typically released (unless you're calling Python objects from C). This means:

- **Any C/C++ code that doesn't touch Python objects runs at native speed**
- Multiple C++ threads can run in parallel while Python waits
- The C++ code can process data and return results without Python overhead

### Lesson

**Python's GIL is not a problem if your hot paths are in C/C++.** The GIL only matters for Python-level parallelism. The solution isn't "avoid the GIL" — it's "move CPU-bound work out of Python."

---

## Lesson 6: Procedural Generation Is Cheap, But Not Free

### The Problem

Orx generates all assets at startup: textures, enemy sprites, weapon art, audio samples, the synth-wave music loop, and the dungeon map. If you look at `assets/procedural.py`, you'll see nested loops generating textures pixel by pixel:

```python
for y in range(tex_size):
    for x in range(tex_size):
        base = 110 + random.randint(-20, 20)
        ...
        stone.set_at((x, y), (r, g, b))
```

For 4 textures at 64×64, this is 4 × 4096 = 16,384 `set_at` calls — but only **once at startup**, not per frame. The music loop generates raw PCM audio buffers using NumPy-style array math.

### Why This Isn't a Problem

Asset generation happens once during `Game.__init__()`. The player sees the start screen, so they don't notice a ~200ms initialization delay. The per-frame cost of using these assets is zero — they're pre-generated surfaces and sound buffers that get blitted/played at C speed.

### The Lesson

**Not all Python code needs to be fast.** Code that runs once at startup can be as slow and readable as you want. Code that runs every frame must be fast. Learn to distinguish between:

- **Init-time code** (asset generation, file loading, config parsing) — any speed is fine
- **Per-frame code** (rendering, AI updates, physics) — must be fast, profile this
- **Per-interaction code** (shooting, opening doors, level transitions) — should be fast enough to not lag

This is why we generate 64×64 textures with Python `set_at` (init-time) but render 540-pixel wall columns with C-level `blit` (per-frame).

---

## Lesson 7: Start Screen Was Free (and You Should Have One)

We added a start screen with:

- **Animated cyber grid** — scrolling horizontal lines
- **Pulsing logo glow** — `math.sin()` driven alpha animation  
- **CRT post-processing** — scanlines and vignette overlay

Neither of these affects gameplay performance because:

1. The start screen runs a different render path (`_render_start_screen` vs `_render`)
2. The animation uses `math.sin()` — a C function called twice per frame
3. The grid is just a few `pygame.draw.line` calls
4. The CRT overlays are pre-generated surfaces, just two `blit` calls

The total CPU cost of the start screen is negligible (<0.5ms per frame).

### Lesson

**UI polish is usually cheap.** A pulsing glow, an animated background, a few translucent overlays — these are a handful of `blit` operations. They look like a lot of work, but to the CPU they're nothing compared to ray casting.

If your game feels unpolished, don't assume the fix will cost performance. Try adding it — you might be surprised how cheap it is.

---

## The Before/After Numbers

### Without Optimizations (original code)

| Component | Cost per frame |
|---|---|
| 960 DDA ray casts (Python) | ~58ms |
| 259,000 `set_at` calls | ~130ms |
| Side-darkening second pass | ~50ms (additional) |
| **Total theoretical** | **~238ms (4.2 FPS)** |

### With Optimizations (current code)

| Component | Cost per frame |
|---|---|
| 320 DDA ray casts (Python, or C++) | ~8ms (Python) / ~0.2ms (C++) |
| Wall rendering (subsurface + scale + blit) | ~3ms |
| Side-darkening (baked into shade) | $0 (free) |
| **Total theoretical** | **~11ms (90 FPS Python) / ~3ms (333 FPS C++)** |

> These are approximate estimates. Real-world numbers depend on scene complexity, wall heights, enemy count, etc.

### What Each Optimization Gave Us

| Optimization | Speedup | Difficulty |
|---|---|---|
| Reducing `NUM_RAYS` 960 → 320 | 3× in ray casting | Trivial (change one constant) |
| `set_at` → `subsurface` + `blit` | ~40× in wall rendering | Medium (rewrite render logic) |
| Two-pass → one-pass shading | 2× on side walls | Trivial (move multiply) |
| Python → C++ raycaster | 10-50× in ray casting | Hard (requires C++ + pybind11) |

---

## Key Takeaways for a Learning Engineer

### 1. Count your operations

Before writing any performance-sensitive code, estimate: "How many times will this line run per frame?" If the answer is more than 1,000, think hard about it. If it's more than 10,000, you need a C-level solution.

### 2. The Python-to-C boundary is expensive

Every `pygame.draw.line()`, `surface.get_at()`, `surface.set_at()` call crosses from Python to C. Minimize the number of crossings, not the amount of work. 100 crossings with 100 pixels each is faster than 10,000 crossings with 1 pixel each.

### 3. Batch your work

Instead of:
```python
for pixel in pixels:
    surface.set_at(pixel)
```

Do:
```python
# Pre-process in Python
processed = batch_process(pixels)
# One C call to apply
surface.blit(processed, (0, 0))
```

### 4. Profile before optimizing

The human brain is terrible at guessing where bottlenecks are. Use `cProfile` or `time.perf_counter()` to measure before changing anything. Fix the thing that's actually slow, not the thing you *think* is slow.

### 5. Know your tools' C APIs

pygame is a C library. Read its documentation — you'll find that most pixel operations you'd write as a loop already have a C function. `transform.scale()`, `fill()` with blend modes, `blit()` with source rects — these are your friends.

### 6. C++ is not scary for hot paths

You don't need to write your whole game in C++. You just need to write the 50-100 lines that iterate millions of times per second in C++. pybind11 makes this dead simple — write a function, bind it, call it from Python. Everything else stays in Python.

### 7. The best optimization is doing less work

Before optimizing how something runs, ask: "Does it need to run at all?" Reducing NUM_RAYS by 3× gave us a 3× speedup with zero complexity cost. That's the kind of optimization you want — the one where you delete code, not add it.

### 8. Distinguish init-time from per-frame

Init-time code can be as slow as you want. Per-frame code must be ruthlessly efficient. Make sure you know which is which before optimizing.

---

## Further Reading

- **DDA Ray Casting**: [Lode's Computer Graphics Tutorial](https://lodev.org/cgtutor/raycasting.html)
- **pygame-ce performance**: [pygame-ce docs — Surface](https://pygame-ce.github.io/ref/surface.html)
- **pybind11**: [pybind11 documentation](https://pybind11.readthedocs.io/)
- **Python GIL**: [Real Python — GIL](https://realpython.com/python-gil/)
- **Profiling Python**: [Python docs — profile](https://docs.python.org/3/library/profile.html)

---

*Written while debugging 4 FPS in a ray-casting game engine.*
