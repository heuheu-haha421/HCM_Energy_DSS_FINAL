from secrets import token_urlsafe

from app.config import EnvManager


def main():
    env = EnvManager()
    env.set_many({
        "JWT_SECRET_KEY": token_urlsafe(48),
        "JWT_ALGORITHM" : "HS256",
    })
    print(f"JWT_SECRET_KEY and JWT_ALGORITHM saved to {env.env_file_path}")


if __name__ == "__main__":
    main()
