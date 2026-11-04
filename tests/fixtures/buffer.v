// Fixture with no rare net at all (a single pass-through bit, P(y=1)=0.5): the build.py
// "fewer than 2 rare nets found" failure path.
module buffer(input a, output y);
    assign y = a;
endmodule
