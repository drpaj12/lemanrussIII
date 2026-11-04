// Regression fixture for lemanruss.htl.build's victim-exclusion fix: exactly one internal net
// ($n5-shaped after write_blif) plus the output itself would be the only two rare-at candidates
// if the output were not excluded from trigger-net selection -- a trigger reading the victim's
// own net creates a combinational loop once the payload rewires that net's driver (found by
// running this shape against the real Prob011_norgate_ref.sv from
// external/Gate-Breaker-verilog-eval, not constructed to order).
module norgate_like(input a, input b, output out);
    assign out = ~(a | b);
endmodule
