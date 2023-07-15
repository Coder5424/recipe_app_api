"""
Test for recipe api
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """create and return recipe"""
    default = {
        'title': 'Default Name',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Default description',
        'link': 'https://example.com'
    }
    default.update(params)

    recipe = Recipe.objects.create(user=user, **default)

    return recipe


def create_user(**params):
    """Create and return new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='test123',
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_recipe_list_limited_to_user(self):
        """Test list recipes is limited to authenticated user"""
        other_user = create_user(
            email='other@example.com',
            password='other123',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Recipe title',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(
                getattr(recipe, key),  # value recipe
                value                  # value payload
            )

        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update recipe"""
        original_link = 'https://example.com'
        recipe = create_recipe(
            user=self.user,
            title='Recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update recipe"""
        recipe = create_recipe(
            user=self.user,
            title='Recipe title',
            link='https://example.com',
            description='Recipe description',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://new_example.com',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('1.99'),
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()

        for key, value in payload.items():
            self.assertEqual(
                getattr(recipe, key),  # value recipe
                value                  # value payload
            )

        self.assertEqual(recipe.user, self.user)

    def test_update_user_return_error(self):
        """Test updating recipe user return error"""
        new_user = create_user(
            email='new_user@example.com',
            password='new_password123',
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting recipe successful"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Recipe.objects.filter(id=recipe.id).exists()
        )

    def test_delete_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error"""
        new_user = create_user(
            email='new_user@example.com',
            password='new_pass123',
        )
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Recipe.objects.filter(id=recipe.id).exists()
        )