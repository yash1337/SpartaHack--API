import os
from passlib.context import CryptContext

#To load config variables from object.
class BaseConfig:
    DEBUG=False
    TESTING=False
    SECRET_KEY=os.getenv("SECRET_KEY")
    CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    CRYPTO_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto",bcrypt__rounds=os.getenv("PASS_ENCRYPT_ROUNDS"))
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USERNAME=os.getenv("MAIL_USERNAME")

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI=os.getenv("DEV_DATABASE_URL")
    ROLE_CHANGE_PASS_DEV = os.getenv("ROLE_CHANGE_PASS_DEV")
    MAIL_DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI=os.getenv("PROD_DATABASE_URL")
    ROLE_CHANGE_PASS_PROD = os.getenv("ROLE_CHANGE_PASS_PROD")
