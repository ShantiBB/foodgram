import hashlib
import os

from django.core.files.storage import FileSystemStorage


class DeduplicateStorage(FileSystemStorage):
    """Проверяет на наличие дупликатов файлов"""

    def save(self, name, content, max_length=None):
        content.seek(0)
        content_hash = hashlib.sha256(content.read()).hexdigest()
        content.seek(0)
        dir_name, file_name = os.path.split(name)
        base_name, ext = os.path.splitext(file_name)
        new_name = os.path.join(dir_name, f"{content_hash}{ext}")

        if not self.exists(new_name):
            return super().save(new_name, content, max_length)
        return new_name
