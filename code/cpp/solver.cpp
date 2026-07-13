// Faithful C++ port of the lunar 1-D thermal solver's hot path
// (src/lunar/solver.py: solve_pixel radiative march).
//
// Scope: the SOLVER only -- properties, harmonic faces, Crank-Nicolson
// assembly, Newton surface balance (trapezoidal ghost, 2026-07-03), Thomas
// solve, lunation march. No statistics, no bootstrap.
//
// Faithfulness contract: every formula and its evaluation ORDER mirrors the
// Python line it ports (comments cite the function). Inputs arrive as a raw
// binary blob written by pipeline/compute/benchmark_cpp.py, so grid
// construction and forcing stay in Python -- zero duplication of those
// definitions (single-definition law). Output: the final lunation's full
// T(z, t) cycle, binary doubles.
//
// Build:  clang++ -O3 -std=c++17 -o cpp/lunar_solver cpp/solver.cpp
// Run:    cpp/lunar_solver <input.bin> <output.bin>
//
// Input layout (all little-endian float64 unless noted):
//   int64 n_z, int64 n_t, int64 n_lunations, int64 n_picard
//   z_mid[n_z], dz[n_z], t[n_t], insol[n_t], T_init[n_z]
//   albedo, emissivity, Q_b,
//   Ks, Kd, H, chi, Tref,          (conductivity_hayne)
//   rho_s, rho_d,                  (density_hayne; shares H)
//   cp_c0..cp_c4,                  (Hayne cp polynomial)
//   sigma_SB

#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <chrono>

static double rd(FILE* f) { double v; fread(&v, 8, 1, f); return v; }
static int64_t ri(FILE* f) { int64_t v; fread(&v, 8, 1, f); return v; }

struct Params {
    double albedo, emissivity, Qb;
    double Ks, Kd, H, chi, Tref;
    double rho_s, rho_d;
    double c0, c1, c2, c3, c4;
    double sigma;
};

// properties.conductivity_hayne: K = Kc(z) * (1 + chi*(T/Tref)^3)
static inline double k_hayne(double T, double z, const Params& p) {
    const double Kc = p.Kd - (p.Kd - p.Ks) * std::exp(-z / p.H);
    const double r = T / p.Tref;
    return Kc * (1.0 + p.chi * r * r * r);
}

// properties._cp_hayne: 4th-order polynomial
static inline double cp_hayne(double T, const Params& p) {
    return p.c0 + T * (p.c1 + T * (p.c2 + T * (p.c3 + T * p.c4)));
}

// solver._solve_surface_newton (tol 1e-4, max_iter 40, floor guard)
static double surface_newton(double S, double K_surf, double dz_surf,
                             double T_sub, double T_guess, const Params& p) {
    double T_s = T_guess > 1.0 ? T_guess : 1.0;
    for (int it = 0; it < 40; ++it) {
        const double R = (1.0 - p.albedo) * S
                       - p.emissivity * p.sigma * T_s * T_s * T_s * T_s
                       - K_surf * (T_s - T_sub) / (0.5 * dz_surf);
        const double dR = -4.0 * p.emissivity * p.sigma * T_s * T_s * T_s
                        - 2.0 * K_surf / dz_surf;
        double T_new = T_s - R / dR;
        if (T_new < 1.0) T_new = 0.5 * (T_s + 1.0);
        if (std::fabs(T_new - T_s) < 1e-4) return T_new;
        T_s = T_new;
    }
    return T_s;  // best effort, mirroring Python
}

// solver._thomas
static void thomas(const std::vector<double>& a, const std::vector<double>& b,
                   const std::vector<double>& c, const std::vector<double>& d,
                   std::vector<double>& x, std::vector<double>& cp,
                   std::vector<double>& dp) {
    const size_t n = b.size();
    cp[0] = c[0] / b[0];
    dp[0] = d[0] / b[0];
    for (size_t i = 1; i < n; ++i) {
        const double m = b[i] - a[i] * cp[i - 1];
        cp[i] = (i < n - 1) ? c[i] / m : 0.0;
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m;
    }
    x[n - 1] = dp[n - 1];
    for (size_t i = n - 1; i-- > 0;) x[i] = dp[i] - cp[i] * x[i + 1];
}

int main(int argc, char** argv) {
    if (argc != 3) { std::fprintf(stderr, "usage: %s in.bin out.bin\n", argv[0]); return 1; }
    FILE* f = std::fopen(argv[1], "rb");
    if (!f) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 1; }

    const int64_t n_z = ri(f), n_t = ri(f), n_lun = ri(f), n_picard = ri(f);
    std::vector<double> z(n_z), dz(n_z), t(n_t), insol(n_t), T(n_z);
    fread(z.data(), 8, n_z, f);
    fread(dz.data(), 8, n_z, f);
    fread(t.data(), 8, n_t, f);
    fread(insol.data(), 8, n_t, f);
    fread(T.data(), 8, n_z, f);
    Params p;
    p.albedo = rd(f); p.emissivity = rd(f); p.Qb = rd(f);
    p.Ks = rd(f); p.Kd = rd(f); p.H = rd(f); p.chi = rd(f); p.Tref = rd(f);
    p.rho_s = rd(f); p.rho_d = rd(f);
    p.c0 = rd(f); p.c1 = rd(f); p.c2 = rd(f); p.c3 = rd(f); p.c4 = rd(f);
    p.sigma = rd(f);
    std::fclose(f);

    const size_t n = (size_t)n_z;
    // z-only precomputes (rho as in _default_rho; dz_c as in _step)
    std::vector<double> rho(n), dz_c(n + 1);
    for (size_t i = 0; i < n; ++i)
        rho[i] = p.rho_d - (p.rho_d - p.rho_s) * std::exp(-z[i] / p.H);
    dz_c[0] = 0.5 * dz[0];
    dz_c[n] = 0.5 * dz[n - 1];
    for (size_t i = 1; i < n; ++i) dz_c[i] = 0.5 * (dz[i - 1] + dz[i]);

    std::vector<double> K(n), Kf(n + 1), cap(n), al(n), ar(n);
    std::vector<double> a(n), b(n), c(n), d(n), x(n), cwork(n), dwork(n);
    std::vector<double> Tprops(n);  // property state per Picard sweep (_step)
    std::vector<double> out((size_t)n_z * (size_t)n_t);
    std::vector<double> Tsurf(n_t);

    const auto t0 = std::chrono::steady_clock::now();

    // wrap step length: the periodic grid spans [0, P-dt], so each cycle
    // must ALSO march t[-1] -> P (forcing = insol[0]); skipping it slips
    // the phase by dt per cycle and makes the attractor first-order in dt
    // (solve_pixel, audit F-5 addendum III, 2026-07-03)
    const double dt_wrap = t[1] - t[0];
    double Ts_at_zero = -1.0;  // <0: not yet available (first cycle)

    // One Crank-Nicolson step with midpoint-Picard sweeps (_step,
    // 2026-07-03): sweep 0 evaluates properties at T_prev (predictor);
    // each corrector sweep re-evaluates them at 0.5*(T_prev + T_new) and
    // re-anchors the surface Newton at the implicit T_new[0]. T stays the
    // previous state for the explicit RHS across ALL sweeps. Updates T in
    // place and returns the new surface temperature.
    auto do_step = [&](double dt, double S_new, double Ts_prev) -> double {
        for (size_t i = 0; i < n; ++i) Tprops[i] = T[i];
        double T_sub = T[0];      // Newton anchor (lagged on sweep 0)
        double Ts_new = T[0];     // Newton guess (prev sweep's Ts after 0)
        for (int64_t sweep = 0; sweep <= n_picard; ++sweep) {
            for (size_t i = 0; i < n; ++i) K[i] = k_hayne(Tprops[i], z[i], p);
            // harmonic faces (_face_harmonic_mean)
            Kf[0] = K[0]; Kf[n] = K[n - 1];
            for (size_t i = 1; i < n; ++i)
                Kf[i] = (K[i - 1] == 0.0 || K[i] == 0.0) ? 0.0
                      : 2.0 * K[i - 1] * K[i] / (K[i - 1] + K[i]);
            for (size_t i = 0; i < n; ++i) {
                cap[i] = rho[i] * cp_hayne(Tprops[i], p) * dz[i];
                al[i] = dt * Kf[i] / (dz_c[i] * cap[i]);
                ar[i] = dt * Kf[i + 1] / (dz_c[i + 1] * cap[i]);
                a[i] = -0.5 * al[i];
                c[i] = -0.5 * ar[i];
                b[i] = 1.0 + 0.5 * (al[i] + ar[i]);
            }
            // explicit RHS with wall surrogates (as in _step)
            for (size_t i = 0; i < n; ++i) {
                const double left = (i > 0) ? T[i - 1] : T[i];
                const double right = (i < n - 1) ? T[i + 1] : T[i];
                d[i] = 0.5 * al[i] * left
                     + (1.0 - 0.5 * (al[i] + ar[i])) * T[i]
                     + 0.5 * ar[i] * right;
            }
            // surface BC: Newton at endpoint forcing; trapezoidal prev ghost
            Ts_new = surface_newton(S_new, K[0], dz[0], T_sub, Ts_new, p);
            d[0] -= 0.5 * al[0] * T[0];
            d[0] += 0.5 * al[0] * Ts_prev;
            d[0] += 0.5 * al[0] * Ts_new;
            // basal Neumann (Q_b ghost)
            b[n - 1] -= 0.5 * ar[n - 1];
            d[n - 1] += dt * p.Qb / cap[n - 1];

            thomas(a, b, c, d, x, cwork, dwork);
            // midpoint state + implicit surface anchor for next sweep
            for (size_t i = 0; i < n; ++i) Tprops[i] = 0.5 * (T[i] + x[i]);
            T_sub = x[0];
        }
        for (size_t i = 0; i < n; ++i) T[i] = x[i];
        return Ts_new;
    };

    for (int64_t cyc = 1; cyc <= n_lun; ++cyc) {
        // cycle start: record state + surface temp at t=0 (solve_pixel)
        for (size_t i = 0; i < n; ++i) out[i * n_t + 0] = T[i];
        Tsurf[0] = (Ts_at_zero > 0.0)
                 ? Ts_at_zero
                 : surface_newton(insol[0], k_hayne(T[0], z[0], p), dz[0],
                                  T[0], T[0], p);
        for (int64_t k = 1; k < n_t; ++k) {
            Tsurf[k] = do_step(t[k] - t[k - 1], insol[k], Tsurf[k - 1]);
            for (size_t i = 0; i < n; ++i) out[i * n_t + k] = T[i];
        }
        // wrap step: t[-1] -> period end == next cycle's t=0 (insol[0])
        Ts_at_zero = do_step(dt_wrap, insol[0], Tsurf[n_t - 1]);
    }

    const double secs = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - t0).count();

    FILE* g = std::fopen(argv[2], "wb");
    fwrite(&secs, 8, 1, g);
    fwrite(out.data(), 8, out.size(), g);
    std::fclose(g);
    std::fprintf(stderr, "marched %lld lunations x %lld steps on %lld cells in %.3f s\n",
                 (long long)n_lun, (long long)(n_t - 1), (long long)n_z, secs);
    return 0;
}
