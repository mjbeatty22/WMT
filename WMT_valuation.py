"""Simple peer P/E valuation.

Run with: python WMT_valuation.py
"""

# Editable inputs. Prices and EPS are dollars per share.
TARGET = {
    "ticker": "WMT",
    "price": None,  # Unresolved: Nasdaq matched-date close not verified.
    "diluted_eps": 2.73,  # FY ended January 31, 2026.
}

PEERS = [
    {
        "ticker": "COST",
        "price": None,  # Unresolved: Nasdaq matched-date close not verified.
        "diluted_eps": 18.21,  # FY ended August 31, 2025.
    },
]


def is_positive_number(value):
    return isinstance(value, (int, float)) and value > 0


def is_valid_peer(peer):
    return is_positive_number(peer.get("price")) and is_positive_number(
        peer.get("diluted_eps")
    )


def median(values):
    ordered_values = sorted(values)
    count = len(ordered_values)
    middle = count // 2

    if count % 2 == 1:
        return ordered_values[middle]

    return (ordered_values[middle - 1] + ordered_values[middle]) / 2


def unique_non_target_peers(peers, target_ticker):
    unique_peers = []
    seen_tickers = set()
    target_ticker = target_ticker.upper()

    for peer in peers:
        ticker = str(peer.get("ticker", "")).upper()

        if not ticker or ticker == target_ticker or ticker in seen_tickers:
            continue

        seen_tickers.add(ticker)
        unique_peers.append(peer)

    return unique_peers


def peer_pe(peer):
    return peer["price"] / peer["diluted_eps"]


def implied_price(pe_multiple, target_eps):
    return pe_multiple * target_eps


def print_peer_peers(peers):
    print("Peer P/E multiples")

    for peer in peers:
        ticker = peer.get("ticker", "Unknown")

        if is_valid_peer(peer):
            print(f"{ticker}: {peer_pe(peer):.6f}x")
        else:
            print(f"{ticker}: not meaningful (missing or nonpositive price or diluted EPS)")


def print_implied_prices(valid_peers, target_eps):
    if not is_positive_number(target_eps):
        print("\nImplied target prices: not meaningful (missing or nonpositive target diluted EPS)")
        return None

    peer_multiples = [peer_pe(peer) for peer in valid_peers]

    if not peer_multiples:
        print("\nImplied target prices: no usable peers")
        return None

    minimum_multiple = min(peer_multiples)
    median_multiple = median(peer_multiples)
    maximum_multiple = max(peer_multiples)

    minimum_price = implied_price(minimum_multiple, target_eps)
    median_price = implied_price(median_multiple, target_eps)
    maximum_price = implied_price(maximum_multiple, target_eps)

    print("\nImplied target prices")

    if len(valid_peers) == 1:
        print(f"Reference estimate: ${median_price:.2f} ({median_multiple:.6f}x)")
    else:
        print(f"Minimum: ${minimum_price:.2f} ({minimum_multiple:.6f}x)")
        print(f"Median: ${median_price:.2f} ({median_multiple:.6f}x)")
        print(f"Maximum: ${maximum_price:.2f} ({maximum_multiple:.6f}x)")

    return median_price


def print_peer_removals(peers, target_eps, full_peer_estimate):
    print("\nPeer-removal analysis")

    if full_peer_estimate is None:
        print("No estimate: there are no usable full-peer results.")
        return

    for peer_to_remove in peers:
        remaining_peers = [peer for peer in peers if peer is not peer_to_remove]
        remaining_valid_peers = [peer for peer in remaining_peers if is_valid_peer(peer)]
        ticker = peer_to_remove.get("ticker", "Unknown")

        if not remaining_valid_peers:
            print(f"Remove {ticker}: no estimate (no usable peers remain)")
            continue

        remaining_multiples = [peer_pe(peer) for peer in remaining_valid_peers]
        remaining_median = median(remaining_multiples)
        remaining_price = implied_price(remaining_median, target_eps)
        dollar_change = remaining_price - full_peer_estimate

        print(
            f"Remove {ticker}: ${remaining_price:.2f}; "
            f"change from full-peer estimate: {dollar_change:+.2f}"
        )


def main():
    target_ticker = str(TARGET.get("ticker", "")).upper()
    peers = unique_non_target_peers(PEERS, target_ticker)
    target_eps = TARGET.get("diluted_eps")
    target_price = TARGET.get("price")

    print(f"Target: {target_ticker}")

    if is_positive_number(target_price):
        print(f"Target price: ${target_price:.2f}")
    else:
        print("Target price: not meaningful (missing or nonpositive price)")

    if is_positive_number(target_eps):
        print(f"Target diluted EPS: ${target_eps:.6f}")
    else:
        print("Target diluted EPS: not meaningful (missing or nonpositive diluted EPS)")

    print_peer_peers(peers)
    valid_peers = [peer for peer in peers if is_valid_peer(peer)]
    full_peer_estimate = print_implied_prices(valid_peers, target_eps)

    if is_positive_number(target_eps):
        print_peer_removals(peers, target_eps, full_peer_estimate)
    else:
        print("\nPeer-removal analysis: not meaningful (missing or nonpositive target diluted EPS)")


if __name__ == "__main__":
    main()
