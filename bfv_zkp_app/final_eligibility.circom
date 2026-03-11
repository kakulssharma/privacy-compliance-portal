pragma circom 2.0.0;
include "circuits/bitify.circom"; // Points to the file you just made

template AMLCompliance() {
    signal input global_total;      
    signal input risk_threshold;    

    signal diff;
    diff <== risk_threshold - global_total;

    component n2b = Num2Bits(32);
    n2b.in <== diff;
}

component main {public [risk_threshold]} = AMLCompliance();