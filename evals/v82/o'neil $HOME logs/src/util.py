def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def slug(s):
    return s.lower().replace(" ", "-")

def parse_flag(s):
    # TODO: accept yes/no as well
    return s == "1"
