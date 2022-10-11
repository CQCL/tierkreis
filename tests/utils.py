from tierkreis import TierkreisGraph


def nint_adder(number: int) -> TierkreisGraph:
    tk_g = TierkreisGraph()
    current_outputs = tk_g.vec_last_n_elems(tk_g.input["array"], number)

    while len(current_outputs) > 1:
        next_outputs = []
        n_even = len(current_outputs) & ~1

        for i in range(0, n_even, 2):
            nod = tk_g.add_func(
                "iadd",
                a=current_outputs[i],
                b=current_outputs[i + 1],
            )
            next_outputs.append(nod["value"])
        if len(current_outputs) > n_even:
            nod = tk_g.add_func(
                "iadd",
                a=next_outputs[-1],
                b=current_outputs[n_even],
            )
            next_outputs[-1] = nod["value"]
        current_outputs = next_outputs

    tk_g.set_outputs(out=current_outputs[0])

    return tk_g
