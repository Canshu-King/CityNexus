from __future__ import annotations

import argparse

from app.traveler_principal import issue_traveler_token


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mint one short-lived CityNexus traveler bearer for local R28 validation."
    )
    parser.add_argument("--traveler-id", required=True)
    parser.add_argument("--ttl-seconds", type=int, default=None)
    args = parser.parse_args()
    print(
        issue_traveler_token(
            args.traveler_id,
            ttl_seconds=args.ttl_seconds,
        )
    )


if __name__ == "__main__":
    main()
