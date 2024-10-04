
def pop_items(self, validated_data):
    ingredients_data = validated_data.pop('recipe_ingredients')
    tags_data = validated_data.pop('tags')

    return ingredients_data, tags_data

def create_ingredients(self, item_data):
    ing_id = item_data.get('ingredient').get('id')
    amount = item_data.get('amount')
    try:
        exist_ingredient = Ingredient.objects.get(id=ing_id)
    except Ingredient.DoesNotExist:
        raise NotFound(f'Ингредиент с id {ing_id} не существует')
    return exist_ingredient, amount