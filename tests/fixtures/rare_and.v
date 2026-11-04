// Fixture for lemanruss.htl.sites tests: `y` is 1 only when both a and b are 1 (rare at 1 under
// uniform random bits: P(y=1) = 0.25), so it is a clean, deterministic rarity check.
module rare_and(input a, input b, output y);
    assign y = a & b;
endmodule
