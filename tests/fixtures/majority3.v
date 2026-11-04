// Fixture: 3-input majority voter. y=1 when at least two of a,b,c are 1 (P(y=1)=0.5 exactly
// under uniform random bits, so m is a non-rare baseline next to rare_and and word4.
module majority3(input a, input b, input c, output y);
    assign y = (a & b) | (b & c) | (a & c);
endmodule
