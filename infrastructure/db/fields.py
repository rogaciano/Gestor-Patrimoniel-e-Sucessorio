from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64

class EncryptedDataField(models.CharField):
    description = "Armazena dados criptografados de forma transparente"

    def __init__(self, *args, **kwargs):
        # We assume FIELD_ENCRYPTION_KEY is available in settings.
        # However, to avoid import errors during migrations if it's not set yet, we might want to be careful.
        # But per instructions, we implement strict integration.
        kwargs.setdefault('max_length', 500) # Espaço extra para o hash da criptografia
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Criptografa o dado antes de salvar no banco."""
        if value is None:
            return value
        fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)
        return fernet.encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        """Descriptografa o dado ao ler do banco."""
        if value is None:
            return value
        try:
            fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)
            return fernet.decrypt(value.encode()).decode()
        except Exception:
            return value

    def to_python(self, value):
        """Garante a descriptografia na manipulação do formulário/admin."""
        if value is None or not isinstance(value, str):
            return value
        try:
            # If it looks like base64-encoded encrypted data, try to decrypt.
            # But this is tricky because plain text could also be valid.
            # Usually from_db_value handles the DB read. to_python handles form input which is usually plain text.
            # But if we assign an encrypted string to the model field, we might want todecrypt it? 
            # Actually, standard Django flow: form provides plain text -> to_python returns plain text -> get_prep_value encrypts it.
            # from_db_value decrypts DB content -> Python object.
            # The user's code for to_python decrypted it. This implies usage where internal value MIGHT be encrypted.
            fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)
            return fernet.decrypt(value.encode()).decode()
        except Exception:
            return value
