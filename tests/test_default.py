import pytest


pytestmark = [pytest.mark.django_db(transaction=True)]


def test_print():
    print(1)
