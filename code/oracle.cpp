// Independent subset dynamic program for maximum linear arrangement.
// No structural assumptions, path profiles, or hub parameter are used here.
#include <cstdint>
#include <vector>
#include <algorithm>

extern "C" long long maxla_oracle(int n, const int* ends) {
    if (n < 1 || n > 24) return -1;
    std::vector<uint32_t> neighbors(n, 0);
    std::vector<int> degree(n, 0);
    for (int i=0; i<n-1; ++i) {
        int u=ends[2*i], v=ends[2*i+1];
        neighbors[u] |= uint32_t(1)<<v;
        neighbors[v] |= uint32_t(1)<<u;
        ++degree[u]; ++degree[v];
    }
    uint32_t size=uint32_t(1)<<n;
    std::vector<int> cut(size,0), dp(size,0);
    for (uint32_t mask=1; mask<size; ++mask) {
        uint32_t bit=mask & -mask;
        int v=__builtin_ctz(bit);
        uint32_t previous=mask^bit;
        cut[mask]=cut[previous]+degree[v]-2*__builtin_popcount(neighbors[v]&previous);
        int best=0;
        for (uint32_t s=mask; s; s&=s-1) {
            uint32_t b=s & -s;
            best=std::max(best, dp[mask^b]);
        }
        dp[mask]=best+cut[mask];
    }
    return dp.back();
}
