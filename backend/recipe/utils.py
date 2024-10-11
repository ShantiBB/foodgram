import random
import string


def generate_short_link():
    short_link = ''.join(random.choices(
        string.ascii_letters + string.digits,
        k=random.randint(6, 10)
    ))
    return short_link.lower()
