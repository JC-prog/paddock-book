import argparse
import sys

from src.core.db import get_connection
from src.core.logging import configure_logging
from src.modules.admin.service import promote_account


def main() -> int:
    configure_logging()

    parser = argparse.ArgumentParser(
        prog="python -m src.modules.admin.cli",
        description="Promote an existing account to admin access.",
    )
    parser.add_argument("--promote-admin", required=True, metavar="EMAIL", help="Email of the account to promote")
    args = parser.parse_args()

    conn = get_connection()
    try:
        promoted = promote_account(args.promote_admin, conn=conn)
    except ValueError as exc:
        print(f"Promotion failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"'{promoted['email']}' now has admin access.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
