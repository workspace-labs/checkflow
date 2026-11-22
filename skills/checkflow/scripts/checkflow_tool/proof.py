"""Keep both proofs with enough attribution to select the client evidence."""

from .storage import Refusal


FIRST_LABEL = "First checker: "
SECOND_LABEL = "\nSecond checker: "
PAIR_HEADER = "Proof for the reported result: "


def labelled(first, second):
    return first if first == second else f"{FIRST_LABEL}{first}{SECOND_LABEL}{second}"


def attributed(first, second, selected):
    if first == second:
        return first
    # Length keeps a label inside either checker’s multiline proof from ending it.
    return f"{PAIR_HEADER}{selected} {len(first)}\n{labelled(first, second)}"


def split_pair(text):
    if not text.startswith(PAIR_HEADER):
        return None
    header, _, body = text[len(PAIR_HEADER):].partition("\n")
    selected, _, size = header.partition(" ")
    error = "Refresh the merged proof. Its checker attribution is incomplete."
    if (selected not in ("first", "second", "both") or not size.isdecimal()
            or len(size) > len(str(len(body)))):
        raise Refusal(error)
    left_end = len(FIRST_LABEL) + int(size)
    right_start = left_end + len(SECOND_LABEL)
    first, second = body[len(FIRST_LABEL):left_end], body[right_start:]
    if (not body.startswith(FIRST_LABEL) or body[left_end:right_start] != SECOND_LABEL
            or not first.strip() or not second.strip()):
        raise Refusal(error)
    return selected, first, second


def owner_text(text):
    pair = split_pair(text)
    if pair is None:
        return text
    _, first, second = pair
    return labelled(owner_text(first), owner_text(second))


def client_text(text, point_id):
    pair = split_pair(text)
    if pair is None:
        if text.startswith(FIRST_LABEL) and SECOND_LABEL in text:
            raise Refusal(f"Refresh proof for {point_id} with evidence for its reported result. "
                          "This earlier merged proof does not record which evidence supports it.")
        return text
    selected, first, second = pair
    if selected == "first":
        return client_text(first, point_id)
    if selected == "second":
        return client_text(second, point_id)
    return f"{client_text(first, point_id)}\n{client_text(second, point_id)}"
