/*
 * Search core for the cube-method research project.
 *
 *  - Cube model with centres tracked (so slice / wide moves are native).
 *  - 45 search moves: 0..26  = U R F D L B M E S  x {1,2,3 quarter turns}
 *                     27..44 = u r f d l b (wide) x {1,2,3}
 *    plus 45..53 = rotations x y z (only used to build goal sets).
 *  - Part A: Korf-style optimal solver (face moves only, HTM) with a corner
 *    pattern database and two configurable edge pattern databases.
 *  - Part B: generic "pattern" abstraction tables (pieces grouped into classes,
 *    orientation tracked per class) + IDA* step solver.  This is how method
 *    steps (cross, blocks, EO, ...) are defined and measured.
 *
 * Every solution produced here is verified in Python by an independent model.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "moves.h"

typedef struct { uint8_t cp[8], co[8], ep[12], eo[12], ct[6]; } Cube;

#define N_SEARCH 45
#define N_ALL 54
static Cube MV[N_ALL];
static int MV_BASE[N_ALL];   /* 0..14 base id (U R F D L B M E S u r f d l b), 15.. rotations */
static int MV_AXIS[N_ALL];
static int inited = 0;

static void cube_id(Cube *c) {
    for (int i = 0; i < 8; i++) c->cp[i] = i, c->co[i] = 0;
    for (int i = 0; i < 12; i++) c->ep[i] = i, c->eo[i] = 0;
    for (int i = 0; i < 6; i++) c->ct[i] = i;
}
/* r = a * b  (apply a, then b) */
static void cube_mul(const Cube *a, const Cube *b, Cube *r) {
    Cube t;
    for (int i = 0; i < 8; i++) { t.cp[i] = a->cp[b->cp[i]]; t.co[i] = (a->co[b->cp[i]] + b->co[i]) % 3; }
    for (int i = 0; i < 12; i++) { t.ep[i] = a->ep[b->ep[i]]; t.eo[i] = a->eo[b->ep[i]] ^ b->eo[i]; }
    for (int i = 0; i < 6; i++) t.ct[i] = a->ct[b->ct[i]];
    *r = t;
}
static void base_cube(int b, Cube *c) {
    for (int i = 0; i < 8; i++) c->cp[i] = B_CP[b][i], c->co[i] = B_CO[b][i];
    for (int i = 0; i < 12; i++) c->ep[i] = B_EP[b][i], c->eo[i] = B_EO[b][i];
    for (int i = 0; i < 6; i++) c->ct[i] = B_CTR[b][i];
}

static void init_moves(void) {
    if (inited) return;
    Cube q[15], tmp;
    for (int b = 0; b < 9; b++) base_cube(b, &q[b]);
    /* wide: u = U E', r = R M', f = F S, d = D E, l = L M, b = B S' */
    int wf[6] = {0, 1, 2, 3, 4, 5}, ws[6] = {7, 6, 8, 7, 6, 8}, wp[6] = {3, 3, 1, 1, 1, 3};
    for (int w = 0; w < 6; w++) {
        Cube s; cube_id(&s);
        for (int k = 0; k < wp[w]; k++) cube_mul(&s, &q[ws[w]], &s);
        cube_mul(&q[wf[w]], &s, &q[9 + w]);
    }
    int axis_of_base[15] = {0, 1, 2, 0, 1, 2, 1, 0, 2, 0, 1, 2, 0, 1, 2};
    for (int b = 0; b < 15; b++) {
        Cube acc = q[b];
        for (int p = 0; p < 3; p++) {
            MV[3 * b + p] = acc; MV_BASE[3 * b + p] = b; MV_AXIS[3 * b + p] = axis_of_base[b];
            cube_mul(&acc, &q[b], &acc);
        }
    }
    for (int r = 0; r < 3; r++) {
        Cube acc; base_cube(9 + r, &acc); Cube one = acc;
        for (int p = 0; p < 3; p++) {
            MV[45 + 3 * r + p] = acc; MV_BASE[45 + 3 * r + p] = 15 + r; MV_AXIS[45 + 3 * r + p] = 3;
            cube_mul(&acc, &one, &acc);
        }
    }
    (void)tmp;
    inited = 1;
}

/* ---------------------------------------------------------------- API: basics */
int core_init(void) { init_moves(); return N_SEARCH; }

/* apply moves to a cube given as 46 bytes (cp co ep eo ct) */
void core_apply(uint8_t *st, const int *moves, int n) {
    init_moves();
    Cube c; memcpy(&c, st, sizeof c);
    for (int i = 0; i < n; i++) cube_mul(&c, &MV[moves[i]], &c);
    memcpy(st, &c, sizeof c);
}

/* =============================================================== Part A: Korf */
static uint16_t CPM[40320][18];
static uint16_t COM[2187][18];
static uint8_t EMV[24][18];      /* (pos*2+ori) -> new (pos*2+ori) for an edge under face move */
static uint8_t *CDB = NULL;      /* nibbles, 88,179,840 entries */
static uint8_t *EDB[4] = {0};    /* nibble edge DBs */
static int EK[4], ESET[4][8], NEDB = 0;
static uint64_t ESIZE[4];
static uint32_t FACT[13] = {1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800, 39916800, 479001600};

static int perm8_rank(const uint8_t *p) {
    int r = 0;
    for (int i = 0; i < 8; i++) {
        int c = 0;
        for (int j = i + 1; j < 8; j++) if (p[j] < p[i]) c++;
        r = r * (8 - i) + c;
    }
    return r;
}
static void perm8_unrank(int r, uint8_t *p) {
    int d[8];
    for (int i = 7; i >= 0; i--) { d[i] = r % (8 - i); r /= (8 - i); }
    int used[8] = {0};
    for (int i = 0; i < 8; i++) {
        int c = d[i];
        for (int v = 0; v < 8; v++) if (!used[v]) { if (c == 0) { p[i] = v; used[v] = 1; break; } c--; }
    }
}
static int co_rank(const uint8_t *co) { int r = 0; for (int i = 0; i < 7; i++) r = r * 3 + co[i]; return r; }
static void co_unrank(int r, uint8_t *co) {
    int s = 0;
    for (int i = 6; i >= 0; i--) { co[i] = r % 3; r /= 3; s += co[i]; }
    co[7] = (3 - s % 3) % 3;
}
static inline int nib_get(const uint8_t *t, uint64_t i) { return (t[i >> 1] >> ((i & 1) << 2)) & 15; }

static void korf_tables_moves(void) {
    static int done = 0;
    if (done) return;
    init_moves();
    Cube c, r;
    for (int i = 0; i < 40320; i++) {
        cube_id(&c); perm8_unrank(i, c.cp);
        for (int m = 0; m < 18; m++) { cube_mul(&c, &MV[m], &r); CPM[i][m] = perm8_rank(r.cp); }
    }
    for (int i = 0; i < 2187; i++) {
        cube_id(&c); co_unrank(i, c.co);
        for (int m = 0; m < 18; m++) { cube_mul(&c, &MV[m], &r); COM[i][m] = co_rank(r.co); }
    }
    for (int p = 0; p < 12; p++) for (int o = 0; o < 2; o++) for (int m = 0; m < 18; m++) {
        int q; for (q = 0; q < 12; q++) if (MV[m].ep[q] == p) break;
        EMV[p * 2 + o][m] = q * 2 + (o ^ MV[m].eo[q]);
    }
    done = 1;
}

/* partial permutation rank of k distinct positions out of 12, times 2^k orientation */
static uint64_t edge_rank(int k, const uint8_t *pos, const uint8_t *ori) {
    uint64_t r = 0; uint32_t used = 0;
    for (int i = 0; i < k; i++) {
        int p = pos[i];
        int c = __builtin_popcount(used & ((1u << p) - 1));
        r = r * (12 - i) + (p - c);
        used |= 1u << p;
    }
    uint64_t o = 0;
    for (int i = 0; i < k; i++) o = o * 2 + ori[i];
    return (r << k) | o;
}
static void edge_unrank(int k, uint64_t idx, uint8_t *pos, uint8_t *ori) {
    for (int i = k - 1; i >= 0; i--) { ori[i] = idx & 1; idx >>= 1; }
    int d[8];
    for (int i = k - 1; i >= 0; i--) { d[i] = idx % (12 - i); idx /= (12 - i); }
    uint32_t used = 0;
    for (int i = 0; i < k; i++) {
        int c = d[i];
        for (int v = 0; v < 12; v++) if (!(used >> v & 1)) { if (c == 0) { pos[i] = v; used |= 1u << v; break; } c--; }
    }
}

static uint8_t *bfs_to_nibbles(uint8_t *d, uint64_t n) {
    uint8_t *t = calloc((n + 1) / 2, 1);
    for (uint64_t i = 0; i < n; i++) {
        int v = d[i] > 15 ? 15 : d[i];
        t[i >> 1] |= v << ((i & 1) << 2);
    }
    return t;
}

static int load_or_save(const char *path, uint8_t **tab, uint64_t bytes, int save) {
    FILE *f = fopen(path, save ? "wb" : "rb");
    if (!f) return 0;
    size_t k;
    if (save) k = fwrite(*tab, 1, bytes, f);
    else { *tab = malloc(bytes); k = fread(*tab, 1, bytes, f); }
    fclose(f);
    return k == bytes;
}

int korf_build_corners(const char *path) {
    korf_tables_moves();
    const uint64_t N = 40320ull * 2187;
    if (path && load_or_save(path, &CDB, (N + 1) / 2, 0)) return 1;
    uint8_t *d = malloc(N); memset(d, 255, N);
    d[0] = 0; uint64_t seen = 1;
    for (int lev = 0; seen < N; lev++) {
        uint64_t before = seen;
        if (seen < N / 2) {
            for (uint64_t i = 0; i < N; i++) if (d[i] == lev) {
                int a = i / 2187, b = i % 2187;
                for (int m = 0; m < 18; m++) {
                    uint64_t j = (uint64_t)CPM[a][m] * 2187 + COM[b][m];
                    if (d[j] == 255) { d[j] = lev + 1; seen++; }
                }
            }
        } else {
            for (uint64_t i = 0; i < N; i++) if (d[i] == 255) {
                int a = i / 2187, b = i % 2187;
                for (int m = 0; m < 18; m++) {
                    uint64_t j = (uint64_t)CPM[a][m] * 2187 + COM[b][m];
                    if (d[j] == lev) { d[i] = lev + 1; seen++; break; }
                }
            }
        }
        fprintf(stderr, "corners depth %d: %llu\n", lev + 1, (unsigned long long)(seen - before));
        if (seen == before) break;
    }
    CDB = bfs_to_nibbles(d, N); free(d);
    if (path) load_or_save(path, &CDB, (N + 1) / 2, 1);
    return 1;
}

int korf_build_edges(int slot, int k, const int *set, const char *path) {
    korf_tables_moves();
    EK[slot] = k; for (int i = 0; i < k; i++) ESET[slot][i] = set[i];
    uint64_t perms = 1; for (int i = 0; i < k; i++) perms *= (12 - i);
    uint64_t N = perms << k; ESIZE[slot] = N;
    if (slot + 1 > NEDB) NEDB = slot + 1;
    if (path && load_or_save(path, &EDB[slot], (N + 1) / 2, 0)) return 1;
    uint8_t *d = malloc(N); memset(d, 255, N);
    uint8_t pos[8], ori[8], p2[8], o2[8];
    for (int i = 0; i < k; i++) pos[i] = set[i], ori[i] = 0;
    d[edge_rank(k, pos, ori)] = 0; uint64_t seen = 1;
    for (int lev = 0; seen < N; lev++) {
        uint64_t before = seen;
        int back = seen > N / 3;
        for (uint64_t i = 0; i < N; i++) {
            if (back ? d[i] != 255 : d[i] != lev) continue;
            edge_unrank(k, i, pos, ori);
            for (int m = 0; m < 18; m++) {
                for (int t = 0; t < k; t++) { int e = EMV[pos[t] * 2 + ori[t]][m]; p2[t] = e >> 1; o2[t] = e & 1; }
                uint64_t j = edge_rank(k, p2, o2);
                if (!back) { if (d[j] == 255) { d[j] = lev + 1; seen++; } }
                else if (d[j] == lev) { d[i] = lev + 1; seen++; break; }
            }
        }
        fprintf(stderr, "edges[%d] depth %d: %llu\n", slot, lev + 1, (unsigned long long)(seen - before));
        if (seen == before) break;
    }
    EDB[slot] = bfs_to_nibbles(d, N); free(d);
    if (path) load_or_save(path, &EDB[slot], (N + 1) / 2, 1);
    return 1;
}

/* ---- Korf IDA* ---- */
typedef struct {
    int cpc, coc;
    uint8_t pos[4][8], ori[4][8];
} KNode;

static int k_sol[64], k_path[64];
static int *k_out; static int k_out_cap, k_out_n, k_nsol, k_maxsol;
static uint64_t k_nodes, k_node_limit;
static uint32_t k_allowed;   /* bitmask over 18 face moves */
static int k_abort;

static inline int k_h(const KNode *s) {
    int h = nib_get(CDB, (uint64_t)s->cpc * 2187 + s->coc);
    for (int t = 0; t < NEDB; t++) {
        int v = nib_get(EDB[t], edge_rank(EK[t], s->pos[t], s->ori[t]));
        if (v > h) h = v;
    }
    return h;
}

static void k_search(const KNode *s, int g, int bound, int last) {
    if (k_abort) return;
    if (++k_nodes > k_node_limit) { k_abort = 1; return; }
    int h = k_h(s);
    if (h == 0) {
        if (g != bound) return;
        /* solved?  pattern DBs all zero implies corners and all tracked edges solved */
        if (k_out_n + g + 1 <= k_out_cap) {
            k_out[k_out_n++] = g;
            for (int i = 0; i < g; i++) k_out[k_out_n++] = k_path[i];
        }
        if (++k_nsol >= k_maxsol) k_abort = 1;
        return;
    }
    if (g + h > bound) return;
    for (int m = 0; m < 18; m++) {
        if (!(k_allowed >> m & 1)) continue;
        int b = m / 3;
        if (last >= 0) {
            int lb = last / 3;
            if (b == lb) continue;
            if (b % 3 == lb % 3 && b < lb) continue;  /* opposite faces: fixed order */
        }
        KNode n;
        n.cpc = CPM[s->cpc][m]; n.coc = COM[s->coc][m];
        for (int t = 0; t < NEDB; t++) for (int i = 0; i < EK[t]; i++) {
            int e = EMV[s->pos[t][i] * 2 + s->ori[t][i]][m]; n.pos[t][i] = e >> 1; n.ori[t][i] = e & 1;
        }
        k_path[g] = m;
        k_search(&n, g + 1, bound, m);
        if (k_abort) return;
    }
}

/* Solve optimally (HTM, face moves).  Edge DBs must jointly cover all 12 edges
 * for h==0 to imply solved.  Returns: optimal length, or -1 if node limit hit /
 * nothing found up to max_len.  Solutions written as [len, m1..mlen]* into out.
 * slack: also enumerate solutions up to best+slack (all found until max_sol). */
int korf_solve(const uint8_t *st, int max_len, int max_sol, int slack, uint32_t allowed,
               uint64_t node_limit, int *out, int out_cap, int *n_written, uint64_t *nodes) {
    korf_tables_moves();
    Cube c; memcpy(&c, st, sizeof c);
    KNode s; s.cpc = perm8_rank(c.cp); s.coc = co_rank(c.co);
    int where[12];
    for (int p = 0; p < 12; p++) where[c.ep[p]] = p;
    for (int t = 0; t < NEDB; t++) for (int i = 0; i < EK[t]; i++) {
        int e = ESET[t][i]; s.pos[t][i] = where[e]; s.ori[t][i] = c.eo[where[e]];
    }
    k_out = out; k_out_cap = out_cap; k_out_n = 0; k_nsol = 0; k_maxsol = max_sol;
    k_nodes = 0; k_node_limit = node_limit ? node_limit : ~0ull; k_allowed = allowed; k_abort = 0;
    int best = -1;
    for (int bound = k_h(&s); bound <= max_len; bound++) {
        k_search(&s, 0, bound, -1);
        if (k_nsol > 0 && best < 0) best = bound;
        if (k_abort) break;
        if (best >= 0 && bound >= best + slack) break;
    }
    *n_written = k_out_n; *nodes = k_nodes;
    if (k_nodes > k_node_limit && best < 0) return -2;
    return best;
}

/* ============================================================ Part B: patterns */
typedef struct {
    int n, mod, ncls, no;          /* positions, orientation modulus, #classes, #oriented pieces */
    int cls[12], oriented[12];     /* class of each piece, oriented flag per class */
    int count[12];
    uint64_t ncomb, size;
    uint32_t *mt;                  /* move table size*nm */
} Part;

typedef struct {
    Part p[3];                     /* corners, edges, centres */
    int nm, moves[N_SEARCH];
    uint64_t size;
    uint8_t *dist;
    int maxd;
} Pattern;

#define MAXPAT 256
static Pattern *PAT[MAXPAT];
static int NPAT = 0;

static uint64_t multinom(int n, const int *cnt, int k) {
    uint64_t r = FACT[n];
    for (int i = 0; i < k; i++) r /= FACT[cnt[i]];
    return r;
}
static uint64_t part_rank(const Part *P, const uint8_t *seq, const uint8_t *ori) {
    int cnt[12]; memcpy(cnt, P->count, sizeof cnt);
    uint64_t r = 0;
    for (int i = 0; i < P->n; i++) {
        int a = seq[i];
        for (int k = 0; k < a; k++) if (cnt[k]) { cnt[k]--; r += multinom(P->n - i - 1, cnt, P->ncls); cnt[k]++; }
        cnt[a]--;
    }
    uint64_t o = 0;
    for (int i = 0; i < P->n; i++) if (P->oriented[seq[i]]) o = o * P->mod + ori[i];
    return r * (P->size / P->ncomb) + o;
}
static void part_unrank(const Part *P, uint64_t idx, uint8_t *seq, uint8_t *ori) {
    uint64_t osz = P->size / P->ncomb;
    uint64_t o = idx % osz, r = idx / osz;
    int cnt[12]; memcpy(cnt, P->count, sizeof cnt);
    for (int i = 0; i < P->n; i++) {
        for (int k = 0; k < P->ncls; k++) {
            if (!cnt[k]) continue;
            cnt[k]--;
            uint64_t m = multinom(P->n - i - 1, cnt, P->ncls);
            if (r < m) { seq[i] = k; break; }
            r -= m; cnt[k]++;
        }
    }
    for (int i = P->n - 1; i >= 0; i--) {
        if (P->oriented[seq[i]]) { ori[i] = o % P->mod; o /= P->mod; } else ori[i] = 0;
    }
}
/* abstract state of a part from a full cube */
static uint64_t part_from_cube(const Part *P, const Cube *c, int which) {
    uint8_t seq[12], ori[12];
    for (int i = 0; i < P->n; i++) {
        int piece = which == 0 ? c->cp[i] : which == 1 ? c->ep[i] : c->ct[i];
        seq[i] = P->cls[piece];
        ori[i] = which == 0 ? c->co[i] : which == 1 ? c->eo[i] : 0;
    }
    return part_rank(P, seq, ori);
}
static void part_init(Part *P, int n, int mod, const int *cls, const int *oriented_cls, int which, const int *moves, int nm) {
    P->n = n; P->mod = mod; P->ncls = 0;
    memset(P->count, 0, sizeof P->count);
    for (int i = 0; i < n; i++) { P->cls[i] = cls[i]; if (cls[i] + 1 > P->ncls) P->ncls = cls[i] + 1; P->count[cls[i]]++; }
    P->no = 0;
    for (int k = 0; k < P->ncls; k++) { P->oriented[k] = mod > 1 ? oriented_cls[k] : 0; if (P->oriented[k]) P->no += P->count[k]; }
    P->ncomb = multinom(n, P->count, P->ncls);
    uint64_t osz = 1; for (int i = 0; i < P->no; i++) osz *= mod;
    P->size = P->ncomb * osz;
    P->mt = malloc(sizeof(uint32_t) * P->size * nm);
    uint8_t seq[12], ori[12], s2[12], o2[12];
    for (uint64_t idx = 0; idx < P->size; idx++) {
        part_unrank(P, idx, seq, ori);
        for (int j = 0; j < nm; j++) {
            const Cube *M = &MV[moves[j]];
            for (int i = 0; i < n; i++) {
                int from = which == 0 ? M->cp[i] : which == 1 ? M->ep[i] : M->ct[i];
                int d = which == 0 ? M->co[i] : which == 1 ? M->eo[i] : 0;
                s2[i] = seq[from];
                o2[i] = P->oriented[seq[from]] ? (ori[from] + d) % mod : 0;
            }
            P->mt[idx * nm + j] = (uint32_t)part_rank(P, s2, o2);
        }
    }
}
static inline uint64_t pat_index(const Pattern *T, uint64_t a, uint64_t b, uint64_t c) {
    return (a * T->p[1].size + b) * T->p[2].size + c;
}

/* Create a pattern.  cls arrays give the class of every corner/edge/centre
 * cubie (class ids 0..k-1); ori arrays give a 0/1 "orientation tracked" flag per
 * class.  targets: ntarget cube states (46 bytes each) that count as solved.
 * Returns a handle, or -1. */
int pattern_create(const int *ccls, const int *cori, const int *ecls, const int *eori,
                   const int *xcls, const int *moves, int nm,
                   const uint8_t *targets, int ntarget, const char *cache_path) {
    init_moves();
    if (NPAT >= MAXPAT) return -1;
    Pattern *T = calloc(1, sizeof *T);
    T->nm = nm; memcpy(T->moves, moves, sizeof(int) * nm);
    int zero[12] = {0};
    part_init(&T->p[0], 8, 3, ccls, cori, 0, moves, nm);
    part_init(&T->p[1], 12, 2, ecls, eori, 1, moves, nm);
    part_init(&T->p[2], 6, 1, xcls, zero, 2, moves, nm);
    T->size = T->p[0].size * T->p[1].size * T->p[2].size;
    if (cache_path && load_or_save(cache_path, &T->dist, T->size, 0)) {
        T->maxd = 0; for (uint64_t i = 0; i < T->size; i++) if (T->dist[i] != 255 && T->dist[i] > T->maxd) T->maxd = T->dist[i];
        PAT[NPAT] = T; return NPAT++;
    }
    T->dist = malloc(T->size); memset(T->dist, 255, T->size);
    uint64_t seen = 0;
    for (int t = 0; t < ntarget; t++) {
        Cube c; memcpy(&c, targets + 46 * t, 46);
        uint64_t i = pat_index(T, part_from_cube(&T->p[0], &c, 0), part_from_cube(&T->p[1], &c, 1), part_from_cube(&T->p[2], &c, 2));
        if (T->dist[i] == 255) { T->dist[i] = 0; seen++; }
    }
    uint64_t S1 = T->p[1].size, S2 = T->p[2].size;
    int lev;
    for (lev = 0; ; lev++) {
        uint64_t before = seen;
        for (uint64_t i = 0; i < T->size; i++) {
            if (T->dist[i] != lev) continue;
            uint64_t a = i / (S1 * S2), b = (i / S2) % S1, c = i % S2;
            for (int j = 0; j < nm; j++) {
                uint64_t k = pat_index(T, T->p[0].mt[a * nm + j], T->p[1].mt[b * nm + j], T->p[2].mt[c * nm + j]);
                if (T->dist[k] == 255) { T->dist[k] = lev + 1; seen++; }
            }
        }
        if (seen == before) break;
    }
    T->maxd = lev;
    if (cache_path) load_or_save(cache_path, &T->dist, T->size, 1);
    PAT[NPAT] = T;
    return NPAT++;
}

uint64_t pattern_size(int h) { return PAT[h]->size; }
int pattern_maxdepth(int h) { return PAT[h]->maxd; }
/* histogram of distances (over reachable abstract states) */
void pattern_histogram(int h, uint64_t *hist, int nh) {
    Pattern *T = PAT[h];
    memset(hist, 0, sizeof(uint64_t) * nh);
    for (uint64_t i = 0; i < T->size; i++) if (T->dist[i] != 255 && T->dist[i] < nh) hist[T->dist[i]]++;
}
int pattern_distance(int h, const uint8_t *st) {
    Pattern *T = PAT[h]; Cube c; memcpy(&c, st, 46);
    return T->dist[pat_index(T, part_from_cube(&T->p[0], &c, 0), part_from_cube(&T->p[1], &c, 1), part_from_cube(&T->p[2], &c, 2))];
}

/* ---- step IDA* over a conjunction of patterns sharing one move list ---- */
static int s_np, s_hs[16], s_nm, s_moves[N_SEARCH];
static int s_path[64];
static int *s_out; static int s_cap, s_outn, s_nsol, s_maxsol, s_abort;
static uint64_t s_nodes, s_limit;

static void s_search(uint64_t *co, int g, int bound, int lastm) {
    if (s_abort) return;
    if (++s_nodes > s_limit) { s_abort = 1; return; }
    int h = 0;
    for (int t = 0; t < s_np; t++) {
        Pattern *T = PAT[s_hs[t]];
        int v = T->dist[pat_index(T, co[3 * t], co[3 * t + 1], co[3 * t + 2])];
        if (v > h) h = v;
    }
    if (h == 0) {
        if (g == bound) {
            if (s_outn + g + 1 <= s_cap) { s_out[s_outn++] = g; for (int i = 0; i < g; i++) s_out[s_outn++] = s_moves[s_path[i]]; }
            if (++s_nsol >= s_maxsol) s_abort = 1;
        }
        return;   /* do not extend through a goal state: solutions are minimal-prefix */
    }
    if (g + h > bound) return;
    uint64_t nc[48];
    for (int j = 0; j < s_nm; j++) {
        int m = s_moves[j];
        if (lastm >= 0) {
            int lm = s_moves[lastm];
            if (MV_AXIS[m] == MV_AXIS[lm] && MV_BASE[m] <= MV_BASE[lm]) continue;
        }
        for (int t = 0; t < s_np; t++) {
            Pattern *T = PAT[s_hs[t]];
            nc[3 * t] = T->p[0].mt[co[3 * t] * s_nm + j];
            nc[3 * t + 1] = T->p[1].mt[co[3 * t + 1] * s_nm + j];
            nc[3 * t + 2] = T->p[2].mt[co[3 * t + 2] * s_nm + j];
        }
        s_path[g] = j;
        s_search(nc, g + 1, bound, j);
        if (s_abort) return;
    }
}

/* Returns the optimal length (>=0), -1 if none within max_len, -2 if node limit
 * hit before any solution.  Solutions of length best..best+slack are written as
 * [len, move ids...] (move ids are global 0..44). */
int step_solve(const uint8_t *st, const int *handles, int np, int max_len, int max_sol, int slack,
               uint64_t node_limit, int *out, int out_cap, int *n_written, uint64_t *nodes) {
    init_moves();
    s_np = np; memcpy(s_hs, handles, sizeof(int) * np);
    Pattern *T0 = PAT[handles[0]];
    s_nm = T0->nm; memcpy(s_moves, T0->moves, sizeof(int) * s_nm);
    for (int t = 1; t < np; t++) {
        if (PAT[handles[t]]->nm != s_nm || memcmp(PAT[handles[t]]->moves, s_moves, sizeof(int) * s_nm)) return -3;
    }
    Cube c; memcpy(&c, st, 46);
    uint64_t co[48];
    int h0 = 0;
    for (int t = 0; t < np; t++) {
        Pattern *T = PAT[handles[t]];
        co[3 * t] = part_from_cube(&T->p[0], &c, 0);
        co[3 * t + 1] = part_from_cube(&T->p[1], &c, 1);
        co[3 * t + 2] = part_from_cube(&T->p[2], &c, 2);
        int v = T->dist[pat_index(T, co[3 * t], co[3 * t + 1], co[3 * t + 2])];
        if (v == 255) { *n_written = 0; *nodes = 0; return -1; }
        if (v > h0) h0 = v;
    }
    s_out = out; s_cap = out_cap; s_outn = 0; s_nsol = 0; s_maxsol = max_sol; s_abort = 0;
    s_nodes = 0; s_limit = node_limit ? node_limit : ~0ull;
    int best = -1;
    for (int bound = h0; bound <= max_len; bound++) {
        s_search(co, 0, bound, -1);
        if (s_nsol > 0 && best < 0) best = bound;
        if (s_abort) break;
        if (best >= 0 && bound >= best + slack) break;
    }
    *n_written = s_outn; *nodes = s_nodes;
    if (best < 0 && s_nodes > s_limit) return -2;
    return best;
}
