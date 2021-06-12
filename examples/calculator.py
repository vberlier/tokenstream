from tokenstream import TokenStream


def evaluate_sum(stream: TokenStream) -> float:
    with stream.syntax(add=r"\+", sub=r"-"):
        result = evaluate_product(stream)
        for token in stream:
            if token.match("add"):
                result += evaluate_product(stream)
            elif token.match("sub"):
                result -= evaluate_product(stream)
        return result


def evaluate_product(stream: TokenStream) -> float:
    with stream.syntax(mul=r"\*", div=r"/"):
        result = evaluate_atom(stream)
        for token in stream:
            if token.match("mul"):
                result *= evaluate_product(stream)
            elif token.match("div"):
                result /= evaluate_product(stream)
        return result


def evaluate_atom(stream: TokenStream) -> float:
    with stream.syntax(number=r"[0-9]+", brace=r"\(|\)"):
        token = stream.expect("number", brace="(")
        if token.match("number"):
            return int(token.value)
        elif token.match(brace="("):
            result = evaluate_sum(stream)
            stream.expect(brace=")")
            return result


def calculator(stream: TokenStream) -> float:
    with stream.syntax(
        add=r"\+",
        sub=r"-",
        mul=r"\*",
        div=r"/",
        number=r"[0-9]+",
        brace=r"\(|\)",
    ), stream.ignore(blanks=True):
        return calculate_sum(stream)


def calculate_sum(stream: TokenStream) -> float:
    result = calculate_product(stream)
    for add, sub in stream.collect("add", "sub"):
        if add:
            result += calculate_product(stream)
        elif sub:
            result -= calculate_product(stream)
    return result


def calculate_product(stream: TokenStream) -> float:
    result = calculate_value(stream)
    for mul, div in stream.collect("mul", "div"):
        if mul:
            result *= calculate_value(stream)
        elif div:
            result /= calculate_value(stream)
    return result


def calculate_value(stream: TokenStream) -> float:
    number, brace = stream.expect("number", brace="(")
    if number:
        return int(number.value)
    if brace:
        result = calculate_sum(stream)
        stream.expect(brace=")")
        return result
