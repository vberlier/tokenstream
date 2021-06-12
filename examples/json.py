from tokenstream import TokenStream


def parse_json(stream: TokenStream):
    with stream.syntax(
        curly=r"\{|\}",
        bracket=r"\[|\]",
        string=r'"(?:\\.|[^\\])*?"',
        number=r"\d+",
        literal="\S+",
        colon=":",
        comma=",",
    ):
        curly, bracket, string, number, literal = stream.expect(
            ["curly", "{"],
            ["bracket", "["],
            "string",
            "number",
            "literal",
        )

        if curly:
            key = stream.expect("string")
            stream.expect("comma")
            result = {key.value: parse_json(stream)}

            for _ in stream.collect("comma"):
                key = stream.expect("string")
                stream.expect("comma")
                result[key.value] = parse_json(stream)

            return result

        elif bracket:
            result = [parse_json(stream)]

            for _ in stream.collect("comma"):
                result.append(parse_json(stream))

            return result

        elif string:
            return string.value

        elif number:
            return float(number.value)

        elif literal:
            return literal.value
