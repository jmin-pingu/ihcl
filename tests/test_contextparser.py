import unittest
import os
import sys
# Get the absolute path of the project's root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the 'src' directory to the Python path
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
from contexts import Context

class TestContext(unittest.TestCase):
    def test_context_ftype(self):
        c1 = Context("test", "test.txt") 
        self.assertEqual(c1.ftype, 'txt')
        self.assertEqual(c1.description, "test")

        c2 = Context("test2", "test.pdf") 
        self.assertEqual(c2.ftype, 'pdf')
        self.assertEqual(c2.description, "test2")

        c3 = Context("test3", "test.docx") 
        self.assertEqual(c3.ftype, 'docx')
        self.assertEqual(c3.description, "test3")

        c4 = Context("test4", "test") 
        self.assertEqual(c4.ftype, None)
        self.assertEqual(c4.description, "test4")

if __name__ == "__main__":
    unittest.main()
