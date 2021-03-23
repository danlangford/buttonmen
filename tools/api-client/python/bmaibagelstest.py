import unittest
from bmaibagels import SomeUtils


class TestSomeUtils(unittest.TestCase):

  def setUp(self):
    self.SomeUtils = SomeUtils()

  def test_random_fortune_file(self):
    filepath = self.SomeUtils.get_fortune_file()
    print(filepath)
    self.assertIsNotNone(filepath)

  def test_random_fortune(self):
    fortune = self.SomeUtils.get_random_fortune()
    print(fortune)
    self.assertIsNotNone(fortune)


if __name__ == '__main__':
  unittest.main()
