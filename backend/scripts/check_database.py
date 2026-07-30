from app.core.database import check_database_connection


def main() -> None:
    status = "connected" if check_database_connection() else "unavailable"
    print(f"MySQL connection status: {status}")


if __name__ == "__main__":
    main()
