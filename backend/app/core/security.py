import datetime

import jwt

from app.config import EnvManager
from app.utilities import DebugMixin


class TokenService(DebugMixin):
    SECRET_KEY_ENV    = "JWT_SECRET_KEY"
    ALGORITHM_ENV     = "JWT_ALGORITHM"
    DEFAULT_ALGORITHM = "HS256"

    def __init__(self):
        self.env_manager = EnvManager()
        self.env_manager.load({self.SECRET_KEY_ENV, self.ALGORITHM_ENV})
        self.secret_key = self.env_manager.get_str(self.SECRET_KEY_ENV, "")
        self.algorithm  = self.env_manager.get_str(
            self.ALGORITHM_ENV,
            self.DEFAULT_ALGORITHM,
        )

        if not self.secret_key:
            raise RuntimeError("JWT_SECRET_KEY is missing. Run backend/dev_generate_jwt_secret.py")

    def create_token(self, payload: dict, expires_minutes: int = 60):
        data        = payload.copy()
        data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes)

        return jwt.encode(data, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str): 
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    def verify_token(self, token: str):
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload

        except jwt.ExpiredSignatureError:
            self.printDebug("Token expired")
            return None

        except jwt.InvalidTokenError as e:
            self.printDebug(f"Token invalid: {e}")
            return None
        
        except Exception as e:
            self.printDebug(f"Error decoding token: {e}")
            return None
