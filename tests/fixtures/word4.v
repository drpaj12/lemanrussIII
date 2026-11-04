// Fixture: a 4-bit word output, for ErrHi/ErrLo payload coverage (ErrHi/ErrLo need width > 1).
// out[3]=a&b (rare at 1, P=0.25), out[2:0]=c (a straight pass-through).
module word4(input a, input b, input [2:0] c, output [3:0] out);
    assign out = {a & b, c};
endmodule
