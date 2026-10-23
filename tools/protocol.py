"""Plain-text trace and FNV-1a result protocol shared by all three harnesses."""

OFFSET = 0xCBF29CE484222325
PRIME = 0x100000001B3
MASK = 0xFFFFFFFFFFFFFFFF


def digest_lines(lines):
    value = OFFSET
    for line in lines:
        for byte in (line + "\n").encode("ascii"):
            value = ((value ^ byte) * PRIME) & MASK
    return f"{value:016x}"


def result_line(book, op):
    code = op[0]
    if code == "A":
        trades = book.add(int(op[1]), op[2], int(op[3]), int(op[4]))
    elif code == "M":
        trades = book.modify(int(op[1]), int(op[2]), int(op[3]))
    elif code == "D":
        book.delete(int(op[1]))
        return "D"
    else:
        level = book.best_bid() if code == "B" else book.best_ask()
        return code + "|" + ("-" if level is None else f"{level[0]},{level[1]}")
    return code + "|" + ";".join(f"{t[0]},{t[1]},{t[2]},{t[3]}" for t in trades)


def reference_digest(path):
    from reference import ReferenceBook
    book = ReferenceBook()
    with open(path, encoding="ascii") as stream:
        return digest_lines(result_line(book, line.split()) for line in stream if line.strip())

