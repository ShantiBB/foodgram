import csv
import os

import django

from recipe.models import Ingredient

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'foodgram_backend.settings')
django.setup()


def import_ingredients(csv_filepath):
    if not os.path.exists(csv_filepath):
        print(f"Файл {csv_filepath} не найден.")
        return

    with open(csv_filepath, encoding='utf-8') as f:
        reader = csv.reader(f)
        count = 0
        for row in reader:
            print(row)
            name = row[0]
            measurement_unit = row[1]

            if not name or not measurement_unit:
                print(f"Пропущена строка с данными: {row}")
                continue

            ingredient, created = Ingredient.objects.get_or_create(
                name=name,
                defaults={'measurement_unit': measurement_unit}
            )
            if created:
                print(f"Создано: {ingredient}")
            else:
                print(f"Уже существует: {ingredient}")
            count += 1

        print(f"Импортировано {count} ингредиентов.")


if __name__ == '__main__':
    csv_file_path = 'ingredients.csv'
    import_ingredients(csv_file_path)
