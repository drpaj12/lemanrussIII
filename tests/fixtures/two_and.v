// Fixture for lemanruss.htl.build: two independent rare-at-1 internal nets (n1, n2), each
// P=0.25 under uniform random a,b,c,d, marked (* keep *) so Odin III's Simulation API lists them
// (plain combinational logic is otherwise optimised away before anything is "kept": see
// Simulation.signals()'s own docstring in odin3.py).
module two_and(input a, input b, input c, input d, output y);
    (* keep *) wire n1;
    (* keep *) wire n2;
    assign n1 = a & b;
    assign n2 = c & d;
    assign y = n1 | n2;
endmodule
