class ChatFile:
    def __init__(self, filename):
        self.f = open(filename, "w")

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.f.close()

    def write_msg(self, data: bytearray):
        hex = data.hex()
        self.f.write(" ".join(hex[i : (i + 2)] for i in range(0, len(hex), 2)) + "\n")
        self.f.write(
            "  ".join(chr(c) if chr(c).isprintable() else "." for c in data) + "\n"
        )
        self.f.flush()


def read_chat_file(filename):
    ret = []
    with open(filename, "r") as f:
        for line in f:
            b = line.split()
            if all(
                map(
                    lambda x: len(x) == 2
                    and all(map(lambda y: y in "0123456789ABCDEF", x.upper())),
                    b,
                )
            ):
                ret.append(bytearray(map(lambda x: int(x, 16), b)))
    return ret


def parse_res_from_chatfile(filename):
    msg = next(filter(lambda x: x.startswith(b"\x04\x0F"), read_chat_file(filename)))
    return parse_result_msg(msg)
