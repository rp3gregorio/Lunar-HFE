# Physics and Code for Beginners — A Guide to This Repository

> **Who this is for.** You. Someone who is smart and motivated but has **no
> prior background in coding, numerical methods, or heat-transfer physics**,
> and who wants to understand *this specific project* — not generic
> tutorials — from the ground up.
>
> **How to read it.** Top to bottom, once, slowly. Each section builds on the
> one before. Wherever you see a file path like `lunar/solver.py` or a
> function name like `solve_periodic_equilibrium`, that is a real thing in
> this repository you can open and look at. The guide is the map; the code is
> the territory.
>
> **The one-sentence summary of the whole project:** *We take the only two
> sets of underground temperature measurements ever made on the Moon (from
> Apollo 15 and 17), build a small physics simulator of how heat moves through
> Moon soil, and tune one number in that simulator — the deep thermal
> conductivity `K_d` — until the simulator matches the real measurements at
> each site.*

---

## Table of contents

1. [The big picture: what question does this repo answer, and why care?](#1-the-big-picture)
2. [Physics fundamentals, from scratch](#2-physics-fundamentals-from-scratch)
3. [The numerical method, gently](#3-the-numerical-method-gently)
4. [The Anchor Point Method (the centerpiece)](#4-the-anchor-point-method)
5. [The K_d retrieval and uncertainty analysis](#5-the-kd-retrieval-and-uncertainty-analysis)
6. [Code tour: every file, in plain terms](#6-code-tour)
7. [How to run it yourself](#7-how-to-run-it-yourself)
8. [Glossary](#8-glossary)
9. [A learning roadmap: what to study next](#9-a-learning-roadmap)

---

## 1. The big picture

### 1.1 The scientific question in one breath

How well does the loose, dusty soil on the Moon (called **regolith**) conduct
heat, about a meter below the surface, **at two specific places** — the Apollo
15 and Apollo 17 landing sites? And is that number **the same at both sites**,
or different?

The single number that captures "how well does deep Moon soil conduct heat" is
called **`K_d`** — the *deep thermal conductivity*. This whole repository
exists to measure `K_d` at those two sites and to ask whether they differ.

### 1.2 Why this is hard, and why it matters

Here is the situation:

- The Moon has been mapped from orbit in incredible detail. But orbiters only
  see the **surface**. To know what is happening a meter *down*, you need a
  thermometer *in the ground*.
- Thermometers have been buried in the Moon **exactly twice in history**:
  during Apollo 15 (1971) and Apollo 17 (1972). Astronauts drilled holes and
  dropped temperature probes down them. This was the **Heat-Flow Experiment
  (HFE)**. The instruments radioed back temperatures from 1971 to 1977.
- That 1971–1977 record is therefore *the only direct measurement of
  meter-scale lunar soil conductivity that exists*. Everything else is an
  educated guess extrapolated from surface data.
- Current models (notably the widely used **Hayne et al. 2017** model) apply a
  **single conductivity value to the entire Moon**. This project asks: is one
  global number actually good enough, or do different places genuinely differ?

**Why anyone cares:**

- Future missions want to detect **water ice** trapped below the lunar
  surface. Whether ice is stable (stays frozen) or sublimates away depends on
  the **temperature profile underground**, which depends directly on `K_d`.
- An upcoming terahertz mission (**TSUKIMI**) will try to "see" into the
  regolith from orbit. To interpret what it sees, it needs the underground
  temperature-vs-depth curve `T(z)` as a boundary condition — and that curve
  is set by `K_d`.
- More fundamentally: if "one number for the whole Moon" is wrong, every model
  built on it inherits the error.

### 1.3 The headline result (the answer)

After all the modeling and statistics, this is what the repository finds
(these exact numbers are committed in
`output/kd_retrieval_results.json` and quoted in the paper abstract):

| Site | Retrieved `K_d*` | Units |
|---|---|---|
| Apollo 15 | **4.58** (+1.33 / −0.28) | mW m⁻¹ K⁻¹ |
| Apollo 17 | **8.12** (+0.49 / −0.61) | mW m⁻¹ K⁻¹ |

- The little `*` in `K_d*` means "the best-fit value" (the star is the
  retrieved estimate).
- The units **mW m⁻¹ K⁻¹** are milliwatts per meter per kelvin — a measure of
  conductivity. (Section 2.5 explains what conductivity units mean.) For
  scale, the "one global value" everyone used before is `K_d = 3.4` in the
  same units, and window glass is ~1000, and copper is ~400,000,000. Lunar
  regolith is an *extraordinary* insulator.
- The **inter-site contrast** (the difference, A17 − A15) is **≈ 3.3** mW m⁻¹
  K⁻¹, with a 95% confidence interval of roughly [0.4, 4.6] that **excludes
  zero** (p ≈ 0.01). In plain terms: the two sites really do appear to differ
  — Apollo 17 soil conducts heat noticeably better than Apollo 15 soil
  — by roughly a factor of 1.8.

That factor-of-1.8 difference, established from the only underground data that
exist, is the scientific contribution. The rest of this guide explains *how*
the repository gets there.

---

## 2. Physics fundamentals, from scratch

This section assumes you know nothing about heat physics. Take it slowly.

> **Full symbol tables and TikZ figures** (Sun–Moon geometry, insolation curve,
> surface energy-balance diagram) are in the PDF handbook:
> `docs/teaching/beginners_guide.pdf` — Section *Notation reference* and
> *Orbital mechanics and the top boundary*.

### 2.0 Notation reference — every symbol in this project

Keep this table open while reading the physics sections or the code. Symbols are
grouped by topic; units are SI unless noted.

#### Coordinates, time, and indexing

| Symbol | Meaning | Units | Code / paper |
|--------|---------|-------|--------------|
| `z` | Depth, positive **downward** from surface | m | `grid.z_mid`; paper `z=0` at surface |
| `t` | Time within one lunation | s | `PixelInputs.t`; hourly steps in production |
| `T(z,t)` | Temperature at depth `z`, time `t` | K | `PixelOutputs.T[i,k]` |
| `T_s(t)` | **Skin** (surface) temperature | K | `PixelOutputs.T_surface`; Newton each step |
| `⟨T⟩(z)` | Cycle-**mean** temperature at depth `z` | K | `EquilibriumResult.T_mean` |
| `∂T/∂t` | Rate of temperature change | K/s | `(T^{n+1}-T^n)/Δt` in the solver |
| `∂T/∂z` | Temperature gradient with depth | K/m | `np.gradient`, Fourier flux |
| `i`, `k` | Depth index, time index | — | cell `i`, timestep `k` |

#### Heat, flux, and energy

| Symbol | Meaning | Units | Code / typical value |
|--------|---------|-------|----------------------|
| `q` | **Heat flux** — power per area crossing a horizontal plane | W/m² | Fourier: `q = −K · ∂T/∂z` |
| `Q_b` | **Basal / geothermal flux** from lunar interior at column bottom | W/m² | A15 `0.021`, A17 `0.015` (`Q_BASAL`) |
| `u_rect` | **Rectified flux** — extra cycle-mean flux in diurnal skin | W/m² | `_rectified_flux` in `equilibrium.py` |
| `ρ` | Bulk density | kg/m³ | `density_hayne` |
| `c_p` | Specific heat | J/(kg·K) | `specific_heat` |
| `ρ c_p` | Volumetric heat capacity | J/(m³·K) | product `cap` in `_step` |

#### Thermal conductivity (Hayne 2017 model)

| Symbol | Meaning | Units | Typical / retrieved |
|--------|---------|-------|---------------------|
| `K(T,z)` | Total effective conductivity | W/(m·K) | `conductivity_hayne` |
| `K_c(z)` | Structural (contact) part of `K` | W/(m·K) | rises from `K_s` to `K_d` with depth |
| `K_s` | Surface contact conductivity | W/(m·K) | `7.4×10⁻⁴` |
| **`K_d`** | **Deep conductivity — the retrieved parameter** | W/(m·K) | A15 **4.58**, A17 **8.12** mW/m/K |
| `H` | Compaction scale height for `K_c(z)` and `ρ(z)` | m | ~0.06 |
| `χ` | Radiative conductivity coefficient | — | 2.7 |
| `T_ref` | Reference temperature in radiative term | K | 350 |
| `ρ_s`, `ρ_d` | Surface / deep bulk density | kg/m³ | ~1100 / ~1800 |

#### Surface radiation, albedo, and orbital forcing

| Symbol | Meaning | Units | Typical / code |
|--------|---------|-------|----------------|
| `S_0` | Solar constant at 1 AU | W/m² | 1361 (`S0` in `config.py`) |
| `F_⊙(t)`, `S(t)` | **Insolation** on local horizontal surface | W/m² | `insolation` in `run_with` |
| `θ_⊙(t)` | **Solar zenith angle** — angle from vertical to Sun | rad or ° | idealised cosine model |
| `φ` | Site **latitude** (north positive) | ° | A15 26.13°N, A17 20.19°N |
| `P` | Mean **synodic lunation** | s | `2_551_443` (`T_LUNAR`) |
| `A` | **Bond albedo** — fraction of sunlight reflected | — | ~0.13 per site |
| `(1−A)` | Fraction of sunlight **absorbed** | — | ~0.87 |
| `ε` | **Emissivity** — thermal radiation efficiency | — | 0.95 |
| `σ` | Stefan–Boltzmann constant | W/(m²·K⁴) | `5.6704×10⁻⁸` |
| `ε σ T_s⁴` | Outgoing infrared flux | W/m² | top boundary balance |

#### Boundary conditions and problem setup

| Item | Meaning | Where |
|------|---------|-------|
| Interior PDE | `ρ c_p ∂T/∂t = ∂/∂z(K ∂T/∂z)` | all interior cells |
| **Top BC** | `(1−A) F_⊙ = ε σ T_s⁴ + q_cond` | `surface_energy_balance_residual` |
| **Bottom BC** | `−K ∂T/∂z = Q_b` at `z = z_max` | `d[-1] += dt*Q_b/cap[-1]` |
| `z_max` | Bottom of model column | 5 m |
| `z_anchor` | Anchor depth for equilibrium method | 0.55 m |

#### Skin depth and diffusivity

| Symbol | Meaning | Formula |
|--------|---------|---------|
| `α` | Thermal diffusivity | `α = K/(ρ c_p)` |
| `ω` | Angular frequency of diurnal forcing | `ω = 2π/P` |
| `δ` | **Thermal skin depth** | `δ = √(2α/ω)` — few cm |

#### Numerical discretisation

| Symbol | Meaning | Production value |
|--------|---------|------------------|
| `Δz_i` | Layer thickness (geometric grid) | 2 mm at top, ~8% growth/layer |
| `Δt` | Timestep | 1 h |
| `N_z` | Number of depth cells | ~69 for 5 m |
| `N_t` | Timesteps per lunation | 709 |

#### Retrieval and statistics

| Symbol | Meaning | Where |
|--------|---------|-------|
| `K_d*` | Retrieved deep conductivity minimising RMSE | `kd_retrieval_results.json` |
| `T_eq,i` | Equilibrium temperature at sensor `i` | `extract_sensor_stability` |
| `R_i` | Residual `T_model − T_eq` | `run_kd_sweep_extended` |
| RMSE | Root mean square error of residuals | `kd_star_from_residuals` |

**Sign conventions:** Depth `z` increases **downward**. Heat flux `q` is positive
when flowing **downward** (`q = −K ∂T/∂z`). Basal flux `Q_b` is positive when
flowing **upward** from the interior. Temperatures are always in **kelvin (K)** in
the solver.

---

### 2.1 Heat vs. temperature (they are not the same thing)

- **Temperature** is *how hot something is* — a single number at a point, like
  300 kelvin. It tells you the average jiggling energy of the atoms there.
- **Heat** is *energy in transit* — energy flowing from a hotter place to a
  colder place. You measure it as a *rate of flow*.

Analogy: temperature is like the **water level** in a tank; heat is like the
**water flowing** between tanks. Two tanks at the same level (same
temperature) have no flow between them, even if one is huge and one is tiny.

**Kelvin (K)** is just the temperature scale scientists use. It starts at
absolute zero (the coldest possible), so there are no negative numbers.
0 °C = 273.15 K. Lunar daytime soil-surface can hit ~390 K (scorching);
lunar night can fall below 100 K (−170 °C). A meter down, it settles to a
near-constant ~250 K.

### 2.2 Conduction: how heat moves through a solid

There are three ways heat travels: **conduction** (through direct contact,
atom bumping atom), **convection** (carried by a moving fluid like air or
water), and **radiation** (electromagnetic waves, like sunlight or the warmth
you feel from a fire).

The Moon has **no air and no water underground**, so inside the regolith
column there is essentially only **conduction** (plus a small radiative effect
across the tiny gaps between dust grains, which we fold into an "effective"
conductivity — see 2.5). This is why the model is "1-D conduction."

The basic law of conduction (**Fourier's law**) says, in words:

> Heat flows from hot to cold, and the *rate* of flow is proportional to how
> steep the temperature change is, times how good a conductor the material is.

As a tiny equation:

```
heat flux  =  −K · (dT/dz)
```

- `dT/dz` is the **temperature gradient**: how fast temperature changes as you
  go down (`z` is depth). Steep gradient → fast flow.
- `K` is the **thermal conductivity**: the material property — high `K` means
  heat flows easily (metal), low `K` means it resists (styrofoam, lunar dust).
- The minus sign just means heat flows *down* the gradient, from hot to cold.

In this repo Fourier's law literally appears as the conductive term in the
surface energy balance and in every interior step. See
`surface_energy_balance_residual` in `lunar/solver.py`.

### 2.3 The 1-D heat equation — full derivation from scratch

This section answers three questions in order:

1. **What problem is the code actually solving?**
2. **Where does the differential equation come from?** (step by step, no prior PDE
   course assumed)
3. **What do the top and bottom boundaries mean?**

The final equation is the one in `lunar/solver.py` and in the paper (Eq. 1). By
the end you should be able to read it as a physical sentence, not as scary
calculus.

---

#### 2.3.1 The problem in one sentence

> **Given** how sunlight hits the lunar surface hour by hour, and **given** how
> the soil conducts heat at each depth, **find** the temperature `T` at every
> depth `z` and every time `t`.

That is it. The simulator does not predict the weather on Earth or model ice
directly. It predicts a **temperature profile through the soil column** —
a list of temperatures from the surface down to 5 m — and updates that profile
as the lunar day/night cycle rolls on.

In code, the answer lives in `PixelOutputs.T` from `solve_pixel` in
`lunar/solver.py`: a 2-D array of shape `(N_z, N_t)` — temperature at each grid
cell and each timestep.

---

#### 2.3.2 Picture a thin horizontal slice of soil

Imagine the regolith as a **stack of thin horizontal pancakes**, each pancake a
soil layer between depth `z` and depth `z + Δz` (Δz = "a small step downward").

Focus on **one pancake** in the middle of the stack:

```
     surface (z = 0)  ← sunlight, radiation to space
  ─────────────────────────────────────────
        warmer layer
  ─────────────────────────────────────────   ← top face of our slice (depth z)
        OUR SLICE  (thickness Δz)
  ─────────────────────────────────────────   ← bottom face (depth z + Δz)
        cooler layer
  ─────────────────────────────────────────
        ...
  ─────────────────────────────────────────
     bottom (z = 5 m)  ← steady heat from Moon's interior
```

We track a **column** of soil 1 m × 1 m in footprint (one "pixel" on the
Moon). Everything below is about **energy** entering and leaving that one
pancake.

**How much "thermal mass" does the slice have?**

- Mass in the slice ≈ `ρ · Δz` (kg per m² of surface), where `ρ` is density.
- To raise the slice's temperature by 1 K, you need energy `ρ · c_p · Δz`
  (joules per m²), where `c_p` is specific heat.

So `ρ · c_p` is the soil's **thermal inertia**: dense, high-`c_p` soil is hard
to warm up or cool down (like a heavy cast-iron pan).

---

#### 2.3.3 Heat flux: how much energy crosses each face

**Heat flux** `q` (units: W/m² = joules per second per square meter) is the
rate at which thermal energy crosses a horizontal plane — like measuring how
many "energy dollars" per second flow through a toll gate at depth `z`.

**Fourier's law** (already in Section 2.2) says the flux is driven by how
steeply temperature changes with depth:

```
q(z)  =  −K(T,z) · ∂T/∂z
```

Read the signs carefully:

- Heat flows **from hot toward cold** (down the temperature hill).
- `∂T/∂z` means "how fast `T` changes as you go **down**" (positive if it
  gets warmer with depth).
- The minus sign makes `q` positive when heat flows **downward** into deeper,
  cooler soil (the usual daytime situation near the surface).

`K` can depend on **both** depth and temperature in this repo (`K(T,z)` from
`conductivity_hayne`).

For our slice between `z` and `z + Δz`:

- `q_in`  = flux crossing the **top** face (into the slice from above)
- `q_out` = flux crossing the **bottom** face (out of the slice downward)

---

#### 2.3.4 Energy conservation: the bookkeeping step

Physics has one non-negotiable rule: **energy is not created or destroyed** in
the slice (we ignore nuclear reactions in regolith!). So:

```
(rate energy piles up in slice)  =  (flux in) − (flux out)
```

**Left-hand side — warming the slice**

If the slice's temperature changes at rate `∂T/∂t` (K per second), the stored
energy per m² changes at rate:

```
ρ · c_p · Δz · (∂T/∂t)
```

**Right-hand side — net heat through the faces**

If `q_in` and `q_out` differ, the difference is the net power (watts per m²)
deposited in the slice:

```
q_in − q_out
```

Set them equal:

```
ρ · c_p · Δz · (∂T/∂t)  =  q_in − q_out
```

---

#### 2.3.5 From two faces to a derivative (the leap to "d/dz")

When the slice is **thin**, the change in flux across it is approximately:

```
q_out − q_in  ≈  (∂q/∂z) · Δz
```

The symbol `∂q/∂z` just means: *"how fast the heat flux changes as you move
downward."* You meet the same idea in everyday language: if the temperature
drops quickly with depth, flux changes quickly with depth.

So:

```
q_in − q_out  ≈  −(∂q/∂z) · Δz
```

Substitute into the balance:

```
ρ · c_p · Δz · (∂T/∂t)  =  −(∂q/∂z) · Δz
```

Cancel `Δz` (the slice thickness cancels — the physics does not depend on how
thin you imagined the pancake):

```
ρ · c_p · (∂T/∂t)  =  −(∂q/∂z)
```

Now plug in Fourier's law `q = −K · ∂T/∂z`:

```
−(∂q/∂z)  =  −(∂/∂z)[ −K · (∂T/∂z) ]
           =  +(∂/∂z)[ K · (∂T/∂z) ]
```

So the **1-D heat equation** is:

```
ρ(z) · c_p(T) · (∂T/∂t)  =  (∂/∂z)[ K(T,z) · (∂T/∂z) ]
```

That is exactly what `lunar/solver.py` solves (and paper Eq. 1).

**Why is it called a "partial differential equation" (PDE)?**

Because `T` depends on **two** independent variables — depth `z` *and* time
`t` — and the equation contains **partial** derivatives (`∂T/∂t` and `∂T/∂z`).
You do not need a full PDE course: treat `∂T/∂t` as "how fast temperature at
this depth is changing right now" and `∂T/∂z` as "how steep the temperature
profile is at this instant."

**Discrete intuition (what the computer actually does).**

Before calculus, the same idea on a **finite** grid is:

```
(ρ c_p)ᵢ · (Tᵢⁿ⁺¹ − Tᵢⁿ) / Δt
    =  (flux into cell i from above) − (flux out below)
```

where `i` indexes depth cells and `n` indexes time steps. Crank–Nicolson
(Section 3.3) is a clever way to rearrange this balance so the timestep can be
one hour without the simulation blowing up. The comment inside `_step` in
`solver.py` states it plainly:

```
cap_i · dT_i/dt = flux_right(i) − flux_left(i)
```

---

#### 2.3.6 Reading the final equation, term by term

```
ρ(z) · c_p(T) · ∂T/∂t  =  ∂/∂z [ K(T,z) · ∂T/∂z ]
```

| Piece | Plain English | Code |
|-------|---------------|------|
| `T(z,t)` | Temperature at depth `z`, time `t` | `PixelOutputs.T[i, k]` |
| `∂T/∂t` | How fast this depth is warming/cooling | finite difference over `Δt` |
| `ρ(z)` | Soil density (kg/m³) | `rho_func` / `density_hayne` |
| `c_p(T)` | Energy to warm 1 kg by 1 K | `cp_func` / `specific_heat` |
| `ρ c_p` | Thermal inertia of the soil | product in `_step` as `cap` |
| `K(T,z)` | Conductivity (W/m/K) | `K_func` / `conductivity_hayne` |
| `K ∂T/∂z` | Heat flux (Fourier) | face fluxes in `_step` |
| `∂/∂z[…]` | Net flux divergence — more in than out warms the cell | difference of face fluxes |

**Left side** = storage: "how fast this cell's temperature must change given the
energy it is gaining or losing."

**Right side** = conduction: "net heat conducted into this cell from its
neighbours above and below."

When `K` varies with `z` or `T`, it must stay **inside** the `∂/∂z` derivative.
Physically, if conductivity changes with depth, the *same* temperature gradient
can carry a different flux at different depths.

---

#### 2.3.7 The two boundaries — what pins the solution (summary)

The PDE alone is not enough — it needs **boundary conditions** at `z = 0` and
`z = z_max` to close the problem. In brief:

- **Top:** radiative surface balance `(1−A)S − εσT_s⁴ − q_cond(0) = 0`
- **Bottom:** fixed geothermal flux `−K ∂T/∂z = Q_b`

**Section 2.8** derives both from scratch and explains exactly how they connect
to the PDE and code. **Section 2.9** adds orbital mechanics (where insolation
comes from) with diagrams for the top boundary.
to the interior heat equation and to the code in `lunar/solver.py`.


#### 2.3.8 What "solving" means in this repository

Putting it all together, the simulator solves this **initial-boundary-value
problem**:

1. **PDE** (every interior cell, every timestep):
   `ρ c_p ∂T/∂t = ∂/∂z(K ∂T/∂z)`
2. **Top BC** (each timestep): radiative balance for `T_s`
3. **Bottom BC** (always): fixed geothermal flux `Q_b`
4. **Initial condition**: a starting temperature profile `T(z, t=0)` — the
   equilibrium driver (`lunar/equilibrium.py`) iterates until this guess no
   longer matters (Anchor Point Method, Section 4).

**One timestep in `solve_pixel`:**

1. Evaluate `K`, `ρ`, `c_p` at each cell from the current temperatures.
2. Assemble the discrete heat balance (Crank–Nicolson).
3. Solve for the new surface temperature (Newton).
4. Solve the tridiagonal linear system (`_thomas`) for all interior
   temperatures.
5. Advance the clock by `Δt` (1 hour in production).

Repeat for every hour in a lunation (~709 steps), repeat for several lunations
until the diurnal cycle repeats — then you have `T(z,t)`.

**What you do *not* need to derive yourself:** the Crank–Nicolson algebra and
the Thomas algorithm (Section 3). The physics core is Sections 2.3.1–2.3.7:
*energy conservation + Fourier conduction + surface/bottom BCs*.

---

#### 2.3.9 Quick sanity checks (does the equation make sense?)

- **Uniform temperature, constant `K`:** `∂T/∂z = 0` → no flux → right side
  zero → `∂T/∂t = 0` → profile stays flat. Good.
- **Steady state with bottom heat `Q_b`:** time derivatives zero → flux constant
  with depth → `d⟨T⟩/dz = Q_b / K` — the geothermal gradient (Section 2.6).
- **High conductivity `K`:** same gradient carries more flux → shallower
  diurnal swings at depth (larger skin depth).

These are exactly the behaviours the code exhibits when you run it.

### 2.4 The three soil properties — what they mean and why the heat equation needs them

The heat equation (Section 2.3) has three material functions on the right-hand
side: `K(T,z)`, `ρ(z)`, and `c_p(T)`. Here is what each one **physically is**,
why it enters the equation, and where it lives in code.

#### 2.4.1 Thermal capacity: why `ρ · c_p` sits on the left

When you warm soil, you are storing **internal energy** in it. For a slice of
thickness `Δz` and footprint 1 m²:

```
mass in slice  =  ρ · Δz        (kg per m²)
energy to warm by 1 K  =  ρ · c_p · Δz   (joules per m²)
```

So `ρ · c_p` is **volumetric heat capacity** (J m⁻³ K⁻¹): how much energy
per cubic metre is needed to raise temperature by 1 K.

Dividing the energy-balance rate (watts per m²) by this capacity gives the
warming rate:

```
(ρ c_p) · (∂T/∂t)  =  (net heat flux divergence)
```

That is exactly why `ρ` and `c_p` multiply on the **left** of the heat
equation — they convert "energy piling up" into "temperature rising."

| Symbol | Name | Units | Physical meaning | Code |
|--------|------|-------|------------------|------|
| `ρ(z)` | Density | kg/m³ | How compact the soil is | `density_hayne` |
| `c_p(T)` | Specific heat | J kg⁻¹ K⁻¹ | Energy to warm 1 kg by 1 K | `specific_heat` |
| `ρ c_p` | Volumetric heat capacity | J m⁻³ K⁻¹ | Thermal inertia per volume | product in `_step` as `cap` |
| `K(T,z)` | Conductivity | W m⁻¹ K⁻¹ | How easily heat flows | `conductivity_hayne` |

**Analogy:** `ρ c_p` is like the **thermal mass** of the soil (how hard it is
to change temperature). `K` is like the **thermal conductance** (how easily
heat travels through). A thick cast-iron pan has high `ρ c_p` (slow to warm);
a copper rod has high `K` (heat shoots through).

All three are evaluated at every grid cell on every timestep from
`lunar/properties.py`, using constants in `lunar/constants.py`.

### 2.5 Thermal conductivity `K(T,z)` — full physical picture

`K_d` — the quantity this whole project retrieves — lives inside the
conductivity formula. This section explains **where the formula comes from** and
**what each term means physically**.

#### 2.5.1 Two ways heat crosses lunar soil (in vacuum)

On Earth, heat in soil moves mostly by **solid-to-solid contact** (atoms
vibrating and passing energy to neighbours). On the Moon there is **no air** in
the pores, so a second channel opens up:

1. **Contact (solid) conduction** — heat hops grain-to-grain where grains touch.
   Fluffy, loosely packed regolith has few contact points → very low contact
   conductivity. This is why lunar surface soil is a better insulator than
   styrofoam.

2. **Radiative conduction across vacuum gaps** — where grains *don't* touch,
   infrared photons can still carry energy across the gap. Hotter gaps radiate
   more strongly. This adds an effective conductivity that grows with
   temperature.

The Hayne model splits these two ideas explicitly:

```
K(T,z)  =  K_c(z)  ×  (1 + radiative boost in T)
          ────────     ─────────────────────────
          structural   gap-radiation term
```

#### 2.5.2 The structural part `K_c(z)` — compaction with depth

As you go deeper, overlying soil weight **compacts** the regolith: more grains
touch, fewer big pores, better heat paths. Hayne parameterises this with a
smooth exponential transition from a low surface value `K_s` to a deep
asymptote `K_d`:

```
K_c(z) = K_d − (K_d − K_s) · exp(−z / H)
```

Read it term by term:

| Term | At the surface (`z = 0`) | Deep down (`z → ∞`) | Meaning |
|------|--------------------------|---------------------|---------|
| `K_s` | `K_c = K_s` | — | Fluffy-surface contact conductivity (~0.74 mW/m/K) |
| `K_d` | — | `K_c → K_d` | Compact-deep conductivity (**the unknown we fit**) |
| `H` | — | — | Scale height (~6 cm): depth where ~63% of the rise happens |
| `exp(−z/H)` | 1 at surface | → 0 deep | Smooth compaction curve |

**Why an exponential?** It is the same mathematical shape used for density
compaction (Section 2.5.4) and is a standard empirical choice: one parameter
`H` controls how fast the soil "settles" from fluffy to compact. At `z = H`
the conductivity has moved about `(1 − 1/e) ≈ 63%` of the way from `K_s` to
`K_d`.

In code: `conductivity_hayne` in `lunar/properties.py`, paper Eq. 4.

#### 2.5.3 The radiative boost `(1 + χ · (T/350)³)` — why temperature cubed?

Across a narrow vacuum gap between two surfaces at temperatures `T₁` and `T₂`,
the net radiative heat flux is approximately proportional to `T₁⁴ − T₂⁴`. When
the gap is small and the temperature difference `ΔT` is modest compared to the
mean temperature `T`, you can expand:

```
T₁⁴ − T₂⁴  ≈  4 T³ · ΔT     (for small ΔT)
```

So radiative transport across a gap acts like an **extra conductivity**
proportional to `T³` — hotter soil radiates across gaps much more efficiently.

Hayne folds this into a dimensionless multiplier on the contact conductivity:

```
radiative factor  =  1 + χ · (T / T_ref)³     with  T_ref = 350 K,  χ ≈ 2.7
```

- At cold temperatures the factor is ~1 (contact dominates).
- At `T ≈ 250 K` the factor is ~2 (radiation roughly **doubles** effective `K`).
- The `T³` is **not optional** — omitting it is a known bug that breaks the
  surface energy balance.

**Analogy:** imagine heat travelling through a pile of marbles. Contact
conduction is energy passed where marbles touch. Radiative conduction is
infrared light jumping the tiny airless gaps between marbles — and a hotter
gap glows brighter.

#### 2.5.4 Density `ρ(z)` — the same compaction story

Density follows the **identical exponential form** (Hayne Eq. 5,
`density_hayne`):

```
ρ(z) = ρ_d − (ρ_d − ρ_s) · exp(−z / H)
```

| | Surface | Deep |
|---|---------|------|
| `ρ_s` | ~1100 kg/m³ (fluffy) | — |
| `ρ_d` | — | ~1800 kg/m³ (compact) |

Same `H` ties density and conductivity compaction to the same physical process:
gravitational packing with depth.

#### 2.5.5 Specific heat `c_p(T)` — how hard it is to warm a kilogram

`c_p` is the energy needed to raise **1 kg** of soil by 1 K. For real
regolith it varies with temperature. The default model is a 4th-order
polynomial from Hayne (2017) Appendix A (`specific_heat`, model `'hayne'`):

```
c_p(T) = c₀ + c₁T + c₂T² + c₃T³ + c₄T⁴
```

Coefficients live in `lunar/constants.py` (`CP_HAYNE_C0` … `CP_HAYNE_C4`). At
lunar temperatures (~200–300 K) `c_p` is a few hundred J kg⁻¹ K⁻¹ and changes
slowly — it matters for the **timescale** of heating (how fast the skin
responds) but is not the free parameter of the retrieval.

#### 2.5.6 What the retrieval actually varies

The retrieval holds `K_s`, `H`, `χ`, `ρ_s`, `ρ_d`, and the `c_p` polynomial
**fixed** at published values. It slides only **`K_d`** — the deep plateau of
the structural conductivity — until model temperatures match Apollo data.

```46:55:lunar/constants.py
#: Surface contact conductivity [W m^-1 K^-1] — Hayne et al. (2017) Table 2.
K_SURFACE: float = 7.4e-4

#: Deep contact conductivity [W m^-1 K^-1] — Hayne et al. (2017) Table 2.
#: NOTE: earlier versions of heat1d had an incorrect value here. The correct
#: published value is 3.4e-3.
K_DEEP: float = 3.4e-3

#: Radiative conductivity coefficient chi [dimensionless] — Hayne et al. (2017).
CHI_RADIATIVE: float = 2.7
```

> **Units note.** Conductivity is in **W m⁻¹ K⁻¹** (watts per meter per
> kelvin). `3.4e-3` W m⁻¹ K⁻¹ = `3.4` mW m⁻¹ K⁻¹ — the paper quotes
> milliwatts (mW) because the numbers are tiny. 1 W = 1000 mW. So the
> committed `K_d* = 4.58e-3` in the JSON prints as `4.58` mW m⁻¹ K⁻¹.

### 2.6 The thermal skin and skin depth — full derivation

#### 2.6.1 The physical picture

Shine a daily heat wave on the surface (hot lunar noon, cold lunar midnight)
and it penetrates downward — but it **fades with depth**, like how a loud sound
outside is muffled inside a thick wall.

- For the Moon's daily cycle, the **skin depth** `δ` is only a few centimetres.
- Below ~1 m, the daily swing is essentially **gone**.
- Apollo sensors below ~80 cm sit **below the noisy skin** — exactly why they
  are useful for measuring `K_d`.

See `scripts/analysis/phase2_depth_convergence.py` and `analytical_thermal_wave`
in `lunar/solver.py`.

#### 2.6.2 Thermal diffusivity — how fast disturbances spread

```
α  =  K / (ρ · c_p)        [units: m²/s]
```

**Thermal diffusivity `α`** measures how quickly a temperature disturbance
diffuses. High `α` (metal) → fast spreading. Low `α` (fluffy regolith) → slow.

Dividing the heat equation by `ρ c_p` (when properties are constant):

```
∂T/∂t  =  α · ∂²T/∂z²
```

This is a **diffusion equation** — the same mathematics as heat in a rod or dye
in water.

#### 2.6.3 The decaying thermal wave

If the surface oscillates sinusoidally with frequency `ω`:

```
T(0, t)  =  T_mean  +  A_s · cos(ωt)
```

The classic solution is a wave that decays with depth:

```
T(z, t)  =  T_mean  +  A_s · exp(−z / δ) · cos(ωt − z / δ)
```

At `z = δ` the amplitude is `A_s / e ≈ 0.37 A_s`. At `z = 3δ` it is ~5% of
the surface swing — essentially gone.

#### 2.6.4 Deriving `δ = √(2α / ω)`

Substituting the wave into `∂T/∂t = α ∂²T/∂z²` and matching decay rates:

```
δ  =  √( 2α / ω )
```

| Factor | Effect | Intuition |
|--------|--------|-----------|
| Larger `α` | Deeper `δ` | Heat penetrates farther per cycle |
| Larger `ω` | Shallower `δ` | Faster forcing → less time to diffuse down |

**Moon example:** `K ~ 0.005`, `ρ ~ 1500`, `c_p ~ 700` → `α ~ 5×10⁻⁷` m²/s.
With `ω ~ 2.5×10⁻⁷` rad/s → `δ ~ 6` cm. Matches simulations.

#### 2.6.5 Why sensors must sit below the skin

Apollo sensors (0.8–2.4 m) are **10–40× deeper** than `δ`. There the diurnal
oscillation is negligible and temperature is the **cycle mean** `⟨T⟩`, set by
the geothermal gradient (Section 2.7.4). This separation underpins both
`MIN_DEPTH_CM = 80` and the Anchor Point Method (Section 4).

### 2.7 Radiation, sunlight, and the geothermal gradient — full picture

Section 2.3.7 introduced the boundary conditions in brief. Here we build each
one from physical first principles. (They pin the top and bottom of the soil
column.)

#### 2.7.1 Stefan–Boltzmann radiation — why `T⁴`?

Every object at temperature `T` (in kelvin) emits electromagnetic radiation. For
a real surface that is not a perfect emitter, the outgoing radiative flux is:

```
q_rad  =  ε · σ · T⁴
```

| Symbol | Meaning | Typical value here |
|--------|---------|-------------------|
| `ε` | Emissivity — how efficiently the surface radiates (0–1) | ~0.95 |
| `σ` | Stefan–Boltzmann constant | 5.67×10⁻⁸ W m⁻² K⁻⁴ |
| `T` | Surface temperature | 100–400 K on the Moon |

**Why the fourth power?** It comes from thermodynamics and quantum statistics
(blackbody radiation). For this guide, the key intuition is:

> **A slightly hotter surface radiates vastly more energy** — double the
> temperature (in kelvin) and the radiated power goes up by 2⁴ = 16×.

That steep `T⁴` curve is why lunar noon is so violent (surface radiates hard
to balance intense sunlight) and why the surface equation cannot be solved
with simple algebra — we need Newton iteration (Section 3.5).

#### 2.7.2 The surface energy balance — deriving the top boundary

On the airless Moon there is no air to convect heat away. At the surface skin,
energy balance at each instant says:

```
(power in from Sun)  =  (power out to space)  +  (power conducted into soil)
```

In symbols (paper Eq. 2):

```
(1 − A) · S(t)  −  ε · σ · T_s⁴  −  q_cond(0)  =  0
```

| Term | Meaning | Code |
|------|---------|------|
| `(1−A)·S(t)` | Absorbed sunlight | `(1-albedo)*insolation` |
| `ε·σ·T_s⁴` | Emitted infrared | `emissivity*SIGMA_SB*T_s**4` |
| `q_cond(0)` | Conduction into first soil cell | `K*(T_s - T_sub)/dz` |

`A` (**albedo**) ≈ 0.13 → ~87% of sunlight is absorbed, ~13% reflected.

The code packs this into `surface_energy_balance_residual` in
`lunar/solver.py` — it returns zero when the balance is satisfied. Each
timestep, `_solve_surface_newton` finds the `T_s` that makes the residual zero.

#### 2.7.3 The insolation model — where `S(t)` comes from

The Sun's heating over one lunar day is approximated by a **cosine**:

```
S(t)  =  S₀ · cos(lat) · max(0, cos(2πt / T_lunation))
```

| Piece | Meaning |
|-------|---------|
| `S₀` | Solar constant at 1 AU (~1361 W/m²) |
| `cos(lat)` | Less sunlight at higher latitude |
| `cos(2πt / T)` | Bright at local noon (`t=0`), zero at night |
| `max(0, …)` | No negative sunlight — night means `S = 0` |

Built in `run_with` (`scripts/pipeline/retrieve_kd.py`):

```python
insol = S0 * cos_lat * np.maximum(0.0, np.cos(phase))
```

This is an **idealisation** — it ignores lunar libration, orbital eccentricity,
and terrain slope. The paper bounds those neglected terms; they are small
compared to the conductivity uncertainty.

#### 2.7.4 The geothermal gradient — deriving `d⟨T⟩/dz = Q_b / K`

**Bottom boundary (paper Eq. 3):** a fixed upward heat flux from the lunar
interior:

```
−K · (∂T/∂z)|_{bottom}  =  Q_b
```

Values: `Q_b = 0.021` W/m² (Apollo 15), `0.015` W/m² (Apollo 17) — from
`SITES` in `lunar/config.py` (Langseth 1976 / Nagihara 2018).

**Now derive the rising mean profile.** Deep below the skin, the temperature
barely oscillates day-to-night. Take the **time average** `⟨·⟩` over one
lunation of the heat equation:

```
ρ c_p · ∂⟨T⟩/∂t  =  ∂/∂z [ K · ∂⟨T⟩/∂z ]
```

In periodic steady state, the left side is **zero** — the mean temperature at
each depth is not changing anymore. So:

```
∂/∂z [ K · ∂⟨T⟩/∂z ]  =  0
```

This means `K · ∂⟨T⟩/∂z` is **constant with depth** — the same steady heat
flux everywhere:

```
K · d⟨T⟩/dz  =  constant  =  Q_b
```

Solve for the gradient:

```
d⟨T⟩/dz  =  Q_b / K
```

**Read it:** if more heat must flow up from the interior (`Q_b` larger), or if
the soil conducts poorly (`K` smaller), the temperature must rise **more
steeply** with depth to carry that flux.

**Numerical example (A15):** `Q_b = 0.021` W/m², `K_d ≈ 0.0046` W/m/K →
gradient ≈ 4.6 K/m. Over 2 m that is ~9 K of warming — consistent with Apollo
data.

This is why the mean profile is a **straight rising line** below ~1 m, not a
flat plateau. The `phase2` scripts demonstrate it directly.

#### 2.7.5 The `K_d`–`Q_b` degeneracy (preview)

Deep sensor temperatures depend on the **ratio** `Q_b / K_d`, not on either
alone. If you assumed a different `Q_b`, you would retrieve a different `K_d`
to fit the same temperatures. Section 5.4 discusses this honestly; every
headline result is stated *conditional on the published basal heat fluxes*.

---

### 2.8 Boundary conditions — full derivation and connection to the main equation

This section answers the question: *the heat equation governs the interior —
but what happens at the top and bottom faces, and how do those rules connect to
the PDE and to the code?*

#### 2.8.1 Why the main equation is not enough by itself

The heat equation (Section 2.3) is a **partial differential equation** in `z`
and `t`. It relates how temperature **changes in time** to how heat **varies
with depth**:

```
ρ c_p · ∂T/∂t  =  ∂/∂z [ K · ∂T/∂z ]        (interior, 0 < z < z_max)
```

This is **one equation for one unknown** `T(z,t)`, but it contains **second
derivatives in depth** (`∂²T/∂z²` in disguise). In mathematics, a second-order
equation in `z` needs **two boundary conditions** — one at each end of the
domain — plus an **initial condition** at `t = 0` to pick out a unique solution.

**Analogy:** the heat equation is like saying "every point in the column obeys
energy conservation." But without rules at the **surface** (where the Sun hits)
and the **deep bottom** (where interior heat enters), infinitely many
temperature profiles would satisfy the interior rule. The boundary conditions
are those missing rules.

The **complete problem** this repository solves is:

```
┌─────────────────────────────────────────────────────────────────┐
│  INTERIOR (every cell):   ρ c_p ∂T/∂t = ∂/∂z(K ∂T/∂z)         │
│  TOP (z = 0):             radiative energy balance → T_s(t)    │
│  BOTTOM (z = z_max):      prescribed upward flux Q_b           │
│  INITIAL (t = 0):         starting profile T(z, 0)               │
└─────────────────────────────────────────────────────────────────┘
```

Paper Eqs. 1–3 are exactly this list.

#### 2.8.2 One unifying idea: energy balance at every control volume

Section 2.3 derived the interior PDE from energy balance on a **thin slice**
sandwiched between two interior faces. At the **boundaries**, the same
bookkeeping applies — but one face of the control volume is no longer "another
soil cell"; it is the **edge of the world** (space above, or the deep interior
below).

```
Interior cell i:     (flux in from above) − (flux out below) = storage
Top surface:         (Sun in) − (radiation out) − (flux into soil) = 0
Bottom cell:         (flux in from above) − (fixed flux Q_b out below) = storage
```

The boundary conditions are **not separate physics** — they are the **same
energy-conservation principle** applied where the domain ends.

#### 2.8.3 Top boundary — deriving the radiative surface balance

**Step 1 — Choose the control volume.**

Take the **surface skin** at `z = 0`: a thin layer of regolith in contact with
space above and with the first grid cell below. Its temperature is `T_s(t)` —
this may differ slightly from the temperature at the centre of the first soil
cell `T(z₁)` because of the finite grid spacing.

**Step 2 — List energy flows (no soil above).**

There is **no conduction from above** (vacuum). At each instant:

| Flow | Direction | Expression |
|------|-----------|------------|
| Absorbed sunlight | IN | `(1 − A) · S(t)` |
| Emitted infrared | OUT | `ε · σ · T_s⁴` |
| Conduction into soil | OUT (downward) | `q_cond(0)` |

**Step 3 — Apply energy conservation.**

For the surface skin in steady balance over a timestep (no net storage in the
infinitely thin skin):

```
(1 − A) · S(t)  −  ε · σ · T_s⁴  −  q_cond(0)  =  0
```

This is **paper Eq. 2** and `surface_energy_balance_residual` in
`lunar/solver.py`.

**Step 4 — Connect conduction to the main equation (Fourier's law).**

The conductive term is not a new law — it is **Fourier's law** (Section 2.2)
evaluated at the top face:

```
q_cond(0)  =  −K(T_s, 0) · (∂T/∂z)|_{z=0+}
```

In words: heat conducted **into** the column equals conductivity times the
temperature gradient just below the surface. The code approximates this across
the half-cell from the surface to the first cell centre:

```
q_cond(0)  ≈  K_surf · (T_s − T_sub) / (Δz₀ / 2)
```

where `T_sub` is the temperature at the first interior point (`T[0]` in the
grid) and `Δz₀/2` is the distance from the surface to that cell centre. This
is exactly what `surface_energy_balance_residual` implements:

```289:312:lunar/solver.py
def surface_energy_balance_residual(
    T_s: float,
    insolation: float,
    albedo: float,
    emissivity: float,
    K_surf: float,
    dz_surf: float,
    T_subsurf: float,
) -> float:
    ...
    radiative_in = (1.0 - albedo) * insolation
    radiative_out = emissivity * SIGMA_SB * T_s**4
    conductive = K_surf * (T_s - T_subsurf) / (0.5 * dz_surf)
    return radiative_in - radiative_out - conductive
```

**Step 5 — How this replaces the interior equation at `z = 0`.**

The interior heat equation is **not applied** at the mathematical surface
`z = 0` in the same form. Instead:

- The **first soil cell** still obeys the discretised heat equation (Crank–
  Nicolson in `_step`).
- But its **top neighbour** is not another cell — it is the surface at
  temperature `T_s`, which is **not known in advance**.
- Each timestep, `_solve_surface_newton` finds `T_s` such that the energy
  balance residual is zero, **then** plugs `T_s` into the first row of the
  tridiagonal system as a "ghost" boundary temperature:

```
d[0] += 0.5 * alpha_l[0] * T_s_new    # implicit-side ghost at surface
```

So the top BC **couples** the radiative balance to the interior diffusion
equation: the surface temperature adjusts until the Sun's input, the radiation
to space, and the heat flowing into the first cell are consistent.

**Why Newton?** The `T_s⁴` term makes the balance **non-linear** — you cannot
write `T_s = (something simple)`. Newton iteration finds the root of
`R(T_s) = 0` in a few steps (Section 3.5).

#### 2.8.4 Bottom boundary — deriving the geothermal flux condition

**Step 1 — Choose the control volume.**

Take the **deepest grid cell** (index `n−1`), between depth `z_{n−2}` and the
bottom face at `z = z_max`.

**Step 2 — What is below the domain?**

We do **not** model the Moon's mantle and core in this 5 m column. We only know
from heat-flow measurements that a **steady upward flux** `Q_b` enters the
bottom of the regolith column from below (Langseth 1976; Nagihara 2018).

**Step 3 — Prescribe flux instead of temperature.**

At the bottom face we impose **Neumann** (flux) boundary condition:

```
q|_{z=z_max}  =  −K · (∂T/∂z)|_{z_max}  =  Q_b
```

Sign convention: `Q_b > 0` means heat flows **upward** (from the interior of the
Moon toward the surface). Fourier's law with `z` positive downward gives the
minus sign: a **positive** upward flux requires temperature to **increase** with
depth (`∂T/∂z > 0`).

This is **paper Eq. 3**. Values: `Q_b = 0.021` W/m² (A15), `0.015` W/m² (A17).

**Step 4 — Connect to the interior PDE.**

For the bottom cell, the interior heat equation still holds:

```
ρ c_p · ∂T/∂t  =  (flux in from cell above) − (flux out at bottom face)
```

But the **outgoing flux at the bottom face is not computed from a neighbour
cell** — it is **fixed** to `Q_b`. In discrete form, this adds a source term
to the bottom cell's energy budget:

```
(storage change)  =  (flux from above) − Q_b
```

The code implements this as:

```487:497:lunar/solver.py
    # --- Lower BC: geothermal flux (Neumann) --------------------------------
    ...
    b[-1] -= 0.5 * alpha_r[-1]
    d[-1] += dt * inputs.Q_b / cap[-1]
```

The term `dt * Q_b / cap[-1]` is exactly "energy per m² deposited in the bottom
cell per timestep from the prescribed basal flux," converted into a temperature
increment.

**Step 5 — Steady-state consequence (link to Section 2.7.4).**

When `∂T/∂t = 0` everywhere, flux is constant with depth. The bottom BC sets
that constant to `Q_b`. Combined with Fourier's law throughout the column:

```
K · d⟨T⟩/dz  =  Q_b   everywhere below the skin
⟹  d⟨T⟩/dz  =  Q_b / K
```

The bottom BC is therefore the **physical source** of the rising mean
temperature profile — it continually feeds heat upward, and conduction carries
it toward the surface.

#### 2.8.5 How the three pieces fit together in one timestep

Here is the full logic flow inside `_step` / `solve_pixel` for one hourly step:

```
                    ┌──────────────────────┐
                    │  Known: T^n at all   │
                    │  depths, S(t), Q_b   │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   ┌───────────┐        ┌────────────┐       ┌────────────┐
   │ TOP: find │        │ INTERIOR:  │       │ BOTTOM:    │
   │ T_s from  │        │ Crank–     │       │ add Q_b    │
   │ radiative │        │ Nicolson   │       │ source to  │
   │ balance   │        │ on cells   │       │ last cell  │
   │ (Newton)  │        │ 1…n−2      │       │            │
   └─────┬─────┘        └──────┬─────┘       └──────┬─────┘
         │                     │                     │
         │    T_s feeds top    │    same PDE         │  fixes flux
         │    ghost of row 0   │    ρc∂T/∂t=∂(K∂T/∂z)/∂z│  at z_max
         └─────────────────────┼─────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Solve tridiagonal   │
                    │  system → T^{n+1}    │
                    │  at all depths       │
                    └──────────────────────┘
```

| Region | Governing rule | What it fixes |
|--------|----------------|---------------|
| Interior cells | Discretised heat equation | How each layer warms/cools from neighbour fluxes |
| Top face | Radiative balance | Surface temperature `T_s` (unknown each step) |
| Bottom face | Prescribed flux `Q_b` | Upward heat entering the column from the deep Moon |

The interior PDE and both BCs are **coupled in one linear system** (Thomas
solve) after `T_s` is found — they are not solved independently.

#### 2.8.6 Initial condition — the fourth ingredient

The PDE is first-order in time (`∂T/∂t`), so we also need **T(z, t=0)** — a
starting temperature at every depth. In principle any guess would eventually
relax to the correct periodic answer after ~1000 lunations.

The Anchor Point Method (Section 4) exists precisely because:

1. A bad initial guess contaminates the deep profile if you stop early.
2. The equilibrium driver iterates until the **combined** PDE + BCs + periodic
   constraint are satisfied, erasing the guess.

So the initial condition is the fourth leg of the stool; the BCs are what make
the top and bottom physically meaningful.

#### 2.8.7 Sanity check — do BCs + PDE give the right lunar behaviour?

| Observation | Which piece explains it |
|-------------|-------------------------|
| Surface swings ~100 K day/night | Top BC: Sun vs `T_s⁴` radiation |
| Deep sensors barely oscillate | Interior PDE: skin damping (Section 2.6) |
| Mean profile rises with depth | Bottom BC: steady `Q_b` upward |
| `K_d` retrieval works at 0.8–2.4 m | BCs + PDE set the deep gradient `Q_b/K_d` |
| Diviner surface closure test | Top BC + insolation model (Section 5 / paper) |

If any boundary were wrong — e.g. fixed surface temperature instead of
radiation, or `Q_b = 0` — the interior solver would still run, but the
profile would be **physically wrong** and would not match Apollo or Diviner.

---

### 2.9 Orbital mechanics and the top boundary — full picture with diagrams

Section 2.8 derived the top BC from energy balance. This section adds **where
`F_⊙(t)` comes from** (Sun–Moon geometry) and how orbital forcing plugs into
that balance. The PDF handbook (`docs/teaching/beginners_guide.pdf`) has colour
TikZ figures for this section; ASCII sketches below mirror the same content.

#### 2.9.1 What “one lunar day” means

The Moon rotates once per orbit, so the same face always points at Earth. From
a fixed spot on the surface, **day and night are set by the Sun**, not Earth.

- **Synodic month** `P ≈ 29.53` days — time from one local noon to the next.
  Code: `T_LUNAR ≈ 2.55×10⁶` s.
- **Subsolar point** — where the Sun is directly overhead (`θ_⊙ = 0`); it marches
  around the equator once per month.
- **Site latitude `φ`** — A15 at 26.1°N, A17 at 20.2°N. The Sun never passes
  directly overhead; at “noon” it is lower in the sky than at the equator.

#### 2.9.2 Sun–Moon–surface geometry (zenith angle)

```
                    Sun
                     \
                      \   sunlight
                       \
                        \  θ_⊙  (solar zenith angle)
                         \
    ─ ─ ─ lunar equator ─ ● ─ ─ ─  (subsolar march)
                         /\
                        /  \  φ = site latitude
                       /    \
                      /      ●  Apollo site (surface)
                     /       |
                    /    local vertical (zenith)
```

**Solar zenith angle `θ_⊙`:** angle between the local vertical and the Sun.
Smaller `θ_⊙` → Sun higher → stronger heating per horizontal square metre.

#### 2.9.3 From geometry to insolation (cosine law)

The solar constant `S_0 ≈ 1361 W/m²` is flux in a beam **perpendicular** to the
Sun. On a **horizontal** patch, only the cosine component counts:

```
F_⊙(t)  =  max( 0 ,  S_0 · cos θ_⊙(t) )
```

At night, `cos θ_⊙ < 0` and the `max(0,·)` clips insolation to zero.

**Idealised model used in production** (same as the manuscript):

```
cos θ_⊙(t)  =  cos φ · cos( 2π t / P )
F_⊙(t)      =  S_0 · max( 0 , cos θ_⊙(t) )
```

Code in `scripts/pipeline/retrieve_kd.py`:

```python
cos_lat = np.cos(np.radians(lat))
phase = 2 * np.pi * t / T_LUNAR
insol = S0 * cos_lat * np.maximum(0.0, np.cos(phase))
```

**What is neglected (and why that is OK here):**

| Effect | Size | Why neglected for `K_d*` retrieval |
|--------|------|-------------------------------------|
| Solar declination | ±1.5° | Compares **mean** temps, not diurnal phase |
| Orbital eccentricity | ±3.3% peak flux | <0.1% on cycle-mean insolation |
| Libration / crater shadows | local | Idealised horizontal patch at each site |

Full SPICE ephemeris (exact zenith vs Unix time) lives in `lunar/ephem.py` but
is **not** used in the main `K_d` retrieval loop.

#### 2.9.4 Insolation over one lunation (schematic)

```
F_⊙ (W/m²)
  │
S_0├ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  │     ╱╲                    peak < S_0 because φ > 0
  │    ╱  ╲
  │   ╱    ╲
  │  ╱      ╲___________________________  night (F_⊙ = 0)
  └────────────────────────────────────────── t (days)
  0        ~7.4       ~14.8      ~22.1      ~29.5
              ←──── one synodic month P ────→
```

At Apollo latitudes, peak daytime flux is **`S_0 cos φ`**, not full `S_0`.

#### 2.9.5 Top boundary control volume (ties orbit to Section 2.8)

```
        space / sky  (T_space ≈ 0)
  ═══════════════════════════════════════  z = 0  (surface, temperature T_s)
        │ emitted IR:  ε σ T_s⁴  ↑
        │ conduction:  q_cond = −K ∂T/∂z  ↓  into regolith
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  ░░░░░░░░░░░░░  regolith  (z > 0)  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

  FROM LEFT (daytime):  incident solar F_⊙(t)
                        absorbed: (1−A) F_⊙(t)
                        reflected: A F_⊙(t)  (small arrow back to space)
```

**Balance at every instant** (same as Section 2.8.3):

```
(1 − A) · F_⊙(t)  =  ε σ T_s(t)⁴  +  q_cond(t)
```

- **`F_⊙(t)`** is **prescribed** from the orbital cosine model (known input).
- **`T_s(t)`** is **unknown** — Newton's method finds it each hour so the
  balance holds (`surface_energy_balance_residual` → `_solve_surface_newton`).
- **`q_cond`** couples the surface to the interior PDE.

#### 2.9.6 End-to-end chain (orbit → PDE)

```
Orbit + latitude φ
       ↓
cos θ_⊙(t) = cos φ cos(2πt/P)
       ↓
F_⊙(t) = S_0 max(0, cos θ_⊙)
       ↓
Top BC: (1−A)F_⊙ = εσT_s⁴ + q_cond     →  Newton finds T_s
       ↓
Interior PDE: ρ c_p ∂T/∂t = ∂/∂z(K ∂T/∂z)   +   bottom BC: Q_b
```

#### 2.9.7 Bottom boundary (for contrast)

The bottom at `z = z_max = 5 m` sees **no Sun** — only a small steady upward
flux from the lunar interior:

```
−K · ∂T/∂z  =  Q_b     (≈ 0.02 W/m² at Apollo sites)
```

No orbital variation; only the top boundary feels the synodic cycle.

#### 2.9.8 Code map

| Step | Code | Role |
|------|------|------|
| 1 | `cos_lat = np.cos(np.radians(lat))` | latitude factor |
| 2 | `phase = 2*np.pi*t/T_LUNAR` | lunation phase |
| 3 | `insol = S0 * cos_lat * max(0, cos(phase))` | build `F_⊙(t)` |
| 4 | `run_with(..., insolation=insol)` | pass into solver |
| 5 | `_solve_surface_newton(...)` | top BC → `T_s` |
| 6 | `_step(...)` | Crank–Nicolson interior + bottom `Q_b` |

---

## 3. The numerical method, gently

The heat equation (2.3) is a continuous statement about every point and every
instant. A computer can't handle "infinitely many points." So we
**discretize**: chop space into finite slices and time into finite steps, and
turn the calculus into arithmetic the computer can repeat millions of times.

### 3.1 Slicing the depth: why a *geometric* grid

We split the 5-meter soil column into many thin horizontal layers and track one
temperature per layer. The clever part: the layers are **not equally thick**.

- Near the surface, temperature swings violently over a few centimeters (the
  skin). To capture that we need **very thin** layers (~2 mm at the top).
- Deep down, temperature barely changes over a whole meter. Thin layers there
  would just waste computer effort.

So each layer is made ~8% thicker than the one above it. This is a **geometric
grid** (each step multiplied by a constant ratio). The docstring of
`lunar/grid.py` puts it perfectly:

```5:15:lunar/grid.py
To simulate heat moving through soil, we chop the 5-metre column into
many thin horizontal slices and track the temperature of each one. The
trick: the slices are NOT all the same thickness. Near the surface,
where temperature swings wildly between lunar day and night, we use
paper-thin slices (~2 mm) so we capture the fast changes. Deeper down,
where temperature barely moves, the slices get gradually thicker (each
~8% thicker than the one above). This "geometric" spacing puts the
computational effort where the action is -- like taking many photos per
second of a sprint start but only one per minute of a marathon's
middle.
```

The grid is built by `make_geometric_grid`, configured in `lunar/config.py`:

```43:44:lunar/config.py
# --- depth grid (geometric) --------------------------------------------------
GRID = dict(z_max=5.0, dz0=0.002, growth=0.08)
```

That reads: total depth 5 m, top layer 2 mm thick, each next layer 8% thicker
(growth ratio 1.08). Uniform grids are *deliberately forbidden* in this project
(the code even raises an error) because they under-resolve the skin while
wasting effort deep down.

> **Heads-up on a harmless duplication.** `lunar/constants.py` also defines
> *fallback* grid defaults (`Z_MAX_DEFAULT = 3.0`, `GROWTH_DEFAULT = 0.15`).
> Those are only used if someone calls `make_geometric_grid()` with no
> arguments. The real science runs always pass `GRID` from `config.py`
> (5 m / 2 mm / 1.08), so the production grid is the `config.py` one. Don't be
> confused by the two different numbers.

### 3.2 Stepping through time: what a "timestep" is

We also chop **time** into steps. Here each step `Δt` is **one hour**
(`DT_STEP = 3600.0` seconds in `config.py`). Starting from the temperatures
right now, we apply the heat equation to compute the temperatures one hour
later, then repeat. One full lunar day (a "lunation") is ~29.5 Earth days
(2,551,443 seconds), so one simulated lunation is **709 hourly samples**
(`N_t = int(T_LUNAR / DT_STEP) + 1` in `run_with`). The test suite samples more
coarsely (2-hour steps) to keep continuous-integration runs fast.

> **A handy units gotcha.** Watch out for the number 2551: it looks like a
> timestep count but is really the lunation *length* in thousands of seconds
> (2,551,443 s). The number of hourly steps is **709**. (Earlier code comments
> in `scripts/pipeline/retrieve_kd.py` mixed these up; they've since been
> corrected to 709.)

### 3.3 Crank–Nicolson: a stable, accurate way to take a step

There are simple ways to step a heat equation forward, but the naïve ones
either blow up (become numerically unstable) unless the timestep is
microscopically small, or they're inaccurate. **Crank–Nicolson** is the
standard professional choice. Intuition:

- An **explicit** step computes the future purely from the present. Cheap, but
  unstable for stiff problems like heat (it can oscillate and explode).
- An **implicit** step computes the future from the future (you solve a small
  system of equations). Stable, but slightly less accurate.
- **Crank–Nicolson averages the two** ("half now, half later," the `0.5`
  factors you'll see in the code). The result is both **stable** *and*
  **second-order accurate** in time. It's coded in `_step` in
  `lunar/solver.py` (look for the `0.5 * alpha_...` terms — that 0.5 *is* the
  Crank–Nicolson averaging).

You don't need to derive it. Just know: *Crank–Nicolson is the recipe that
lets us take comfortable one-hour steps without the simulation exploding.*

### 3.4 The tridiagonal (Thomas) solver: the fast inner engine

An implicit/Crank–Nicolson step requires solving a system of linear equations:
"find all the new-layer temperatures at once such that they're mutually
consistent." Normally solving N equations in N unknowns is slow (cost grows
like N³). But here each layer only talks to its **immediate neighbors above and
below** — so the system is **tridiagonal** (nonzero only on the diagonal and
the two adjacent diagonals).

For tridiagonal systems there's a famous shortcut, the **Thomas algorithm**,
that solves them in a single sweep down and a single sweep back up — cost grows
only like N (linear), which is as fast as it gets. It's implemented in
`_thomas` in `lunar/solver.py`:

```147:167:lunar/solver.py
@njit(cache=True)
def _thomas(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Thomas algorithm for an (a, b, c) tridiagonal system A x = d.

    ``a`` and ``c`` are the sub- and super-diagonals; ``a[0]`` and
    ``c[n-1]`` are ignored. All arrays have shape ``(n,)``.
    """
    n = b.size
    cp = np.empty(n)
    dp = np.empty(n)
    x = np.empty(n)
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x
```

The `@njit` decorator is **Numba**, a tool that compiles this Python down to
machine code so it runs ~10–100× faster (this inner loop runs millions of
times). If Numba isn't installed, the code falls back to plain Python and still
works — see the `try/except` at the top of `lunar/solver.py`. (`docs/`
contains `NUMBA_VS_CPP_JUSTIFICATION.md` explaining why Numba was chosen over
writing C++.)

One more detail: conductivity between two adjacent layers uses the **harmonic
mean** (`_face_harmonic_mean`), not the simple average. For heat flowing
*through* two materials in series (like the deep, conductive layer feeding the
fluffy, insulating layer above), the harmonic mean is the physically correct
combination — the poor conductor dominates, just as the narrowest pipe
dominates a series of pipes.

### 3.5 Newton's method for the non-linear surface

Remember the surface radiates as `Ts⁴` (2.7). That fourth power makes the
surface energy-balance equation **non-linear** — you can't just solve for `Ts`
algebraically. Instead we use **Newton's method**, the classic "guess, check
the error, slide toward the answer, repeat" root-finder:

1. Guess a surface temperature `Ts`.
2. Compute the **residual** `R(Ts)` — how badly the energy balance fails
   (absorbed − radiated − conducted; `surface_energy_balance_residual`).
3. Use the slope `dR/dTs` to jump to a better guess.
4. Repeat until `R` is ~0 (a few iterations).

This is `_solve_surface_newton` in `lunar/solver.py`. The code notes the
derivative is always negative, which guarantees Newton converges from any
positive starting temperature. So at **every hourly step**, the solver does a
tiny Newton solve to pin the surface temperature, then a Thomas sweep to update
the whole column. That's the complete inner loop.

---

## 4. The Anchor Point Method

This is the **centerpiece** of the project — the clever idea that makes the
whole thing fast *and* trustworthy. It lives in `lunar/equilibrium.py`. Read
that file's docstring; it's excellent. This section builds on it.

### 4.1 The problem: the deep Moon settles agonizingly slowly

We want the **periodic steady state**: the repeating day-after-day temperature
pattern the soil settles into after a long time, when every lunar day looks
like the last. To get there the obvious approach is "spin-up" — just press play
and simulate many lunar days until things stop changing.

The catch: the **deep** column relaxes on the *diffusion timescale of the whole
5-meter column*, which is roughly **1000 lunar days**. Simulating 1000
lunations per run, for the ~300 runs the retrieval needs, is hopeless.

Worse, if you stop early (say after 30 lunations), the deep temperature still
**secretly remembers your starting guess**. And the deep temperature is exactly
what the Apollo sensors measure. So your "measurement" of `K_d` would be
contaminated by an arbitrary guess you typed in. This was a real, critical bug
caught in the project's own audit — **flag F1** in `docs/FLAG_REPORT.md`. The
original code used hard-coded starting temperatures (250 K for A15, 255 K for
A17), and a ±5 K change in that guess swung the retrieved `K_d*` by a factor of
~6 — *larger than the very inter-site contrast the paper reports!* That had to
be fixed before any result could be believed.

### 4.2 The key insight: two clocks

The fix comes from realizing the soil has **two very different "clocks":**

- **The shallow skin (top ~half meter) is FAST.** It settles into its
  repeating day/night rhythm within a handful of lunar days, because it's thin
  and driven hard by the surface.
- **The deep column is SLOW** to settle by brute force — *but* in steady state
  it must obey one dead-simple rule: the same steady interior heat `Q_b` flows
  through every layer. That single rule, `d⟨T⟩/dz = Q_b/K`, **fixes the entire
  deep temperature shape instantly** — no waiting required. (`⟨T⟩` means the
  cycle-averaged temperature; angle brackets = "average over one day.")

So instead of waiting 1000 lunations for the deep column, we **calculate** it
from the steady-flux rule, and only ever simulate the fast skin.

#### 4.2.1 Where `d⟨T⟩/dz = Q_b / K` comes from (the physics shortcut)

This is the same derivation as Section 2.7.4, but now in the **anchor-point
context**:

1. Start from the full heat equation (Section 2.3).
2. Take the **cycle mean** `⟨·⟩` over one lunation.
3. In periodic steady state, `∂⟨T⟩/∂t = 0` at every depth (the mean profile
   is not drifting anymore).
4. The equation collapses to: `∂/∂z [ K · ∂⟨T⟩/∂z ] = 0`.
5. So `K · d⟨T⟩/dz` is constant = `Q_b` everywhere below the skin.
6. Integrate downward from the anchor: `⟨T⟩(z) = ⟨T⟩(z_anchor) + ∫ Q_b/K dz`.

That integral is exactly what `_reconstruct_subskin` does in
`lunar/equilibrium.py` — a few lines of midpoint (RK2) integration.

**Analogy:** you don't need to watch paint dry on every wall in a house to know
the steady temperature profile in the insulated attic. Once the roof (skin) has
settled, the deep floors are set by a simple "heat leaking up from the
basement" rule.

#### 4.2.2 The rectified flux `u_rect` — why the anchor sits at 0.55 m

Inside the diurnal skin, two complications make the naive mean-flux rule
slightly wrong:

1. **Conductivity depends on temperature** (`K(T)` rises when hot).
2. **Temperature oscillates daily** (hot noon, cold midnight).

The cycle-mean flux is not exactly `K(⟨T⟩) · d⟨T⟩/dz`. There is a small extra
**rectification** (eddy) term:

```
⟨K · ∂T/∂z⟩  =  K(⟨T⟩) · d⟨T⟩/dz  +  u_rect
```

`u_rect` is measured exactly from the resolved cycle in `_rectified_flux`. The
reconstruction uses:

```
d⟨T⟩/dz  =  (Q_b − u_rect) / K(⟨T⟩)
```

`u_rect` is negligible below ~1 m but can be a few percent of `Q_b` near
0.3–0.5 m. That is why the anchor is placed at **0.55 m** — below the worst
rectification zone but still shallow enough to relax quickly.

### 4.3 The method: alternate "settle the skin" and "rebuild the deep"

The algorithm (the "outer iteration") alternates two cheap steps until they
agree:

1. **Settle the skin.** Run the full solver for just a few lunar days
   (`n_inner = 12`) starting from the current profile. This locks the fast skin
   into rhythm against the current deep column.
2. **Rebuild the deep.** Read the cycle-mean temperature at one trusted
   **anchor depth** just below the skin (`z_anchor = 0.55 m`), then integrate
   the steady-flux rule `d⟨T⟩/dz = (Q_b − u_rect)/K` *downward* from there to
   reconstruct the entire deep profile exactly.

Repeat steps 1–2 a few times (typically 3–5). The result "locks on" to the true
periodic steady state. The actual loop is `solve_periodic_equilibrium` in
`lunar/equilibrium.py`; the deep rebuild is `_reconstruct_subskin`.

Two refinements worth knowing:

- **`u_rect` — the rectified flux.** Inside the skin, the daily wobble plus the
  fact that conductivity depends on temperature creates a small extra
  *day-night-averaged* heat term (an "eddy" or "rectification" term). The code
  measures it exactly from the resolved cycle (`_rectified_flux`) and
  subtracts it, so the deep rebuild stays accurate. It's negligible below ~1 m
  but matters a few percent right at the anchor — which is precisely why the
  anchor is placed at 0.55 m, *below* the worst of it.
- **Two-stage anchor schedule.** The code first anchors high (0.25 m, relaxes
  fast) to cheaply kill most of the starting-guess error, then drops to 0.55 m
  for the accurate finish. See the `stages` tuple in
  `solve_periodic_equilibrium`.

### 4.4 Why it's both fast *and* unbiased

- **Fast:** it only ever simulates the quick skin (a few lunations per outer
  step, ~36–60 lunations total) instead of ~1000. Comparable cost to the old
  broken spin-up, but correct.
- **Unbiased (this is the crucial part):** the final answer **no longer
  depends on the starting guess**. The skin is forced periodic by step 1; the
  deep is forced to satisfy steady flux by step 2. The only fixed point of that
  two-step map is the *true* equilibrium. The starting guess just seeds the
  first iterate and gets erased.

This is **certified, not assumed.** The regression test
`tests/test_equilibrium.py::test_guess_independence` literally runs the solver
from two different starting guesses (242 K and 258 K) and asserts the converged
profiles agree:

```32:43:tests/test_equilibrium.py
def test_guess_independence():
    """Converged profiles from 242 K and 258 K guesses must agree."""
    grid, t, insol, k_func, cp_func = _setup()
    profiles = []
    for guess in (242.0, 258.0):
        eq = solve_periodic_equilibrium(
            grid=grid, t=t, insolation=insol, albedo=0.131,
            emissivity=0.95, Q_b=0.021, K_func=k_func, cp_func=cp_func,
            T_guess=guess)
        assert eq.converged
        profiles.append(eq.T_mean)
    assert np.max(np.abs(profiles[0] - profiles[1])) < 0.1
```

In the full production setting the guess-dependence is ≤ 0.023 K (vs the old
1.6–4.5 K). That is what "F1 RESOLVED" at the top of `docs/FLAG_REPORT.md`
means, and it's why the retrieved `K_d*` values can be trusted.

### 4.5 "Flux closure" — how the code proves it worked

How do you know the deep profile really satisfies steady heat flow? You check
whether the cycle-mean conductive flux equals `Q_b` at every depth. The maximum
relative deviation is the **flux closure** number (`flux_closure` in
`EquilibriumResult`). The retrieval warns if closure is worse than 3%. It is
deliberately measured **below the diurnal skin** (where the rule actually
applies and where every Apollo sensor sits), not at the noisy surface. The test
`test_flux_closure` checks this. The `make_equilibrium_certification.py` figure
script visualizes the whole certification.

---

## 5. The K_d retrieval and uncertainty analysis

Now we connect the simulator to the real Apollo data and extract `K_d`. The
driver is `scripts/pipeline/retrieve_kd.py`.

### 5.1 The data: turning raw HFE records into "equilibrium temperatures"

The bundled Apollo data lives in `data/apollo/depth/` as `.tab` text files
(one per mission per probe, e.g. `a15p1_depth.tab`). Each row is a timestamp, a
temperature, a sensor name, and the sensor's depth in cm. The loader is
`load_apollo_hfe_depth` (`lunar/validation.py`).

But the raw record drifts for years after the probes were emplaced (the
drilling disturbed the soil, which slowly re-equilibrated). We only want the
final **settled** temperature of each sensor. `find_stable_window`
(`lunar/apollo_helpers.py`) scans the late part of each sensor's record and
picks the earliest window where the temperature has gone **flat** (trend slope
below 0.08 K/year), then averages it. That average is the sensor's
**equilibrium temperature `T_eq`**. `extract_sensor_stability` does this for
every sensor and returns depths + `T_eq` values.

Crucially, only sensors **deeper than `MIN_DEPTH_CM = 80 cm`** are used for the
fit (the `deep_mask`). Shallower sensors are contaminated by the borestem (the
hardware sticking up) and by the daily skin, so they're excluded *a priori*.

### 5.2 The retrieval: sweep `K_d`, minimize RMSE

The core idea is a **sweep** (`run_kd_sweep_extended`):

1. Pick a grid of candidate `K_d` values (e.g. 28 values from 1 to 15 mW for
   A15; see `KD_GRIDS` in `config.py`).
2. For each candidate `K_d`, run the equilibrium solver (`run_with`, which
   calls `solve_periodic_equilibrium`) to get a predicted temperature-vs-depth
   profile.
3. Read the model temperature at each real sensor depth and subtract the
   measured `T_eq`. That difference is the **residual**.
4. Combine the residuals into one number, the **RMSE**.

#### 5.2.1 Residuals — what we compare

For sensor `i` at depth `z_i` with measured equilibrium temperature `T_obs,i`
and model prediction `T_model,i(K_d)`:

```
R_i(K_d)  =  T_model,i(K_d)  −  T_obs,i
```

Positive residual → model too hot. Negative → model too cold.

The residual matrix `R` has shape `[n_sensors, n_K_d_values]` — one column per
trial conductivity, built in `run_kd_sweep_extended`.

#### 5.2.2 RMSE — the score we minimize

**RMSE = Root Mean Square Error.** For `N` deep sensors:

```
RMSE(K_d)  =  sqrt( (1/N) · Σᵢ R_i(K_d)² )
```

Step by step in plain English:

1. **Square** each residual — so positive and negative errors don't cancel,
   and big misses are penalised more.
2. **Average** the squares.
3. **Square root** — back to kelvin units, so RMSE is interpretable as "typical
   error size."

Smaller RMSE = better fit. Units are kelvin.

**Example:** if residuals are `[+1, −1, +2]` K → mean square =
`(1+1+4)/3 = 2` → RMSE = √2 ≈ 1.4 K.

#### 5.2.3 Finding `K_d*` — parabolic refinement

The code evaluates RMSE on a grid of `K_d` values, finds the minimum, then fits
a parabola through the three points around the minimum (`kd_star_from_residuals`)
to interpolate the bottom precisely:

```
K_d*  ≈  value where d(RMSE²)/dK_d = 0
```

That is the whole retrieval: *slide the one knob `K_d` until model temperatures
best match the measured ones.*

Result: A15 lands at `K_d* ≈ 4.58`, A17 at `≈ 8.12` mW m⁻¹ K⁻¹, and switching
to per-site values roughly **halves** the Apollo-17 mismatch versus the old
global `K_d = 3.4`.

**Why only `K_d`?** Every other parameter (`K_s`, `H`, `χ`, `Q_b`, albedo,
emissivity) is held at published values. `K_d` is the single deep knob inside
the fixed Hayne shape that the meter-scale Apollo temperatures are sensitive to.

### 5.3 Uncertainty: the bootstrap

A single best-fit number isn't science without an error bar. How sure are we?
The biggest uncertainty is that the **sensor depths themselves** are only known
to about ±2.5 cm (Nagihara 2018). The repo propagates this with a
**bootstrap** (`bootstrap_kd_with_depth_uncertainty`):

- Repeat 1500 times: randomly **resample** the sensors (draw with replacement)
  *and* **jitter** each depth by a random ±2.5 cm wiggle, then re-find `K_d*`.
- You end up with 1500 slightly different `K_d*` values — a whole distribution.
- The middle 95% of that distribution is the **95% confidence interval** (the
  `+1.33/−0.28` style error bars).

A bootstrap is just "shake the inputs within their uncertainty, many times, and
watch how much the answer wobbles." The wobble *is* the error bar. (The
bootstrap reuses cached solver outputs, so it's pure fast statistics — no new
physics runs. It's ~65% of the pipeline's runtime purely because of the 1500
repeats.)

### 5.4 Inter-site contrast and the `K_d`–`Q_b` degeneracy

The headline scientific claim is the **contrast**: A17 − A15 ≈ 3.3 mW m⁻¹ K⁻¹.
Because we have a bootstrap distribution for *each* site, we can subtract them
sample-by-sample to get a distribution for the **difference**, and check
whether it excludes zero. It does, at the published heat fluxes: 95% CI
≈ [0.4, 4.6], p ≈ 0.01 (`contrast_bootstrap` in the results JSON).

The big caveat the paper is honest about: deep temperature depends on the
**ratio** `Q_b/K_d`, so `K_d` and the basal flux `Q_b` are partly
**degenerate** — if you assumed a different `Q_b`, you'd retrieve a different
`K_d`. That's why every result is stated *"conditional on the published basal
heat fluxes."* Propagating the full uncertainty in `Q_b` dilutes the
significance (the ordering probability drops to ~83%). The honest summary: *the
sites differ in the combination `T(z)` they produce; attributing that purely to
conductivity rather than basal flux rests on the published `Q_b` values.*

Several auxiliary scripts probe robustness (held-out tests, model selection,
borestem cut, an independent Bayesian/MCMC cross-check) — see Section 6.

### 5.5 The optional bedrock toggle (for future ice work)

Recently added: an **optional bedrock layer** (`with_bedrock` in
`lunar/properties.py`, configured by `BEDROCK` in `lunar/config.py`). The
standard model treats the Moon as fluffy regolith all the way down. In reality,
below ~10 m there's solid rock, which conducts far better. `with_bedrock` wraps
any conductivity model so that below `z_bedrock` (10 m) the conductivity ramps
smoothly (via a `tanh`) up to a rock value (`K_rock = 2.0`).

It is **OFF by default** and **does not change the published retrieval** — every
Apollo sensor is at ≤ 2.4 m, far above the 10 m transition, where enabling
bedrock shifts temperatures by only ~0.05 K. The tests
`tests/test_bedrock.py` lock in both guarantees (off by default; sensor-depth
temperatures unchanged). It exists for **future deep-profile / ice-stability
studies**, where the temperature far below the regolith *does* matter.

---

## 6. Code tour

A file-by-file map. Two layers: the **`lunar/` package** is the reusable
engine (all the physics and config); the **`scripts/`** are thin command-line
drivers that call the engine and write results/figures. There is exactly one
definition of everything — config never gets copy-pasted.

### 6.1 The `lunar/` package (the engine)

| File | What it does, in plain terms |
|---|---|
| `lunar/__init__.py` | Marks the folder as a package; sets the version. Nothing to study. |
| `lunar/constants.py` | The **physical numbers**: solar constant, Stefan–Boltzmann, regolith `K_s`/`K_d`/`H`/`χ`, density/specific-heat coefficients, basal fluxes. Every value is cited to a paper. Project rule: no unsourced numbers. |
| `lunar/config.py` | The **settings menu / single source of truth**: the two-site table (`SITES`), the depth grid (`GRID`), the Hayne bundle (`HAYNE`), equilibrium-solver knobs, the `K_d` sweep grids, the bedrock toggle. Change "what the experiment is" here. |
| `lunar/grid.py` | Builds the **geometric depth grid** (`make_geometric_grid` → a `DepthGrid` of layer faces, centers, thicknesses). Section 3.1. |
| `lunar/properties.py` | The **soil property formulas**: conductivity (`conductivity_hayne`, `conductivity_martinez`, `conductivity_icy`), density (`density_hayne`), specific heat (`specific_heat`), and the optional `with_bedrock` wrapper. Section 2.4–2.5. |
| `lunar/solver.py` | The **heat-equation engine**: one Crank–Nicolson step (`_step`), the tridiagonal `_thomas` solver, harmonic-mean faces, the Newton surface solve (`_solve_surface_newton`), the driver `solve_pixel`, and the analytical wave used for testing. Section 3. |
| `lunar/equilibrium.py` | The **Anchor Point Method**: `solve_periodic_equilibrium` plus helpers (`_rectified_flux`, `_reconstruct_subskin`, `_diurnal_skin_index`, `_mean_flux_closure`). Returns an `EquilibriumResult`. Section 4. **Read this docstring.** |
| `lunar/validation.py` | Loads the bundled **Apollo HFE** `.tab` data into numpy arrays (`load_apollo_hfe_depth`). |
| `lunar/apollo_helpers.py` | Turns raw HFE records into per-sensor **equilibrium temperatures**: `find_stable_window` (detect the settled tail) and `extract_sensor_stability`. Section 5.1. |
| `lunar/ephem.py` | A **correct SPICE/DE440 solar-position** helper (sun elevation → insolation). *Note:* the `K_d` pipeline uses the simpler idealized cosine forcing, not this — see the discrepancy note in 6.4. |
| `lunar/diviner.py` | Helpers for **Diviner** orbital surface-temperature data, used for the surface-temperature "closure" cross-check. |
| `lunar/plotting/style.py` | Shared **figure styling** (JGR:Planets sizes, color palette, layout helpers). Importing it gives every figure a consistent look. |
| `lunar/_bootstrap.py` | Small **environment bootstrap** so standalone scripts can find the package and the data. Plumbing, not physics. |

### 6.2 `scripts/pipeline/` (compute results → write `output/*.json`)

| File | What it produces |
|---|---|
| `retrieve_kd.py` | **The main event.** Loads HFE data, runs the `K_d` sweep + bootstrap + joint (`K_d`,`H`) grid + held-out tests, writes `output/kd_retrieval_results.json` and the bootstrap/robustness/holdout figures. Start here. |
| `compute_headline_rmse.py` | The headline RMSE-vs-`K_d` numbers (a second grid as a cross-check). |
| `compute_borestem_sensitivity.py` | How `K_d*` changes if you move the shallow-sensor cutoff (the borestem-contamination test). |
| `compute_stability_threshold_sensitivity.py` | How results depend on the "flatness" threshold used to detect equilibrium windows. |
| `compute_surface_bias_test.py` | Tests for systematic surface-temperature bias. |
| `compute_uniform_kd_sensitivity.py` | What you'd get with a single uniform `K_d` (the "old way") for comparison. |
| `compute_fixed_input_sensitivities.py` | How `K_d*` responds to fixed inputs (albedo, `H`, etc.) — feeds the error budget. |
| `compute_model_selection.py` | Compares competing conductivity models (AICc model selection). |
| `compute_error_budget.py` | Assembles the full systematic error budget (paper Table 4). |
| `bayesian_crosscheck.py` | An independent **MCMC/Bayesian** retrieval as a cross-check on the bootstrap. |
| `compute_diviner_closure.py` | Checks the model's surface temperature against orbital **Diviner** data. |

### 6.3 `scripts/figures/` and `scripts/analysis/`

- `scripts/make_all_figures.py` — runs **every** figure generator in order.
- `scripts/figures/make_letter_figures.py`, `make_results_figures.py`,
  `make_intro_figures.py` — the paper's figures.
- `make_equilibrium_certification.py`, `make_equilibrium_demo.py`,
  `make_spinup_animation.py`, `make_newmethod_animation.py`,
  `make_reconstruct_animation.py` — visualize the Anchor Point Method
  (great for understanding Section 4).
- `make_primer_figures.py`, `make_book_figures.py`, `make_codeguide_figures.py`
  — teaching figures for the manuscript/guidebook.
- `scripts/analysis/phase2_depth_convergence.py` — the standalone "what happens
  deep down?" diagnostic (Section 2.6). A great first script to *run and read*.
- `scripts/fetch_diviner.py` — one-time download of Diviner data (~310 MB).
- `scripts/run_all_timed.py` — runs the whole pipeline with timing.

### 6.4 The end-to-end data flow

```
                 lunar/constants.py  (cited physical numbers)
                          │
                          ▼
                 lunar/config.py  (SITES, GRID, HAYNE, solver knobs)
                          │
        ┌─────────────────┼───────────────────────────┐
        ▼                 ▼                           ▼
 lunar/grid.py     lunar/properties.py        data/apollo/*.tab
 (depth slices)    (K, ρ, c_p formulas)              │
        │                 │              lunar/validation.py (load)
        └───────┬─────────┘                          │
                ▼                       lunar/apollo_helpers.py
        lunar/solver.py                 (settle → T_eq per sensor)
        (one CN step + Thomas + Newton)             │
                ▼                                    │
     lunar/equilibrium.py                            │
     (Anchor Point Method → steady T(z))            │
                │                                    │
                └──────────────┬─────────────────────┘
                               ▼
           scripts/pipeline/retrieve_kd.py
   (sweep K_d → min RMSE vs Apollo T_eq → bootstrap → contrast)
                               │
                ┌──────────────┴───────────────┐
                ▼                               ▼
   output/kd_retrieval_results.json   scripts/figures/*  →  paper/letter/
   (K_d* = 4.58 / 8.12, contrast 3.3)     (figures)        letter.tex (PDF)
```

Read it top-to-bottom: cited constants feed the config; the config plus the
property/grid modules feed the solver; the solver wrapped in the Anchor Point
Method produces a steady temperature profile; the retrieval slides `K_d` to
match that profile to the processed Apollo data; the results become JSON,
figures, and ultimately the paper.

---

## 7. How to run it yourself

These commands are cross-checked against `docs/REPRODUCING.md` and the
`Makefile`. Run them from the repository root (`/Users/rp3gregorio/Lunar-HFE`).

### 7.1 One-time setup

```bash
# 1. Create an isolated Python environment (so you don't clutter your system)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install the package + dev tools (pytest, jupyterlab, matplotlib, ...)
make install                     # same as: pip install -e ".[dev]"
```

A **virtual environment** (`venv`) is just a private sandbox of Python
packages for this project. `pip install -e .` installs the `lunar` package in
"editable" mode, meaning Python sees your local `lunar/` folder directly — edit
a file and the change takes effect immediately.

### 7.2 Run the tests first (always do this)

```bash
python3 -m pytest -q
```

This runs the suite in `tests/` (grid, properties, solver, equilibrium,
bedrock, ephem, constants). They finish in under a minute and should **all
pass**. If they don't, fix your environment before trusting any results.
Running tests is the fastest way to confirm everything is wired correctly — and
reading a test is often the clearest example of how a function is meant to be
used.

### 7.3 Verify the committed headline numbers (no computation needed)

The canonical result ships in the repo, so you can check it instantly:

```bash
python3 -c "
import json, math
r = json.load(open('output/kd_retrieval_results.json'))
print('A15 K_d* =', r['A15']['kd_star'] * 1e3, 'mW/m/K')
print('A17 K_d* =', r['A17']['kd_star'] * 1e3, 'mW/m/K')
assert math.isclose(r['A15']['kd_star']*1e3, 4.58, abs_tol=0.01)
assert math.isclose(r['A17']['kd_star']*1e3, 8.12, abs_tol=0.01)
print('Headline values verified.')
"
```

### 7.4 Reproduce the science (recompute from scratch)

```bash
make help          # list every one-word command

make retrieve      # the core K_d retrieval + bootstrap (~5 min)
                   #   → writes output/kd_retrieval_results.json
make aux           # all auxiliary sweeps, model selection, error budget, MCMC
make figures       # regenerate every figure
make paper         # compile the PDFs (needs a LaTeX install)
make all           # everything end-to-end
```

`make retrieve` is the one to run first — it regenerates the headline JSON. The
slow auxiliary sweeps (`make aux`) are rarely needed because their results are
already committed.

### 7.5 Run a single illuminating script

To *see* the deep-temperature physics (Section 2.6) with your own eyes:

```bash
python3 scripts/analysis/phase2_depth_convergence.py
```

It prints the skin depth, the deep gradient, and confirms the mean temperature
keeps rising along `Q_b/K`, then saves
`output/figures/fig_phase2_depth_convergence.png`. Open that image. This is one
of the best on-ramps to understanding the project.

### 7.6 The notebooks (guided, in order)

```bash
jupyter lab notebooks/
```

Run them in order: `00_setup` (checks), `01_methods` (figures + parameter
table), `02_retrieval` (the `K_d` retrieval + bootstrap), `03_results`,
`04_discussion`, `05_animations`. There's also `equilibrium_demo.ipynb`, a
standalone demo that a brute-force 1000-lunation spin-up converges onto the
fast Anchor Point solver — a great way to *believe* Section 4.

### 7.7 Where outputs land

- `output/*.json` — numerical results (the canonical `kd_retrieval_results.json`
  and the auxiliary JSONs).
- `output/figures/*.png` / `*.pdf` — diagnostic and appendix figures.
- `paper/letter/figures/*.pdf` — the paper's figures.
- `paper/letter/letter.pdf` — the compiled manuscript.

---

## 8. Glossary

Plain one-liners. Physics, then numerical, then code/project terms.

**Physics**

- **Regolith** — the loose broken rock and dust covering the Moon; the "soil."
- **Temperature (K, kelvin)** — how hot something is; a scale starting at
  absolute zero (0 K = −273.15 °C).
- **Heat flux** — rate of heat energy flow through a unit area (W/m²).
- **Conduction** — heat moving by direct contact, atom to atom.
- **Thermal conductivity `K`** — how easily a material conducts heat
  (W m⁻¹ K⁻¹); high = metal, low = lunar dust.
- **`K_d`** — the *deep* regolith conductivity; the quantity this project
  retrieves. `K_d*` is the best-fit value.
- **`K_s`** — the *surface* regolith conductivity (very low).
- **`H` (scale height)** — sets how fast conductivity/density transition from
  surface to deep values (~6 cm).
- **`χ` (chi, radiative coefficient)** — strength of the temperature-dependent
  radiative boost to conductivity (the `T³` term).
- **Density `ρ` (rho)** — mass per unit volume (kg/m³).
- **Specific heat `c_p`** — energy to warm 1 kg by 1 K (J kg⁻¹ K⁻¹).
- **Heat equation** — the master PDE: `ρ c_p ∂T/∂t = ∂/∂z(K ∂T/∂z)`. Derived in
  Section 2.3 from energy conservation + Fourier's law.
- **Heat flux `q`** — thermal energy crossing a surface per second per m²
  (W/m²); `q = −K ∂T/∂z` (Section 2.3.3).
- **Boundary condition** — rule at domain edge closing the PDE: radiative balance
  (top), fixed `Q_b` (bottom). Same energy conservation as the interior;
  Section 2.8.
- **Neumann BC** — prescribed flux (not temperature) at an edge; bottom uses `Q_b`.
- **Ghost cell / `T_s`** — surface temperature found each step by Newton; couples
  top BC to the first soil cell.
- **Thermal diffusivity `α`** — `K/(ρ·c_p)`; how fast a temperature change
  spreads through a material (Section 2.6.2).
- **Skin depth `δ`** — `√(2α/ω)`; depth where diurnal amplitude decays to 1/e
  (Section 2.6.4).
- **Stefan–Boltzmann law** — radiative flux `ε σ T⁴`; why the surface BC is
  non-linear (Section 2.7.1).
- **Insolation `S(t)`** — incoming solar power; cosine diurnal model (Section 2.7.3).
- **Geothermal gradient** — `d⟨T⟩/dz = Q_b/K`; derived from steady-state heat
  equation (Sections 2.7.4, 4.2.1).
- **Rectified flux `u_rect`** — day-night-averaged eddy term in the skin;
  subtracted in anchor reconstruction (Section 4.2.2).
- **Residual `R_i`** — model minus observed temperature at sensor i (Section 5.2.1).
- **RMSE** — `√(mean of squared residuals)`; retrieval score in kelvin (Section 5.2.2).
- **Albedo `A`** — fraction of sunlight reflected (≈0.13 here).
- **Emissivity `ε`** — how efficiently a surface radiates heat (≈0.95).
- **Stefan–Boltzmann law** — radiated power ∝ `T⁴`; the `σ` is its constant.
- **Geothermal / basal heat flux `Q_b`** — steady heat seeping up from the
  Moon's interior (~15–21 mW/m²).
- **Periodic steady state / equilibrium** — the repeating day-after-day
  temperature pattern reached after long settling.
- **Diurnal** — daily (here, one lunar day ≈ 29.5 Earth days, a "lunation").

**Numerical**

- **Discretize** — replace continuous space/time with finite slices/steps so a
  computer can solve it.
- **Grid** — the set of depth slices; here **geometric** (each slice ~8%
  thicker than the one above).
- **Timestep `Δt`** — the time jump per update (1 hour here).
- **Crank–Nicolson** — a stable, accurate "half-now, half-later" time-stepping
  scheme.
- **Tridiagonal system** — a linear system where each unknown only couples to
  its two neighbors.
- **Thomas algorithm** — the fast (linear-cost) solver for tridiagonal systems.
- **Harmonic mean** — the correct way to average conductivity between two
  layers in series.
- **Newton's method** — iterative root-finder used for the non-linear surface
  temperature.
- **Residual** — how badly an equation fails for a trial value (model − data,
  or the energy-balance mismatch).
- **RMSE** — root-mean-square error; the average size of the model-vs-data
  mismatch (K).
- **Bootstrap** — estimate uncertainty by resampling/jittering inputs many
  times and watching the answer wobble.
- **Confidence interval (CI)** — the range that contains the answer with stated
  probability (e.g. 95%).
- **Degeneracy** — when two parameters trade off so only their combination is
  constrained (here `K_d` and `Q_b`).

**Code / project**

- **Anchor Point Method** — this project's fast, unbiased equilibrium solver
  (Section 4); the "two clocks" idea.
- **Flux closure** — diagnostic checking the mean conductive flux equals `Q_b`
  at depth (proof the solver converged).
- **`u_rect` (rectified flux)** — small day-night-averaged eddy heat term
  inside the skin, measured and subtracted.
- **Spin-up** — running many cycles to settle a simulation (the slow approach
  the Anchor Point Method replaces).
- **F1** — the audit flag (in `docs/FLAG_REPORT.md`) for the old
  starting-guess-bias bug that the Anchor Point Method fixed.
- **HFE** — Apollo Heat-Flow Experiment (the buried thermometers).
- **Numba / `@njit`** — a just-in-time compiler that speeds up the hot inner
  loops ~10–100×.
- **venv** — an isolated Python environment for this project.
- **pytest** — the tool that runs the test suite.

---

## 9. A learning roadmap

A suggested order to go from "I read this guide" to "I can change the code."

**Day 1 — orient and run.**
1. Re-read Sections 1, 2.1–2.3 (full heat-equation derivation) until the
   bookkeeping picture feels natural.
2. Do setup (7.1), tests (7.2), verify headline numbers (7.3).
3. Run `scripts/analysis/phase2_depth_convergence.py` while reading Section 2.6
   (skin depth) and 2.7.4 (geothermal gradient).

**Day 2 — properties, boundaries, and the engine.**
4. Read Sections 2.4–2.8 (conductivity, skin, radiation, **`K_d`–`Q_b`**, and
   the full BC derivation connecting to the main equation).
5. Read `lunar/constants.py` then `lunar/config.py`.
6. Read `lunar/properties.py` alongside Section 2.5.
7. Read `lunar/grid.py` alongside Section 3.1.
8. Skim `lunar/solver.py`: focus on the *docstring*, `surface_energy_balance_residual`,
   and `_thomas`. Don't try to absorb every index in `_step` yet.

**Day 3 — the centerpiece.**
9. Read the full docstring of `lunar/equilibrium.py` (it's a teaching text in
   itself), then `solve_periodic_equilibrium`, with Section 4 open beside it.
10. Read `tests/test_equilibrium.py` — the tests *are* the precise statement of
    what "correct" means here.
11. Optional: run `equilibrium_demo.ipynb` to watch brute-force converge onto
    the fast method.

**Day 4 — the science.**
12. Read `scripts/pipeline/retrieve_kd.py` top to bottom with Section 5 open.
    Follow one `K_d` value through `run_with` → `run_kd_sweep_extended` →
    `kd_star_from_residuals`.
13. Read `lunar/apollo_helpers.py` to see how raw data becomes `T_eq`.
14. Skim the paper abstract, plain-language summary, and §2 (methods) in
    `paper/letter/letter.tex`.

**Then — make a change (the real test of understanding).**
15. Try a tiny experiment: in a scratch script, call `run_with(SITES['A15'],
    kd=...)` at a couple of `K_d` values and print the temperature at 1.4 m.
    Watch it move toward the data as `K_d` approaches 4.58.
16. Read `docs/FLAG_REPORT.md` to see how the project audits *itself* — this is
    how careful computational science is actually done.

**Deeper study, when ready.**
- Numerical methods: the finite-volume method, implicit vs explicit schemes,
  stability (any intro numerical-PDE text).
- Heat transfer: Fourier's law and the 1-D heat equation (any intro
  heat-transfer text).
- Python scientific stack: NumPy basics (arrays, broadcasting, `np.interp`,
  `np.gradient`) — used everywhere here.
- Statistics: the bootstrap and confidence intervals.

> **The single most effective habit:** keep this guide open on one side and the
> actual code file on the other. Every concept here points at a real function
> you can open, run, and modify. Understanding grows fastest when the words and
> the code are side by side.
