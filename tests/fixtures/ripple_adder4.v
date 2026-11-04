// Regression fixture for lemanruss.htl.build's equivalence fix: a 4-bit ripple-carry adder's
// internal carry nets can each be realised by more than one input combination, so excluding
// only the single witness find_driving_inputs returns (round 2's first attempt) wrongly
// reported "not equivalent" against the real adder_4bit.v
// (external/vtr-verilog-to-routing/vtr_flow/benchmarks/func_sim/adder_4bit/adder_4bit.v, not
// constructed to order); the fix excludes every combination the trigger fires on.
module ripple_adder4(
    input cin, input a0, a1, a2, a3, input b0, b1, b2, b3,
    output s0, s1, s2, s3, output cout
);
    wire c0, c1, c2;
    assign s0 = a0 ^ b0 ^ cin;
    assign c0 = (a0 & b0) | ((a0 ^ b0) & cin);
    assign s1 = a1 ^ b1 ^ c0;
    assign c1 = (a1 & b1) | ((a1 ^ b1) & c0);
    assign s2 = a2 ^ b2 ^ c1;
    assign c2 = (a2 & b2) | ((a2 ^ b2) & c1);
    assign s3 = a3 ^ b3 ^ c2;
    assign cout = (a3 & b3) | ((a3 ^ b3) & c2);
endmodule
