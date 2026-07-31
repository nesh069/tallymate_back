from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class SplitError(ValueError):
    """Raised when a split request is invalid (bad amounts/percentages)."""


def _to_cents(value):
    return int(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def _distribute_remainder(base_cents, total_cents, ordered_user_ids):
    """Spread the leftover cents (due to rounding) across participants, one cent
    at a time, so the shares always sum exactly to the expense amount."""
    remainder = total_cents - sum(base_cents.values())
    step = 1 if remainder >= 0 else -1
    idx = 0
    while remainder != 0:
        uid = ordered_user_ids[idx % len(ordered_user_ids)]
        base_cents[uid] += step
        remainder -= step
        idx += 1
    return base_cents


def split_equal(amount, user_ids):
    if not user_ids:
        raise SplitError("At least one participant is required.")
    if len(set(user_ids)) != len(user_ids):
        raise SplitError("Duplicate participants are not allowed.")

    total_cents = _to_cents(amount)
    n = len(user_ids)
    base_share = total_cents // n
    cents = {uid: base_share for uid in user_ids}
    cents = _distribute_remainder(cents, total_cents, sorted(user_ids))

    return {uid: (Decimal(c) / 100).quantize(CENT) for uid, c in cents.items()}


def split_unequal(amount, shares):
    if not shares:
        raise SplitError("At least one participant is required.")

    total_cents = _to_cents(amount)
    share_cents = {uid: _to_cents(val) for uid, val in shares.items()}

    if sum(share_cents.values()) != total_cents:
        raise SplitError("The individual amounts must add up to the total expense amount.")

    return {uid: (Decimal(c) / 100).quantize(CENT) for uid, c in share_cents.items()}


def split_percentage(amount, percentages):
    if not percentages:
        raise SplitError("At least one participant is required.")

    total_pct = sum(Decimal(str(p)) for p in percentages.values())
    if total_pct != Decimal("100"):
        raise SplitError("Percentages must add up to 100.")

    total_cents = _to_cents(amount)
    cents = {
        uid: int((Decimal(str(pct)) / 100 * total_cents).to_integral_value(rounding=ROUND_HALF_UP))
        for uid, pct in percentages.items()
    }
    cents = _distribute_remainder(cents, total_cents, sorted(percentages.keys()))

    return {uid: (Decimal(c) / 100).quantize(CENT) for uid, c in cents.items()}


def compute_shares(split_type, amount, participants):
    """participants: dict user_id -> value, where value's meaning depends on split_type.
    - equal: values are ignored, only the keys (user_ids) matter.
    - unequal: values are the exact amount owed by that user.
    - percentage: values are the percentage owed by that user.
    Returns dict user_id -> Decimal amount, plus percentages dict for percentage splits.
    """
    if split_type == "equal":
        amounts = split_equal(amount, list(participants.keys()))
        percentages = None
    elif split_type == "unequal":
        amounts = split_unequal(amount, participants)
        percentages = None
    elif split_type == "percentage":
        amounts = split_percentage(amount, participants)
        percentages = {uid: Decimal(str(pct)) for uid, pct in participants.items()}
    else:
        raise SplitError(f"Unknown split_type '{split_type}'.")

    return amounts, percentages
