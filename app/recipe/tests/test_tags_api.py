"""
Tests for tags API
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    Tag,
    Recipe,
)
from recipe.serializers import TagSerializer
from decimal import Decimal


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create and return tag detail URL"""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='pass123'):
    """Create and return new user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_tags(self):
        """Test retrieving list of tags"""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""
        user2 = create_user(email='user2@example.com', password='passuser2')
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(res.data),
            1
        )
        self.assertEqual(
            res.data[0]['name'],
            tag.name
        )
        self.assertEqual(
            res.data[0]['id'],
            tag.id
        )

    def test_update_tag(self):
        """Test updating tag"""
        tag = Tag.objects.create(user=self.user, name='Dinner')

        payload = {'name': 'Dessert'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tag.refresh_from_db()

        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting tag"""
        tag = Tag.objects.create(user=self.user, name='Dinner')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Tag.objects.filter(user=self.user).exists()
        )

    def test_filter_tags_assigned_recipes(self):
        """Test listing tags assigned to recipes"""
        tag1 = Tag.objects.create(user=self.user, name='tag 1')
        tag2 = Tag.objects.create(user=self.user, name='tag 2')

        recipe = Recipe.objects.create(
            title='Default Name',
            time_minutes=22,
            price=Decimal('5.25'),
            user=self.user,
        )
        recipe.tags.add(tag1)

        res = self.client.get(
            TAGS_URL,
            {'assigned_only': 1}
        )

        ser1 = TagSerializer(tag1)
        ser2 = TagSerializer(tag2)

        self.assertIn(ser1.data, res.data)
        self.assertNotIn(ser2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtered tags returns unique list"""
        tag = Tag.objects.create(user=self.user, name='tag 1')
        Tag.objects.create(user=self.user, name='tag 2')

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
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        ser = TagSerializer(tag)

        res = self.client.get(
            TAGS_URL,
            {'assigned_only': 1}
        )

        self.assertEqual(
            len(res.data),
            1
        )
        self.assertIn(ser.data, res.data)



