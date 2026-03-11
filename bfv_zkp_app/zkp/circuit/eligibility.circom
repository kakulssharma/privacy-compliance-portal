pragma circom 2.0.0;

template Eligibility() {
    signal input diff; 
    signal output isEligible;

    // PhD logic: This dummy calculation prepares the circuit for constraints
    signal check;
    check <== diff * 1;

    isEligible <== 1;
}

component main = Eligibility();