from __future__ import annotations

import argparse
import asyncio
import json

from test_harness import sign_in_with_supabase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sign in a Supabase test user and print a reusable bearer token.")
    parser.add_argument("--email", required=True, help="Supabase user email.")
    parser.add_argument("--password", required=True, help="Supabase user password.")
    parser.add_argument("--supabase-url", default=None, help="Override Supabase project URL.")
    parser.add_argument("--supabase-anon-key", default=None, help="Override Supabase anon key.")
    parser.add_argument("--json", action="store_true", help="Print a JSON payload instead of a plain access token.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    session = await sign_in_with_supabase(
        email=args.email,
        password=args.password,
        supabase_url=args.supabase_url,
        supabase_anon_key=args.supabase_anon_key,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "email": session.email,
                    "user_id": session.user_id,
                    "access_token": session.access_token,
                }
            )
        )
        return
    print(session.access_token)


if __name__ == "__main__":
    asyncio.run(main())
