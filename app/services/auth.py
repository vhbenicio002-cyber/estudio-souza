from datetime import datetime, timedelta
from typing import Optional
import jwt
from jwt import InvalidTokenError
from argon2 import PasswordHasher, exceptions as argon2_exceptions
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User, TipoUsuario

pwd_hasher = PasswordHasher()


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def hash_password(self, password: str) -> str:
        return pwd_hasher.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_hasher.verify(hashed_password, plain_password)
        except (argon2_exceptions.VerificationError, argon2_exceptions.InvalidHashError):
            return False

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except (InvalidTokenError, TypeError, ValueError):
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_admin_user(self) -> User:
        """Cria usuário admin padrão se não existir"""
        admin = self.db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=self.hash_password(settings.ADMIN_PASSWORD),
                nome="Administrador",
                tipo=TipoUsuario.ADMIN,
            )
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)
        elif not self.verify_password(settings.ADMIN_PASSWORD, admin.hashed_password):
            # .env é a fonte de verdade para a senha administrativa; atualizar aqui
            # permite trocar a senha com segurança e reiniciar a aplicação.
            admin.hashed_password = self.hash_password(settings.ADMIN_PASSWORD)
            self.db.commit()
            self.db.refresh(admin)
        return admin