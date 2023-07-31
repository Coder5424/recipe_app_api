"""
Test for ingredients api
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    Ingredient,
    Recipe
)
from recipe.serializers import IngredientSerializer
from decimal import Decimal


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return ingredient detail URL"""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='pass123'):
    """Create and return new user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientsAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPITests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Ingredient_1')
        Ingredient.objects.create(user=self.user, name='Ingredient_2')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user"""
        user2 = create_user(email='user2@example.com')

        Ingredient.objects.create(user=user2, name='Ingredient_user2')
        ingredient = Ingredient.objects.create(user=self.user, name='Ingredient_self.user')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(res.data),
            1
        )
        self.assertEqual(
            res.data[0]['name'],
            ingredient.name
        )
        self.assertEqual(
            res.data[0]['id'],
            ingredient.id
        )

    def test_update_ingredient(self):
        """Test updating ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='ingredient_1')

        payload = {
            'name': 'ingredient_1_new'
        }
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredient.refresh_from_db()

        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='ingredient_1')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        ingredients = Ingredient.objects.filter(user=self.user)

        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_recipes(self):
        """Test listing ingredients assigned to recipes"""
        ing1 = Ingredient.objects.create(user=self.user, name='ing 1')
        ing2 = Ingredient.objects.create(user=self.user, name='ing 2')

        recipe = Recipe.objects.create(
            title='Default Name',
            time_minutes=22,
            price=Decimal('5.25'),
            user=self.user,
        )
        recipe.ingredients.add(ing1)

        res = self.client.get(
            INGREDIENTS_URL,
            {'assigned_only': 1}
        )

        ser1 = IngredientSerializer(ing1)
        ser2 = IngredientSerializer(ing2)

        self.assertIn(ser1.data, res.data)
        self.assertNotIn(ser2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns unique list"""
        ing = Ingredient.objects.create(user=self.user, name='ing 1')
        Ingredient.objects.create(user=self.user, name='ing 2')

        recipe1 = Recipe.objects.create(
            title='Recipe 1',
            time_minutes=22,
            price=Decimal('5.25'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Recipe 2',
            time_minutes=22,
            price=Decimal('5.25'),
            user=self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        ser = IngredientSerializer(ing)

        res = self.client.get(
            INGREDIENTS_URL,
            {'assigned_only': 1}
        )

        self.assertEqual(
            len(res.data),
            1
        )
        self.assertIn(ser.data, res.data)




